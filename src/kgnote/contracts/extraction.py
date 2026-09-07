"""Validation helpers for the versioned extraction boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "extraction" / "v1"


class ExtractionInputValidationError(ValueError):
    """A safe, machine-assertable ExtractionInput validation failure."""

    def __init__(self, code: str, path: tuple[object, ...], validator: str):
        self.code = code
        self.path = path
        self.validator = validator
        pointer = "/" + "/".join(str(part) for part in path) if path else "/"
        super().__init__(f"{code} at {pointer} ({validator})")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _build_input_validator() -> Draft202012Validator:
    definitions = _load_json(SCHEMA_ROOT / "definitions.schema.json")
    input_schema = _load_json(SCHEMA_ROOT / "input.schema.json")
    registry = Registry().with_resource(
        definitions["$id"], Resource.from_contents(definitions)
    )
    return Draft202012Validator(
        input_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


_INPUT_VALIDATOR = _build_input_validator()


def _error_code(path: tuple[object, ...]) -> str:
    field_codes = {
        ("source", "id"): "invalid_source_id",
        ("source", "source_kind"): "invalid_source_kind",
        ("source", "title"): "invalid_title",
        ("source", "content_sha256"): "invalid_content_sha256",
        ("source", "captured_at"): "invalid_captured_at",
        ("source", "locator_basis"): "invalid_locator_basis",
        ("source", "content"): "invalid_content",
    }
    return field_codes.get(path, "invalid_extraction_input")


def validate_extraction_input(payload: Mapping[str, Any]) -> None:
    """Validate a payload without returning or logging its potentially private data."""

    errors = sorted(
        _INPUT_VALIDATOR.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if not errors:
        return

    error = errors[0]
    path = tuple(error.absolute_path)
    raise ExtractionInputValidationError(
        code=_error_code(path),
        path=path,
        validator=str(error.validator),
    )
