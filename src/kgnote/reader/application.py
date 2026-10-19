"""Filesystem-facing, read-only application boundary for registered source text."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Mapping

from kgnote.contracts.reader import (
    APPLICATION_VERSION,
    ReaderValidationError,
    parse_line_range,
    validate_reader_application_result,
    validate_reader_query,
)
from kgnote.storage import read_canonical_store
from kgnote.visualization.read_model import project_graph_read_model


MAX_SOURCE_BYTES = 2 * 1024 * 1024
READER_RESPONSE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@dataclass(frozen=True)
class ReaderApplicationProblem:
    component: Literal["store", "projector", "query", "source", "reader"]
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class ReaderApplicationResult:
    status: Literal["ready", "rejected"]
    _response_json: str = field(default="{}", repr=False)
    problem: ReaderApplicationProblem | None = None

    @property
    def response(self) -> dict[str, Any]:
        return json.loads(self._response_json)

    def __repr__(self) -> str:
        return f"ReaderApplicationResult(status={self.status!r}, problem={self.problem!r})"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _result(payload: Mapping[str, Any], problem: ReaderApplicationProblem | None = None) -> ReaderApplicationResult:
    return ReaderApplicationResult(payload["status"], _canonical_json(payload), problem)


def _reject(
    component: Literal["store", "projector", "query", "source", "reader"],
    code: str,
    path: tuple[object, ...] = (),
) -> ReaderApplicationResult:
    problem = ReaderApplicationProblem(component, code, path)
    return _result({
        "schema_version": APPLICATION_VERSION,
        "status": "rejected",
        "response_headers": READER_RESPONSE_HEADERS,
        "problem": {"component": component, "code": code, "path": list(path)},
    }, problem)


def _registered_source_path(root: Path, uri_or_path: Any) -> Path | None:
    if not isinstance(uri_or_path, str) or "\\" in uri_or_path:
        return None
    relative = PurePosixPath(uri_or_path)
    if relative.as_posix() != uri_or_path:
        return None
    if relative.is_absolute() or relative.suffix.lower() != ".md":
        return None
    if not relative.parts or relative.parts[0] != "raw" or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def _overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _registered_line_range(locator: Mapping[str, Any]) -> tuple[tuple[int, int], str]:
    """Adapt canonical single-line locators to the Reader's explicit range shape."""
    value = str(locator.get("value", ""))
    single = re.fullmatch(r"L([1-9][0-9]*)", value)
    if single is not None:
        line = int(single.group(1))
        return (line, line), f"L{line}-L{line}"
    parsed = parse_line_range(locator)
    return parsed, value


def _annotations(
    records: list[dict[str, Any]],
    source_id: str,
    selected_range: tuple[int, int] | None,
    line_count: int,
) -> list[dict[str, Any]]:
    concepts = [record for record in records if record["type"] == "concept"]
    edges = [record for record in records if record["type"] == "edge"]
    annotations: list[dict[str, Any]] = []
    for evidence in records:
        if (
            evidence["type"] != "evidence"
            or evidence["source_id"] != source_id
            or evidence["review_status"] not in {"accepted", "corrected"}
        ):
            continue
        locator = evidence["locator"]
        if locator.get("kind") != "line_range":
            continue
        evidence_range, normalized_locator = _registered_line_range(locator)
        if evidence_range[1] > line_count:
            raise ReaderValidationError("registered_evidence_out_of_range", ("locator",))
        if selected_range is not None and not _overlaps(evidence_range, selected_range):
            continue
        evidence_id = evidence["id"]
        annotations.append({
            "evidence_id": evidence_id,
            "locator": {"kind": "line_range", "value": normalized_locator},
            "proposition": evidence["proposition"],
            "review_status": evidence["review_status"],
            "concept_ids": sorted(record["id"] for record in concepts if evidence_id in record["evidence_ids"]),
            "edge_ids": sorted(record["id"] for record in edges if evidence_id in record["evidence_ids"]),
        })
    return sorted(annotations, key=lambda item: item["evidence_id"])


