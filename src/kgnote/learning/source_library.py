"""Versioned local source library for product imports and exact read-back."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

from kgnote.ingestion.markdown_source import SourceMetadata, build_extraction_input


LIBRARY_VERSION = "kgnote.source-library.v2"
IMPORT_VERSION = "kgnote.source-import.v2"
BATCH_VERSION = "kgnote.source-import-batch.v1"
MAX_SOURCE_BYTES = 1_000_000
MAX_BATCH_SOURCES = 16

_SOURCE_ID = re.compile(r"src_[0-9a-f]{24}")
_REVISION_ID = re.compile(r"revision_[0-9a-f]{24}")
_TITLE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_SPEAKER_HEADING = re.compile(r"^#{1,6}\s+(User|Assistant|System|Tool|Learner|Tutor)\s*#*\s*$", re.I)
_SPEAKER_PREFIX = re.compile(r"^(User|Assistant|System|Tool|Learner|Tutor):\s*(.*)$", re.I)
_POSSIBLE_PREFIX = re.compile(r"^([^:#]{1,40}):\s+.+$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SPEAKER_ROLES = {
    "user": "user",
    "learner": "user",
    "assistant": "assistant",
    "tutor": "assistant",
    "system": "system",
    "tool": "tool",
}
_LOCK = threading.RLock()


class SourceLibraryError(RuntimeError):
    """A safe source-library failure that never embeds source content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _problem(code: str) -> dict[str, Any]:
    return {"problem": {"code": code}}


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _semantic_content(content: str) -> str:
    """Remove only the optional leading UTF-8 BOM for semantic interpretation."""
    return content[1:] if content.startswith("\ufeff") else content


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _assert_safe_tree(root: Path) -> None:
    if root.is_symlink():
        raise SourceLibraryError("library_root_symlink")
    if not root.exists():
        return
    if not root.is_dir():
        raise SourceLibraryError("library_root_not_directory")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SourceLibraryError("library_symlink_not_allowed")


def _source_directory(root: Path, source_id: str) -> Path:
    if not _SOURCE_ID.fullmatch(source_id):
        raise SourceLibraryError("invalid_source_id")
    return root / "sources" / source_id


def _metadata_path(root: Path, source_id: str) -> Path:
    return _source_directory(root, source_id) / "source.json"


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceLibraryError(code) from error
    if not isinstance(value, dict):
        raise SourceLibraryError(code)
    return value


def _load_source_metadata(root: Path, source_id: str) -> dict[str, Any] | None:
    path = _metadata_path(root, source_id)
    if not path.exists():
        return None
    metadata = _load_json(path, "source_metadata_unavailable")
    if metadata.get("schema_version") != LIBRARY_VERSION or metadata.get("source_id") != source_id:
        raise SourceLibraryError("source_metadata_mismatch")
    current = metadata.get("current_revision_id")
    revisions = metadata.get("revisions")
    if not isinstance(current, str) or not _REVISION_ID.fullmatch(current) or not isinstance(revisions, list):
        raise SourceLibraryError("source_metadata_mismatch")
    if not any(isinstance(item, dict) and item.get("revision_id") == current for item in revisions):
        raise SourceLibraryError("source_metadata_mismatch")
    revision_ids = [item.get("revision_id") for item in revisions if isinstance(item, dict)]
    if len(revision_ids) != len(revisions) or len(revision_ids) != len(set(revision_ids)):
        raise SourceLibraryError("source_revision_identity_ambiguous")
    return metadata


def _markdown_fenced_code_lines(lines: list[str]) -> set[int]:
    """Return one-based lines inside Markdown fences, rejecting an unclosed fence."""
    fenced: set[int] = set()
    marker: str | None = None
    marker_length = 0
    for number, line in enumerate(lines, 1):
        if marker is None:
            match = _FENCE.match(line)
            if match:
                marker = match.group(1)[0]
                marker_length = len(match.group(1))
                fenced.add(number)
            continue
        fenced.add(number)
        closing = re.fullmatch(rf" {{0,3}}{re.escape(marker)}{{{marker_length},}}\s*", line)
        if closing:
            marker = None
            marker_length = 0
    if marker is not None:
        raise SourceLibraryError("ambiguous_conversation_speaker")
    return fenced


