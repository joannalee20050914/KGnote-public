#!/usr/bin/env python3
"""Trusted, idempotent bootstrap for the one authorized successor worktree."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import hashlib
from pathlib import Path


SUCCESSOR_EVENT_RE = re.compile(r"source-library-successor-codex-20261019(?:-cycle-(?:0[2-9]|1[0-2]))?")
AUTHORIZED_WORKTREE = Path("/home/kgnote/.local/share/kgnote/source-library-successor-20261019")
WORKTREE_ROOT = Path("/home/kgnote/.local/share/kgnote")
GENERIC_ROOT = WORKTREE_ROOT / "work-items"


class BootstrapError(RuntimeError):
    pass


def _require_real_directory(
    path: Path, *, owner_uid: int, owner_gid: int, require_private: bool = True
) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise BootstrapError(f"required directory is absent: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BootstrapError(f"path is not a real directory: {path}")
    if metadata.st_uid != owner_uid or metadata.st_gid != owner_gid:
        raise BootstrapError(f"directory ownership mismatch: {path}")
    if require_private and stat.S_IMODE(metadata.st_mode) & 0o022:
        raise BootstrapError(f"directory is group/world writable: {path}")
    return metadata


def _validate_generic_identity(
    identity: object, *, event_id: str, stage: str, working_directory: Path,
) -> dict[str, object]:
    if not isinstance(identity, dict) or identity.get("schema_version") != "kgnote.authorized-work-identity.v1":
        raise BootstrapError("generic bootstrap identity is missing or unsupported")
    repository, issue = identity.get("repository"), identity.get("issue")
    goal_id, work_item_id = identity.get("goal_id"), identity.get("work_item_id")
    branch, slug = identity.get("branch"), identity.get("worktree_slug")
    authority_record, authority_sha256 = identity.get("authority_record"), identity.get("authority_sha256")
    if repository != "joannalee20050914/KGnote-public" or not isinstance(issue, int) or issue < 1:
        raise BootstrapError("generic bootstrap repository or Issue is invalid")
    if not isinstance(goal_id, str) or not re.fullmatch(r"GOAL-KGNOTE-[A-Z0-9-]+", goal_id):
        raise BootstrapError("generic bootstrap goal identity is invalid")
    if not isinstance(work_item_id, str) or not re.fullmatch(r"D2-T[0-9]{2}", work_item_id):
        raise BootstrapError("generic bootstrap work item is invalid")
    if not isinstance(branch, str) or not re.fullmatch(r"codex/[a-z0-9][a-z0-9-]{2,80}", branch):
        raise BootstrapError("generic bootstrap branch is invalid")
    expected_slug = f"issue-{issue}-{work_item_id.lower()}"
    if slug != expected_slug or event_id != f"{expected_slug}-codex-20261019" or stage != "codex":
        raise BootstrapError("generic bootstrap event identity is inconsistent")
    if authority_record != f"https://github.com/{repository}/issues/{issue}":
        raise BootstrapError("generic bootstrap authority record is invalid")
    if not isinstance(authority_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", authority_sha256):
        raise BootstrapError("generic bootstrap authority digest is invalid")
    if working_directory != GENERIC_ROOT / expected_slug:
        raise BootstrapError("generic bootstrap directory is not identity-bound")
    return identity


def prepare(event_id: str, stage: str, working_directory: Path, identity: object = None) -> dict[str, object]:
    legacy = SUCCESSOR_EVENT_RE.fullmatch(event_id) and stage == "codex" and working_directory == AUTHORIZED_WORKTREE and identity is None
    if not legacy:
        if identity is None:
            raise BootstrapError("event, stage, and working-directory identity are not authorized")
        identity = _validate_generic_identity(identity, event_id=event_id, stage=stage, working_directory=working_directory)
    allowed_parent = WORKTREE_ROOT if legacy else GENERIC_ROOT
    if not working_directory.is_absolute() or working_directory.parent != allowed_parent:
        raise BootstrapError("working directory is outside the exact authorized root")
    uid, gid = os.geteuid(), os.getegid()
    # The pre-existing shared workspace root is managed by the trusted guest
    # setup and may be group-writable.  The newly authorized leaf must be
    # private; neither path may be a symlink or owned by another identity.
    _require_real_directory(WORKTREE_ROOT, owner_uid=uid, owner_gid=gid, require_private=False)
    if not legacy:
        if GENERIC_ROOT.is_symlink():
            raise BootstrapError("generic worktree root must not be a symbolic link")
        if not GENERIC_ROOT.exists():
            GENERIC_ROOT.mkdir(mode=0o700)
        _require_real_directory(GENERIC_ROOT, owner_uid=uid, owner_gid=gid)
    if working_directory.is_symlink():
        raise BootstrapError("working directory must not be a symbolic link")
    created = False
    if not working_directory.exists():
        working_directory.mkdir(mode=0o700)
        created = True
    metadata = _require_real_directory(working_directory, owner_uid=uid, owner_gid=gid)
    return {
        "schema_version": "kgnote.worker-bootstrap.v1",
        "status": "READY",
        "event_id": event_id,
        "stage": stage,
        "working_directory": str(working_directory),
        "created": created,
        "owner_uid": metadata.st_uid,
        "owner_gid": metadata.st_gid,
        "mode": oct(stat.S_IMODE(metadata.st_mode)),
        "identity_sha256": hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest() if identity is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--working-directory", required=True, type=Path)
    parser.add_argument("--identity-json")
    args = parser.parse_args()
    try:
        identity = json.loads(args.identity_json) if args.identity_json else None
        result = prepare(args.event_id, args.stage, args.working_directory, identity)
    except (BootstrapError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
