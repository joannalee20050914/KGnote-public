#!/usr/bin/env python3
"""Install, attest, or roll back the unique Issue #47 LaunchAgent.

Installation writes one disabled-by-default LaunchAgent and never bootstraps or
enables it.  Rollback latches the Stop Marker before unloading/removing only
the exact new entrypoint files.  The legacy O2 LaunchAgent is read-only and
must remain unloaded throughout.
"""
from __future__ import annotations

import argparse
import fcntl
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
ACTIVATION_SCHEMA = "kgnote.collaboration-goal-entrypoint-activation.v1"
ROLLBACK_SCHEMA = "kgnote.collaboration-goal-entrypoint-rollback.v1"
ENGINEERING_GOAL_ID = "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION"
PRODUCT_ENABLED_STATUS = "ENABLED_FOR_EXACT_PRODUCT_GOAL"
ENGINEERING_ENABLED_STATUS = "ENABLED_FOR_EXACT_ENGINEERING_GOAL_WAKEUP"
ENABLED_STATUSES = {PRODUCT_ENABLED_STATUS, ENGINEERING_ENABLED_STATUS}


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


def _latch_stop_marker(path: Path, message: bytes) -> bool:
    preexisting = path.exists() or path.is_symlink()
    if preexisting:
        if path.is_symlink() or not path.is_file():
            raise EntrypointInstallError("existing Stop Marker is not a regular file")
    else:
        _atomic_bytes(path, message, mode=0o600)
    return preexisting


def _runtime_relative(repo: Path, raw: Any, label: str) -> Path:
    value = str(raw)
    if not value or Path(value).is_absolute():
        raise EntrypointInstallError(f"{label} must be a runtime-relative path")
    path = (repo / value).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise EntrypointInstallError(f"{label} leaves the engineering runtime") from exc
    return path


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


