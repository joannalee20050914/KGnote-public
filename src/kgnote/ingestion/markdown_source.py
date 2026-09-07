"""Read one explicit Markdown source into an ExtractionInput payload."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kgnote.contracts.extraction import (
    ExtractionInputValidationError,
    validate_extraction_input,
)


@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    source_kind: str
    title: str
    captured_at: str | None
    locator_basis: str


class MarkdownSourceImportError(ValueError):
    """An importer failure that never embeds source content."""

    def __init__(self, code: str, *, field_path: tuple[object, ...] = ()):
        self.code = code
        self.field_path = field_path
        pointer = (
            "/" + "/".join(str(part) for part in field_path)
            if field_path
            else "/"
        )
        super().__init__(f"{code} at {pointer}")


def build_extraction_input(
    *,
    content: str,
    metadata: SourceMetadata,
) -> dict[str, Any]:
    """Purely build and validate an ExtractionInput v1 payload."""

    payload = {
        "schema_version": "kgnote.extraction-input.v1",
        "source": {
            "id": metadata.source_id,
            "source_kind": metadata.source_kind,
            "title": metadata.title,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "captured_at": metadata.captured_at,
            "locator_basis": metadata.locator_basis,
            "content": content,
        },
    }
    try:
        validate_extraction_input(payload)
    except ExtractionInputValidationError as error:
        raise MarkdownSourceImportError(
            error.code,
            field_path=error.path,
        ) from error
    return payload


def import_markdown_source(
    path: str | Path,
    *,
    metadata: SourceMetadata,
) -> dict[str, Any]:
    """Read exactly one local Markdown file and return a validated payload."""

    source_path = Path(path)
    if not source_path.exists():
        raise MarkdownSourceImportError("path_not_found")
    if not source_path.is_file():
        raise MarkdownSourceImportError("not_regular_file")
    if source_path.suffix.lower() != ".md":
        raise MarkdownSourceImportError("unsupported_extension")

    try:
        source_bytes = source_path.read_bytes()
    except OSError as error:
        raise MarkdownSourceImportError("read_failed") from error
    try:
        content = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise MarkdownSourceImportError("invalid_utf8") from error

    if not content.strip():
        raise MarkdownSourceImportError("empty_content")

    return build_extraction_input(
        content=content,
        metadata=metadata,
    )
