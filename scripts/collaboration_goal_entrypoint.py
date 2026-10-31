#!/usr/bin/env python3
"""Fail-closed launcher for the Issue #47 collaboration Goal dispatcher.

The installed configuration is deliberately disabled.  A later, separately
authorized Product Goal can replace it with an exact enabled configuration;
until then this entrypoint never reads GitHub and never starts a worker.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


CONFIG_SCHEMA = "kgnote.collaboration-goal-entrypoint-config.v1"
RESULT_SCHEMA = "kgnote.collaboration-goal-entrypoint-result.v1"
ENABLED_STATUS = "ENABLED_FOR_EXACT_PRODUCT_GOAL"
DISABLED_STATUSES = {"DISABLED", "ROLLED_BACK"}


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

    product_goal = config.get("product_goal")
    if not isinstance(product_goal, dict):
        raise EntrypointError("enabled entrypoint lacks an exact Product Goal binding")
    required = {"spec", "state", "ledger"}
    if set(product_goal) != required:
        raise EntrypointError("enabled Product Goal binding fields differ")
    dispatcher = _inside(
        repo,
        str(config.get("dispatcher", "scripts/collaboration_goal_dispatch.py")),
        "dispatcher",
    )
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