def _speaker_spans(content: str, source_kind: str) -> list[dict[str, Any]]:
    if source_kind != "chatgpt_conversation":
        return []
    lines = content.splitlines()
    fenced_lines = _markdown_fenced_code_lines(lines)
    heading_matches = [
        (index, match)
        for index, line in enumerate(lines, 1)
        if index not in fenced_lines and (match := _SPEAKER_HEADING.match(line))
    ]
    spans: list[dict[str, Any]] = []
    if heading_matches:
        speaker_level = len(lines[heading_matches[0][0] - 1]) - len(lines[heading_matches[0][0] - 1].lstrip("#"))
        for number, line in enumerate(lines, 1):
            if number in fenced_lines:
                continue
            heading = _TITLE.match(line)
            if not heading or number < heading_matches[0][0]:
                if _POSSIBLE_PREFIX.match(line) and not _SPEAKER_PREFIX.match(line):
                    raise SourceLibraryError("ambiguous_conversation_speaker")
                continue
            level = len(line) - len(line.lstrip("#"))
            if level == speaker_level and not _SPEAKER_HEADING.match(line):
                raise SourceLibraryError("ambiguous_conversation_speaker")
        markers = list(heading_matches)
        markers.extend(
            (number, match)
            for number, line in enumerate(lines, 1)
            if number not in fenced_lines and (match := _SPEAKER_PREFIX.match(line))
        )
        markers.sort(key=lambda item: item[0])
        for position, (start, match) in enumerate(markers):
            end = markers[position + 1][0] - 1 if position + 1 < len(markers) else len(lines)
            label = match.group(1)
            spans.append({
                "speaker": label,
                "role": _SPEAKER_ROLES[label.casefold()],
                "locator": {"basis": "line_range", "value": f"L{start}-L{end}"},
            })
        return spans

    active: dict[str, Any] | None = None
    for number, line in enumerate(lines, 1):
        if number in fenced_lines:
            continue
        match = _SPEAKER_PREFIX.match(line)
        if match:
            if active is not None:
                active["locator"]["value"] += f"-L{number - 1}"
                spans.append(active)
            label = match.group(1)
            active = {
                "speaker": label,
                "role": _SPEAKER_ROLES[label.casefold()],
                "locator": {"basis": "line_range", "value": f"L{number}"},
            }
        elif _POSSIBLE_PREFIX.match(line):
            raise SourceLibraryError("ambiguous_conversation_speaker")
    if active is not None:
        active["locator"]["value"] += f"-L{len(lines)}"
        spans.append(active)
    if not spans:
        raise SourceLibraryError("conversation_speaker_missing")
    return spans


