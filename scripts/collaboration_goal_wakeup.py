#!/usr/bin/env python3
"""Read-only one-shot bridge from exact Goal authority to planner readiness.

This command deliberately has no activation, scheduling, reservation, routing,
GitHub-write, or model-launch path.  It validates and reports one planner
decision with ``trial=True``; a later, separately authorized scheduler must
perform every durable or external action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import github_product_goal_control as github_control
import goal_continuity
import goal_runner_adapter


ZONE = ZoneInfo("Asia/Taipei")
SCHEMA_VERSION = "kgnote.collaboration-goal-oneshot.v1"
PROTECTED_GOAL_IDS = {"GOAL-KGNOTE-O2-READING-EXPERIENCE"}
PUBLIC_STATUSES = {
    "STOPPED",
    "WAITING_AUTHORIZATION",
    "RUNNING",
    "REVIEWING",
    "BLOCKED",
    "READY_FOR_ACCEPTANCE",
}

AUTHORIZATION_STATUSES = {
    "WAIT_AUTHORITY",
    "TRIAL_ONLY",
    "GO_LIVE_NOT_AUTHORIZED",
}
ACCEPTANCE_STATUSES = {"HUMAN_ACCEPTANCE_REQUIRED", "COMPLETION_GATE_READY"}
STOPPED_STATUSES = {
    "GOAL_CLOSED",
    "GOAL_HARD_STOP",
    "WAIT_TRIAL_START",
    "WAIT_WORK_WINDOW",
    "WAIT_QUOTA_BACKOFF",
    "WAIT_WINDOW_BUDGET",
    "WAIT_LAUNCH_INTERVAL",
    "WAIT_RESERVE",
    "WAIT_CAPACITY",
}
READY_STATUSES = {"ACTION_READY", "TRIAL_ACTION_READY", "RECOVERY_READY"}

SAFETY_ATTESTATION = {
    "readiness_only": True,
    "execution_started": False,
    "dispatch_performed": False,
    "reservation_created": False,
    "model_launch_started": False,
    "schedule_enabled": False,
    "github_write_performed": False,
    "legacy_o2_runner_used": False,
    "input_mutation_detected": False,
}


class CollaborationWakeupError(goal_continuity.GoalContractError):
    """The one-shot cannot safely report a bound planner snapshot."""


class ProtectedGoalError(CollaborationWakeupError):
    """The historical O2 Goal may not enter the new collaboration path."""


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(goal_continuity.canonical_json_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise CollaborationWakeupError(f"required input is not a regular file: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "git read failed").strip()
        raise CollaborationWakeupError(detail)
    return result.stdout.strip()


def _repository_slug(remote: str) -> str:
    patterns = (
        r"^https://github\.com/(?P<slug>[^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/(?P<slug>[^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<slug>[^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, remote)
        if match:
            return match.group("slug")
    raise CollaborationWakeupError("origin must be an exact github.com owner/repository remote")


def repository_identity(repo: Path) -> dict[str, str]:
    root = Path(_run_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo.resolve():
        raise CollaborationWakeupError("--repo must be the exact Git worktree root")
    remote = _run_git(repo, "remote", "get-url", "origin")
    return {
        "repository": _repository_slug(remote),
        "branch": _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": _run_git(repo, "rev-parse", "HEAD"),
    }


def parse_observation_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(ZONE)
    try:
        observed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CollaborationWakeupError("--now must be an ISO-8601 timestamp") from exc
    if observed.tzinfo is None:
        raise CollaborationWakeupError("--now must include a timezone offset")
    return observed.astimezone(ZONE)


def public_status(planner: dict[str, Any]) -> str:
    source = str(planner.get("status") or "")
    if source in AUTHORIZATION_STATUSES:
        return "WAITING_AUTHORIZATION"
    if source in ACCEPTANCE_STATUSES:
        return "READY_FOR_ACCEPTANCE"
    if source in STOPPED_STATUSES:
        return "STOPPED"
    if source in READY_STATUSES:
        return "REVIEWING" if planner.get("action") == "DISPATCH_REVIEW" else "RUNNING"
    return "BLOCKED"


def _authority_summary(authority: dict[str, Any]) -> dict[str, Any]:
    record = authority.get("record")
    current = None
    if isinstance(record, dict):
        current = {
            "action": record.get("action"),
            "comment_id": record.get("comment_id"),
            "comment_url": record.get("comment_url"),
            "body_sha256": record.get("body_sha256"),
            "author_login": record.get("author_login"),
            "created_at": record.get("created_at"),
        }
    return {
        "status": authority.get("status"),
        "authority_lease": authority.get("authority_lease"),
        "current_record": current,
        "valid_record_count": len(authority.get("valid_records", [])),
        "rejected_records": deepcopy(authority.get("rejected_records", [])),
    }


def _assert_candidate_binding(
    state: dict[str, Any], repository: dict[str, str]
) -> None:
    candidate = state.get("candidate_identity")
    if candidate is None:
        return
    if not isinstance(candidate, dict):
        raise CollaborationWakeupError("runner candidate identity must be an object")
    if candidate.get("commit") != repository["head"]:
        raise CollaborationWakeupError("runner candidate commit differs from current HEAD")
    if (
        repository["branch"] != "HEAD"
        and candidate.get("branch") != repository["branch"]
    ):
        raise CollaborationWakeupError("runner candidate branch differs from current branch")


def _snapshot_digest(result: dict[str, Any]) -> str:
    return _canonical_sha256(result)


def serialize_result(result: dict[str, Any]) -> str:
    """Return stable bytes for fixed inputs and a fixed observation time."""
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def inspect_once(
    *,
    repo: Path,
    spec_path: Path,
    state_path: Path,
    ledger_path: Path,
    comments_path: Path | None = None,
    stop_marker: Path | None = None,
    now: datetime,
    comments_fetcher: Callable[[dict[str, Any]], list[dict[str, Any]]] = github_control.fetch_issue_comments,
) -> dict[str, Any]:
    """Return one immutable readiness snapshot without changing external state."""
    if now.tzinfo is None:
        raise CollaborationWakeupError("observation time must be timezone-aware")
    repo = repo.resolve()
    paths = {
        "spec": spec_path.resolve(),
        "state": state_path.resolve(),
        "ledger": ledger_path.resolve(),
    }
    before = {name: _file_sha256(path) for name, path in paths.items()}
    repository = repository_identity(repo)
    spec = goal_continuity.load_json(paths["spec"])
    goal_continuity.validate_goal_spec(spec)
    if spec["goal_id"] in PROTECTED_GOAL_IDS:
        raise ProtectedGoalError(
            f"protected historical Goal {spec['goal_id']} cannot use the Issue #47 wakeup path"
        )
    if repository["repository"] != spec["repository"]:
        raise CollaborationWakeupError(
            "Goal repository differs from the current origin repository"
        )

    state = goal_continuity.load_json(paths["state"])
    ledger = goal_continuity.read_ledger(paths["ledger"])
    goal_continuity.validate_runner_state(state, spec)
    goal_continuity.validate_ledger_binding(ledger, state, spec)
    _assert_candidate_binding(state, repository)

    comments_digest: str | None = None
    if stop_marker is not None and stop_marker.exists():
        authority_summary = {
            "status": "NOT_READ_STOP_REQUESTED",
            "authority_lease": state["authority_lease"],
            "current_record": None,
            "valid_record_count": 0,
            "rejected_records": [],
        }
        planner = {
            "status": "STOP_MARKER",
            "requires_model": False,
            "reason": "an explicit stop marker is present",
        }
        status = "STOPPED"
    else:
        if comments_path is not None:
            try:
                comments = json.loads(comments_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CollaborationWakeupError("comments fixture is not valid JSON") from exc
        else:
            comments = comments_fetcher(spec)
        if not isinstance(comments, list):
            raise CollaborationWakeupError("GitHub comments input must be a JSON list")
        comments_digest = _canonical_sha256(comments)
        authority = github_control.resolve_authority(comments, spec)
        authority_summary = _authority_summary(authority)
        planner = goal_runner_adapter.next_action(
            spec,
            state,
            ledger,
            authority,
            now=now.astimezone(ZONE),
            trial=True,
        )
        status = public_status(planner)

    after = {name: _file_sha256(path) for name, path in paths.items()}
    if after != before:
        raise CollaborationWakeupError("one-shot input bytes changed during planning")
    if repository_identity(repo) != repository:
        raise CollaborationWakeupError("repository identity changed during planning")

    cursor = state["event_cursor"]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": now.astimezone(ZONE).isoformat(),
        "status": status,
        "source_status": planner.get("status"),
        "repository": repository,
        "goal": {
            "goal_id": spec["goal_id"],
            "goal_version": spec["goal_version"],
            "github_issue": spec["github_issue"],
            "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
            "spec_file_sha256": before["spec"],
            "state_sha256": before["state"],
            "ledger_sha256": before["ledger"],
            "ledger_cursor": {
                "sequence": cursor["sequence"],
                "event_sha256": cursor["event_sha256"],
            },
        },
        "authority": authority_summary,
        "comments_sha256": comments_digest,
        "planner": deepcopy(planner),
        "safety": deepcopy(SAFETY_ATTESTATION),
    }
    if status not in PUBLIC_STATUSES:  # pragma: no cover - defensive invariant
        raise CollaborationWakeupError(f"unsupported public status: {status}")
    result["snapshot_sha256"] = _snapshot_digest(result)
    return result


def blocked_result(message: str, *, now: datetime) -> dict[str, Any]:
    safety = deepcopy(SAFETY_ATTESTATION)
    safety["input_mutation_detected"] = "input bytes changed during planning" in message
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": now.astimezone(ZONE).isoformat(),
        "status": "BLOCKED",
        "source_status": "VALIDATION_ERROR",
        "error": {"message": message},
        "safety": safety,
    }
    result["snapshot_sha256"] = _snapshot_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--comments", type=Path)
    parser.add_argument("--stop-marker", type=Path)
    parser.add_argument("--now")
    args = parser.parse_args()
    try:
        observed = parse_observation_time(args.now)
        result = inspect_once(
            repo=args.repo,
            spec_path=args.spec,
            state_path=args.state,
            ledger_path=args.ledger,
            comments_path=args.comments,
            stop_marker=args.stop_marker,
            now=observed,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        observed = locals().get("observed")
        if not isinstance(observed, datetime):
            observed = datetime.now(ZONE)
        result = blocked_result(str(exc), now=observed)
        print(serialize_result(result), end="")
        return 2
    print(serialize_result(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
