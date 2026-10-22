#!/usr/bin/env python3
"""Pure control-plane primitives for a repository-authorized KGnote Product Goal.

This module deliberately has no model, GitHub, SSH, or deployment adapter.  It
keeps Codex App execution identity as provenance only and makes every durable
Product Goal change replayable from a hash-chained ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import fcntl
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover - production preflight reports this explicitly
    jsonschema = None
    Registry = Resource = None


SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas/product-goal/v1"
LEDGER_SCHEMA_VERSION = "kgnote.product-goal-ledger-event.v1"
RUNNER_SCHEMA_VERSION = "kgnote.product-goal-runner-state.v1"
PRODUCT_IDENTITY = "KGNOTE_PRODUCT_GOAL"
PRODUCT_AUTHORITY = "GITHUB_OWNER_APPROVAL"
PRODUCT_LIFECYCLE_OWNER = "MAC_RUNNER"

LIFECYCLE_STATES = {
    "PLANNED", "APPROVAL_REQUIRED", "APPROVED", "ACTIVE", "BLOCKED",
    "ACCEPTANCE_REQUIRED", "CLOSED",
}
AUTHORITY_LEASES = {"ACTIVE", "PAUSED", "REVOKED"}
PROGRESS_CLASSES = {
    "VERIFIED_RESOLVED",
    "FUNCTIONAL_PROGRESS_UNVERIFIED",
    "NO_OBLIGATION_PROGRESS",
    "EVIDENCE_INSUFFICIENT",
    "REGRESSION",
    "AUTHORITY_CHANGED",
}


class GoalContractError(ValueError):
    """The Product Goal contract or its accounting history is invalid."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def goal_spec_sha256(spec: dict[str, Any]) -> str:
    return sha256_value(spec)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GoalContractError(f"{path}: expected a JSON object")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Durably replace one JSON state file without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_document(value: dict[str, Any], schema_name: str) -> None:
    if jsonschema is None:
        raise GoalContractError("jsonschema is required to validate Product Goal records")
    schema_path = SCHEMA_ROOT / schema_name
    schema = load_json(schema_path)
    local_schemas = [load_json(path) for path in SCHEMA_ROOT.glob("*.schema.json")]
    registry = Registry().with_resources(
        (item["$id"], Resource.from_contents(item)) for item in local_schemas
    )
    try:
        jsonschema.Draft202012Validator(schema, registry=registry).validate(value)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise GoalContractError(f"{schema_name}:{location}: {exc.message}") from exc


def validate_goal_spec(spec: dict[str, Any]) -> None:
    validate_document(spec, "goal-spec.schema.json")
    obligation_ids = [row["obligation_id"] for row in spec["obligations"]]
    if len(obligation_ids) != len(set(obligation_ids)):
        raise GoalContractError("obligation_id values must be unique")
    known = set(obligation_ids)
    work_ids: set[str] = set()
    for work in spec["work_items"]:
        work_id = work["work_item_id"]
        if work_id in work_ids:
            raise GoalContractError(f"duplicate work_item_id: {work_id}")
        work_ids.add(work_id)
        unknown = set(work["obligation_ids"]) - known
        if unknown:
            raise GoalContractError(f"{work_id}: unknown obligations {sorted(unknown)}")
        extra = set(work["allowed_operations"]) - set(spec["allowed_operations"])
        if extra:
            raise GoalContractError(f"{work_id}: operations exceed Goal authority: {sorted(extra)}")
    for work in spec["work_items"]:
        unknown = set(work["dependencies"]) - work_ids
        if unknown:
            raise GoalContractError(
                f"{work['work_item_id']}: unknown work dependencies {sorted(unknown)}"
            )
    repairs = [row for row in spec["work_items"] if row["kind"] == "REPAIR"]
    for work in spec["work_items"]:
        if work["kind"] == "REVIEW" and not any(
            set(work["obligation_ids"]).intersection(row["obligation_ids"])
            for row in repairs
        ):
            raise GoalContractError(
                f"{work['work_item_id']}: REVIEW requires a pre-authorized REPAIR lane"
            )
    for name, policy in spec["resource_policy"]["providers"].items():
        observation = policy["capacity_observation"]
        trusted = observation["status"] == "TRUSTED"
        trusted_fields_present = (
            observation["remaining_percent"] is not None
            and isinstance(observation["source_kind"], str)
            and bool(observation["source_kind"].strip())
            and isinstance(observation["observed_at"], str)
        )
        unobservable_fields_clear = all(
            observation[key] is None
            for key in ("remaining_percent", "source_kind", "observed_at")
        )
        if (trusted and not trusted_fields_present) or (
            not trusted and not unobservable_fields_clear
        ):
            raise GoalContractError(
                f"{name}: TRUSTED capacity requires percentage/source/time; "
                "unobservable capacity requires all three to be null"
            )


