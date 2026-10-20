"""Validation for the explicit-source Reader query and application result."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


QUERY_VERSION = "kgnote.reader-query.v1"
APPLICATION_VERSION = "kgnote.reader-application.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "reader" / "v1"
_LINE_RANGE = re.compile(r"^L([1-9][0-9]*)-L([1-9][0-9]*)$")


class ReaderValidationError(ValueError):
    """Stable validation error that never embeds source text or local paths."""

    def __init__(self, code: str, path: tuple[object, ...] = (), validator: str = "semantic"):
        self.code = code
        self.path = path
        self.validator = validator
        pointer = "/" + "/".join(str(part) for part in path) if path else "/"
        super().__init__(f"{code} at {pointer} ({validator})")


def _validator(filename: str) -> Draft202012Validator:
    with (SCHEMA_ROOT / filename).open(encoding="utf-8") as handle:
        schema = json.load(handle)
    return Draft202012Validator(schema, format_checker=FormatChecker())


_QUERY_VALIDATOR = _validator("query.schema.json")
_RESULT_VALIDATOR = _validator("application-result.schema.json")


def _schema_validate(payload: Any, validator: Draft202012Validator, code: str) -> None:
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if errors:
        error = errors[0]
        raise ReaderValidationError(code, tuple(error.absolute_path), str(error.validator))


def parse_line_range(locator: Mapping[str, Any]) -> tuple[int, int]:
    """Parse an already shape-checked line locator."""

    match = _LINE_RANGE.fullmatch(str(locator.get("value", "")))
    if match is None:
        raise ReaderValidationError("invalid_line_range", ("locator", "value"))
    start, end = (int(value) for value in match.groups())
    if start > end:
        raise ReaderValidationError("reversed_line_range", ("locator", "value"))
    return start, end


def validate_reader_query(payload: Any) -> None:
    _schema_validate(payload, _QUERY_VALIDATOR, "invalid_reader_query")
    if payload["locator"] is not None:
        parse_line_range(payload["locator"])


def _sorted_unique(values: list[str], path: tuple[object, ...]) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        raise ReaderValidationError("non_deterministic_order", path)


def _line_slice(content: str, start: int, end: int) -> str:
    return "".join(content.splitlines(keepends=True)[start - 1 : end])


def validate_reader_application_result(payload: Any) -> None:
    _schema_validate(payload, _RESULT_VALIDATOR, "invalid_reader_application_result")
    if payload["status"] == "rejected":
        return

    document = payload["document"]
    content = document["content"]
    encoded = content.encode("utf-8")
    lines = content.splitlines(keepends=True)
    if document["byte_length"] != len(encoded):
        raise ReaderValidationError("byte_length_mismatch", ("document", "byte_length"))
    if document["line_count"] != len(lines):
        raise ReaderValidationError("line_count_mismatch", ("document", "line_count"))
    digest = hashlib.sha256(encoded).hexdigest()
    if document["source"]["content_sha256"] != digest:
        raise ReaderValidationError("content_digest_mismatch", ("document", "source", "content_sha256"))

    annotation_ids = [item["evidence_id"] for item in document["annotations"]]
    _sorted_unique(annotation_ids, ("document", "annotations"))
    evidence_ids: set[str] = set()
    concept_ids: set[str] = set()
    edge_ids: set[str] = set()
    for index, annotation in enumerate(document["annotations"]):
        _sorted_unique(annotation["concept_ids"], ("document", "annotations", index, "concept_ids"))
        _sorted_unique(annotation["edge_ids"], ("document", "annotations", index, "edge_ids"))
        start, end = parse_line_range(annotation["locator"])
        if end > len(lines):
            raise ReaderValidationError("annotation_out_of_range", ("document", "annotations", index, "locator"))
        evidence_ids.add(annotation["evidence_id"])
        concept_ids.update(annotation["concept_ids"])
        edge_ids.update(annotation["edge_ids"])

    focus = document["focus"]
    if focus is None:
        return
    start, end = parse_line_range(focus["locator"])
    if (start, end) != (focus["start_line"], focus["end_line"]):
        raise ReaderValidationError("focus_line_mismatch", ("document", "focus"))
    if end > len(lines):
        raise ReaderValidationError("focus_out_of_range", ("document", "focus", "locator"))
    if focus["excerpt"] != _line_slice(content, start, end):
        raise ReaderValidationError("focus_excerpt_mismatch", ("document", "focus", "excerpt"))
    expected = {
        "evidence_ids": sorted(evidence_ids),
        "concept_ids": sorted(concept_ids),
        "edge_ids": sorted(edge_ids),
    }
    for field_name, values in expected.items():
        _sorted_unique(focus[field_name], ("document", "focus", field_name))
        if focus[field_name] != values:
            raise ReaderValidationError("focus_reference_mismatch", ("document", "focus", field_name))


__all__ = [
    "APPLICATION_VERSION",
    "QUERY_VERSION",
    "ReaderValidationError",
    "parse_line_range",
    "validate_reader_application_result",
    "validate_reader_query",
]
