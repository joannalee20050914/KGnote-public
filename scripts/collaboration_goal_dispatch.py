#!/usr/bin/env python3
"""Run one exact Product Goal transition through the existing trust chain.

This is the execution companion to ``collaboration_goal_wakeup.py``.  It owns
no Product Goal state machine: authority, planning, reservation, accounting,
checkpoint reconciliation, Router execution and Worker results remain owned by
the existing Product Goal modules.  One invocation performs at most one
durable transition or one route.
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
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo

import collaboration_goal_wakeup as readiness
import github_product_goal_control as github_control
import goal_continuity
import goal_runner_adapter


ZONE = ZoneInfo("Asia/Taipei")
SCHEMA_VERSION = "kgnote.collaboration-goal-dispatch.v1"
DEFAULT_STOP_MARKER = Path(".ai/ORCHESTRATOR_STOP")
DEFAULT_ROUTER = Path(__file__).resolve().with_name("linux_worker_router.py")
DEFAULT_EPOCH = Path(__file__).resolve().parents[1] / ".ai/CLAUDE_REVIEWER_CUTOVER_EPOCH.json"
DEFAULT_SCOPE_ADMISSION = Path(__file__).resolve().with_name("epoch_scope_admission.py")
PROTECTED_GOAL_IDS = readiness.PROTECTED_GOAL_IDS
GH = "/opt/homebrew/bin/gh"
PR_MARKER = "KGNOTE-PRODUCT-GOAL-CANDIDATE-V1"


class CollaborationDispatchError(goal_continuity.GoalContractError):
    """The one-shot dispatch could not cross a trusted boundary."""


def _sha256_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise CollaborationDispatchError(f"required input is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(goal_continuity.canonical_json_bytes(value)).hexdigest()


def _resolved_inside(repo: Path, path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise CollaborationDispatchError(f"{label} leaves the repository evidence root") from exc
    return resolved


@contextmanager
def writer_lock(repo: Path) -> Iterator[Path]:
    """Serialize only the new collaboration path; never use the O2 lock/state."""
    directory = repo / "output/control-plane/collaboration-goal"
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / "writer.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CollaborationDispatchError(
                "another collaboration Goal writer owns the exact one-shot lock"
            ) from exc
        yield lock_path


def _run_checked_gate(
    command: list[str], *, repo: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
    label: str,
) -> None:
    completed = command_runner(
        command, cwd=repo, capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "").strip()[-1000:]
        raise CollaborationDispatchError(
            f"{label} rejected the sealed WorkOrder" + (f": {detail}" if detail else "")
        )


def _route_order(
    *, repo: Path, router: Path, order_path: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> int:
    completed = command_runner(
        [sys.executable, str(router), "--order", str(order_path)],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    return int(completed.returncode)


def ensure_candidate_pull_request(
    *, repo: Path, spec: dict[str, Any], state: dict[str, Any],
    state_path: Path, ledger_path: Path, occurred_at: str,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    """Create at most one Draft PR and bind only exact GitHub read-back."""
    candidate = state.get("candidate_identity")
    if not isinstance(candidate, dict) or candidate.get("pull_request") is not None:
        return state
    if "draft_pr" not in spec["allowed_operations"]:
        raise CollaborationDispatchError("Product Goal does not authorize Draft PR creation")
    repository = str(spec["repository"])
    branch = str(candidate.get("branch") or "")
    head = str(candidate.get("commit") or "")
    fingerprint = str(candidate.get("fingerprint") or "")
    marker = (
        f"<!-- {PR_MARKER} goal_id={spec['goal_id']} "
        f"candidate_commit={head} candidate_fingerprint={fingerprint} -->"
    )
    query = command_runner(
        [
            GH, "pr", "list", "--repo", repository, "--head", branch,
            "--state", "open", "--json",
            "number,headRefOid,headRefName,state,isDraft,url",
        ],
        cwd=repo, capture_output=True, text=True, timeout=30, check=False,
    )
    if query.returncode:
        raise CollaborationDispatchError("GitHub candidate PR lookup failed")
    try:
        rows = json.loads(query.stdout)
    except json.JSONDecodeError as exc:
        raise CollaborationDispatchError("GitHub candidate PR lookup is not JSON") from exc
    if not isinstance(rows, list) or len(rows) > 1:
        raise CollaborationDispatchError("GitHub candidate PR lookup is invalid or ambiguous")
    if not rows:
        body = (
            "## 目的\n\n"
            "承載此 Product Goal 的 exact candidate；Draft PR 不代表 Owner 驗收或合併授權。\n\n"
            "## 安全邊界\n\n"
            "候選仍須通過 deterministic verification、獨立審查與真人產品驗收。\n\n"
            + marker
        )
        created = command_runner(
            [
                GH, "pr", "create", "--repo", repository,
                "--head", branch, "--base", "main", "--draft",
                "--title", f"[{spec['goal_id']}] {spec['title']}",
                "--body", body,
            ],
            cwd=repo, capture_output=True, text=True, timeout=30, check=False,
        )
        if created.returncode:
            raise CollaborationDispatchError("GitHub Draft PR creation failed")
    readback = command_runner(
        [
            GH, "pr", "view", branch, "--repo", repository, "--json",
            "number,headRefOid,headRefName,state,isDraft,url,body",
        ],
        cwd=repo, capture_output=True, text=True, timeout=30, check=False,
    )
    if readback.returncode:
        raise CollaborationDispatchError("GitHub candidate PR read-back failed")
    try:
        observed = json.loads(readback.stdout)
    except json.JSONDecodeError as exc:
        raise CollaborationDispatchError("GitHub candidate PR read-back is not JSON") from exc
    marker_pattern = re.compile(
        rf"<!--\s*{re.escape(PR_MARKER)}\s+goal_id={re.escape(spec['goal_id'])}\s+"
        rf"candidate_commit=([0-9a-f]{{40}})\s+"
        rf"candidate_fingerprint=([0-9a-f]{{64}})\s*-->"
    )
    matches = marker_pattern.findall(
        str(observed.get("body", "")) if isinstance(observed, dict) else ""
    )
    if (
        not isinstance(observed, dict)
        or observed.get("headRefOid") != head
        or observed.get("headRefName") != branch
        or observed.get("state") != "OPEN"
        or observed.get("isDraft") is not True
        or not isinstance(observed.get("number"), int)
        or not isinstance(observed.get("url"), str)
        or matches != [(head, fingerprint)]
    ):
        raise CollaborationDispatchError(
            "GitHub candidate PR HEAD/branch/fingerprint read-back differs"
        )
    return goal_runner_adapter.bind_candidate_pull_request(
        spec, state, state_path=state_path, ledger_path=ledger_path,
        pull_request=int(observed["number"]), head=head, branch=branch,
        artifact_url=str(observed["url"]), occurred_at=occurred_at,
    )


def _discover_runtime(
    *, repo: Path, router: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    completed = command_runner(
        [sys.executable, str(router), "--discover-runtime"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise CollaborationDispatchError("Ubuntu runtime identity discovery failed")
    try:
        value = json.loads(completed.stdout)
        return goal_runner_adapter.runtime_admission.validate_runtime_identity(value)
    except (
        json.JSONDecodeError,
        goal_runner_adapter.runtime_admission.RuntimeAdmissionError,
    ) as exc:
        raise CollaborationDispatchError("Ubuntu runtime identity is malformed") from exc


def _pre_reservation_admission(
    *, repo: Path, router: Path, order_path: Path,
    runtime_identity: dict[str, Any],
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Path:
    # Randomness is used only as an anti-replay challenge.  It cannot grant
    # authority and is committed into the exact admission receipt.
    challenge = os.urandom(32).hex()
    receipt_path = (
        repo / "output/control-plane/collaboration-goal/runtime-admissions"
        / f"{challenge}.json"
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    completed = command_runner(
        [
            sys.executable, str(router), "--admit-order", str(order_path),
            "--runtime-identity-json",
            json.dumps(runtime_identity, sort_keys=True, separators=(",", ":")),
            "--challenge", challenge,
            "--admission-receipt", str(receipt_path),
        ],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise CollaborationDispatchError("live Ubuntu pre-reservation admission failed")
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise CollaborationDispatchError("live Ubuntu admission receipt is absent")
    try:
        returned = json.loads(completed.stdout)
        written = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CollaborationDispatchError("live Ubuntu admission receipt is malformed") from exc
    if goal_continuity.canonical_json_bytes(returned) != goal_continuity.canonical_json_bytes(written):
        raise CollaborationDispatchError("live Ubuntu admission read-back differs")
    return receipt_path


def _result(
    *, status: str, observed_at: datetime, spec: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None, authority: dict[str, Any] | None = None,
    decision: dict[str, Any] | None = None, extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at.astimezone(ZONE).isoformat(),
        "status": status,
        "goal": None,
        "authority": None,
        "decision": deepcopy(decision),
        "safety": {
            "legacy_o2_runner_used": False,
            "legacy_o2_state_or_ledger_used": False,
            "single_writer": True,
            "model_launch_started": status == "DISPATCHED" and bool(
                (decision or {}).get("requires_model")
            ),
        },
    }
    if spec is not None:
        value["goal"] = {
            "goal_id": spec["goal_id"],
            "goal_version": spec["goal_version"],
            "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
            "github_issue": spec["github_issue"],
        }
    if state is not None:
        value["ledger_cursor"] = deepcopy(state["event_cursor"])
    if authority is not None:
        value["authority"] = {
            "status": authority.get("status"),
            "authority_lease": authority.get("authority_lease"),
            "record": deepcopy(authority.get("record")),
        }
    if extra:
        value.update(deepcopy(extra))
    value["receipt_sha256"] = _canonical_sha256(value)
    return value


def dispatch_once(
    *, repo: Path, spec_path: Path, state_path: Path, ledger_path: Path,
    now: datetime, router: Path = DEFAULT_ROUTER,
    epoch_record: Path = DEFAULT_EPOCH,
    scope_admission: Path = DEFAULT_SCOPE_ADMISSION,
    stop_marker: Path | None = None,
    comments_fetcher: Callable[[dict[str, Any]], list[dict[str, Any]]] = github_control.fetch_issue_comments,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Perform at most one durable transition/route for one exact Product Goal."""
    if now.tzinfo is None:
        raise CollaborationDispatchError("observation time must be timezone-aware")
    observed_at = now.astimezone(ZONE)
    repo = repo.resolve()
    spec_path = _resolved_inside(repo, spec_path, "Goal spec")
    state_path = _resolved_inside(repo, state_path, "Runner state")
    ledger_path = _resolved_inside(repo, ledger_path, "Goal ledger")
    router = _resolved_inside(repo, router, "Linux Router")
    epoch_record = _resolved_inside(repo, epoch_record, "epoch record")
    scope_admission = _resolved_inside(repo, scope_admission, "scope admission")
    marker = (repo / DEFAULT_STOP_MARKER) if stop_marker is None else _resolved_inside(
        repo, stop_marker, "Stop Marker"
    )

    with writer_lock(repo):
        spec = goal_continuity.load_json(spec_path)
        goal_continuity.validate_goal_spec(spec)
        if spec["goal_id"] in PROTECTED_GOAL_IDS:
            raise readiness.ProtectedGoalError(
                f"protected historical Goal {spec['goal_id']} cannot use the collaboration dispatcher"
            )
        repository = readiness.repository_identity(repo)
        if repository["repository"] != spec["repository"]:
            raise CollaborationDispatchError("Goal repository differs from current origin")
        state = goal_continuity.load_json(state_path)
        ledger = goal_continuity.read_ledger(ledger_path)
        goal_continuity.validate_runner_state(state, spec)
        goal_continuity.validate_ledger_binding(ledger, state, spec)
        goal_continuity.validate_history_carryover_evidence(
            spec, repository_root=repo,
        )
        readiness._assert_candidate_binding(state, repository)

        if marker.exists():
            projection = goal_continuity.reduce_ledger(ledger)
            pending = next(
                (
                    (attempt_id, reservation)
                    for attempt_id, reservation in projection.get(
                        "dispatch_reservations", {}
                    ).items()
                    if not reservation.get("reconciled")
                ),
                None,
            )
            if pending is not None:
                attempt_id, _reservation = pending
                recovered = goal_runner_adapter.reconcile_dispatch_checkpoint(
                    spec, state, state_path=state_path, ledger_path=ledger_path,
                    repo=repo, attempt_id=str(attempt_id),
                    occurred_at=observed_at.isoformat(timespec="seconds"),
                )
                refreshed = goal_continuity.load_json(state_path)
                return _result(
                    status="STOPPED", observed_at=observed_at, spec=spec,
                    state=refreshed,
                    decision={
                        "status": "STOP_MARKER", "requires_model": False,
                        "reason": "Stop Marker remains latched after checkpoint reconciliation",
                    },
                    extra={"reconciliation": recovered},
                )
            return _result(
                status="STOPPED", observed_at=observed_at, spec=spec,
                state=state,
                decision={
                    "status": "STOP_MARKER", "requires_model": False,
                    "reason": "the explicit Stop Marker blocks every new transition",
                },
            )

        comments = comments_fetcher(spec)
        if not isinstance(comments, list):
            raise CollaborationDispatchError("GitHub comments input must be a JSON list")
        authority = github_control.resolve_authority(comments, spec)
        reconciled = goal_runner_adapter.reconcile_owner_authority(
            spec, state, authority, state_path=state_path,
            ledger_path=ledger_path, observed_at=observed_at,
        )
        state = reconciled["state"]
        if reconciled["rejected_transitions"]:
            return _result(
                status="AUTHORITY_COMMAND_REJECTED", observed_at=observed_at,
                spec=spec, state=state, authority=authority,
                decision={
                    "status": "AUTHORITY_COMMAND_REJECTED",
                    "requires_model": False,
                    "rejected_transitions": reconciled["rejected_transitions"],
                },
            )

        ledger = goal_continuity.read_ledger(ledger_path)
        decision = goal_runner_adapter.next_action(
            spec, state, ledger, authority, now=observed_at, trial=False,
        )
        if (
            decision.get("status") == "RECOVERY_READY"
            and decision.get("action") == "RECONCILE_CHECKPOINT"
        ):
            recovered = goal_runner_adapter.reconcile_dispatch_checkpoint(
                spec, state, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=str(decision["attempt_id"]),
                occurred_at=observed_at.isoformat(timespec="seconds"),
            )
            refreshed = goal_continuity.load_json(state_path)
            return _result(
                status=str(recovered["status"]), observed_at=observed_at,
                spec=spec, state=refreshed, authority=authority,
                decision=decision, extra={"reconciliation": recovered},
            )
        if (
            decision.get("status") == "RECOVERY_READY"
            and decision.get("action") == "RESUME_AFTER_QUOTA"
        ):
            resumed = goal_runner_adapter.resume_after_quota_backoff(
                spec, state, state_path=state_path, ledger_path=ledger_path,
                now=observed_at,
            )
            return _result(
                status=str(resumed["status"]), observed_at=observed_at,
                spec=spec, state=goal_continuity.load_json(state_path),
                authority=authority, decision=decision,
                extra={"recovery": resumed},
            )
        if (
            decision.get("status") == "RECOVERY_READY"
            and decision.get("action")
            in goal_runner_adapter.RECOVERABLE_RUNTIME_ACTIONS
        ):
            resumed = goal_runner_adapter.resume_recoverable_runtime_block(
                spec, state, state_path=state_path, ledger_path=ledger_path,
                now=observed_at,
            )
            return _result(
                status=str(resumed["status"]), observed_at=observed_at,
                spec=spec, state=goal_continuity.load_json(state_path),
                authority=authority, decision=decision,
                extra={"recovery": resumed},
            )
        if decision.get("status") != "ACTION_READY":
            return _result(
                status=(
                    "WAITING_AUTHORIZATION"
                    if decision.get("status") in readiness.AUTHORIZATION_STATUSES
                    else str(decision.get("status") or "BLOCKED")
                ),
                observed_at=observed_at, spec=spec, state=state,
                authority=authority, decision=decision,
            )

        if (
            decision.get("action") == "DISPATCH_REVIEW"
            and isinstance(state.get("candidate_identity"), dict)
            and state["candidate_identity"].get("pull_request") is None
        ):
            state = ensure_candidate_pull_request(
                repo=repo, spec=spec, state=state, state_path=state_path,
                ledger_path=ledger_path,
                occurred_at=observed_at.isoformat(timespec="seconds"),
                command_runner=command_runner,
            )

        runtime_identity = None
        runtime_required = goal_runner_adapter.requires_runtime_admission(spec, decision)
        if decision.get("requires_model") is True and not runtime_required:
            raise CollaborationDispatchError(
                "model dispatch is denied until the generic Product Goal identity has "
                "the same live Ubuntu pre-reservation admission as the exact O2 path"
            )
        if runtime_required:
            runtime_identity = _discover_runtime(
                repo=repo, router=router, command_runner=command_runner,
            )
        state, order_path, order, _ = goal_runner_adapter.ensure_bound_order(
            spec, state, decision, repo=repo, state_path=state_path,
            ledger_path=ledger_path,
            occurred_at=observed_at.isoformat(timespec="seconds"),
            runtime_identity=runtime_identity,
            persist_binding=not runtime_required,
        )
        _run_checked_gate(
            [
                sys.executable, str(scope_admission), "--epoch",
                str(epoch_record), "--order", str(order_path),
            ],
            repo=repo, command_runner=command_runner,
            label="epoch/scope admission",
        )
        admission_receipt_path = None
        if runtime_required:
            assert runtime_identity is not None
            admission_receipt_path = _pre_reservation_admission(
                repo=repo, router=router, order_path=order_path,
                runtime_identity=runtime_identity,
                command_runner=command_runner,
            )
        reserved, order_path, attempt_id = goal_runner_adapter.reserve_dispatch(
            spec, state, decision, state_path=state_path,
            ledger_path=ledger_path, repo=repo,
            occurred_at=observed_at.isoformat(timespec="seconds"),
            prepared_order_path=(order_path if runtime_required else None),
            admission_receipt_path=admission_receipt_path,
        )
        route_exit = _route_order(
            repo=repo, router=router, order_path=order_path,
            command_runner=command_runner,
        )
        updated = goal_runner_adapter.record_route_outcome(
            spec, reserved, state_path=state_path,
            work_item_id=str(decision["work_item_id"]),
            attempt_id=attempt_id, route_exit_code=route_exit,
            occurred_at=observed_at.isoformat(timespec="seconds"),
        )
        status = "DISPATCHED" if route_exit == 0 else "ROUTE_FAILED_RECONCILIATION_REQUIRED"
        return _result(
            status=status, observed_at=observed_at, spec=spec, state=updated,
            authority=authority, decision=decision,
            extra={
                "attempt_id": attempt_id,
                "order": {
                    "path": str(order_path.relative_to(repo)),
                    "sha256": _sha256_file(order_path),
                    "event_id": order["event_id"],
                    "checkpoint_path": order["checkpoint_path"],
                },
                "route_exit_code": route_exit,
            },
        )