def _validated_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise SourceLibraryError("invalid_source_request")
    allowed = {
        "schema_version", "source_id", "expected_revision_id", "title", "content",
        "source_kind", "locator",
    }
    if set(request) - allowed or request.get("schema_version") != IMPORT_VERSION:
        raise SourceLibraryError("invalid_source_request")
    title = request.get("title")
    content = request.get("content")
    source_kind = request.get("source_kind")
    locator = request.get("locator")
    source_id = request.get("source_id")
    expected_revision_id = request.get("expected_revision_id")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
        raise SourceLibraryError("invalid_source_title")
    if not isinstance(content, str):
        raise SourceLibraryError("empty_source")
    semantic_content = _semantic_content(content)
    if not semantic_content.strip():
        raise SourceLibraryError("empty_source")
    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError as error:
        raise SourceLibraryError("invalid_utf8") from error
    if len(encoded) > MAX_SOURCE_BYTES:
        raise SourceLibraryError("source_too_large")
    if source_kind not in {"document", "chatgpt_conversation"}:
        raise SourceLibraryError("invalid_source_kind")
    if not isinstance(locator, dict) or set(locator) != {"kind", "value"}:
        raise SourceLibraryError("invalid_source_locator")
    if locator.get("kind") not in {"file_name", "pasted"}:
        raise SourceLibraryError("invalid_source_locator")
    locator_value = locator.get("value")
    if (
        not isinstance(locator_value, str)
        or not locator_value.strip()
        or len(locator_value) > 240
        or "\x00" in locator_value
        or "/" in locator_value
        or "\\" in locator_value
        or locator_value in {".", ".."}
    ):
        raise SourceLibraryError("invalid_source_locator")
    if source_id is not None and (not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id)):
        raise SourceLibraryError("invalid_source_id")
    if expected_revision_id is not None and (
        not isinstance(expected_revision_id, str) or not _REVISION_ID.fullmatch(expected_revision_id)
    ):
        raise SourceLibraryError("invalid_expected_revision")

    identity = json.dumps(
        {"source_kind": source_kind, "locator": {"kind": locator["kind"], "value": locator_value.strip()}},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    derived_source_id = f"src_{_sha256(identity)[:24]}"
    if source_id is None:
        source_id = derived_source_id
    digest = _sha256(encoded)
    spans = _speaker_spans(semantic_content, source_kind)

    # Reuse the public extraction input contract as the import boundary.
    build_extraction_input(
        content=semantic_content,
        metadata=SourceMetadata(
            source_id=source_id,
            source_kind=source_kind,
            title=title.strip(),
            captured_at=None,
            locator_basis="line_range",
        ),
    )
    return {
        "source_id": source_id,
        "expected_revision_id": expected_revision_id,
        "title": title.strip(),
        "source_kind": source_kind,
        "locator": {"kind": locator["kind"], "value": locator_value.strip()},
        "content": content,
        "encoded": encoded,
        "content_sha256": digest,
        "speaker_spans": spans,
    }


def _revision_summary(prepared: dict[str, Any], previous: str | None, imported_at: str) -> dict[str, Any]:
    return {
        "revision_id": prepared["revision_id"],
        "content_sha256": prepared["content_sha256"],
        "byte_length": len(prepared["encoded"]),
        "line_count": len(prepared["content"].splitlines()),
        "previous_revision_id": previous,
        "imported_at": imported_at,
        "raw_path": f"revisions/{prepared['revision_id']}.md",
        "speaker_spans": prepared["speaker_spans"],
        "provenance": {
            "adapter_version": IMPORT_VERSION,
            "locator": prepared["locator"],
            "locator_basis": "line_range",
        },
    }


def _apply_prepared(root: Path, prepared: dict[str, Any], imported_at: str) -> tuple[str, dict[str, Any]]:
    source_id = prepared["source_id"]
    existing = _load_source_metadata(root, source_id)
    if existing is not None:
        current = existing["current_revision_id"]
        current_summary = next((item for item in existing["revisions"] if item.get("revision_id") == current), None)
        if current_summary is None:
            raise SourceLibraryError("source_metadata_mismatch")
        if current_summary.get("content_sha256") == prepared["content_sha256"]:
            return "unchanged", existing
        if prepared["expected_revision_id"] != current:
            raise SourceLibraryError("stale_source_revision")
        if existing.get("source_kind") != prepared["source_kind"] or existing.get("locator") != prepared["locator"]:
            raise SourceLibraryError("source_identity_mismatch")
        previous = current
        revisions = list(existing["revisions"])
        created_at = existing.get("created_at")
    else:
        if prepared["expected_revision_id"] is not None:
            raise SourceLibraryError("source_not_found")
        previous = None
        revisions = []
        created_at = imported_at

    revision_identity = _canonical_json({
        "source_id": source_id,
        "ordinal": len(revisions) + 1,
        "previous_revision_id": previous,
        "content_sha256": prepared["content_sha256"],
    })
    prepared = {**prepared, "revision_id": f"revision_{_sha256(revision_identity)[:24]}"}
    if any(item.get("revision_id") == prepared["revision_id"] for item in revisions):
        raise SourceLibraryError("source_revision_collision")
    summary = _revision_summary(prepared, previous, imported_at)
    revisions.append(summary)
    metadata = {
        "schema_version": LIBRARY_VERSION,
        "source_id": source_id,
        "title": prepared["title"],
        "source_kind": prepared["source_kind"],
        "locator": prepared["locator"],
        "created_at": created_at,
        "updated_at": imported_at,
        "current_revision_id": prepared["revision_id"],
        "revision_count": len(revisions),
        "revisions": revisions,
    }
    directory = _source_directory(root, source_id)
    raw_path = directory / summary["raw_path"]
    if raw_path.exists() and raw_path.read_bytes() != prepared["encoded"]:
        raise SourceLibraryError("source_revision_collision")
    if not raw_path.exists():
        _atomic_write(raw_path, prepared["encoded"])
    _atomic_write(directory / "source.json", _canonical_json(metadata))
    return ("updated" if existing is not None else "created"), metadata


def _commit_staged_root(root: Path, staged: Path) -> None:
    root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=f".{root.name}.backup-", dir=root.parent))
    backup.rmdir()
    moved_existing = False
    keep_backup = False
    try:
        if root.exists():
            os.replace(root, backup)
            moved_existing = True
        os.replace(staged, root)
    except OSError:
        if moved_existing and not root.exists() and backup.exists():
            try:
                os.replace(backup, root)
            except OSError:
                keep_backup = True
        raise
    finally:
        if backup.exists() and not keep_backup:
            shutil.rmtree(backup, ignore_errors=True)


