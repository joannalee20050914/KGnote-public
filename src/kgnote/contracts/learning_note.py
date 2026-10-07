"""Validation for document-level LearningNote v1 records and save commands."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


LEARNING_NOTE_VERSION = "kgnote.learning-note.v1"
SAVE_REQUEST_VERSION = "kgnote.learning-note-save.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "learning-note" / "v1"
_RAW_HTML = re.compile(r"(^|\n)[ \t]*</?[A-Za-z][^\n>]*>")
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(")


class LearningNoteValidationError(ValueError):
    def __init__(self, code: str, path: tuple[object, ...] = (), validator: str = "semantic"):
        self.code = code
        self.path = path
        self.validator = validator
        super().__init__(f"{code} at {'/'.join(map(str, path)) or '/'} ({validator})")


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    registry = None
    if filename == "save-request.schema.json":
        document = json.loads((SCHEMA_ROOT / "learning-note.schema.json").read_text(encoding="utf-8"))
        try:
            from referencing import Registry, Resource
            registry = Registry().with_resource(document["$id"], Resource.from_contents(document))
        except ImportError:  # pragma: no cover - jsonschema dependency supplies referencing
            registry = None
    options = {"format_checker": FormatChecker()}
    if registry is not None:
        options["registry"] = registry
    return Draft202012Validator(schema, **options)


_DOCUMENT_VALIDATOR = _validator("learning-note.schema.json")
_SAVE_VALIDATOR = _validator("save-request.schema.json")


def _validate(payload: Any, validator: Draft202012Validator, code: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda error: tuple(str(part) for part in error.absolute_path))
    if errors:
        error = errors[0]
        raise LearningNoteValidationError(code, tuple(error.absolute_path), str(error.validator))


def _semantic_markdown(markdown: str) -> None:
    if "\x00" in markdown:
        raise LearningNoteValidationError("markdown_contains_nul", ("markdown",))
    if _RAW_HTML.search(markdown):
        raise LearningNoteValidationError("raw_html_not_allowed", ("markdown",))
    if _MARKDOWN_IMAGE.search(markdown):
        raise LearningNoteValidationError("markdown_images_not_allowed", ("markdown",))


def _semantic_anchors(anchors: list[dict[str, Any]]) -> None:
    ids = [anchor["id"] for anchor in anchors]
    if len(ids) != len(set(ids)):
        raise LearningNoteValidationError("duplicate_source_anchor", ("source_anchors",))
    for index, anchor in enumerate(anchors):
        match = re.fullmatch(r"L([1-9][0-9]*)-L([1-9][0-9]*)", anchor["locator"]["value"])
        if match is None or int(match.group(1)) > int(match.group(2)):
            raise LearningNoteValidationError("invalid_source_anchor_range", ("source_anchors", index, "locator", "value"))


def validate_learning_note(payload: Any) -> None:
    _validate(payload, _DOCUMENT_VALIDATOR, "invalid_learning_note")
    _semantic_anchors(payload["source_anchors"])
    _semantic_markdown(payload["markdown"])


def validate_learning_note_save(payload: Any) -> None:
    _validate(payload, _SAVE_VALIDATOR, "invalid_learning_note_save")
    _semantic_anchors(payload["source_anchors"])
    _semantic_markdown(payload["markdown"])


__all__ = [
    "LEARNING_NOTE_VERSION", "SAVE_REQUEST_VERSION", "LearningNoteValidationError",
    "validate_learning_note", "validate_learning_note_save",
]
