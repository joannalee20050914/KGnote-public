#!/usr/bin/env python3
"""Durable autonomous implementer/reviewer loop for the KGnote control plane.

Repository artifacts remain authoritative.  This process only coordinates the
existing fingerprint-bound review helpers and separate ephemeral Codex contexts;
it does not decide product questions or promote human/release gates.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import codex_control as control
import external_review_control
import publish_external_candidate


STATE_PATH = ".ai/ORCHESTRATOR_STATE.json"
STOP_PATH = ".ai/ORCHESTRATOR_STOP"
LOCK_PATH = ".ai/ORCHESTRATOR.lock"
HISTORY_PATH = ".ai/ORCHESTRATION_HISTORY/events.jsonl"
TERMINAL_STATES = {
    "HUMAN_CHECKPOINT_REQUIRED",
    "PRODUCT_DECISION_REQUIRED",
    "AUTHORITY_CONFLICT",
    "AUTOMATION_BLOCKED",
    "BUDGET_EXHAUSTED",
    "GOAL_COMPLETE",
    "STOPPED",
}
MACHINE_HANDOFF_STATES = {"AWAITING_EXTERNAL_PRODUCT_REVIEW"}
MACHINE_STATES = {
    "IMPLEMENTING",
    "VALIDATING",
    "READY_FOR_AI_REVIEW",
    "REVIEWING",
    "REPAIRING",
}
QUOTA_MARKERS = (
    "usage limit",
    "quota exceeded",
    "insufficient quota",
    "budget exhausted",
    "rate limit exceeded",
)


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")


def state_path(repo: Path) -> Path:
    return repo / STATE_PATH


def read_state(repo: Path) -> dict[str, Any] | None:
    path = state_path(repo)
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "kgnote.orchestrator-state.v1":
        raise ValueError("orchestrator_state: unsupported schema_version")
    return value


def write_state(repo: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    path = state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_event(repo: Path, state: dict[str, Any], event_type: str, **details: Any) -> None:
    path = repo / HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_type": event_type,
        "run_id": state["run_id"],
        "goal_id": state.get("active_goal"),
        "work_package": state.get("work_package"),
        "state": state.get("state"),
        "review_cycle": state.get("review_cycle"),
        "candidate_fingerprint": state.get("candidate_fingerprint"),
        "created_at": now(),
        **details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n")


def next_human_checkpoint(plan: dict[str, Any]) -> dict[str, Any] | None:
    for gate in plan.get("preserved_human_gates", []):
        if gate.get("status") not in {"complete", "passed", "approved"}:
            return {
                "id": gate.get("id"),
                "status": gate.get("status"),
                "description": gate.get("rule") or gate.get("description"),
            }
    return None


def derive_state(repo: Path, *, max_review_cycles: int = 5) -> dict[str, Any]:
    plan, status = control.load_plan_status(repo)
    request, result, _ = control.load_review_artifacts(repo)
    review_state = request.get("status")
    mapped = {
        "IMPLEMENTING": "IMPLEMENTING",
        "READY_FOR_REVIEW": "READY_FOR_AI_REVIEW",
        "UNDER_REVIEW": "REVIEWING",
        "CHANGES_REQUIRED": "REPAIRING",
        "PRODUCT_DECISION_REQUIRED": "PRODUCT_DECISION_REQUIRED",
        "PASS": "VALIDATING",
    }.get(review_state, "AUTOMATION_BLOCKED")
    if plan.get("status") == "complete":
        mapped = "GOAL_COMPLETE"
    return {
        "schema_version": "kgnote.orchestrator-state.v1",
        "run_id": f"orch-{uuid.uuid4().hex[:12]}",
        "active_goal": plan.get("goal_id"),
        "work_package": plan.get("active_milestone_id"),
        "state": mapped,
        "current_agent": None,
        "candidate_fingerprint": request.get("candidate_fingerprint"),
        "review_id": request.get("review_id") if review_state != "IMPLEMENTING" else None,
        "review_cycle": 0,
        "max_review_cycles": max_review_cycles,
        "agent_failures": 0,
        "max_agent_failures": 3,
        "empty_reviewer_results": 0,
        "blockers": [],
        "next_action": status.get("next_action"),
        "human_action_required": mapped in TERMINAL_STATES - {"GOAL_COMPLETE", "STOPPED"},
        "candidate_custody": {
            "status": "REVIEWER" if review_state == "UNDER_REVIEW" else (
                "SEALED" if review_state == "READY_FOR_REVIEW" else "NONE"
            ),
            "owner": "INDEPENDENT_REVIEWER" if review_state == "UNDER_REVIEW" else None,
            "review_id": request.get("review_id") if review_state in {"READY_FOR_REVIEW", "UNDER_REVIEW"} else None,
            "fingerprint": request.get("candidate_fingerprint") if review_state in {"READY_FOR_REVIEW", "UNDER_REVIEW"} else None,
        },
        "next_human_checkpoint": next_human_checkpoint(plan),
        "last_agent_run": None,
        "created_at": now(),
        "updated_at": now(),
    }


def update_state(repo: Path, state: dict[str, Any], new_state: str, next_action: str, **fields: Any) -> None:
    state["state"] = new_state
    state["next_action"] = next_action
    state["human_action_required"] = new_state in TERMINAL_STATES - {"GOAL_COMPLETE", "STOPPED"}
    state.update(fields)
    write_state(repo, state)
    append_event(repo, state, "STATE_TRANSITION", next_action=next_action)


def acquire_lock(repo: Path, state: dict[str, Any]) -> int:
    path = repo / LOCK_PATH
    for _attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError as exc:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {"detail": "unreadable lock"}
            pid = existing.get("pid")
            alive = False
            if isinstance(pid, int) and pid > 0:
                try:
                    os.kill(pid, 0)
                    alive = True
                except ProcessLookupError:
                    alive = False
                except PermissionError:
                    alive = True
            if alive or _attempt:
                raise ValueError(f"orchestrator_lock: another runner may be active: {existing}") from exc
            path.unlink(missing_ok=True)
            append_event(repo, state, "STALE_PROCESS_LOCK_RECOVERED", stale_lock=existing)
    else:  # pragma: no cover - loop either breaks or raises
        raise ValueError("orchestrator_lock: unable to acquire lock")
    os.write(descriptor, json.dumps({"pid": os.getpid(), "run_id": state["run_id"], "created_at": now()}).encode())
    os.fsync(descriptor)
    return descriptor


def release_lock(repo: Path, descriptor: int) -> None:
    os.close(descriptor)
    try:
        (repo / LOCK_PATH).unlink()
    except FileNotFoundError:
        pass


def role_prompt(role: str) -> str:
    if role == "reviewer":
        return (
            "YOU are the required independent reviewer. Perform the review now; do not defer to ChatGPT Work "
            "or ask a human to continue. Reconstruct authority solely from the repository, follow "
            ".ai/REVIEWER_BOOTSTRAP.md, inspect the exact sealed candidate, and write a complete reviewer-owned "
            ".ai/REVIEW_RESULT.md. Do not modify candidate files. The orchestrator already owns machine handoff "
            "and will submit and route your verdict."
        )
    return (
        "You are the KGnote implementer in an autonomous repair/work-package context. Reconstruct authority and "
        "state solely from AGENTS.md, PLAN.md, CODEX_STATUS.md, .ai/IMPLEMENTER_BOOTSTRAP.md, and current review "
        "artifacts. Implement only the active authorized work package. If findings exist, preserve their IDs, "
        "repair them, and mark each fixed item FIXED_PENDING_REVIEW with concrete evidence. Do not act as reviewer, "
        "select a product decision, promote human gates, or wait for the human to type continue. Finish when the "
        "candidate is ready for deterministic validation; the orchestrator will validate and hand it off."
    )


def codex_agent_command(repo: Path, role: str, output_path: Path) -> list[str]:
    """Build a CLI command compatible with Codex's global/subcommand split."""
    return [
        os.environ.get("KGNOTE_CODEX_BIN", "codex"),
        "-a",
        "never",
        "-s",
        "workspace-write",
        "-C",
        str(repo),
        "exec",
        "--ephemeral",
        "-o",
        str(output_path),
        role_prompt(role),
    ]


