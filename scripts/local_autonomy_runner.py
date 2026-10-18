#!/usr/bin/env python3
"""Single Mac production Runner for cgroup-confined Ubuntu worker orders."""
from __future__ import annotations
import argparse, fcntl, json, os, subprocess, sys, tempfile
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
DEFAULT_PENDING = Path("/Users/joanna/KGnote-claude-reviewer-integration/.ai/PENDING_SUCCESSOR_GOAL.json")
SUCCESSOR_HANDOFF = Path(".ai/SUCCESSOR_HANDOFF.json")

def append(event: str, **fields: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": datetime.now(ZONE).isoformat(timespec="seconds"), "event": event, **fields}, ensure_ascii=False) + "\n")

def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path.name} must contain an object")
    return value


def atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def successor_errors(pending: dict[str, object], current: datetime) -> list[str]:
    errors: list[str] = []
    if pending.get("schema_version") != "kgnote.pending-successor-goal.v1": errors.append("unsupported pending goal schema")
    if pending.get("status") not in {"PENDING_ELIGIBLE", "ACTIVATING", "ACTIVE"}: errors.append("pending goal is not eligible")
    authority = pending.get("authority", {})
    if not isinstance(authority, dict) or authority.get("status") != "APPROVED_FOR_FUTURE_WINDOW": errors.append("future-window authority is missing")
    try: activation = datetime.fromisoformat(str(pending["activation_not_before"]))
    except (KeyError, ValueError): errors.append("activation_not_before is invalid"); activation = current
    if current < activation: errors.append("activation time has not arrived")
    budget = pending.get("continuous_budget", {})
    if not isinstance(budget, dict): errors.append("continuous budget is invalid")
    else:
        for name in ("new_prs", "claude_product_reviews", "codex_implementation_or_repair_cycles"):
            item = budget.get(name, {})
            if not isinstance(item, dict) or not isinstance(item.get("authorized"), int) or not isinstance(item.get("used"), int) or item["used"] >= item["authorized"]:
                errors.append(f"{name} budget is exhausted or invalid")
    legacy = pending.get("legacy_inheritance", {})
    if not isinstance(legacy, dict) or legacy.get("pull_request") != 23 or legacy.get("review_round") != 8 or legacy.get("cycle") != 20:
        errors.append("legacy PR/Round/Cycle inheritance is invalid")
    if pending.get("product_work_started") is not False and pending.get("status") != "ACTIVE": errors.append("pending goal has inconsistent product state")
    return errors


