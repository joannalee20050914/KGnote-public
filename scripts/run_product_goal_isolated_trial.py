#!/usr/bin/env python3
"""Run B-scheme paths A/B entirely in memory with no model or external writes."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import github_product_goal_control as github_control
import goal_continuity
import goal_notifications
import goal_runner_adapter
import replay_issue9_goal_history


ZONE = ZoneInfo("Asia/Taipei")
FIXED_NOW = datetime(2026, 10, 22, 10, 0, tzinfo=ZONE)


def owner_comment(spec: dict) -> dict:
    payload = {
        "schema_version": "kgnote.product-goal-authority-command.v1",
        "action": "APPROVE",
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "permissions": spec["allowed_operations"],
    }
    return {
        "id": 1,
        "html_url": "https://example.invalid/kgnote-isolated-trial/issues/1#issuecomment-1",
        "issue_url": "https://api.example.invalid/repos/example.invalid/kgnote-isolated-trial/issues/1",
        "created_at": "2026-10-22T02:00:00Z",
        "author_association": "OWNER",
        "user": {"login": "isolated-owner-fixture"},
        "body": (
            github_control.MARKER + "\n```json\n"
            + json.dumps(payload, sort_keys=True) + "\n```"
        ),
    }


def ledger_event(events: list[dict], spec: dict, event_id: str, event_type: str, payload: dict):
    events.append(goal_continuity.prepare_ledger_event(
        events, event_id=event_id, event_type=event_type,
        occurred_at=FIXED_NOW.isoformat(), goal_id=spec["goal_id"],
        goal_version=spec["goal_version"], logical_work_id="WI-TRIAL-IMPLEMENT",
        attempt_id=None, payload=payload,
    ))


def run_trial(spec: dict, backlog: dict, issue9_fixture: dict) -> dict:
    goal_continuity.validate_goal_spec(spec)
    authority = github_control.resolve_authority([owner_comment(spec)], spec)
    state = goal_continuity.initial_runner_state(
        spec, now=FIXED_NOW.isoformat(),
        codex_app_goal_provenance={
            "goal_id": "CODEX-APP-GOAL-B-CONTINUOUS-DELEGATION-20261022",
            "status": "complete",
            "authority_effect": "NONE",
        },
    )
    record = authority["record"]
    state.update({
        "authority_record": deepcopy(record),
        "authority_lease": "ACTIVE",
        "go_live_authorized": True,
        "lifecycle": {
            "state": "ACTIVE", "revision": 1, "changed_at": FIXED_NOW.isoformat(),
            "reason": "isolated fixture only; no production authority",
        },
    })
    events: list[dict] = []
    ledger_event(events, spec, "isolated-go-live", "GOAL_AUTHORITY_VERIFIED", {
        "go_live_authorized": True,
        "authority_comment_id": record["comment_id"],
        "authority_body_sha256": record["body_sha256"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "fixture_only": True,
    })

    path_a = {}
    path_a["initial"] = goal_runner_adapter.next_action(
        spec, state, events, authority, now=FIXED_NOW, trial=True
    )
    quota_state = deepcopy(state)
    quota_state["runtime_block"] = {"failure_class": "USAGE_LIMIT_REACHED"}
    path_a["quota"] = goal_runner_adapter.next_action(
        spec, quota_state, events, authority, now=FIXED_NOW, trial=True
    )
    unknown_state = deepcopy(state)
    unknown_state["runtime_block"] = {"failure_class": "UNKNOWN_OUTCOME"}
    path_a["unknown_result"] = goal_runner_adapter.next_action(
        spec, unknown_state, events, authority, now=FIXED_NOW, trial=True
    )
    repair_state = deepcopy(state)
    repair_state["runtime_block"] = {"failure_class": "CHANGES_REQUIRED"}
    repair_state["work_items"][0]["status"] = "REPAIR_REQUIRED"
    path_a["changes_required"] = goal_runner_adapter.next_action(
        spec, repair_state, events, authority, now=FIXED_NOW, trial=True
    )
    path_a["next_window"] = goal_runner_adapter.next_action(
        spec, state, events, authority,
        now=datetime(2026, 10, 22, 20, 0, tzinfo=ZONE), trial=True,
    )

    first_goal = backlog["items"][0]["goal_id"]
    path_b = goal_continuity.select_next_backlog_goal(
        backlog,
        closed_goal_ids={first_goal},
        resolved_external_dependencies={"LEGACY-ISSUE-9-DISPOSITION"},
    )
    notice_a = goal_notifications.build_notification(
        goal_id=path_b["goal_id"], goal_version=path_b["goal_version"],
        event_kind="NEXT_GOAL_APPROVAL_REQUIRED", decision_key=path_b["goal_version"],
        summary="前一 Goal 已結案；下一 Goal 等待核准。",
        decision_requested="核准、延後或要求調整。", github_issue=1,
    )
    notice_b = goal_notifications.build_notification(
        goal_id=path_b["goal_id"], goal_version=path_b["goal_version"],
        event_kind="NEXT_GOAL_APPROVAL_REQUIRED", decision_key=path_b["goal_version"],
        summary="前一 Goal 已結案；下一 Goal 等待核准。",
        decision_requested="核准、延後或要求調整。", github_issue=1,
    )
    replay = replay_issue9_goal_history.replay(issue9_fixture)
    checks = {
        "path_a_initial_trial_action": path_a["initial"]["status"] == "TRIAL_ACTION_READY",
        "path_a_quota_waits_without_model": path_a["quota"]["status"] == "WAIT_QUOTA_BACKOFF" and not path_a["quota"]["requires_model"],
        "path_a_unknown_reconciles_without_model": path_a["unknown_result"]["action"] == "RECONCILE_CHECKPOINT" and not path_a["unknown_result"]["requires_model"],
        "path_a_changes_required_routes_repair": path_a["changes_required"]["action"] == "DISPATCH_REPAIR",
        "path_a_cross_window_waits": path_a["next_window"]["status"] == "WAIT_WORK_WINDOW",
        "path_b_next_goal_waits_owner": path_b["status"] == "APPROVAL_REQUIRED" and not path_b["authority_granted"],
        "notification_dedup_identity_stable": notice_a["notification_id"] == notice_b["notification_id"],
        "chatgpt_work_unverified_github_fallback": notice_a["chatgpt_work_status"] == "UNVERIFIED" and notice_a["transport"] == "GITHUB_NATIVE",
        "legacy_replay_preserves_budget": replay["legacy_budgets_unchanged"],
        "legacy_quota_attempt_not_review": not replay["quota_attempt_is_review"],
    }
    if not all(checks.values()):
        raise goal_continuity.GoalContractError(
            f"isolated trial failed: {[key for key, value in checks.items() if not value]}"
        )
    return {
        "schema_version": "kgnote.b-scheme-isolated-trial-result.v1",
        "executed_at": FIXED_NOW.isoformat(),
        "fixture_repository": spec["repository"],
        "production_activation": False,
        "model_invocations": 0,
        "external_writes": 0,
        "path_a": path_a,
        "path_b": path_b,
        "notification": notice_a,
        "legacy_replay": replay,
        "checks": checks,
        "result": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--backlog", type=Path, required=True)
    parser.add_argument("--issue9-fixture", type=Path, required=True)
    args = parser.parse_args()
    result = run_trial(
        json.loads(args.spec.read_text(encoding="utf-8")),
        json.loads(args.backlog.read_text(encoding="utf-8")),
        json.loads(args.issue9_fixture.read_text(encoding="utf-8")),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