def run_codex_agent(repo: Path, role: str, state: dict[str, Any]) -> dict[str, Any]:
    output_dir = repo / "output/control-plane/orchestrator"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y%m%dT%H%M%S%z")
    output_path = output_dir / f"{state['run_id']}-{role}-{stamp}.txt"
    command = codex_agent_command(repo, role, output_path)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = completed.stdout
        exit_code = completed.returncode
    except OSError as exc:
        output = f"{type(exc).__name__}: {exc}"
        exit_code = 127
    transcript = output_dir / f"{state['run_id']}-{role}-{stamp}.json"
    record = {
        "role": role,
        "separate_ephemeral_context": True,
        "exit_code": exit_code,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output_tail": output[-4000:],
        "last_message_path": str(output_path.relative_to(repo)),
        "created_at": now(),
    }
    transcript.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record["transcript_path"] = str(transcript.relative_to(repo))
    return record


AgentRunner = Callable[[Path, str, dict[str, Any]], dict[str, Any]]


def quota_exhausted(run: dict[str, Any]) -> bool:
    text = str(run.get("output_tail", "")).lower()
    return any(marker in text for marker in QUOTA_MARKERS)


def handle_agent_failure(repo: Path, state: dict[str, Any], run: dict[str, Any]) -> None:
    state["agent_failures"] = int(state.get("agent_failures", 0)) + 1
    blocker = {
        "type": "agent_invocation_failure",
        "role": run.get("role"),
        "exit_code": run.get("exit_code"),
        "transcript_path": run.get("transcript_path"),
        "attempt": state["agent_failures"],
    }
    state["blockers"] = [blocker]
    if quota_exhausted(run):
        update_state(repo, state, "BUDGET_EXHAUSTED", "Restore model usage/quota, then run orchestrator resume.")
    elif state["agent_failures"] >= state.get("max_agent_failures", 3):
        update_state(
            repo,
            state,
            "AUTOMATION_BLOCKED",
            "Agent invocation failed repeatedly; inspect the recorded transcript and repair the automation runtime.",
        )
    else:
        write_state(repo, state)
        append_event(repo, state, "AGENT_RETRY_SCHEDULED", blocker=blocker)