def validate_backlog(backlog: dict[str, Any]) -> None:
    validate_document(backlog, "backlog.schema.json")
    items = backlog["items"]
    sequences = [row["sequence"] for row in items]
    if sequences != list(range(1, len(items) + 1)):
        raise GoalContractError("backlog sequence must be contiguous and ordered")
    goal_ids = [row["goal_id"] for row in items]
    if len(goal_ids) != len(set(goal_ids)):
        raise GoalContractError("backlog goal_id values must be unique")
    position = {goal_id: index for index, goal_id in enumerate(goal_ids)}
    for index, item in enumerate(items):
        for dependency in item["dependencies"]:
            if dependency in position and position[dependency] >= index:
                raise GoalContractError(
                    f"{item['goal_id']}: dependency {dependency} is not an earlier Goal"
                )


def select_next_backlog_goal(
    backlog: dict[str, Any],
    *,
    closed_goal_ids: set[str],
    resolved_external_dependencies: set[str],
) -> dict[str, Any]:
    """Select at most one approval candidate; selection itself never authorizes it."""
    validate_backlog(backlog)
    for index, item in enumerate(backlog["items"]):
        if item["goal_id"] in closed_goal_ids:
            continue
        earlier = {row["goal_id"] for row in backlog["items"][:index]}
        if not earlier.issubset(closed_goal_ids):
            return {
                "status": "WAIT_PREVIOUS_CLOSED",
                "goal_id": item["goal_id"],
                "missing_closed_goals": sorted(earlier - closed_goal_ids),
            }
        dependencies = set(item["dependencies"])
        satisfied = closed_goal_ids | resolved_external_dependencies
        if not dependencies.issubset(satisfied):
            return {
                "status": "WAIT_DEPENDENCY",
                "goal_id": item["goal_id"],
                "missing_dependencies": sorted(dependencies - satisfied),
            }
        return {
            "status": "APPROVAL_REQUIRED",
            "goal_id": item["goal_id"],
            "goal_version": item["goal_version"],
            "authority_granted": False,
            "next_action": "publish an Owner decision request; do not execute the Goal",
        }
    return {"status": "BACKLOG_COMPLETE", "authority_granted": False}


