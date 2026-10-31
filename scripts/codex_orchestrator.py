#!/usr/bin/env python3
"""Durable autonomous implementer/reviewer loop for the KGnote control plane.

Repository artifacts remain authoritative.  This process only coordinates the
existing fingerprint-bound review helpers and separate ephemeral Codex contexts;
it does not decide product questions or promote human/release gates.
"""

from __future__ import annotations

import argparse
import hashlib
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
import external_review_handoff
import publish_external_candidate
from issue47_engineering_wakeup import continuation_binding


STATE_PATH = ".ai/ORCHESTRATOR_STATE.json"
ENVELOPE_PATH = ".ai/work-package-envelope.json"
STOP_PATH = ".ai/ORCHESTRATOR_STOP"
LOCK_PATH = ".ai/ORCHESTRATOR.lock"
HISTORY_PATH = ".ai/ORCHESTRATION_HISTORY/events.jsonl"
TERMINAL_STATES = {
    "HUMAN_CHECKPOINT_REQUIRED",  # historical state accepted for migration only
    "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
    "PRODUCT_DECISION_REQUIRED",
    "AUTHORITY_CONFLICT",
    "AUTOMATION_BLOCKED",
    "BUDGET_EXHAUSTED",
    "GOAL_COMPLETE",
    "STOPPED",
}
EXPLICIT_RESUME_STATES = {"STOPPED", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED"}
WORK_TIMEZONE = ZoneInfo("Asia/Taipei")
WORKDAY_START_MINUTE = 9 * 60
WORKDAY_END_MINUTE = 18 * 60
LEGACY_CANARY_END_MINUTE = 18 * 60 + 30
LEGACY_CANARY_GOAL_IDS = frozenset({"GOAL-KGNOTE-D2-T01-SOURCE-LIBRARY-V1"})
ISSUE47_ENGINEERING_GOAL_ID = (
    "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION"
)
ISSUE47_WEEKEND_SPEC_VERSION = "2026-10-31.4-engineering-continuation-simplification"
ISSUE47_WEEKEND_SPEC_SHA256 = (
    "0507d2dbc5c9780afbe3e67a3c8ca66f8fb1b93eff9507c86299baac0141ad5d"
)
ISSUE47_WEEKEND_OWNER_COMMENT_ID = 6538300483
ISSUE47_WEEKEND_OWNER_BODY_SHA256 = (
    "96eb37ed4b4e76aa6c7eab4767fec2c53c12b3d96843b1d77c6a19217844d1a2"
)
ISSUE47_WEEKEND_OWNER_COMMAND_SHA256 = (
    "53cb7c25ad8216dca4d8daa408af81df1902298d73c91f0fd8c7fefbf53cf7b4"
)
ISSUE47_WEEKEND_SCOPE = "ISSUE47_INFRA_ENGINEERING_ONLY"
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
    return datetime.now(WORK_TIMEZONE).isoformat(timespec="seconds")


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_exact_issue47_weekend_spec(repo: Path | None) -> dict[str, Any] | None:
    """Return the exact approved successor spec, or fail closed.

    Weekend authority is not keyed only by a Goal name.  It requires the
    repository's PLAN and STATUS to point at the exact immutable spec and the
    exact Owner receipt.  Any stale checkout, missing receipt, path escape, or
    byte drift therefore keeps the ordinary weekday-only guard in force.
    """
    if repo is None:
        return None
    try:
        root = repo.resolve()
        plan, status = control.load_plan_status(root)
        if plan.get("goal_id") != ISSUE47_ENGINEERING_GOAL_ID:
            return None
        if status.get("goal_id") != ISSUE47_ENGINEERING_GOAL_ID:
            return None
        if plan.get("product_goal_authorized") is not False:
            return None
        if status.get("product_goal_authorized") is not False:
            return None

        plan_goal = plan.get("goal_spec", {})
        status_goal = status.get("goal_spec", {})
        expected = {
            "version": ISSUE47_WEEKEND_SPEC_VERSION,
            "canonical_sha256": ISSUE47_WEEKEND_SPEC_SHA256,
            "authority_status": "EXACT_GITHUB_OWNER_APPROVED",
        }
        if any(plan_goal.get(key) != value for key, value in expected.items()):
            return None
        if any(status_goal.get(key) != value for key, value in expected.items()):
            return None
        if plan_goal.get("path") != status_goal.get("path"):
            return None

        receipt = plan_goal.get("authority_receipt", {})
        authority = status_goal.get("authority_comment", {})
        if (
            receipt.get("comment_id") != ISSUE47_WEEKEND_OWNER_COMMENT_ID
            or receipt.get("body_sha256") != ISSUE47_WEEKEND_OWNER_BODY_SHA256
            or receipt.get("command_canonical_sha256")
            != ISSUE47_WEEKEND_OWNER_COMMAND_SHA256
            or receipt.get("validation")
            != "EXACT_SEMANTIC_MATCH_AND_REMOTE_SPEC_BLOB_READ_BACK"
            or authority.get("comment_id") != ISSUE47_WEEKEND_OWNER_COMMENT_ID
            or authority.get("body_sha256") != ISSUE47_WEEKEND_OWNER_BODY_SHA256
            or authority.get("command_canonical_sha256")
            != ISSUE47_WEEKEND_OWNER_COMMAND_SHA256
            or authority.get("authority_marker_present") is not True
            or authority.get("command_exact_semantic_match") is not True
        ):
            return None

        relative_path = Path(str(plan_goal.get("path", "")))
        spec_path = (root / relative_path).resolve()
        spec_path.relative_to(root)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            return None
        if _canonical_sha256(spec) != ISSUE47_WEEKEND_SPEC_SHA256:
            return None
        if (
            spec.get("goal_id") != ISSUE47_ENGINEERING_GOAL_ID
            or spec.get("goal_version") != ISSUE47_WEEKEND_SPEC_VERSION
            or spec.get("product_goal_authorized") is not False
        ):
            return None
        return spec
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _within_exact_issue47_work_hours(local: datetime, repo: Path | None) -> bool:
    spec = _load_exact_issue47_weekend_spec(repo)
    if spec is None:
        return False
    try:
        work_period = spec["work_period"]
        if work_period["timezone"] != "Asia/Taipei":
            return False
        period_start = datetime.fromisoformat(work_period["start"]).astimezone(
            WORK_TIMEZONE
        )
        period_end = datetime.fromisoformat(work_period["end"]).astimezone(
            WORK_TIMEZONE
        )
        if not period_start <= local < period_end:
            return False

        minute = local.hour * 60 + local.minute
        daily_start = int(work_period["daily_start"][:2]) * 60 + int(
            work_period["daily_start"][3:]
        )
        daily_end = int(work_period["daily_end"][:2]) * 60 + int(
            work_period["daily_end"][3:]
        )
        if local.weekday() in work_period["weekdays"]:
            return daily_start <= minute < daily_end

        local_date = local.date().isoformat()
        for window in work_period.get("exception_work_windows", []):
            if (
                window.get("date") != local_date
                or window.get("scope") != ISSUE47_WEEKEND_SCOPE
            ):
                continue
            start = int(window["start"][:2]) * 60 + int(window["start"][3:])
            end = int(window["end"][:2]) * 60 + int(window["end"][3:])
            return start <= minute < end
    except (KeyError, TypeError, ValueError):
        return False
    return False


def within_authorized_work_hours(
    moment: datetime | None = None,
    *,
    goal_id: str | None = None,
    repo: Path | None = None,
) -> bool:
    """Return whether new autonomous work may start in Asia/Taipei.

    O2 and all unrecognized goals use the current weekday-only 09:00-18:00
    boundary.  The Legacy Issue #8 production canary keeps its separately
    authorized 09:00-18:30 legacy window; the goal identity is repository
    state, not an environment override.
    """
    if moment is None:
        local = datetime.now(WORK_TIMEZONE)
    elif moment.tzinfo is None:
        local = moment.replace(tzinfo=WORK_TIMEZONE)
    else:
        local = moment.astimezone(WORK_TIMEZONE)
    if goal_id == ISSUE47_ENGINEERING_GOAL_ID:
        return _within_exact_issue47_work_hours(local, repo)
    if goal_id in LEGACY_CANARY_GOAL_IDS:
        end_minute = LEGACY_CANARY_END_MINUTE
    else:
        if local.weekday() >= 5:
            return False
        end_minute = WORKDAY_END_MINUTE
    minute = local.hour * 60 + local.minute
    return WORKDAY_START_MINUTE <= minute < end_minute


def terminal_resume_authorized(state: dict[str, Any], requested_state: str | None) -> bool:
    """Require an exact operator request and preserve exhausted review budgets."""
    current = state.get("state")
    if current not in EXPLICIT_RESUME_STATES or requested_state != current:
        return False
    if current != "AUTOMATION_BLOCKED":
        return True
    for blocker in state.get("blockers", []):
        if blocker.get("type") != "repair_budget_exhausted":
            continue
        review_cycle = int(state.get("review_cycle", 0))
        if "supplemental_review_limit" in state or "base_review_cycles" in state:
            effective_limit = int(
                state.get("base_review_cycles", state.get("max_review_cycles", 5))
            ) + int(state.get("supplemental_review_limit", 0))
        else:
            effective_limit = int(
                blocker.get("effective_review_limit", state.get("max_review_cycles", 5))
            )
        if review_cycle >= effective_limit:
            return False
    return True


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


def _repo_relative_runtime_path(repo: Path, value: Path, *, field: str) -> tuple[Path, str]:
    """Bind mutable review runtime state to an explicit path inside the repository.

    Goal-scoped external reviews may not reuse the historical singleton files.
    Persisting repository-relative paths makes a later Runner wakeup independent
    of the invoking shell while preventing an order from redirecting the
    orchestrator to unrelated host files.
    """
    candidate = value if value.is_absolute() else repo / value
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must remain inside the repository") from exc
    if not resolved.is_file():
        raise ValueError(f"{field} does not exist: {relative}")
    return resolved, relative.as_posix()


def bind_external_review_runtime(
    repo: Path,
    state: dict[str, Any],
    *,
    config_path: Path | None,
    external_state_path: Path | None,
    persist: bool = True,
) -> tuple[Path, Path]:
    """Resolve and durably bind one Goal's external-review config and state.

    Both paths are supplied together on the first wakeup. Subsequent wakeups
    use the persisted binding and reject a silent switch to another Goal or
    review program.
    """
    if (config_path is None) != (external_state_path is None):
        raise ValueError("external review config and state paths must be supplied together")

    existing = state.get("external_review_binding")
    if existing is not None and not isinstance(existing, dict):
        raise ValueError("external_review_binding must be an object")

    if config_path is None:
        if isinstance(existing, dict):
            config_path = Path(str(existing.get("config_path", "")))
            external_state_path = Path(str(existing.get("state_path", "")))
        else:
            # Historical repositories use the singleton paths. Preserve that
            # compatibility without requiring those files during unrelated
            # implementation/review phases; the handoff validates them when
            # the state actually reaches the external-review boundary.
            return (
                repo / external_review_control.CONFIG_PATH,
                repo / external_review_control.STATE_PATH,
            )

    assert external_state_path is not None
    resolved_config, relative_config = _repo_relative_runtime_path(
        repo, config_path, field="external review config path"
    )
    resolved_state, relative_state = _repo_relative_runtime_path(
        repo, external_state_path, field="external review state path"
    )
    config = external_review_control.load_json(resolved_config)
    review_state = external_review_control.load_json(resolved_state)
    authority_errors = external_review_control.repository_authority_errors(config)
    if authority_errors:
        raise ValueError("; ".join(authority_errors))
    if config.get("program_id") != review_state.get("program_id"):
        raise ValueError("external review program identity differs between config and state")
    if review_state.get("goal_id") != state.get("active_goal"):
        raise ValueError("external review goal identity differs from the active orchestrator goal")

    binding = {
        "program_id": config.get("program_id"),
        "goal_id": review_state.get("goal_id"),
        "config_path": relative_config,
        "state_path": relative_state,
    }
    if isinstance(existing, dict) and existing != binding:
        raise ValueError("external review runtime is already bound to a different identity or path")
    if existing != binding and persist:
        state["external_review_binding"] = binding
        write_state(repo, state)
    return resolved_config, resolved_state


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
            "YOU are the authorized Ubuntu Claude independent reviewer. Perform the review now; do not ask "
            "ChatGPT Work or a human to continue. Reconstruct authority solely from the repository, follow "
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


def ubuntu_claude_routine_review_active(repo: Path) -> bool:
    """Return true only for repositories carrying the approved role cutover."""
    path = repo / "docs/control-plane/CLAUDE_REVIEWER_ROLE_DECISION_20261020.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "Status: `APPROVED`" in text and "Ubuntu Claude is the sole routine independent AI product reviewer" in text


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


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label}: must contain an object")
    return value