def run_role(repo: Path, state: dict[str, Any], role: str, runner: AgentRunner) -> bool:
    state["current_agent"] = role.upper()
    write_state(repo, state)
    run = runner(repo, role, state)
    state["last_agent_run"] = run
    state["current_agent"] = None
    if run.get("exit_code") != 0:
        handle_agent_failure(repo, state, run)
        return False
    state["agent_failures"] = 0
    state["blockers"] = []
    write_state(repo, state)
    append_event(repo, state, "AGENT_COMPLETED", role=role, transcript_path=run.get("transcript_path"))
    return True


def current_milestone(plan: dict[str, Any]) -> dict[str, Any] | None:
    return next((item for item in plan.get("milestones", []) if item.get("status") == "active"), None)


def validate_and_request(repo: Path, state: dict[str, Any]) -> bool:
    update_state(repo, state, "VALIDATING", "Run deterministic verification for the current candidate.")
    control.sync_implementing_fingerprint(repo, "Implementation context completed; validation is pending.")
    evidence, exit_code = control.verify(repo)
    if exit_code != 0:
        state["blockers"] = [{
            "type": "validation_failure",
            "evidence": evidence.get("evidence_path"),
            "failed_gates": [gate.get("name") for gate in evidence.get("gates", []) if not gate.get("passed")],
        }]
        update_state(
            repo,
            state,
            "REPAIRING",
            "Validation failed; automatically return the evidence to a fresh implementer context.",
        )
        return False
    plan, _ = control.load_plan_status(repo)
    milestone = current_milestone(plan) or {}
    prepared = control.prepare_review_request(
        repo,
        evidence["evidence_path"],
        [f"active work package {milestone.get('id')}: {milestone.get('title', '')}"],
        list(milestone.get("acceptance", [])),
        [],
        [],
    )
    state["candidate_fingerprint"] = prepared["candidate_fingerprint"]
    state["review_id"] = prepared["review_id"]
    state["candidate_custody"] = {
        "status": "SEALED",
        "owner": None,
        "review_id": prepared["review_id"],
        "fingerprint": prepared["candidate_fingerprint"],
    }
    update_state(
        repo,
        state,
        "READY_FOR_AI_REVIEW",
        "Machine handoff: acquire reviewer custody and invoke an independent reviewer context.",
    )
    return True