def initial_runner_state(
    spec: dict[str, Any],
    *,
    now: str,
    codex_app_goal_provenance: dict[str, Any] | None = None,
    dependency_receipts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create an unapproved state. App provenance never supplies authority."""
    validate_goal_spec(spec)
    first_milestone = spec["work_items"][0]["milestone_id"] if spec["work_items"] else None
    return {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "identity_kind": PRODUCT_IDENTITY,
        "authority_kind": PRODUCT_AUTHORITY,
        "lifecycle_owner": PRODUCT_LIFECYCLE_OWNER,
        "goal_id": spec["goal_id"],
        "active_goal": spec["active_goal"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_spec_sha256(spec),
        "milestone_id": first_milestone,
        "lifecycle": {
            "state": "APPROVAL_REQUIRED",
            "revision": 0,
            "changed_at": now,
            "reason": "exact GitHub Owner approval has not been read back",
        },
        "authority_lease": "PAUSED",
        "authority_record": None,
        "work_items": [
            {
                "work_item_id": row["work_item_id"],
                "milestone_id": row["milestone_id"],
                # A repair lane is dormant until an independent review or a
                # deterministic gate activates it.  This prevents a static
                # Goal DAG from running repair work after a clean PASS.
                "status": "BLOCKED" if row["kind"] == "REPAIR" else "PLANNED",
                "dependencies": deepcopy(row["dependencies"]),
                "obligation_ids": deepcopy(row["obligation_ids"]),
                "attempts": 0,
                "strategy_adjustments": 0,
                "failure_counts": {},
            }
            for row in spec["work_items"]
        ],
        "obligations": [
            {
                "obligation_id": row["obligation_id"],
                "semantic_key": row["semantic_key"],
                "status": "OPEN",
                "last_progress_class": None,
                "consecutive_no_progress": 0,
            }
            for row in spec["obligations"]
        ],
        "event_cursor": {"sequence": 0, "event_sha256": None},
        "go_live_authorized": False,
        "dependency_receipts": deepcopy(dependency_receipts or []),
        "codex_app_goal_provenance": deepcopy(codex_app_goal_provenance),
    }


def _event_content(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key != "event_sha256"}


def event_sha256(event: dict[str, Any]) -> str:
    return sha256_value(_event_content(event))


def verify_ledger(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    previous: str | None = None
    seen: dict[str, str] = {}
    for expected_sequence, event in enumerate(events, start=1):
        validate_document(event, "ledger-event.schema.json")
        if event["sequence"] != expected_sequence:
            raise GoalContractError(
                f"ledger sequence {event['sequence']} is not expected {expected_sequence}"
            )
        if event["previous_event_sha256"] != previous:
            raise GoalContractError(f"ledger chain mismatch at event {event['event_id']}")
        digest = event_sha256(event)
        if event["event_sha256"] != digest:
            raise GoalContractError(f"ledger digest mismatch at event {event['event_id']}")
        prior = seen.get(event["event_id"])
        if prior is not None:
            raise GoalContractError(f"duplicate event_id: {event['event_id']}")
        seen[event["event_id"]] = digest
        verified.append(deepcopy(event))
        previous = digest
    return verified


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        text = handle.read()
    return _parse_ledger_text(text)


def _parse_ledger_text(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise GoalContractError(f"ledger line {line_number}: expected object")
        events.append(value)
    return verify_ledger(events)


def prepare_ledger_event(
    existing: list[dict[str, Any]],
    *,
    event_id: str,
    event_type: str,
    occurred_at: str,
    goal_id: str,
    goal_version: str,
    logical_work_id: str | None,
    attempt_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    verified = verify_ledger(existing)
    event = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "event_id": event_id,
        "sequence": len(verified) + 1,
        "previous_event_sha256": verified[-1]["event_sha256"] if verified else None,
        "event_sha256": "",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "goal_id": goal_id,
        "goal_version": goal_version,
        "logical_work_id": logical_work_id,
        "attempt_id": attempt_id,
        "payload": deepcopy(payload),
    }
    event["event_sha256"] = event_sha256(event)
    validate_document(event, "ledger-event.schema.json")
    return event


def append_ledger_event(path: Path, **fields: Any) -> tuple[dict[str, Any], bool]:
    """Append exactly once; return (event, appended). Conflicting replay fails closed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        existing = _parse_ledger_text(handle.read())
        duplicate = next(
            (row for row in existing if row["event_id"] == fields["event_id"]),
            None,
        )
        if duplicate is not None:
            comparable = {
                key: fields[key]
                for key in (
                    "event_id", "event_type", "occurred_at", "goal_id", "goal_version",
                    "logical_work_id", "attempt_id", "payload",
                )
            }
            stored = {key: duplicate[key] for key in comparable}
            if canonical_json_bytes(stored) != canonical_json_bytes(comparable):
                raise GoalContractError(
                    f"event_id replay changed payload: {fields['event_id']}"
                )
            return duplicate, False
        event = prepare_ledger_event(existing, **fields)
        handle.seek(0, os.SEEK_END)
        handle.write(canonical_json_bytes(event).decode("utf-8") + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event, True


def reduce_ledger(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Project separate accounting dimensions without inventing equivalence."""
    rows = verify_ledger(events)
    result: dict[str, Any] = {
        "event_count": len(rows),
        "model_attempts": {},
        "dispatch_reservations": {},
        "usage": {},
        "review_verdicts": [],
        "publications": {},
        "obligations": {},
        "notifications": {},
        "lifecycle": None,
        "authority": None,
        "authority_history": [],
    }
    for event in rows:
        kind, payload = event["event_type"], event["payload"]
        attempt_id = event["attempt_id"]
        if payload.get("operation") == "DISPATCH_RESERVED" and attempt_id:
            result["dispatch_reservations"][attempt_id] = {
                "event_type": kind,
                "logical_work_id": event["logical_work_id"],
                **deepcopy(payload),
            }
        elif payload.get("operation") == "DISPATCH_RECONCILED" and attempt_id:
            result["dispatch_reservations"].setdefault(attempt_id, {}).update(
                {"reconciled": True, **deepcopy(payload)}
            )
        if kind == "MODEL_ATTEMPT_STARTED" and attempt_id:
            result["model_attempts"].setdefault(attempt_id, {}).update(
                {"started": True, "logical_work_id": event["logical_work_id"]}
            )
        elif kind == "MODEL_ATTEMPT_FINISHED" and attempt_id:
            result["model_attempts"].setdefault(attempt_id, {}).update(
                {"finished": True, **deepcopy(payload)}
            )
        elif kind == "USAGE_OBSERVED" and attempt_id:
            result["usage"][attempt_id] = deepcopy(payload)
        elif kind == "REVIEW_VERDICT_ACCEPTED":
            result["review_verdicts"].append(deepcopy(payload))
        elif kind == "RESULT_PUBLICATION_RECORDED" and event["logical_work_id"]:
            result["publications"][event["logical_work_id"]] = deepcopy(payload)
        elif kind == "PRODUCT_OBLIGATION_EVALUATED":
            progress = payload.get("progress_class")
            if progress not in PROGRESS_CLASSES:
                raise GoalContractError(f"unknown progress_class: {progress}")
            result["obligations"][payload["obligation_id"]] = deepcopy(payload)
        elif kind.startswith("NOTIFICATION_"):
            notice_id = payload.get("notification_id")
            if notice_id:
                result["notifications"].setdefault(notice_id, {}).update(
                    {"last_event": kind, **deepcopy(payload)}
                )
        elif kind == "GOAL_LIFECYCLE_TRANSITION":
            if payload.get("state") not in LIFECYCLE_STATES:
                raise GoalContractError(f"unknown lifecycle state: {payload.get('state')}")
            result["lifecycle"] = deepcopy(payload)
        elif kind == "GOAL_AUTHORITY_VERIFIED":
            result["authority_history"].append(deepcopy(payload))
            if payload.get("accepted") is not False:
                result["authority"] = deepcopy(payload)
    result["event_cursor"] = {
        "sequence": len(rows),
        "event_sha256": rows[-1]["event_sha256"] if rows else None,
    }
    return result


def capacity_decision(
    provider_policy: dict[str, Any],
    *,
    now: datetime,
    last_launch_at: datetime | None,
    launches_in_window: int,
    quota_retry_at: datetime | None = None,
) -> dict[str, Any]:
    """Use trusted account percentage when available; otherwise a bounded fallback."""
    if quota_retry_at is not None and now < quota_retry_at:
        return {"status": "WAIT_QUOTA_BACKOFF", "resume_at": quota_retry_at.isoformat()}
    observation = provider_policy["capacity_observation"]
    if observation["status"] == "TRUSTED":
        remaining = observation["remaining_percent"]
        if remaining is None:
            raise GoalContractError("TRUSTED capacity is missing remaining_percent")
        observed_at = datetime.fromisoformat(observation["observed_at"])
        if observed_at.tzinfo is None or now.tzinfo is None:
            raise GoalContractError("capacity timestamps must be timezone-aware")
        age = (now - observed_at).total_seconds()
        if age < 0:
            raise GoalContractError("capacity observation timestamp is in the future")
        if age <= observation["max_age_seconds"]:
            if remaining <= provider_policy["reserve_percent"]:
                return {"status": "WAIT_RESERVE", "remaining_percent": remaining}
            return {"status": "DISPATCH", "basis": "TRUSTED_PERCENTAGE"}
    fallback = provider_policy["fallback"]
    if launches_in_window >= fallback["max_launches_per_window"]:
        return {"status": "WAIT_WINDOW_BUDGET"}
    if last_launch_at is not None:
        elapsed = (now - last_launch_at).total_seconds()
        if elapsed < fallback["min_launch_interval_seconds"]:
            return {
                "status": "WAIT_LAUNCH_INTERVAL",
                "resume_in_seconds": fallback["min_launch_interval_seconds"] - int(elapsed),
            }
    return {"status": "DISPATCH", "basis": "PERCENTAGE_UNOBSERVABLE_FALLBACK"}


def validate_runner_state(state: dict[str, Any], spec: dict[str, Any]) -> None:
    validate_document(state, "runner-state.schema.json")
    exact = {
        "identity_kind": PRODUCT_IDENTITY,
        "authority_kind": PRODUCT_AUTHORITY,
        "lifecycle_owner": PRODUCT_LIFECYCLE_OWNER,
        "goal_id": spec["goal_id"],
        "active_goal": spec["active_goal"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_spec_sha256(spec),
    }
    mismatches = {
        key: {"expected": expected, "actual": state.get(key)}
        for key, expected in exact.items()
        if state.get(key) != expected
    }
    if mismatches:
        raise GoalContractError(f"runner state identity mismatch: {mismatches}")
    if state["lifecycle"]["state"] not in LIFECYCLE_STATES:
        raise GoalContractError("runner state has unknown lifecycle")
    if state["authority_lease"] not in AUTHORITY_LEASES:
        raise GoalContractError("runner state has unknown authority lease")
    receipts = state.get("dependency_receipts", [])
    dependency_ids = [row.get("dependency_id") for row in receipts]
    if len(dependency_ids) != len(set(dependency_ids)):
        raise GoalContractError("runner state repeats a dependency closure receipt")
    if state["lifecycle"]["state"] in {"APPROVED", "ACTIVE", "ACCEPTANCE_REQUIRED", "CLOSED"}:
        missing = set(spec["dependencies"]) - set(dependency_ids)
        if missing:
            raise GoalContractError(
                f"active runner state lacks dependency closure receipts: {sorted(missing)}"
            )
    spec_work = {row["work_item_id"] for row in spec["work_items"]}
    state_work = {row.get("work_item_id") for row in state["work_items"]}
    if state_work != spec_work:
        raise GoalContractError("runner state work item set differs from Goal spec")
    spec_obligations = {
        (row["obligation_id"], row["semantic_key"]) for row in spec["obligations"]
    }
    state_obligations = {
        (row.get("obligation_id"), row.get("semantic_key")) for row in state["obligations"]
    }
    if state_obligations != spec_obligations:
        raise GoalContractError("runner state obligations differ from Goal spec")


def validate_ledger_binding(
    events: Iterable[dict[str, Any]], state: dict[str, Any], spec: dict[str, Any]
) -> list[dict[str, Any]]:
    """Verify one ledger belongs to the exact Goal and state cursor is its prefix."""
    rows = verify_ledger(events)
    for event in rows:
        if (
            event["goal_id"] != spec["goal_id"]
            or event["goal_version"] != spec["goal_version"]
        ):
            raise GoalContractError("ledger contains an event for a different Goal identity")
    cursor = state["event_cursor"]
    sequence = cursor["sequence"]
    if sequence > len(rows):
        raise GoalContractError("runner state event cursor is ahead of the ledger")
    if sequence == 0:
        if cursor["event_sha256"] is not None:
            raise GoalContractError("zero runner state event cursor must have a null digest")
    elif rows[sequence - 1]["event_sha256"] != cursor["event_sha256"]:
        raise GoalContractError("runner state event cursor is not a valid ledger prefix")
    return rows


def progress_transition(previous_count: int | None, current: str) -> dict[str, Any]:
    if current not in PROGRESS_CLASSES:
        raise GoalContractError(f"unknown progress class: {current}")
    no_progress = current in {"NO_OBLIGATION_PROGRESS", "EVIDENCE_INSUFFICIENT"}
    prior_count = int(previous_count or 0)
    count = prior_count + 1 if no_progress else 0
    return {
        "progress_class": current,
        "consecutive_no_progress": count,
        "strategy_adjustment_required": count >= 2,
    }
