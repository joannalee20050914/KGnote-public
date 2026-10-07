#!/usr/bin/env python3
"""One-command local generator for the disposable Obsidian native spike."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kgnote.obsidian_native import (  # noqa: E402
    NativeSpikeError,
    augment_native_workspace,
    validate_native_workspace,
)
from kgnote.personal_alpha import (  # noqa: E402
    PersonalAlphaMaterializationError,
    PersonalAlphaMaterializationResult,
    PersonalAlphaPreviewError,
    build_learning_workspace_preview,
    materialize_learning_workspace,
    read_back_learning_workspace,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a disposable learner-first Markdown workspace plus optional "
            "deterministic JSON Canvas navigation. No external service is called."
        )
    )
    parser.add_argument("source", help="Path to one explicit UTF-8 Markdown source")
    parser.add_argument(
        "--vault",
        required=True,
        help=(
            "Existing disposable parent directory. Open the printed Workspace path, not this "
            "parent, as the Obsidian vault root; formal/private vaults are out of scope"
        ),
    )
    parser.add_argument(
        "--space",
        default="personal",
        help="Short learning-space name used in candidate identity",
    )
    parser.add_argument(
        "--source-key",
        help=(
            "Optional stable namespaced external identifier used instead of the absolute "
            "source path for portable source/workspace identity"
        ),
    )
    return parser


def _error(error: Exception, stream: TextIO) -> None:
    code = getattr(error, "code", "unexpected_error")
    action = getattr(
        error,
        "action",
        "Preserve the source and disposable destination, then report this failure.",
    )
    stream.write(f"KGnote native spike could not continue [{code}].\n")
    stream.write(f"Problem: {error}\n")
    stream.write(f"Next: {action}\n")


def _materialize_or_reuse(preview, destination: str) -> PersonalAlphaMaterializationResult:
    """Avoid rewriting the Markdown baseline when an identical native vault already exists."""

    workspace_relative = Path(str(preview.payload["planned_artifacts"]["workspace_root"]))
    workspace = Path(destination).expanduser().resolve() / workspace_relative
    if workspace.is_dir() and not workspace.is_symlink():
        audit = read_back_learning_workspace(workspace)
        if audit["source_sha256"] == preview.payload["source"]["content_sha256"]:
            return PersonalAlphaMaterializationResult(
                status="unchanged",
                workspace_path=str(workspace.resolve()),
                entry_note=str(Path(audit["entry_note"])),
                source_sha256=str(audit["source_sha256"]),
                created_files=0,
                updated_files=0,
                unchanged_files=int(audit["managed_files"]) + 1,
                read_back=True,
                recovered_interrupted_transaction=False,
            )
    return materialize_learning_workspace(preview, destination)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = _parser().parse_args(argv)
    try:
        preview = build_learning_workspace_preview(
            args.source, space=args.space, source_key=args.source_key
        )
        markdown = _materialize_or_reuse(preview, args.vault)
        native = augment_native_workspace(preview, markdown.workspace_path)
        audit = validate_native_workspace(preview, markdown.workspace_path)
    except PersonalAlphaPreviewError as error:
        _error(error, stderr)
        return 2
    except PersonalAlphaMaterializationError as error:
        _error(error, stderr)
        return 3
    except NativeSpikeError as error:
        _error(error, stderr)
        return 4

    stdout.write("# KGnote Obsidian native spike\n\n")
    stdout.write(f"Markdown status: {markdown.status}\n")
    stdout.write(f"Native status: {native.status}\n")
    stdout.write(f"Source shape: {native.source_shape}\n")
    stdout.write(f"Workspace: {native.workspace_path}\n")
    stdout.write(f"Obsidian vault root: {native.workspace_path}\n")
    stdout.write(f"Start Here: {markdown.entry_note}\n")
    stdout.write(f"Canvas: {native.canvas_path}\n")
    stdout.write(f"Canvas guide: {native.guide_path}\n")
    stdout.write(f"Nodes/edges: {native.node_count}/{native.edge_count}\n")
    stdout.write(f"Canonical digest: {native.canonical_digest}\n")
    stdout.write(f"Markdown digest: {native.markdown_digest}\n")
    stdout.write(
        "Read-back: passed "
        f"({audit['checked_files']} files, {audit['checked_anchors']} anchors, "
        f"{audit['checked_text_links']} text links).\n"
    )
    stdout.write(
        "Evidence boundary: vault-root paths and Reading-view files passed static read-back; "
        "native Obsidian and human smoke remain pending.\n"
    )
    if native.recovered_interrupted_transaction:
        stdout.write("Recovery: an interrupted native transaction was restored before this run.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
