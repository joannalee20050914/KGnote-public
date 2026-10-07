"""Deterministic optional Obsidian-native navigation artifacts."""

from .spike import (
    NATIVE_MANIFEST_VERSION,
    NativeSpikeError,
    NativeSpikeResult,
    augment_native_workspace,
    build_native_canvas,
)
from .validator import validate_markdown_subpath, validate_native_workspace

__all__ = [
    "NATIVE_MANIFEST_VERSION",
    "NativeSpikeError",
    "NativeSpikeResult",
    "augment_native_workspace",
    "build_native_canvas",
    "validate_markdown_subpath",
    "validate_native_workspace",
]
