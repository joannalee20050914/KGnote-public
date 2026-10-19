"""Attempt v1 validation and atomic local persistence.

Attempts are learner activity records.  They never mutate Source, Claim, Evidence,
or the legacy ReviewInteraction store.
"""

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


ATTEMPT_VERSION = "kgnote.attempt.v1"
ATTEMPT_REQUEST_VERSION = "kgnote.attempt-save-request.v1"
ATTEMPT_ID = re.compile(r"attempt_[a-f0-9]{32}")
ACTIVITY_TYPES = {"relation_recall", "free_explanation", "application_prediction", "distinction"}
STATES = {"draft", "submitted", "cancelled"}
SUPPORT_STATES = {"unassisted", "hinted"}
EXPOSURE_STATES = {"hidden", "revealed_after_submission"}
OUTCOMES = {"CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"}
_WRITE_LOCK = threading.RLock()


def _serialized(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _WRITE_LOCK:
            return function(*args, **kwargs)
    return locked


@dataclass(frozen=True, repr=False)
class AttemptResult:
    status: Literal["ready", "saved", "unchanged", "conflict", "rejected", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> AttemptResult:
    return AttemptResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _safe_ref(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 200 and not any(character in value for character in "\x00/\\")


def validate_attempt_request(request: Any) -> str | None:
    required = {
        "schema_version", "attempt_id", "review_item_id", "item_revision", "learning_unit_id",
        "activity_type", "state", "started_at", "submitted_at", "raw_response", "confidence",
        "hint_events", "support_state", "answer_exposure_state", "outcome", "correction_feedback",
        "entry_context", "source_refs", "claim_refs", "evidence_refs",
    }
    if not isinstance(request, Mapping) or set(request) != required:
        return "invalid_request"
    if request["schema_version"] != ATTEMPT_REQUEST_VERSION or not ATTEMPT_ID.fullmatch(str(request["attempt_id"])):
        return "invalid_identity"
    if not all(_safe_ref(request[name]) for name in ("review_item_id", "learning_unit_id")):
        return "invalid_reference"
    if not isinstance(request["item_revision"], int) or isinstance(request["item_revision"], bool) or request["item_revision"] < 1:
        return "invalid_revision"
    if request["activity_type"] not in ACTIVITY_TYPES or request["state"] not in STATES:
        return "invalid_activity"
    if not _timestamp(request["started_at"]):
        return "invalid_started_at"
    submitted_at = request["submitted_at"]
    if submitted_at is not None and not _timestamp(submitted_at):
        return "invalid_submitted_at"
    if request["state"] == "submitted" and submitted_at is None:
        return "missing_submission"
    if request["state"] != "submitted" and submitted_at is not None:
        return "unexpected_submission"
    raw_response = request["raw_response"]
    if not isinstance(raw_response, str) or len(raw_response) > 8000:
        return "invalid_response"
    if request["state"] == "submitted" and not raw_response.strip():
        return "empty_submission"
    confidence = request["confidence"]
    if confidence is not None and confidence not in {"low", "medium", "high"}:
        return "invalid_confidence"
    if request["support_state"] not in SUPPORT_STATES or request["answer_exposure_state"] not in EXPOSURE_STATES:
        return "invalid_exposure"
    if request["state"] == "submitted" and request["answer_exposure_state"] != "revealed_after_submission":
        return "invalid_exposure"
    if request["state"] != "submitted" and request["answer_exposure_state"] != "hidden":
        return "invalid_exposure"
    outcome = request["outcome"]
    if request["state"] == "submitted" and outcome not in OUTCOMES:
        return "invalid_outcome"
    if request["state"] != "submitted" and outcome is not None:
        return "unexpected_outcome"
    feedback = request["correction_feedback"]
    if feedback is not None and (not isinstance(feedback, str) or len(feedback) > 4000):
        return "invalid_feedback"
    if not isinstance(request["entry_context"], Mapping) or set(request["entry_context"]) != {"route", "from_route", "entry_kind", "due_id"}:
        return "invalid_entry_context"
    if not all(isinstance(request["entry_context"][key], str) and len(request["entry_context"][key]) <= 200 for key in ("route", "from_route", "entry_kind")):
        return "invalid_entry_context"
    if request["entry_context"]["entry_kind"] not in {"voluntary_practice", "scheduled_review"}:
        return "invalid_entry_context"
    due_id = request["entry_context"]["due_id"]
    if due_id is not None and not _safe_ref(due_id):
        return "invalid_entry_context"
    if (request["entry_context"]["entry_kind"] == "scheduled_review") != (due_id is not None):
        return "invalid_entry_context"
    if not isinstance(request["hint_events"], list) or len(request["hint_events"]) > 20:
        return "invalid_hint_events"
    for event in request["hint_events"]:
        if not isinstance(event, Mapping) or set(event) != {"kind", "occurred_at"} or event["kind"] != "requested" or not _timestamp(event["occurred_at"]):
            return "invalid_hint_events"
    if (request["support_state"] == "hinted") != bool(request["hint_events"]):
        return "invalid_hint_events"
    for name in ("source_refs", "evidence_refs"):
        if not isinstance(request[name], list) or not request[name] or not all(_safe_ref(item) for item in request[name]):
            return "invalid_reference"
    if not isinstance(request["claim_refs"], list) or not request["claim_refs"]:
        return "invalid_reference"
    for reference in request["claim_refs"]:
        if not isinstance(reference, Mapping) or set(reference) != {"claim_id", "revision"} or not _safe_ref(reference["claim_id"]) or not isinstance(reference["revision"], int):
            return "invalid_reference"
    return None


def _directory(root: Path, create: bool) -> Path | None:
    directory = root / "attempts"
    if directory.exists():
        return directory if directory.is_dir() and not directory.is_symlink() else None
    if not create:
        return directory
    try:
        directory.mkdir(mode=0o700, parents=True)
    except OSError:
        return None
    return directory


def _request_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in record if key not in {"schema_version", "recorded_at", "updated_at", "payload_sha256"}} | {
        "schema_version": ATTEMPT_REQUEST_VERSION,
    }


def _digest(request: Mapping[str, Any]) -> str:
    encoded = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and value.get("schema_version") == ATTEMPT_VERSION else None


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> bool:
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return True
    except OSError:
        return False
    finally:
        temporary.unlink(missing_ok=True)


@_serialized
def save_attempt(root: str | os.PathLike[str], request: Any, *, recorded_at: str | None = None) -> AttemptResult:
    """Create/update a draft or submit once, with retry-safe conflict semantics."""
    problem = validate_attempt_request(request)
    if problem:
        return _result("rejected", problem=problem)
    timestamp = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat()
    if not _timestamp(timestamp):
        return _result("rejected", problem="invalid_recorded_at")
    root_path = Path(root)
    if root_path.is_symlink():
        return _result("rejected", problem="unsafe_attempt_root")
    directory = _directory(root_path, create=True)
    if directory is None:
        return _result("failed", problem="attempt_directory_failed")
    path = directory / f"{request['attempt_id']}.json"
    existing = _read(path) if path.exists() else None
    if path.exists() and existing is None:
        return _result("failed", problem="attempt_read_failed")
    request_value = dict(request)
    request_digest = _digest(request_value)
    if existing:
        if existing["state"] == "submitted":
            if existing.get("payload_sha256") == request_digest:
                return _result("unchanged", {"attempt": existing})
            return _result("conflict", {"attempt_id": request["attempt_id"]}, "submitted_attempt_conflict")
        immutable = ("attempt_id", "review_item_id", "item_revision", "learning_unit_id", "activity_type", "started_at", "entry_context", "source_refs", "claim_refs", "evidence_refs")
        if any(existing.get(key) != request_value[key] for key in immutable):
            return _result("conflict", {"attempt_id": request["attempt_id"]}, "attempt_identity_conflict")
        if existing["state"] == "cancelled" and request["state"] != "cancelled":
            return _result("conflict", {"attempt_id": request["attempt_id"]}, "cancelled_attempt_conflict")
        if existing.get("payload_sha256") == request_digest:
            return _result("unchanged", {"attempt": existing})
    record = {**request_value, "schema_version": ATTEMPT_VERSION, "recorded_at": existing["recorded_at"] if existing else timestamp, "updated_at": timestamp, "payload_sha256": request_digest}
    if not _atomic_write(path, record):
        return _result("failed", problem="attempt_write_failed")
    return _result("saved", {"attempt": record, "created": existing is None})


def list_attempts(root: str | os.PathLike[str], learning_unit_id: str) -> AttemptResult:
    if not _safe_ref(learning_unit_id):
        return _result("rejected", problem="invalid_learning_unit")
    directory = _directory(Path(root), create=False)
    if directory is None:
        return _result("rejected", problem="unsafe_attempt_directory")
    if not directory.exists():
        return _result("ready", {"attempts": []})
    attempts: list[dict[str, Any]] = []
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return _result("failed", problem="attempt_list_failed")
    for path in entries:
        if path.is_symlink() or not path.is_file() or not ATTEMPT_ID.fullmatch(path.stem):
            continue
        record = _read(path)
        if record and record.get("learning_unit_id") == learning_unit_id:
            attempts.append(record)
    attempts.sort(key=lambda item: (item["started_at"], item["attempt_id"]), reverse=True)
    return _result("ready", {"attempts": attempts})


def read_attempt(root: str | os.PathLike[str], attempt_id: str) -> AttemptResult:
    if not ATTEMPT_ID.fullmatch(str(attempt_id)):
        return _result("rejected", problem="invalid_attempt_id")
    directory = _directory(Path(root), create=False)
    if directory is None:
        return _result("rejected", problem="unsafe_attempt_directory")
    path = directory / f"{attempt_id}.json"
    if not path.exists():
        return _result("rejected", problem="unknown_attempt")
    if path.is_symlink() or not path.is_file():
        return _result("rejected", problem="unsafe_attempt_path")
    record = _read(path)
    if record is None:
        return _result("failed", problem="attempt_read_failed")
    return _result("ready", {"attempt": record})


__all__ = [
    "ATTEMPT_REQUEST_VERSION", "ATTEMPT_VERSION", "AttemptResult", "list_attempts",
    "read_attempt", "save_attempt", "validate_attempt_request",
]