def execute_reviewer(repo: Path, state: dict[str, Any], runner: AgentRunner) -> str:
    """Run or resume reviewer custody and return the resulting review state."""
    update_state(repo, state, "REVIEWING", "Invoke the independent reviewer against the exact sealed candidate.")
    if not run_role(repo, state, "reviewer", runner):
        return control.load_review_artifacts(repo)[0].get("status")
    if recover_stale_candidate(repo, state):
        return "IMPLEMENTING"
    request, result, _ = control.load_review_artifacts(repo)
    if request.get("status") == "UNDER_REVIEW" and result.get("artifact_state") == "SUBMITTED":
        state["empty_reviewer_results"] = 0
        control.archive_submitted_result(repo)
        request, result, _ = control.load_review_artifacts(repo)
    if request.get("status") == "UNDER_REVIEW" and result.get("artifact_state") == "EMPTY":
        state["empty_reviewer_results"] = int(state.get("empty_reviewer_results", 0)) + 1
        if state["empty_reviewer_results"] >= state["max_agent_failures"]:
            state["blockers"] = [{
                "type": "reviewer_produced_no_result",
                "review_id": request.get("review_id"),
                "attempts": state["empty_reviewer_results"],
            }]
            update_state(repo, state, "AUTOMATION_BLOCKED", "Reviewer repeatedly returned without a result.")
        else:
            write_state(repo, state)
            append_event(repo, state, "REVIEWER_RETRY_SCHEDULED", review_id=request.get("review_id"))
    return request.get("status")


def reset_review_bus_after_pass(repo: Path, next_action: str) -> None:
    request, _, _ = control.load_review_artifacts(repo)
    plan, status = control.load_plan_status(repo)
    active = current_milestone(plan)
    old_review_id = request["review_id"]
    old_fingerprint = request.get("candidate_fingerprint")
    request["review_id"] = control.next_review_id(old_review_id)
    request["status"] = "IMPLEMENTING"
    request["candidate_revision"] = None
    request["candidate_fingerprint"] = None
    request["requested_at"] = None
    if active is not None:
        request["milestone_id"] = active["id"]
        request["acceptance_criteria"] = list(active.get("acceptance", []))
    control.write_review_request(repo, request)
    control.replace_embedded_json(
        repo / ".ai/REVIEW_RESULT.md",
        control.REVIEW_RESULT_BEGIN,
        control.REVIEW_RESULT_END,
        control.empty_review_result(),
    )
    status["updated_at"] = now()
    status["implementation_state"] = "IMPLEMENTING"
    status["review"] = {
        "state": "IMPLEMENTING",
        "current_review_id": None,
        "candidate_revision": None,
        "candidate_fingerprint": None,
        "unresolved_findings": control.history_unresolved_finding_ids(repo),
        "human_decision_blockers": [],
    }
    status["verification"]["candidate_verified"] = False
    status["verification"]["control_plane_ready"] = False
    status["verification"]["release_verified"] = False
    status["verification"]["last_result"] = (
        f"Reviewer PASS for {old_review_id} was archived and consumed for deterministic progression; "
        "it is not rebound to the post-progression fingerprint."
    )
    status["next_action"] = next_action
    control.write_status(repo, status)
    control.append_history_event(repo, {
        "event_type": "PASS_CONSUMED_FOR_PROGRESSION",
        "review_id": old_review_id,
        "actor_role": "ORCHESTRATOR",
        "candidate_fingerprint": old_fingerprint,
        "snapshot_path": None,
        "snapshot_sha256": None,
        "created_at": now(),
    })


def render_plan_recovery(plan: dict[str, Any], state: str, next_action: str) -> str:
    return (
        "## Current recovery note\n\n"
        f"Autonomous orchestration state: `{state}`. "
        f"Active work package: `{plan.get('active_milestone_id')}`.\n"
        f"Next action: {next_action}\n"
        "Repository artifacts remain authoritative; PA-HUMAN-1, NS-HUMAN-SMOKE, and "
        "release_verified=false remain unchanged.\n"
    )


def write_plan(repo: Path, plan: dict[str, Any], state: str, next_action: str) -> None:
    path = repo / "PLAN.md"
    control.replace_embedded_json(path, control.PLAN_BEGIN, control.PLAN_END, plan)
    text = path.read_text(encoding="utf-8")
    heading = "## Current recovery note"
    prefix = text.split(heading, 1)[0].rstrip() if heading in text else text.rstrip()
    path.write_text(prefix + "\n\n" + render_plan_recovery(plan, state, next_action), encoding="utf-8")


