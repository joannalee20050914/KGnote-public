#!/usr/bin/env python3
"""Single Mac production Runner for cgroup-confined Ubuntu worker orders."""
from __future__ import annotations
import argparse, fcntl, json, subprocess, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output/control-plane/production-runner"
LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
ZONE = ZoneInfo("Asia/Taipei")
TERMINAL = {"STOPPED", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED", "GOAL_COMPLETE", "HUMAN_CHECKPOINT_REQUIRED", "PRODUCT_DECISION_REQUIRED", "AUTHORITY_CONFLICT"}
RUNNABLE = {"IMPLEMENTING", "VALIDATING", "READY_FOR_AI_REVIEW", "REVIEWING", "REPAIRING", "AWAITING_EXTERNAL_PRODUCT_REVIEW"}
STOP_MARKER = Path(".ai/ORCHESTRATOR_STOP")
PRODUCT_ORDER = Path(".ai/linux-worker-order.json")
DEFAULT_ROUTER = Path("/Users/joanna/KGnote-claude-reviewer-integration/scripts/linux_worker_router.py")
DEFAULT_EPOCH = Path("/Users/joanna/KGnote-claude-reviewer-integration/.ai/CLAUDE_REVIEWER_CUTOVER_EPOCH.json")
DEFAULT_ADMISSION = Path("/Users/joanna/KGnote-claude-reviewer-integration/scripts/epoch_scope_admission.py")

def append(event: str, **fields: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": datetime.now(ZONE).isoformat(timespec="seconds"), "event": event, **fields}, ensure_ascii=False) + "\n")

def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path.name} must contain an object")
    return value

def in_window(envelope: dict[str, object], current: datetime | None = None) -> bool:
    current, window = current or datetime.now(ZONE), envelope.get("work_window", {})
    if not isinstance(window, dict) or window.get("timezone") != "Asia/Taipei": return False
    try:
        sh, sm = map(int, str(window["start"]).split(":")); eh, em = map(int, str(window["end"]).split(":"))
    except (KeyError, ValueError): return False
    minute = current.hour * 60 + current.minute
    return sh * 60 + sm <= minute < eh * 60 + em

def envelope_errors(envelope: dict[str, object], state: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if envelope.get("schema_version") != "kgnote.work-package-envelope.v1": errors.append("unsupported envelope schema")
    if envelope.get("status") != "APPROVED": errors.append("work package is not approved")
    approval = envelope.get("approval", {})
    if not isinstance(approval, dict) or approval.get("source_status") != "RECONCILING" or not approval.get("receipt"):
        errors.append("pre-seal reconciliation approval receipt is missing")
    if envelope.get("goal_id") != state.get("active_goal"): errors.append("goal identity mismatch")
    if envelope.get("work_package_id") != state.get("work_package"): errors.append("work package identity mismatch")
    if not envelope.get("authority_record"): errors.append("authority record is missing")
    budgets = envelope.get("budgets", {})
    if not isinstance(budgets, dict): return errors + ["budgets must be an object"]
    for name in ("local_repairs", "internal_reviews", "external_reviews"):
        item = budgets.get(name, {})
        if not isinstance(item, dict): errors.append(f"{name} is invalid"); continue
        authorized, used = item.get("authorized"), item.get("used")
        if isinstance(authorized, bool) or not isinstance(authorized, int) or authorized < 0: errors.append(f"{name}.authorized is invalid")
        if isinstance(used, bool) or not isinstance(used, int) or used < 0: errors.append(f"{name}.used is invalid")
        if isinstance(authorized, int) and isinstance(used, int) and used > authorized: errors.append(f"{name} exceeds authorization")
    return errors

def route_order(
    repo: Path,
    router: Path,
    order_path: Path,
    command_runner=subprocess.run,
) -> int:
    if not router.is_file():
        append("linux_router_rejected", reason="router_missing", router=str(router))
        return 2
    probe = command_runner(
        ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes", "-o", "ConnectTimeout=5", "kgnote-ubuntu", "/usr/bin/true"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        append("linux_router_rejected", reason="guest_unavailable", exit_code=probe.returncode)
        return 2
    command = [sys.executable, str(router), "--order", str(order_path)]
    completed = command_runner(command, cwd=repo, capture_output=True, text=True)
    append(
        "linux_router_completed",
        order=str(order_path),
        exit_code=completed.returncode,
        output_tail=(completed.stdout or "")[-1000:],
    )
    return completed.returncode


def idle_health_order(repo: Path) -> Path:
    path = OUT / "linux-idle-health-order.json"
    value = {
        "event_id": "production-idle-health-v1",
        "stage": "ingestion",
        "working_directory": "/home/kgnote/.local/share/kgnote",
        "command": ["/usr/bin/true"],
        "checkpoint_path": str(OUT / "linux-idle-health-checkpoint.json"),
        "memory_max": "128M",
        "tasks_max": 16,
        "timeout_seconds": 30,
        "lease_timeout_seconds": 8,
    }
    if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != value:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_canary_order(path: Path) -> None:
    value = load(path)
    if not str(value.get("event_id", "")).startswith("production-canary-"):
        raise ValueError("canary event_id is not allowlisted")
    if value.get("working_directory") != "/home/kgnote/.local/share/kgnote/smoke-repo":
        raise ValueError("canary worktree is not the private smoke repository")
    checkpoint = Path(str(value.get("checkpoint_path", "")))
    allowed = Path("/Users/joanna/KGnote-claude-reviewer-integration/output/claude-reviewer-final")
    if not checkpoint.is_absolute() or not checkpoint.is_relative_to(allowed):
        raise ValueError("canary checkpoint is outside the integration evidence root")


def run_once(
    repo: Path = REPO,
    current: datetime | None = None,
    command_runner=subprocess.run,
    router: Path = DEFAULT_ROUTER,
    canary_order: Path | None = None,
    epoch_record: Path = DEFAULT_EPOCH,
    admission: Path = DEFAULT_ADMISSION,
) -> int:
    global OUT, LOCK, LOG
    OUT = repo / "output/control-plane/production-runner"; LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock_handle:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: append("writer_lock_blocked"); return 0
        try:
            state = load(repo / ".ai/ORCHESTRATOR_STATE.json"); envelope = load(repo / ".ai/work-package-envelope.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc: append("configuration_rejected", reason=str(exc)); return 2
        if (repo / STOP_MARKER).exists():
            order = idle_health_order(repo)
            if canary_order is not None:
                try: validate_canary_order(canary_order)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    append("canary_rejected", reason=str(exc)); return 2
                order = canary_order
            result = route_order(repo, router, order, command_runner)
            append("product_stop_marker_preserved_idle", linux_health_exit_code=result)
            return result
        persisted = str(state.get("state", ""))
        if persisted in TERMINAL: append("hard_stop_preserved", status=persisted); return 0
        errors = envelope_errors(envelope, state)
        if errors: append("authorization_rejected", errors=errors); return 2
        if not in_window(envelope, current): append("outside_work_window"); return 0
        if persisted not in RUNNABLE: append("state_rejected", status=persisted); return 2
        order_path = repo / PRODUCT_ORDER
        if not order_path.is_file():
            append("production_dispatch_failed_closed", reason="linux_worker_order_missing", status=persisted)
            return 2
        if not epoch_record.is_file() or not admission.is_file():
            append("epoch_admission_rejected", reason="epoch gate unavailable")
            return 2
        gate = command_runner(
            [sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order_path)],
            cwd=repo, capture_output=True, text=True,
        )
        if gate.returncode:
            append("epoch_admission_rejected", output_tail=(gate.stdout or "")[-1000:])
            return 2
        append("epoch_admission_passed", output_tail=(gate.stdout or "")[-1000:])
        append("linux_worker_dispatch_started", status=persisted, order=str(order_path))
        return route_order(repo, router, order_path, command_runner)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--router", type=Path, default=DEFAULT_ROUTER)
    parser.add_argument("--canary-order", type=Path)
    parser.add_argument("--epoch-record", type=Path, default=DEFAULT_EPOCH)
    parser.add_argument("--scope-admission", type=Path, default=DEFAULT_ADMISSION)
    args = parser.parse_args()
    return run_once(
        args.repo.resolve(), router=args.router.resolve(),
        canary_order=args.canary_order.resolve() if args.canary_order else None,
        epoch_record=args.epoch_record.resolve(), admission=args.scope_admission.resolve(),
    )

if __name__ == "__main__": raise SystemExit(main())
