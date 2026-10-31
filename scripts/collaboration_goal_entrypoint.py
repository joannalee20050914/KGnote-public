#!/usr/bin/env python3
"""Fail-closed launcher for the Issue #47 collaboration Goal dispatcher.

The installed configuration is deliberately disabled.  A later, separately
authorized Product Goal can replace it with an exact enabled configuration;
until then this entrypoint never reads GitHub and never starts a worker.
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
from pathlib import Path
from typing import Any, Callable


CONFIG_SCHEMA = "kgnote.collaboration-goal-entrypoint-config.v1"
RECEIPT_SCHEMA = "kgnote.collaboration-goal-entrypoint-install.v1"
ACTIVATION_SCHEMA = "kgnote.collaboration-goal-entrypoint-activation.v1"
RESULT_SCHEMA = "kgnote.collaboration-goal-entrypoint-result.v1"
ENABLED_STATUS = "ENABLED_FOR_EXACT_PRODUCT_GOAL"
DISABLED_STATUSES = {"DISABLED", "ROLLED_BACK"}
ENGINEERING_GOAL_ID = "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION"
LEGACY_O2_LABEL = "com.kgnote.local-autonomy-runner"


class EntrypointError(RuntimeError):
    pass


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EntrypointError("entrypoint config is absent or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EntrypointError("entrypoint config is not valid JSON") from exc
    if not isinstance(value, dict) or value.get("schema_version") != CONFIG_SCHEMA:
        raise EntrypointError("entrypoint config schema differs")
    if value.get("status") not in DISABLED_STATUSES | {ENABLED_STATUS}:
        raise EntrypointError("entrypoint config status is invalid")
    return value


def _inside(root: Path, raw: str, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise EntrypointError(f"{label} leaves the deployment repository") from exc
    return resolved


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EntrypointError(f"{label} is unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EntrypointError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EntrypointError(f"{label} root is not an object")
    return value


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", *args], cwd=repo,
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise EntrypointError("deployment Git identity is unreadable")
    return completed.stdout.strip()


def _require_no_unexpected_model_processes(
    *, command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    completed = command_runner(
        ["/bin/ps", "-axo", "pid=,command="],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise EntrypointError("cannot prove the model-process lane is idle")
    unexpected: list[str] = []
    for raw in completed.stdout.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)$", raw)
        if not match or int(match.group(1)) == os.getpid():
            continue
        command = match.group(2)
        if re.search(r"(?:^|\s)(?:\S*/)?codex\s+exec(?:\s|$)", command):
            unexpected.append(f"pid={match.group(1)} codex-exec")
        elif re.search(
            r"(?:^|\s)(?:\S*/)?claude\s+(?:.*\s)?(?:-p|--print)(?:\s|$)",
            command,
        ):
            unexpected.append(f"pid={match.group(1)} claude-print")
    if unexpected:
        raise EntrypointError(
            "unexpected model process is active: " + ", ".join(unexpected)
        )


def _require_no_competing_writer(repo: Path) -> None:
    lock_path = repo / "output/control-plane/collaboration-goal/writer.lock"
    if not lock_path.exists() and not lock_path.is_symlink():
        return
    if lock_path.is_symlink() or not lock_path.is_file():
        raise EntrypointError("collaboration Goal writer lock is not a regular file")
    with lock_path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EntrypointError("another collaboration Goal writer is active") from exc
        finally:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _require_o2_unloaded(
    *, command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    completed = command_runner(
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{LEGACY_O2_LABEL}"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode == 0:
        raise EntrypointError("legacy O2 Runner is loaded; fail closed")


def _verify_enabled_identity(
    config_path: Path, config: dict[str, Any], *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[Path, Path]:
    receipt_path = Path(str(config.get("install_receipt", "")))
    activation_path = Path(str(config.get("activation_record", "")))
    receipt = _load_object(receipt_path, "install receipt")
    activation = _load_object(activation_path, "activation record")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise EntrypointError("install receipt schema differs")
    if activation.get("schema_version") != ACTIVATION_SCHEMA:
        raise EntrypointError("activation record schema differs")
    repo = Path(str(config.get("deployment_repository", ""))).resolve()
    if not repo.is_dir() or repo.is_symlink():
        raise EntrypointError("deployment repository is absent or is a symlink")
    deployment = receipt.get("deployment")
    if not isinstance(deployment, dict):
        raise EntrypointError("install receipt deployment identity is missing")
    commit = str(deployment.get("commit", ""))
    tree = str(deployment.get("tree", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(
        r"[0-9a-f]{40}", tree
    ):
        raise EntrypointError("install receipt deployment identity is not exact")
    if config.get("deployment_commit") != commit or config.get("deployment_tree") != tree:
        raise EntrypointError("enabled config deployment identity differs")
    if _git(repo, "rev-parse", "HEAD") != commit:
        raise EntrypointError("deployment HEAD differs from reviewed commit")
    if _git(repo, "rev-parse", "HEAD^{tree}") != tree:
        raise EntrypointError("deployment tree differs from reviewed tree")
    status_lines = {
        line for line in _git(
            repo, "status", "--porcelain=v1", "--untracked-files=all"
        ).splitlines() if line
    }
    allowed_runtime_evidence = {
        "?? .ai/ORCHESTRATOR_STOP",
        "?? output/control-plane/collaboration-goal/writer.lock",
    }
    if status_lines - allowed_runtime_evidence:
        raise EntrypointError("deployment repository must remain clean")
    if _git(repo, "branch", "--show-current"):
        raise EntrypointError("deployment repository must remain detached")
    entrypoint = repo / "scripts/collaboration_goal_entrypoint.py"
    dispatcher = repo / "scripts/collaboration_goal_dispatch.py"
    if Path(str(receipt.get("entrypoint", ""))).resolve() != entrypoint:
        raise EntrypointError("install receipt entrypoint path differs")
    if _inside(repo, str(config.get("dispatcher", "")), "dispatcher") != dispatcher:
        raise EntrypointError("enabled dispatcher path differs from reviewed path")
    for name, path in (("entrypoint", entrypoint), ("dispatcher", dispatcher)):
        if not path.is_file() or path.is_symlink():
            raise EntrypointError(f"reviewed {name} is unavailable")
        if _sha256(path) != receipt.get(f"{name}_sha256"):
            raise EntrypointError(f"reviewed {name} bytes drifted")
    plist_path = Path(str(receipt.get("plist_path", "")))
    if not plist_path.is_file() or plist_path.is_symlink():
        raise EntrypointError("LaunchAgent is unavailable")
    if Path(str(receipt.get("config_path", ""))) != config_path:
        raise EntrypointError("install receipt config path differs")
    exact = {
        "status": ENABLED_STATUS,
        "engineering_goal_id": ENGINEERING_GOAL_ID,
        "install_receipt": str(receipt_path),
        "install_receipt_sha256": _sha256(receipt_path),
        "enabled_config_sha256": _sha256(config_path),
        "enabled_plist_sha256": _sha256(plist_path),
        "deployment": deployment,
        "entrypoint_sha256": receipt.get("entrypoint_sha256"),
        "dispatcher_sha256": receipt.get("dispatcher_sha256"),
        "product_goal": config.get("product_goal"),
        "activation_authority": config.get("activation_authority"),
    }
    for field, expected in exact.items():
        if activation.get(field) != expected:
            raise EntrypointError(f"activation record mismatch for {field}")
    authority = activation.get("activation_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("status") != "APPROVED"
        or isinstance(authority.get("authorization_comment_id"), bool)
        or not isinstance(authority.get("authorization_comment_id"), int)
        or not re.fullmatch(r"[0-9a-f]{64}", str(authority.get("goal_spec_sha256", "")))
    ):
        raise EntrypointError("activation authority receipt is not exact")
    if Path(str(receipt.get("python", ""))).resolve() != Path(sys.executable).resolve():
        raise EntrypointError("entrypoint Python differs from the install receipt")
    _require_no_unexpected_model_processes(command_runner=command_runner)
    _require_no_competing_writer(repo)
    _require_o2_unloaded(command_runner=command_runner)
    return repo, dispatcher


def run_once(
    config_path: Path,
    *,
    now: str | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    config = _load_config(config_path)
    status = str(config["status"])
    base = {
        "schema_version": RESULT_SCHEMA,
        "engineering_goal_id": config.get("engineering_goal_id"),
        "entrypoint_status": status,
        "model_launch_started": False,
        "legacy_o2_runner_used": False,
    }
    if status in DISABLED_STATUSES:
        return {**base, "status": "STOPPED", "reason": "entrypoint is disabled"}

    repo = Path(str(config.get("deployment_repository", ""))).resolve()
    if not repo.is_dir() or repo.is_symlink():
        raise EntrypointError("deployment repository is absent or is a symlink")
    marker = _inside(repo, str(config.get("stop_marker", "")), "Stop Marker")
    if marker.exists():
        return {**base, "status": "STOPPED", "reason": "Stop Marker is latched"}

    repo, dispatcher = _verify_enabled_identity(
        config_path, config, command_runner=command_runner,
    )

    product_goal = config.get("product_goal")
    if not isinstance(product_goal, dict):
        raise EntrypointError("enabled entrypoint lacks an exact Product Goal binding")
    required = {"spec", "state", "ledger"}
    if set(product_goal) != required:
        raise EntrypointError("enabled Product Goal binding fields differ")
    command = [
        sys.executable,
        str(dispatcher),
        "--repo",
        str(repo),
        "--spec",
        str(_inside(repo, str(product_goal["spec"]), "Product Goal spec")),
        "--state",
        str(_inside(repo, str(product_goal["state"]), "Product Goal state")),
        "--ledger",
        str(_inside(repo, str(product_goal["ledger"]), "Product Goal ledger")),
        "--stop-marker",
        str(marker),
    ]
    if now is not None:
        command.extend(["--now", now])
    completed = command_runner(
        command, cwd=repo, capture_output=True, text=True, check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EntrypointError("dispatcher result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise EntrypointError("dispatcher result is not a JSON object")
    return {
        **base,
        "status": result.get("status", "BLOCKED"),
        "dispatcher_exit_code": completed.returncode,
        "dispatcher_result": result,
        "model_launch_started": bool(
            result.get("safety", {}).get("model_launch_started", False)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--now")
    args = parser.parse_args()
    try:
        result = run_once(args.config, now=args.now)
    except (EntrypointError, OSError, ValueError) as exc:
        result = {
            "schema_version": RESULT_SCHEMA,
            "status": "BLOCKED",
            "error": str(exc),
            "model_launch_started": False,
            "legacy_o2_runner_used": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] in {"STOPPED", "DISPATCHED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