def advance_after_pass(repo: Path, state: dict[str, Any]) -> None:
    plan, status = control.load_plan_status(repo)
    active = current_milestone(plan)
    if active is None:
        update_state(repo, state, "AUTOMATION_BLOCKED", "PASS exists but PLAN has no active work package.")
        return
    if active.get("id") == "AR-EXTERNAL-REVIEW":
        external_state = external_review_control.load_json(
            repo / external_review_control.STATE_PATH
        )
        external_result = external_state.get("external_review", {})
        if not (
            external_result.get("status") == "PASS"
            and not external_result.get("blocking_findings")
        ):
            request, _, _ = control.load_review_artifacts(repo)
            fingerprint = control.repository_fingerprint(repo)["value"]
            head = control.run_git(repo, "rev-parse", "HEAD").stdout.decode().strip()
            external_state.update({
                "phase": "READY_FOR_PUBLICATION",
                "review_round": int(external_state.get("review_round", 0)) + 1,
                "candidate_commit": head,
                "candidate_fingerprint": fingerprint,
                "internal_review": {
                    "status": "PASS",
                    "artifact": f".ai/REVIEW_RESULT.md#{request.get('review_id')}",
                },
                "publication": {
                    "status": "PENDING",
                    "repository": external_state.get("canonical_repository"),
                    "pull_request": external_state.get("pull_request"),
                    "remote_head": None,
                    "candidate_fingerprint": fingerprint,
                    "request_marker": None,
                    "artifact_url": None,
                },
                "external_review": {
                    "status": "PENDING",
                    "reviewed_commit": None,
                    "reviewed_fingerprint": None,
                    "artifact_url": None,
                    "blocking_findings": [],
                },
                "human_acceptance": {
                    "eligible": False,
                    "reason": "Exact external product review is pending.",
                },
                "release_verified": False,
            })
            external_path = repo / external_review_control.STATE_PATH
            temporary = external_path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(external_state, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, external_path)
            try:
                publication = publish_external_candidate.publish(repo)
            except publish_external_candidate.PublicationError as exc:
                state["blockers"] = [{"type": "external_publication_failed", "reason": str(exc)}]
                update_state(
                    repo,
                    state,
                    "AUTOMATION_BLOCKED",
                    "Exact candidate publication failed closed; preserve review evidence and repair the machine transition.",
                )
                return
            update_state(
                repo,
                state,
                "AWAITING_EXTERNAL_PRODUCT_REVIEW",
                f"Exact candidate published at {publication['artifact_url']}; await and consume the configured ChatGPT Work event result automatically.",
            )
            return
    if active.get("id") == "AR-PUBLISH":
        publication_blockers = (
            external_review_control.repository_publication_progression_blockers(repo)
        )
        if publication_blockers:
            update_state(
                repo,
                state,
                "REPAIRING",
                "AR-PUBLISH cannot complete before exact canonical remote read-back: "
                + "; ".join(publication_blockers),
            )
            return
    active["status"] = "complete"
    completed = {item.get("id") for item in plan.get("milestones", []) if item.get("status") == "complete"}
    ready = [
        item for item in plan.get("milestones", [])
        if item.get("status") == "pending" and set(item.get("dependencies", [])) <= completed
    ]
    next_package = ready[0] if ready else None
    if next_package and next_package.get("human_gate", "none") not in {"none", "complete"}:
        external_blockers = external_review_control.repository_human_gate_blockers(repo)
        if external_blockers:
            next_action = (
                "Do not enter the human checkpoint; continue the autonomous external "
                "product-review loop. " + "; ".join(external_blockers)
            )
            active["status"] = "active"
            update_state(repo, state, "REPAIRING", next_action)
            return
        plan["status"] = "human_checkpoint_required"
        plan["active_milestone_id"] = None
        next_action = f"Human checkpoint {next_package.get('human_gate')} is required before {next_package.get('id')}."
        write_plan(repo, plan, "HUMAN_CHECKPOINT_REQUIRED", next_action)
        reset_review_bus_after_pass(repo, next_action)
        _, status = control.load_plan_status(repo)
        status["goal_status"] = plan["status"]
        status["active_milestone_id"] = None
        status["milestone_status"] = "pending_human_checkpoint"
        status["working_state"]["fingerprint"] = control.repository_fingerprint(repo)["value"]
        control.write_status(repo, status)
        update_state(repo, state, "HUMAN_CHECKPOINT_REQUIRED", next_action, work_package=None)
        return
    if next_package:
        next_package["status"] = "active"
        plan["active_milestone_id"] = next_package["id"]
        next_action = f"Automatically begin authorized work package {next_package['id']}."
        write_plan(repo, plan, "IMPLEMENTING", next_action)
        reset_review_bus_after_pass(repo, next_action)
        _, status = control.load_plan_status(repo)
        status["active_milestone_id"] = next_package["id"]
        status["milestone_status"] = "active"
        status["working_state"]["fingerprint"] = control.repository_fingerprint(repo)["value"]
        control.write_status(repo, status)
        update_state(
            repo,
            state,
            "IMPLEMENTING",
            next_action,
            work_package=next_package["id"],
            candidate_fingerprint=None,
            review_id=None,
            candidate_custody={"status": "NONE", "owner": None, "review_id": None, "fingerprint": None},
        )
        return
    plan["status"] = "complete"
    plan["active_milestone_id"] = None
    next_action = "Goal complete; report the next preserved HUMAN checkpoint, not another machine action."
    write_plan(repo, plan, "GOAL_COMPLETE", next_action)
    reset_review_bus_after_pass(repo, next_action)
    _, status = control.load_plan_status(repo)
    status["goal_status"] = "complete"
    status["active_milestone_id"] = None
    status["milestone_status"] = "complete"
    status["working_state"]["fingerprint"] = control.repository_fingerprint(repo)["value"]
    status["verification"]["candidate_verified"] = False
    status["verification"]["release_verified"] = False
    control.write_status(repo, status)
    state["next_human_checkpoint"] = next_human_checkpoint(plan)
    update_state(
        repo,
        state,
        "GOAL_COMPLETE",
        next_action,
        work_package=None,
        candidate_fingerprint=None,
        review_id=None,
        candidate_custody={"status": "NONE", "owner": None, "review_id": None, "fingerprint": None},
    )


