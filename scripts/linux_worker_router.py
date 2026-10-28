#!/usr/bin/env python3
"""Mac Runner adapter for one Linux cgroup-confined KGnote worker event."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from codex_jsonl_evidence import parse_codex_jsonl, provider_failure_from_output
from product_goal_worker_identity import (
    PRODUCT_IDENTITY_SCHEMA,
    ProductGoalIdentityError,
    validate_product_goal_identity,
    validate_product_goal_runtime_context,
)


GUEST_HOST = "kgnote-ubuntu"
GUEST_GUARD = "/home/kgnote/.local/share/kgnote/runtime/linux_worker_guard.py"
GUEST_LANDLOCK = "/home/kgnote/.local/share/kgnote/runtime/linux_landlock_exec.py"
GUEST_BOOTSTRAP = "/home/kgnote/.local/share/kgnote/runtime/linux_worker_bootstrap.py"
EVENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
STAGES = {"codex", "claude", "publisher", "push", "ingestion"}
WORKTREE_ROOT = Path("/home/kgnote/.local/share/kgnote")
EVIDENCE_PREFIX = "KGNOTE_EXECUTION_EVIDENCE="
ORDER_SCHEMA = "kgnote.linux-worker-order.v1"


class RoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerOrder:
    event_id: str
    stage: str
    working_directory: Path
    handoff_directory: Path | None
    command: tuple[str, ...]
    checkpoint_path: Path
    memory_max: str
    tasks_max: int
    timeout_seconds: int
    lease_timeout_seconds: int
    deadline_at: datetime | None
    bootstrap_working_directory: bool
    bootstrap_identity: dict[str, Any] | None
    execution_context: dict[str, Any] | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WorkerOrder":
        if raw.get("schema_version") != ORDER_SCHEMA:
            raise RoutingError("worker order schema_version is missing or unsupported")
        try:
            order = cls(
                event_id=str(raw["event_id"]),
                stage=str(raw["stage"]),
                working_directory=Path(raw["working_directory"]),
                handoff_directory=Path(raw["handoff_directory"]) if raw.get("handoff_directory") else None,
                command=tuple(str(item) for item in raw["command"]),
                checkpoint_path=Path(raw["checkpoint_path"]),
                memory_max=str(raw.get("memory_max", "1G")),
                tasks_max=int(raw.get("tasks_max", 128)),
                timeout_seconds=int(raw.get("timeout_seconds", 900)),
                lease_timeout_seconds=int(raw.get("lease_timeout_seconds", 8)),
                deadline_at=(
                    datetime.fromisoformat(str(raw["deadline_at"]))
                    if raw.get("deadline_at") else None
                ),
                bootstrap_working_directory=raw.get("bootstrap_working_directory", False),
                bootstrap_identity=raw.get("bootstrap_identity"),
                execution_context=raw.get("execution_context"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RoutingError(f"invalid worker order: {exc}") from exc
        order.validate()
        return order

    def validate(self) -> None:
        if not EVENT_RE.fullmatch(self.event_id):
            raise RoutingError("event_id must be a bounded lowercase identifier")
        if self.stage not in STAGES:
            raise RoutingError("stage must select one credential-isolated worker profile")
        if not self.working_directory.is_absolute() or not self.working_directory.is_relative_to(WORKTREE_ROOT):
            raise RoutingError("working_directory must be inside the bounded Guest workspace root")
        if self.handoff_directory is not None:
            product_goal_handoff = (
                isinstance(self.bootstrap_identity, dict)
                and self.bootstrap_identity.get("schema_version") == PRODUCT_IDENTITY_SCHEMA
                and self.handoff_directory == WORKTREE_ROOT / "runtime-state/product-goal"
            )
            if self.stage not in {"claude", "ingestion"} and not product_goal_handoff:
                raise RoutingError("handoff_directory is allowed only for claude or ingestion")
            if not self.handoff_directory.is_absolute() or not self.handoff_directory.is_relative_to(WORKTREE_ROOT):
                raise RoutingError("handoff_directory must be inside the bounded Guest workspace root")
            if self.handoff_directory == self.working_directory:
                raise RoutingError("handoff_directory must be separate from the candidate worktree")
            if (
                isinstance(self.bootstrap_identity, dict)
                and self.bootstrap_identity.get("schema_version") == PRODUCT_IDENTITY_SCHEMA
                and not product_goal_handoff
            ):
                raise RoutingError("Product Goal handoff_directory differs from the exact durable root")
        if not self.command or not self.command[0].startswith(("/bin/", "/usr/bin/", "/home/kgnote/.local/")):
            raise RoutingError("command must use an approved absolute guest executable")
        if any("\x00" in item or "\n" in item for item in self.command):
            raise RoutingError("command contains unsafe control characters")
        if not re.fullmatch(r"(?:[1-9][0-9]{0,3})(?:M|G)", self.memory_max):
            raise RoutingError("memory_max must be an explicit M/G value")
        if not 4 <= self.tasks_max <= 512:
            raise RoutingError("tasks_max is outside the bounded range")
        if not 1 <= self.timeout_seconds <= 3600:
            raise RoutingError("timeout_seconds is outside the bounded range")
        if not 3 <= self.lease_timeout_seconds <= 60:
            raise RoutingError("lease_timeout_seconds is outside the bounded range")
        if self.deadline_at is not None:
            if self.deadline_at.tzinfo is None:
                raise RoutingError("deadline_at must include a timezone")
            if self.deadline_at.astimezone(ZoneInfo("Asia/Taipei")).strftime("%H:%M") != "18:00":
                raise RoutingError("deadline_at must be the Asia/Taipei 18:00 boundary")
        if not isinstance(self.bootstrap_working_directory, bool):
            raise RoutingError("bootstrap_working_directory must be boolean")
        if self.bootstrap_working_directory:
            legacy = (
                re.fullmatch(r"source-library-successor-codex-20261019(?:-cycle-(?:0[2-9]|1[0-2]))?", self.event_id)
                and self.stage == "codex"
                and self.working_directory == Path("/home/kgnote/.local/share/kgnote/source-library-successor-20261019")
                and self.bootstrap_identity is None
            )
            if not legacy:
                if self.bootstrap_identity is None:
                    raise RoutingError("working-directory bootstrap is not authorized for this order")
                validate_bootstrap_identity(
                    self.bootstrap_identity, event_id=self.event_id, stage=self.stage,
                    working_directory=self.working_directory,
                )
        if self.execution_context is not None and not isinstance(self.execution_context, dict):
            raise RoutingError("execution_context must be an object")
        if (
            isinstance(self.bootstrap_identity, dict)
            and self.bootstrap_identity.get("schema_version") == PRODUCT_IDENTITY_SCHEMA
        ):
            try:
                validate_product_goal_runtime_context(
                    self.execution_context, identity=self.bootstrap_identity,
                )
            except ProductGoalIdentityError as exc:
                raise RoutingError(str(exc)) from exc


def validate_bootstrap_identity(
    identity: object, *, event_id: str, stage: str, working_directory: Path,
) -> None:
    """Bind generic bootstrap to one owner-authorized Issue identity."""
    if isinstance(identity, dict) and identity.get("schema_version") == PRODUCT_IDENTITY_SCHEMA:
        try:
            validate_product_goal_identity(
                identity, event_id=event_id, stage=stage,
                working_directory=working_directory, worktree_root=WORKTREE_ROOT,
            )
        except ProductGoalIdentityError as exc:
            raise RoutingError(str(exc)) from exc
        return
    if not isinstance(identity, dict) or identity.get("schema_version") != "kgnote.authorized-work-identity.v1":
        raise RoutingError("generic bootstrap identity is missing or unsupported")
    repository = identity.get("repository")
    issue = identity.get("issue")
    goal_id = identity.get("goal_id")
    work_item_id = identity.get("work_item_id")
    branch = identity.get("branch")
    slug = identity.get("worktree_slug")
    authority_record = identity.get("authority_record")
    authority_sha256 = identity.get("authority_sha256")
    if repository != "joannalee20050914/KGnote-public":
        raise RoutingError("generic bootstrap repository is not authorized")
    if not isinstance(issue, int) or issue < 1:
        raise RoutingError("generic bootstrap issue is invalid")
    if not isinstance(goal_id, str) or not re.fullmatch(r"GOAL-KGNOTE-[A-Z0-9-]+", goal_id):
        raise RoutingError("generic bootstrap goal identity is invalid")
    if not isinstance(work_item_id, str) or not re.fullmatch(r"D2-T[0-9]{2}", work_item_id):
        raise RoutingError("generic bootstrap work-item identity is invalid")
    if not isinstance(branch, str) or not re.fullmatch(r"codex/[a-z0-9][a-z0-9-]{2,80}", branch):
        raise RoutingError("generic bootstrap branch is invalid")
    expected_slug = f"issue-{issue}-{work_item_id.lower()}"
    if slug != expected_slug:
        raise RoutingError("generic bootstrap worktree slug does not match Issue/work item")
    if authority_record != f"https://github.com/{repository}/issues/{issue}":
        raise RoutingError("generic bootstrap authority record is not the exact Issue")
    if not isinstance(authority_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", authority_sha256):
        raise RoutingError("generic bootstrap authority digest is invalid")
    if stage != "codex" or event_id != f"{expected_slug}-codex-20261019":
        raise RoutingError("generic bootstrap event or stage does not match authority")
    expected_directory = WORKTREE_ROOT / "work-items" / expected_slug
    if working_directory != expected_directory:
        raise RoutingError("generic bootstrap directory does not match authority")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_text(path: Path, value: str, limit: int = 65536) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value[-limit:])
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command_digest(order: WorkerOrder) -> str:
    value = {
        "event_id": order.event_id,
        "stage": order.stage,
        "working_directory": str(order.working_directory),
        "handoff_directory": str(order.handoff_directory) if order.handoff_directory else None,
        "command": order.command,
    }
    # Preserve command identities for already-issued orders. New evidence is
    # identity-bound only when the work order explicitly carries it.
    if order.execution_context is not None:
        value["execution_context"] = order.execution_context
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def execution_evidence(order: WorkerOrder, stdout: str, stderr: str) -> dict[str, Any] | None:
    evidence: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if line.startswith(EVIDENCE_PREFIX):
            try:
                candidate = json.loads(line[len(EVIDENCE_PREFIX):])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                evidence = candidate
    if order.stage == "claude":
        try:
            candidate = json.loads(stdout)
        except json.JSONDecodeError:
            candidate = None
        if isinstance(candidate, dict) and isinstance(candidate.get("execution_evidence"), dict):
            evidence = candidate["execution_evidence"]
    if evidence is None and isinstance(order.execution_context, dict):
        evidence = dict(order.execution_context)
    if evidence is not None and order.stage == "codex":
        summary = parse_codex_jsonl(stdout)
        provider_failure = provider_failure_from_output(stdout + "\n" + stderr)
        evidence = dict(evidence)
        evidence["token_usage"] = summary.get("usage")
        evidence["provider_failure"] = provider_failure
        evidence["codex_jsonl"] = {
            "event_count": summary["event_count"],
            "turn_completed": summary["turn_completed"],
        }
    return evidence


def sandbox_command(order: WorkerOrder) -> list[str]:
    command = [
        "/usr/bin/python3", GUEST_LANDLOCK,
        "--ro", "/usr", "--ro", "/etc", "--ro", "/proc", "--ro", "/sys",
        "--ro", "/run/systemd/resolve", "--ro", "/home/kgnote/.local",
        "--rw", "/dev", "--rw", "/tmp", "--rw", "/run/user/1002",
    ]
    if order.stage == "codex":
        command.extend(("--rw", "/home/kgnote/.codex", "--rw", str(order.working_directory)))
    elif order.stage == "claude":
        command.extend(("--rw", "/home/kgnote/.claude", "--ro", str(order.working_directory)))
    elif order.stage == "push":
        command.extend(("--rw", "/home/kgnote/.ssh", "--rw", str(order.working_directory)))
    elif order.stage in {"publisher", "ingestion"}:
        command.extend(("--rw", str(order.working_directory)))
    if order.handoff_directory is not None:
        command.extend(("--rw", str(order.handoff_directory)))
    return [*command, "--", "/usr/bin/env", "-C", str(order.working_directory), *order.command]


def remote_command(order: WorkerOrder) -> list[str]:
    lease = f"/run/user/1002/kgnote-{order.event_id}.lease"
    return [
        "systemd-run", "--user", "--wait", "--collect", "--pipe",
        f"--unit=kgnote-{order.event_id}", f"--property=MemoryMax={order.memory_max}",
        "--property=MemorySwapMax=0", f"--property=TasksMax={order.tasks_max}",
        "--property=KillMode=control-group", "--property=TimeoutStopSec=3s",
        "--property=NoNewPrivileges=yes", "--property=PrivateTmp=yes",
        "/usr/bin/python3", GUEST_GUARD, "--lease", lease,
        "--lease-timeout", str(order.lease_timeout_seconds), "--", *sandbox_command(order),
    ]


def bootstrap_command(order: WorkerOrder) -> list[str]:
    command = [
        "/usr/bin/python3", GUEST_BOOTSTRAP,
        "--event-id", order.event_id,
        "--stage", order.stage,
        "--working-directory", str(order.working_directory),
    ]
    if order.bootstrap_identity is not None:
        command.extend(("--identity-json", json.dumps(order.bootstrap_identity, sort_keys=True, separators=(",", ":"))))
    return command


def route(
    order: WorkerOrder,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    now: Callable[[], datetime] = lambda: datetime.now(ZoneInfo("Asia/Taipei")),
) -> dict[str, Any]:
    digest = command_digest(order)
    deadline_seconds: float | None = None
    if order.deadline_at is not None:
        deadline_seconds = (order.deadline_at - now()).total_seconds()
        if deadline_seconds <= 0:
            raise RoutingError("worker deadline is already closed")
    prior: dict[str, Any] = {}
    if order.checkpoint_path.exists():
        try:
            prior = json.loads(order.checkpoint_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RoutingError("existing routing checkpoint is unreadable") from exc
        if prior.get("event_id") == order.event_id and prior.get("command_digest") != digest:
            raise RoutingError("event_id was reused with different command bytes")
        if prior.get("event_id") == order.event_id and prior.get("status") == "COMPLETED":
            return {**prior, "status": "ALREADY_COMPLETED"}
    lease = f"/run/user/1002/kgnote-{order.event_id}.lease"
    ssh_base = ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes", GUEST_HOST]
    if prior.get("event_id") == order.event_id and prior.get("status") == "RUNNING":
        probe = run(
            [*ssh_base, shlex.join(["systemctl", "--user", "is-active", f"kgnote-{order.event_id}.service"])],
            text=True, capture_output=True, timeout=15, check=False,
        )
        if probe.returncode == 0:
            raise RoutingError("prior worker is still active; duplicate dispatch denied")
        interrupted = {
            **prior, "status": "FAILED_CLOSED", "reason": "controller_interrupted",
            "exit_code": None, "host_fallback_used": False,
        }
        _atomic_json(order.checkpoint_path, interrupted)
        return interrupted
    if order.bootstrap_working_directory:
        prepared = run(
            [*ssh_base, shlex.join(bootstrap_command(order))],
            text=True, capture_output=True, timeout=15, check=False,
        )
        try:
            bootstrap_receipt = json.loads(prepared.stdout) if prepared.stdout.strip() else None
        except json.JSONDecodeError:
            bootstrap_receipt = None
        product_codex = (
            order.stage == "codex"
            and isinstance(order.bootstrap_identity, dict)
            and order.bootstrap_identity.get("schema_version") == PRODUCT_IDENTITY_SCHEMA
        )
        bootstrap_admitted = (
            isinstance(bootstrap_receipt, dict)
            and bootstrap_receipt.get("status") == "READY"
            and (
                not product_codex
                or (bootstrap_receipt.get("development_environment") or {}).get("status")
                == "DEVELOPMENT_ENVIRONMENT_READY"
            )
        )
        if prepared.returncode or not bootstrap_admitted:
            blocked = {
                "schema_version": "kgnote.linux-worker-route.v1", "status": "BLOCKED",
                "reason": "bootstrap_failed" if prepared.returncode else "bootstrap_admission_failed",
                "failure_class": (
                    "WORKER_ENVIRONMENT_ADMISSION_FAILED"
                    if product_codex else "DETERMINISTIC_WORKER_FAILURE"
                ),
                "event_id": order.event_id,
                "command_digest": digest, "exit_code": prepared.returncode,
                "attempt_count": int(prior.get("attempt_count", 0)),
                "memory_max": order.memory_max, "tasks_max": order.tasks_max,
                "lease_timeout_seconds": order.lease_timeout_seconds,
                "bootstrap_stdout_sha256": hashlib.sha256(prepared.stdout.encode()).hexdigest(),
                "bootstrap_stderr_sha256": hashlib.sha256(prepared.stderr.encode()).hexdigest(),
                "host_fallback_used": False,
            }
            _atomic_json(order.checkpoint_path, blocked)
            return blocked
    touch_command = shlex.join(["/usr/bin/touch", lease])
    touch = run([*ssh_base, touch_command], text=True, capture_output=True, timeout=15, check=False)
    if touch.returncode:
        raise RoutingError("guest is unavailable; dispatch denied")
    _atomic_json(order.checkpoint_path, {
        "schema_version": "kgnote.linux-worker-route.v1", "status": "RUNNING",
        "reason": None, "event_id": order.event_id, "command_digest": digest,
        "exit_code": None, "memory_max": order.memory_max, "tasks_max": order.tasks_max,
        "lease_timeout_seconds": order.lease_timeout_seconds, "host_fallback_used": False,
    })
    process = popen([*ssh_base, shlex.join(remote_command(order))], text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
    stopped = threading.Event()

    def heartbeat() -> None:
        while not stopped.wait(2):
            result = run([*ssh_base, touch_command], text=True, capture_output=True,
                         timeout=10, check=False)
            if result.returncode:
                return

    thread = threading.Thread(target=heartbeat, name=f"lease-{order.event_id}", daemon=True)
    thread.start()
    effective_timeout = min(
        float(order.timeout_seconds),
        deadline_seconds if deadline_seconds is not None else float(order.timeout_seconds),
    )
    deadline_won = deadline_seconds is not None and deadline_seconds <= order.timeout_seconds
    try:
        stdout, stderr = process.communicate(timeout=effective_timeout)
    except subprocess.TimeoutExpired:
        # Stop refreshing the guest lease first. The guest guard sends SIGTERM to
        # the complete worker process group; systemd KillMode=control-group and
        # TimeoutStopSec provide the final cgroup-wide cleanup boundary.
        stopped.set(); thread.join(timeout=3)
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=order.lease_timeout_seconds + 5)
        except subprocess.TimeoutExpired:
            process.kill(); stdout, stderr = process.communicate()
        status = "DEADLINE_STOPPED" if deadline_won else "FAILED_CLOSED"
        reason = "work_window_deadline" if deadline_won else "host_timeout"
        exit_code = process.returncode
    else:
        exit_code = process.returncode
        status = "COMPLETED" if exit_code == 0 else "FAILED_CLOSED"
        reason = None if exit_code == 0 else "guest_worker_failed"
    finally:
        stopped.set(); thread.join(timeout=3)
    attempt_count = int(prior.get("attempt_count", 0)) + 1
    if status == "FAILED_CLOSED" and attempt_count >= 3:
        status = "BLOCKED"
        reason = "deterministic_worker_failure"
    stdout_path = order.checkpoint_path.with_suffix(".stdout.log")
    stderr_path = order.checkpoint_path.with_suffix(".stderr.log")
    _atomic_text(stdout_path, stdout)
    _atomic_text(stderr_path, stderr)
    checkpoint = {
        "schema_version": "kgnote.linux-worker-route.v1", "status": status,
        "reason": reason, "event_id": order.event_id, "command_digest": digest,
        "exit_code": exit_code, "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "memory_max": order.memory_max, "tasks_max": order.tasks_max,
        "lease_timeout_seconds": order.lease_timeout_seconds, "host_fallback_used": False,
        "deadline_at": order.deadline_at.isoformat() if order.deadline_at else None,
        "attempt_count": attempt_count,
        "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
        "execution_evidence": execution_evidence(order, stdout, stderr),
    }
    _atomic_json(order.checkpoint_path, checkpoint)
    return checkpoint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = route(WorkerOrder.from_dict(json.loads(args.order.read_text())))
    except (OSError, json.JSONDecodeError, RoutingError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"COMPLETED", "ALREADY_COMPLETED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
