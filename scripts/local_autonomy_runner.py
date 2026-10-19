#!/usr/bin/env python3
"""Single Mac production Runner for cgroup-confined Ubuntu worker orders."""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import external_review_control

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
        "NO_ELIGIBLE_READY_WORK": "queue:idle",
    }.get(status, "queue:ready")


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
        if not work_id or raw.get("status") != "READY":
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
        handle.write(json.dumps({"at": datetime.now(ZONE).isoformat(timespec="seconds"), "event": event, **fields}, ensure_ascii=False) + "\n")

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
    atomic_json(pending_path, pending)
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
    )
    return completed.returncode


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
    decision = select_ready_work(pending, current, stop_marker_present=stop_marker_present)
    pending["scheduler"] = {
        "status": decision["status"],
        "evaluated_at": current.isoformat(timespec="seconds"),
        "selected_work_item": (
            decision["selected"].get("work_item_id")
            if isinstance(decision.get("selected"), dict) else None
        ),
        "blocks": decision["blocks"],
    }
    if decision["status"] != "DISPATCH_READY":
        pending["runner_status"] = decision["status"]
        atomic_json(pending_path, pending)
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
        atomic_json(pending_path, pending)
        return 2
    if not order_path.is_file() or not epoch_record.is_file() or not admission.is_file():
        pending["runner_status"] = "WORK_ITEM_BLOCKED"
        pending["scheduler"]["blocks"].append(blocking_record(
            "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason="sealed order or epoch admission gate is unavailable",
            affected_work=[str(selected.get("work_item_id"))],
            release_condition="restore the existing sealed order and epoch admission files",
            next_legal_action="remain idle without creating replacement work",
        ))
        atomic_json(pending_path, pending)
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
        atomic_json(pending_path, pending)
        return 2
    result = route_order(repo, router, order_path, command_runner)
    if result:
        pending["runner_status"] = "WORK_ITEM_BLOCKED"
        pending["scheduler"]["blocks"].append(blocking_record(
            "WORK_ITEM_BLOCKED", scope="WORK_ITEM", reason=f"isolated worker route failed with exit {result}",
            affected_work=[str(selected.get("work_item_id"))],
            release_condition="the recoverable worker route succeeds within its existing retry policy",
            next_legal_action="preserve the checkpoint; retry without resetting budget or completed work",
        ))
        atomic_json(pending_path, pending)
        return result
    selected["status"] = "DISPATCHED"
    budget = selected["budget"]
    budget["used"] = int(budget["used"]) + 1
    pending["runner_status"] = "DISPATCHED"
    pending["scheduler"]["status"] = "DISPATCHED"
    atomic_json(pending_path, pending)
    append("independent_ready_work_dispatched", work_item_id=selected.get("work_item_id"), order=str(order_path))
    return 0