def load_reader(root: str | os.PathLike[str], query: Mapping[str, Any]) -> ReaderApplicationResult:
    """Return exact text for one registered Source and an optional bounded line focus."""

    if not isinstance(root, (str, os.PathLike)):
        return _reject("store", "invalid_store_root")
    snapshot = read_canonical_store(root)
    if snapshot.status != "loaded":
        problem = snapshot.problem
        safe_path = (problem.path,) if problem and problem.path and not os.path.isabs(problem.path) else ()
        return _reject("store", problem.code if problem else "store_rejected", safe_path)
    projection = project_graph_read_model(snapshot.records)
    if projection.status != "projected":
        problem = projection.problem
        return _reject(
            "projector",
            problem.code if problem else "projection_rejected",
            problem.path if problem else (),
        )
    try:
        validate_reader_query(query)
    except ReaderValidationError as error:
        return _reject("query", error.code, error.path)
    model = projection.model
    if query["snapshot_sha256"] != model["snapshot_sha256"]:
        return _reject("query", "stale_graph_snapshot", ("snapshot_sha256",))

    source = next(
        (record for record in snapshot.records if record["type"] == "source" and record["id"] == query["source_id"]),
        None,
    )
    if source is None:
        return _reject("source", "source_not_registered", ("source_id",))
    graph_source = next(item for item in model["sources"] if item["id"] == source["id"])
    try:
        resolved_root = Path(snapshot.root).resolve(strict=True)
    except (FileNotFoundError, OSError):
        return _reject("store", "store_root_missing")
    source_path = _registered_source_path(resolved_root, source.get("uri_or_path"))
    if source_path is None:
        return _reject("source", "unsafe_registered_source_path")
    try:
        source_size = source_path.stat().st_size
        if source_size < 1 or source_size > MAX_SOURCE_BYTES:
            return _reject("source", "source_size_out_of_bounds")
        source_bytes = source_path.read_bytes()
    except OSError:
        return _reject("source", "source_unreadable")
    if not source_bytes or len(source_bytes) > MAX_SOURCE_BYTES:
        return _reject("source", "source_size_out_of_bounds")
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != source["content_sha256"]:
        return _reject("source", "source_content_digest_mismatch")
    try:
        content = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _reject("source", "source_invalid_utf8")
    lines = content.splitlines(keepends=True)
    if not lines:
        return _reject("source", "source_has_no_lines")

    locator = query["locator"]
    selected_range = parse_line_range(locator) if locator is not None else None
    if selected_range is not None and selected_range[1] > len(lines):
        return _reject("query", "locator_out_of_range", ("locator", "value"))
    try:
        annotations = _annotations(snapshot.records, source["id"], selected_range, len(lines))
    except ReaderValidationError as error:
        return _reject("reader", "invalid_registered_evidence_locator", error.path)
    focus = None
    if selected_range is not None:
        start, end = selected_range
        focus = {
            "locator": locator,
            "start_line": start,
            "end_line": end,
            "excerpt": "".join(lines[start - 1 : end]),
            "evidence_ids": sorted(item["evidence_id"] for item in annotations),
            "concept_ids": sorted({item for annotation in annotations for item in annotation["concept_ids"]}),
            "edge_ids": sorted({item for annotation in annotations for item in annotation["edge_ids"]}),
        }
    payload = {
        "schema_version": APPLICATION_VERSION,
        "status": "ready",
        "response_headers": READER_RESPONSE_HEADERS,
        "document": {
            "snapshot_sha256": model["snapshot_sha256"],
            "source": {
                "id": graph_source["id"],
                "label": graph_source["label"],
                "source_kind": graph_source["source_kind"],
                "captured_at": graph_source["captured_at"],
                "content_sha256": graph_source["content_sha256"],
            },
            "content": content,
            "byte_length": len(source_bytes),
            "line_count": len(lines),
            "focus": focus,
            "annotations": annotations,
        },
    }
    try:
        validate_reader_application_result(payload)
    except ReaderValidationError as error:
        return _reject("reader", "projected_reader_document_invalid", error.path)
    return _result(payload)


__all__ = [
    "MAX_SOURCE_BYTES",
    "READER_RESPONSE_HEADERS",
    "ReaderApplicationProblem",
    "ReaderApplicationResult",
    "load_reader",
]
