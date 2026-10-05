#!/usr/bin/env python3
"""One-command, local-only KGnote Personal Alpha workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kgnote.personal_alpha import (  # noqa: E402
    PersonalAlphaMaterializationError,
    PersonalAlphaPreviewError,
    build_learning_workspace_preview,
    materialize_learning_workspace,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Turn one explicitly selected Markdown learning source into a local, "
            "plugin-free Obsidian Personal Alpha workspace. No external API is called."
        )
    )
    parser.add_argument("source", help="Path to one UTF-8 .md learning source")
    parser.add_argument(
        "--vault",
        required=True,
        help="Existing Obsidian vault or disposable destination directory",
    )
    parser.add_argument(
        "--space",
        default="personal",
        help="Short learning-space name used only in candidate identity (default: personal)",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Print the exact learning preview and perform zero destination writes",
    )
    return parser


def _error(error: Exception, stream: TextIO) -> None:
    code = getattr(error, "code", "unexpected_error")
    action = getattr(error, "action", "Preserve the source and destination, then report this failure.")
    stream.write(f"KGnote Personal Alpha could not continue [{code}].\n")
    stream.write(f"Problem: {error}\n")
    stream.write(f"Next: {action}\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = _parser().parse_args(argv)
    try:
        preview = build_learning_workspace_preview(args.source, space=args.space)
    except PersonalAlphaPreviewError as error:
        _error(error, stderr)
        return 2

    stdout.write(preview.markdown)
    if not preview.markdown.endswith("\n"):
        stdout.write("\n")
    if args.preview_only:
        stdout.write("Preview complete: zero files written. Remove --preview-only to materialize this plan.\n")
        return 0

    try:
        result = materialize_learning_workspace(preview, args.vault)
    except PersonalAlphaMaterializationError as error:
        _error(error, stderr)
        return 3

    stdout.write("\n## Materialization result\n\n")
    stdout.write(f"Status: {result.status}\n")
    stdout.write(f"Entry note: {result.entry_note}\n")
    stdout.write(f"Workspace: {result.workspace_path}\n")
    stdout.write(f"Source SHA-256: {result.source_sha256}\n")
    stdout.write(
        "Files: "
        f"{result.created_files} created, {result.updated_files} updated, "
        f"{result.unchanged_files} unchanged\n"
    )
    stdout.write("Read-back: passed\n")
    if result.recovered_interrupted_transaction:
        stdout.write("Recovery: an interrupted prior transaction was recovered before this run.\n")
    stdout.write(f"Next: Open `{result.entry_note}` in Obsidian.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