def idle_health_order(repo: Path) -> Path:
    path = OUT / "linux-idle-health-order.json"
    value = {
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
) -> int:
    global OUT, LOCK, LOG
    OUT = repo / "output/control-plane/production-runner"; LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock_handle:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: append("writer_lock_blocked"); return 0
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
                atomic_json(pending_goal, pending)
                append("legacy_human_checkpoint_scope_reconciled", status=pending["status"], consistency_error=consistency_error)
            if pending.get("status") in WORK_ITEM_PAUSED | {"COMPONENT_REVIEW_COMPLETE"}:
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
                decision = load(consumer_checkpoint); verdict = str(decision.get("status"))
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
                atomic_json(pending_goal,pending)
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
                atomic_json(pending_goal,pending)
                result = route_order(repo, router, route_path, command_runner)
                pending = load(pending_goal)
                if result:
                    pending["status"]="BLOCKED"; pending["runtime_block"]={"failure_class":"CLAUDE_REVIEW_FAILED","retry_blocked":True,"reason":"bounded Claude reviewer route failed","blocked_at":datetime.now(ZONE).isoformat(timespec="seconds")}
                else:
                    pending["status"]="REVIEW_TRANSPORT_COMPLETE"
                    review_budget["used"]=review_round
                atomic_json(pending_goal,pending); append("successor_claude_dispatched", review_round=review_round, exit_code=result)
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
                    atomic_json(pending_goal, pending); append("successor_publish_blocked", remote_head=remote_head)
                    return 2
                if remote_head != candidate:
                    deadline = transition_now.replace(hour=18, minute=0, second=0, microsecond=0)
                    push_order = repo / OUT.relative_to(repo) / f"successor-push-order-{candidate[:8]}.json"
                    atomic_json(push_order, {
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
                atomic_json(pending_goal, pending)
                append("successor_candidate_published", candidate_head=candidate, pull_request=pending.get("successor_pull_request"))
                return 0
            if (
                canary_order is None and pending.get("status") == "BLOCKED"
                and isinstance(runtime_block, dict)
                and runtime_block.get("failure_class") == "CANDIDATE_VERIFICATION_REQUIRED"
                and candidate_ready and in_window({"work_window": pending.get("work_window", {})}, transition_now)
            ):
                candidate = str(last_codex["resulting_head"]); short = candidate[:8]
                remote_receipt = f"output/control-plane/runner-verification-{short}.json"
                deadline = transition_now.replace(hour=18, minute=0, second=0, microsecond=0)
                verify_order = OUT / f"successor-verify-order-{short}.json"
                atomic_json(verify_order, {
                    "event_id":f"source-library-successor-verify-{short}", "stage":"ingestion",
                    "working_directory":"/home/kgnote/.local/share/kgnote/source-library-successor-20261019",
                    "command":["/bin/sh","-c",f"PATH=/home/kgnote/.local/bin:/home/kgnote/.local/lib/node-v24.12.0/bin:/usr/bin:/bin; export PATH; .venv/bin/python scripts/codex_control.py --repo . verify > {remote_receipt}"],
                    "checkpoint_path":str(OUT / f"successor-verify-checkpoint-{short}.json"),
                    "memory_max":"4G","tasks_max":192,"timeout_seconds":1800,"lease_timeout_seconds":8,"deadline_at":deadline.isoformat(),
                    "execution_context": configured_execution_context(
                        "DETERMINISTIC_VERIFICATION", pull_request=26
                    ),
                })
                result = route_order(repo, router, verify_order, command_runner)
                fetched = command_runner(["ssh","kgnote-ubuntu","/usr/bin/cat",f"/home/kgnote/.local/share/kgnote/source-library-successor-20261019/{remote_receipt}"],cwd=repo,capture_output=True,text=True) if result == 0 else None
                try: evidence = json.loads(fetched.stdout) if fetched is not None and fetched.returncode == 0 else {}
                except json.JSONDecodeError: evidence = {}
                fingerprint = verified_candidate_fingerprint(evidence, candidate) if isinstance(evidence,dict) else None
                verified = result == 0 and fingerprint is not None
                pending = load(pending_goal)
                if not verified:
                    pending["runtime_block"]={**runtime_block,"failure_class":"CANDIDATE_VERIFICATION_FAILED","reason":f"full deterministic verification failed for {candidate}; route_exit={result}; evidence_result={evidence.get('result')}; fingerprint_stable={evidence.get('fingerprint_stable')}","retry_blocked":True}
                    atomic_json(pending_goal,pending); append("successor_candidate_verification_failed",candidate=candidate,exit_code=result)
                    return result or 2
                pending["candidate_verification"]={"status":"PASS","candidate_commit":candidate,"candidate_fingerprint":fingerprint,"evidence_path":evidence.get("evidence_path"),"evidence_readback":True,"verified_at":datetime.now(ZONE).isoformat(timespec="seconds")}
                block = pending.pop("runtime_block",runtime_block); block={**block,"retry_blocked":False,"resolved_at":datetime.now(ZONE).isoformat(timespec="seconds"),"resolution":"automatic full deterministic verification passed for the exact candidate"}
                pending.setdefault("resolved_runtime_blocks",[]).append(block); pending["status"]="ACTIVE"
                atomic_json(pending_goal,pending); append("successor_candidate_verified",candidate=candidate,fingerprint=fingerprint)
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
                        atomic_json(pending_goal, pending)
                        handoff = load(repo / SUCCESSOR_HANDOFF); handoff["status"] = "CODEX_DISPATCHED"; atomic_json(repo / SUCCESSOR_HANDOFF, handoff)
                    else:
                        checkpoint = load(repo / "output/control-plane/production-runner/successor-codex-route.json")
                        if checkpoint.get("status") == "BLOCKED":
                            pending = load(pending_goal)
                            pending.update({
                                "status": "BLOCKED",
                                "runtime_block": {
                                    "blocked_at": datetime.now(ZONE).isoformat(timespec="seconds"),
                                    "event_id": checkpoint.get("event_id"),
                                    "failure_class": "DETERMINISTIC_WORKER_FAILURE",
                                    "guest_exit_code": checkpoint.get("exit_code"),
                                    "reason": checkpoint.get("reason"),
                                    "retry_blocked": True,
                                },
                            })
                            atomic_json(pending_goal, pending)
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

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--router", type=Path, default=DEFAULT_ROUTER)
    parser.add_argument("--canary-order", type=Path)
    parser.add_argument("--epoch-record", type=Path, default=DEFAULT_EPOCH)
    parser.add_argument("--scope-admission", type=Path, default=DEFAULT_ADMISSION)
    parser.add_argument("--pending-goal", type=Path, default=DEFAULT_PENDING)
    args = parser.parse_args()
    return run_once(
        args.repo.resolve(), router=args.router.resolve(),
        canary_order=args.canary_order.resolve() if args.canary_order else None,
        epoch_record=args.epoch_record.resolve(), admission=args.scope_admission.resolve(),
        pending_goal=args.pending_goal.resolve(),
    )

if __name__ == "__main__": raise SystemExit(main())
