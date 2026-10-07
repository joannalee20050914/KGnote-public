"""Small explainable Due Queue v1, separate from Attempt identity."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import threading
from functools import wraps
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping
from zoneinfo import ZoneInfo


DUE_VERSION = "kgnote.due-item.v1"
DUE_ACTION_VERSION = "kgnote.due-action.v1"
MILESTONE_DAYS = (1, 3, 7, 21)
TIMEZONE = "Asia/Taipei"
DUE_ID = re.compile(r"due_[a-f0-9]{32}")
ACTION_ID = re.compile(r"action_[A-Za-z0-9_-]{1,180}")
_WRITE_LOCK = threading.RLock()


def _serialized(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _WRITE_LOCK:
            return function(*args, **kwargs)
    return locked


@dataclass(frozen=True, repr=False)
class DueResult:
    status: Literal["ready", "saved", "unchanged", "conflict", "rejected", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None
    @property
    def payload(self) -> dict[str, Any]: return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> DueResult:
    return DueResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None: raise ValueError("timezone required")
    return parsed


def milestone_due_at(anchor: str, milestone_index: int, timezone: str = TIMEZONE) -> str | None:
    if milestone_index >= len(MILESTONE_DAYS): return None
    local = parse_time(anchor).astimezone(ZoneInfo(timezone))
    due_local = local + dt.timedelta(days=MILESTONE_DAYS[milestone_index])
    return due_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def due_identity(learning_unit_id: str, review_item_id: str) -> str:
    digest = hashlib.sha256(f"{learning_unit_id}\0{review_item_id}".encode()).hexdigest()
    return f"due_{digest[:32]}"


def _directory(root: Path, create: bool) -> Path | None:
    directory = root / "due-items"
    if directory.exists(): return directory if directory.is_dir() and not directory.is_symlink() else None
    if not create: return directory
    try: directory.mkdir(mode=0o700, parents=True)
    except OSError: return None
    return directory


def _atomic_write(path: Path, value: Mapping[str, Any]) -> bool:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.stem}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory_descriptor)
        finally: os.close(directory_descriptor)
        return True
    except OSError: return False
    finally: temporary.unlink(missing_ok=True)


def _read(path: Path) -> dict[str, Any] | None:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError): return None
    return value if isinstance(value, dict) and value.get("schema_version") == DUE_VERSION else None


@_serialized
def schedule_after_feedback(root: str | os.PathLike[str], attempt: Mapping[str, Any], feedback_event: Mapping[str, Any]) -> DueResult:
    """Create first due item or advance only when this was a scheduled review."""
    if attempt.get("state") != "submitted" or feedback_event.get("outcome") not in {"CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"}:
        return _result("rejected", problem="invalid_schedule_input")
    due_id = due_identity(attempt["learning_unit_id"], attempt["review_item_id"])
    directory = _directory(Path(root), True)
    if directory is None: return _result("failed", problem="due_directory_failed")
    path = directory / f"{due_id}.json"
    existing = _read(path) if path.exists() else None
    if path.exists() and existing is None: return _result("failed", problem="corrupted_due_item")
    if not existing:
        anchor = attempt["submitted_at"]
        record = {
            "schema_version": DUE_VERSION, "due_id": due_id, "learning_unit_id": attempt["learning_unit_id"],
            "review_item_id": attempt["review_item_id"], "item_revision": attempt["item_revision"],
            "schedule_anchor_at": anchor, "scheduler_timezone": TIMEZONE, "heuristic": "prototype-milestones-1-3-7-21.v1",
            "milestone_index": 0, "due_at": milestone_due_at(anchor, 0), "state": "active",
            "reason": "首次完成後的 prototype 第 1 天複習；這不是最佳記憶模型。",
            "attempt_ids": [attempt["attempt_id"]], "actions": [], "last_outcome": feedback_event["outcome"],
        }
    else:
        if attempt["attempt_id"] in existing["attempt_ids"]: return _result("unchanged", {"due": existing})
        context = attempt.get("entry_context", {})
        if context.get("entry_kind") != "scheduled_review" or context.get("due_id") != due_id:
            return _result("unchanged", {"due": existing, "reason": "voluntary_retry_does_not_advance_schedule"})
        next_index = existing["milestone_index"] + 1
        record = {**existing, "milestone_index": next_index, "due_at": milestone_due_at(existing["schedule_anchor_at"], next_index),
                  "state": "completed" if next_index >= len(MILESTONE_DAYS) else "active",
                  "reason": "已完成排定複習，前進到下一個固定 milestone；不換算 mastery。",
                  "attempt_ids": [*existing["attempt_ids"], attempt["attempt_id"]], "last_outcome": feedback_event["outcome"]}
    if not _atomic_write(path, record): return _result("failed", problem="due_write_failed")
    return _result("saved", {"due": record, "created": existing is None})


@_serialized
def act_on_due(root: str | os.PathLike[str], request: Any) -> DueResult:
    required = {"schema_version", "action_id", "due_id", "action", "occurred_at", "snooze_until"}
    if not isinstance(request, Mapping) or set(request) != required or request.get("schema_version") != DUE_ACTION_VERSION:
        return _result("rejected", problem="invalid_due_action")
    if not DUE_ID.fullmatch(str(request["due_id"])) or not ACTION_ID.fullmatch(str(request["action_id"])):
        return _result("rejected", problem="invalid_due_action_identity")
    if request["action"] not in {"snooze", "skip", "stop"}: return _result("rejected", problem="invalid_due_action")
    try: parse_time(request["occurred_at"])
    except (TypeError, ValueError): return _result("rejected", problem="invalid_due_action_time")
    if request["action"] == "snooze":
        try: parse_time(request["snooze_until"])
        except (TypeError, ValueError): return _result("rejected", problem="invalid_snooze_time")
    elif request["snooze_until"] is not None: return _result("rejected", problem="unexpected_snooze_time")
    directory = _directory(Path(root), False)
    path = directory / f"{request['due_id']}.json" if directory else Path("/")
    existing = _read(path) if path.is_file() and not path.is_symlink() else None
    if not existing: return _result("rejected", problem="unknown_due_item")
    duplicate = next((item for item in existing["actions"] if item["action_id"] == request["action_id"]), None)
    action = {key: request[key] for key in ("action_id", "action", "occurred_at", "snooze_until")}
    if duplicate: return _result("unchanged", {"due": existing}) if duplicate == action else _result("conflict", problem="due_action_id_conflict")
    record = {**existing, "actions": [*existing["actions"], action]}
    if request["action"] == "snooze": record.update(due_at=request["snooze_until"], state="active", reason="使用者 snooze；沒有建立 Attempt。")
    elif request["action"] == "stop": record.update(state="stopped", due_at=None, reason="使用者停止複習；歷史保留。")
    else:
        next_index = existing["milestone_index"] + 1
        record.update(milestone_index=next_index, due_at=milestone_due_at(existing["schedule_anchor_at"], next_index), state="completed" if next_index >= len(MILESTONE_DAYS) else "active", reason="使用者跳過此 milestone；沒有建立 Attempt。")
    if not _atomic_write(path, record): return _result("failed", problem="due_write_failed")
    return _result("saved", {"due": record})


def list_due(root: str | os.PathLike[str], *, now: str) -> DueResult:
    try: current = parse_time(now)
    except (TypeError, ValueError): return _result("rejected", problem="invalid_clock")
    directory = _directory(Path(root), False)
    if directory is None: return _result("rejected", problem="unsafe_due_directory")
    items = []
    if directory.exists():
        try: paths = sorted(directory.iterdir())
        except OSError: return _result("failed", problem="due_list_failed")
        for path in paths:
            if path.is_symlink() or not path.is_file() or not DUE_ID.fullmatch(path.stem): continue
            record = _read(path)
            if not record: return _result("failed", problem="corrupted_due_item")
            category = "inactive"
            if record["state"] == "active" and record["due_at"]:
                category = "due_now" if parse_time(record["due_at"]) <= current else "upcoming"
            items.append({**record, "category": category})
    items.sort(key=lambda item: (item["due_at"] is None, item["due_at"] or "", item["due_id"]))
    return _result("ready", {"now": now, "items": items})


def due_exposure_signal(due: Mapping[str, Any], events: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Project a non-assessment scheduling hint without advancing or scoring a Due item."""
    natural = [event for event in events if event.get("kind") in {"encountered", "recognized", "applied"} and event.get("learning_unit_id") == due.get("learning_unit_id")]
    if not natural:
        return None
    latest = max(natural, key=lambda event: (str(event.get("occurred_at", "")), str(event.get("event_id", ""))))
    recommendations = {
        "encountered": "informational_only",
        "recognized": "consider_snooze",
        "applied": "consider_snooze_or_changed_context",
    }
    return {
        "kind": latest["kind"],
        "occurred_at": latest["occurred_at"],
        "event_id": latest["event_id"],
        "recommendation": recommendations[latest["kind"]],
        "counts_as_retrieval_success": False,
    }


__all__ = ["DUE_ACTION_VERSION", "DUE_VERSION", "DueResult", "MILESTONE_DAYS", "act_on_due", "due_exposure_signal", "due_identity", "list_due", "milestone_due_at", "schedule_after_feedback"]
