"""Versioned Markdown LearningNote persistence with optimistic concurrency."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml

from kgnote.contracts.learning_note import (
    LEARNING_NOTE_VERSION,
    LearningNoteValidationError,
    validate_learning_note,
    validate_learning_note_save,
)


NOTE_ID_PATTERN = re.compile(r"note_[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
ETAG_PATTERN = re.compile(r'"[a-f0-9]{64}"')
_WRITE_LOCK = threading.Lock()


@dataclass(frozen=True, repr=False)
class LearningNoteResult:
    status: Literal["ready", "saved", "unchanged", "not_found", "rejected", "conflict", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)

    def __repr__(self) -> str:
        return f"LearningNoteResult(status={self.status!r}, problem_code={self.problem_code!r})"


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> LearningNoteResult:
    return LearningNoteResult(
        status,
        json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        problem,
    )


def _etag(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()}"'


def _request_digest(request: Mapping[str, Any]) -> str:
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_value(child) for child in value]
    return value


def _notes_directory(root: Path, *, create: bool) -> Path | None:
    if root.is_symlink():
        return None
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return None
    if not resolved_root.is_dir():
        return None
    directory = resolved_root / "notes"
    if directory.exists():
        return directory if directory.is_dir() and not directory.is_symlink() else None
    if not create:
        return directory
    try:
        directory.mkdir(mode=0o700)
    except OSError:
        return None
    return directory


def _target(directory: Path, note_id: str) -> Path | None:
    if NOTE_ID_PATTERN.fullmatch(note_id) is None:
        return None
    path = directory / f"{note_id}.md"
    return None if path.is_symlink() else path


def _parse(content: bytes) -> dict[str, Any]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LearningNoteValidationError("invalid_note_utf8") from error
    if not text.startswith("---\n"):
        raise LearningNoteValidationError("missing_note_front_matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise LearningNoteValidationError("malformed_note_front_matter")
    try:
        metadata = yaml.safe_load(text[4:end])
    except yaml.YAMLError as error:
        raise LearningNoteValidationError("malformed_note_yaml") from error
    if not isinstance(metadata, dict):
        raise LearningNoteValidationError("note_front_matter_not_object")
    note = {**_json_value(metadata), "markdown": text[end + 5 :]}
    validate_learning_note(note)
    return note


def _render(note: Mapping[str, Any]) -> bytes:
    metadata = {key: value for key, value in note.items() if key != "markdown"}
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False, width=4096)
    return f"---\n{front_matter}---\n{note['markdown']}".encode("utf-8")


def _public_payload(note: Mapping[str, Any], etag: str) -> dict[str, Any]:
    public = {key: value for key, value in note.items() if key not in {"last_save_id", "last_request_sha256"}}
    return {"schema_version": "kgnote.learning-note-read.v1", "note": public, "etag": etag}


def read_note(root: str | os.PathLike[str], note_id: str) -> LearningNoteResult:
    directory = _notes_directory(Path(root), create=False)
    if directory is None:
        return _result("rejected", problem="unsafe_notes_directory")
    target = _target(directory, note_id)
    if target is None:
        return _result("rejected", problem="invalid_note_id")
    if not target.exists():
        return _result("not_found", problem="note_not_found")
    if not target.is_file() or target.is_symlink():
        return _result("rejected", problem="unsafe_note_path")
    try:
        content = target.read_bytes()
        note = _parse(content)
    except OSError:
        return _result("failed", problem="note_read_failed")
    except LearningNoteValidationError as error:
        return _result("rejected", problem=error.code)
    if note["id"] != note_id:
        return _result("rejected", problem="note_filename_id_mismatch")
    return _result("ready", _public_payload(note, _etag(content)))


def _timestamp(value: str | None) -> str | None:
    if value is None:
        return dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed.isoformat()


def _save_note_locked(
    root: str | os.PathLike[str],
    request: Any,
    *,
    if_match: str | None,
    saved_at: str | None = None,
) -> LearningNoteResult:
    try:
        validate_learning_note_save(request)
    except LearningNoteValidationError as error:
        return _result("rejected", problem=error.code)
    timestamp = _timestamp(saved_at)
    if timestamp is None:
        return _result("rejected", problem="invalid_saved_at")
    if if_match is None or (if_match != "*" and ETAG_PATTERN.fullmatch(if_match) is None):
        return _result("rejected", problem="if_match_required")

    directory = _notes_directory(Path(root), create=True)
    if directory is None:
        return _result("rejected", problem="unsafe_notes_directory")
    target = _target(directory, request["note_id"])
    if target is None:
        return _result("rejected", problem="invalid_note_id")
    digest = _request_digest(request)
    existing: dict[str, Any] | None = None
    current_etag: str | None = None
    if target.exists():
        if not target.is_file() or target.is_symlink():
            return _result("rejected", problem="unsafe_note_path")
        try:
            current_bytes = target.read_bytes()
            existing = _parse(current_bytes)
        except OSError:
            return _result("failed", problem="note_read_failed")
        except LearningNoteValidationError as error:
            return _result("rejected", problem=error.code)
        current_etag = _etag(current_bytes)
        if existing["last_save_id"] == request["save_id"]:
            if existing["last_request_sha256"] != digest:
                return _result("conflict", {"etag": current_etag}, "save_id_reused")
            return _result("unchanged", _public_payload(existing, current_etag))
        if if_match != current_etag:
            return _result("conflict", {"etag": current_etag}, "stale_note")
        if existing["notebook_id"] != request["notebook_id"] or existing["learning_unit_id"] != request["learning_unit_id"]:
            return _result("conflict", {"etag": current_etag}, "note_identity_changed")
        revision = existing["revision"] + 1
        created_at = existing["created_at"]
    else:
        if if_match != "*":
            return _result("conflict", problem="note_missing")
        revision = 1
        created_at = timestamp

    note = {
        "schema_version": LEARNING_NOTE_VERSION,
        "id": request["note_id"],
        "type": "learning_note",
        "notebook_id": request["notebook_id"],
        "learning_unit_id": request["learning_unit_id"],
        "revision": revision,
        "title": request["title"],
        "source_anchors": request["source_anchors"],
        "created_at": created_at,
        "updated_at": timestamp,
        "last_save_id": request["save_id"],
        "last_request_sha256": digest,
        "markdown": request["markdown"],
    }
    try:
        validate_learning_note(note)
        rendered = _render(note)
    except (LearningNoteValidationError, UnicodeError):
        return _result("rejected", problem="invalid_learning_note")

    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{request['note_id']}.", suffix=".tmp", dir=directory)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        temporary = None
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        return _result("failed", {"etag": current_etag} if current_etag else {}, "note_write_failed")
    new_etag = _etag(rendered)
    return _result("saved", {**_public_payload(note, new_etag), "created": existing is None})


def save_note(
    root: str | os.PathLike[str],
    request: Any,
    *,
    if_match: str | None,
    saved_at: str | None = None,
) -> LearningNoteResult:
    """Serialize compare-and-replace commands within the local server process."""
    with _WRITE_LOCK:
        return _save_note_locked(root, request, if_match=if_match, saved_at=saved_at)


def _heading_for(lines: list[str], index: int) -> str | None:
    for position in range(index, -1, -1):
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", lines[position])
        if match:
            return match.group(1)
    return None


def search_notes(root: str | os.PathLike[str], notebook_id: str, query: str) -> LearningNoteResult:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", notebook_id) or not isinstance(query, str) or len(query) > 200:
        return _result("rejected", problem="invalid_note_search")
    directory = _notes_directory(Path(root), create=False)
    if directory is None:
        return _result("rejected", problem="unsafe_notes_directory")
    if not directory.exists():
        return _result("ready", {"schema_version": "kgnote.learning-note-search.v1", "query": query, "results": []})
    needle = query.casefold().strip()
    results: list[dict[str, Any]] = []
    try:
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:
        return _result("failed", problem="notes_directory_unreadable")
    for path in entries:
        if path.is_symlink() or not path.is_file() or NOTE_ID_PATTERN.fullmatch(path.stem) is None:
            return _result("rejected", problem="unexpected_notes_entry")
        try:
            note = _parse(path.read_bytes())
        except (OSError, LearningNoteValidationError):
            return _result("rejected", problem="invalid_note_store")
        if note["notebook_id"] != notebook_id:
            continue
        anchors = note["source_anchors"]
        lines = note["markdown"].splitlines()
        candidates: list[tuple[str | None, str, list[dict[str, Any]]]] = [(None, note["title"], anchors)]
        candidates.extend((_heading_for(lines, index), line.strip(), anchors) for index, line in enumerate(lines) if line.strip())
        candidates.extend((None, anchor["label"], [anchor]) for anchor in anchors)
        for heading, snippet, candidate_anchors in candidates:
            if needle and needle not in snippet.casefold():
                continue
            hit = {
                "note_id": note["id"], "title": note["title"], "revision": note["revision"],
                "heading": heading, "snippet": snippet[:240], "source_anchors": candidate_anchors,
            }
            if hit not in results:
                results.append(hit)
            if len(results) >= 100:
                break
        if len(results) >= 100:
            break
    return _result("ready", {
        "schema_version": "kgnote.learning-note-search.v1", "query": query,
        "results": results, "truncated": len(results) >= 100,
    })


__all__ = ["LearningNoteResult", "read_note", "save_note", "search_notes"]