def blocked_result(message: str, *, now: datetime) -> dict[str, Any]:
    return _result(
        status="BLOCKED", observed_at=now,
        decision={"status": "VALIDATION_ERROR", "requires_model": False},
        extra={"error": {"message": message}},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--router", type=Path, default=DEFAULT_ROUTER)
    parser.add_argument("--epoch-record", type=Path, default=DEFAULT_EPOCH)
    parser.add_argument("--scope-admission", type=Path, default=DEFAULT_SCOPE_ADMISSION)
    parser.add_argument("--stop-marker", type=Path)
    parser.add_argument("--now")
    args = parser.parse_args()
    observed = datetime.now(ZONE)
    try:
        observed = readiness.parse_observation_time(args.now)
        result = dispatch_once(
            repo=args.repo, spec_path=args.spec, state_path=args.state,
            ledger_path=args.ledger, now=observed, router=args.router,
            epoch_record=args.epoch_record,
            scope_admission=args.scope_admission,
            stop_marker=args.stop_marker,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = blocked_result(str(exc), now=observed)
        print(readiness.serialize_result(result), end="")
        return 2
    print(readiness.serialize_result(result), end="")
    failures = {
        "BLOCKED", "AUTHORITY_COMMAND_REJECTED",
        "ROUTE_FAILED_RECONCILIATION_REQUIRED",
    }
    return 2 if result["status"] in failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
