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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import github_product_goal_control as github_control
import goal_continuity
import goal_notifications
import linux_worker_router


ZONE = ZoneInfo("Asia/Taipei")
TERMINAL_WORK = {"VERIFIED", "CLOSED", "SUPERSEDED"}
RUNNABLE_WORK = {"PLANNED", "READY", "REPAIR_REQUIRED", "VERIFY_REQUIRED", "PUBLISH_REQUIRED"}
NO_MODEL_ACTIONS = {"RECONCILE_CHECKPOINT", "RETRY_PUBLICATION", "RETRY_COMPLETION_GATE"}


class GoalRunnerError(goal_continuity.GoalContractError):
    pass


def _state_patch(state: dict[str, Any]) -> dict[str, Any]:
    """Return only mutable Runner-owned fields for crash-safe ledger replay."""
    return {
        key: deepcopy(state[key])
        for key in (
            "milestone_id", "lifecycle", "authority_lease", "authority_record",
            "work_items", "obligations", "go_live_authorized", "dependency_receipts",
        )
        if key in state
    } | {
        key: deepcopy(state[key])
        for key in ("resource_accounting",)
        if key in state
    } | {"runtime_block": deepcopy(state.get("runtime_block"))}


def synchronize_state_from_ledger(
    spec: dict[str, Any], state: dict[str, Any], ledger: list[dict[str, Any]],
    *, state_path: Path | None = None,
) -> dict[str, Any]:
    """Replay committed Runner patches when a crash left the JSON state behind."""
    rows = goal_continuity.validate_ledger_binding(ledger, state, spec)
    updated = deepcopy(state)
    start = updated["event_cursor"]["sequence"]
    mutable = {
        "milestone_id", "lifecycle", "authority_lease", "authority_record",
        "work_items", "obligations", "go_live_authorized",
        "dependency_receipts", "resource_accounting", "runtime_block",
    }
    for event in rows[start:]:
        patch = event["payload"].get("state_patch")
        if patch is not None:
            if not isinstance(patch, dict) or set(patch) - mutable:
                raise GoalRunnerError("ledger state_patch contains non-Runner-owned fields")
            for key, value in patch.items():
                if key == "runtime_block" and value is None:
                    updated.pop(key, None)
                else:
                    updated[key] = deepcopy(value)
        updated["event_cursor"] = {
            "sequence": event["sequence"], "event_sha256": event["event_sha256"]
        }
    goal_continuity.validate_runner_state(updated, spec)
    if state_path is not None and updated != state:
        goal_continuity.atomic_write_json(state_path, updated)
    return updated


def _lifecycle_patch(
    state: dict[str, Any], *, lifecycle: str, changed_at: str, reason: str,
    authority_record: dict[str, Any] | None = None,
    authority_lease: str | None = None, go_live_authorized: bool | None = None,
) -> dict[str, Any]:
    updated = deepcopy(state)
    if authority_record is not None:
        updated["authority_record"] = deepcopy(authority_record)
    if authority_lease is not None:
        updated["authority_lease"] = authority_lease
    if go_live_authorized is not None:
        updated["go_live_authorized"] = go_live_authorized
    if updated["lifecycle"]["state"] != lifecycle:
        revision = int(updated["lifecycle"]["revision"]) + 1
    else:
        revision = int(updated["lifecycle"]["revision"])
    updated["lifecycle"] = {
        "state": lifecycle, "revision": revision,
        "changed_at": changed_at, "reason": reason,
    }
    return updated


def _authority_event_fields(
    spec: dict[str, Any], record: dict[str, Any], *, suffix: str,
    event_type: str, payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": f"goal-authority-{record['comment_id']}-{suffix}",
        "event_type": event_type,
        "occurred_at": record["created_at"],
        "goal_id": spec["goal_id"], "goal_version": spec["goal_version"],
        "logical_work_id": None, "attempt_id": None, "payload": payload,
    }


def _completion_ready(state: dict[str, Any]) -> bool:
    return (
        all(row["status"] in TERMINAL_WORK for row in state["work_items"])
        and all(row["status"] == "VERIFIED_RESOLVED" for row in state["obligations"])
    )


