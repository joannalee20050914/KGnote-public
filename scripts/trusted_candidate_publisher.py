#!/usr/bin/env python3
"""Trusted, local-only commit boundary for sandboxed Codex edits.

Codex may edit an isolated worktree, but this module alone stages and commits
after checking the exact branch, parent, changed paths, index and test receipt.
Remote push is intentionally outside this boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_PREFIXES = (".ai/", "docs/control-plane/", "docs/requirements/")
FORBIDDEN_EXACT = {"AGENTS.md", "PLAN.md", "CODEX_STATUS.md"}


class PublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublishRequest:
    worktree: Path
    branch: str
    expected_parent: str
    allowed_paths: tuple[str, ...]
    test_receipt: Path
    test_receipt_sha256: str
    message: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PublishRequest":
        try:
            request = cls(
                worktree=Path(raw["worktree"]).resolve(),
                branch=str(raw["branch"]),
                expected_parent=str(raw["expected_parent"]),
                allowed_paths=tuple(str(item) for item in raw["allowed_paths"]),
                test_receipt=Path(raw["test_receipt"]).resolve(),
                test_receipt_sha256=str(raw["test_receipt_sha256"]),
                message=str(raw["message"]),
            )
        except (KeyError, TypeError) as exc:
            raise PublishError(f"invalid publish request: {exc}") from exc
        request.validate()
        return request

    def validate(self) -> None:
        if not self.worktree.is_dir():
            raise PublishError("worktree is unavailable")
        if not self.branch.startswith("codex/") or any(ch.isspace() for ch in self.branch):
            raise PublishError("branch must be an explicit codex/* branch")
        if not SHA1_RE.fullmatch(self.expected_parent):
            raise PublishError("expected_parent must be a full lowercase commit SHA")
        if not self.allowed_paths:
            raise PublishError("allowed_paths must not be empty")
        for value in self.allowed_paths:
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or value in FORBIDDEN_EXACT or value.startswith(FORBIDDEN_PREFIXES):
                raise PublishError(f"unsafe allowed path: {value}")
        if len(self.message.strip()) < 8 or "\n" in self.message:
            raise PublishError("commit message must be one meaningful line")


def _run(command: list[str], cwd: Path, runner: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    result = runner(command, cwd=cwd, text=True, capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise PublishError(result.stderr.strip() or f"command failed: {command[0]}")
    # Porcelain status has significant leading columns; only remove line ends.
    return result.stdout.rstrip("\r\n")


def _allowed(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots)


def publish(
    request: PublishRequest,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    git = "/usr/bin/git"
    branch = _run([git, "branch", "--show-current"], request.worktree, runner)
    head = _run([git, "rev-parse", "HEAD"], request.worktree, runner)
    if branch != request.branch or head != request.expected_parent:
        raise PublishError("branch or parent identity mismatch")
    staged = _run([git, "diff", "--cached", "--name-only", "-z"], request.worktree, runner)
    if staged:
        raise PublishError("index must be empty before trusted publication")
    status = _run([git, "status", "--porcelain=v1", "-z", "--untracked-files=all"], request.worktree, runner)
    entries = [item for item in status.split("\0") if item]
    changed: list[str] = []
    for entry in entries:
        if len(entry) < 4:
            raise PublishError("malformed git status entry")
        path = entry[3:]
        if " -> " in path:
            raise PublishError("renames require a separately reviewed publisher path")
        if path in FORBIDDEN_EXACT or path.startswith(FORBIDDEN_PREFIXES):
            raise PublishError(f"control-plane or contract path is forbidden: {path}")
        if not _allowed(path, request.allowed_paths):
            raise PublishError(f"changed path is outside the work order: {path}")
        changed.append(path)
    if not changed:
        raise PublishError("no candidate changes to publish")
    receipt = request.test_receipt.read_bytes()
    if hashlib.sha256(receipt).hexdigest() != request.test_receipt_sha256:
        raise PublishError("test receipt digest mismatch")
    try:
        evidence = json.loads(receipt)
    except json.JSONDecodeError as exc:
        raise PublishError("test receipt is not JSON") from exc
    if evidence.get("status") != "PASS" or evidence.get("candidate_parent") != head:
        raise PublishError("test receipt does not authorize this parent")
    if sorted(evidence.get("changed_paths", [])) != sorted(changed):
        raise PublishError("test receipt changed-path set mismatch")
    _run([git, "add", "--", *changed], request.worktree, runner)
    try:
        tree_paths = _run([git, "diff", "--cached", "--name-only"], request.worktree, runner).splitlines()
        if sorted(tree_paths) != sorted(changed):
            raise PublishError("staged path set changed during publication")
        _run([git, "commit", "-m", request.message], request.worktree, runner)
    except Exception:
        runner([git, "restore", "--staged", "--", *changed], cwd=request.worktree,
               text=True, capture_output=True, timeout=30, check=False)
        raise
    commit = _run([git, "rev-parse", "HEAD"], request.worktree, runner)
    parent = _run([git, "rev-parse", "HEAD^"], request.worktree, runner)
    if parent != request.expected_parent:
        raise PublishError("committed parent changed unexpectedly")
    return {
        "schema_version": "kgnote.trusted-candidate-publication.v1",
        "status": "COMMITTED_LOCAL_ONLY",
        "branch": branch,
        "parent": parent,
        "commit": commit,
        "changed_paths": sorted(changed),
        "test_receipt_sha256": request.test_receipt_sha256,
        "remote_push_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True, help="trusted publication request JSON")
    args = parser.parse_args()
    try:
        raw = json.loads(args.request.read_text(encoding="utf-8"))
        result = publish(PublishRequest.from_dict(raw))
    except (OSError, json.JSONDecodeError, PublishError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