def recover_stale_candidate(repo: Path, state: dict[str, Any]) -> bool:
    request, _, _ = control.load_review_artifacts(repo)
    if request.get("status") not in {"READY_FOR_REVIEW", "UNDER_REVIEW"}:
        return False
    actual = control.repository_fingerprint(repo)["value"]
    if request.get("candidate_fingerprint") == actual:
        return False
    result = control.invalidate_stale_review(
        repo,
        f"sealed fingerprint {request.get('candidate_fingerprint')} changed to {actual}",
    )
    state["candidate_fingerprint"] = result["replacement_fingerprint"]
    state["review_id"] = None
    state["candidate_custody"] = {"status": "NONE", "owner": None, "review_id": None, "fingerprint": None}
    update_state(
        repo,
        state,
        "REPAIRING",
        "Stale review was rejected; inspect the drift and produce a newly validated candidate automatically.",
    )
    return True


def classify_preflight_failure(errors: list[str]) -> str:
    if any("authority_drift" in error or "consent_gate" in error for error in errors):
        return "AUTHORITY_CONFLICT"
    return "AUTOMATION_BLOCKED"


def orchestrate_step(repo: Path, state: dict[str, Any], runner: AgentRunner = run_codex_agent) -> None:
    if recover_stale_candidate(repo, state):
        return
    # A reviewer result is durable before the orchestrator-owned STATUS/history
    # projection changes.  Consume that expected handoff window first so crash
    # recovery cannot misclassify it as state drift.
    request, result, _ = control.load_review_artifacts(repo)
    if request.get("status") == "UNDER_REVIEW" and result.get("artifact_state") == "SUBMITTED":
        pending_errors, _ = control.validate_pending_review_result(repo)
        if pending_errors:
            state["blockers"] = [{"type": "invalid_pending_review_result", "errors": pending_errors}]
            update_state(repo, state, "AUTOMATION_BLOCKED", "A durable pending reviewer result failed exact validation.")
            return
        control.archive_submitted_result(repo)
        state["empty_reviewer_results"] = 0
    preflight = control.preflight(repo)
    if preflight.get("status") != "pass":
        terminal = classify_preflight_failure(preflight.get("errors", []))
        state["blockers"] = [{"type": "preflight_failure", "errors": preflight.get("errors", [])}]
        update_state(repo, state, terminal, "Resolve the structured preflight blockers, then run orchestrator resume.")
        return
    request, result, _ = control.load_review_artifacts(repo)
    review_state = request.get("status")

    if review_state == "IMPLEMENTING":
        phase = "REPAIRING" if result.get("verdict") == "CHANGES_REQUIRED" else "IMPLEMENTING"
        update_state(repo, state, phase, "Invoke a fresh implementer context for the authorized work package.")
        if not run_role(repo, state, "implementer", runner):
            return
        validate_and_request(repo, state)
        return

    if review_state == "READY_FOR_REVIEW":
        if state["review_cycle"] >= state["max_review_cycles"]:
            state["blockers"] = [{
                "type": "repair_budget_exhausted",
                "review_cycle": state["review_cycle"],
                "max_review_cycles": state["max_review_cycles"],
                "unresolved_findings": control.history_unresolved_finding_ids(repo),
            }]
            update_state(
                repo,
                state,
                "AUTOMATION_BLOCKED",
                "Five review/repair cycles were exhausted; inspect structured findings and choose a recovery action.",
            )
            return
        state["review_cycle"] += 1
        reviewer_identity = f"codex-independent-reviewer:{state['run_id']}:{state['review_cycle']}"
        control.accept_review_custody(repo, reviewer_identity)
        state["candidate_custody"] = {
            "status": "REVIEWER",
            "owner": reviewer_identity,
            "review_id": request["review_id"],
            "fingerprint": request["candidate_fingerprint"],
        }
        review_state = execute_reviewer(repo, state, runner)
        if state["state"] in TERMINAL_STATES:
            return

    elif review_state == "UNDER_REVIEW" and result.get("artifact_state") == "EMPTY":
        # Crash/context restart recovery: custody and fingerprint remain durable,
        # so a new independent reviewer context resumes the same sealed review.
        review_state = execute_reviewer(repo, state, runner)
        if state["state"] in TERMINAL_STATES:
            return

    if review_state == "UNDER_REVIEW" and result.get("artifact_state") == "SUBMITTED":
        control.archive_submitted_result(repo)
        request, result, _ = control.load_review_artifacts(repo)
        review_state = request.get("status")

    if review_state == "CHANGES_REQUIRED":
        if state["review_cycle"] >= state["max_review_cycles"]:
            state["blockers"] = [{
                "type": "repair_budget_exhausted",
                "review_cycle": state["review_cycle"],
                "max_review_cycles": state["max_review_cycles"],
                "unresolved_findings": control.history_unresolved_finding_ids(repo),
            }]
            update_state(repo, state, "AUTOMATION_BLOCKED", "Review/repair budget exhausted with unresolved findings.")
            return
        control.resume_implementation(repo)
        update_state(repo, state, "REPAIRING", "Automatically return reviewer findings to a fresh implementer context.")
        return

    if review_state == "PRODUCT_DECISION_REQUIRED":
        update_state(
            repo,
            state,
            "PRODUCT_DECISION_REQUIRED",
            "Human must select and durably record a product/architecture decision before resume.",
        )
        return

    if review_state == "PASS":
        advance_after_pass(repo, state)
        return

    if review_state == "UNDER_REVIEW":
        # A reviewer that returned no result is retried by the next loop step;
        # repeated empty returns become AUTOMATION_BLOCKED in execute_reviewer.
        update_state(repo, state, "REVIEWING", "Resume reviewer custody in a fresh independent context.")
        return

    update_state(repo, state, "AUTOMATION_BLOCKED", f"Unsupported review state {review_state!r}.")


