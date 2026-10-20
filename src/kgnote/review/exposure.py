"""Append-only, non-assessment exposure events for Soak and natural encounters."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

EXPOSURE_VERSION = "kgnote.exposure-event.v1"
EXPOSURE_REQUEST_VERSION = "kgnote.exposure-save-request.v1"
EVENT_ID = re.compile(r"exposure_[a-f0-9]{32}")
SESSION_ID = re.compile(r"soak_[a-f0-9]{32}")
KINDS = {"presented", "answer_revealed", "skipped", "encountered", "recognized", "applied"}
_WRITE_LOCK = threading.Lock()


@dataclass(frozen=True, repr=False)
class ExposureResult:
    status: Literal["ready", "recorded", "unchanged", "conflict", "rejected", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> ExposureResult:
    return ExposureResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _safe(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 200 and not any(char in value for char in "\x00/\\")


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def validate_exposure_request(request: Any) -> str | None:
    required = {"schema_version", "event_id", "exposure_session_id", "learning_unit_id", "item_id", "concept_id", "kind", "occurred_at", "source_refs"}
    if not isinstance(request, Mapping) or set(request) != required:
        return "invalid_exposure_request"
    if request["schema_version"] != EXPOSURE_REQUEST_VERSION or not EVENT_ID.fullmatch(str(request["event_id"])) or not SESSION_ID.fullmatch(str(request["exposure_session_id"])):
        return "invalid_exposure_identity"
    if not all(_safe(request[key]) for key in ("learning_unit_id", "item_id", "concept_id")):
        return "invalid_exposure_reference"
    if request["kind"] not in KINDS or not _timestamp(request["occurred_at"]):
        return "invalid_exposure_event"
    if not isinstance(request["source_refs"], list) or not request["source_refs"] or not all(_safe(ref) for ref in request["source_refs"]):
        return "invalid_exposure_reference"
    return None


def _directory(root: Path, create: bool) -> Path | None:
    path = root / "exposures"
    if path.exists():
        return path if path.is_dir() and not path.is_symlink() else None
    if not create:
        return path
    try:
        path.mkdir(mode=0o700, parents=True)
    except OSError:
        return None
    return path


def _write(path: Path, record: Mapping[str, Any]) -> bool:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
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


def record_exposure(root: str | os.PathLike[str], request: Any) -> ExposureResult:
    problem = validate_exposure_request(request)
    if problem:
        return _result("rejected", problem=problem)
    root_path = Path(root)
    if root_path.is_symlink():
        return _result("rejected", problem="unsafe_exposure_root")
    record = {**request, "schema_version": EXPOSURE_VERSION}
    with _WRITE_LOCK:
        directory = _directory(root_path, True)
        if directory is None:
            return _result("failed", problem="exposure_directory_failed")
        path = directory / f"{request['event_id']}.json"
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                return _result("failed", problem="exposure_read_failed")
            if existing == record:
                return _result("unchanged", {"event": existing})
            return _result("conflict", problem="exposure_event_conflict")
        if not _write(path, record):
            return _result("failed", problem="exposure_write_failed")
    return _result("recorded", {"event": record})


def list_exposures(root: str | os.PathLike[str], learning_unit_id: str) -> ExposureResult:
    if not _safe(learning_unit_id):
        return _result("rejected", problem="invalid_learning_unit")
    directory = _directory(Path(root), False)
    if directory is None:
        return _result("rejected", problem="unsafe_exposure_directory")
    if not directory.exists():
        return _result("ready", {"events": []})
    events = []
    try:
        paths = sorted(directory.iterdir())
    except OSError:
        return _result("failed", problem="exposure_list_failed")
    for path in paths:
        if path.is_symlink() or not path.is_file() or not EVENT_ID.fullmatch(path.stem):
            continue
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return _result("failed", problem="exposure_read_failed")
        if event.get("schema_version") != EXPOSURE_VERSION:
            return _result("failed", problem="exposure_read_failed")
        if event.get("learning_unit_id") == learning_unit_id:
            events.append(event)
    events.sort(key=lambda item: (item["occurred_at"], item["event_id"]), reverse=True)
    return _result("ready", {"events": events})


__all__ = ["EXPOSURE_REQUEST_VERSION", "EXPOSURE_VERSION", "ExposureResult", "list_exposures", "record_exposure", "validate_exposure_request"]