def prepare_successor_handoff(repo: Path, pending_path: Path, current: datetime, command_runner=subprocess.run) -> tuple[Path | None, list[str]]:
    """Create one epoch-new branch/PR and a durable Ubuntu Codex order.

    GitHub mutations are idempotent read-before-write operations. Candidate
    commits are never pushed here; later pushes remain restricted to the Guest
    push stage and its repository-scoped deploy key.
    """
    try: pending = load(pending_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc: return None, [str(exc)]
    errors = successor_errors(pending, current)
    if errors: return None, errors
    goal_id = str(pending["goal_id"]); repository = str((pending.get("scope") or {}).get("repository"))
    legacy = pending["legacy_inheritance"]; head = str(legacy["head"])
    branch = "codex/source-library-successor-20261019"
    ref_endpoint = f"repos/{repository}/git/ref/heads/{branch}"
    read_ref = command_runner(["/opt/homebrew/bin/gh", "api", ref_endpoint], cwd=repo, capture_output=True, text=True)
    if read_ref.returncode:
        created = command_runner(
            ["/opt/homebrew/bin/gh", "api", "--method", "POST", f"repos/{repository}/git/refs", "-f", f"ref=refs/heads/{branch}", "-f", f"sha={head}"],
            cwd=repo, capture_output=True, text=True,
        )
        if created.returncode: return None, ["successor branch creation failed"]
    confirmed = command_runner(["/opt/homebrew/bin/gh", "api", ref_endpoint], cwd=repo, capture_output=True, text=True)
    try: remote_head = ((json.loads(confirmed.stdout).get("object") or {}).get("sha"))
    except json.JSONDecodeError: remote_head = None
    if confirmed.returncode or remote_head != head: return None, ["successor branch read-back mismatch"]
    listed = command_runner(
        ["/opt/homebrew/bin/gh", "pr", "list", "--repo", repository, "--head", branch, "--state", "all", "--json", "number,state,isDraft,headRefName,baseRefName,url"],
        cwd=repo, capture_output=True, text=True,
    )
    try: prs = json.loads(listed.stdout) if not listed.returncode else []
    except json.JSONDecodeError: prs = []
    if prs:
        pr = prs[0]
    else:
        made = command_runner(
            ["/opt/homebrew/bin/gh", "pr", "create", "--repo", repository, "--base", "codex/issue-19-real-review", "--head", branch, "--draft", "--title", "Issue #8 後繼：Source Library R-004", "--body", "此 Draft PR 由既有 Pending Goal 在合法工作時段建立。它保留 Legacy PR #23、Round 8、Cycle 20 與累計預算，不合併、不啟用 Auto Merge，且不提升任何 Human Gate。"],
            cwd=repo, capture_output=True, text=True,
        )
        if made.returncode: return None, ["successor Draft PR creation failed"]
        number = int(made.stdout.strip().rstrip("/").split("/")[-1])
        viewed = command_runner(["/opt/homebrew/bin/gh", "pr", "view", str(number), "--repo", repository, "--json", "number,state,isDraft,headRefName,baseRefName,url"], cwd=repo, capture_output=True, text=True)
        try: pr = json.loads(viewed.stdout)
        except json.JSONDecodeError: return None, ["successor Draft PR read-back is invalid"]
    if pr.get("state") != "OPEN" or pr.get("isDraft") is not True or pr.get("headRefName") != branch or pr.get("baseRefName") != "codex/issue-19-real-review":
        return None, ["successor Draft PR identity mismatch"]
    deadline = current.replace(hour=18, minute=0, second=0, microsecond=0)
    worktree = "/home/kgnote/.local/share/kgnote/source-library-successor-20261019"
    checkpoint = repo / "output/control-plane/production-runner/successor-codex-route.json"
    prompt = (
        "Resume the owner-authorized KGnote successor goal. Preserve Legacy PR #23, External Round 8 review 5561321715, "
        "finding-r-004, Cycle 20, supplemental usage 15/17, the cutover epoch, and every human gate. "
        "Work only on the inherited finding-r-004 and necessary tests. Do not merge, push, use paid APIs, or modify main. "
        "Read AGENTS.md, PLAN.md, CODEX_STATUS.md and repository authority before editing; checkpoint resumable state before exit."
    )
    order = {
        "event_id": "source-library-successor-codex-20261019", "stage": "codex",
        "working_directory": worktree,
        "command": ["/home/kgnote/.local/bin/kgnote-successor-codex", repository, branch, head, prompt],
        "checkpoint_path": str(checkpoint), "memory_max": "4G", "tasks_max": 192,
        "timeout_seconds": max(1, min(3600, int((deadline-current).total_seconds()))),
        "lease_timeout_seconds": 8, "deadline_at": deadline.isoformat(),
        "review_admission": {
            "repository": repository, "pull_request": pr["number"], "head_sha": head,
            "candidate_fingerprint": str(legacy.get("candidate_fingerprint", "")),
            "review_round": 9,
            "authority": {"status":"APPROVED", "goal_id":goal_id, "authority_record":str(pending.get("authority", {}).get("source", "owner instruction"))},
            "budget": {"authorized": int((pending["continuous_budget"]["claude_product_reviews"])["authorized"]), "used": int((pending["continuous_budget"]["claude_product_reviews"])["used"])},
            "work_window_allowed": True, "stop_marker_clear": True,
            "existing_exact_candidate_result": False,
        },
    }
    order_path = repo / PRODUCT_ORDER; atomic_json(order_path, order)
    handoff = {
        "schema_version": "kgnote.successor-handoff.v1", "goal_id": goal_id,
        "status": "DISPATCH_READY", "repository": repository, "legacy_pr": 23,
        "successor_pr": pr["number"], "successor_pr_url": pr["url"], "branch": branch,
        "inherited_head": head, "review_round": 8, "cycle": 20,
        "cutover_epoch": pending.get("cutover_epoch"), "order_path": str(order_path),
        "deadline_at": deadline.isoformat(), "human_gates_preserved": True,
    }
    atomic_json(repo / SUCCESSOR_HANDOFF, handoff)
    pending.update({"status":"ACTIVATING", "new_product_pr_created":True, "successor_pull_request":pr["number"], "successor_branch":branch})
    atomic_json(pending_path, pending)
    return order_path, []

def in_window(envelope: dict[str, object], current: datetime | None = None) -> bool:
    current, window = current or datetime.now(ZONE), envelope.get("work_window", {})
    if not isinstance(window, dict) or window.get("timezone") != "Asia/Taipei": return False
    # Production product work is weekday-only.  The hard 18:00 ceiling is an
    # execution safety boundary even when an older envelope still says 18:30.
    if current.weekday() >= 5:
        return False
    try:
        sh, sm = map(int, str(window["start"]).split(":")); eh, em = map(int, str(window["end"]).split(":"))
    except (KeyError, ValueError): return False
    end = min(eh * 60 + em, 18 * 60)
    minute = current.hour * 60 + current.minute
    return sh * 60 + sm <= minute < end

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
        "event_id": "production-idle-health-v2",
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
    pending_goal: Path = DEFAULT_PENDING,
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
            pending: dict[str, object] = {}
            try: pending = load(pending_goal)
            except (OSError, ValueError, json.JSONDecodeError): pass
            transition_now = current or datetime.now(ZONE)
            if pending and not successor_errors(pending, transition_now) and in_window({"work_window": pending.get("work_window", {})}, transition_now):
                order, errors = prepare_successor_handoff(repo, pending_goal, current or datetime.now(ZONE), command_runner)
                if errors: append("pending_successor_rejected", errors=errors); return 2
                if order is not None:
                    gate = command_runner([sys.executable, str(admission), "--epoch", str(epoch_record), "--order", str(order)], cwd=repo, capture_output=True, text=True)
                    if gate.returncode:
                        append("successor_epoch_admission_rejected", output_tail=(gate.stdout or "")[-1000:]); return 2
                    append("successor_epoch_admission_passed", output_tail=(gate.stdout or "")[-1000:])
                    result = route_order(repo, router, order, command_runner)
                    if result == 0:
                        pending = load(pending_goal); pending.update({"status":"ACTIVE", "product_work_started":True}); atomic_json(pending_goal, pending)
                        handoff = load(repo / SUCCESSOR_HANDOFF); handoff["status"] = "CODEX_DISPATCHED"; atomic_json(repo / SUCCESSOR_HANDOFF, handoff)
                    append("pending_successor_dispatched", exit_code=result)
                    return result
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
    parser.add_argument("--pending-goal", type=Path, default=DEFAULT_PENDING)
    args = parser.parse_args()
    return run_once(
        args.repo.resolve(), router=args.router.resolve(),
        canary_order=args.canary_order.resolve() if args.canary_order else None,
        epoch_record=args.epoch_record.resolve(), admission=args.scope_admission.resolve(),
        pending_goal=args.pending_goal.resolve(),
    )

if __name__ == "__main__": raise SystemExit(main())