def run_loop(repo: Path, state: dict[str, Any], runner: AgentRunner, max_steps: int | None) -> dict[str, Any]:
    descriptor = acquire_lock(repo, state)
    try:
        steps = 0
        while state["state"] not in TERMINAL_STATES | MACHINE_HANDOFF_STATES:
            if (repo / STOP_PATH).exists():
                (repo / STOP_PATH).unlink()
                update_state(repo, state, "STOPPED", "Operator requested a safe stop; run resume to continue.")
                break
            orchestrate_step(repo, state, runner)
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
        return state
    finally:
        release_lock(repo, descriptor)


def resume_after_product_decision(repo: Path, state: dict[str, Any]) -> bool:
    request, result, decisions = control.load_review_artifacts(repo)
    if request.get("status") != "PRODUCT_DECISION_REQUIRED":
        return True
    required_ids = result.get("human_decisions_required", [])
    entries = {
        item.get("decision_id"): item
        for item in decisions.get("decisions", [])
        if isinstance(item, dict)
    }
    errors = control.validate_decisions(decisions, repo, request)
    errors.extend(control.validate_review_result(request, result, decisions))
    missing = sorted(set(required_ids) - set(entries))
    pending = sorted(
        decision_id
        for decision_id in required_ids
        if decision_id in entries and entries[decision_id].get("status") != "DECIDED"
    )
    if not required_ids:
        errors.append("orchestrator_resume: PRODUCT_DECISION_REQUIRED has no exact required decision IDs")
    if missing:
        errors.append(f"orchestrator_resume: missing required human decisions {missing}")
    if pending:
        errors.append(f"orchestrator_resume: required human decisions remain undecided {pending}")
    if not errors:
        errors.extend(control.validate_human_decision_delta(repo, request, decisions, set(required_ids)))
    if errors:
        state["blockers"] = [{
            "type": "human_decision_evidence_invalid",
            "required_decision_ids": list(required_ids),
            "errors": errors,
        }]
        update_state(
            repo,
            state,
            "PRODUCT_DECISION_REQUIRED",
            "Required human decisions are missing, pending, or invalid; record valid external authority evidence and resume.",
        )
        return False
    adopted_fingerprint = control.resume_implementation(repo)
    if not adopted_fingerprint:
        raise ValueError("orchestrator_resume: human decision resume did not adopt the repository fingerprint")
    state["blockers"] = []
    update_state(
        repo,
        state,
        "IMPLEMENTING",
        "Human decisions were validated; invoke a fresh implementer context for the authorized resolution.",
        review_id=None,
        candidate_fingerprint=adopted_fingerprint["value"],
        candidate_custody={"status": "NONE", "owner": None, "review_id": None, "fingerprint": None},
    )
    return True