def _require_no_unexpected_model_processes(
    *, command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    completed = command_runner(
        ["/bin/ps", "-axo", "pid=,command="],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise EntrypointInstallError("cannot prove the model-process lane is idle")
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
        raise EntrypointInstallError(
            "unexpected model process is active: " + ", ".join(unexpected)
        )


def _require_no_competing_writer(repo: Path) -> None:
    lock_path = repo / "output/control-plane/collaboration-goal/writer.lock"
    if not lock_path.exists() and not lock_path.is_symlink():
        return
    if lock_path.is_symlink() or not lock_path.is_file():
        raise EntrypointInstallError("collaboration Goal writer lock is not a regular file")
    with lock_path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EntrypointInstallError(
                "another collaboration Goal writer is active"
            ) from exc
        finally:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EntrypointInstallError(f"{label} is unavailable")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EntrypointInstallError(f"{label} root is not an object")
    return value


def _verify_deployment_receipt(receipt: dict[str, Any]) -> tuple[Path, dict[str, str]]:
    repo = Path(str(receipt.get("deployment_repository", ""))).resolve()
    deployment = receipt.get("deployment")
    if not isinstance(deployment, dict):
        raise EntrypointInstallError("install receipt deployment identity is missing")
    identity = _deployment_identity(repo, str(deployment.get("commit", "")))
    if identity != deployment:
        raise EntrypointInstallError("deployment tree differs from the install receipt")
    expected_paths = {
        "entrypoint": repo / "scripts/collaboration_goal_entrypoint.py",
        "dispatcher": repo / "scripts/collaboration_goal_dispatch.py",
        "engineering_wakeup": repo / "scripts/issue47_engineering_wakeup.py",
    }
    for name, path in expected_paths.items():
        if Path(str(receipt.get(name, ""))).resolve() != path:
            raise EntrypointInstallError(f"install receipt {name} path differs")
    for name, path in expected_paths.items():
        if not path.is_file() or path.is_symlink():
            raise EntrypointInstallError(f"reviewed {name} is unavailable")
        if _sha256(path) != receipt.get(f"{name}_sha256"):
            raise EntrypointInstallError(f"reviewed {name} bytes drifted")
    python = Path(str(receipt.get("python", "")))
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise EntrypointInstallError("entrypoint Python no longer matches an executable")
    return repo, identity


def _verify_activation(
    *, receipt_path: Path, receipt: dict[str, Any], config_path: Path,
    config: dict[str, Any], plist_path: Path, plist: dict[str, Any],
) -> dict[str, Any]:
    activation_path = Path(str(config.get("activation_record", "")))
    expected_activation_path = Path(str(receipt.get("activation_record_path", "")))
    if activation_path != expected_activation_path:
        raise EntrypointInstallError("activation record path differs from install receipt")
    activation = _load_json_object(activation_path, "activation record")
    exact = {
        "schema_version": ACTIVATION_SCHEMA,
        "status": config.get("status"),
        "engineering_goal_id": ENGINEERING_GOAL_ID,
        "install_receipt": str(receipt_path),
        "install_receipt_sha256": _sha256(receipt_path),
        "enabled_config_sha256": _sha256(config_path),
        "enabled_plist_sha256": _sha256(plist_path),
        "deployment": receipt.get("deployment"),
        "entrypoint_sha256": receipt.get("entrypoint_sha256"),
        "dispatcher_sha256": receipt.get("dispatcher_sha256"),
        "engineering_wakeup_sha256": receipt.get("engineering_wakeup_sha256"),
        "product_goal": config.get("product_goal"),
        "engineering_goal": config.get("engineering_goal"),
        "activation_authority": config.get("activation_authority"),
    }
    for field, expected in exact.items():
        if activation.get(field) != expected:
            raise EntrypointInstallError(f"activation record mismatch for {field}")
    if config.get("install_receipt") != str(receipt_path):
        raise EntrypointInstallError("enabled config install receipt path differs")
    authority = activation.get("activation_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("status") != "APPROVED"
        or isinstance(authority.get("authorization_comment_id"), bool)
        or not isinstance(authority.get("authorization_comment_id"), int)
        or not re.fullmatch(r"[0-9a-f]{64}", str(authority.get("goal_spec_sha256", "")))
    ):
        raise EntrypointInstallError("activation authority receipt is not exact")
    if config.get("status") == PRODUCT_ENABLED_STATUS:
        if not isinstance(config.get("product_goal"), dict) or config.get("engineering_goal") is not None:
            raise EntrypointInstallError("Product Goal activation bindings differ")
    elif config.get("status") == ENGINEERING_ENABLED_STATUS:
        if config.get("product_goal") is not None or not isinstance(config.get("engineering_goal"), dict):
            raise EntrypointInstallError("engineering Goal activation bindings differ")
        if authority.get("authorization_comment_id") != 6538300483:
            raise EntrypointInstallError("engineering wakeup authority comment differs from v4")
        if authority.get("goal_spec_sha256") != "0507d2dbc5c9780afbe3e67a3c8ca66f8fb1b93eff9507c86299baac0141ad5d":
            raise EntrypointInstallError("engineering wakeup Goal digest differs from v4")
    else:
        raise EntrypointInstallError("activation status is invalid")
    if plist.get("Disabled") is not False:
        raise EntrypointInstallError("enabled activation still has a disabled LaunchAgent")
    return activation


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
    engineering_wakeup = repo / "scripts/issue47_engineering_wakeup.py"
    if any(
        not path.is_file() or path.is_symlink()
        for path in (entrypoint, dispatcher, engineering_wakeup)
    ):
        raise EntrypointInstallError("reviewed entrypoint, dispatcher, or engineering wakeup is unavailable")
    _require_no_unexpected_model_processes(command_runner=command_runner)
    _require_no_competing_writer(repo)
    _require_o2_unloaded(command_runner=command_runner)
    if _launchctl_loaded(LABEL, command_runner=command_runner):
        raise EntrypointInstallError("new collaboration Goal entrypoint is already loaded")

    launch_agents = launch_agents.resolve()
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{LABEL}.plist"
    activation_path = config_path.with_name("activation.json")
    for target in (plist_path, config_path, receipt_path, activation_path):
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
        "engineering_wakeup": "scripts/issue47_engineering_wakeup.py",
        "stop_marker": ".ai/ORCHESTRATOR_STOP",
        "install_receipt": str(receipt_path),
        "activation_record": str(activation_path),
        "product_goal": None,
        "engineering_goal": None,
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
        "dispatcher": str(dispatcher),
        "engineering_wakeup": str(engineering_wakeup),
        "entrypoint_sha256": _sha256(entrypoint),
        "dispatcher_sha256": _sha256(dispatcher),
        "engineering_wakeup_sha256": _sha256(engineering_wakeup),
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "plist_path": str(plist_path),
        "plist_sha256": _sha256(plist_path),
        "receipt_path": str(receipt_path),
        "activation_record_path": str(activation_path),
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
    receipt = _load_json_object(receipt_path, "entrypoint install receipt")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise EntrypointInstallError("entrypoint install receipt schema differs")
    config_path = Path(str(receipt["config_path"]))
    plist_path = Path(str(receipt["plist_path"]))
    config = _load_json_object(config_path, "entrypoint config")
    plist = plistlib.loads(plist_path.read_bytes())
    repo, identity = _verify_deployment_receipt(receipt)
    _require_no_unexpected_model_processes(command_runner=command_runner)
    _require_no_competing_writer(repo)
    _require_o2_unloaded(command_runner=command_runner)
    new_loaded = _launchctl_loaded(LABEL, command_runner=command_runner)
    if config.get("status") == "DISABLED":
        if _sha256(config_path) != receipt.get("config_sha256"):
            raise EntrypointInstallError("disabled entrypoint config bytes drifted")
        if _sha256(plist_path) != receipt.get("plist_sha256"):
            raise EntrypointInstallError("disabled LaunchAgent bytes drifted")
        if plist.get("Disabled") is not True:
            raise EntrypointInstallError("entrypoint is not disabled by default")
        if Path(str(receipt.get("activation_record_path", ""))).exists():
            raise EntrypointInstallError("disabled install has an unexpected activation record")
        if new_loaded:
            raise EntrypointInstallError("disabled entrypoint is unexpectedly loaded")
        status = "STOPPED"
    elif config.get("status") in ENABLED_STATUSES:
        _verify_activation(
            receipt_path=receipt_path, receipt=receipt, config_path=config_path,
            config=config, plist_path=plist_path, plist=plist,
        )
        status = "RUNNING" if new_loaded else "ENABLED_NOT_LOADED"
    else:
        raise EntrypointInstallError("entrypoint config status is invalid")
    return {
        "schema_version": RECEIPT_SCHEMA,
        "status": status,
        "label": LABEL,
        "loaded": new_loaded,
        "legacy_o2_runner_loaded": False,
        "deployment": identity,
    }


def rollback(
    receipt_path: Path,
    *,
    rollback_receipt_path: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise EntrypointInstallError("entrypoint install receipt is unavailable")
    receipt = _load_json_object(receipt_path, "entrypoint install receipt")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise EntrypointInstallError("entrypoint install receipt schema differs")
    repo = Path(str(receipt["deployment_repository"])).resolve()
    if repo.is_symlink() or not repo.is_dir():
        raise EntrypointInstallError("deployment repository is absent or is a symlink")
    stop_marker = repo / ".ai/ORCHESTRATOR_STOP"
    marker_preexisting = _latch_stop_marker(
        stop_marker, b"Issue #47 collaboration Goal rollback; do not auto-resume.\n"
    )
    _require_o2_unloaded(command_runner=command_runner)
    config_path = Path(str(receipt["config_path"]))
    plist_path = Path(str(receipt["plist_path"]))
    config = _load_json_object(config_path, "entrypoint config")
    plist = plistlib.loads(plist_path.read_bytes())
    _verify_deployment_receipt(receipt)
    activation_path = Path(str(receipt.get("activation_record_path", "")))
    if config.get("status") == "DISABLED":
        if _sha256(config_path) != receipt.get("config_sha256"):
            raise EntrypointInstallError("refusing rollback after config drift")
        if _sha256(plist_path) != receipt.get("plist_sha256"):
            raise EntrypointInstallError("refusing rollback after LaunchAgent drift")
        if activation_path.exists() or activation_path.is_symlink():
            raise EntrypointInstallError("disabled rollback found an activation record")
    elif config.get("status") in ENABLED_STATUSES:
        _verify_activation(
            receipt_path=receipt_path, receipt=receipt, config_path=config_path,
            config=config, plist_path=plist_path, plist=plist,
        )
    else:
        raise EntrypointInstallError("refusing rollback for an invalid config status")

    runtime_stop_marker: Path | None = None
    runtime_marker_preexisting: bool | None = None
    if config.get("status") == ENGINEERING_ENABLED_STATUS:
        binding = config.get("engineering_goal")
        if not isinstance(binding, dict):
            raise EntrypointInstallError("engineering Goal binding is unavailable")
        runtime = Path(str(binding.get("runtime_repository", "")))
        if not runtime.is_absolute() or runtime.is_symlink() or not runtime.is_dir():
            raise EntrypointInstallError("engineering runtime is unavailable")
        runtime_stop_marker = _runtime_relative(
            runtime.resolve(), binding.get("stop_marker"), "engineering Stop Marker"
        )
        runtime_marker_preexisting = _latch_stop_marker(
            runtime_stop_marker,
            b"Issue #47 engineering wakeup rollback; do not auto-resume.\n",
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
    removed = [str(plist_path), str(config_path)]
    plist_path.unlink()
    config_path.unlink()
    if activation_path.exists():
        if activation_path.is_symlink() or not activation_path.is_file():
            raise EntrypointInstallError("activation record is not a regular file")
        activation_path.unlink()
        removed.append(str(activation_path))
    result = {
        "schema_version": ROLLBACK_SCHEMA,
        "status": "STOPPED",
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        "label": LABEL,
        "was_loaded": was_loaded,
        "entrypoint_files_removed": removed,
        "stop_marker": str(stop_marker),
        "stop_marker_preexisting": marker_preexisting,
        "engineering_runtime_stop_marker": (
            str(runtime_stop_marker) if runtime_stop_marker is not None else None
        ),
        "engineering_runtime_stop_marker_preexisting": runtime_marker_preexisting,
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
