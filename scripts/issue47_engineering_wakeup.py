#!/usr/bin/env python3
"""No-model admission gate for the single Issue #47 engineering wakeup.

The scheduler runs this program before any Codex or Claude command.  It reads
the exact Owner authority, work window, cumulative accounting, review state,
Stop Marker, writer lock, provider backoff, and the paused Codex App heartbeat.
Only an atomic, duplicate-suppressed reservation may authorize a later model
command.  This module never launches a model itself.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import tempfile
import tomllib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo


ZONE = ZoneInfo("Asia/Taipei")
GOAL_ID = "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION"
GOAL_VERSION = "2026-10-31.4-engineering-continuation-simplification"
GOAL_SPEC_SHA256 = "0507d2dbc5c9780afbe3e67a3c8ca66f8fb1b93eff9507c86299baac0141ad5d"
OWNER_COMMENT_ID = 6538300483
OWNER_LOGIN = "joannalee20050914"
AUTHORITY_MARKER = "<!-- kgnote-codex-app-engineering-goal-authority:v1 -->"
HEARTBEAT_ID = "kgnote-47-goal"
SCHEMA_VERSION = "kgnote.issue47-engineering-wakeup.v1"
STATE_SCHEMA_VERSION = "kgnote.issue47-engineering-wakeup-state.v2"
LEGACY_STATE_SCHEMA_VERSION = "kgnote.issue47-engineering-wakeup-state.v1"
DISPATCH_STATUSES = {"RESERVED", "RUNNING", "COMPLETED", "FAILED"}
CONTINUATION_BINDINGS = {
    ("READY_FOR_REVIEW", "READY_FOR_AI_REVIEW"): ("DISPATCH_REVIEW", "claude"),
    ("IMPLEMENTING", "IMPLEMENTING"): ("DISPATCH_IMPLEMENTATION", "codex"),
    ("IMPLEMENTING", "REPAIRING"): ("DISPATCH_IMPLEMENTATION", "codex"),
    ("CHANGES_REQUIRED", "REPAIRING"): ("DISPATCH_IMPLEMENTATION", "codex"),
}


class WakeupError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise WakeupError(f"{label} is absent or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WakeupError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise WakeupError(f"{label} root must be an object")
    return value


def embedded_json(path: Path, begin: str, end: str, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise WakeupError(f"{label} is absent or not a regular file")
    text = path.read_text(encoding="utf-8")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise WakeupError(f"{label} has invalid structured markers")
    body = text.split(begin, 1)[1].split(end, 1)[0]
    match = re.search(r"```json\s*(.*?)\s*```", body, re.DOTALL)
    if match is None:
        raise WakeupError(f"{label} lacks structured JSON")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise WakeupError(f"{label} structured JSON is invalid") from exc
    if not isinstance(value, dict):
        raise WakeupError(f"{label} structured JSON must be an object")
    return value


def parse_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(ZONE)
    try:
        observed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise WakeupError("--now must be ISO-8601") from exc
    if observed.tzinfo is None:
        raise WakeupError("--now must include an offset")
    return observed.astimezone(ZONE)


def within_work_window(spec: dict[str, Any], now: datetime) -> bool:
    period = spec.get("work_period")
    if not isinstance(period, dict) or period.get("timezone") != "Asia/Taipei":
        raise WakeupError("spec work period is unavailable")
    start = datetime.fromisoformat(str(period.get("start"))).astimezone(ZONE)
    end = datetime.fromisoformat(str(period.get("end"))).astimezone(ZONE)
    if not start <= now < end:
        return False
    local_date = now.date().isoformat()
    for window in period.get("exception_work_windows", []):
        if not isinstance(window, dict) or window.get("date") != local_date:
            continue
        if window.get("scope") != "ISSUE47_INFRA_ENGINEERING_ONLY":
            raise WakeupError("exception window scope differs")
        return str(window["start"]) <= now.strftime("%H:%M") < str(window["end"])
    if now.weekday() not in period.get("weekdays", []):
        return False
    return str(period["daily_start"]) <= now.strftime("%H:%M") < str(period["daily_end"])


def _parse_authority_body(body: str) -> dict[str, Any]:
    if body.count(AUTHORITY_MARKER) != 1:
        raise WakeupError("Owner authority marker differs")
    match = re.search(
        re.escape(AUTHORITY_MARKER) + r"\s*```json\s*(\{.*?\})\s*```",
        body,
        re.DOTALL,
    )
    if match is None:
        raise WakeupError("Owner authority command is missing")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise WakeupError("Owner authority command is invalid JSON") from exc
    if not isinstance(value, dict):
        raise WakeupError("Owner authority command must be an object")
    return value


def fetch_authority(
    spec: dict[str, Any],
    *,
    fixture: Path | None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    if fixture is not None:
        comment = load_object(fixture, "Owner authority fixture")
    else:
        completed = command_runner(
            [
                "/opt/homebrew/bin/gh",
                "api",
                f"repos/{spec['repository']}/issues/comments/{OWNER_COMMENT_ID}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise WakeupError("GitHub Owner authority read-back failed")
        try:
            comment = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise WakeupError("GitHub Owner authority read-back is invalid") from exc
        if not isinstance(comment, dict):
            raise WakeupError("GitHub Owner authority read-back must be an object")
    if (
        comment.get("id") != OWNER_COMMENT_ID
        or comment.get("author_association") != "OWNER"
        or not isinstance(comment.get("user"), dict)
        or comment["user"].get("login") != OWNER_LOGIN
    ):
        raise WakeupError("GitHub Owner authority identity differs")
    command = _parse_authority_body(str(comment.get("body", "")))
    providers = spec["resource_policy"]["providers"]
    expected = {
        "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
        "action": "APPROVE",
        "goal_id": GOAL_ID,
        "goal_version": GOAL_VERSION,
        "goal_spec_sha256": GOAL_SPEC_SHA256,
        "permissions": spec["allowed_operations"],
        "product_goal_coexistence": spec["product_goal_coexistence"]["policy"],
        "product_goal_authorized": False,
        "standing_b_scheme_go_live_authorized": False,
    }
    for key, value in expected.items():
        if command.get(key) != value:
            raise WakeupError(f"Owner authority {key} differs")
    resources = command.get("resource_acknowledgement")
    if not isinstance(resources, dict):
        raise WakeupError("Owner authority resources are missing")
    resource_expected = {
        "max_model_concurrency": 1,
        "codex_max_per_workday": providers["codex"]["max_launches_per_workday"],
        "codex_max_total": providers["codex"]["max_total_launches"],
        "codex_known_preapproval": providers["codex"]["known_preapproval_launches"],
        "claude_max_per_workday": providers["claude"]["max_launches_per_workday"],
        "claude_max_total": providers["claude"]["max_total_launches"],
        "claude_known_preapproval": providers["claude"]["known_preapproval_launches"],
        "paid_api_fallback": False,
        "history_reset_forbidden": True,
    }
    for key, value in resource_expected.items():
        if resources.get(key) != value:
            raise WakeupError(f"Owner authority resource {key} differs")
    return {
        "comment_id": OWNER_COMMENT_ID,
        "comment_url": comment.get("html_url"),
        "body_sha256": hashlib.sha256(str(comment["body"]).encode()).hexdigest(),
        "command_sha256": canonical_sha256(command),
    }


def load_heartbeat(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise WakeupError("Codex heartbeat definition is unavailable")
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise WakeupError("Codex heartbeat definition is invalid") from exc
    if value.get("id") != HEARTBEAT_ID or value.get("status") != "PAUSED":
        raise WakeupError("Codex heartbeat must be the exact paused Issue #47 task")
    return {"id": HEARTBEAT_ID, "status": "PAUSED", "updated_at": value.get("updated_at")}


def action_identity(
    status: dict[str, Any], orchestrator: dict[str, Any], request: dict[str, Any]
) -> tuple[str, str, str | None]:
    review_state = request.get("status")
    binding = continuation_binding(review_state, orchestrator.get("state"))
    if binding is None:
        raise WakeupError(
            f"review/orchestrator state pair {review_state!r}/"
            f"{orchestrator.get('state')!r} is not wakeable"
        )
    return (*binding, str(request.get("review_id")))


def continuation_binding(
    review_state: Any, orchestrator_state: Any,
) -> tuple[str, str] | None:
    """Return the one action/provider pair both admission and continuation accept."""
    return CONTINUATION_BINDINGS.get((review_state, orchestrator_state))


def _usage(
    status: dict[str, Any], provider: str,
) -> tuple[int, int, int, int, str]:
    policy = status.get("resource_accounting", {}).get(provider)
    if not isinstance(policy, dict):
        raise WakeupError(f"{provider} accounting is missing")
    fields = (
        policy.get("consumed_total_conservative"),
        policy.get("current_workday_launches"),
        policy.get("ceiling"),
        policy.get("daily_ceiling"),
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in fields):
        raise WakeupError(f"{provider} accounting is not exact")
    workday = policy.get("current_workday")
    if not isinstance(workday, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", workday):
        raise WakeupError(f"{provider} accounting workday is not exact")
    return (*fields, workday)  # type: ignore[return-value]


def _runtime_identity(status: dict[str, Any]) -> tuple[str, str]:
    git = status.get("git")
    working = status.get("working_state")
    if not isinstance(git, dict) or not isinstance(working, dict):
        raise WakeupError("runtime candidate identity is missing")
    commit = git.get("head")
    fingerprint = working.get("fingerprint")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise WakeupError("runtime candidate commit is not exact")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise WakeupError("runtime candidate fingerprint is not exact")
    return commit, fingerprint


def _new_history(status: dict[str, Any]) -> dict[str, Any]:
    baseline: dict[str, Any] = {}
    for provider in ("codex", "claude"):
        total, today, total_limit, daily_limit, workday = _usage(status, provider)
        baseline[provider] = {
            "consumed_total": total,
            "workday": workday,
            "workday_launches": today,
            "total_limit": total_limit,
            "daily_limit": daily_limit,
        }
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "goal_id": GOAL_ID,
        "goal_version": GOAL_VERSION,
        "accounting_baseline": baseline,
        "dispatches": [],
        "events": [],
    }


def _migrate_legacy_state(
    legacy: dict[str, Any], status: dict[str, Any], now: datetime,
) -> dict[str, Any]:
    if legacy.get("schema_version") != LEGACY_STATE_SCHEMA_VERSION:
        raise WakeupError("wakeup state schema differs")
    old_status = legacy.get("status")
    if old_status not in DISPATCH_STATUSES:
        raise WakeupError("legacy wakeup state status is invalid")
    dispatch_key = legacy.get("dispatch_key")
    provider = legacy.get("provider")
    action = legacy.get("action")
    if not isinstance(dispatch_key, str) or not re.fullmatch(r"[0-9a-f]{64}", dispatch_key):
        raise WakeupError("legacy wakeup dispatch key is invalid")
    if provider not in {"codex", "claude"} or action not in {
        "DISPATCH_IMPLEMENTATION", "DISPATCH_REVIEW",
    }:
        raise WakeupError("legacy wakeup dispatch identity is invalid")
    history = _new_history(status)
    workday = str(legacy.get("reserved_at", now.isoformat()))[:10]
    history["migrated_from"] = LEGACY_STATE_SCHEMA_VERSION
    history["dispatches"].append({
        "dispatch_key": dispatch_key,
        "goal_id": legacy.get("goal_id", GOAL_ID),
        "goal_version": legacy.get("goal_version", GOAL_VERSION),
        "action": action,
        "provider": provider,
        "review_id": legacy.get("review_id"),
        "candidate_commit": legacy.get("candidate_commit"),
        "candidate_fingerprint": legacy.get("candidate_fingerprint"),
        "charged_at": legacy.get("reserved_at", now.isoformat()),
        "workday": workday,
        "usage_charge": 1,
        "accounting_included_in_baseline": True,
    })
    history["events"].append({
        "dispatch_key": dispatch_key,
        "status": "RESERVED",
        "observed_at": legacy.get("reserved_at", now.isoformat()),
        "model_launch_started": False,
        "continuation_exit_code": None,
    })
    if old_status in {"RUNNING", "COMPLETED", "FAILED"} and legacy.get("running_at"):
        history["events"].append({
            "dispatch_key": dispatch_key,
            "status": "RUNNING",
            "observed_at": legacy["running_at"],
            "model_launch_started": True,
            "continuation_exit_code": None,
        })
    if old_status in {"COMPLETED", "FAILED"} or (
        old_status == "RUNNING" and not legacy.get("running_at")
    ):
        history["events"].append({
            "dispatch_key": dispatch_key,
            "status": old_status,
            "observed_at": legacy.get(
                f"{str(old_status).lower()}_at", now.isoformat()
            ),
            "model_launch_started": True,
            "continuation_exit_code": legacy.get("continuation_exit_code"),
        })
    return history


def _validated_history(
    existing: dict[str, Any] | None, status: dict[str, Any], now: datetime,
) -> tuple[dict[str, Any], dict[str, str]]:
    history = _new_history(status) if existing is None else (
        _migrate_legacy_state(existing, status, now)
        if existing.get("schema_version") == LEGACY_STATE_SCHEMA_VERSION
        else existing
    )
    if (
        history.get("schema_version") != STATE_SCHEMA_VERSION
        or history.get("goal_id") != GOAL_ID
        or history.get("goal_version") != GOAL_VERSION
    ):
        raise WakeupError("wakeup history identity differs")
    baseline = history.get("accounting_baseline")
    dispatches = history.get("dispatches")
    events = history.get("events")
    if not isinstance(baseline, dict) or not isinstance(dispatches, list) or not isinstance(events, list):
        raise WakeupError("wakeup history structure differs")
    for provider in ("codex", "claude"):
        total, today, total_limit, daily_limit, workday = _usage(status, provider)
        expected = {
            "consumed_total": total,
            "workday": workday,
            "workday_launches": today,
            "total_limit": total_limit,
            "daily_limit": daily_limit,
        }
        if baseline.get(provider) != expected:
            raise WakeupError(f"{provider} accounting baseline drifted")
    by_key: dict[str, dict[str, Any]] = {}
    for item in dispatches:
        if not isinstance(item, dict):
            raise WakeupError("dispatch history contains a non-object")
        key = item.get("dispatch_key")
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key) or key in by_key:
            raise WakeupError("dispatch history key is invalid or duplicated")
        if item.get("provider") not in {"codex", "claude"} or item.get("usage_charge") != 1:
            raise WakeupError("dispatch history charge is invalid")
        if not isinstance(item.get("workday"), str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", item["workday"]
        ):
            raise WakeupError("dispatch history workday is invalid")
        by_key[key] = item
    latest: dict[str, str] = {}
    for event in events:
        if not isinstance(event, dict) or event.get("dispatch_key") not in by_key:
            raise WakeupError("dispatch event identity is invalid")
        observed_at = event.get("observed_at")
        if not isinstance(observed_at, str):
            raise WakeupError("dispatch event timestamp is missing")
        try:
            observed = datetime.fromisoformat(observed_at)
        except ValueError as exc:
            raise WakeupError("dispatch event timestamp is invalid") from exc
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise WakeupError("dispatch event timestamp must include an offset")
        key = str(event["dispatch_key"])
        new = event.get("status")
        if new not in DISPATCH_STATUSES:
            raise WakeupError("dispatch event status is invalid")
        old = latest.get(key)
        allowed = old is None and new == "RESERVED" or (
            old == "RESERVED" and new in {"RUNNING", "COMPLETED", "FAILED"}
        ) or (old == "RUNNING" and new in {"COMPLETED", "FAILED"})
        if not allowed:
            raise WakeupError("dispatch event transition is invalid")
        latest[key] = str(new)
    if set(latest) != set(by_key):
        raise WakeupError("dispatch history is missing a reservation event")
    return history, latest


def _effective_usage(
    history: dict[str, Any], provider: str, workday: str,
) -> tuple[int, int, int, int]:
    baseline = history["accounting_baseline"][provider]
    chargeable = [
        item for item in history["dispatches"]
        if item["provider"] == provider and item.get("accounting_included_in_baseline") is not True
    ]
    total = int(baseline["consumed_total"]) + len(chargeable)
    today = (
        int(baseline["workday_launches"])
        if baseline["workday"] == workday else 0
    ) + sum(item["workday"] == workday for item in chargeable)
    return total, today, int(baseline["total_limit"]), int(baseline["daily_limit"])


def _active_provider_backoff(
    orchestrator: dict[str, Any], provider: str, now: datetime
) -> str | None:
    for blocker in orchestrator.get("blockers", []):
        if not isinstance(blocker, dict):
            continue
        blocker_type = str(blocker.get("type", ""))
        if "daily_budget" in blocker_type:
            continue
        if provider not in blocker_type and blocker.get("provider") != provider:
            continue
        retry = blocker.get("retry_at") or blocker.get("backoff_until")
        if isinstance(retry, str) and datetime.fromisoformat(retry).astimezone(ZONE) > now:
            return retry
    return None


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise WakeupError("writer lock is not a regular file")
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WakeupError("another Issue #47 writer is active") from exc
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise WakeupError("wakeup state is not a regular file")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect(
    *,
    repo: Path,
    spec_path: Path,
    heartbeat_path: Path,
    state_path: Path,
    writer_lock: Path,
    authority_fixture: Path | None,
    stop_marker: Path,
    now: datetime,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    reserve: bool = False,
) -> dict[str, Any]:
    safety = {
        "no_model_gate": True,
        "model_launch_started": False,
        "product_goal_dispatched": False,
        "legacy_o2_runner_used": False,
        "paid_api_used": False,
    }
    if stop_marker.exists() or stop_marker.is_symlink():
        return {"schema_version": SCHEMA_VERSION, "status": "STOPPED", "safety": safety}
    repo = repo.resolve()
    spec = load_object(spec_path, "v4 engineering Goal spec")
    if (
        spec.get("goal_id") != GOAL_ID
        or spec.get("goal_version") != GOAL_VERSION
        or canonical_sha256(spec) != GOAL_SPEC_SHA256
    ):
        raise WakeupError("v4 engineering Goal identity or digest differs")
    if not within_work_window(spec, now):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "WAITING_WORK_WINDOW",
            "observed_at": now.isoformat(),
            "safety": safety,
        }
    plan = embedded_json(
        repo / "PLAN.md", "<!-- BEGIN CODEX PLAN JSON -->",
        "<!-- END CODEX PLAN JSON -->", "PLAN",
    )
    status = embedded_json(
        repo / "CODEX_STATUS.md", "<!-- BEGIN CODEX STATUS JSON -->",
        "<!-- END CODEX STATUS JSON -->", "CODEX_STATUS",
    )
    if plan.get("goal_id") != GOAL_ID or status.get("goal_id") != GOAL_ID:
        raise WakeupError("PLAN/STATUS Goal identity differs")
    for source, label in ((plan, "PLAN"), (status, "CODEX_STATUS")):
        bound = source.get("goal_spec")
        if not isinstance(bound, dict):
            raise WakeupError(f"{label} lacks Goal spec binding")
        if (
            bound.get("version") != GOAL_VERSION
            or bound.get("canonical_sha256") != GOAL_SPEC_SHA256
        ):
            raise WakeupError(f"{label} is not bound to v4")
    orchestrator = load_object(repo / ".ai/ORCHESTRATOR_STATE.json", "orchestrator state")
    request = embedded_json(
        repo / ".ai/REVIEW_REQUEST.md", "<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->",
        "<!-- END KGNOTE REVIEW REQUEST JSON -->", "review request",
    )
    action, provider, review_id = action_identity(status, orchestrator, request)
    candidate_commit, fingerprint = _runtime_identity(status)
    if action == "DISPATCH_REVIEW":
        if request.get("candidate_fingerprint") != fingerprint:
            raise WakeupError("sealed review fingerprint differs from runtime identity")
        revision = str(request.get("candidate_revision", ""))
        if not revision.startswith(candidate_commit + "+worktree:" + fingerprint):
            raise WakeupError("sealed review revision differs from runtime identity")
    if orchestrator.get("active_goal") != GOAL_ID:
        raise WakeupError("orchestrator Goal identity differs")
    orchestrator_review_id = orchestrator.get("review_id")
    if orchestrator_review_id is not None and request.get("review_id") != orchestrator_review_id:
        raise WakeupError("review identity differs between request and orchestrator")
    heartbeat = load_heartbeat(heartbeat_path)
    authority = fetch_authority(spec, fixture=authority_fixture, command_runner=command_runner)
    static_total, static_today, total_limit, daily_limit, accounting_workday = _usage(
        status, provider
    )
    spec_provider = spec["resource_policy"]["providers"][provider]
    if total_limit != spec_provider["max_total_launches"] or daily_limit != spec_provider["max_launches_per_workday"]:
        raise WakeupError(f"{provider} local ceilings do not implement v4")
    dispatch_key = canonical_sha256({
        "goal_id": GOAL_ID,
        "goal_version": GOAL_VERSION,
        "action": action,
        "provider": provider,
        "review_id": review_id,
        "candidate_commit": candidate_commit,
        "candidate_fingerprint": fingerprint,
    })
    with exclusive_lock(writer_lock):
        existing = load_object(state_path, "wakeup state") if state_path.exists() else None
        history, latest = _validated_history(existing, status, now)
        consumed, today, _, _ = _effective_usage(history, provider, now.date().isoformat())
        if consumed < static_total or (
            accounting_workday == now.date().isoformat() and today < static_today
        ):
            raise WakeupError("effective usage regressed below the durable baseline")
        if consumed >= total_limit or today >= daily_limit:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "WAITING_QUOTA",
                "provider": provider,
                "usage": {"total": consumed, "today": today, "total_limit": total_limit, "daily_limit": daily_limit},
                "safety": safety,
            }
        backoff = _active_provider_backoff(orchestrator, provider, now)
        if backoff is not None:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "WAITING_PROVIDER_BACKOFF",
                "provider": provider,
                "retry_at": backoff,
                "safety": safety,
            }
        by_key = {item["dispatch_key"]: item for item in history["dispatches"]}
        if dispatch_key in by_key:
            existing_status = latest[dispatch_key]
            if existing_status in DISPATCH_STATUSES:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "status": "WAITING_DUPLICATE",
                    "dispatch_key": dispatch_key,
                    "existing_dispatch_key": dispatch_key,
                    "existing_status": existing_status,
                    "safety": safety,
                }
        for existing_key, existing_status in latest.items():
            if existing_key != dispatch_key and existing_status in {"RESERVED", "RUNNING"}:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "status": "WAITING_ACTIVE_RESERVATION",
                    "dispatch_key": dispatch_key,
                    "existing_dispatch_key": existing_key,
                    "safety": safety,
                }
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "READY_TO_WAKE",
            "observed_at": now.isoformat(),
            "goal_id": GOAL_ID,
            "goal_version": GOAL_VERSION,
            "goal_spec_sha256": GOAL_SPEC_SHA256,
            "action": action,
            "provider": provider,
            "review_id": review_id,
            "candidate_commit": candidate_commit,
            "candidate_fingerprint": fingerprint,
            "dispatch_key": dispatch_key,
            "authority": authority,
            "heartbeat": heartbeat,
            "usage_before": {"total": consumed, "today": today, "total_limit": total_limit, "daily_limit": daily_limit},
            "safety": safety,
        }
        if reserve:
            reservation = {
                "dispatch_key": dispatch_key,
                "goal_id": GOAL_ID,
                "goal_version": GOAL_VERSION,
                "action": action,
                "provider": provider,
                "review_id": review_id,
                "candidate_commit": candidate_commit,
                "candidate_fingerprint": fingerprint,
                "charged_at": now.isoformat(),
                "workday": now.date().isoformat(),
                "usage_charge": 1,
                "accounting_included_in_baseline": False,
            }
            history["dispatches"].append(reservation)
            history["events"].append({
                "dispatch_key": dispatch_key,
                "status": "RESERVED",
                "observed_at": now.isoformat(),
                "model_launch_started": False,
                "continuation_exit_code": None,
            })
            _atomic_json(state_path, history)
            charged_total, charged_today, _, _ = _effective_usage(
                history, provider, now.date().isoformat()
            )
            result["status"] = "RESERVED"
            result["reservation_sha256"] = hashlib.sha256(state_path.read_bytes()).hexdigest()
            result["usage_after_charge"] = {
                "total": charged_total,
                "today": charged_today,
                "total_limit": total_limit,
                "daily_limit": daily_limit,
            }
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--writer-lock", type=Path, required=True)
    parser.add_argument("--authority-fixture", type=Path)
    parser.add_argument("--stop-marker", type=Path, required=True)
    parser.add_argument("--now")
    parser.add_argument("--reserve", action="store_true")
    args = parser.parse_args()
    try:
        result = inspect(
            repo=args.repo,
            spec_path=args.spec,
            heartbeat_path=args.heartbeat,
            state_path=args.state,
            writer_lock=args.writer_lock,
            authority_fixture=args.authority_fixture,
            stop_marker=args.stop_marker,
            now=parse_time(args.now),
            reserve=args.reserve,
        )
    except (OSError, ValueError, WakeupError) as exc:
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "BLOCKED",
            "error": str(exc),
            "safety": {
                "no_model_gate": True,
                "model_launch_started": False,
                "product_goal_dispatched": False,
                "legacy_o2_runner_used": False,
                "paid_api_used": False,
            },
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"READY_TO_WAKE", "RESERVED", "STOPPED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