def _repo_record_exists(repo: Path, record: object) -> bool:
    if not isinstance(record, str) or not record:
        return False
    if record.startswith(("https://", "http://")):
        return True
    path = Path(record)
    return not path.is_absolute() and ".." not in path.parts and (repo / path).is_file()


def approve_reconciled_envelope(repo: Path, state: dict[str, Any]) -> tuple[bool, list[str]]:
    """Atomically authorize one reconciled package before verification/sealing.

    The reconciliation receipt binds the pre-transition repository fingerprint.
    The APPROVED envelope is then part of the fingerprint that verification and
    the review request seal.  No historical review identity is reused.
    """
    path = repo / ENVELOPE_PATH
    errors: list[str] = []
    try:
        envelope = _load_json_object(path, "work_package_envelope")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, [f"work_package_envelope: {exc}"]

    if envelope.get("schema_version") != "kgnote.work-package-envelope.v1":
        errors.append("work_package_envelope: unsupported schema_version")
    if envelope.get("goal_id") != state.get("active_goal"):
        errors.append("work_package_envelope: goal identity mismatch")
    if envelope.get("work_package_id") != state.get("work_package"):
        errors.append("work_package_envelope: work package identity mismatch")
    if not _repo_record_exists(repo, envelope.get("authority_record")):
        errors.append("work_package_envelope: authority record is missing or unavailable")

    try:
        plan, _ = control.load_plan_status(repo)
        milestone = current_milestone(plan)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        milestone = None
        errors.append(f"work_package_envelope: PLAN/STATUS unavailable: {exc}")
    if not milestone or milestone.get("id") != state.get("work_package"):
        errors.append("work_package_envelope: active PLAN milestone mismatch")
    else:
        scope = envelope.get("scope")
        owned = milestone.get("owned_paths")
        if not isinstance(scope, list) or not scope or any(not isinstance(item, str) for item in scope):
            errors.append("work_package_envelope: scope must be a non-empty path list")
        elif not isinstance(owned, list) or sorted(set(scope)) != sorted(set(owned)):
            errors.append("work_package_envelope: scope does not match active milestone owned_paths")

    budgets = envelope.get("budgets")
    if not isinstance(budgets, dict):
        errors.append("work_package_envelope: budgets must be an object")
    else:
        for name in ("local_repairs", "internal_reviews", "external_reviews"):
            item = budgets.get(name)
            if not isinstance(item, dict):
                errors.append(f"work_package_envelope: {name} budget is invalid")
                continue
            authorized, used = item.get("authorized"), item.get("used")
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (authorized, used)):
                errors.append(f"work_package_envelope: {name} budget is invalid")
            elif used > authorized:
                errors.append(f"work_package_envelope: {name} exceeds authorization")
            elif name in {"internal_reviews", "external_reviews"} and used >= authorized:
                errors.append(f"work_package_envelope: {name} has no remaining downstream review budget")

    lock_path = repo / LOCK_PATH
    try:
        lock = _load_json_object(lock_path, "orchestrator_lock")
        if lock.get("pid") != os.getpid() or lock.get("run_id") != state.get("run_id"):
            errors.append("work_package_envelope: writer lock belongs to another runner")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"work_package_envelope: current writer lock is not proven: {exc}")

    status = envelope.get("status")
    if status == "APPROVED":
        approval = envelope.get("approval")
        if not isinstance(approval, dict) or approval.get("source_status") != "RECONCILING":
            errors.append("work_package_envelope: APPROVED transition receipt is missing")
        return not errors, errors
    if status != "RECONCILING":
        errors.append("work_package_envelope: status must be RECONCILING before approval")

    reconciliation = envelope.get("reconciliation")
    if not isinstance(reconciliation, dict) or reconciliation.get("status") != "COMPLETE":
        errors.append("work_package_envelope: reconciliation is incomplete")
        receipt = None
    else:
        receipt_name = reconciliation.get("receipt")
        try:
            if not isinstance(receipt_name, str) or not receipt_name:
                raise ValueError("receipt path is missing")
            receipt_path = Path(receipt_name)
            if receipt_path.is_absolute() or ".." in receipt_path.parts:
                raise ValueError("receipt path must be repository-relative")
            receipt = _load_json_object(repo / receipt_path, "reconciliation_receipt")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            receipt = None
            errors.append(f"work_package_envelope: reconciliation receipt unavailable: {exc}")

    fingerprint = control.repository_fingerprint(repo)
    if receipt is not None:
        expected = {
            "schema_version": "kgnote.reconciliation-receipt.v1",
            "status": "COMPLETE",
            "goal_id": state.get("active_goal"),
            "work_package_id": state.get("work_package"),
            "authority_record": envelope.get("authority_record"),
            "candidate_fingerprint": fingerprint["value"],
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                errors.append(f"work_package_envelope: reconciliation receipt {key} mismatch")
    if state.get("candidate_fingerprint") not in {None, fingerprint["value"]}:
        errors.append("work_package_envelope: orchestrator candidate fingerprint drift")
    unexpected = control.unexpected_dirty_paths(control.changed_paths(repo), plan) if milestone else []
    if unexpected:
        errors.append(f"work_package_envelope: unauthorized dirty paths {unexpected}")
    if errors:
        return False, errors

    envelope["status"] = "APPROVED"
    envelope["approval"] = {
        "source_status": "RECONCILING",
        "approved_at": now(),
        "pre_approval_fingerprint": fingerprint["value"],
        "receipt": reconciliation["receipt"],
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    append_event(
        repo,
        state,
        "WORK_PACKAGE_ENVELOPE_APPROVED",
        pre_approval_fingerprint=fingerprint["value"],
        reconciliation_receipt=reconciliation["receipt"],
    )
    return True, []


def validate_and_request(repo: Path, state: dict[str, Any]) -> bool:
    approved, approval_errors = approve_reconciled_envelope(repo, state)
    if not approved:
        state["blockers"] = [{"type": "envelope_reconciliation_rejected", "errors": approval_errors}]
        update_state(
            repo,
            state,
            "AUTOMATION_BLOCKED",
            "Resolve the exact reconciliation/envelope blockers; verification and sealing were not started.",
        )
        return False
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
        binding = state.get("external_review_binding")
        if isinstance(binding, dict):
            review_config_path, external_path = bind_external_review_runtime(
                repo, state, config_path=None, external_state_path=None
            )
        else:
            review_config_path = repo / external_review_control.CONFIG_PATH
            external_path = repo / external_review_control.STATE_PATH
        external_state = external_review_control.load_json(external_path)
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
            temporary = external_path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(external_state, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, external_path)
            try:
                publication = (
                    publish_external_candidate.publish(
                        repo,
                        config_path=review_config_path,
                        state_path=external_path,
                    )
                    if isinstance(binding, dict)
                    else publish_external_candidate.publish(repo)
                )
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
                f"Exact candidate published at {publication['artifact_url']}; Runner must dispatch Ubuntu Claude, relay the exact result to GitHub, and require canonical Consumer read-back.",
                review_id=request.get("review_id"),
                candidate_fingerprint=fingerprint,
                candidate_custody={"status": "NONE", "owner": None, "review_id": None, "fingerprint": None},
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
    completed = {
        item.get("id")
        for item in plan.get("milestones", [])
        if item.get("status") in {"complete", "superseded"}
    }
    ready = [
        item for item in plan.get("milestones", [])
        if item.get("status") == "pending" and set(item.get("dependencies", [])) <= completed
    ]
    next_package = ready[0] if ready else None
    if next_package and next_package.get("human_gate", "none") not in {
        "none",
        "complete",
        external_review_control.FINAL_HUMAN_GATE_ID,
    }:
        next_package["status"] = "superseded"
        next_package["superseded_by"] = external_review_control.FINAL_HUMAN_GATE_ID
        completed.add(next_package.get("id"))
        ready = [
            item
            for item in plan.get("milestones", [])
            if item.get("status") == "pending"
            and set(item.get("dependencies", [])) <= completed
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
        plan["status"] = "final_human_acceptance_required"
        plan["active_milestone_id"] = None
        next_action = f"Human checkpoint {next_package.get('human_gate')} is required before {next_package.get('id')}."
        write_plan(repo, plan, "FINAL_HUMAN_ACCEPTANCE_REQUIRED", next_action)
        reset_review_bus_after_pass(repo, next_action)
        _, status = control.load_plan_status(repo)
        status["goal_status"] = plan["status"]
        status["active_milestone_id"] = None
        status["milestone_status"] = "pending_human_checkpoint"
        status["working_state"]["fingerprint"] = control.repository_fingerprint(repo)["value"]
        control.write_status(repo, status)
        update_state(repo, state, "FINAL_HUMAN_ACCEPTANCE_REQUIRED", next_action, work_package=None)
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
        if ubuntu_claude_routine_review_active(repo):
            state["candidate_custody"] = {
                "status": "SEALED", "owner": "PRODUCTION_RUNNER",
                "review_id": request["review_id"], "fingerprint": request["candidate_fingerprint"],
            }
            update_state(
                repo, state, "AWAITING_EXTERNAL_PRODUCT_REVIEW",
                "Production Runner must dispatch Ubuntu Claude for the sealed candidate, relay the exact result to GitHub, and require canonical Consumer read-back.",
                review_id=request["review_id"],
                candidate_fingerprint=request["candidate_fingerprint"],
            )
            return
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
        if ubuntu_claude_routine_review_active(repo):
            state["candidate_custody"] = {
                "status": "SEALED", "owner": "PRODUCTION_RUNNER",
                "review_id": request["review_id"], "fingerprint": request["candidate_fingerprint"],
            }
            update_state(
                repo, state, "AWAITING_EXTERNAL_PRODUCT_REVIEW",
                "Legacy local reviewer custody is not resumed; Production Runner must dispatch Ubuntu Claude and consume canonical GitHub evidence.",
                review_id=request["review_id"],
                candidate_fingerprint=request["candidate_fingerprint"],
            )
            return
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
        update_state(
            repo,
            state,
            "REPAIRING",
            "Automatically return reviewer findings to a fresh implementer context.",
            review_id=None,
            candidate_custody={"status": "NONE", "owner": None, "review_id": None, "fingerprint": None},
        )
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
            if not within_authorized_work_hours(
                goal_id=state.get("active_goal"), repo=repo
            ):
                break
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


def start(
    repo: Path,
    *,
    resume: bool,
    max_review_cycles: int,
    max_steps: int | None,
    runner: AgentRunner,
    resume_terminal_state: str | None = None,
    external_review_config_path: Path | None = None,
    external_review_state_path: Path | None = None,
) -> dict[str, Any]:
    existing = read_state(repo)
    if resume:
        if existing is None:
            raise ValueError("orchestrator_resume: no durable state exists; use start")
        state = existing
        work_hours_allowed = within_authorized_work_hours(
            goal_id=state.get("active_goal"), repo=repo
        )
        review_config_path, review_state_path = bind_external_review_runtime(
            repo,
            state,
            config_path=external_review_config_path,
            external_state_path=external_review_state_path,
            persist=work_hours_allowed,
        )
        if not work_hours_allowed:
            return state
        if state["state"] == "AWAITING_EXTERNAL_PRODUCT_REVIEW":
            decision = external_review_handoff.process(
                repo,
                config_path=review_config_path,
                state_path=review_state_path,
            )
            if not decision.get("accepted"):
                state["next_action"] = "External review not yet accepted; a future event or bounded resume may retry."
                write_state(repo, state)
                return state
            if decision.get("verdict") == "PASS":
                advance_after_pass(repo, state)
                return state
            if decision.get("verdict") == "PRODUCT_DECISION_REQUIRED":
                update_state(repo, state, "PRODUCT_DECISION_REQUIRED", "External product reviewer requires a durable human decision.")
                return state
            update_state(repo, state, "REPAIRING", "External CHANGES_REQUIRED was accepted; route exact findings to repair.")
            return state
        if state["state"] == "PRODUCT_DECISION_REQUIRED":
            if not resume_after_product_decision(repo, state):
                return state
        elif state["state"] in {
            "HUMAN_CHECKPOINT_REQUIRED",  # superseded input migration
            "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
            "AUTHORITY_CONFLICT",
        }:
            # Re-derive after the human or authority artifact was durably updated.
            state = derive_state(repo, max_review_cycles=state.get("max_review_cycles", max_review_cycles))
        elif state["state"] in EXPLICIT_RESUME_STATES:
            if not terminal_resume_authorized(state, resume_terminal_state):
                return state
            state["state"] = derive_state(repo, max_review_cycles=state.get("max_review_cycles", max_review_cycles))["state"]
            state["blockers"] = []
            state["human_action_required"] = False
            state["run_id"] = f"orch-{uuid.uuid4().hex[:12]}"
            write_state(repo, state)
    else:
        if existing and existing.get("state") not in TERMINAL_STATES:
            raise ValueError("orchestrator_start: active durable state exists; use resume or stop")
        state = derive_state(repo, max_review_cycles=max_review_cycles)
        work_hours_allowed = within_authorized_work_hours(
            goal_id=state.get("active_goal"), repo=repo
        )
        bind_external_review_runtime(
            repo,
            state,
            config_path=external_review_config_path,
            external_state_path=external_review_state_path,
            persist=work_hours_allowed,
        )
        if not work_hours_allowed:
            return state
        write_state(repo, state)
        append_event(repo, state, "ORCHESTRATOR_STARTED")
    return run_loop(repo, state, runner, max_steps)


def request_stop(repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if state is None:
        return {"status": "not_running", "human_action_required": False}
    (repo / STOP_PATH).write_text(now() + "\n", encoding="utf-8")
    return {"status": "stop_requested", "run_id": state.get("run_id"), "human_action_required": False}


def validate_engineering_reservation(
    repo: Path, reservation_path: Path, dispatch_key: str,
    expected_action: str, expected_provider: str,
) -> None:
    """Bind one scheduler continuation to the exact no-model reservation."""
    try:
        resolved = reservation_path.resolve()
        resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise ValueError("engineering reservation leaves the runtime repository") from exc
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if value.get("schema_version") != "kgnote.issue47-engineering-wakeup-state.v2":
        raise ValueError("engineering reservation schema differs")
    dispatches = value.get("dispatches")
    events = value.get("events")
    if not isinstance(dispatches, list) or not isinstance(events, list):
        raise ValueError("engineering reservation history is malformed")
    matches = [
        item for item in dispatches
        if isinstance(item, dict) and item.get("dispatch_key") == dispatch_key
    ]
    dispatch_events = [
        item for item in events
        if isinstance(item, dict) and item.get("dispatch_key") == dispatch_key
    ]
    if len(matches) != 1 or not dispatch_events or dispatch_events[-1].get("status") != "RUNNING":
        raise ValueError("engineering reservation is not the exact running dispatch")
    reservation = matches[0]
    expected_pairs = {
        "DISPATCH_IMPLEMENTATION": "codex",
        "DISPATCH_REVIEW": "claude",
    }
    if expected_pairs.get(expected_action) != expected_provider:
        raise ValueError("engineering expected action/provider pair is invalid")
    if reservation.get("action") != expected_action or reservation.get("provider") != expected_provider:
        raise ValueError("engineering continuation differs from the reserved action/provider")
    fingerprint = control.repository_fingerprint(repo)
    if (
        reservation.get("candidate_commit") != fingerprint.get("head")
        or reservation.get("candidate_fingerprint") != fingerprint.get("value")
    ):
        raise ValueError("engineering runtime candidate differs from the reservation")
    request, _, _ = control.load_review_artifacts(repo)
    state = read_state(repo)
    if state is None:
        raise ValueError("engineering orchestrator state is unavailable")
    binding = continuation_binding(request.get("status"), state.get("state"))
    if binding != (expected_action, expected_provider):
        raise ValueError("engineering continuation state pair differs from the reservation")
    if request.get("review_id") != reservation.get("review_id"):
        raise ValueError("engineering continuation review identity differs")
    if (
        expected_action == "DISPATCH_REVIEW"
        and request.get("candidate_fingerprint") != reservation.get("candidate_fingerprint")
    ):
        raise ValueError("engineering review continuation candidate differs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "resume"):
        command = sub.add_parser(name)
        command.add_argument("--max-review-cycles", type=int, default=5)
        command.add_argument("--max-steps", type=int)
        command.add_argument("--external-review-config", type=Path)
        command.add_argument("--external-review-state", type=Path)
        if name == "resume":
            command.add_argument(
                "--resume-terminal-state",
                choices=sorted(EXPLICIT_RESUME_STATES),
                help="explicitly authorize recovery from the exact persisted terminal state",
            )
            command.add_argument("--engineering-reservation", type=Path)
            command.add_argument("--dispatch-key")
            command.add_argument(
                "--expected-action",
                choices=("DISPATCH_IMPLEMENTATION", "DISPATCH_REVIEW"),
            )
            command.add_argument("--expected-provider", choices=("codex", "claude"))
    sub.add_parser("status")
    sub.add_parser("stop")
    args = parser.parse_args()
    repo = args.repo.resolve()
    try:
        if args.command in {"start", "resume"}:
            if args.max_review_cycles < 1:
                raise ValueError("max-review-cycles must be positive")
            reservation_values = (
                getattr(args, "engineering_reservation", None),
                getattr(args, "dispatch_key", None),
                getattr(args, "expected_action", None),
                getattr(args, "expected_provider", None),
            )
            if any(value is not None for value in reservation_values):
                if args.command != "resume" or not all(reservation_values):
                    raise ValueError("engineering reservation binding must be complete and resume-only")
                validate_engineering_reservation(
                    repo, reservation_values[0], reservation_values[1],
                    reservation_values[2], reservation_values[3],
                )
            result = start(
                repo,
                resume=args.command == "resume",
                max_review_cycles=args.max_review_cycles,
                max_steps=args.max_steps,
                runner=run_codex_agent,
                resume_terminal_state=getattr(args, "resume_terminal_state", None),
                external_review_config_path=args.external_review_config,
                external_review_state_path=args.external_review_state,
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
