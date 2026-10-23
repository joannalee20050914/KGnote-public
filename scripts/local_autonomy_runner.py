#!/usr/bin/env python3
"""Single Mac production Runner for cgroup-confined Ubuntu worker orders."""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, subprocess, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import external_review_control
import cross_issue_admission
import goal_runner_adapter

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output/control-plane/production-runner"
LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
ZONE = ZoneInfo("Asia/Taipei")
GLOBAL_TERMINAL = {"STOPPED", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED", "GOAL_COMPLETE", "AUTHORITY_CONFLICT"}
WORK_ITEM_PAUSED = {
    "WORK_ITEM_BLOCKED",
    "DEPENDENCY_BLOCKED",
    "WAITING_HUMAN_ACCEPTANCE",  # historical read/migration only
    "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
}
RUNNABLE = {"IMPLEMENTING", "VALIDATING", "READY_FOR_AI_REVIEW", "REVIEWING", "REPAIRING", "AWAITING_EXTERNAL_PRODUCT_REVIEW"}
STOP_MARKER = Path(".ai/ORCHESTRATOR_STOP")
PRODUCT_ORDER = Path(".ai/linux-worker-order.json")
SUCCESSOR_ORDER = Path("output/control-plane/production-runner/successor-linux-worker-order.json")
INTEGRATION_REPO = Path(
    os.environ.get(
        "KGNOTE_REVIEW_INTEGRATION_ROOT",
        str(REPO.parent / "KGnote-claude-reviewer-integration"),
    )
).resolve()
DEFAULT_ROUTER = INTEGRATION_REPO / "scripts/linux_worker_router.py"
DEFAULT_EPOCH = INTEGRATION_REPO / ".ai/CLAUDE_REVIEWER_CUTOVER_EPOCH.json"
DEFAULT_ADMISSION = INTEGRATION_REPO / "scripts/epoch_scope_admission.py"
DEFAULT_PENDING = INTEGRATION_REPO / ".ai/PENDING_SUCCESSOR_GOAL.json"
CLAUDE_ADAPTER = INTEGRATION_REPO / "scripts/claude_reviewer_adapter.py"
SUCCESSOR_HANDOFF = Path("output/control-plane/production-runner/successor-handoff.json")
CODEX_MODEL = "gpt-5.6-terra"
CODEX_EFFORT = "medium"
CLAUDE_MODEL = "sonnet"
CLAUDE_EFFORT = "medium"
SUCCESSOR_GOAL = "GOAL-KGNOTE-SOURCE-LIBRARY-SUCCESSOR-20261019"
ORDER_SCHEMA = "kgnote.linux-worker-order.v1"
REMOTE_SUCCESSOR_WORKTREE = Path("/home/kgnote/.local/share/kgnote/source-library-successor-20261019")
REMOTE_VERIFICATION_PYTHON = Path(
    "/home/kgnote/.local/share/kgnote/"
    "source-library-successor-20261019-pre-runner-handoff-20261020/.venv/bin/python"
)
VERIFICATION_MAX_ATTEMPTS = 3
STATUS_BEGIN = "<!-- BEGIN CODEX STATUS JSON -->"
STATUS_END = "<!-- END CODEX STATUS JSON -->"
RUNNER_EVENT_IDENTITY: dict[str, object] = {}
QUEUE_LABELS = {
    "queue:work-item-blocked", "queue:dependency-blocked", "queue:global-blocked",
    "queue:waiting-human", "queue:waiting-final-human", "queue:product-decision",
    "queue:idle", "queue:ready",
}
QUEUE_PROJECTION_STATES = {
    "WORK_ITEM_BLOCKED", "DEPENDENCY_BLOCKED", "GLOBAL_BLOCKED",
    "WAITING_HUMAN_ACCEPTANCE", "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
    "PRODUCT_DECISION_REQUIRED", "NO_ELIGIBLE_READY_WORK",
}
QUEUE_LABEL_RETRY = "queue-label-retry.json"
QUEUE_LABEL_RETRY_SECONDS = (60, 120, 300, 600, 1200, 1800)


class PendingWriteConflict(RuntimeError):
    pass


def blocking_record(
    kind: str,
    *,
    scope: str,
    reason: str,
    affected_work: list[str],
    release_condition: str,
    next_legal_action: str,
) -> dict[str, object]:
    """Return the one canonical shape used for every scheduler stop reason."""
    return {
        "schema_version": "kgnote.runner-block.v1",
        "kind": kind,
        "scope": scope,
        "reason": reason,
        "affected_work": affected_work,
        "release_condition": release_condition,
        "next_legal_action": next_legal_action,
    }


def github_queue_label(status: str) -> str:
    return {
        "WORK_ITEM_BLOCKED": "queue:work-item-blocked",
        "DEPENDENCY_BLOCKED": "queue:dependency-blocked",
        "GLOBAL_BLOCKED": "queue:global-blocked",
        "WAITING_HUMAN_ACCEPTANCE": "queue:waiting-human",
        "FINAL_HUMAN_ACCEPTANCE_REQUIRED": "queue:waiting-final-human",
        "PRODUCT_DECISION_REQUIRED": "queue:product-decision",
        "NO_ELIGIBLE_READY_WORK": "queue:idle",
    }.get(status, "queue:ready")


def record_issue8_completion_receipt(
    pending: dict[str, object], canonical: dict[str, object], *, command_runner=subprocess.run,
) -> dict[str, object]:
    """Record exact delivery evidence and move Issue #8 to Review Queue, idempotently."""
    repository = "joannalee20050914/KGnote-public"
    body = (
        "<!-- kgnote-delivery-receipt:issue-8-round-5 -->\n"
        "## Issue #8 精確候選交付證據\n\n"
        f"- PR：#26\n- HEAD：`{canonical['candidate_commit']}`\n"
        f"- Fingerprint：`{canonical['candidate_fingerprint']}`\n"
        f"- Ubuntu Claude Round 5：`PASS`，blocking findings：`0`\n"
        f"- Canonical review：{canonical['artifact_url']}\n"
        f"- GitHub record ID：`{canonical['record_id']}`\n"
        "- Consumer：exact identity 與原文 digest read-back 通過\n"
        "- 保留：PR 未合併；PA-HUMAN-1、NS-HUMAN-SMOKE、release_verified=false\n"
    )
    endpoint = f"repos/{repository}/issues/8/comments"
    read = command_runner(["/opt/homebrew/bin/gh", "api", endpoint, "--paginate"], capture_output=True, text=True)
    if read.returncode:
        raise RuntimeError((read.stderr or "Issue receipt read failed").strip())
    rows = json.loads(read.stdout)
    matches = [row for row in rows if row.get("body") == body and row.get("user", {}).get("login") == "joannalee20050914"]
    if not matches:
        write = command_runner(["/opt/homebrew/bin/gh", "api", endpoint, "-f", f"body={body}"], capture_output=True, text=True)
        if write.returncode:
            raise RuntimeError((write.stderr or "Issue receipt write failed").strip())
        read = command_runner(["/opt/homebrew/bin/gh", "api", endpoint, "--paginate"], capture_output=True, text=True)
        if read.returncode:
            raise RuntimeError((read.stderr or "Issue receipt read-back failed").strip())
        rows = json.loads(read.stdout)
        matches = [row for row in rows if row.get("body") == body and row.get("user", {}).get("login") == "joannalee20050914"]
    if len(matches) != 1:
        raise RuntimeError("Issue #8 exact completion receipt did not read back exactly once")
    edit = command_runner([
        "/opt/homebrew/bin/gh", "project", "item-edit",
        "--id", "PVTI_lAHOCdyRA84BnSs6zhBKcNo", "--project-id", "PVT_kwHOCdyRA84BnSs6",
        "--field-id", "PVTSSF_lAHOCdyRA84BnSs6zhl3_64", "--single-select-option-id", "be81b156",
    ], capture_output=True, text=True)
    if edit.returncode:
        raise RuntimeError((edit.stderr or "Project receipt write failed").strip())
    return {
        "status": "VERIFIED", "issue": 8, "project_status": "Review Queue",
        "issue_comment_id": matches[0].get("id"), "issue_comment_url": matches[0].get("html_url"),
        "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "review_record_id": canonical["record_id"], "review_artifact_url": canonical["artifact_url"],
    }


def scheduler_projection_status(
    pending: dict[str, object], decision: dict[str, object],
) -> str | None:
    """Return durable GitHub state, excluding transient dispatch-window stops."""
    durable = str(pending.get("status") or "")
    if durable in QUEUE_PROJECTION_STATES:
        return durable
    blocks = decision.get("blocks", [])
    blocks = blocks if isinstance(blocks, list) else []
    first = blocks[0] if blocks and isinstance(blocks[0], dict) else {}
    if first.get("reason") == "outside the authorized product work window":
        # Time windows control model dispatch only. The durable PR/work-item
        # classification was already projected from pending.status and must
        # not be rewritten merely because the clock crossed a boundary.
        return None
    candidate = str(first.get("kind") or decision.get("status") or "")
    return candidate if candidate in QUEUE_PROJECTION_STATES else None


def review_progression_error(
    previous: dict[str, object] | None,
    current: dict[str, object],
) -> str | None:
    """Reject unexplained CHANGES_REQUIRED -> PASS flips for one exact candidate.

    A new reviewer invocation is not new evidence.  If bytes did not change,
    every previous blocking finding needs structured, independently checkable
    resolution evidence in the new result.
    """
    if not isinstance(previous, dict):
        return None
    if previous.get("verdict") != "CHANGES_REQUIRED" or current.get("verdict") != "PASS":
        return None
    same_identity = (
        previous.get("candidate_commit") == current.get("candidate_commit")
        and previous.get("candidate_fingerprint") == current.get("candidate_fingerprint")
    )
    if not same_identity:
        return None
    blocking_ids = {
        str(finding.get("id"))
        for finding in previous.get("findings", [])
        if isinstance(finding, dict) and finding.get("severity") == "blocking" and finding.get("id")
    }
    evidence = current.get("resolution_evidence", [])
    resolved_ids: set[str] = set()
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            identity = item.get("evidence_identity")
            if not isinstance(identity, str) or not identity.strip():
                continue
            linked = item.get("finding_ids", [])
            if isinstance(linked, list):
                resolved_ids.update(str(value) for value in linked)
    if not blocking_ids or not blocking_ids.issubset(resolved_ids):
        missing = sorted(blocking_ids - resolved_ids)
        return (
            "same exact candidate changed from CHANGES_REQUIRED to PASS without "
            f"structured new resolution evidence for {missing or ['prior blocking finding']}"
        )
    return None


def persisted_review_progression_error(
    pending: dict[str, object], evidence_root: Path,
) -> tuple[str | None, dict[str, object] | None]:
    result = pending.get("review_result", {})
    if not isinstance(result, dict) or result.get("verdict") != "PASS":
        return None, None
    review_round = result.get("round")
    if not isinstance(review_round, int) or review_round < 2:
        return None, None
    try:
        previous_event = load(evidence_root / f"successor-review-event-r{review_round - 1}.json")
        current_event = load(evidence_root / f"successor-review-event-r{review_round}.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return "review transition evidence is missing or unreadable", None
    previous = previous_event.get("review")
    current_review = current_event.get("review")
    if not isinstance(previous, dict) or not isinstance(current_review, dict):
        return "review transition evidence does not contain both exact results", None
    return review_progression_error(previous, current_review), previous


def human_checkpoint_eligibility_errors(pending: dict[str, object]) -> list[str]:
    """Delegate every Consumer to the one final-gate validator."""
    checkpoint = pending.get("human_checkpoint")
    commit = pending.get("candidate_commit")
    fingerprint = pending.get("candidate_fingerprint")
    return external_review_control.final_human_acceptance_errors(
        checkpoint,
        candidate_commit=commit if isinstance(commit, str) else None,
        candidate_fingerprint=fingerprint if isinstance(fingerprint, str) else None,
    )


def status_after_component_pass(pending: dict[str, object]) -> str:
    """Route PASS without confusing preserved gates with an immediate stop."""
    if not human_checkpoint_eligibility_errors(pending):
        return "FINAL_HUMAN_ACCEPTANCE_REQUIRED"
    return "COMPONENT_REVIEW_COMPLETE"


def soft_feedback_key(goal_id: str, candidate_version: str, experience_scope: str) -> str:
    """Return the stable dedup identity required by the product decision."""
    payload = json.dumps(
        [goal_id.strip(), candidate_version.strip(), experience_scope.strip()],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def work_notification_eligible(event_type: str) -> bool:
    """Work is notification-only; routine autonomous events are never eligible."""
    return event_type in {"SOFT_FEEDBACK_AVAILABLE", "FINAL_HUMAN_ACCEPTANCE_REQUIRED"}


def soft_feedback_eligibility_errors(event: object) -> list[str]:
    if not isinstance(event, dict):
        return ["soft_feedback: event must be an object"]
    errors: list[str] = []
    for field in ("goal_id", "candidate_version", "experience_scope", "entrypoint"):
        value = event.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"soft_feedback: {field} is required")
    for field in ("operable_evidence", "suggested_steps", "experience_questions"):
        value = event.get(field)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(f"soft_feedback: {field} must contain concrete entries")
    if event.get("actually_operable") is not True:
        errors.append("soft_feedback: actually_operable must be proven")
    return errors


def register_soft_feedback_event(
    pending: dict[str, object], event: dict[str, object]
) -> tuple[dict[str, object] | None, bool]:
    """Persist one optional event without changing the scheduler state."""
    errors = soft_feedback_eligibility_errors(event)
    if errors:
        return None, False
    key = soft_feedback_key(
        str(event["goal_id"]),
        str(event["candidate_version"]),
        str(event["experience_scope"]),
    )
    events = pending.setdefault("soft_feedback_events", [])
    if not isinstance(events, list):
        return None, False
    for existing in events:
        if isinstance(existing, dict) and existing.get("notification_key") == key:
            return existing, False
    stored = {
        **event,
        "event_type": "SOFT_FEEDBACK_AVAILABLE",
        "blocking": False,
        "feedback_status": "OPTIONAL_PENDING",
        "notification_key": key,
        "notification_status": "PENDING_PERMISSION_VERIFICATION",
    }
    events.append(stored)
    return stored, True


def soft_feedback_notification(event: dict[str, object]) -> dict[str, object]:
    """Project the required GitHub/Work notification body without sending it."""
    return {
        "notification_key": event.get("notification_key"),
        "title": "可選擇的人類體驗回饋（不是正式驗收）",
        "optional": True,
        "blocks_development": False,
        "candidate_version": event.get("candidate_version"),
        "experience_scope": event.get("experience_scope"),
        "entrypoint": event.get("entrypoint"),
        "suggested_steps": event.get("suggested_steps"),
        "experience_questions": event.get("experience_questions"),
        "continuation_notice": "不提供意見時，系統仍會繼續已授權的產品開發。",
    }


def final_human_acceptance_notification(checkpoint: dict[str, object]) -> dict[str, object]:
    """Project the blocking final notice after the shared validator passes."""
    errors = external_review_control.final_human_acceptance_errors(
        checkpoint,
        candidate_commit=(checkpoint.get("candidate_commit") if isinstance(checkpoint.get("candidate_commit"), str) else None),
        candidate_fingerprint=(checkpoint.get("candidate_fingerprint") if isinstance(checkpoint.get("candidate_fingerprint"), str) else None),
    )
    if errors:
        raise ValueError("; ".join(errors))
    evidence = checkpoint.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("final_acceptance: actual prerequisite evidence list is missing")
    acceptance_scope = checkpoint.get("acceptance_scope")
    if not isinstance(acceptance_scope, list) or not acceptance_scope:
        raise ValueError("final_acceptance: formal user acceptance scope is missing")
    return {
        "gate_id": external_review_control.FINAL_HUMAN_GATE_ID,
        "title": "KGnote 完整產品正式人類驗收",
        "blocking": True,
        "candidate": {
            "commit": checkpoint.get("candidate_commit"),
            "fingerprint": checkpoint.get("candidate_fingerprint"),
        },
        "prerequisite_evidence": evidence,
        "installation_and_trial_entrypoint": checkpoint.get("trial_entrypoint"),
        "acceptance_scope": acceptance_scope,
        "continuation_notice": "正式交付流程正在等待產品擁有人確認；系統不會自動通過此驗收。",
    }


def record_late_soft_feedback(
    pending: dict[str, object],
    notification_key: str,
    *,
    feedback: str,
    impact_scope: list[str],
) -> dict[str, object] | None:
    """Bind a late reply to its original candidate and bounded impact."""
    events = pending.get("soft_feedback_events")
    if not isinstance(events, list) or not feedback.strip() or not impact_scope:
        return None
    for event in events:
        if not isinstance(event, dict) or event.get("notification_key") != notification_key:
            continue
        event["feedback_status"] = "RECEIVED"
        followup = {
            "notification_key": notification_key,
            "goal_id": event.get("goal_id"),
            "candidate_version": event.get("candidate_version"),
            "experience_scope": event.get("experience_scope"),
            "feedback": feedback,
            "impact_scope": impact_scope,
            "status": "NEEDS_BOUNDED_TRIAGE",
        }
        pending.setdefault("feedback_followups", []).append(followup)
        return followup
    return None


def select_ready_work(
    pending: dict[str, object],
    current: datetime,
    *,
    stop_marker_present: bool,
) -> dict[str, object]:
    """Select an already-authorized isolated order without inventing work."""
    queue = pending.get("ready_queue", [])
    items = queue if isinstance(queue, list) else []
    states = pending.get("work_item_states", {})
    states = states if isinstance(states, dict) else {}
    global_constraints = pending.get("global_constraints", [])
    if isinstance(global_constraints, list):
        active = [item for item in global_constraints if isinstance(item, dict) and item.get("active") is True]
        if active:
            reason = str(active[0].get("reason", "active global constraint"))
            return {"status": "GLOBAL_BLOCKED", "selected": None, "blocks": [blocking_record(
                "GLOBAL_BLOCKED", scope="RUNNER", reason=reason,
                affected_work=[str(item.get("work_item_id")) for item in items if isinstance(item, dict)],
                release_condition=str(active[0].get("release_condition", "clear the global constraint through its authorized owner")),
                next_legal_action="remain idle and preserve every work-item state",
            )]}
    window = pending.get("work_window", {})
    if not in_window({"work_window": window}, current):
        return {"status": "GLOBAL_BLOCKED", "selected": None, "blocks": [blocking_record(
            "GLOBAL_BLOCKED", scope="RUNNER", reason="outside the authorized product work window",
            affected_work=[str(item.get("work_item_id")) for item in items if isinstance(item, dict)],
            release_condition="the next authorized Asia/Taipei work window begins",
            next_legal_action="remain idle; retry selection on the next scheduled wake",
        )]}

    blocks: list[dict[str, object]] = []
    stop_policy = pending.get("stop_marker_policy", {})
    stop_policy = stop_policy if isinstance(stop_policy, dict) else {}
    global_stop = stop_marker_present and stop_policy.get("scope") == "GLOBAL"
    if global_stop:
        return {"status": "GLOBAL_BLOCKED", "selected": None, "blocks": [blocking_record(
            "GLOBAL_BLOCKED", scope="RUNNER", reason=str(stop_policy.get("reason", "global operator stop marker")),
            affected_work=[str(item.get("work_item_id")) for item in items if isinstance(item, dict)],
            release_condition=str(stop_policy.get("release_condition", "operator clears the global stop")),
            next_legal_action="remain idle; do not clear the marker automatically",
        )]}
    marker_affected = set(str(value) for value in stop_policy.get("affected_work", []) if value)

    for raw in items:
        if not isinstance(raw, dict):
            continue
        work_id = str(raw.get("work_item_id", ""))
        item_status = str(raw.get("status", ""))
        if not work_id:
            continue
        if item_status == "WORK_ITEM_BLOCKED":
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM",
                reason=str(raw.get("blocked_reason") or "work item is durably blocked"),
                affected_work=[work_id],
                release_condition=str(raw.get("release_condition") or "the recorded failure is resolved under existing authority"),
                next_legal_action="preserve the checkpoint and do not redispatch",
            ))
            continue
        if item_status in {"DISPATCHING", "DISPATCHED"}:
            blocks.append(blocking_record(
                "WORK_ITEM_WAITING", scope="WORK_ITEM",
                reason=f"{item_status.lower()} item is waiting for its existing checkpoint",
                affected_work=[work_id], release_condition="the exact checkpoint reaches a terminal state",
                next_legal_action="consume the checkpoint without invoking the router again",
            ))
            continue
        if item_status == "WORKER_COMPLETED":
            blocks.append(blocking_record(
                "WORK_ITEM_COMPLETE", scope="WORK_ITEM", reason="worker checkpoint was already consumed",
                affected_work=[work_id], release_condition="none",
                next_legal_action="do not consume or push this event again",
            ))
            continue
        if item_status != "READY":
            continue
        if stop_marker_present and work_id in marker_affected:
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="legacy stop marker applies to this work item",
                affected_work=[work_id], release_condition=str(stop_policy.get("release_condition", "authorized marker clearance")),
                next_legal_action="leave this item queued and evaluate independent ready work",
            ))
            continue
        authority = raw.get("authority", {})
        if not isinstance(authority, dict) or authority.get("status") != "APPROVED":
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="explicit execution authority is missing",
                affected_work=[work_id], release_condition="record an approved authority source and bounded execution envelope",
                next_legal_action="do not dispatch this item",
            ))
            continue
        dependencies = raw.get("dependencies", [])
        dependencies = dependencies if isinstance(dependencies, list) else []
        missing = [str(dep) for dep in dependencies if states.get(str(dep)) != "COMPLETE"]
        if missing:
            blocks.append(blocking_record(
                "DEPENDENCY_BLOCKED", scope="DEPENDENCY_SUBGRAPH",
                reason=f"unfinished dependencies: {missing}", affected_work=[work_id, *missing],
                release_condition="every named dependency reaches COMPLETE without bypassing its gates",
                next_legal_action="leave dependent work queued and evaluate another independent item",
            ))
            continue
        budget = raw.get("budget", {})
        if not isinstance(budget, dict) or not isinstance(budget.get("authorized"), int) or not isinstance(budget.get("used"), int) or budget["used"] >= budget["authorized"]:
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="work-item execution budget is exhausted or invalid",
                affected_work=[work_id], release_condition="an authorized budget remains available",
                next_legal_action="do not reset or extend the budget",
            ))
            continue
        safety = raw.get("safety", {})
        if not isinstance(safety, dict) or safety.get("isolated_worktree") is not True or safety.get("automatic_merge") is not False:
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="safe isolated execution or merge protection is not proven",
                affected_work=[work_id], release_condition="provide an isolated worktree and preserve automatic_merge=false",
                next_legal_action="do not dispatch this item",
            ))
            continue
        order_path = raw.get("order_path")
        if not isinstance(order_path, str) or not order_path:
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="no pre-authorized worker order is bound to the ready item",
                affected_work=[work_id], release_condition="seal a bounded worker order through the existing control plane",
                next_legal_action="do not create a branch or PR merely to keep the Runner busy",
            ))
            continue
        return {"status": "DISPATCH_READY", "selected": raw, "blocks": blocks}
    return {"status": "NO_ELIGIBLE_READY_WORK", "selected": None, "blocks": blocks}


