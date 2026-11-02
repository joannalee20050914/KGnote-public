#!/usr/bin/env python3
"""No-model preflight for an explicitly selected, Owner-approved Product Goal.

This does not activate a LaunchAgent, reserve an attempt, initialize a Goal,
write to GitHub, or run Codex/Claude. The installed launcher must attest this
file's exact bytes and recheck the same guards before dispatching anything.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import goal_continuity as goal
import github_product_goal_control as github

SCHEMA = "kgnote.product-goal-generic-intake.v1"
ZONE = ZoneInfo("Asia/Taipei")
O2_LABEL = "com.kgnote.local-autonomy-runner"
SHA = re.compile(r"^[0-9a-f]{64}$")


class IntakeBlocked(ValueError):
    pass


def _safe(status: str, *, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA, "status": status,
        "no_model_gate": True, "model_launch_started": False,
        "model_reservation_created": False, "product_goal_dispatched": False,
        "legacy_o2_runner_used": False, "paid_api_used": False,
    }
    if spec is not None:
        result.update(goal_id=spec["goal_id"], goal_version=spec["goal_version"],
                      goal_spec_sha256=goal.goal_spec_sha256(spec))
    return result


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise IntakeBlocked("required local proof is absent or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntakeBlocked("required local proof is invalid") from exc
    if not isinstance(value, dict):
        raise IntakeBlocked("required local proof must be an object")
    return value


def _pinned_file(value: Any) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise IntakeBlocked("exact file proof has invalid fields")
    raw, digest = value["path"], value["sha256"]
    if not isinstance(raw, str) or not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise IntakeBlocked("exact file proof identity is invalid")
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise IntakeBlocked("exact file proof is absent or unsafe")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise IntakeBlocked("exact file proof bytes differ")
    return path.resolve()


def _inside(repo: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise IntakeBlocked("Goal spec path must remain repository-relative")
    path = repo / candidate
    if path.is_symlink() or not path.is_file():
        raise IntakeBlocked("Goal spec file is absent or unsafe")
    try:
        path.resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise IntakeBlocked("Goal spec leaves the repository") from exc
    return path


def _canonical_remote(raw: str) -> str:
    raw = raw.strip()
    for prefix in ("https://github.com/", "git@github.com:"):
        if raw.startswith(prefix):
            suffix = raw[len(prefix):].removesuffix(".git")
            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", suffix):
                return suffix
    raise IntakeBlocked("repository remote is not a canonical GitHub origin")


def _require_repository(repo: Path, spec: dict[str, Any],
                        runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    completed = runner(["git", "-C", str(repo), "remote", "get-url", "origin"],
                       capture_output=True, text=True, check=False)
    if completed.returncode or _canonical_remote(completed.stdout) != spec["repository"]:
        raise IntakeBlocked("Goal repository differs from GitHub origin")


def _window(spec: dict[str, Any], now: datetime) -> bool:
    if now.tzinfo is None:
        raise IntakeBlocked("observation time must have a timezone")
    local = now.astimezone(ZONE)
    window = spec["work_window"]
    return (local.weekday() in window["weekdays"]
            and window["start"] <= local.strftime("%H:%M") < window["end"])


def _lock_available(path: Path) -> bool:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise IntakeBlocked("pre-existing global writer lock proof is absent")
    with path.open("rb") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        finally:
            # A successful read-only probe never reserves or owns model work.
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return True


def _legacy_unloaded(runner: Callable[..., subprocess.CompletedProcess[str]]) -> bool:
    completed = runner(
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{O2_LABEL}"],
        capture_output=True, text=True, check=False,
    )
    return completed.returncode != 0


def _require_isolated_proofs(
    guard: dict[str, Any], spec: dict[str, Any], repo: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    if guard.get("schema_version") != "kgnote.product-goal-isolation-guard.v1":
        raise IntakeBlocked("isolation guard schema differs")
    if guard.get("goal_id") != spec["goal_id"] or guard.get(
        "goal_spec_sha256"
    ) != goal.goal_spec_sha256(spec):
        raise IntakeBlocked("isolation guard is not bound to the exact Product Goal")
    protected = guard.get("legacy_o2")
    if not isinstance(protected, dict) or set(protected) != {"state", "ledger"}:
        raise IntakeBlocked("legacy O2 preservation proof is incomplete")
    o2_state = _pinned_file(protected["state"])
    o2_ledger = _pinned_file(protected["ledger"])
    if o2_state == o2_ledger:
        raise IntakeBlocked("legacy O2 state and ledger overlap")
    selected = guard.get("private_source_selection")
    if not isinstance(selected, dict) or set(selected) != {"receipt"}:
        return False
    selected_receipt = _read(_pinned_file(selected["receipt"]))
    if (selected_receipt.get("goal_id") != spec["goal_id"]
            or selected_receipt.get("goal_spec_sha256") != goal.goal_spec_sha256(spec)
            or selected_receipt.get("selected_by_owner") is not True):
        raise IntakeBlocked("private source selection is not bound to this Goal")
    # The original source remains entirely on the local host and never enters
    # any GitHub output or model request through this preflight.
    source_path = _pinned_file(selected_receipt.get("source"))
    if source_path.is_relative_to(repo):
        raise IntakeBlocked("private source cannot be stored inside the public repository")
    deps = guard.get("dependencies")
    if not isinstance(deps, dict):
        return False
    if set(spec["dependencies"]) - set(deps):
        return False
    for dependency in spec["dependencies"]:
        receipt = _read(_pinned_file(deps[dependency]))
        if receipt.get("dependency_id") != dependency or receipt.get("status") != "PASS":
            raise IntakeBlocked("Goal dependency receipt is not verified")
    runtime = guard.get("product_runtime")
    if not isinstance(runtime, dict) or set(runtime) != {"state", "ledger", "writer_lock"}:
        return False
    state = Path(str(runtime["state"]))
    ledger = Path(str(runtime["ledger"]))
    writer = Path(str(runtime["writer_lock"]))
    if (not state.is_absolute() or not ledger.is_absolute()
            or state.resolve() == ledger.resolve()
            or state.resolve() in {o2_state, o2_ledger}
            or ledger.resolve() in {o2_state, o2_ledger}
            or state.resolve().parent in {o2_state.parent, o2_ledger.parent}
            or ledger.resolve().parent in {o2_state.parent, o2_ledger.parent}):
        raise IntakeBlocked("new Product Goal runtime is not separated from O2")
    if not _lock_available(writer):
        return False
    if not _legacy_unloaded(runner):
        return False
    return True


def inspect(
    *, repo: Path, spec_relative: str, guard_path: Path, guard_sha256: str,
    stop_marker: Path, now: datetime,
    comments_fetcher: Callable[[dict[str, Any]], list[dict[str, Any]]] = github.fetch_issue_comments,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if stop_marker.exists() or stop_marker.is_symlink():
        return _safe("STOPPED")
    if not SHA.fullmatch(guard_sha256):
        raise IntakeBlocked("guard pin is not an exact SHA-256")
    repo = repo.resolve()
    spec = goal.load_json(_inside(repo, spec_relative))
    goal.validate_goal_spec(spec)
    _require_repository(repo, spec, runner)
    if "paid_api" not in spec["forbidden_operations"] or "merge" not in spec["forbidden_operations"]:
        raise IntakeBlocked("proposed Goal lacks required paid and merge restrictions")
    if any(not p["subscription_only"] or p["paid_api_fallback"]
           for p in spec["resource_policy"]["providers"].values()):
        raise IntakeBlocked("provider policy permits unapproved paid execution")
    if not _window(spec, now):
        return _safe("WAITING_WORK_WINDOW", spec=spec)
    comments = comments_fetcher(spec)
    if not isinstance(comments, list):
        raise IntakeBlocked("GitHub Owner authority read-back is not a comment list")
    authority = github.resolve_authority(comments, spec)
    if authority["rejected_records"]:
        raise IntakeBlocked("invalid or conflicting Product Goal authority marker")
    if (authority["status"] != "APPROVED" or authority["authority_lease"] != "ACTIVE"
            or not authority["record"] or authority["record"]["action"] != "APPROVE"):
        return _safe("WAITING_AUTHORIZATION", spec=spec)
    if guard_path.is_symlink() or not guard_path.is_file():
        return _safe("WAITING_ISOLATION_GUARD", spec=spec)
    if guard_path.resolve().is_relative_to(repo):
        raise IntakeBlocked("private isolation guard must not live in the public repository")
    if hashlib.sha256(guard_path.read_bytes()).hexdigest() != guard_sha256:
        raise IntakeBlocked("private isolation guard bytes differ from activation pin")
    guard = _read(guard_path)
    if not _require_isolated_proofs(guard, spec, repo, runner):
        return _safe("WAITING_ISOLATION_OR_SOURCE", spec=spec)
    result = _safe("ADMISSION_ELIGIBLE_NO_MODEL_ONLY", spec=spec)
    result["authorization_comment_id"] = authority["record"]["comment_id"]
    result["authorization_body_sha256"] = authority["record"]["body_sha256"]
    # Eligibility is read-only. The existing Runner must independently reconcile
    # authority, state/ledger, source scope, live runtime identity, and quota
    # immediately before any durable attempt reservation or model launch.
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--spec", required=True, help="repository-relative Goal spec")
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--guard-sha256", required=True)
    parser.add_argument("--stop-marker", type=Path, required=True)
    parser.add_argument("--now")
    args = parser.parse_args()
    try:
        observed = datetime.fromisoformat(args.now) if args.now else datetime.now(ZONE)
        result = inspect(
            repo=args.repo, spec_relative=args.spec, guard_path=args.guard,
            guard_sha256=args.guard_sha256, stop_marker=args.stop_marker, now=observed,
        )
    except (OSError, ValueError, goal.GoalContractError, github.GitHubAuthorityError,
            subprocess.SubprocessError) as exc:
        # Do not print exception text: private source paths may be part of it.
        result = _safe("BLOCKED")
        result["reason_code"] = type(exc).__name__
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"STOPPED", "WAITING_WORK_WINDOW",
                                      "WAITING_AUTHORIZATION", "WAITING_ISOLATION_GUARD",
                                      "WAITING_ISOLATION_OR_SOURCE",
                                      "ADMISSION_ELIGIBLE_NO_MODEL_ONLY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