def start(repo: Path, *, resume: bool, max_review_cycles: int, max_steps: int | None, runner: AgentRunner) -> dict[str, Any]:
    existing = read_state(repo)
    if resume:
        if existing is None:
            raise ValueError("orchestrator_resume: no durable state exists; use start")
        state = existing
        if state["state"] == "PRODUCT_DECISION_REQUIRED":
            if not resume_after_product_decision(repo, state):
                return state
        elif state["state"] in {"HUMAN_CHECKPOINT_REQUIRED", "AUTHORITY_CONFLICT"}:
            # Re-derive after the human or authority artifact was durably updated.
            state = derive_state(repo, max_review_cycles=state.get("max_review_cycles", max_review_cycles))
        elif state["state"] in {"STOPPED", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED"}:
            state["state"] = derive_state(repo, max_review_cycles=state.get("max_review_cycles", max_review_cycles))["state"]
            state["blockers"] = []
            state["human_action_required"] = False
            state["run_id"] = f"orch-{uuid.uuid4().hex[:12]}"
            write_state(repo, state)
    else:
        if existing and existing.get("state") not in TERMINAL_STATES:
            raise ValueError("orchestrator_start: active durable state exists; use resume or stop")
        state = derive_state(repo, max_review_cycles=max_review_cycles)
        write_state(repo, state)
        append_event(repo, state, "ORCHESTRATOR_STARTED")
    return run_loop(repo, state, runner, max_steps)


def request_stop(repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if state is None:
        return {"status": "not_running", "human_action_required": False}
    (repo / STOP_PATH).write_text(now() + "\n", encoding="utf-8")
    return {"status": "stop_requested", "run_id": state.get("run_id"), "human_action_required": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "resume"):
        command = sub.add_parser(name)
        command.add_argument("--max-review-cycles", type=int, default=5)
        command.add_argument("--max-steps", type=int)
    sub.add_parser("status")
    sub.add_parser("stop")
    args = parser.parse_args()
    repo = args.repo.resolve()
    try:
        if args.command in {"start", "resume"}:
            if args.max_review_cycles < 1:
                raise ValueError("max-review-cycles must be positive")
            result = start(
                repo,
                resume=args.command == "resume",
                max_review_cycles=args.max_review_cycles,
                max_steps=args.max_steps,
                runner=run_codex_agent,
            )
        elif args.command == "status":
            result = read_state(repo) or derive_state(repo)
        else:
            result = request_stop(repo)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
