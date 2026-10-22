#!/usr/bin/env python3
"""Dormant Product Goal scheduler adapter for the existing Mac Runner.

The adapter plans one idempotent action at a time. It cannot activate itself:
live dispatch requires exact GitHub Owner authority, a ledger-bound go-live
receipt, an active lease, and an explicit CLI invocation from the Mac Runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import github_product_goal_control as github_control
import goal_continuity


ZONE = ZoneInfo("Asia/Taipei")
TERMINAL_WORK = {"VERIFIED", "CLOSED", "SUPERSEDED"}
RUNNABLE_WORK = {"PLANNED", "READY", "REPAIR_REQUIRED", "VERIFY_REQUIRED", "PUBLISH_REQUIRED"}
NO_MODEL_ACTIONS = {"RECONCILE_CHECKPOINT", "RETRY_PUBLICATION", "RETRY_COMPLETION_GATE"}


class GoalRunnerError(goal_continuity.GoalContractError):
    pass


def in_work_window(spec: dict[str, Any], now: datetime) -> bool:
    local = now.astimezone(ZONE)
    window = spec["work_window"]
    if local.weekday() not in window["weekdays"]:
        return False
    current = local.strftime("%H:%M")
    start, end = window["start"], window["end"]
    return start <= current < end if start <= end else current >= start or current < end


def classify_recovery(failure: dict[str, Any]) -> dict[str, Any]:
    """Map evidence classes to the next legal action without inventing a model round."""
    failure_class = str(failure.get("failure_class") or "UNKNOWN_OUTCOME")
    if failure_class in {"QUOTA_EXHAUSTED", "RATE_LIMITED", "USAGE_LIMIT_REACHED"}:
        return {"action": "WAIT_QUOTA_BACKOFF", "requires_model": False}
    if failure_class in {"WORK_WINDOW_CLOSED", "CAPACITY_RESERVE"}:
        return {"action": "WAIT_CAPACITY", "requires_model": False}
    if failure_class in {"UNKNOWN_OUTCOME", "CHECKPOINT_MISSING", "TRANSPORT_INTERRUPTED"}:
        return {"action": "RECONCILE_CHECKPOINT", "requires_model": False}
    if failure_class in {"PUBLICATION_FAILED", "GITHUB_WRITEBACK_FAILED"}:
        return {"action": "RETRY_PUBLICATION", "requires_model": False}
    if failure_class in {"COMPLETION_GATE_FAILED", "COMPLETION_RECEIPT_MISSING"}:
        return {"action": "RETRY_COMPLETION_GATE", "requires_model": False}
    if failure_class == "CHANGES_REQUIRED":
        return {"action": "DISPATCH_REPAIR", "requires_model": True}
    if failure_class in {"PRODUCT_DECISION_REQUIRED", "NEW_PERMISSION_REQUIRED", "NEW_EXPENSE"}:
        return {"action": "WAIT_HUMAN_DECISION", "requires_model": False}
    return {"action": "ADJUST_STRATEGY", "requires_model": False}


def _go_live_receipt(
    projection: dict[str, Any], authority: dict[str, Any], state: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any] | None:
    record = authority.get("record")
    payload = projection.get("authority")
    if not isinstance(record, dict) or not isinstance(payload, dict):
        return None
    if "activate_runner" not in record["permissions"]:
        return None
    state_record = state.get("authority_record")
    if not isinstance(state_record, dict):
        return None
    if (
        state_record.get("comment_id") != record["comment_id"]
        or state_record.get("body_sha256") != record["body_sha256"]
    ):
        return None
    required = {
        "go_live_authorized": True,
        "authority_comment_id": record["comment_id"],
        "authority_body_sha256": record["body_sha256"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
    }
    if all(payload.get(key) == value for key, value in required.items()):
        return payload
    return None


def _dependency_ready(work: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> bool:
    return all(by_id[item]["status"] in TERMINAL_WORK for item in work["dependencies"])


def _work_action(work: dict[str, Any]) -> dict[str, Any]:
    status = work["status"]
    if status == "PUBLISH_REQUIRED":
        return {"action": "RETRY_PUBLICATION", "requires_model": False}
    if status == "VERIFY_REQUIRED":
        return {"action": "RUN_DETERMINISTIC_VERIFICATION", "requires_model": False}
    if status == "REPAIR_REQUIRED":
        return {"action": "DISPATCH_REPAIR", "requires_model": True}
    return {"action": "DISPATCH_IMPLEMENTATION", "requires_model": True}


def _unreconciled_dispatch(projection: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for attempt_id, reservation in projection.get("dispatch_reservations", {}).items():
        if not reservation.get("reconciled"):
            return attempt_id, reservation
    return None


def next_action(
    spec: dict[str, Any],
    state: dict[str, Any],
    ledger: list[dict[str, Any]],
    authority: dict[str, Any],
    *,
    now: datetime,
    trial: bool,
) -> dict[str, Any]:
    goal_continuity.validate_goal_spec(spec)
    goal_continuity.validate_runner_state(state, spec)
    ledger = goal_continuity.validate_ledger_binding(ledger, state, spec)
    projection = goal_continuity.reduce_ledger(ledger)
    if authority["authority_lease"] != "ACTIVE":
        return {
            "status": "WAIT_AUTHORITY", "authority_status": authority["status"],
            "reason": "an exact active GitHub Owner authority lease is required",
        }
    if authority["status"] == "CLOSED" or state["lifecycle"]["state"] == "CLOSED":
        return {"status": "GOAL_CLOSED"}
    receipt = _go_live_receipt(projection, authority, state, spec)
    if not state["go_live_authorized"] or receipt is None:
        return {
            "status": "TRIAL_ONLY" if trial else "GO_LIVE_NOT_AUTHORIZED",
            "reason": "state flag and exact ledger-bound Owner go-live receipt are both required",
        }
    pending_dispatch = _unreconciled_dispatch(projection)
    if pending_dispatch is not None:
        attempt_id, reservation = pending_dispatch
        return {
            "status": "RECOVERY_READY",
            "action": "RECONCILE_CHECKPOINT",
            "requires_model": False,
            "attempt_id": attempt_id,
            "work_item_id": reservation.get("logical_work_id"),
            "reason": "a durable dispatch reservation exists without a reconciled checkpoint",
        }
    if not in_work_window(spec, now):
        return {"status": "WAIT_WORK_WINDOW", "requires_model": False}
    runtime_block = state.get("runtime_block")
    if isinstance(runtime_block, dict):
        recovery = classify_recovery(runtime_block)
        if recovery["action"] == "WAIT_HUMAN_DECISION":
            return {"status": "HUMAN_DECISION_REQUIRED", **recovery}
        if recovery["action"] in NO_MODEL_ACTIONS:
            return {"status": "RECOVERY_READY", **recovery}
        if recovery["action"].startswith("WAIT_"):
            return {"status": recovery["action"], **recovery}
    by_id = {row["work_item_id"]: row for row in state["work_items"]}
    eligible = [
        row for row in state["work_items"]
        if row["status"] in RUNNABLE_WORK and _dependency_ready(row, by_id)
    ]
    if not eligible:
        if all(row["status"] in TERMINAL_WORK for row in state["work_items"]):
            obligations = {row["status"] for row in state["obligations"]}
            if obligations == {"VERIFIED_RESOLVED"}:
                return {
                    "status": "HUMAN_ACCEPTANCE_REQUIRED"
                    if spec["human_acceptance_required"] else "COMPLETION_GATE_READY",
                    "requires_model": False,
                }
        blocked = [row["work_item_id"] for row in state["work_items"] if row["status"] == "BLOCKED"]
        return {
            "status": "NO_ELIGIBLE_READY_WORK",
            "blocked_work_items": blocked,
            "reason": "unmet dependencies or affected-subgraph strategy exhaustion",
        }
    selected = eligible[0]
    plan = _work_action(selected)
    if plan["requires_model"]:
        work_spec = next(row for row in spec["work_items"] if row["work_item_id"] == selected["work_item_id"])
        provider = work_spec["provider"]
        if provider == "NONE":
            raise GoalRunnerError("model action cannot use provider NONE")
        launches = int(state.get("resource_accounting", {}).get(provider, {}).get("launches_in_window", 0))
        last_value = state.get("resource_accounting", {}).get(provider, {}).get("last_launch_at")
        last_launch = datetime.fromisoformat(last_value) if isinstance(last_value, str) else None
        retry_value = state.get("resource_accounting", {}).get(provider, {}).get("quota_retry_at")
        quota_retry = datetime.fromisoformat(retry_value) if isinstance(retry_value, str) else None
        capacity = goal_continuity.capacity_decision(
            spec["resource_policy"]["providers"][provider], now=now,
            last_launch_at=last_launch, launches_in_window=launches,
            quota_retry_at=quota_retry,
        )
        if capacity["status"] != "DISPATCH":
            return {"status": capacity["status"], "provider": provider, **capacity}
        plan["provider"] = provider
        plan["capacity_basis"] = capacity["basis"]
    return {
        "status": "TRIAL_ACTION_READY" if trial else "ACTION_READY",
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "work_item_id": selected["work_item_id"],
        "milestone_id": selected["milestone_id"],
        **plan,
    }


def validated_bound_order(
    spec: dict[str, Any], state: dict[str, Any], action: dict[str, Any], *, repo: Path
) -> tuple[Path, dict[str, Any], str]:
    """Resolve one Runner-owned sealed order; never synthesize an order from Goal prose."""
    if action.get("status") != "ACTION_READY":
        raise GoalRunnerError("only an ACTION_READY decision can bind a dispatch")
    work = next(
        row for row in state["work_items"]
        if row["work_item_id"] == action["work_item_id"]
    )
    binding = work.get("dispatch_binding")
    if not isinstance(binding, dict):
        raise GoalRunnerError("selected work item has no Runner-owned sealed dispatch binding")
    order_path = Path(binding["order_path"])
    if not order_path.is_absolute():
        order_path = repo / order_path
    try:
        order_path.resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise GoalRunnerError("sealed order is outside the repository evidence root") from exc
    if not order_path.is_file():
        raise GoalRunnerError("sealed order file is unavailable")
    digest = hashlib.sha256(order_path.read_bytes()).hexdigest()
    if digest != binding["order_sha256"]:
        raise GoalRunnerError("sealed order digest differs from the Runner state binding")
    order = goal_continuity.load_json(order_path)
    if order.get("schema_version") != "kgnote.linux-worker-order.v1":
        raise GoalRunnerError("sealed order has an unsupported schema")
    if order.get("event_id") != binding["order_event_id"]:
        raise GoalRunnerError("sealed order event identity differs from the Runner state binding")
    attempt_id = (
        f"attempt-{spec['goal_version']}-{action['work_item_id']}-"
        f"{binding['order_event_id']}"
    )
    return order_path, order, attempt_id


def reserve_dispatch(
    spec: dict[str, Any], state: dict[str, Any], action: dict[str, Any],
    *, state_path: Path, ledger_path: Path, repo: Path, occurred_at: str,
) -> tuple[dict[str, Any], Path, str]:
    """Persist an exact-once reservation before an external worker can start."""
    order_path, order, attempt_id = validated_bound_order(spec, state, action, repo=repo)
    event_type = "MODEL_ATTEMPT_STARTED" if action.get("requires_model") else "WORK_STATE_TRANSITION"
    event, appended = goal_continuity.append_ledger_event(
        ledger_path,
        event_id=f"{attempt_id}-reserved",
        event_type=event_type,
        occurred_at=occurred_at,
        goal_id=spec["goal_id"],
        goal_version=spec["goal_version"],
        logical_work_id=action["work_item_id"],
        attempt_id=attempt_id,
        payload={
            "operation": "DISPATCH_RESERVED",
            "action": action["action"],
            "provider": action.get("provider"),
            "order_event_id": order["event_id"],
            "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
        },
    )
    if not appended:
        raise GoalRunnerError("dispatch was already reserved; reconcile it instead of redispatching")
    updated = deepcopy(state)
    work = next(
        row for row in updated["work_items"]
        if row["work_item_id"] == action["work_item_id"]
    )
    work["status"] = "DISPATCHING"
    work["active_attempt_id"] = attempt_id
    work["attempts"] = int(work.get("attempts", 0)) + 1
    if action.get("requires_model"):
        provider = action["provider"]
        accounting = updated.setdefault("resource_accounting", {}).setdefault(provider, {})
        accounting["launches_in_window"] = int(accounting.get("launches_in_window", 0)) + 1
        accounting["last_launch_at"] = occurred_at
    updated["event_cursor"] = {
        "sequence": event["sequence"], "event_sha256": event["event_sha256"]
    }
    goal_continuity.validate_runner_state(updated, spec)
    goal_continuity.atomic_write_json(state_path, updated)
    return updated, order_path, attempt_id


def record_route_outcome(
    spec: dict[str, Any], state: dict[str, Any], *, state_path: Path,
    work_item_id: str, attempt_id: str, route_exit_code: int, occurred_at: str,
) -> dict[str, Any]:
    """Record routing only; checkpoint reconciliation decides the worker outcome."""
    updated = deepcopy(state)
    work = next(row for row in updated["work_items"] if row["work_item_id"] == work_item_id)
    if work.get("active_attempt_id") != attempt_id or work.get("status") != "DISPATCHING":
        raise GoalRunnerError("route outcome does not match the active dispatch reservation")
    if route_exit_code == 0:
        work["status"] = "DISPATCHED"
    else:
        work["status"] = "BLOCKED"
        updated["runtime_block"] = {
            "failure_class": "UNKNOWN_OUTCOME",
            "work_item_id": work_item_id,
            "attempt_id": attempt_id,
            "route_exit_code": route_exit_code,
            "observed_at": occurred_at,
        }
    goal_continuity.validate_runner_state(updated, spec)
    goal_continuity.atomic_write_json(state_path, updated)
    return updated


def apply_obligation_progress(
    state: dict[str, Any],
    spec: dict[str, Any],
    *,
    work_item_id: str,
    obligation_id: str,
    progress_class: str,
) -> dict[str, Any]:
    """Update one subgraph; strategy exhaustion never globally ends the Goal."""
    updated = deepcopy(state)
    obligation = next(row for row in updated["obligations"] if row["obligation_id"] == obligation_id)
    transition = goal_continuity.progress_transition(
        obligation.get("consecutive_no_progress"), progress_class
    )
    obligation.update({
        "last_progress_class": progress_class,
        "consecutive_no_progress": transition["consecutive_no_progress"],
    })
    if progress_class == "VERIFIED_RESOLVED":
        obligation["status"] = "VERIFIED_RESOLVED"
    elif progress_class == "REGRESSION":
        obligation["status"] = "OPEN"
    work = next(row for row in updated["work_items"] if row["work_item_id"] == work_item_id)
    if transition["strategy_adjustment_required"]:
        work["strategy_adjustments"] = int(work.get("strategy_adjustments", 0)) + 1
        # A strategy adjustment starts a new observation pair. Without this
        # reset, every later no-progress event would count as another change
        # even though the new strategy had not received two observations.
        obligation["consecutive_no_progress"] = 0
        work["status"] = (
            "BLOCKED"
            if work["strategy_adjustments"] >= spec["recovery_policy"]["max_strategy_adjustments"]
            else "REPAIR_REQUIRED"
        )
    return updated


def run_once(
    spec_path: Path,
    state_path: Path,
    ledger_path: Path,
    *,
    comments_path: Path | None,
    trial: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    spec = goal_continuity.load_json(spec_path)
    state = goal_continuity.load_json(state_path)
    ledger = goal_continuity.read_ledger(ledger_path)
    comments = (
        json.loads(comments_path.read_text(encoding="utf-8"))
        if comments_path else github_control.fetch_issue_comments(spec)
    )
    if not isinstance(comments, list):
        raise GoalRunnerError("comments fixture must be a JSON list")
    authority = github_control.resolve_authority(comments, spec)
    return next_action(spec, state, ledger, authority, now=now or datetime.now(ZONE), trial=trial)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--comments", type=Path)
    parser.add_argument("--trial", action="store_true")
    args = parser.parse_args()
    result = run_once(
        args.spec, args.state, args.ledger,
        comments_path=args.comments, trial=args.trial,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] not in {"GO_LIVE_NOT_AUTHORIZED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