def configured_execution_context(role: str, *, pull_request: int, cycle: int | None = None,
                                 review_round: int | None = None) -> dict[str, object]:
    if role == "CODEX_IMPLEMENTER":
        return {
            "schema_version":"kgnote.model-execution-evidence.v1", "role":role,
            "goal_id":SUCCESSOR_GOAL, "pull_request":pull_request, "cycle":cycle,
            "provider":"OpenAI", "authentication":"ChatGPT OAuth",
            "requested_model":CODEX_MODEL, "requested_effort":CODEX_EFFORT,
            "cli_version_expected":"codex-cli 0.146.0", "configuration_status":"CONFIGURED",
            "effective_model":None, "effective_effort":None, "effective_status":"EFFECTIVE_UNKNOWN",
            "token_usage":None,
        }
    if role == "CLAUDE_PRODUCT_REVIEWER":
        return {
            "schema_version":"kgnote.model-execution-evidence.v1", "role":role,
            "goal_id":SUCCESSOR_GOAL, "pull_request":pull_request, "review_round":review_round,
            "provider":"Anthropic", "authentication":"Claude Pro OAuth",
            "requested_model":CLAUDE_MODEL, "requested_effort":CLAUDE_EFFORT,
            "cli_version_expected":"2.1.302 (Claude Code)", "configuration_status":"CONFIGURED",
            "actual_models":[], "effective_status":"EFFECTIVE_UNKNOWN", "token_usage":None,
        }
    return {
        "schema_version":"kgnote.model-execution-evidence.v1", "role":role,
        "goal_id":SUCCESSOR_GOAL, "pull_request":pull_request,
        "provider":None, "requested_model":None, "requested_effort":None,
        "model_usage_status":"NOT_APPLICABLE", "token_usage":None,
    }

def append(event: str, **fields: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": datetime.now(ZONE).isoformat(timespec="seconds"), "event": event, **RUNNER_EVENT_IDENTITY, **fields}, ensure_ascii=False) + "\n")

def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path.name} must contain an object")
    return value


def atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def write_pending(path: Path, value: dict[str, object]) -> None:
    """Compare-and-swap the sole mutable Runner state document."""
    expected = int(value.get("revision", 0))
    try:
        current = load(path)
        observed = int(current.get("revision", 0))
    except FileNotFoundError:
        observed = 0
    if observed != expected:
        append("pending_revision_conflict", path=str(path), expected_revision=expected, observed_revision=observed)
        raise PendingWriteConflict(
            f"pending revision changed concurrently: expected {expected}, observed {observed}"
        )
    value["revision"] = expected + 1
    atomic_json(path, value)


def record_scheduler_runtime(current: datetime, status: str, selected: str | None) -> None:
    atomic_json(OUT / "scheduler-runtime.json", {
        "schema_version": "kgnote.runner-scheduler-runtime.v1",
        "evaluated_at": current.isoformat(timespec="seconds"),
        "status": status,
        "selected_work_item": selected,
    })


