"""Append-only human feedback/self-assessment for immutable submitted Attempts."""

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


FEEDBACK_VERSION = "kgnote.attempt-feedback.v1"
FEEDBACK_REQUEST_VERSION = "kgnote.attempt-feedback-request.v1"
ASSESSMENT_ID = re.compile(r"assessment_[a-f0-9]{32}")
ATTEMPT_ID = re.compile(r"attempt_[a-f0-9]{32}")
OUTCOMES = {"CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"}
_WRITE_LOCK = threading.RLock()


def _serialized(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _WRITE_LOCK:
            return function(*args, **kwargs)
    return locked


@dataclass(frozen=True, repr=False)
class FeedbackResult:
    status: Literal["ready", "recorded", "unchanged", "conflict", "rejected", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]: return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> FeedbackResult:
    return FeedbackResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 64: return False
    try: parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return False
    return parsed.tzinfo is not None


def validate_feedback_request(request: Any) -> str | None:
    required = {"schema_version", "assessment_id", "attempt_id", "outcome", "disagrees", "correction", "occurred_at"}
    if not isinstance(request, Mapping) or set(request) != required: return "invalid_request"
    if request["schema_version"] != FEEDBACK_REQUEST_VERSION: return "invalid_version"
    if not ASSESSMENT_ID.fullmatch(str(request["assessment_id"])) or not ATTEMPT_ID.fullmatch(str(request["attempt_id"])): return "invalid_identity"
    if request["outcome"] not in OUTCOMES or not isinstance(request["disagrees"], bool): return "invalid_assessment"
    if request["correction"] is not None and (not isinstance(request["correction"], str) or len(request["correction"]) > 4000): return "invalid_correction"
    if request["disagrees"] and not str(request["correction"] or "").strip(): return "missing_correction"
    if not _timestamp(request["occurred_at"]): return "invalid_occurred_at"
    return None


def _directory(root: Path, create: bool) -> Path | None:
    directory = root / "feedback"
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


def read_feedback(root: str | os.PathLike[str], attempt_id: str) -> FeedbackResult:
    if not ATTEMPT_ID.fullmatch(str(attempt_id)): return _result("rejected", problem="invalid_attempt_id")
    directory = _directory(Path(root), False)
    if directory is None: return _result("rejected", problem="unsafe_feedback_directory")
    path = directory / f"{attempt_id}.json"
    if not path.exists(): return _result("ready", {"attempt_id": attempt_id, "events": [], "latest": None})
    try: record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError): return _result("failed", problem="feedback_read_failed")
    if not isinstance(record, dict) or record.get("schema_version") != FEEDBACK_VERSION: return _result("failed", problem="corrupted_feedback")
    return _result("ready", {"attempt_id": attempt_id, "events": record["events"], "latest": record["events"][-1] if record["events"] else None})


@_serialized
def append_feedback(root: str | os.PathLike[str], request: Any, attempt: Mapping[str, Any]) -> FeedbackResult:
    problem = validate_feedback_request(request)
    if problem: return _result("rejected", problem=problem)
    if attempt.get("attempt_id") != request["attempt_id"] or attempt.get("state") != "submitted": return _result("rejected", problem="attempt_not_submitted")
    directory = _directory(Path(root), True)
    if directory is None: return _result("failed", problem="feedback_directory_failed")
    path = directory / f"{request['attempt_id']}.json"
    existing = read_feedback(root, request["attempt_id"])
    if existing.status != "ready": return existing
    events = existing.payload["events"]
    duplicate = next((event for event in events if event["assessment_id"] == request["assessment_id"]), None)
    event = {key: request[key] for key in ("assessment_id", "outcome", "disagrees", "correction", "occurred_at")}
    event["payload_sha256"] = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if duplicate:
        return _result("unchanged", {"event": duplicate}) if duplicate == event else _result("conflict", problem="assessment_id_conflict")
    record = {"schema_version": FEEDBACK_VERSION, "attempt_id": request["attempt_id"], "events": [*events, event]}
    if not _atomic_write(path, record): return _result("failed", problem="feedback_write_failed")
    return _result("recorded", {"event": event, "latest": event})


__all__ = ["FEEDBACK_REQUEST_VERSION", "FEEDBACK_VERSION", "FeedbackResult", "append_feedback", "read_feedback", "validate_feedback_request"]
