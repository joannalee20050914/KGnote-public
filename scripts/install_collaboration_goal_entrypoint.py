#!/usr/bin/env python3
"""Install, attest, or roll back the unique Issue #47 LaunchAgent.

Installation writes one disabled-by-default LaunchAgent and never bootstraps or
enables it.  Rollback latches the Stop Marker before unloading/removing only
the exact new entrypoint files.  The legacy O2 LaunchAgent is read-only and
must remain unloaded throughout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


LABEL = "com.kgnote.issue47-collaboration-goal"
LEGACY_O2_LABEL = "com.kgnote.local-autonomy-runner"
CONFIG_SCHEMA = "kgnote.collaboration-goal-entrypoint-config.v1"
RECEIPT_SCHEMA = "kgnote.collaboration-goal-entrypoint-install.v1"
ROLLBACK_SCHEMA = "kgnote.collaboration-goal-entrypoint-rollback.v1"
ENGINEERING_GOAL_ID = "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION"


class EntrypointInstallError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise EntrypointInstallError(f"target is not a regular file: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(),
    )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", *args], cwd=repo, capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise EntrypointInstallError("deployment Git identity is unreadable")
    return completed.stdout.strip()


def _deployment_identity(repo: Path, expected_commit: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise EntrypointInstallError("expected deployment commit is not exact")
    if repo.is_symlink() or not repo.is_dir():
        raise EntrypointInstallError("deployment repository is absent or is a symlink")
    if _git(repo, "rev-parse", "HEAD") != expected_commit:
        raise EntrypointInstallError("deployment HEAD differs from reviewed commit")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise EntrypointInstallError("deployment repository must be clean")
    if _git(repo, "branch", "--show-current"):
        raise EntrypointInstallError("deployment repository must be detached")
    return {
        "commit": expected_commit,
        "tree": _git(repo, "rev-parse", "HEAD^{tree}"),
    }


def _launchctl_loaded(
    label: str,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    completed = command_runner(
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True, text=True, check=False,
    )
    return completed.returncode == 0


def _require_o2_unloaded(
    *, command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    if _launchctl_loaded(LEGACY_O2_LABEL, command_runner=command_runner):
        raise EntrypointInstallError("legacy O2 Runner is loaded; fail closed")


def install_disabled(
    *,
    repo: Path,
    expected_commit: str,
    python: Path,
    launch_agents: Path,
    config_path: Path,
    receipt_path: Path,
    interval_seconds: int = 900,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    repo = repo.resolve()
    identity = _deployment_identity(repo, expected_commit)
    if interval_seconds < 300:
        raise EntrypointInstallError("scheduler interval must be at least five minutes")
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise EntrypointInstallError("entrypoint Python is unavailable")
    entrypoint = repo / "scripts/collaboration_goal_entrypoint.py"
    dispatcher = repo / "scripts/collaboration_goal_dispatch.py"
    if any(not path.is_file() or path.is_symlink() for path in (entrypoint, dispatcher)):
        raise EntrypointInstallError("reviewed entrypoint or dispatcher is unavailable")
    _require_o2_unloaded(command_runner=command_runner)
    if _launchctl_loaded(LABEL, command_runner=command_runner):
        raise EntrypointInstallError("new collaboration Goal entrypoint is already loaded")

    launch_agents = launch_agents.resolve()
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{LABEL}.plist"
    for target in (plist_path, config_path, receipt_path):
        if target.exists() or target.is_symlink():
            raise EntrypointInstallError(f"refusing to replace existing target: {target}")

    config = {
        "schema_version": CONFIG_SCHEMA,
        "engineering_goal_id": ENGINEERING_GOAL_ID,
        "status": "DISABLED",
        "deployment_repository": str(repo),
        "deployment_commit": expected_commit,
        "deployment_tree": identity["tree"],
        "dispatcher": "scripts/collaboration_goal_dispatch.py",
        "stop_marker": ".ai/ORCHESTRATOR_STOP",
        "product_goal": None,
        "activation_authority": None,
    }
    _atomic_json(config_path, config)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(entrypoint), "--config", str(config_path)],
        "Disabled": True,
        "RunAtLoad": False,
        "KeepAlive": False,
        "StartInterval": interval_seconds,
        "ProcessType": "Background",
    }
    _atomic_bytes(plist_path, plistlib.dumps(plist, fmt=plistlib.FMT_XML), mode=0o600)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "INSTALLED_DISABLED_NOT_LOADED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engineering_goal_id": ENGINEERING_GOAL_ID,
        "label": LABEL,
        "legacy_o2_label": LEGACY_O2_LABEL,
        "deployment_repository": str(repo),
        "deployment": identity,
        "python": str(python),
        "entrypoint": str(entrypoint),
        "entrypoint_sha256": _sha256(entrypoint),
        "dispatcher_sha256": _sha256(dispatcher),
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "plist_path": str(plist_path),
        "plist_sha256": _sha256(plist_path),
        "receipt_path": str(receipt_path),
        "activation": "DISABLED_BY_DEFAULT",
        "launchctl_bootstrap_performed": False,
        "legacy_o2_runner_loaded": False,
    }
    _atomic_json(receipt_path, receipt)
    return receipt


def read_status(
    receipt_path: Path,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise EntrypointInstallError("entrypoint install receipt is unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise EntrypointInstallError("entrypoint install receipt schema differs")
    config_path = Path(str(receipt["config_path"]))
    plist_path = Path(str(receipt["plist_path"]))
    if _sha256(config_path) != receipt.get("config_sha256"):
        raise EntrypointInstallError("disabled entrypoint config bytes drifted")
    if _sha256(plist_path) != receipt.get("plist_sha256"):
        raise EntrypointInstallError("disabled LaunchAgent bytes drifted")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    plist = plistlib.loads(plist_path.read_bytes())
    _require_o2_unloaded(command_runner=command_runner)
    new_loaded = _launchctl_loaded(LABEL, command_runner=command_runner)
    if config.get("status") != "DISABLED" or plist.get("Disabled") is not True:
        raise EntrypointInstallError("entrypoint is not disabled by default")
    if new_loaded:
        raise EntrypointInstallError("disabled entrypoint is unexpectedly loaded")
    return {
        "schema_version": RECEIPT_SCHEMA,
        "status": "STOPPED",
        "label": LABEL,
        "loaded": False,
        "legacy_o2_runner_loaded": False,
        "deployment": receipt["deployment"],
    }


def rollback(
    receipt_path: Path,
    *,
    rollback_receipt_path: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise EntrypointInstallError("entrypoint install receipt is unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise EntrypointInstallError("entrypoint install receipt schema differs")
    _require_o2_unloaded(command_runner=command_runner)
    repo = Path(str(receipt["deployment_repository"])).resolve()
    config_path = Path(str(receipt["config_path"]))
    plist_path = Path(str(receipt["plist_path"]))
    if _sha256(config_path) != receipt.get("config_sha256"):
        raise EntrypointInstallError("refusing rollback after config drift")
    if _sha256(plist_path) != receipt.get("plist_sha256"):
        raise EntrypointInstallError("refusing rollback after LaunchAgent drift")

    stop_marker = repo / ".ai/ORCHESTRATOR_STOP"
    marker_preexisting = stop_marker.exists() or stop_marker.is_symlink()
    if marker_preexisting:
        if stop_marker.is_symlink() or not stop_marker.is_file():
            raise EntrypointInstallError("existing Stop Marker is not a regular file")
    else:
        _atomic_bytes(
            stop_marker,
            b"Issue #47 collaboration Goal rollback; do not auto-resume.\n",
            mode=0o600,
        )
    was_loaded = _launchctl_loaded(LABEL, command_runner=command_runner)
    if was_loaded:
        completed = command_runner(
            ["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode:
            raise EntrypointInstallError("new collaboration entrypoint could not be unloaded")
    if _launchctl_loaded(LABEL, command_runner=command_runner):
        raise EntrypointInstallError("new collaboration entrypoint remains loaded")
    _require_o2_unloaded(command_runner=command_runner)
    plist_path.unlink()
    config_path.unlink()
    result = {
        "schema_version": ROLLBACK_SCHEMA,
        "status": "STOPPED",
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        "label": LABEL,
        "was_loaded": was_loaded,
        "entrypoint_files_removed": [str(plist_path), str(config_path)],
        "stop_marker": str(stop_marker),
        "stop_marker_preexisting": marker_preexisting,
        "install_receipt": str(receipt_path),
        "preserved_evidence": True,
        "legacy_o2_runner_loaded": False,
    }
    _atomic_json(rollback_receipt_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install = subparsers.add_parser("install-disabled")
    install.add_argument("--repo", type=Path, required=True)
    install.add_argument("--expected-commit", required=True)
    install.add_argument("--python", type=Path, required=True)
    install.add_argument("--launch-agents", type=Path, required=True)
    install.add_argument("--config", type=Path, required=True)
    install.add_argument("--receipt", type=Path, required=True)
    status = subparsers.add_parser("status")
    status.add_argument("--receipt", type=Path, required=True)
    roll = subparsers.add_parser("rollback")
    roll.add_argument("--receipt", type=Path, required=True)
    roll.add_argument("--rollback-receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "install-disabled":
            result = install_disabled(
                repo=args.repo,
                expected_commit=args.expected_commit,
                python=args.python,
                launch_agents=args.launch_agents,
                config_path=args.config,
                receipt_path=args.receipt,
            )
        elif args.command == "status":
            result = read_status(args.receipt)
        else:
            result = rollback(
                args.receipt, rollback_receipt_path=args.rollback_receipt,
            )
    except (EntrypointInstallError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
