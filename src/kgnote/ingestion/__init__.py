"""Adapters that register immutable source material."""

from .markdown_source import SourceMetadata, import_markdown_source

__all__ = ["SourceMetadata", "import_markdown_source"]