def reconcile_owner_authority(
    spec: dict[str, Any], state: dict[str, Any], authority: dict[str, Any],
    *, state_path: Path, ledger_path: Path,
) -> dict[str, Any]:
    """Durably apply exact Owner commands; parsing alone never changes authority."""
    goal_continuity.validate_goal_spec(spec)
    state = synchronize_state_from_ledger(
        spec, state, goal_continuity.read_ledger(ledger_path), state_path=state_path
    )
    event_ids = {row["event_id"] for row in goal_continuity.read_ledger(ledger_path)}
    for record in authority.get("valid_records", []):
        prefix = f"goal-authority-{record['comment_id']}"
        accepted_event_id = f"{prefix}-accepted"
        rejected_event_id = f"{prefix}-rejected"
        final_suffix = {
            "APPROVE": "lifecycle-2-active",
            "PAUSE": "lifecycle-1-blocked",
            "RESUME": "lifecycle-1-active",
            "REVOKE": "lifecycle-1-blocked",
            "ACCEPT": "lifecycle-1-closed",
            "CLOSE": "lifecycle-1-closed",
        }[record["action"]]
        if rejected_event_id in event_ids or f"{prefix}-{final_suffix}" in event_ids:
            continue
        action = record["action"]
        already_accepted = accepted_event_id in event_ids
        accepted = True
        reason = ""
        current = state["lifecycle"]["state"]
        lease = state["authority_lease"]
        if already_accepted:
            pass  # Resume an already-admitted command after a process interruption.
        elif action == "APPROVE":
            satisfied = {
                row.get("dependency_id") for row in state.get("dependency_receipts", [])
            }
            if set(spec["dependencies"]) - satisfied:
                accepted, reason = False, "APPROVE requires exact receipts for every Goal dependency"
            elif current not in {"PLANNED", "APPROVAL_REQUIRED"} or lease == "REVOKED":
                accepted, reason = False, "APPROVE requires an unapproved, non-revoked Goal version"
        elif action == "PAUSE":
            if lease != "ACTIVE" or current in {"CLOSED", "ACCEPTANCE_REQUIRED"}:
                accepted, reason = False, "PAUSE requires an active, non-terminal Goal"
        elif action == "RESUME":
            if lease != "PAUSED" or current != "BLOCKED":
                accepted, reason = False, "RESUME requires an Owner-paused BLOCKED Goal"
        elif action == "REVOKE":
            if lease == "REVOKED" or current == "CLOSED":
                accepted, reason = False, "REVOKE requires a non-terminal authority lease"
        elif action == "ACCEPT":
            if current != "ACCEPTANCE_REQUIRED" or not _completion_ready(state):
                accepted, reason = False, "ACCEPT requires evidence-backed completion and ACCEPTANCE_REQUIRED"
        elif action == "CLOSE":
            if spec["human_acceptance_required"] or current != "ACCEPTANCE_REQUIRED" or not _completion_ready(state):
                accepted, reason = False, "CLOSE cannot bypass required human acceptance or completion evidence"

        authority_payload = {
            "accepted": accepted, "action": action,
            "authority_comment_id": record["comment_id"],
            "authority_body_sha256": record["body_sha256"],
            "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
            "go_live_authorized": accepted and action in {"APPROVE", "RESUME"},
        }
        if not accepted:
            authority_payload["rejection_reason"] = reason
            goal_continuity.append_ledger_event(
                ledger_path, **_authority_event_fields(
                    spec, record, suffix="rejected", event_type="GOAL_AUTHORITY_VERIFIED",
                    payload=authority_payload,
                )
            )
            state = synchronize_state_from_ledger(
                spec, state, goal_continuity.read_ledger(ledger_path), state_path=state_path
            )
            event_ids = {row["event_id"] for row in goal_continuity.read_ledger(ledger_path)}
            continue

        authority_event, _ = goal_continuity.append_ledger_event(
            ledger_path, **_authority_event_fields(
                spec, record, suffix="accepted", event_type="GOAL_AUTHORITY_VERIFIED",
                payload=authority_payload,
            )
        )
        transitions: list[tuple[str, str, str, bool]] = []
        if action == "APPROVE":
            transitions = [
                ("APPROVED", "ACTIVE", "exact Owner approval admitted", True),
                ("ACTIVE", "ACTIVE", "Runner activated the approved Goal", True),
            ]
        elif action == "PAUSE":
            transitions = [("BLOCKED", "PAUSED", "exact Owner pause applied", False)]
        elif action == "RESUME":
            transitions = [("ACTIVE", "ACTIVE", "exact Owner resume applied", True)]
        elif action == "REVOKE":
            transitions = [("BLOCKED", "REVOKED", "exact Owner revocation applied", False)]
        elif action in {"ACCEPT", "CLOSE"}:
            closure_evidence_sha256 = authority_event["event_sha256"]
            if action == "ACCEPT":
                acceptance_event, _ = goal_continuity.append_ledger_event(
                    ledger_path, **_authority_event_fields(
                        spec, record, suffix="human-acceptance",
                        event_type="HUMAN_ACCEPTANCE_RECORDED",
                        payload={
                            "authority_comment_id": record["comment_id"],
                            "authority_body_sha256": record["body_sha256"],
                            "authority_effect": "CLOSE_EXACT_GOAL_ONLY",
                        },
                    )
                )
                closure_evidence_sha256 = acceptance_event["event_sha256"]
            receipts = list(state.get("dependency_receipts", []))
            if not any(row.get("dependency_id") == spec["goal_id"] for row in receipts):
                receipts.append({
                    "dependency_id": spec["goal_id"], "status": "CLOSED",
                    "source_kind": "PRODUCT_GOAL_CLOSED",
                    "goal_version": spec["goal_version"],
                    "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
                    "evidence_sha256": closure_evidence_sha256,
                })
            state["dependency_receipts"] = receipts
            transitions = [("CLOSED", lease, f"exact Owner {action.lower()} applied", False)]

        for index, (target, target_lease, transition_reason, live) in enumerate(transitions, start=1):
            state = _lifecycle_patch(
                state, lifecycle=target, changed_at=record["created_at"],
                reason=transition_reason, authority_record=record,
                authority_lease=target_lease, go_live_authorized=live,
            )
            goal_continuity.append_ledger_event(
                ledger_path, **_authority_event_fields(
                    spec, record, suffix=f"lifecycle-{index}-{target.lower()}",
                    event_type="GOAL_LIFECYCLE_TRANSITION",
                    payload={
                        "state": target, "reason": transition_reason,
                        "authority_comment_id": record["comment_id"],
                        "state_patch": _state_patch(state),
                    },
                )
            )
            state = synchronize_state_from_ledger(
                spec, state, goal_continuity.read_ledger(ledger_path), state_path=state_path
            )
            event_ids = {row["event_id"] for row in goal_continuity.read_ledger(ledger_path)}
    history = goal_continuity.reduce_ledger(goal_continuity.read_ledger(ledger_path))[
        "authority_history"
    ]
    unresolved: list[dict[str, Any]] = []
    records = authority.get("valid_records", [])
    if records:
        last = records[-1]
        outcome = next(
            (row for row in reversed(history) if row.get("authority_comment_id") == last["comment_id"]),
            None,
        )
        if isinstance(outcome, dict) and outcome.get("accepted") is False:
            unresolved.append({
                "comment_id": last["comment_id"], "action": last["action"],
                "reason": outcome.get("rejection_reason"),
            })
    return {"state": state, "rejected_transitions": unresolved}


def in_work_window(spec: dict[str, Any], now: datetime) -> bool:
    local = now.astimezone(ZONE)
    window = spec["work_window"]
    current = local.strftime("%H:%M")
    start, end = window["start"], window["end"]
    if start <= end:
        window_weekday = local.weekday()
        inside = start <= current < end
    else:
        # The after-midnight segment belongs to the local date on which the
        # authorized window began.
        window_weekday = (
            local - timedelta(days=1)
        ).weekday() if current < end else local.weekday()
        inside = current >= start or current < end
    return inside and window_weekday in window["weekdays"]


def resource_window_id(spec: dict[str, Any], now: datetime) -> str:
    """Return the stable local work-window identity containing ``now``."""
    local = now.astimezone(ZONE)
    window = spec["work_window"]
    current = local.strftime("%H:%M")
    start_date = local.date()
    if window["start"] > window["end"] and current < window["end"]:
        start_date -= timedelta(days=1)
    return f"{start_date.isoformat()}@{window['start']}-{window['end']}"


