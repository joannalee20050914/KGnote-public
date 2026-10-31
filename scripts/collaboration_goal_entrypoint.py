#!/usr/bin/env python3
"""Fail-closed launcher for the Issue #47 collaboration Goal dispatcher.

The installed configuration is deliberately disabled.  It may later be
activated either for one exact Product Goal or for the exact Issue #47
engineering continuation.  The engineering mode always runs the reviewed
no-model admission gate before it invokes the continuation command.
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
import tempfile
from pathlib import Path
from typing import Any, Callable


CONFIG_SCHEMA = "kgnote.collaboration-goal-entrypoint-config.v1"
RECEIPT_SCHEMA = "kgnote.collaboration-goal-entrypoint-install.v1"
ACTIVATION_SCHEMA = "kgnote.collaboration-goal-entrypoint-activation.v1"
RESULT_SCHEMA = "kgnote.collaboration-goal-entrypoint-result.v1"
ENGINEERING_WAKEUP_STATE_SCHEMA = "kgnote.issue47-engineering-wakeup-state.v1"
V4_OWNER_COMMENT_ID = 6538300483
V4_GOAL_SPEC_SHA256 = "0507d2dbc5c9780afbe3e67a3c8ca66f8fb1b93eff9507c86299baac0141ad5d"
ENABLED_STATUS = "ENABLED_FOR_EXACT_PRODUCT_GOAL"
ENGINEERING_ENABLED_STATUS = "ENABLED_FOR_EXACT_ENGINEERING_GOAL_WAKEUP"
ENABLED_STATUSES = {ENABLED_STATUS, ENGINEERING_ENABLED_STATUS}
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
    if value.get("status") not in DISABLED_STATUSES | ENABLED_STATUSES:
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
) -> tuple[Path, Path, Path]:
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
    wakeup = repo / "scripts/issue47_engineering_wakeup.py"
    if Path(str(receipt.get("entrypoint", ""))).resolve() != entrypoint:
        raise EntrypointError("install receipt entrypoint path differs")
    if Path(str(receipt.get("engineering_wakeup", ""))).resolve() != wakeup:
        raise EntrypointError("install receipt engineering wakeup path differs")
    if _inside(repo, str(config.get("dispatcher", "")), "dispatcher") != dispatcher:
        raise EntrypointError("enabled dispatcher path differs from reviewed path")
    if _inside(repo, str(config.get("engineering_wakeup", "")), "engineering wakeup") != wakeup:
        raise EntrypointError("enabled engineering wakeup path differs from reviewed path")
    for name, path in (
        ("entrypoint", entrypoint), ("dispatcher", dispatcher), ("engineering_wakeup", wakeup),
    ):
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
        "status": config.get("status"),
        "engineering_goal_id": ENGINEERING_GOAL_ID,
        "install_receipt": str(receipt_path),
        "install_receipt_sha256": _sha256(receipt_path),
        "enabled_config_sha256": _sha256(config_path),
        "enabled_plist_sha256": _sha256(plist_path),
        "deployment": deployment,
        "entrypoint_sha256": receipt.get("entrypoint_sha256"),
        "dispatcher_sha256": receipt.get("dispatcher_sha256"),
        "engineering_wakeup_sha256": receipt.get("engineering_wakeup_sha256"),
        "product_goal": config.get("product_goal"),
        "engineering_goal": config.get("engineering_goal"),
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
    if config.get("status") == ENGINEERING_ENABLED_STATUS and (
        authority.get("authorization_comment_id") != V4_OWNER_COMMENT_ID
        or authority.get("goal_spec_sha256") != V4_GOAL_SPEC_SHA256
    ):
        raise EntrypointError("engineering wakeup activation is not bound to exact v4 authority")
    if Path(str(receipt.get("python", ""))).resolve() != Path(sys.executable).resolve():
        raise EntrypointError("entrypoint Python differs from the install receipt")
    _require_no_unexpected_model_processes(command_runner=command_runner)
    _require_no_competing_writer(repo)
    _require_o2_unloaded(command_runner=command_runner)
    return repo, dispatcher, wakeup


def _absolute_regular_directory(raw: Any, label: str) -> Path:
    path = Path(str(raw))
    if not path.is_absolute():
        raise EntrypointError(f"{label} must be absolute")
    if path.is_symlink():
        raise EntrypointError(f"{label} is absent or is a symlink")
    resolved = path.resolve()
    if not resolved.is_dir():
        raise EntrypointError(f"{label} is absent or is a symlink")
    return resolved


def _runtime_path(repo: Path, raw: Any, label: str) -> Path:
    value = str(raw)
    if not value or Path(value).is_absolute():
        raise EntrypointError(f"{label} must be a non-empty runtime-relative path")
    return _inside(repo, value, label)


def _json_result(
    completed: subprocess.CompletedProcess[str], label: str,
) -> dict[str, Any]:
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EntrypointError(f"{label} result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise EntrypointError(f"{label} result is not a JSON object")
    return result


def _transition_wakeup_state(
    *, state_path: Path, writer_lock: Path, dispatch_key: str,
    status: str, observed_at: str | None, continuation_exit_code: int | None = None,
) -> None:
    if status not in {"RUNNING", "COMPLETED", "FAILED"}:
        raise EntrypointError("engineering wakeup transition status is invalid")
    writer_lock.parent.mkdir(parents=True, exist_ok=True)
    if writer_lock.is_symlink() or (writer_lock.exists() and not writer_lock.is_file()):
        raise EntrypointError("engineering writer lock is not a regular file")
    with writer_lock.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EntrypointError("another Issue #47 writer became active") from exc
        state = _load_object(state_path, "engineering wakeup state")
        if (
            state.get("schema_version") != ENGINEERING_WAKEUP_STATE_SCHEMA
            or state.get("dispatch_key") != dispatch_key
            or state.get("status") not in {"RESERVED", "RUNNING"}
        ):
            raise EntrypointError("engineering wakeup reservation identity differs")
        state["status"] = status
        state["model_launch_started"] = True
        state[f"{status.lower()}_at"] = observed_at
        if continuation_exit_code is not None:
            state["continuation_exit_code"] = continuation_exit_code
        state_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{state_path.name}.", dir=state_path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream, indent=2, sort_keys=True, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _run_engineering_wakeup(
    *, deployment_repo: Path, wakeup: Path, config: dict[str, Any],
    now: str | None, base: dict[str, Any],
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    binding = config.get("engineering_goal")
    if not isinstance(binding, dict):
        raise EntrypointError("engineering wakeup lacks an exact engineering Goal binding")
    required = {
        "runtime_repository", "goal_spec", "heartbeat", "wakeup_state",
        "writer_lock", "stop_marker",
    }
    if set(binding) != required:
        raise EntrypointError("engineering Goal binding fields differ")
    if config.get("product_goal") is not None:
        raise EntrypointError("engineering wakeup cannot contain a Product Goal binding")
    runtime = _absolute_regular_directory(binding["runtime_repository"], "engineering runtime")
    spec = _runtime_path(runtime, binding["goal_spec"], "engineering Goal spec")
    state = _runtime_path(runtime, binding["wakeup_state"], "engineering wakeup state")
    writer_lock = _runtime_path(runtime, binding["writer_lock"], "engineering writer lock")
    stop_marker = _runtime_path(runtime, binding["stop_marker"], "engineering Stop Marker")
    heartbeat = Path(str(binding["heartbeat"]))
    if not heartbeat.is_absolute():
        raise EntrypointError("Codex heartbeat path must be absolute")
    heartbeat = heartbeat.resolve()
    if not heartbeat.is_file() or heartbeat.is_symlink():
        raise EntrypointError("Codex heartbeat definition is unavailable")
    if stop_marker.exists() or stop_marker.is_symlink():
        return {**base, "status": "STOPPED", "reason": "engineering Stop Marker is latched"}

    gate_command = [
        sys.executable, str(wakeup), "--repo", str(runtime), "--spec", str(spec),
        "--heartbeat", str(heartbeat), "--state", str(state),
        "--writer-lock", str(writer_lock), "--stop-marker", str(stop_marker), "--reserve",
    ]
    if now is not None:
        gate_command.extend(["--now", now])
    gate_completed = command_runner(
        gate_command, cwd=deployment_repo, capture_output=True, text=True, check=False,
    )
    gate = _json_result(gate_completed, "engineering admission gate")
    gate_safety = gate.get("safety")
    if not isinstance(gate_safety, dict) or gate_safety.get("model_launch_started") is not False:
        raise EntrypointError("engineering admission gate did not prove a no-model decision")
    if gate.get("status") != "RESERVED":
        return {
            **base,
            "status": gate.get("status", "BLOCKED"),
            "admission_gate_exit_code": gate_completed.returncode,
            "admission_gate_result": gate,
        }
    if gate_completed.returncode:
        raise EntrypointError("engineering admission reservation returned a failing exit code")
    if gate.get("action") not in {"DISPATCH_IMPLEMENTATION", "DISPATCH_REVIEW"}:
        raise EntrypointError("engineering admission action is not supported")
    dispatch_key = str(gate.get("dispatch_key", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", dispatch_key):
        raise EntrypointError("engineering admission dispatch key is not exact")

    orchestrator = runtime / "scripts/codex_orchestrator.py"
    if not orchestrator.is_file() or orchestrator.is_symlink():
        raise EntrypointError("engineering continuation orchestrator is unavailable")
    continuation = [
        sys.executable, str(orchestrator), "--repo", str(runtime),
        "resume", "--max-steps", "1",
    ]
    _transition_wakeup_state(
        state_path=state, writer_lock=writer_lock, dispatch_key=dispatch_key,
        status="RUNNING", observed_at=now,
    )
    completed = command_runner(
        continuation, cwd=runtime, capture_output=True, text=True, check=False,
    )
    result = _json_result(completed, "engineering continuation")
    _transition_wakeup_state(
        state_path=state, writer_lock=writer_lock, dispatch_key=dispatch_key,
        status="COMPLETED" if completed.returncode == 0 else "FAILED",
        observed_at=now, continuation_exit_code=completed.returncode,
    )
    return {
        **base,
        "status": result.get("state", result.get("status", "BLOCKED")),
        "admission_gate_exit_code": gate_completed.returncode,
        "admission_gate_result": gate,
        "continuation_exit_code": completed.returncode,
        "continuation_result": result,
        # A reservation followed by invocation is charged conservatively even
        # if the provider fails before returning a durable launch receipt.
        "model_launch_started": True,
    }


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
    if status == ENGINEERING_ENABLED_STATUS:
        binding = config.get("engineering_goal")
        if not isinstance(binding, dict):
            raise EntrypointError("engineering wakeup lacks an exact engineering Goal binding")
        runtime = _absolute_regular_directory(
            binding.get("runtime_repository"), "engineering runtime"
        )
        runtime_marker = _runtime_path(
            runtime, binding.get("stop_marker"), "engineering Stop Marker"
        )
        if runtime_marker.exists() or runtime_marker.is_symlink():
            return {
                **base,
                "status": "STOPPED",
                "reason": "engineering Stop Marker is latched",
            }

    repo, dispatcher, wakeup = _verify_enabled_identity(
        config_path, config, command_runner=command_runner,
    )

    if status == ENGINEERING_ENABLED_STATUS:
        return _run_engineering_wakeup(
            deployment_repo=repo, wakeup=wakeup, config=config, now=now,
            base=base, command_runner=command_runner,
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
    result = _json_result(completed, "dispatcher")
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
    if result.get("continuation_exit_code") == 0:
        return 0
    normal_no_model_states = {
        "STOPPED", "DISPATCHED", "WAITING_WORK_WINDOW", "WAITING_QUOTA",
        "WAITING_PROVIDER_BACKOFF", "WAITING_DUPLICATE", "WAITING_ACTIVE_RESERVATION",
    }
    return 0 if result["status"] in normal_no_model_states else 2


if __name__ == "__main__":
    raise SystemExit(main())