def runner_code_identity(code_root: Path) -> dict[str, object]:
    head = subprocess.run(
        ["/usr/bin/git", "-C", str(code_root), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=False,
    )
    dirty = subprocess.run(
        ["/usr/bin/git", "-C", str(code_root), "status", "--porcelain", "--untracked-files=all"],
        text=True, capture_output=True, check=False,
    )
    return {
        "runner_code_head": head.stdout.strip() if head.returncode == 0 else None,
        "runner_code_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else True,
        "runner_code_status_error": None if head.returncode == 0 and dirty.returncode == 0 else "git_identity_unavailable",
    }


def worker_command_digest(order: dict[str, object]) -> str:
    value: dict[str, object] = {
        "event_id": order.get("event_id"), "stage": order.get("stage"),
        "working_directory": str(order.get("working_directory")),
        "handoff_directory": str(order.get("handoff_directory")) if order.get("handoff_directory") else None,
        "command": tuple(str(item) for item in order.get("command", [])),
    }
    if order.get("execution_context") is not None:
        value["execution_context"] = order["execution_context"]
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def route_failure(checkpoint: dict[str, object] | None, route_exit: int) -> tuple[str, str]:
    checkpoint = checkpoint if isinstance(checkpoint, dict) else {}
    if checkpoint.get("reason") == "quota_exhausted":
        return "QUOTA_EXHAUSTED", "quota_exhausted"
    return "DETERMINISTIC_WORKER_FAILURE", str(checkpoint.get("reason") or f"worker route failed with exit {route_exit}")


def apply_queue_label(
    pending: dict[str, object], status: str, *, item: dict[str, object] | None = None,
    command_runner=subprocess.run, current: datetime | None = None,
) -> bool:
    """Safely and idempotently project one queue state.

    The desired label is validated and added before stale labels are removed.
    A persistent bounded backoff prevents a failing GitHub mutation from being
    retried by every Runner tick, including across Runner restarts.
    """
    label = github_queue_label(status)
    admission = (item or {}).get("admission", {}) if isinstance(item, dict) else {}
    admission = admission if isinstance(admission, dict) else {}
    receipt = (item or {}).get("admission_receipt", {}) if isinstance(item, dict) else {}
    receipt = receipt if isinstance(receipt, dict) else {}
    scope = pending.get("scope", {})
    scope = scope if isinstance(scope, dict) else {}
    repository = str(admission.get("repository") or scope.get("repository") or "")
    pull_request = receipt.get("pull_request") or scope.get("pull_request") or pending.get("successor_pull_request")
    issue = admission.get("issue") or scope.get("issue")
    kind, number = ("pr", pull_request) if isinstance(pull_request, int) else ("issue", issue)
    if not repository or not isinstance(number, int):
        append("github_queue_label_skipped", status=status, reason="target_identity_missing")
        return False
    now = current or datetime.now(ZONE)
    retry_path = OUT / QUEUE_LABEL_RETRY
    retry_key = f"{repository}:{kind}:{number}:{label}"
    try:
        retry_state = load(retry_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        retry_state = {}
    entries = retry_state.get("entries", {})
    entries = entries if isinstance(entries, dict) else {}
    retry = entries.get(retry_key, {})
    retry = retry if isinstance(retry, dict) else {}
    try:
        next_retry = datetime.fromisoformat(str(retry.get("next_retry_at")))
    except (TypeError, ValueError):
        next_retry = None
    if next_retry is not None and now < next_retry:
        append(
            "github_queue_label_retry_deferred", status=status,
            target=f"{kind}#{number}", next_retry_at=next_retry.isoformat(),
        )
        return False

    def record_failure(operation: str, result: subprocess.CompletedProcess[str]) -> bool:
        count = min(int(retry.get("failure_count", 0)) + 1, len(QUEUE_LABEL_RETRY_SECONDS))
        delay = QUEUE_LABEL_RETRY_SECONDS[count - 1]
        entries[retry_key] = {
            "failure_count": count,
            "last_failure_at": now.isoformat(),
            "next_retry_at": (now + timedelta(seconds=delay)).isoformat(),
            "operation": operation,
            "exit_code": result.returncode,
            "error_tail": (result.stderr or "")[-1000:],
        }
        atomic_json(retry_path, {"schema_version": "kgnote.queue-label-retry.v1", "entries": entries})
        append(
            "github_queue_label_failed", status=status, target=f"{kind}#{number}",
            exit_code=result.returncode, operation=operation,
            next_retry_at=entries[retry_key]["next_retry_at"],
        )
        return False

    def clear_retry() -> None:
        if retry_key not in entries:
            return
        entries.pop(retry_key, None)
        atomic_json(retry_path, {"schema_version": "kgnote.queue-label-retry.v1", "entries": entries})

    def read_labels() -> tuple[subprocess.CompletedProcess[str], set[str]]:
        result = command_runner(
            ["/opt/homebrew/bin/gh", kind, "view", str(number), "--repo", repository, "--json", "labels"],
            capture_output=True, text=True,
        )
        try:
            names = {
                str(entry.get("name")) for entry in json.loads(result.stdout).get("labels", [])
                if isinstance(entry, dict) and isinstance(entry.get("name"), str)
            }
        except (json.JSONDecodeError, AttributeError):
            names = set()
        return result, names

    view, existing = read_labels()
    if view.returncode:
        return record_failure("read_current", view)
    stale = sorted((existing & QUEUE_LABELS) - {label})
    if label in existing and not stale:
        clear_retry()
        return True

    # A missing or inaccessible target label must be discovered before any
    # existing known-good queue label is touched.
    target = command_runner(
        ["/opt/homebrew/bin/gh", "label", "list", "--repo", repository, "--search", label, "--json", "name", "--limit", "100"],
        capture_output=True, text=True,
    )
    if target.returncode:
        return record_failure("validate_target", target)
    try:
        target_names = {
            str(entry.get("name")) for entry in json.loads(target.stdout)
            if isinstance(entry, dict) and isinstance(entry.get("name"), str)
        }
    except (json.JSONDecodeError, TypeError):
        target_names = set()
    if label not in target_names:
        synthetic = subprocess.CompletedProcess([], 1, "", "target label does not exist")
        return record_failure("validate_target", synthetic)
    if label not in existing:
        edited = command_runner(
            ["/opt/homebrew/bin/gh", kind, "edit", str(number), "--repo", repository, "--add-label", label],
            capture_output=True, text=True,
        )
        if edited.returncode:
            return record_failure("add_target", edited)
        verified, existing = read_labels()
        if verified.returncode:
            return record_failure("verify_target", verified)
        if label not in existing:
            synthetic = subprocess.CompletedProcess([], 1, "", "target label absent after successful add")
            return record_failure("verify_target", synthetic)
        stale = sorted((existing & QUEUE_LABELS) - {label})
    if stale:
        remove_command = ["/opt/homebrew/bin/gh", kind, "edit", str(number), "--repo", repository]
        for old in stale:
            remove_command.extend(("--remove-label", old))
        removed = command_runner(remove_command, capture_output=True, text=True)
        if removed.returncode:
            return record_failure("remove_stale", removed)
        verified, final_labels = read_labels()
        if verified.returncode:
            return record_failure("verify_final", verified)
        if label not in final_labels or ((final_labels & QUEUE_LABELS) - {label}):
            synthetic = subprocess.CompletedProcess([], 1, "", "queue labels did not converge")
            return record_failure("verify_final", synthetic)
    clear_retry()
    append("github_queue_label_applied", status=status, target=f"{kind}#{number}", label=label, removed=stale)
    return True


def publish_admission_error(remote_head: str | None, candidate: str, legacy_head: str,
                            published_head: str | None, verification: dict[str, object]) -> str | None:
    if remote_head not in {legacy_head, published_head, candidate}:
        return "remote_head_mismatch"
    if verification.get("status") != "PASS" or verification.get("candidate_commit") != candidate:
        return "candidate_not_verified"
    fingerprint = verification.get("candidate_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        return "candidate_fingerprint_invalid"
    return None


def verified_candidate_fingerprint(evidence: dict[str, object], candidate: str) -> str | None:
    fingerprint = ((evidence.get("fingerprint_after") or {}).get("value")) if isinstance(evidence.get("fingerprint_after"), dict) else None
    if (evidence.get("result") == "pass" and evidence.get("evidence_readback") is True
            and isinstance(evidence.get("repository"), dict) and evidence["repository"].get("head") == candidate
            and evidence.get("fingerprint_stable") is True and isinstance(fingerprint, str) and len(fingerprint) == 64):
        return fingerprint
    return None


def render_verification_status(
    text: str, *, candidate: str, fingerprint: str, updated_at: str,
) -> str:
    """Synchronize only the mutable STATUS receipt for pre-publication verification."""
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise ValueError("candidate is not a full Git commit")
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("candidate fingerprint is invalid")
    start = text.find(STATUS_BEGIN)
    end = text.find(STATUS_END)
    if start < 0 or end <= start:
        raise ValueError("CODEX_STATUS markers are missing")
    fenced = text.find("```json", start, end)
    closing = text.find("```", fenced + len("```json"), end)
    if fenced < 0 or closing < 0:
        raise ValueError("CODEX_STATUS JSON fence is missing")
    value = json.loads(text[fenced + len("```json"):closing])
    if not isinstance(value, dict):
        raise ValueError("CODEX_STATUS JSON root must be an object")
    git_state = value.get("git")
    working_state = value.get("working_state")
    verification = value.get("verification")
    if not all(isinstance(item, dict) for item in (git_state, working_state, verification)):
        raise ValueError("CODEX_STATUS identity sections are missing")
    value["updated_at"] = updated_at
    git_state["branch"] = "codex/source-library-successor-20261019"
    git_state["head"] = candidate
    git_state["checkpoint_commit"] = candidate
    working_state["fingerprint"] = fingerprint
    verification["candidate_verified"] = False
    verification["control_plane_ready"] = False
    rendered = json.dumps(value, indent=2, ensure_ascii=False)
    return text[:fenced + len("```json")] + "\n" + rendered + "\n" + text[closing:]


def prepare_remote_candidate_verification(
    repo: Path, candidate: str, command_runner=subprocess.run,
) -> tuple[bool, str | None]:
    """Prepare ignored tooling/output and one fingerprint-excluded STATUS mutation.

    Product bytes and the candidate commit remain untouched.  The dirty STATUS
    receipt intentionally selects the ordinary pre-publication preflight path,
    rather than claiming that the not-yet-pushed candidate is already the live
    publication-adapter HEAD.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        return False, "candidate identity is invalid"
    remote = str(REMOTE_SUCCESSOR_WORKTREE)
    status = command_runner(
        ["ssh", "kgnote-ubuntu", "/usr/bin/git", "-C", remote, "status", "--porcelain", "--untracked-files=all"],
        cwd=repo, capture_output=True, text=True,
    )
    dirty = [line for line in (status.stdout or "").splitlines() if line]
    if status.returncode or any(line != " M CODEX_STATUS.md" for line in dirty):
        return False, f"candidate worktree has non-STATUS drift: {dirty!r}"
    identity = command_runner(
        ["ssh", "kgnote-ubuntu", "/usr/bin/python3", f"{remote}/scripts/codex_control.py", "--repo", remote, "fingerprint"],
        cwd=repo, capture_output=True, text=True,
    )
    try:
        fingerprint = json.loads(identity.stdout)
    except json.JSONDecodeError:
        fingerprint = {}
    if (
        identity.returncode
        or fingerprint.get("head") != candidate
        or fingerprint.get("branch") != "codex/source-library-successor-20261019"
        or not isinstance(fingerprint.get("value"), str)
    ):
        return False, "remote candidate fingerprint identity does not match the pending candidate"
    current = command_runner(
        ["ssh", "kgnote-ubuntu", "/usr/bin/cat", f"{remote}/CODEX_STATUS.md"],
        cwd=repo, capture_output=True, text=True,
    )
    if current.returncode:
        return False, "remote CODEX_STATUS is unreadable"
    try:
        rendered = render_verification_status(
            current.stdout,
            candidate=candidate,
            fingerprint=str(fingerprint["value"]),
            updated_at=datetime.now(ZONE).isoformat(timespec="seconds"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return False, f"remote CODEX_STATUS cannot be synchronized: {exc}"
    local_status = OUT / f"verification-status-{candidate[:8]}.md"
    local_status.write_text(rendered, encoding="utf-8")
    remote_temporary = f"{remote}/.CODEX_STATUS.runner.tmp"
    copied = command_runner(
        ["scp", str(local_status), f"kgnote-ubuntu:{remote_temporary}"],
        cwd=repo, capture_output=True, text=True,
    )
    if copied.returncode:
        return False, "remote CODEX_STATUS staging failed"
    installed = command_runner(
        ["ssh", "kgnote-ubuntu", "/usr/bin/mv", remote_temporary, f"{remote}/CODEX_STATUS.md"],
        cwd=repo, capture_output=True, text=True,
    )
    if installed.returncode:
        return False, "remote CODEX_STATUS atomic install failed"
    final = command_runner(
        ["ssh", "kgnote-ubuntu", "/usr/bin/git", "-C", remote, "status", "--porcelain", "--untracked-files=all"],
        cwd=repo, capture_output=True, text=True,
    )
    final_dirty = [line for line in (final.stdout or "").splitlines() if line]
    if final.returncode or final_dirty != [" M CODEX_STATUS.md"]:
        return False, f"verification preparation changed unexpected paths: {final_dirty!r}"
    return True, None


def verification_failure_disposition(
    evidence: dict[str, object], *, route_exit: int, stderr: str,
) -> tuple[str, str]:
    """Separate routine repair routing from protected fail-closed boundaries."""
    lowered = stderr.lower()
    if any(marker in lowered for marker in ("permission denied", "operation not permitted", "landlock", "authority")):
        return "HARD_STOP", "verification hit a permission, sandbox, or authority boundary"
    if not evidence:
        return "INFRA_RETRY", f"verification produced no readable evidence (route exit {route_exit})"
    if evidence.get("evidence_readback") is not True:
        return "INFRA_RETRY", "verification evidence write/read-back did not complete"
    if evidence.get("fingerprint_stable") is not True:
        return "HARD_STOP", "candidate fingerprint changed during deterministic verification"
    preflight = evidence.get("preflight", {})
    errors = preflight.get("errors", []) if isinstance(preflight, dict) else []
    errors = [str(item) for item in errors] if isinstance(errors, list) else [str(errors)]
    if errors:
        if all(item.startswith("tooling:") for item in errors):
            return "INFRA_RETRY", "verification toolchain is unavailable"
        return "HARD_STOP", "candidate preflight failed a protected identity, authority, or safety gate"
    gates = evidence.get("gates", [])
    failed = {
        str(gate.get("name"))
        for gate in gates if isinstance(gate, dict) and gate.get("passed") is not True
    } if isinstance(gates, list) else set()
    if failed & {"public_safety_scan"}:
        return "HARD_STOP", "candidate failed the public-safety scan"
    if failed:
        return "PRODUCT_REPAIR", "candidate deterministic tests or candidate-quality gates failed"
    return "INFRA_RETRY", f"verification exit {route_exit} was not accompanied by a valid PASS"


def verification_command(remote_receipt: str) -> list[str]:
    if not re.fullmatch(r"output/control-plane/runner-verification-[0-9a-f]{8}\.json", remote_receipt):
        raise ValueError("verification receipt path is invalid")
    verification_python = str(REMOTE_VERIFICATION_PYTHON)
    return ["/bin/sh", "-c", (
        "set -eu; /usr/bin/mkdir -p output/control-plane; "
        "PATH=/home/kgnote/.local/bin:/home/kgnote/.local/lib/node-v24.12.0/bin:/usr/bin:/bin; "
        f"KGNOTE_TEST_PYTHON={verification_python}; export PATH KGNOTE_TEST_PYTHON; "
        f"{verification_python} scripts/codex_control.py --repo . verify > {remote_receipt}"
    )]


def successor_errors(pending: dict[str, object], current: datetime) -> list[str]:
    errors: list[str] = []
    if pending.get("schema_version") != "kgnote.pending-successor-goal.v1": errors.append("unsupported pending goal schema")
    if pending.get("status") not in {"PENDING_ELIGIBLE", "ACTIVATING", "ACTIVE", "BLOCKED"}: errors.append("pending goal is not eligible")
    authority = pending.get("authority", {})
    if not isinstance(authority, dict) or authority.get("status") != "APPROVED_FOR_FUTURE_WINDOW": errors.append("future-window authority is missing")
    try: activation = datetime.fromisoformat(str(pending["activation_not_before"]))
    except (KeyError, ValueError): errors.append("activation_not_before is invalid"); activation = current
    if current < activation: errors.append("activation time has not arrived")
    budget = pending.get("continuous_budget", {})
    if not isinstance(budget, dict): errors.append("continuous budget is invalid")
    else:
        for name in ("new_prs", "claude_product_reviews", "codex_implementation_or_repair_cycles"):
            item = budget.get(name, {})
            if not isinstance(item, dict) or not isinstance(item.get("authorized"), int) or not isinstance(item.get("used"), int) or item["used"] >= item["authorized"]:
                errors.append(f"{name} budget is exhausted or invalid")
    legacy = pending.get("legacy_inheritance", {})
    if not isinstance(legacy, dict) or legacy.get("pull_request") != 23 or legacy.get("review_round") != 8 or legacy.get("cycle") != 20:
        errors.append("legacy PR/Round/Cycle inheritance is invalid")
    if pending.get("product_work_started") is not False and pending.get("status") != "ACTIVE": errors.append("pending goal has inconsistent product state")
    return errors


def prepare_successor_handoff(repo: Path, pending_path: Path, current: datetime, command_runner=subprocess.run) -> tuple[Path | None, list[str]]:
    """Create one epoch-new branch/PR and a durable Ubuntu Codex order.

    GitHub mutations are idempotent read-before-write operations. Candidate
    commits are never pushed here; later pushes remain restricted to the Guest
    push stage and its repository-scoped deploy key.
    """
    try: pending = load(pending_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc: return None, [str(exc)]
    errors = successor_errors(pending, current)
    if errors: return None, errors
    goal_id = str(pending["goal_id"]); repository = str((pending.get("scope") or {}).get("repository"))
    legacy = pending["legacy_inheritance"]
    published = pending.get("published_candidate", {})
    head = str((published or {}).get("commit") or legacy["head"])
    codex_budget = pending["continuous_budget"]["codex_implementation_or_repair_cycles"]
    successor_cycle = int(codex_budget["used"]) + 1
    branch = "codex/source-library-successor-20261019"
    ref_endpoint = f"repos/{repository}/git/ref/heads/{branch}"
    read_ref = command_runner(["/opt/homebrew/bin/gh", "api", ref_endpoint], cwd=repo, capture_output=True, text=True)
    if read_ref.returncode:
        created = command_runner(
            ["/opt/homebrew/bin/gh", "api", "--method", "POST", f"repos/{repository}/git/refs", "-f", f"ref=refs/heads/{branch}", "-f", f"sha={head}"],
            cwd=repo, capture_output=True, text=True,
        )
        if created.returncode: return None, ["successor branch creation failed"]
    confirmed = command_runner(["/opt/homebrew/bin/gh", "api", ref_endpoint], cwd=repo, capture_output=True, text=True)
    try: remote_head = ((json.loads(confirmed.stdout).get("object") or {}).get("sha"))
    except json.JSONDecodeError: remote_head = None
    if confirmed.returncode or remote_head != head: return None, ["successor branch read-back mismatch"]
    listed = command_runner(
        ["/opt/homebrew/bin/gh", "pr", "list", "--repo", repository, "--head", branch, "--state", "all", "--json", "number,state,isDraft,headRefName,baseRefName,url"],
        cwd=repo, capture_output=True, text=True,
    )
    try: prs = json.loads(listed.stdout) if not listed.returncode else []
    except json.JSONDecodeError: prs = []
    if prs:
        pr = prs[0]
    else:
        made = command_runner(
            ["/opt/homebrew/bin/gh", "pr", "create", "--repo", repository, "--base", "codex/issue-19-real-review", "--head", branch, "--draft", "--title", "Issue #8 後繼：Source Library R-004", "--body", "此 Draft PR 由既有 Pending Goal 在合法工作時段建立。它保留 Legacy PR #23、Round 8、Cycle 20 與累計預算，不合併、不啟用 Auto Merge，且不提升任何 Human Gate。"],
            cwd=repo, capture_output=True, text=True,
        )
        if made.returncode: return None, ["successor Draft PR creation failed"]
        number = int(made.stdout.strip().rstrip("/").split("/")[-1])
        viewed = command_runner(["/opt/homebrew/bin/gh", "pr", "view", str(number), "--repo", repository, "--json", "number,state,isDraft,headRefName,baseRefName,url"], cwd=repo, capture_output=True, text=True)
        try: pr = json.loads(viewed.stdout)
        except json.JSONDecodeError: return None, ["successor Draft PR read-back is invalid"]
    if pr.get("state") != "OPEN" or pr.get("isDraft") is not True or pr.get("headRefName") != branch or pr.get("baseRefName") != "codex/issue-19-real-review":
        return None, ["successor Draft PR identity mismatch"]
    deadline = current.replace(hour=18, minute=0, second=0, microsecond=0)
    worktree = "/home/kgnote/.local/share/kgnote/source-library-successor-20261019"
    event_id = "source-library-successor-codex-20261019" if successor_cycle == 1 else f"source-library-successor-codex-20261019-cycle-{successor_cycle:02d}"
    checkpoint_name = "successor-codex-route.json" if successor_cycle == 1 else f"successor-codex-route-cycle-{successor_cycle:02d}.json"
    checkpoint = repo / "output/control-plane/production-runner" / checkpoint_name
    prompt = (
        "Resume the owner-authorized KGnote successor goal. Preserve Legacy PR #23, External Round 8 review 5561321715, "
        "finding-r-004, Cycle 20, supplemental usage 15/17, the cutover epoch, and every human gate. "
        "Work only on the inherited finding-r-004 and necessary tests. Do not merge, push, use paid APIs, or modify main. "
        "Read AGENTS.md, PLAN.md, CODEX_STATUS.md and repository authority before editing. Inspect PR #26 and the inherited "
        "finding-r-004 evidence, implement only the bounded R-004 repair still required, run targeted tests, and create a local "
        "checkpoint commit if candidate bytes change. Do not push; checkpoint resumable state before exit."
    )
    review_result = pending.get("review_result", {})
    if isinstance(review_result, dict) and review_result.get("verdict") == "CHANGES_REQUIRED":
        prompt += " Repair every accepted Claude finding below without dropping or weakening any item: " + json.dumps(review_result.get("findings", []), ensure_ascii=False)
    order = {
        "schema_version": ORDER_SCHEMA,
        "event_id": event_id, "stage": "codex",
        "working_directory": worktree,
        "command": [
            "/home/kgnote/.local/bin/kgnote-successor-codex",
            "--goal-id", goal_id, "--pull-request", str(pr["number"]), "--cycle", str(successor_cycle),
            repository, branch, head, prompt,
        ],
        "checkpoint_path": str(checkpoint), "memory_max": "4G", "tasks_max": 192,
        "timeout_seconds": max(1, min(3600, int((deadline-current).total_seconds()))),
        "lease_timeout_seconds": 8, "deadline_at": deadline.isoformat(),
        "bootstrap_working_directory": True,
        "execution_context": configured_execution_context(
            "CODEX_IMPLEMENTER", pull_request=int(pr["number"]), cycle=successor_cycle
        ),
        "review_admission": {
            "repository": repository, "pull_request": pr["number"], "head_sha": head,
            "candidate_fingerprint": str((published or {}).get("fingerprint") or legacy.get("candidate_fingerprint", "")),
            "review_round": 9,
            "authority": {"status":"APPROVED", "goal_id":goal_id, "authority_record":str(pending.get("authority", {}).get("source", "owner instruction"))},
            "budget": {"authorized": int((pending["continuous_budget"]["claude_product_reviews"])["authorized"]), "used": int((pending["continuous_budget"]["claude_product_reviews"])["used"])},
            "work_window_allowed": True, "stop_marker_clear": True,
            "existing_exact_candidate_result": False,
        },
    }
    order_path = repo / SUCCESSOR_ORDER; atomic_json(order_path, order)
    handoff = {
        "schema_version": "kgnote.successor-handoff.v1", "goal_id": goal_id,
        "status": "DISPATCH_READY", "repository": repository, "legacy_pr": 23,
        "successor_pr": pr["number"], "successor_pr_url": pr["url"], "branch": branch,
        "inherited_head": head, "review_round": 8, "cycle": 20,
        "cutover_epoch": pending.get("cutover_epoch"), "order_path": str(order_path),
        "deadline_at": deadline.isoformat(), "human_gates_preserved": True,
    }
    atomic_json(repo / SUCCESSOR_HANDOFF, handoff)
    pending.update({"status":"ACTIVATING", "new_product_pr_created":True, "successor_pull_request":pr["number"], "successor_branch":branch})
    write_pending(pending_path, pending)
    return order_path, []

def in_window(envelope: dict[str, object], current: datetime | None = None) -> bool:
    current, window = current or datetime.now(ZONE), envelope.get("work_window", {})
    if not isinstance(window, dict) or window.get("timezone") != "Asia/Taipei": return False
    # Production product work is weekday-only.  The hard 18:00 ceiling is an
    # execution safety boundary even when an older envelope still says 18:30.
    if current.weekday() >= 5:
        return False
    try:
        sh, sm = map(int, str(window["start"]).split(":")); eh, em = map(int, str(window["end"]).split(":"))
    except (KeyError, ValueError): return False
    end = min(eh * 60 + em, 18 * 60)
    minute = current.hour * 60 + current.minute
    return sh * 60 + sm <= minute < end

def envelope_errors(envelope: dict[str, object], state: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if envelope.get("schema_version") != "kgnote.work-package-envelope.v1": errors.append("unsupported envelope schema")
    if envelope.get("status") != "APPROVED": errors.append("work package is not approved")
    approval = envelope.get("approval", {})
    if not isinstance(approval, dict) or approval.get("source_status") != "RECONCILING" or not approval.get("receipt"):
        errors.append("pre-seal reconciliation approval receipt is missing")
    if envelope.get("goal_id") != state.get("active_goal"): errors.append("goal identity mismatch")
    if envelope.get("work_package_id") != state.get("work_package"): errors.append("work package identity mismatch")
    if not envelope.get("authority_record"): errors.append("authority record is missing")
    budgets = envelope.get("budgets", {})
    if not isinstance(budgets, dict): return errors + ["budgets must be an object"]
    for name in ("local_repairs", "internal_reviews", "external_reviews"):
        item = budgets.get(name, {})
        if not isinstance(item, dict): errors.append(f"{name} is invalid"); continue
        authorized, used = item.get("authorized"), item.get("used")
        if isinstance(authorized, bool) or not isinstance(authorized, int) or authorized < 0: errors.append(f"{name}.authorized is invalid")
        if isinstance(used, bool) or not isinstance(used, int) or used < 0: errors.append(f"{name}.used is invalid")
        if isinstance(authorized, int) and isinstance(used, int) and used > authorized: errors.append(f"{name} exceeds authorization")
    return errors

def route_order(
    repo: Path,
    router: Path,
    order_path: Path,
    command_runner=subprocess.run,
) -> int:
    if not router.is_file():
        append("linux_router_rejected", reason="router_missing", router=str(router))
        return 2
    probe = command_runner(
        ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes", "-o", "ConnectTimeout=5", "kgnote-ubuntu", "/usr/bin/true"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        append("linux_router_rejected", reason="guest_unavailable", exit_code=probe.returncode)
        return 2
    command = [sys.executable, str(router), "--order", str(order_path)]
    completed = command_runner(command, cwd=repo, capture_output=True, text=True)
    append(
        "linux_router_completed",
        order=str(order_path),
        exit_code=completed.returncode,
        output_tail=(completed.stdout or "")[-1000:],
        error_tail=(completed.stderr or "")[-1000:],
    )
    return completed.returncode


def _block_work_item(
    pending: dict[str, object], item: dict[str, object], *, reason: str,
    failure_class: str = "DETERMINISTIC_WORKER_FAILURE",
) -> None:
    item["status"] = "WORK_ITEM_BLOCKED"
    item["blocked_reason"] = reason
    pending["runner_status"] = "WORK_ITEM_BLOCKED"
    pending["runtime_block"] = {
        "failure_class": failure_class, "retry_blocked": True, "reason": reason,
        "blocked_at": datetime.now(ZONE).isoformat(timespec="seconds"),
        "work_item_id": item.get("work_item_id"),
    }
    scheduler = pending.setdefault("scheduler", {})
    if isinstance(scheduler, dict):
        scheduler["status"] = "WORK_ITEM_BLOCKED"
        blocks = scheduler.setdefault("blocks", [])
        if isinstance(blocks, list):
            blocks.append(blocking_record(
                "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason=reason,
                affected_work=[str(item.get("work_item_id"))],
                release_condition="the recorded failure is resolved under existing authority",
                next_legal_action="preserve the checkpoint and do not redispatch",
            ))


def _default_trusted_publish(
    item: dict[str, object], order: dict[str, object], guest_head: str, dirty: list[str],
    command_runner=subprocess.run,
) -> dict[str, object]:
    if not dirty:
        return {"status": "ALREADY_COMMITTED", "commit": guest_head}
    request_path = item.get("publisher_request_path")
    publisher = INTEGRATION_REPO / "scripts/trusted_candidate_publisher.py"
    if not isinstance(request_path, str) or not request_path or not publisher.is_file():
        raise RuntimeError("trusted Publisher request is missing for dirty worker result")
    completed = command_runner(
        [sys.executable, str(publisher), "--request", request_path],
        capture_output=True, text=True,
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "trusted Publisher rejected candidate")[-1000:])
    result = json.loads(completed.stdout)
    if result.get("status") != "COMMITTED_LOCAL_ONLY":
        raise RuntimeError("trusted Publisher returned an unexpected status")
    return result


def _historical_manual_publication(
    repo: Path, item: dict[str, object], order: dict[str, object], remote_head: str,
    command_runner=subprocess.run,
) -> dict[str, object] | None:
    """Validate, but do not upgrade, the bounded pre-M1 manual Issue publication."""
    receipt = item.get("dispatch_receipt", {})
    admission_receipt = item.get("admission_receipt", {})
    if not isinstance(receipt, dict) or not isinstance(admission_receipt, dict):
        return None
    candidate = receipt.get("candidate_head")
    product = receipt.get("trusted_product_commit")
    route_checkpoint = receipt.get("route_checkpoint")
    evidence_value = receipt.get("verification_evidence")
    worktree_value = admission_receipt.get("worktree")
    commit_ids = (candidate, product, remote_head)
    if (
        receipt.get("route_status") != "COMPLETED"
        or receipt.get("event_id") != order.get("event_id")
        or not all(isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value) for value in commit_ids)
        or not isinstance(route_checkpoint, str)
        or not isinstance(evidence_value, str)
        or not isinstance(worktree_value, str)
    ):
        return None
    expected_checkpoint = Path(str(order.get("checkpoint_path", ""))).resolve()
    recorded_checkpoint = Path(route_checkpoint)
    if not recorded_checkpoint.is_absolute():
        recorded_checkpoint = repo / recorded_checkpoint
    if recorded_checkpoint.resolve() != expected_checkpoint:
        return None
    worktree = Path(os.path.expandvars(os.path.expanduser(worktree_value))).resolve()
    evidence_path = Path(evidence_value)
    if not evidence_path.is_absolute():
        evidence_path = worktree / evidence_path
    evidence_path = evidence_path.resolve()
    if not evidence_path.is_relative_to(worktree):
        return None
    try:
        evidence = load(evidence_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if evidence.get("result") != "pass" or evidence.get("evidence_readback") is not True:
        return None
    local_head = command_runner(
        ["/usr/bin/git", "-C", str(worktree), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    local_dirty = command_runner(
        ["/usr/bin/git", "-C", str(worktree), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if local_head.returncode or local_dirty.returncode or local_head.stdout.strip() != remote_head or local_dirty.stdout.strip():
        return None
    for ancestor in (candidate, product):
        check = command_runner(
            ["/usr/bin/git", "-C", str(worktree), "merge-base", "--is-ancestor", str(ancestor), remote_head],
            capture_output=True, text=True,
        )
        if check.returncode:
            return None
    return {
        "status": "HISTORICAL_MANUAL_PUBLICATION_OBSERVED",
        "commit": remote_head,
        "d3_verified": False,
        "candidate_head": candidate,
        "trusted_product_commit": product,
        "verification_evidence": evidence_value,
    }


def consume_dispatched_checkpoints(
    repo: Path, pending_path: Path, pending: dict[str, object], *,
    command_runner=subprocess.run, publisher=None, pusher=None,
) -> bool:
    """Consume existing worker checkpoints once, without re-routing model work."""
    queue = pending.get("ready_queue", [])
    if not isinstance(queue, list):
        return False
    consumed = pending.setdefault("consumed_ready_work_events", [])
    if not isinstance(consumed, list):
        consumed = []
        pending["consumed_ready_work_events"] = consumed
    for item in queue:
        recoverable_historical_block = (
            isinstance(item, dict)
            and item.get("status") == "WORK_ITEM_BLOCKED"
            and item.get("blocked_reason") == "trusted Publisher rejected candidate: trusted Publisher request is missing for dirty worker result"
            and isinstance(item.get("dispatch_receipt"), dict)
        )
        if not isinstance(item, dict) or (
            item.get("status") not in {"DISPATCHING", "DISPATCHED"}
            and not recoverable_historical_block
        ):
            continue
        order_value = item.get("order_path")
        order_path = Path(str(order_value))
        if not order_path.is_absolute():
            order_path = repo / order_path
        try:
            order = load(order_path)
            checkpoint_path = Path(str(order["checkpoint_path"]))
            checkpoint = load(checkpoint_path)
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            _block_work_item(pending, item, reason=f"worker checkpoint is unavailable: {exc}")
            write_pending(pending_path, pending)
            return True
        event_id = str(order.get("event_id", ""))
        if event_id in consumed:
            item["status"] = "WORKER_COMPLETED"
            pending["runner_status"] = "WORKER_COMPLETED"
            write_pending(pending_path, pending)
            return True
        status = str(checkpoint.get("status", ""))
        if status == "RUNNING":
            pending["runner_status"] = "DISPATCHED"
            pending["scheduler"] = {
                "status": "DISPATCHED", "selected_work_item": item.get("work_item_id"),
                "blocks": [blocking_record(
                    "WORK_ITEM_WAITING", scope="WORK_ITEM", reason="existing worker checkpoint is RUNNING",
                    affected_work=[str(item.get("work_item_id"))],
                    release_condition="the exact checkpoint reaches a terminal state",
                    next_legal_action="wait without invoking the router",
                )],
            }
            write_pending(pending_path, pending)
            return True
        identity_matches = (
            checkpoint.get("event_id") == event_id
            and checkpoint.get("command_digest") == worker_command_digest(order)
        )
        if not identity_matches:
            _block_work_item(pending, item, reason="worker checkpoint event_id or command_digest mismatch")
            write_pending(pending_path, pending)
            return True
        if status in {"FAILED_CLOSED", "BLOCKED"} or checkpoint.get("reason") == "quota_exhausted":
            failure_class, reason = route_failure(checkpoint, int(checkpoint.get("exit_code") or 2))
            _block_work_item(pending, item, reason=reason, failure_class=failure_class)
            write_pending(pending_path, pending)
            return True
        if status not in {"COMPLETED", "ALREADY_COMPLETED"}:
            _block_work_item(pending, item, reason=f"unsupported worker checkpoint status: {status}")
            write_pending(pending_path, pending)
            return True
        worktree = str(order.get("working_directory", ""))
        probe = command_runner(
            ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes", "kgnote-ubuntu",
             f"/usr/bin/git -C {worktree} rev-parse HEAD && /usr/bin/git -C {worktree} status --porcelain"],
            cwd=repo, capture_output=True, text=True,
        )
        lines = (probe.stdout or "").splitlines()
        if probe.returncode or not lines:
            _block_work_item(pending, item, reason="read-only Ubuntu candidate identity probe failed")
            write_pending(pending_path, pending)
            return True
        guest_head, dirty = lines[0], lines[1:]
        admission = item.get("admission", {})
        receipt = item.get("admission_receipt", {})
        admission = admission if isinstance(admission, dict) else {}
        receipt = receipt if isinstance(receipt, dict) else {}
        repository, pull_request = admission.get("repository"), receipt.get("pull_request")
        remote = command_runner(
            ["/opt/homebrew/bin/gh", "pr", "view", str(pull_request), "--repo", str(repository),
             "--json", "headRefOid"], cwd=repo, capture_output=True, text=True,
        )
        try:
            remote_head = json.loads(remote.stdout).get("headRefOid")
        except (json.JSONDecodeError, AttributeError):
            remote_head = None
        if remote.returncode or not isinstance(remote_head, str):
            _block_work_item(pending, item, reason="pull request HEAD read-back failed")
            write_pending(pending_path, pending)
            return True
        try:
            historical = _historical_manual_publication(
                repo, item, order, remote_head, command_runner,
            ) if dirty else None
            publication = (
                {"status": "ALREADY_PUBLISHED", "commit": guest_head}
                if not dirty and remote_head == guest_head
                else historical or (publisher or _default_trusted_publish)(item, order, guest_head, dirty, command_runner)
            )
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            _block_work_item(pending, item, reason=f"trusted Publisher rejected candidate: {exc}")
            write_pending(pending_path, pending)
            return True
        committed = str(publication.get("commit") or guest_head)
        if remote_head != committed:
            try:
                if pusher is None:
                    raise RuntimeError("authorized push-order callback is unavailable")
                pusher(item, order, committed, command_runner)
                remote = command_runner(
                    ["/opt/homebrew/bin/gh", "pr", "view", str(pull_request), "--repo", str(repository),
                     "--json", "headRefOid"], cwd=repo, capture_output=True, text=True,
                )
                remote_head = json.loads(remote.stdout).get("headRefOid") if not remote.returncode else None
                if remote_head != committed:
                    raise RuntimeError("push-order PR HEAD read-back mismatch")
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError, AttributeError) as exc:
                _block_work_item(
                    pending, item,
                    reason=f"trusted publication push/read-back failed: {exc}",
                )
                write_pending(pending_path, pending)
                return True
        consumed.append(event_id)
        item["status"] = "WORKER_COMPLETED"
        item.pop("blocked_reason", None)
        item["checkpoint_consumption"] = {
            "event_id": event_id, "command_digest": checkpoint.get("command_digest"),
            "worker_head": guest_head, "published_head": remote_head,
            "publication_status": publication.get("status"),
            "d3_verified": publication.get("d3_verified"),
            "consumed_at": datetime.now(ZONE).isoformat(timespec="seconds"),
        }
        pending["runner_status"] = "WORKER_COMPLETED"
        pending["scheduler"] = {"status": "WORKER_COMPLETED", "selected_work_item": item.get("work_item_id"), "blocks": []}
        runtime_block = pending.get("runtime_block")
        if isinstance(runtime_block, dict) and runtime_block.get("work_item_id") == item.get("work_item_id"):
            resolved = pending.pop("runtime_block")
            resolved.update({
                "retry_blocked": False,
                "resolved_at": datetime.now(ZONE).isoformat(timespec="seconds"),
                "resolution": "validated the bounded historical manual publication receipt without redispatch",
            })
            pending.setdefault("resolved_runtime_blocks", []).append(resolved)
        write_pending(pending_path, pending)
        append("independent_ready_work_checkpoint_consumed", work_item_id=item.get("work_item_id"), event_id=event_id, head=remote_head)
        return True
    return False


def route_next_ready_work(
    repo: Path,
    pending_path: Path,
    pending: dict[str, object],
    current: datetime,
    *,
    stop_marker_present: bool,
    router: Path,
    epoch_record: Path,
    admission: Path,
    command_runner=subprocess.run,
) -> int:
    """Persist a scheduler decision and dispatch only a pre-sealed legal order."""
    queue = pending.get("ready_queue", [])
    states = pending.get("work_item_states", {})
    states = states if isinstance(states, dict) else {}
    if isinstance(queue, list):
        for raw in queue:
            if not isinstance(raw, dict) or raw.get("status") != "ADMISSION_PENDING":
                continue
            dependencies = raw.get("dependencies", [])
            dependencies = dependencies if isinstance(dependencies, list) else []
            missing = [str(dep) for dep in dependencies if states.get(str(dep)) != "COMPLETE"]
            if missing:
                pending["runner_status"] = "NO_ELIGIBLE_READY_WORK"
                pending["scheduler"] = {
                    "status":"NO_ELIGIBLE_READY_WORK",
                    "selected_work_item":None,
                    "blocks":[blocking_record(
                        "DEPENDENCY_BLOCKED", scope="DEPENDENCY_SUBGRAPH",
                        reason=f"unfinished dependencies: {missing}",
                        affected_work=[str(raw.get("work_item_id")), *missing],
                        release_condition="every named dependency reaches COMPLETE without bypassing its gates",
                        next_legal_action="leave the Issue admission pending",
                    )],
                }
                record_scheduler_runtime(current, "NO_ELIGIBLE_READY_WORK", None)
                write_pending(pending_path,pending)
                apply_queue_label(pending, "DEPENDENCY_BLOCKED", item=raw, command_runner=command_runner)
                return 0
            try:
                receipt = cross_issue_admission.prepare(repo, raw, current, runner=command_runner)
            except cross_issue_admission.AdmissionError as exc:
                pending["runner_status"] = "NO_ELIGIBLE_READY_WORK"
                pending["scheduler"] = {
                    "status":"NO_ELIGIBLE_READY_WORK",
                    "selected_work_item":None,
                    "blocks":[blocking_record(
                        "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason=f"cross-Issue admission rejected: {exc}",
                        affected_work=[str(raw.get("work_item_id"))],
                        release_condition="the existing authority, permission, isolation and sealed identity all validate",
                        next_legal_action="preserve the pending admission; do not invent or broaden authority",
                    )],
                }
                record_scheduler_runtime(current, "NO_ELIGIBLE_READY_WORK", None)
                write_pending(pending_path,pending)
                apply_queue_label(pending, "WORK_ITEM_BLOCKED", item=raw, command_runner=command_runner)
                return 0
            raw.update({
                "status":"READY", "order_path":receipt["order_path"],
                "admission_receipt":receipt,
            })
            write_pending(pending_path,pending)
            append("cross_issue_admission_ready",work_item_id=raw.get("work_item_id"),receipt=receipt)
            break
    if consume_dispatched_checkpoints(
        repo, pending_path, pending, command_runner=command_runner,
    ):
        current_pending = load(pending_path)
        queue_now = current_pending.get("ready_queue", [])
        selected_now = next((entry for entry in queue_now if isinstance(entry, dict) and entry.get("work_item_id") == current_pending.get("scheduler", {}).get("selected_work_item")), None) if isinstance(queue_now, list) and isinstance(current_pending.get("scheduler"), dict) else None
        runner_status = str(current_pending.get("runner_status"))
        if runner_status in QUEUE_PROJECTION_STATES:
            apply_queue_label(current_pending, runner_status, item=selected_now, command_runner=command_runner)
        return 0 if current_pending.get("runner_status") in {"DISPATCHED", "WORKER_COMPLETED"} else 2
    decision = select_ready_work(pending, current, stop_marker_present=stop_marker_present)
    pending["scheduler"] = {
        "status": decision["status"],
        "selected_work_item": (
            decision["selected"].get("work_item_id")
            if isinstance(decision.get("selected"), dict) else None
        ),
        "blocks": decision["blocks"],
    }
    record_scheduler_runtime(
        current, str(decision["status"]),
        pending["scheduler"]["selected_work_item"] if isinstance(pending.get("scheduler"), dict) else None,
    )
    if decision["status"] != "DISPATCH_READY":
        pending["runner_status"] = decision["status"]
        write_pending(pending_path, pending)
        label_status = scheduler_projection_status(pending, decision)
        if label_status is not None:
            apply_queue_label(pending, label_status, command_runner=command_runner, current=current)
        append("ready_work_selection_idle", status=decision["status"], blocks=decision["blocks"])
        return 0

    selected = decision["selected"]
    assert isinstance(selected, dict)
    order_value = selected.get("order_path")
    order_path = Path(str(order_value))
    if not order_path.is_absolute():
        order_path = repo / order_path
    try:
        order_path.resolve().relative_to(repo.resolve())
    except ValueError:
        pending["runner_status"] = "WORK_ITEM_BLOCKED"
        pending["scheduler"]["blocks"].append(blocking_record(
            "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="worker order is outside the repository evidence root",
            affected_work=[str(selected.get("work_item_id"))],
            release_condition="bind the item to a repository-owned sealed order",
            next_legal_action="do not dispatch the external path",
        ))
        write_pending(pending_path, pending)
        apply_queue_label(pending, "WORK_ITEM_BLOCKED", item=selected, command_runner=command_runner)
        return 2
    if not order_path.is_file() or not epoch_record.is_file() or not admission.is_file():
        pending["runner_status"] = "WORK_ITEM_BLOCKED"
        pending["scheduler"]["blocks"].append(blocking_record(
            "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="sealed order or epoch admission gate is unavailable",
            affected_work=[str(selected.get("work_item_id"))],
            release_condition="restore the existing sealed order and epoch admission files",
            next_legal_action="remain idle without creating replacement work",
        ))
        write_pending(pending_path, pending)
        apply_queue_label(pending, "WORK_ITEM_BLOCKED", item=selected, command_runner=command_runner)
        return 2
    gate = command_runner(
        [sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order_path)],
        cwd=repo, capture_output=True, text=True,
    )
    if gate.returncode:
        pending["runner_status"] = "WORK_ITEM_BLOCKED"
        pending["scheduler"]["blocks"].append(blocking_record(
            "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="epoch/scope admission rejected the sealed order",
            affected_work=[str(selected.get("work_item_id"))],
            release_condition="the existing admission gate accepts the exact order",
            next_legal_action="preserve the rejection and do not bypass admission",
        ))
        write_pending(pending_path, pending)
        apply_queue_label(pending, "WORK_ITEM_BLOCKED", item=selected, command_runner=command_runner)
        return 2
    # Reserve the sole implementation dispatch before any external model can
    # start. A route failure is still an attempted dispatch and must not make a
    # second paid/model-bearing attempt appear authorized after restart.
    budget = selected["budget"]
    budget["used"] = int(budget["used"]) + 1
    selected["status"] = "DISPATCHING"
    pending["runner_status"] = "DISPATCHING"
    pending["scheduler"]["status"] = "DISPATCHING"
    write_pending(pending_path, pending)
    result = route_order(repo, router, order_path, command_runner)
    if result:
        try:
            checkpoint = load(Path(str(load(order_path).get("checkpoint_path"))))
        except (OSError, ValueError, json.JSONDecodeError):
            checkpoint = {}
        failure_class, reason = route_failure(checkpoint, result)
        if failure_class == "QUOTA_EXHAUSTED":
            budget["used"] = max(0, int(budget["used"]) - 1)
        _block_work_item(pending, selected, reason=reason, failure_class=failure_class)
        write_pending(pending_path, pending)
        apply_queue_label(pending, "WORK_ITEM_BLOCKED", item=selected, command_runner=command_runner)
        return result
    selected["status"] = "DISPATCHED"
    pending["runner_status"] = "DISPATCHED"
    pending["scheduler"]["status"] = "DISPATCHED"
    write_pending(pending_path, pending)
    append("independent_ready_work_dispatched", work_item_id=selected.get("work_item_id"), order=str(order_path))
    return 0


def idle_health_order(repo: Path) -> Path:
    path = OUT / "linux-idle-health-order.json"
    value = {
        "schema_version": ORDER_SCHEMA,
        "event_id": "production-idle-health-v2",
        "stage": "ingestion",
        "working_directory": "/home/kgnote/.local/share/kgnote",
        "command": ["/usr/bin/true"],
        "checkpoint_path": str(OUT / "linux-idle-health-checkpoint.json"),
        "memory_max": "128M",
        "tasks_max": 16,
        "timeout_seconds": 30,
        "lease_timeout_seconds": 8,
    }
    if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != value:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_canary_order(path: Path) -> None:
    value = load(path)
    if not str(value.get("event_id", "")).startswith("production-canary-"):
        raise ValueError("canary event_id is not allowlisted")
    if value.get("working_directory") != "/home/kgnote/.local/share/kgnote/smoke-repo":
        raise ValueError("canary worktree is not the private smoke repository")
    checkpoint = Path(str(value.get("checkpoint_path", "")))
    allowed = INTEGRATION_REPO / "output/claude-reviewer-final"
    if not checkpoint.is_absolute() or not checkpoint.is_relative_to(allowed):
        raise ValueError("canary checkpoint is outside the integration evidence root")


def run_once(
    repo: Path = REPO,
    current: datetime | None = None,
    command_runner=subprocess.run,
    router: Path = DEFAULT_ROUTER,
    canary_order: Path | None = None,
    epoch_record: Path = DEFAULT_EPOCH,
    admission: Path = DEFAULT_ADMISSION,
    pending_goal: Path = DEFAULT_PENDING,
    runner_identity: dict[str, object] | None = None,
) -> int:
    global OUT, LOCK, LOG, RUNNER_EVENT_IDENTITY
    OUT = repo / "output/control-plane/production-runner"; LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    RUNNER_EVENT_IDENTITY = dict(runner_identity or {})
    OUT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock_handle:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: append("writer_lock_blocked"); return 0
        append("runner_tick_started")
        if runner_identity and runner_identity.get("runner_code_dirty") is not False:
            append("runner_code_dirty_idle")
            return 0
        try:
            state = load(repo / ".ai/ORCHESTRATOR_STATE.json"); envelope = load(repo / ".ai/work-package-envelope.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc: append("configuration_rejected", reason=str(exc)); return 2
        if (repo / STOP_MARKER).exists():
            pending: dict[str, object] = {}
            try: pending = load(pending_goal)
            except (OSError, ValueError, json.JSONDecodeError): pass
            transition_now = current or datetime.now(ZONE)
            runtime_block = pending.get("runtime_block", {}) if isinstance(pending, dict) else {}
            last_codex = pending.get("last_codex_result", {}) if isinstance(pending, dict) else {}
            legacy_identity = pending.get("legacy_inheritance", {}) if isinstance(pending, dict) else {}
            if pending.get("status") in {
                "HUMAN_CHECKPOINT_REQUIRED",  # superseded input migration
                "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
            } or (
                pending.get("status") == "WORK_ITEM_BLOCKED"
                and isinstance(pending.get("review_result"), dict)
                and pending["review_result"].get("verdict") == "PASS"
                and pending["review_result"].get("consistency_audited") is not True
            ):
                consistency_error, previous_review = persisted_review_progression_error(pending, OUT)
                if consistency_error:
                    pending["status"] = "WORK_ITEM_BLOCKED"
                    pending["work_item_block"] = blocking_record(
                        "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason=consistency_error,
                        affected_work=[str(pending.get("goal_id", SUCCESSOR_GOAL)), "PR-26"],
                        release_condition="a changed exact candidate or structured new evidence resolves every prior blocking finding",
                        next_legal_action="preserve the prior findings; do not call Claude repeatedly or enter human acceptance",
                    )
                    review_result = pending.get("review_result", {})
                    if isinstance(review_result, dict):
                        review_result["routing_accepted"] = False
                        review_result["consistency_error"] = consistency_error
                        review_result["consistency_audited"] = True
                        review_result["preserved_blocking_findings"] = previous_review.get("findings", []) if isinstance(previous_review, dict) else []
                else:
                    pending["status"] = status_after_component_pass(pending)
                write_pending(pending_goal, pending)
                if pending["status"] in {"WORK_ITEM_BLOCKED", "FINAL_HUMAN_ACCEPTANCE_REQUIRED", "PRODUCT_DECISION_REQUIRED"}:
                    apply_queue_label(pending, str(pending["status"]), command_runner=command_runner)
                append("legacy_human_checkpoint_scope_reconciled", status=pending["status"], consistency_error=consistency_error)
            canonical_relay_pending = (
                pending.get("status") == "WORK_ITEM_BLOCKED"
                and isinstance(pending.get("review_result"), dict)
                and not isinstance(pending["review_result"].get("canonical_record"), dict)
                and isinstance(pending.get("work_item_block"), dict)
                and "canonical GitHub" in str(pending["work_item_block"].get("reason", ""))
            )
            review_result_for_receipt = pending.get("review_result", {})
            work_item_states = pending.setdefault("work_item_states", {})
            if (pending.get("status") == "COMPONENT_REVIEW_COMPLETE"
                    and isinstance(pending.get("delivery_receipt"), dict)
                    and work_item_states.get("PR-26") == "COMPLETE"):
                work_item_states["PR-26"] = "CANDIDATE_VERIFIED_INTEGRATION_PENDING"
                write_pending(pending_goal, pending)
                append("successor_integration_dependency_preserved",
                       reason="PR #22 and PR #26 remain open Draft pull requests")
            if (pending.get("status") == "COMPONENT_REVIEW_COMPLETE"
                    and isinstance(review_result_for_receipt, dict)
                    and isinstance(review_result_for_receipt.get("canonical_record"), dict)
                    and not isinstance(pending.get("delivery_receipt"), dict)):
                try:
                    pending["delivery_receipt"] = record_issue8_completion_receipt(
                        pending, review_result_for_receipt["canonical_record"],
                        command_runner=command_runner,
                    )
                except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                    append("successor_delivery_receipt_blocked", reason=str(exc))
                    return 2
                pending.setdefault("work_item_states", {})["PR-26"] = "CANDIDATE_VERIFIED_INTEGRATION_PENDING"
                write_pending(pending_goal, pending)
                append("successor_delivery_receipt_accepted",
                       issue_comment_url=pending["delivery_receipt"].get("issue_comment_url"))
            if (pending.get("status") in WORK_ITEM_PAUSED | {"COMPONENT_REVIEW_COMPLETE"}
                    and not canonical_relay_pending):
                review_result = pending.get("review_result", {})
                if (pending.get("status") == "COMPONENT_REVIEW_COMPLETE"
                        and isinstance(review_result, dict)
                        and review_result.get("canonical_record") is None):
                    pending["status"] = "WORK_ITEM_BLOCKED"
                    pending["work_item_block"] = blocking_record(
                        "WORK_ITEM_BLOCKED", scope="WORK_ITEM",
                        reason=("validated reviewer output has no canonical GitHub review artifact; "
                                "a local round number is not a GitHub record ID"),
                        affected_work=[str(pending.get("goal_id", SUCCESSOR_GOAL)), "PR-26"],
                        release_condition=("an authorized Publisher writes the exact result and the canonical "
                                           "Consumer reads back its GitHub ID, URL, author, time and body digest"),
                        next_legal_action=("preserve Round 5 and obtain compatible external-review/writeback "
                                           "authority; do not dispatch another reviewer round"),
                    )
                    write_pending(pending_goal, pending)
                    apply_queue_label(pending, "WORK_ITEM_BLOCKED", command_runner=command_runner)
                    append("successor_review_missing_canonical_github_artifact")
                    return 0
                if pending.get("status") in QUEUE_PROJECTION_STATES:
                    apply_queue_label(pending, str(pending["status"]), command_runner=command_runner)
                return route_next_ready_work(
                    repo, pending_goal, pending, transition_now,
                    stop_marker_present=True, router=router, epoch_record=epoch_record,
                    admission=admission, command_runner=command_runner,
                )
            candidate_ready = (
                isinstance(last_codex, dict)
                and last_codex.get("material_progress") is True
                and isinstance(legacy_identity, dict)
                and bool(last_codex.get("resulting_head"))
                and last_codex.get("resulting_head") != legacy_identity.get("head")
            )
            review_result = pending.get("review_result", {})
            work_block = pending.get("work_item_block", {})
            if (canary_order is None and pending.get("status") == "WORK_ITEM_BLOCKED"
                    and isinstance(review_result, dict) and review_result.get("verdict") in {
                        "PASS", "CHANGES_REQUIRED", "PRODUCT_DECISION_REQUIRED"
                    }
                    and not isinstance(review_result.get("canonical_record"), dict)
                    and isinstance(work_block, dict)
                    and "canonical GitHub" in str(work_block.get("reason", ""))):
                review_round = int(review_result.get("round", 0))
                event_path = OUT / f"successor-review-event-r{review_round}.json"
                config_path = OUT / f"successor-review-consumer-config-r{review_round}.json"
                consumer_checkpoint = OUT / f"successor-review-consumer-checkpoint-r{review_round}.json"
                if not event_path.is_file():
                    append("successor_review_writeback_blocked", reason="preserved review event is missing")
                    return 2
                atomic_json(config_path, {
                    "enabled": True, "result_marker": "kgnote-ai-product-review:v1",
                    "trusted_reviewer_author_login": "joannalee20050914",
                    "trusted_reviewer_identities": ["claude-code:ubuntu-review-only"],
                    "github_writeback_enabled": True,
                    "github_writeback_authorized_reviewer_identities": ["claude-code:ubuntu-review-only"],
                    "last_reviewed_candidate_fingerprint": None,
                })
                integration = CLAUDE_ADAPTER.parents[1]
                published = command_runner([
                    str(integration / ".venv/bin/python"),
                    str(integration / "scripts/claude_review_ingestion.py"),
                    "--event", str(event_path), "--config", str(config_path),
                    "--schema", str(integration / "schemas/product-review/v1/review-result.schema.json"),
                    "--checkpoint", str(consumer_checkpoint), "--github-writeback", "--cwd", str(repo),
                ], cwd=integration, capture_output=True, text=True)
                if published.returncode:
                    append("successor_review_writeback_blocked", output_tail=(published.stderr or "")[-2000:])
                    return 2
                decision = load(consumer_checkpoint)
                if (decision.get("product_review_accepted") is not True
                        or not isinstance(decision.get("canonical_record"), dict)):
                    append("successor_review_writeback_blocked", reason="canonical Consumer read-back absent")
                    return 2
                review_result["canonical_record"] = decision["canonical_record"]
                review_result["routing_accepted"] = True
                review_result["consumer_checkpoint"] = str(consumer_checkpoint)
                pending["review_result"] = review_result
                try:
                    pending["delivery_receipt"] = record_issue8_completion_receipt(
                        pending, decision["canonical_record"], command_runner=command_runner
                    )
                except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                    append("successor_delivery_receipt_blocked", reason=str(exc))
                    return 2
                pending.setdefault("work_item_states", {})["PR-26"] = "CANDIDATE_VERIFIED_INTEGRATION_PENDING"
                pending["status"] = status_after_component_pass(pending)
                pending.pop("work_item_block", None)
                write_pending(pending_goal, pending)
                append("successor_review_canonical_github_artifact_accepted",
                       record_id=decision["canonical_record"].get("record_id"),
                       artifact_url=decision["canonical_record"].get("artifact_url"))
                return route_next_ready_work(
                    repo, pending_goal, pending, transition_now,
                    stop_marker_present=True, router=router, epoch_record=epoch_record,
                    admission=admission, command_runner=command_runner,
                )
            if canary_order is None and pending.get("status") == "REVIEW_TRANSPORT_COMPLETE" and in_window({"work_window": pending.get("work_window", {})}, transition_now):
                active_review = pending.get("active_review", {}); review_round = int((active_review or {}).get("round", 0))
                remote_checkpoint = f"/home/kgnote/.local/share/kgnote/successor-review/adapter-checkpoint-r{review_round}.json"
                fetched = command_runner(["ssh", "kgnote-ubuntu", "/usr/bin/cat", remote_checkpoint], cwd=repo, capture_output=True, text=True)
                try: adapter_result = json.loads(fetched.stdout)
                except json.JSONDecodeError: adapter_result = {}
                review = adapter_result.get("review_result") if not fetched.returncode else None
                if adapter_result.get("status") != "COMPLETED" or not isinstance(review, dict):
                    append("successor_review_consumer_blocked", reason="adapter checkpoint missing exact review result"); return 2
                event_path = OUT / f"successor-review-event-r{review_round}.json"
                config_path = OUT / f"successor-review-consumer-config-r{review_round}.json"
                consumer_checkpoint = OUT / f"successor-review-consumer-checkpoint-r{review_round}.json"
                atomic_json(event_path, {
                    "event_id":f"successor-pr26-{active_review.get('identity_key')}", "status":"REVIEW_SUBMITTED",
                    "repository":"joannalee20050914/KGnote-public", "issue":8, "pull_request":26,
                    "program_id":"kgnote-source-library-successor-20261019", "goal_id":"GOAL-KGNOTE-SOURCE-LIBRARY-SUCCESSOR-20261019",
                    "candidate_commit":active_review.get("candidate_commit"), "candidate_fingerprint":active_review.get("candidate_fingerprint"),
                    "review_round":review_round, "cumulative_round_limit":int(pending["continuous_budget"]["claude_product_reviews"]["authorized"]),
                    "reviewer_identity":"claude-code:ubuntu-review-only", "review_scope":"KGNOTE_PRODUCT_CONTRACT", "record_id":review_round, "review":review,
                })
                atomic_json(config_path, {"enabled":True,"result_marker":"kgnote-ai-product-review:v1","trusted_reviewer_author_login":"claude-code-local","trusted_reviewer_identities":["claude-code:ubuntu-review-only"],"last_reviewed_candidate_fingerprint":None})
                integration = CLAUDE_ADAPTER.parents[1]
                consumed = command_runner([str(integration/".venv/bin/python"), str(integration/"scripts/claude_review_ingestion.py"), "--event", str(event_path), "--config", str(config_path), "--schema", str(integration/"schemas/product-review/v1/review-result.schema.json"), "--checkpoint", str(consumer_checkpoint)], cwd=integration, capture_output=True, text=True)
                if consumed.returncode: append("successor_review_consumer_blocked", output_tail=(consumed.stderr or "")[-2000:]); return 2
                decision = load(consumer_checkpoint); verdict = str(decision.get("validated_verdict", decision.get("status")))
                if decision.get("product_review_accepted") is not True or not isinstance(decision.get("canonical_record"), dict):
                    pending["status"] = "WORK_ITEM_BLOCKED"
                    pending["review_result"] = {
                        "verdict": verdict, "round": review_round,
                        "candidate_commit": active_review.get("candidate_commit"),
                        "candidate_fingerprint": active_review.get("candidate_fingerprint"),
                        "findings": decision.get("findings", []),
                        "consumer_checkpoint": str(consumer_checkpoint),
                        "canonical_record": None, "routing_accepted": False,
                    }
                    pending["work_item_block"] = blocking_record(
                        "WORK_ITEM_BLOCKED", scope="WORK_ITEM",
                        reason="review validated locally but canonical GitHub writeback is absent",
                        affected_work=[str(pending.get("goal_id", SUCCESSOR_GOAL)), "PR-26"],
                        release_condition="authorized GitHub writeback and canonical Consumer read-back",
                        next_legal_action="do not start another reviewer round",
                    )
                    write_pending(pending_goal, pending)
                    apply_queue_label(pending, "WORK_ITEM_BLOCKED", command_runner=command_runner)
                    append("successor_review_writeback_required", verdict=verdict, review_round=review_round)
                    return 0
                if verdict not in {"PASS","CHANGES_REQUIRED","PRODUCT_DECISION_REQUIRED"}: append("successor_review_consumer_blocked", reason=f"unexpected verdict {verdict}"); return 2
                previous_review: dict[str, object] | None = None
                previous_event = OUT / f"successor-review-event-r{review_round - 1}.json"
                if previous_event.is_file():
                    try:
                        previous_value = load(previous_event)
                        candidate_previous = previous_value.get("review")
                        if isinstance(candidate_previous, dict):
                            previous_review = candidate_previous
                    except (OSError, ValueError, json.JSONDecodeError):
                        previous_review = None
                consistency_error = review_progression_error(previous_review, review)
                pending["continuous_budget"]["claude_product_reviews"]["used"] = max(int(pending["continuous_budget"]["claude_product_reviews"]["used"]), review_round)
                prior_result = pending.get("review_result")
                history = pending.setdefault("review_history", [])
                if isinstance(history, list) and isinstance(prior_result, dict):
                    identity = (prior_result.get("round"), prior_result.get("candidate_commit"), prior_result.get("candidate_fingerprint"))
                    if not any(isinstance(item, dict) and (item.get("round"), item.get("candidate_commit"), item.get("candidate_fingerprint")) == identity for item in history):
                        history.append(prior_result)
                pending["review_result"]={
                    "verdict":verdict,"round":review_round,
                    "candidate_commit":active_review.get("candidate_commit"),
                    "candidate_fingerprint":active_review.get("candidate_fingerprint"),
                    "findings":decision.get("findings",[]),"consumer_checkpoint":str(consumer_checkpoint),
                    "canonical_record": decision.get("canonical_record"),
                    "accepted_at":datetime.now(ZONE).isoformat(timespec="seconds"),
                    "routing_accepted": consistency_error is None,
                    "consistency_error": consistency_error,
                    "consistency_audited": True,
                }
                if consistency_error:
                    prior_findings = previous_review.get("findings", []) if isinstance(previous_review, dict) else []
                    pending["status"] = "WORK_ITEM_BLOCKED"
                    pending["work_item_block"] = blocking_record(
                        "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason=consistency_error,
                        affected_work=[str(pending.get("goal_id", SUCCESSOR_GOAL)), "PR-26"],
                        release_condition="a changed exact candidate or structured new evidence resolves every prior blocking finding",
                        next_legal_action="preserve the prior findings; do not call Claude repeatedly or enter human acceptance",
                    )
                    pending["review_result"]["preserved_blocking_findings"] = prior_findings
                else:
                    pending["status"] = (
                        "ACTIVE" if verdict == "CHANGES_REQUIRED"
                        else status_after_component_pass(pending) if verdict == "PASS"
                        else "PRODUCT_DECISION_REQUIRED"
                    )
                if verdict == "CHANGES_REQUIRED": pending.pop("last_codex_result", None)
                write_pending(pending_goal,pending)
                if pending["status"] in {"WORK_ITEM_BLOCKED", "FINAL_HUMAN_ACCEPTANCE_REQUIRED", "PRODUCT_DECISION_REQUIRED"}:
                    apply_queue_label(pending, str(pending["status"]), command_runner=command_runner)
                append("successor_review_consumed", verdict=verdict, review_round=review_round, routing_accepted=consistency_error is None)
                if consistency_error or verdict in {"PASS", "PRODUCT_DECISION_REQUIRED"}:
                    return route_next_ready_work(
                        repo, pending_goal, pending, transition_now,
                        stop_marker_present=True, router=router, epoch_record=epoch_record,
                        admission=admission, command_runner=command_runner,
                    )
                return 0
            if canary_order is None and pending.get("status") == "PUBLISHED" and in_window({"work_window": pending.get("work_window", {})}, transition_now):
                published = pending.get("published_candidate", {})
                review_budget = (pending.get("continuous_budget") or {}).get("claude_product_reviews", {})
                candidate = str((published or {}).get("commit", "")); fingerprint = str((published or {}).get("fingerprint", ""))
                review_round = int((review_budget or {}).get("used", 0)) + 1
                review_key = hashlib.sha256(f"26\0{candidate}\0{fingerprint}\0{review_round}".encode()).hexdigest()
                repository = str((pending.get("scope") or {}).get("repository"))
                check = command_runner(["/opt/homebrew/bin/gh", "pr", "view", "26", "--repo", repository, "--json", "headRefOid"], cwd=repo, capture_output=True, text=True)
                try: github_head = json.loads(check.stdout).get("headRefOid")
                except json.JSONDecodeError: github_head = None
                if check.returncode or github_head != candidate:
                    append("successor_claude_head_rejected", expected=candidate, actual=github_head); return 2
                local_work = OUT / f"successor-claude-work-order-r{review_round}.json"
                remote_work = f"/home/kgnote/.local/share/kgnote/successor-review/successor-claude-work-order-r{review_round}.json"
                atomic_json(local_work, {
                    "goal_id":SUCCESSOR_GOAL, "repository":repository, "issue":8, "pull_request":26,
                    "candidate_commit":candidate, "candidate_fingerprint":fingerprint,
                    "review_round_used":review_round-1, "review_round_limit":review_round,
                    "timeout_seconds":1800,
                    "checkpoint_path":f"/home/kgnote/.local/share/kgnote/successor-review/adapter-checkpoint-r{review_round}.json",
                    "agent_loop":"/home/kgnote/.local/share/kgnote/coding-review-agent-loop/.venv/bin/agent-loop",
                    "agent_loop_checkout":"/home/kgnote/.local/share/kgnote/coding-review-agent-loop",
                    "claude_cmd":"/home/kgnote/.local/bin/claude", "codex_cmd":"/home/kgnote/.local/bin/codex",
                    "allow_live_write":False, "review_only_live":True, "safety_baseline_verified":True,
                    "requested_model":CLAUDE_MODEL, "requested_effort":CLAUDE_EFFORT,
                    "requested_provider":"Anthropic",
                })
                setup = command_runner(["ssh", "kgnote-ubuntu", "/usr/bin/mkdir", "-p", "/home/kgnote/.local/share/kgnote/successor-review"], cwd=repo, capture_output=True, text=True)
                copied = command_runner(["scp", str(local_work), f"kgnote-ubuntu:{remote_work}"], cwd=repo, capture_output=True, text=True) if not setup.returncode else setup
                if copied.returncode: append("successor_claude_handoff_failed", exit_code=copied.returncode); return 2
                deadline = transition_now.replace(hour=18, minute=0, second=0, microsecond=0)
                route_path = OUT / f"successor-claude-route-order-r{review_round}.json"
                atomic_json(route_path, {
                    "schema_version":ORDER_SCHEMA,
                    "event_id":f"source-library-successor-claude-v2-r{review_round}-20261019", "stage":"claude",
                    "working_directory":"/home/kgnote/.local/share/kgnote/source-library-successor-20261019",
                    "handoff_directory":"/home/kgnote/.local/share/kgnote/successor-review",
                    "command":["/bin/sh", "-c", f"PATH=/home/kgnote/.local/bin:/home/kgnote/.local/lib/node-v24.12.0/bin:/usr/bin:/bin; XDG_CACHE_HOME=/tmp/kgnote-review-cache; export PATH XDG_CACHE_HOME; /usr/bin/python3 /home/kgnote/.local/share/kgnote/runtime/claude_reviewer_adapter.py {remote_work}"],
                    "checkpoint_path":str(OUT / f"successor-claude-route-checkpoint-r{review_round}.json"),
                    "memory_max":"4G", "tasks_max":192, "timeout_seconds":1800,
                    "lease_timeout_seconds":8, "deadline_at":deadline.isoformat(),
                    "execution_context": configured_execution_context(
                        "CLAUDE_PRODUCT_REVIEWER", pull_request=26, review_round=review_round
                    ),
                })
                pending.update({"status":"REVIEWING", "active_review":{"identity_key":review_key,"round":review_round,"candidate_commit":candidate,"candidate_fingerprint":fingerprint}})
                write_pending(pending_goal,pending)
                result = route_order(repo, router, route_path, command_runner)
                pending = load(pending_goal)
                if result:
                    pending["status"]="BLOCKED"; pending["runtime_block"]={"failure_class":"CLAUDE_REVIEW_FAILED","retry_blocked":True,"reason":"bounded Claude reviewer route failed","blocked_at":datetime.now(ZONE).isoformat(timespec="seconds")}
                else:
                    pending["status"]="REVIEW_TRANSPORT_COMPLETE"
                    review_budget["used"]=review_round
                write_pending(pending_goal,pending); append("successor_claude_dispatched", review_round=review_round, exit_code=result)
                return result
            if canary_order is None and pending.get("status") in {"ACTIVE", "ACTIVATING"} and candidate_ready and in_window({"work_window": pending.get("work_window", {})}, transition_now):
                candidate = str(last_codex["resulting_head"])
                repository = str((pending.get("scope") or {}).get("repository"))
                branch = str(pending.get("successor_branch"))
                remote = command_runner(
                    ["/opt/homebrew/bin/gh", "api", f"repos/{repository}/git/ref/heads/{branch}"],
                    cwd=repo, capture_output=True, text=True,
                )
                try: remote_head = ((json.loads(remote.stdout).get("object") or {}).get("sha"))
                except json.JSONDecodeError: remote_head = None
                legacy_head = str(legacy_identity.get("head", ""))
                previous_published = pending.get("published_candidate", {})
                published_head = str((previous_published or {}).get("commit", "")) or None
                verification = pending.get("candidate_verification", {})
                if remote.returncode:
                    append("successor_publish_readback_unavailable", exit_code=remote.returncode)
                    return 2
                admission_error = publish_admission_error(remote_head, candidate, legacy_head, published_head, verification if isinstance(verification, dict) else {})
                if admission_error:
                    pending.update({"status":"BLOCKED", "runtime_block": {
                        "blocked_at": datetime.now(ZONE).isoformat(timespec="seconds"),
                        "failure_class":"PUBLISH_REMOTE_HEAD_MISMATCH" if admission_error == "remote_head_mismatch" else "CANDIDATE_VERIFICATION_REQUIRED", "retry_blocked":True,
                        "reason":f"publisher admission failed: {admission_error}; remote={remote_head!r}, published_parent={published_head!r}, candidate={candidate!r}",
                    }})
                    write_pending(pending_goal, pending); append("successor_publish_blocked", remote_head=remote_head)
                    return 2
                if remote_head != candidate:
                    deadline = transition_now.replace(hour=18, minute=0, second=0, microsecond=0)
                    push_order = repo / OUT.relative_to(repo) / f"successor-push-order-{candidate[:8]}.json"
                    atomic_json(push_order, {
                        "schema_version":ORDER_SCHEMA,
                        "event_id":f"source-library-successor-push-{candidate[:8]}", "stage":"push",
                        "working_directory":"/home/kgnote/.local/share/kgnote/source-library-successor-20261019",
                        "command":["/usr/bin/git", "-c", "core.sshCommand=/usr/bin/ssh -i /home/kgnote/.ssh/kgnote-public-publisher-ed25519 -o IdentitiesOnly=yes -o BatchMode=yes", "push", "git@github.com:joannalee20050914/KGnote-public.git", f"HEAD:refs/heads/{branch}"],
                        "checkpoint_path":str(OUT / f"successor-push-checkpoint-{candidate[:8]}.json"),
                        "memory_max":"512M", "tasks_max":32, "timeout_seconds":600,
                        "lease_timeout_seconds":8, "deadline_at":deadline.isoformat(),
                    })
                    result = route_order(repo, router, push_order, command_runner)
                    if result: append("successor_publish_failed", exit_code=result); return result
                    remote = command_runner(["/opt/homebrew/bin/gh", "api", f"repos/{repository}/git/ref/heads/{branch}"], cwd=repo, capture_output=True, text=True)
                    try: remote_head = ((json.loads(remote.stdout).get("object") or {}).get("sha"))
                    except json.JSONDecodeError: remote_head = None
                    if remote.returncode or remote_head != candidate:
                        append("successor_publish_readback_failed", remote_head=remote_head); return 2
                pending.update({"status":"PUBLISHED", "published_candidate": {
                    "commit":candidate, "fingerprint":verification["candidate_fingerprint"],
                    "pull_request":pending.get("successor_pull_request"), "github_head":remote_head,
                    "verified_at":datetime.now(ZONE).isoformat(timespec="seconds"),
                }})
                write_pending(pending_goal, pending)
                append("successor_candidate_published", candidate_head=candidate, pull_request=pending.get("successor_pull_request"))
                return 0
            if (
                canary_order is None and pending.get("status") == "BLOCKED"
                and isinstance(runtime_block, dict)
                and runtime_block.get("failure_class") in {
                    "CANDIDATE_VERIFICATION_REQUIRED",
                    "CANDIDATE_VERIFICATION_RETRYABLE",
                    "CANDIDATE_VERIFICATION_FAILED",
                }
                and candidate_ready and in_window({"work_window": pending.get("work_window", {})}, transition_now)
            ):
                candidate = str(last_codex["resulting_head"]); short = candidate[:8]
                remote_receipt = f"output/control-plane/runner-verification-{short}.json"
                deadline = transition_now.replace(hour=18, minute=0, second=0, microsecond=0)
                previous_attempt = runtime_block.get("verification_attempt")
                if not isinstance(previous_attempt, int):
                    historical = OUT / f"successor-verify-checkpoint-{short}.json"
                    previous_attempt = 1 if historical.is_file() else 0
                attempt = previous_attempt + 1
                if attempt > VERIFICATION_MAX_ATTEMPTS:
                    pending["runtime_block"] = {
                        **runtime_block,
                        "failure_class": "VERIFICATION_AUTOMATION_BLOCKED",
                        "reason": "bounded deterministic verification infrastructure retries are exhausted",
                        "retry_blocked": True,
                        "verification_attempt": previous_attempt,
                    }
                    write_pending(pending_goal, pending)
                    append("successor_candidate_verification_hard_stopped", candidate=candidate, reason="retry_limit")
                    return 2
                prepared, preparation_error = prepare_remote_candidate_verification(
                    repo, candidate, command_runner
                )
                if not prepared:
                    pending["runtime_block"] = {
                        **runtime_block,
                        "failure_class": (
                            "VERIFICATION_AUTOMATION_BLOCKED"
                            if attempt >= VERIFICATION_MAX_ATTEMPTS
                            else "CANDIDATE_VERIFICATION_RETRYABLE"
                        ),
                        "reason": preparation_error,
                        "retry_blocked": attempt >= VERIFICATION_MAX_ATTEMPTS,
                        "verification_attempt": attempt,
                    }
                    write_pending(pending_goal, pending)
                    append("successor_candidate_verification_preparation_failed", candidate=candidate, attempt=attempt, reason=preparation_error)
                    return 2
                suffix = "" if attempt == 1 else f"-retry-{attempt:02d}"
                verify_order = OUT / f"successor-verify-order-{short}{suffix}.json"
                atomic_json(verify_order, {
                    "schema_version":ORDER_SCHEMA,
                    "event_id":f"source-library-successor-verify-{short}{suffix}", "stage":"ingestion",
                    "working_directory":str(REMOTE_SUCCESSOR_WORKTREE),
                    "command":verification_command(remote_receipt),
                    "checkpoint_path":str(OUT / f"successor-verify-checkpoint-{short}{suffix}.json"),
                    "memory_max":"4G","tasks_max":192,"timeout_seconds":1800,"lease_timeout_seconds":8,"deadline_at":deadline.isoformat(),
                    "execution_context": configured_execution_context(
                        "DETERMINISTIC_VERIFICATION", pull_request=26
                    ),
                })
                result = route_order(repo, router, verify_order, command_runner)
                fetched = command_runner(["ssh","kgnote-ubuntu","/usr/bin/cat",f"{REMOTE_SUCCESSOR_WORKTREE}/{remote_receipt}"],cwd=repo,capture_output=True,text=True)
                try: evidence = json.loads(fetched.stdout) if fetched.returncode == 0 else {}
                except json.JSONDecodeError: evidence = {}
                fingerprint = verified_candidate_fingerprint(evidence, candidate) if isinstance(evidence,dict) else None
                verified = result == 0 and fingerprint is not None
                pending = load(pending_goal)
                if not verified:
                    checkpoint_path = Path(load(verify_order).get("checkpoint_path", ""))
                    try: checkpoint = load(checkpoint_path)
                    except (OSError, ValueError, json.JSONDecodeError): checkpoint = {}
                    stderr_path = Path(str(checkpoint.get("stderr_path", "")))
                    try: verification_stderr = stderr_path.read_text(encoding="utf-8")
                    except OSError: verification_stderr = ""
                    disposition, detail = verification_failure_disposition(
                        evidence if isinstance(evidence, dict) else {},
                        route_exit=result,
                        stderr=verification_stderr,
                    )
                    reason = (
                        f"full deterministic verification failed for {candidate}; route_exit={result}; "
                        f"evidence_result={evidence.get('result')}; fingerprint_stable={evidence.get('fingerprint_stable')}; "
                        f"disposition={disposition}; detail={detail}"
                    )
                    if disposition == "PRODUCT_REPAIR":
                        budget = pending["continuous_budget"]["codex_implementation_or_repair_cycles"]
                        if int(budget["used"]) >= int(budget["authorized"]):
                            pending["runtime_block"] = {
                                **runtime_block, "failure_class":"BUDGET_EXHAUSTED",
                                "reason":reason, "retry_blocked":True,
                                "verification_attempt":attempt,
                            }
                        else:
                            resolved = {
                                **runtime_block, "failure_class":"PRODUCT_CANDIDATE_VERIFICATION_FAILED",
                                "reason":reason, "retry_blocked":False,
                                "verification_attempt":attempt,
                                "resolved_at":datetime.now(ZONE).isoformat(timespec="seconds"),
                                "resolution":"routed to the formal Runner Codex repair path",
                            }
                            pending.setdefault("resolved_runtime_blocks", []).append(resolved)
                            pending.pop("runtime_block", None)
                            pending.pop("last_codex_result", None)
                            pending["status"] = "ACTIVE"
                    elif disposition == "INFRA_RETRY" and attempt < VERIFICATION_MAX_ATTEMPTS:
                        pending["runtime_block"] = {
                            **runtime_block, "failure_class":"CANDIDATE_VERIFICATION_RETRYABLE",
                            "reason":reason, "retry_blocked":False,
                            "verification_attempt":attempt,
                        }
                    else:
                        pending["runtime_block"] = {
                            **runtime_block,
                            "failure_class": (
                                "VERIFICATION_AUTOMATION_BLOCKED"
                                if disposition == "INFRA_RETRY"
                                else "CANDIDATE_VERIFICATION_HARD_STOP"
                            ),
                            "reason":reason, "retry_blocked":True,
                            "verification_attempt":attempt,
                        }
                    write_pending(pending_goal,pending); append("successor_candidate_verification_failed",candidate=candidate,exit_code=result,attempt=attempt,disposition=disposition)
                    return result or 2
                pending["candidate_verification"]={"status":"PASS","candidate_commit":candidate,"candidate_fingerprint":fingerprint,"evidence_path":evidence.get("evidence_path"),"evidence_readback":True,"verified_at":datetime.now(ZONE).isoformat(timespec="seconds")}
                block = pending.pop("runtime_block",runtime_block); block={**block,"retry_blocked":False,"resolved_at":datetime.now(ZONE).isoformat(timespec="seconds"),"resolution":"automatic full deterministic verification passed for the exact candidate","verification_attempt":attempt}
                pending.setdefault("resolved_runtime_blocks",[]).append(block); pending["status"]="ACTIVE"
                write_pending(pending_goal,pending); append("successor_candidate_verified",candidate=candidate,fingerprint=fingerprint)
                return 0
            if (
                canary_order is None
                and pending.get("status") == "BLOCKED"
                and isinstance(runtime_block, dict)
                and runtime_block.get("retry_blocked") is True
            ):
                order = idle_health_order(repo)
                result = route_order(repo, router, order, command_runner)
                append(
                    "pending_successor_blocked_idle",
                    failure_class=runtime_block.get("failure_class"),
                    linux_health_exit_code=result,
                )
                return result
            if canary_order is None and pending.get("status") in WORK_ITEM_PAUSED | {"PRODUCT_DECISION_REQUIRED"}:
                return route_next_ready_work(
                    repo, pending_goal, pending, transition_now,
                    stop_marker_present=True, router=router, epoch_record=epoch_record,
                    admission=admission, command_runner=command_runner,
                )
            if pending and not successor_errors(pending, transition_now) and in_window({"work_window": pending.get("work_window", {})}, transition_now):
                order, errors = prepare_successor_handoff(repo, pending_goal, current or datetime.now(ZONE), command_runner)
                if errors: append("pending_successor_rejected", errors=errors); return 2
                if order is not None:
                    gate = command_runner([sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order)], cwd=repo, capture_output=True, text=True)
                    if gate.returncode:
                        append("successor_epoch_admission_rejected", output_tail=(gate.stdout or "")[-1000:]); return 2
                    append("successor_epoch_admission_passed", output_tail=(gate.stdout or "")[-1000:])
                    result = route_order(repo, router, order, command_runner)
                    if result == 0:
                        pending = load(pending_goal)
                        order_value = load(order)
                        event_id = str(order_value.get("event_id", ""))
                        consumed = pending.setdefault("consumed_codex_events", [])
                        if not isinstance(consumed, list):
                            consumed = []
                            pending["consumed_codex_events"] = consumed
                        if event_id not in consumed:
                            consumed.append(event_id)
                            budget = pending["continuous_budget"]["codex_implementation_or_repair_cycles"]
                            budget["used"] = int(budget["used"]) + 1
                        probe = command_runner(
                            ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes", "kgnote-ubuntu",
                             f"/usr/bin/git -C {order_value['working_directory']} rev-parse HEAD && /usr/bin/git -C {order_value['working_directory']} status --porcelain"],
                            cwd=repo, capture_output=True, text=True,
                        )
                        lines = (probe.stdout or "").splitlines()
                        resulting_head = lines[0] if lines else None
                        dirty = lines[1:] if len(lines) > 1 else []
                        expected_head = str((order_value.get("review_admission") or {}).get("head_sha", ""))
                        progressed = probe.returncode == 0 and (resulting_head != expected_head or bool(dirty))
                        no_progress = 0 if progressed else int(pending.get("consecutive_no_progress", 0)) + 1
                        pending.update({
                            "status":"ACTIVE", "product_work_started":True,
                            "consecutive_no_progress": no_progress,
                            "last_codex_result": {
                                "event_id": event_id, "route_status": "COMPLETED",
                                "resulting_head": resulting_head, "dirty_paths": dirty,
                                "material_progress": progressed,
                            },
                        })
                        if no_progress >= 2:
                            pending.update({
                                "status": "BLOCKED",
                                "runtime_block": {
                                    "blocked_at": datetime.now(ZONE).isoformat(timespec="seconds"),
                                    "event_id": event_id,
                                    "failure_class": "CODEX_NO_MATERIAL_PROGRESS",
                                    "reason": "two consecutive completed Codex cycles produced no candidate commit or dirty path",
                                    "retry_blocked": True,
                                },
                            })
                        resolved_block = pending.get("runtime_block")
                        if isinstance(resolved_block, dict) and no_progress < 2:
                            pending.pop("runtime_block", None)
                            resolved_block = {**resolved_block, "retry_blocked": False, "resolved_at": datetime.now(ZONE).isoformat(timespec="seconds")}
                            history = pending.setdefault("resolved_runtime_blocks", [])
                            if isinstance(history, list):
                                history.append(resolved_block)
                        write_pending(pending_goal, pending)
                        handoff = load(repo / SUCCESSOR_HANDOFF); handoff["status"] = "CODEX_DISPATCHED"; atomic_json(repo / SUCCESSOR_HANDOFF, handoff)
                    else:
                        order_value = load(order)
                        checkpoint_path = Path(str(order_value.get("checkpoint_path", "")))
                        try: checkpoint = load(checkpoint_path)
                        except (OSError, ValueError, json.JSONDecodeError): checkpoint = {}
                        failure_class, reason = route_failure(checkpoint, result)
                        pending = load(pending_goal)
                        pending.update({
                            "status": "BLOCKED",
                            "runtime_block": {
                                "blocked_at": datetime.now(ZONE).isoformat(timespec="seconds"),
                                "event_id": checkpoint.get("event_id") or order_value.get("event_id"),
                                "failure_class": failure_class,
                                "guest_exit_code": checkpoint.get("exit_code"),
                                "reason": reason,
                                "retry_blocked": True,
                            },
                        })
                        write_pending(pending_goal, pending)
                    append("pending_successor_dispatched", exit_code=result)
                    return result
            order = idle_health_order(repo)
            if canary_order is not None:
                try: validate_canary_order(canary_order)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    append("canary_rejected", reason=str(exc)); return 2
                order = canary_order
            result = route_order(repo, router, order, command_runner)
            append("product_stop_marker_preserved_idle", linux_health_exit_code=result)
            return result
        persisted = str(state.get("state", ""))
        if persisted in GLOBAL_TERMINAL: append("hard_stop_preserved", status=persisted); return 0
        errors = envelope_errors(envelope, state)
        if errors: append("authorization_rejected", errors=errors); return 2
        if not in_window(envelope, current): append("outside_work_window"); return 0
        if persisted not in RUNNABLE: append("state_rejected", status=persisted); return 2
        order_path = repo / PRODUCT_ORDER
        if not order_path.is_file():
            append("production_dispatch_failed_closed", reason="linux_worker_order_missing", status=persisted)
            return 2
        if not epoch_record.is_file() or not admission.is_file():
            append("epoch_admission_rejected", reason="epoch gate unavailable")
            return 2
        gate = command_runner(
            [sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order_path)],
            cwd=repo, capture_output=True, text=True,
        )
        if gate.returncode:
            append("epoch_admission_rejected", output_tail=(gate.stdout or "")[-1000:])
            return 2
        append("epoch_admission_passed", output_tail=(gate.stdout or "")[-1000:])
        append("linux_worker_dispatch_started", status=persisted, order=str(order_path))
        return route_order(repo, router, order_path, command_runner)

def hold_writer_lock(repo: Path, command: list[str], identity: dict[str, object]) -> int:
    global OUT, LOCK, LOG, RUNNER_EVENT_IDENTITY
    OUT = repo / "output/control-plane/production-runner"; LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    RUNNER_EVENT_IDENTITY = identity
    OUT.mkdir(parents=True, exist_ok=True)
    if not command:
        raise ValueError("--hold-lock requires a command after --")
    with LOCK.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        append("writer_lock_held_for_manual_command", command=command)
        completed = subprocess.run(command, cwd=repo)
        append("writer_lock_manual_command_completed", exit_code=completed.returncode)
        return completed.returncode


def run_product_goal_mode(
    repo: Path,
    *,
    spec_path: Path,
    state_path: Path,
    ledger_path: Path,
    comments_path: Path | None,
    backlog_path: Path | None,
    trial: bool,
    router: Path,
    epoch_record: Path,
    admission: Path,
    runner_identity: dict[str, object],
    current: datetime | None = None,
    command_runner=subprocess.run,
) -> dict[str, object]:
    """Plan or route one Product Goal action through the existing trust chain."""
    global OUT, LOCK, LOG, RUNNER_EVENT_IDENTITY
    OUT = repo / "output/control-plane/production-runner"
    LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    RUNNER_EVENT_IDENTITY = runner_identity
    OUT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        if (repo / STOP_MARKER).exists():
            append("product_goal_dispatch_stopped", reason="orchestrator_stop_marker_present")
            return {
                "status": "STOPPED",
                "requires_model": False,
                "reason": "the existing Stop Marker blocks Product Goal dispatch",
            }
        spec = goal_runner_adapter.goal_continuity.load_json(spec_path)
        state = goal_runner_adapter.goal_continuity.load_json(state_path)
        comments = (
            json.loads(comments_path.read_text(encoding="utf-8"))
            if comments_path else goal_runner_adapter.github_control.fetch_issue_comments(spec)
        )
        if not isinstance(comments, list):
            raise goal_runner_adapter.GoalRunnerError("comments input must be a JSON list")
        authority = goal_runner_adapter.github_control.resolve_authority(comments, spec)
        if not trial:
            reconciled = goal_runner_adapter.reconcile_owner_authority(
                spec, state, authority, state_path=state_path, ledger_path=ledger_path,
            )
            state = reconciled["state"]
            if reconciled["rejected_transitions"]:
                decision = {
                    "status": "AUTHORITY_COMMAND_REJECTED", "requires_model": False,
                    "rejected_transitions": reconciled["rejected_transitions"],
                    "reason": "an exact Owner command failed its lifecycle prerequisites",
                }
                append("product_goal_scheduler_decision", decision=decision)
                return decision
            observed_now = current or datetime.now(ZONE)
            notification_delivery = goal_runner_adapter.goal_notifications.deliver_queued_github_notifications(
                ledger_path,
                repository=spec["repository"],
                max_attempts=spec["recovery_policy"]["max_same_failure_attempts"],
                now=observed_now,
                command_runner=command_runner,
            )
            notification_acks = goal_runner_adapter.goal_notifications.reconcile_owner_acknowledgements(
                ledger_path,
                comments,
                repository=spec["repository"],
                owner_logins=spec["owner_logins"],
                observed_at=observed_now.isoformat(timespec="seconds"),
            )
            if notification_delivery or any(notification_acks.values()):
                append(
                    "product_goal_notification_reconciliation",
                    delivery=notification_delivery,
                    acknowledgements=notification_acks,
                )
            state = goal_runner_adapter.synchronize_state_from_ledger(
                spec, state,
                goal_runner_adapter.goal_continuity.read_ledger(ledger_path),
                state_path=state_path,
            )
            if state["lifecycle"]["state"] == "CLOSED" and backlog_path is not None:
                handoff = goal_runner_adapter.prepare_next_goal_handoff(
                    goal_runner_adapter.goal_continuity.load_json(backlog_path), state,
                    ledger_path=ledger_path,
                    occurred_at=(current or datetime.now(ZONE)).isoformat(timespec="seconds"),
                    github_issue=spec["github_issue"],
                )
                state = goal_runner_adapter.synchronize_state_from_ledger(
                    spec, state,
                    goal_runner_adapter.goal_continuity.read_ledger(ledger_path),
                    state_path=state_path,
                )
                append("product_goal_backlog_handoff", decision=handoff)
                return handoff
        ledger = goal_runner_adapter.goal_continuity.read_ledger(ledger_path)
        decision = goal_runner_adapter.next_action(
            spec, state, ledger, authority,
            now=current or datetime.now(ZONE), trial=trial,
        )
        if (
            not trial
            and decision.get("status") == "RECOVERY_READY"
            and decision.get("action") == "RESUME_AFTER_QUOTA"
        ):
            observed_now = current or datetime.now(ZONE)
            try:
                resumed = goal_runner_adapter.resume_after_quota_backoff(
                    spec, state, state_path=state_path, ledger_path=ledger_path,
                    now=observed_now,
                )
            except goal_runner_adapter.GoalRunnerError as exc:
                resumed = {
                    "status": "QUOTA_BACKOFF_RESUME_REJECTED",
                    "requires_model": False,
                    "reason": str(exc),
                }
                append("product_goal_quota_resume", decision=resumed)
                return resumed
            append("product_goal_quota_resume", decision=resumed)
            state = goal_runner_adapter.goal_continuity.load_json(state_path)
            ledger = goal_runner_adapter.goal_continuity.read_ledger(ledger_path)
            decision = goal_runner_adapter.next_action(
                spec, state, ledger, authority, now=observed_now, trial=False,
            )
        if (
            not trial
            and decision.get("status") == "RECOVERY_READY"
            and decision.get("action")
            in goal_runner_adapter.RECOVERABLE_RUNTIME_ACTIONS
        ):
            observed_now = current or datetime.now(ZONE)
            try:
                resumed = goal_runner_adapter.resume_recoverable_runtime_block(
                    spec, state, state_path=state_path, ledger_path=ledger_path,
                    now=observed_now,
                )
            except goal_runner_adapter.GoalRunnerError as exc:
                resumed = {
                    "status": "RUNTIME_BLOCK_RELEASE_REJECTED",
                    "requires_model": False,
                    "reason": str(exc),
                }
                append("product_goal_runtime_recovery", decision=resumed)
                return resumed
            append("product_goal_runtime_recovery", decision=resumed)
            state = goal_runner_adapter.goal_continuity.load_json(state_path)
            ledger = goal_runner_adapter.goal_continuity.read_ledger(ledger_path)
            decision = goal_runner_adapter.next_action(
                spec, state, ledger, authority, now=observed_now, trial=False,
            )
        if (
            not trial
            and decision.get("status") == "RECOVERY_READY"
            and decision.get("action") == "RECONCILE_CHECKPOINT"
        ):
            try:
                result = goal_runner_adapter.reconcile_dispatch_checkpoint(
                    spec, state, state_path=state_path, ledger_path=ledger_path,
                    repo=repo, attempt_id=str(decision["attempt_id"]),
                    occurred_at=(current or datetime.now(ZONE)).isoformat(timespec="seconds"),
                )
            except goal_runner_adapter.GoalRunnerError as exc:
                result = {
                    "status": "CHECKPOINT_RECONCILIATION_REJECTED",
                    "requires_model": False, "reason": str(exc),
                    "attempt_id": decision.get("attempt_id"),
                }
            append("product_goal_checkpoint_reconciliation", decision=result)
            return result
        if decision.get("status") != "ACTION_READY":
            append("product_goal_scheduler_decision", decision=decision)
            return decision
        try:
            order_path, _, _ = goal_runner_adapter.validated_bound_order(
                spec, state, decision, repo=repo
            )
        except goal_runner_adapter.GoalRunnerError as exc:
            append("product_goal_dispatch_binding_rejected", reason=str(exc))
            return {
                **decision,
                "status": "DISPATCH_BINDING_REQUIRED",
                "requires_model": False,
                "reason": str(exc),
            }
        if not router.is_file() or not epoch_record.is_file() or not admission.is_file():
            append("product_goal_admission_unavailable", order=str(order_path))
            return {
                **decision,
                "status": "ADMISSION_UNAVAILABLE",
                "requires_model": False,
                "reason": "router, epoch record, or scope admission helper is unavailable",
            }
        gate = command_runner(
            [sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order_path)],
            cwd=repo, capture_output=True, text=True,
        )
        if gate.returncode:
            append(
                "product_goal_admission_rejected", order=str(order_path),
                error_tail=(gate.stderr or gate.stdout or "")[-1000:],
            )
            return {
                **decision,
                "status": "ADMISSION_REJECTED",
                "requires_model": False,
                "reason": "the existing epoch/scope admission gate rejected the sealed order",
            }
        observed_at = (current or datetime.now(ZONE)).isoformat(timespec="seconds")
        reserved, order_path, attempt_id = goal_runner_adapter.reserve_dispatch(
            spec, state, decision, state_path=state_path, ledger_path=ledger_path,
            repo=repo, occurred_at=observed_at,
        )
        append(
            "product_goal_dispatch_reserved", work_item_id=decision["work_item_id"],
            attempt_id=attempt_id, order=str(order_path),
        )
        exit_code = route_order(repo, router, order_path, command_runner)
        updated = goal_runner_adapter.record_route_outcome(
            spec, reserved, state_path=state_path,
            work_item_id=str(decision["work_item_id"]), attempt_id=attempt_id,
            route_exit_code=exit_code, occurred_at=observed_at,
        )
        status = "DISPATCHED" if exit_code == 0 else "ROUTE_FAILED_RECONCILIATION_REQUIRED"
        append(
            "product_goal_route_completed", work_item_id=decision["work_item_id"],
            attempt_id=attempt_id, exit_code=exit_code, status=status,
        )
        return {
            **decision,
            "status": status,
            "attempt_id": attempt_id,
            "route_exit_code": exit_code,
            "persisted_work_status": next(
                row["status"] for row in updated["work_items"]
                if row["work_item_id"] == decision["work_item_id"]
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--router", type=Path, default=DEFAULT_ROUTER)
    parser.add_argument("--canary-order", type=Path)
    parser.add_argument("--epoch-record", type=Path, default=DEFAULT_EPOCH)
    parser.add_argument("--scope-admission", type=Path, default=DEFAULT_ADMISSION)
    parser.add_argument("--pending-goal", type=Path, default=DEFAULT_PENDING)
    parser.add_argument("--product-goal-spec", type=Path)
    parser.add_argument("--product-goal-state", type=Path)
    parser.add_argument("--product-goal-ledger", type=Path)
    parser.add_argument("--product-goal-comments", type=Path)
    parser.add_argument("--product-goal-backlog", type=Path)
    parser.add_argument("--product-goal-trial", action="store_true")
    parser.add_argument("--hold-lock", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    identity = runner_code_identity(Path(__file__).resolve().parents[1])
    try:
        product_paths = [args.product_goal_spec, args.product_goal_state, args.product_goal_ledger]
        if any(product_paths):
            if not all(product_paths):
                parser.error("Product Goal adapter requires spec, state, and ledger together")
            result = run_product_goal_mode(
                args.repo.resolve(),
                spec_path=args.product_goal_spec.resolve(),
                state_path=args.product_goal_state.resolve(),
                ledger_path=args.product_goal_ledger.resolve(),
                comments_path=(
                    args.product_goal_comments.resolve() if args.product_goal_comments else None
                ),
                backlog_path=(
                    args.product_goal_backlog.resolve() if args.product_goal_backlog else None
                ),
                trial=args.product_goal_trial,
                router=args.router.resolve(), epoch_record=args.epoch_record.resolve(),
                admission=args.scope_admission.resolve(), runner_identity=identity,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            failures = {
                "GO_LIVE_NOT_AUTHORIZED", "STOPPED", "DISPATCH_BINDING_REQUIRED",
                "ADMISSION_UNAVAILABLE", "ADMISSION_REJECTED",
                "ROUTE_FAILED_RECONCILIATION_REQUIRED",
                "AUTHORITY_COMMAND_REJECTED", "CHECKPOINT_RECONCILIATION_REJECTED",
            }
            return 0 if result["status"] not in failures else 2
        if args.hold_lock:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            return hold_writer_lock(args.repo.resolve(), command, identity)
        return run_once(
            args.repo.resolve(), router=args.router.resolve(),
            canary_order=args.canary_order.resolve() if args.canary_order else None,
            epoch_record=args.epoch_record.resolve(), admission=args.scope_admission.resolve(),
            pending_goal=args.pending_goal.resolve(), runner_identity=identity,
        )
    except PendingWriteConflict:
        return 2
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__": raise SystemExit(main())