def _provider_attempts(
    projection: dict[str, Any], provider: str
) -> list[dict[str, Any]]:
    return [
        row for row in projection.get("model_attempts", {}).values()
        if row.get("provider") == provider and row.get("started") is True
    ]


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
    records = authority.get("valid_records", [])
    approvals = {
        (row["comment_id"], row["body_sha256"]): row
        for row in records
        if row["action"] == "APPROVE" and "activate_runner" in row["permissions"]
    }
    for payload in reversed(projection.get("authority_history", [])):
        identity = (payload.get("authority_comment_id"), payload.get("authority_body_sha256"))
        if (
            payload.get("accepted", True) is True
            and payload.get("action", "APPROVE") == "APPROVE"
            and payload.get("go_live_authorized") is True
            and payload.get("goal_spec_sha256") == goal_continuity.goal_spec_sha256(spec)
            and identity in approvals
        ):
            return payload
    return None


def _dependency_ready(work: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> bool:
    return all(by_id[item]["status"] in TERMINAL_WORK for item in work["dependencies"])


def _work_action(work: dict[str, Any], work_spec: dict[str, Any]) -> dict[str, Any]:
    status = work["status"]
    if status == "PUBLISH_REQUIRED":
        return {"action": "RETRY_PUBLICATION", "requires_model": False}
    if status == "VERIFY_REQUIRED":
        return {"action": "RUN_DETERMINISTIC_VERIFICATION", "requires_model": False}
    if status == "REPAIR_REQUIRED":
        return {"action": "DISPATCH_REPAIR", "requires_model": True, "provider": "codex"}
    kind = work_spec["kind"]
    return {
        "IMPLEMENT": {"action": "DISPATCH_IMPLEMENTATION", "requires_model": True},
        "VERIFY": {"action": "RUN_DETERMINISTIC_VERIFICATION", "requires_model": False},
        "PUBLISH": {"action": "RETRY_PUBLICATION", "requires_model": False},
        "REVIEW": {"action": "DISPATCH_REVIEW", "requires_model": True},
        "REPAIR": {"action": "DISPATCH_REPAIR", "requires_model": True},
        "ACCEPTANCE_PREP": {"action": "RETRY_COMPLETION_GATE", "requires_model": False},
    }[kind]


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
        retry_value = runtime_block.get("retry_at")
        if recovery["action"] == "WAIT_QUOTA_BACKOFF" and isinstance(retry_value, str):
            retry_at = datetime.fromisoformat(retry_value)
            if now >= retry_at:
                return {
                    "status": "RECOVERY_READY",
                    "action": "RESUME_AFTER_QUOTA",
                    "requires_model": False,
                    "work_item_id": runtime_block.get("work_item_id"),
                    "attempt_id": runtime_block.get("attempt_id"),
                    "retry_at": retry_value,
                }
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
    work_spec = next(row for row in spec["work_items"] if row["work_item_id"] == selected["work_item_id"])
    plan = _work_action(selected, work_spec)
    if plan["requires_model"]:
        provider = plan.get("provider", work_spec["provider"])
        if provider == "NONE":
            raise GoalRunnerError("model action cannot use provider NONE")
        current_window = resource_window_id(spec, now)
        attempts = _provider_attempts(projection, provider)
        try:
            started_at = [
                datetime.fromisoformat(str(row["started_at"])) for row in attempts
            ]
        except (KeyError, ValueError) as exc:
            raise GoalRunnerError(
                "model attempt history lacks a valid timezone-bound start"
            ) from exc
        if any(value.tzinfo is None for value in started_at):
            raise GoalRunnerError(
                "model attempt history lacks a valid timezone-bound start"
            )
        launches = sum(
            resource_window_id(spec, value) == current_window
            for value in started_at
        )
        last_launch = max(started_at, default=None)
        retry_value = state.get("resource_accounting", {}).get(provider, {}).get("quota_retry_at")
        quota_retry = datetime.fromisoformat(retry_value) if isinstance(retry_value, str) else None
        capacity = goal_continuity.capacity_decision(
            spec["resource_policy"]["providers"][provider], now=now,
            last_launch_at=last_launch, launches_in_window=launches,
            total_launches=len(attempts),
            quota_retry_at=quota_retry,
        )
        if capacity["status"] != "DISPATCH":
            return {"status": capacity["status"], "provider": provider, **capacity}
        plan["provider"] = provider
        plan["capacity_basis"] = capacity["basis"]
        plan["resource_window_id"] = current_window
        plan["launches_in_window_before"] = launches
        plan["total_launches_before"] = len(attempts)
    return {
        "status": "TRIAL_ACTION_READY" if trial else "ACTION_READY",
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "work_item_id": selected["work_item_id"],
        "milestone_id": selected["milestone_id"],
        **plan,
    }


def resume_after_quota_backoff(
    spec: dict[str, Any], state: dict[str, Any],
    *, state_path: Path, ledger_path: Path, now: datetime,
) -> dict[str, Any]:
    """Durably clear one elapsed provider backoff without launching a model."""
    if now.tzinfo is None:
        raise GoalRunnerError("quota resume time must be timezone-aware")
    if not state_path.is_file():
        raise GoalRunnerError("durable Runner state is unavailable")
    durable_state = goal_continuity.load_json(state_path)
    goal_continuity.validate_runner_state(durable_state, spec)
    if goal_continuity.canonical_json_bytes(durable_state) != (
        goal_continuity.canonical_json_bytes(state)
    ):
        raise GoalRunnerError("in-memory Runner state is stale relative to durable state")
    ledger = goal_continuity.read_ledger(ledger_path)
    state = synchronize_state_from_ledger(
        spec, durable_state, ledger, state_path=state_path
    )
    runtime_block = state.get("runtime_block")
    if not isinstance(runtime_block, dict):
        return {"status": "QUOTA_BACKOFF_ALREADY_RESUMED", "requires_model": False}
    failure_class = str(runtime_block.get("failure_class") or "")
    if failure_class not in {"QUOTA_EXHAUSTED", "RATE_LIMITED", "USAGE_LIMIT_REACHED"}:
        raise GoalRunnerError("runtime block is not a provider quota backoff")
    retry_value = runtime_block.get("retry_at")
    if not isinstance(retry_value, str):
        raise GoalRunnerError("quota backoff lacks a durable retry time")
    try:
        retry_at = datetime.fromisoformat(retry_value)
    except ValueError as exc:
        raise GoalRunnerError("quota backoff retry time is invalid") from exc
    if retry_at.tzinfo is None:
        raise GoalRunnerError("quota backoff retry time must be timezone-aware")
    if now < retry_at:
        raise GoalRunnerError("quota backoff has not elapsed")
    work_item_id = runtime_block.get("work_item_id")
    attempt_id = runtime_block.get("attempt_id")
    if not isinstance(work_item_id, str) or not isinstance(attempt_id, str):
        raise GoalRunnerError("quota backoff lacks exact Work Item/attempt identity")
    work_spec = next(
        (row for row in spec["work_items"] if row["work_item_id"] == work_item_id),
        None,
    )
    if work_spec is None or work_spec["provider"] not in {"codex", "claude"}:
        raise GoalRunnerError("quota backoff Work Item has no model provider")

    updated = deepcopy(state)
    updated.pop("runtime_block", None)
    accounting = updated.get("resource_accounting", {}).get(work_spec["provider"])
    if isinstance(accounting, dict):
        accounting.pop("quota_retry_at", None)
    event, appended = goal_continuity.append_ledger_event(
        ledger_path,
        event_id=f"{attempt_id}-quota-backoff-resumed",
        event_type="WORK_STATE_TRANSITION",
        occurred_at=now.isoformat(),
        goal_id=spec["goal_id"],
        goal_version=spec["goal_version"],
        logical_work_id=work_item_id,
        attempt_id=attempt_id,
        payload={
            "operation": "QUOTA_BACKOFF_RESUMED",
            "failure_class": failure_class,
            "retry_at": retry_value,
            "provider": work_spec["provider"],
            "state_patch": _state_patch(updated),
        },
    )
    if not appended:
        raise GoalRunnerError("quota resume event already exists; reconcile state first")
    updated["event_cursor"] = {
        "sequence": event["sequence"], "event_sha256": event["event_sha256"]
    }
    goal_continuity.validate_runner_state(updated, spec)
    goal_continuity.atomic_write_json(state_path, updated)
    return {
        "status": "QUOTA_BACKOFF_RESUMED",
        "requires_model": False,
        "work_item_id": work_item_id,
        "attempt_id": attempt_id,
        "provider": work_spec["provider"],
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
    bindings = work.get("dispatch_bindings")
    binding_index = 0
    if isinstance(bindings, dict):
        candidates = bindings.get(action["action"])
        if not isinstance(candidates, list) or not candidates:
            raise GoalRunnerError(
                f"selected work item has no sealed binding for {action['action']}"
            )
        binding_index = int(work.get("dispatch_binding_cursor", {}).get(action["action"], 0))
        if binding_index >= len(candidates):
            raise GoalRunnerError(
                f"sealed binding queue is exhausted for {action['action']}"
            )
        binding = candidates[binding_index]
    else:
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
    try:
        parsed_order = linux_worker_router.WorkerOrder.from_dict(order)
    except linux_worker_router.RoutingError as exc:
        raise GoalRunnerError(f"sealed order is not a valid Linux worker order: {exc}") from exc
    expected_stage = {
        "DISPATCH_IMPLEMENTATION": "codex", "DISPATCH_REPAIR": "codex",
        "DISPATCH_REVIEW": "claude", "RETRY_PUBLICATION": "publisher",
        "RUN_DETERMINISTIC_VERIFICATION": "publisher",
        "RETRY_COMPLETION_GATE": "publisher",
    }.get(action["action"])
    if expected_stage is not None and parsed_order.stage != expected_stage:
        raise GoalRunnerError(
            f"{action['action']} requires the {expected_stage} worker profile"
        )
    if expected_stage in {"codex", "claude"} and (
        action.get("requires_model") is not True
        or action.get("provider") != expected_stage
    ):
        raise GoalRunnerError(
            f"{action['action']} requires model accounting for provider {expected_stage}"
        )
    if expected_stage == "publisher" and action.get("requires_model") is not False:
        raise GoalRunnerError(f"{action['action']} is a deterministic publisher action")
    if order.get("event_id") != binding["order_event_id"]:
        raise GoalRunnerError("sealed order event identity differs from the Runner state binding")
    attempt_number = int(work.get("attempts", 0)) + 1
    attempt_id = f"attempt-{spec['goal_version']}-{action['work_item_id']}-{attempt_number}"
    return order_path, order, attempt_id


def reserve_dispatch(
    spec: dict[str, Any], state: dict[str, Any], action: dict[str, Any],
    *, state_path: Path, ledger_path: Path, repo: Path, occurred_at: str,
) -> tuple[dict[str, Any], Path, str]:
    """Persist an exact-once reservation before an external worker can start."""
    try:
        occurred = datetime.fromisoformat(occurred_at)
    except ValueError as exc:
        raise GoalRunnerError("dispatch reservation time is invalid") from exc
    if occurred.tzinfo is None:
        raise GoalRunnerError("dispatch reservation time must be timezone-aware")

    # Planning is read-only and can become stale while admission checks run.
    # Rebuild from the durable ledger and recheck every launch boundary at the
    # final reservation point, before an external worker can start.
    if not state_path.is_file():
        raise GoalRunnerError("durable Runner state is unavailable")
    durable_state = goal_continuity.load_json(state_path)
    goal_continuity.validate_runner_state(durable_state, spec)
    if goal_continuity.canonical_json_bytes(durable_state) != (
        goal_continuity.canonical_json_bytes(state)
    ):
        raise GoalRunnerError("in-memory Runner state is stale relative to durable state")
    ledger = goal_continuity.read_ledger(ledger_path)
    state = synchronize_state_from_ledger(
        spec, durable_state, ledger, state_path=state_path
    )
    projection = goal_continuity.reduce_ledger(ledger)
    if _unreconciled_dispatch(projection) is not None:
        raise GoalRunnerError(
            "an existing dispatch reservation must be reconciled before another dispatch"
        )
    if (
        state["lifecycle"]["state"] != "ACTIVE"
        or state["authority_lease"] != "ACTIVE"
        or state["go_live_authorized"] is not True
        or not isinstance(state.get("authority_record"), dict)
    ):
        raise GoalRunnerError("dispatch requires an active exact Product Goal authority")
    if not in_work_window(spec, occurred):
        raise GoalRunnerError("dispatch reservation is outside the authorized work window")
    if isinstance(state.get("runtime_block"), dict):
        raise GoalRunnerError(
            "dispatch is blocked by a durable runtime recovery condition"
        )

    by_id = {row["work_item_id"]: row for row in state["work_items"]}
    work = by_id.get(action.get("work_item_id"))
    if (
        work is None
        or work["status"] not in RUNNABLE_WORK
        or not _dependency_ready(work, by_id)
        or work.get("active_attempt_id") is not None
    ):
        raise GoalRunnerError("planned action is no longer an eligible Work Item")
    if any(
        row["work_item_id"] != work["work_item_id"]
        and row["status"] in {"DISPATCHING", "DISPATCHED"}
        for row in state["work_items"]
    ):
        raise GoalRunnerError("single-model concurrency is already occupied")
    work_spec = next(
        row for row in spec["work_items"]
        if row["work_item_id"] == work["work_item_id"]
    )
    live_plan = _work_action(work, work_spec)
    live_provider = live_plan.get("provider", work_spec["provider"])
    if (
        action.get("action") != live_plan["action"]
        or action.get("requires_model") is not live_plan["requires_model"]
        or (
            live_plan["requires_model"]
            and action.get("provider") != live_provider
        )
    ):
        raise GoalRunnerError("planned action no longer matches the immutable Work Item")

    if live_plan["requires_model"]:
        attempts = _provider_attempts(projection, live_provider)
        try:
            started_at = [
                datetime.fromisoformat(str(row["started_at"])) for row in attempts
            ]
        except (KeyError, ValueError) as exc:
            raise GoalRunnerError(
                "model attempt history lacks a valid timezone-bound start"
            ) from exc
        if any(value.tzinfo is None for value in started_at):
            raise GoalRunnerError(
                "model attempt history lacks a valid timezone-bound start"
            )
        current_window = resource_window_id(spec, occurred)
        launches = sum(
            resource_window_id(spec, value) == current_window
            for value in started_at
        )
        retry_value = state.get("resource_accounting", {}).get(
            live_provider, {}
        ).get("quota_retry_at")
        quota_retry = (
            datetime.fromisoformat(retry_value)
            if isinstance(retry_value, str) else None
        )
        capacity = goal_continuity.capacity_decision(
            spec["resource_policy"]["providers"][live_provider],
            now=occurred,
            last_launch_at=max(started_at, default=None),
            launches_in_window=launches,
            total_launches=len(attempts),
            quota_retry_at=quota_retry,
        )
        if capacity["status"] != "DISPATCH":
            raise GoalRunnerError(
                f"dispatch no longer satisfies resource policy: {capacity['status']}"
            )
        if (
            action.get("resource_window_id") != current_window
            or action.get("launches_in_window_before") != launches
            or action.get("total_launches_before") != len(attempts)
            or action.get("capacity_basis") != capacity["basis"]
        ):
            raise GoalRunnerError(
                "planned resource evidence is stale; recompute the next action"
            )

    order_path, order, attempt_id = validated_bound_order(spec, state, action, repo=repo)
    event_type = "MODEL_ATTEMPT_STARTED" if action.get("requires_model") else "WORK_STATE_TRANSITION"
    updated = deepcopy(state)
    work = next(
        row for row in updated["work_items"]
        if row["work_item_id"] == action["work_item_id"]
    )
    prior_work_status = work["status"]
    work["status"] = "DISPATCHING"
    work["active_attempt_id"] = attempt_id
    work["attempts"] = int(work.get("attempts", 0)) + 1
    if action.get("requires_model"):
        provider = action["provider"]
        accounting = updated.setdefault("resource_accounting", {}).setdefault(provider, {})
        projection = goal_continuity.reduce_ledger(goal_continuity.read_ledger(ledger_path))
        attempts = _provider_attempts(projection, provider)
        current_window = resource_window_id(spec, occurred)
        accounting["window_id"] = current_window
        accounting["launches_in_window"] = 1 + sum(
            resource_window_id(
                spec, datetime.fromisoformat(str(row["started_at"]))
            ) == current_window
            for row in attempts
        )
        accounting["total_launches"] = len(attempts) + 1
        accounting["last_launch_at"] = occurred_at
    state_patch = _state_patch(updated)
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
            "prior_work_status": prior_work_status,
            "order_event_id": order["event_id"],
            "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
            "state_patch": state_patch,
        },
    )
    if not appended:
        raise GoalRunnerError("dispatch was already reserved; reconcile it instead of redispatching")
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