def import_sources(
    root: Path,
    request: Any,
    *,
    commit: Callable[[Path, Path], None] = _commit_staged_root,
) -> tuple[str, dict[str, Any]]:
    """Atomically import a bounded batch; any rejection leaves the library unchanged."""

    try:
        if not isinstance(request, dict) or set(request) != {"schema_version", "sources"}:
            raise SourceLibraryError("invalid_batch_request")
        if request.get("schema_version") != BATCH_VERSION:
            raise SourceLibraryError("invalid_batch_request")
        sources = request.get("sources")
        if not isinstance(sources, list) or not sources or len(sources) > MAX_BATCH_SOURCES:
            raise SourceLibraryError("invalid_batch_size")
        prepared = [_validated_request(item) for item in sources]
        ids = [item["source_id"] for item in prepared]
        if len(ids) != len(set(ids)):
            raise SourceLibraryError("duplicate_source_in_batch")
        root = Path(root)
        _assert_safe_tree(root)
        root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with _LOCK:
            staged = Path(tempfile.mkdtemp(prefix=f".{root.name}.staged-", dir=root.parent))
            try:
                if root.exists():
                    shutil.copytree(root, staged, dirs_exist_ok=True)
                imported_at = _now()
                results = []
                for item in prepared:
                    action, metadata = _apply_prepared(staged, item, imported_at)
                    results.append({"action": action, "source": metadata})
                if all(item["action"] == "unchanged" for item in results):
                    shutil.rmtree(staged)
                else:
                    commit(root, staged)
            except SourceLibraryError:
                shutil.rmtree(staged, ignore_errors=True)
                raise
            except OSError as error:
                shutil.rmtree(staged, ignore_errors=True)
                raise SourceLibraryError("source_transaction_failed") from error
        actions = {item["action"] for item in results}
        status = "unchanged" if actions == {"unchanged"} else "applied"
        return status, {"schema_version": "kgnote.source-import-result.v2", "status": status, "results": results}
    except SourceLibraryError as error:
        return "rejected" if error.code != "source_transaction_failed" else "failed", _problem(error.code)


def import_source(root: Path, request: Any) -> tuple[str, dict[str, Any]]:
    status, payload = import_sources(root, {"schema_version": BATCH_VERSION, "sources": [request]})
    if status in {"rejected", "failed"}:
        return status, payload
    result = payload["results"][0]
    return result["action"], {"schema_version": payload["schema_version"], "status": result["action"], "source": result["source"]}


def list_sources(root: Path) -> list[dict[str, Any]]:
    root = Path(root)
    _assert_safe_tree(root)
    sources_root = root / "sources"
    if not sources_root.exists():
        return []
    records = []
    for directory in sorted(sources_root.iterdir(), key=lambda path: path.name):
        if not directory.is_dir() or not _SOURCE_ID.fullmatch(directory.name):
            raise SourceLibraryError("unexpected_library_entry")
        metadata = _load_source_metadata(root, directory.name)
        if metadata is None:
            raise SourceLibraryError("source_metadata_unavailable")
        current = next(item for item in metadata["revisions"] if item["revision_id"] == metadata["current_revision_id"])
        records.append({key: metadata[key] for key in (
            "schema_version", "source_id", "title", "source_kind", "locator", "created_at",
            "updated_at", "current_revision_id", "revision_count",
        )} | {"current_revision": current})
    return records


def read_source(root: Path, source_id: str, revision_id: str | None = None) -> dict[str, Any] | None:
    root = Path(root)
    try:
        _assert_safe_tree(root)
        metadata = _load_source_metadata(root, source_id)
        if metadata is None:
            return None
        selected = revision_id or metadata["current_revision_id"]
        if not isinstance(selected, str) or not _REVISION_ID.fullmatch(selected):
            return None
        revision = next((item for item in metadata["revisions"] if item.get("revision_id") == selected), None)
        if revision is None:
            return None
        path = _source_directory(root, source_id) / revision["raw_path"]
        if path.is_symlink() or not path.is_file():
            return None
        original = path.read_bytes()
        if _sha256(original) != revision.get("content_sha256") or len(original) != revision.get("byte_length"):
            return None
        content = original.decode("utf-8", errors="strict")
    except (SourceLibraryError, OSError, UnicodeError):
        return None
    semantic_content = _semantic_content(content)
    headings = [
        {"line": number, "title": match.group(1), "level": len(line) - len(line.lstrip("#"))}
        for number, line in enumerate(semantic_content.splitlines(), 1)
        if (match := _TITLE.match(line))
    ]
    return {
        "schema_version": "kgnote.source-read.v2",
        "source": metadata,
        "revision": revision,
        "content": content,
        "headings": headings,
    }


def extraction_input_for_source(
    root: Path, source_id: str, revision_id: str | None = None,
) -> dict[str, Any] | None:
    """Rebuild the existing ExtractionInput contract from one verified raw revision."""

    source = read_source(root, source_id, revision_id)
    if source is None:
        return None
    metadata = source["source"]
    return build_extraction_input(
        content=_semantic_content(source["content"]),
        metadata=SourceMetadata(
            source_id=metadata["source_id"],
            source_kind=metadata["source_kind"],
            title=metadata["title"],
            captured_at=None,
            locator_basis="line_range",
        ),
    )


__all__ = [
    "BATCH_VERSION", "IMPORT_VERSION", "LIBRARY_VERSION", "MAX_BATCH_SOURCES", "MAX_SOURCE_BYTES",
    "SourceLibraryError", "extraction_input_for_source", "import_source", "import_sources", "list_sources", "read_source",
]
