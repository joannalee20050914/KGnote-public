#!/usr/bin/env python3
"""Bounded production wake-up adapter for the existing KGnote orchestrator."""
from __future__ import annotations
import fcntl, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output/control-plane/production-runner"
LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
ZONE = ZoneInfo("Asia/Taipei")
TERMINAL = {"STOPPED", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED", "GOAL_COMPLETE", "HUMAN_CHECKPOINT_REQUIRED", "PRODUCT_DECISION_REQUIRED", "AUTHORITY_CONFLICT"}
RUNNABLE = {"IMPLEMENTING", "VALIDATING", "READY_FOR_AI_REVIEW", "REVIEWING", "REPAIRING", "AWAITING_EXTERNAL_PRODUCT_REVIEW"}

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

def run_once(repo: Path = REPO, current: datetime | None = None, command_runner=subprocess.run) -> int:
    global OUT, LOCK, LOG
    OUT = repo / "output/control-plane/production-runner"; LOCK, LOG = OUT / "writer.lock", OUT / "runner.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock_handle:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: append("writer_lock_blocked"); return 0
        try:
            state = load(repo / ".ai/ORCHESTRATOR_STATE.json"); envelope = load(repo / ".ai/work-package-envelope.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc: append("configuration_rejected", reason=str(exc)); return 2
        persisted = str(state.get("state", ""))
        if persisted in TERMINAL: append("hard_stop_preserved", status=persisted); return 0
        errors = envelope_errors(envelope, state)
        if errors: append("authorization_rejected", errors=errors); return 2
        if not in_window(envelope, current): append("outside_work_window"); return 0
        if persisted not in RUNNABLE: append("state_rejected", status=persisted); return 2
        command = [sys.executable, str(repo / "scripts/codex_orchestrator.py"), "--repo", str(repo), "resume", "--max-steps", "1"]
        environment = os.environ.copy(); environment["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        append("orchestrator_wake_started", status=persisted)
        completed = command_runner(command, cwd=repo, env=environment, capture_output=True, text=True)
        append("orchestrator_wake_completed", exit_code=completed.returncode)
        return completed.returncode

if __name__ == "__main__": raise SystemExit(run_once())