def _checkpoint_failure_class(
    checkpoint: dict[str, Any], *, repo: Path
) -> str:
    evidence = checkpoint.get("execution_evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("failure_class"), str):
        value = evidence["failure_class"].upper()
        if value in {
            "QUOTA_EXHAUSTED", "RATE_LIMITED", "USAGE_LIMIT_REACHED",
            "WORK_WINDOW_CLOSED", "UNKNOWN_OUTCOME", "TRANSPORT_INTERRUPTED",
            "PUBLICATION_FAILED", "GITHUB_WRITEBACK_FAILED",
            "COMPLETION_GATE_FAILED", "PRODUCT_DECISION_REQUIRED",
        }:
            return value
    reason = str(checkpoint.get("reason") or "").lower()
    if reason == "work_window_deadline":
        return "WORK_WINDOW_CLOSED"
    if reason == "controller_interrupted":
        return "UNKNOWN_OUTCOME"
    text = reason
    for key in ("stdout_path", "stderr_path"):
        raw = checkpoint.get(key)
        if not isinstance(raw, str):
            continue
        path = Path(raw)
        try:
            path.resolve().relative_to(repo.resolve())
        except ValueError:
            continue
        if path.is_file():
            expected = checkpoint.get(key.replace("_path", "_sha256"))
            content = path.read_bytes()
            if isinstance(expected, str) and hashlib.sha256(content).hexdigest() != expected:
                raise GoalRunnerError(f"{key} digest differs from routing checkpoint")
            text += "\n" + content.decode("utf-8", errors="replace").lower()
    if "usage_limit_reached" in text or "quota_exhausted" in text or "http 429" in text:
        return "USAGE_LIMIT_REACHED"
    if "rate limit" in text:
        return "RATE_LIMITED"
    return "DETERMINISTIC_WORKER_FAILURE"


def _append_attempt_event(
    ledger_path: Path, spec: dict[str, Any], reservation: dict[str, Any],
    *, attempt_id: str, suffix: str, event_type: str, payload: dict[str, Any],
) -> None:
    goal_continuity.append_ledger_event(
        ledger_path,
        event_id=f"{attempt_id}-{suffix}", event_type=event_type,
        occurred_at=reservation["reserved_at"],
        goal_id=spec["goal_id"], goal_version=spec["goal_version"],
        logical_work_id=reservation["logical_work_id"], attempt_id=attempt_id,
        payload=payload,
    )


def _failure_usage(checkpoint: dict[str, Any]) -> dict[str, Any]:
    evidence = checkpoint.get("execution_evidence")
    if isinstance(evidence, dict):
        raw = evidence.get("token_usage") or evidence.get("usage")
        if isinstance(raw, dict):
            input_tokens = raw.get("input_tokens")
            output_tokens = raw.get("output_tokens")
            if (
                isinstance(input_tokens, int) and not isinstance(input_tokens, bool)
                and isinstance(output_tokens, int) and not isinstance(output_tokens, bool)
                and input_tokens >= 0 and output_tokens >= 0
            ):
                return {
                    "status": "OBSERVED", "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "source": str(raw.get("source") or "worker_checkpoint"),
                }
    return {
        "status": "UNKNOWN", "input_tokens": None, "output_tokens": None,
        "source": "worker_checkpoint_without_reliable_usage",
    }


def _apply_worker_result(
    spec: dict[str, Any], state: dict[str, Any], result: dict[str, Any],
    *, work_item_id: str,
) -> dict[str, Any]:
    goal_continuity.validate_document(result, "worker-result.schema.json")
    exact = {
        "goal_id": spec["goal_id"], "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "work_item_id": work_item_id,
    }
    if any(result.get(key) != value for key, value in exact.items()):
        raise GoalRunnerError("worker result does not bind the exact Goal/Work Item")
    usage = result["usage"]
    if usage["status"] == "UNKNOWN" and (
        usage["input_tokens"] is not None or usage["output_tokens"] is not None
    ):
        raise GoalRunnerError("UNKNOWN usage cannot carry invented token totals")
    if usage["status"] == "OBSERVED" and (
        usage["input_tokens"] is None or usage["output_tokens"] is None
    ):
        raise GoalRunnerError("OBSERVED usage requires both token totals")

    updated = deepcopy(state)
    work = next(row for row in updated["work_items"] if row["work_item_id"] == work_item_id)
    work_spec = next(row for row in spec["work_items"] if row["work_item_id"] == work_item_id)
    evaluations = result["obligation_evaluations"]
    if len({row["obligation_id"] for row in evaluations}) != len(evaluations):
        raise GoalRunnerError("worker result repeats an obligation evaluation")
    if set(row["obligation_id"] for row in evaluations) - set(work["obligation_ids"]):
        raise GoalRunnerError("worker result evaluates an obligation outside the Work Item")
    if any(row["progress_class"] == "VERIFIED_RESOLVED" for row in evaluations):
        if result["outcome"] != "REVIEW_PASS" or work_spec["kind"] != "REVIEW":
            raise GoalRunnerError("only an independent REVIEW_PASS may verify an obligation")
    verdict = result["review_verdict"]
    if result["outcome"] in {"REVIEW_PASS", "REVIEW_CHANGES_REQUIRED"}:
        expected = "PASS" if result["outcome"] == "REVIEW_PASS" else "CHANGES_REQUIRED"
        if work_spec["kind"] != "REVIEW" or not isinstance(verdict, dict) or verdict["verdict"] != expected:
            raise GoalRunnerError("review outcome lacks a matching independent verdict")
    elif verdict is not None:
        raise GoalRunnerError("non-review work cannot mint a review verdict")
    if result["publication"] is not None and work_spec["kind"] != "PUBLISH":
        raise GoalRunnerError("only a PUBLISH Work Item may record publication")

    for evaluation in evaluations:
        updated = apply_obligation_progress(
            updated, spec, work_item_id=work_item_id,
            obligation_id=evaluation["obligation_id"],
            progress_class=evaluation["progress_class"],
        )
    work = next(row for row in updated["work_items"] if row["work_item_id"] == work_item_id)
    outcome = result["outcome"]
    shared = set(work["obligation_ids"])
    if outcome == "WORK_COMPLETED":
        work["status"] = "VERIFIED"
        if work_spec["kind"] == "REPAIR":
            # A repair re-opens the evidence pipeline for the same stable
            # obligations.  It never self-verifies those obligations.
            specs_by_id = {row["work_item_id"]: row for row in spec["work_items"]}
            for candidate in updated["work_items"]:
                candidate_spec = specs_by_id[candidate["work_item_id"]]
                if candidate["work_item_id"] == work_item_id:
                    continue
                if (
                    int(candidate.get("strategy_adjustments", 0))
                    < spec["recovery_policy"]["max_strategy_adjustments"]
                    and shared.intersection(candidate["obligation_ids"])
                    and candidate_spec["kind"] in {
                    "VERIFY", "PUBLISH", "REVIEW", "ACCEPTANCE_PREP",
                    }
                ):
                    candidate["status"] = "PLANNED"
                    candidate["active_attempt_id"] = None
    elif outcome == "REVIEW_CHANGES_REQUIRED":
        repairs = []
        if work["status"] != "BLOCKED":
            work["status"] = "VERIFIED"
            specs_by_id = {row["work_item_id"]: row for row in spec["work_items"]}
            for candidate in updated["work_items"]:
                candidate_spec = specs_by_id[candidate["work_item_id"]]
                if candidate_spec["kind"] == "REPAIR" and shared.intersection(candidate["obligation_ids"]):
                    candidate["status"] = "READY"
                    repairs.append(candidate)
        if work["status"] != "BLOCKED" and not repairs:
            raise GoalRunnerError("REVIEW_CHANGES_REQUIRED lacks a pre-authorized repair lane")
    elif outcome == "REVIEW_PASS":
        expected = set(work["obligation_ids"])
        resolved = {
            row["obligation_id"] for row in evaluations
            if row["progress_class"] == "VERIFIED_RESOLVED"
        }
        if not expected.issubset(resolved):
            raise GoalRunnerError("REVIEW_PASS must resolve every obligation bound to the review")
        work["status"] = "VERIFIED"
        specs_by_id = {row["work_item_id"]: row for row in spec["work_items"]}
        for candidate in updated["work_items"]:
            candidate_spec = specs_by_id[candidate["work_item_id"]]
            if candidate_spec["kind"] == "REPAIR" and shared.intersection(candidate["obligation_ids"]):
                if candidate["status"] in {"PLANNED", "READY", "BLOCKED"}:
                    candidate["status"] = "SUPERSEDED"
    else:
        work["status"] = "BLOCKED"
        updated["runtime_block"] = {
            "failure_class": "PRODUCT_DECISION_REQUIRED",
            "work_item_id": work_item_id,
            "reason": "worker reported a product decision outside the approved contract",
        }
    work["active_attempt_id"] = None
    return updated


def reconcile_dispatch_checkpoint(
    spec: dict[str, Any], state: dict[str, Any],
    *, state_path: Path, ledger_path: Path, repo: Path,
    attempt_id: str, occurred_at: str,
) -> dict[str, Any]:
    """Consume one exact router checkpoint and make its accounting restart-safe."""
    ledger = goal_continuity.read_ledger(ledger_path)
    state = synchronize_state_from_ledger(spec, state, ledger, state_path=state_path)
    projection = goal_continuity.reduce_ledger(ledger)
    reservation = projection["dispatch_reservations"].get(attempt_id)
    if not isinstance(reservation, dict) or reservation.get("reconciled"):
        raise GoalRunnerError("checkpoint reconciliation lacks one unreconciled reservation")
    reservation_event = next(
        row for row in ledger
        if row["attempt_id"] == attempt_id and row["payload"].get("operation") == "DISPATCH_RESERVED"
    )
    reservation = {**reservation, "reserved_at": reservation_event["occurred_at"]}
    work_item_id = str(reservation["logical_work_id"])
    work = next(row for row in state["work_items"] if row["work_item_id"] == work_item_id)
    work_spec = next(row for row in spec["work_items"] if row["work_item_id"] == work_item_id)
    if work.get("active_attempt_id") != attempt_id:
        raise GoalRunnerError("Runner state active attempt differs from the ledger reservation")

    action = {
        "status": "ACTION_READY", "action": reservation["action"],
        "work_item_id": work_item_id,
        "requires_model": reservation.get("event_type") == "MODEL_ATTEMPT_STARTED",
        "provider": reservation.get("provider"),
    }
    order_path, order, _ = validated_bound_order(spec, state, action, repo=repo)
    checkpoint_path = Path(str(order["checkpoint_path"]))
    if not checkpoint_path.is_absolute():
        checkpoint_path = repo / checkpoint_path
    try:
        checkpoint_path.resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise GoalRunnerError("worker checkpoint is outside the repository evidence root") from exc
    if not checkpoint_path.is_file():
        return {
            "status": "CHECKPOINT_PENDING", "requires_model": False,
            "attempt_id": attempt_id, "work_item_id": work_item_id,
        }
    checkpoint = goal_continuity.load_json(checkpoint_path)
    parsed_order = linux_worker_router.WorkerOrder.from_dict(order)
    if (
        checkpoint.get("event_id") != order["event_id"]
        or checkpoint.get("command_digest") != linux_worker_router.command_digest(parsed_order)
    ):
        raise GoalRunnerError("worker checkpoint identity or command digest mismatch")
    if checkpoint.get("status") == "RUNNING":
        return {
            "status": "CHECKPOINT_RUNNING", "requires_model": False,
            "attempt_id": attempt_id, "work_item_id": work_item_id,
        }

    is_success = checkpoint.get("status") in {"COMPLETED", "ALREADY_COMPLETED"}
    result = None
    result_error = None
    if is_success:
        evidence = checkpoint.get("execution_evidence")
        result = evidence.get("product_goal_result") if isinstance(evidence, dict) else None
        try:
            if not isinstance(result, dict):
                raise GoalRunnerError("completed checkpoint lacks product_goal_result evidence")
            if result.get("order_event_id") != order["event_id"]:
                raise GoalRunnerError("worker result binds a different order event")
            updated = _apply_worker_result(spec, state, result, work_item_id=work_item_id)
        except (GoalRunnerError, goal_continuity.GoalContractError) as exc:
            result_error = str(exc)
            is_success = False

    if reservation.get("event_type") == "MODEL_ATTEMPT_STARTED":
        finish_payload = {
            "outcome": result["outcome"] if is_success and result else "FAILED",
            "checkpoint_status": checkpoint.get("status"),
            "failure_class": None if is_success else (
                "EVIDENCE_INSUFFICIENT" if result_error else _checkpoint_failure_class(checkpoint, repo=repo)
            ),
        }
        _append_attempt_event(
            ledger_path, spec, reservation, attempt_id=attempt_id,
            suffix="finished", event_type="MODEL_ATTEMPT_FINISHED", payload=finish_payload,
        )
        _append_attempt_event(
            ledger_path, spec, reservation, attempt_id=attempt_id,
            suffix="usage", event_type="USAGE_OBSERVED",
            payload=result["usage"] if is_success and result else _failure_usage(checkpoint),
        )
    if is_success and result is not None:
        if result["review_verdict"] is not None:
            _append_attempt_event(
                ledger_path, spec, reservation, attempt_id=attempt_id,
                suffix="review-verdict", event_type="REVIEW_VERDICT_ACCEPTED",
                payload=result["review_verdict"],
            )
        if result["publication"] is not None:
            _append_attempt_event(
                ledger_path, spec, reservation, attempt_id=attempt_id,
                suffix="publication", event_type="RESULT_PUBLICATION_RECORDED",
                payload=result["publication"],
            )
        for evaluation in result["obligation_evaluations"]:
            _append_attempt_event(
                ledger_path, spec, reservation, attempt_id=attempt_id,
                suffix=f"obligation-{evaluation['obligation_id'].lower()}",
                event_type="PRODUCT_OBLIGATION_EVALUATED", payload=evaluation,
            )
        updated_work = next(
            row for row in updated["work_items"] if row["work_item_id"] == work_item_id
        )
        cursor = updated_work.setdefault("dispatch_binding_cursor", {})
        cursor[reservation["action"]] = int(cursor.get(reservation["action"], 0)) + 1
        updated.pop("runtime_block", None)
        outcome = result["outcome"]
    else:
        updated = deepcopy(state)
        updated_work = next(row for row in updated["work_items"] if row["work_item_id"] == work_item_id)
        failure_class = "EVIDENCE_INSUFFICIENT" if result_error else _checkpoint_failure_class(checkpoint, repo=repo)
        updated_work["active_attempt_id"] = None
        updated_work["status"] = str(reservation.get("prior_work_status") or "READY")
        runtime_block: dict[str, Any] = {
            "failure_class": failure_class, "work_item_id": work_item_id,
            "attempt_id": attempt_id, "reason": result_error or checkpoint.get("reason"),
            "observed_at": occurred_at,
        }
        if failure_class in {"QUOTA_EXHAUSTED", "RATE_LIMITED", "USAGE_LIMIT_REACHED"}:
            provider = reservation.get("provider") or work_spec["provider"]
            retry_at = datetime.fromisoformat(occurred_at) + timedelta(
                seconds=spec["resource_policy"]["providers"][provider]["fallback"]["quota_backoff_seconds"]
            )
            runtime_block["retry_at"] = retry_at.isoformat()
            accounting = updated.setdefault("resource_accounting", {}).setdefault(provider, {})
            accounting["quota_retry_at"] = retry_at.isoformat()
        elif failure_class in {"DETERMINISTIC_WORKER_FAILURE", "EVIDENCE_INSUFFICIENT"}:
            counts = updated_work.setdefault("failure_counts", {})
            counts[failure_class] = int(counts.get(failure_class, 0)) + 1
            if result_error:
                cursor = updated_work.setdefault("dispatch_binding_cursor", {})
                cursor[reservation["action"]] = int(cursor.get(reservation["action"], 0)) + 1
            if counts[failure_class] >= spec["recovery_policy"]["max_same_failure_attempts"]:
                updated_work["status"] = "BLOCKED"
        elif failure_class == "PRODUCT_DECISION_REQUIRED":
            updated_work["status"] = "BLOCKED"
            updated = _lifecycle_patch(
                updated, lifecycle="BLOCKED", changed_at=occurred_at,
                reason="worker outcome requires an Owner product decision",
            )
        updated["runtime_block"] = runtime_block
        outcome = failure_class

    reconciliation_payload = {
        "operation": "DISPATCH_RECONCILED", "checkpoint_status": checkpoint.get("status"),
        "outcome": outcome, "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "state_patch": _state_patch(updated),
    }
    _append_attempt_event(
        ledger_path, spec, reservation, attempt_id=attempt_id,
        suffix="checkpoint-reconciled", event_type="CHECKPOINT_RECONCILED",
        payload=reconciliation_payload,
    )
    state = synchronize_state_from_ledger(
        spec, state, goal_continuity.read_ledger(ledger_path), state_path=state_path
    )
    if is_success and _completion_ready(state) and state["lifecycle"]["state"] == "ACTIVE":
        completed = _lifecycle_patch(
            state, lifecycle="ACCEPTANCE_REQUIRED", changed_at=occurred_at,
            reason="all Work Items and stable product obligations are evidence-complete",
        )
        _append_attempt_event(
            ledger_path, spec, reservation, attempt_id=attempt_id,
            suffix="acceptance-required", event_type="GOAL_LIFECYCLE_TRANSITION",
            payload={
                "state": "ACCEPTANCE_REQUIRED",
                "reason": completed["lifecycle"]["reason"],
                "state_patch": _state_patch(completed),
            },
        )
        notice = goal_notifications.build_notification(
            goal_id=spec["goal_id"], goal_version=spec["goal_version"],
            event_kind="FINAL_PRODUCT_ACCEPTANCE_REQUIRED",
            decision_key=goal_continuity.goal_spec_sha256(spec),
            summary="所有已授權 Work Item 與產品義務已有完成證據，等待最終產品驗收。",
            decision_requested="驗收並以 exact Owner ACCEPT 指令結案，或提出產品層級問題。",
            github_issue=spec["github_issue"],
        )
        goal_notifications.queue_decision_notification(
            ledger_path, notice, occurred_at=occurred_at
        )
        state = synchronize_state_from_ledger(
            spec, state, goal_continuity.read_ledger(ledger_path), state_path=state_path
        )
    return {
        "status": "CHECKPOINT_RECONCILED", "requires_model": False,
        "attempt_id": attempt_id, "work_item_id": work_item_id,
        "outcome": outcome, "lifecycle": state["lifecycle"]["state"],
    }


def prepare_next_goal_handoff(
    backlog: dict[str, Any], state: dict[str, Any],
    *, ledger_path: Path, occurred_at: str, github_issue: int,
) -> dict[str, Any]:
    """Queue one decision-only handoff after an evidence-backed Goal closure."""
    if state["lifecycle"]["state"] != "CLOSED":
        return {
            "status": "WAIT_PREVIOUS_CLOSED", "authority_granted": False,
            "reason": "the current Product Goal is not CLOSED",
        }
    receipts = state.get("dependency_receipts", [])
    closed = {
        str(row["dependency_id"])
        for row in receipts if row.get("source_kind") == "PRODUCT_GOAL_CLOSED"
    }
    external = {
        str(row["dependency_id"])
        for row in receipts if row.get("source_kind") == "EXTERNAL_DECISION_RESOLVED"
    }
    decision = goal_continuity.select_next_backlog_goal(
        backlog, closed_goal_ids=closed,
        resolved_external_dependencies=external,
    )
    if decision["status"] != "APPROVAL_REQUIRED":
        return decision
    notice = goal_notifications.build_notification(
        goal_id=decision["goal_id"], goal_version=decision["goal_version"],
        event_kind="NEXT_GOAL_APPROVAL_REQUIRED",
        decision_key=decision["goal_version"],
        summary=(
            f"前一 Product Goal {state['goal_id']} 已以 exact Owner authority 正式結案；"
            f"下一個預排 Goal {decision['goal_id']} 的依賴已滿足。"
        ),
        decision_requested="核准 exact Goal 版本、延後，或要求調整；本通知本身不授權執行。",
        github_issue=github_issue,
    )
    goal_notifications.queue_decision_notification(
        ledger_path, notice, occurred_at=occurred_at
    )
    return {**decision, "notification": notice}


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
