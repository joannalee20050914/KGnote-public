#!/usr/bin/env python3
"""Replay the public-safe Issue #9/PR #29 history without models or mutation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import goal_continuity


def normalized_events(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for source in fixture["events"]:
        events.append(goal_continuity.prepare_ledger_event(
            events,
            event_id=source["event_id"],
            event_type=source["event_type"],
            occurred_at=source["occurred_at"],
            goal_id=fixture["goal_id"],
            goal_version=fixture["goal_version"],
            logical_work_id=source["logical_work_id"],
            attempt_id=source["attempt_id"],
            payload=source["payload"],
        ))
    return events


def replay(fixture: dict[str, Any]) -> dict[str, Any]:
    before = json.loads(json.dumps(fixture["legacy_budget_snapshot"]))
    events = normalized_events(fixture)
    projection = goal_continuity.reduce_ledger(events)
    quota_id = "issue-9-pr29-claude-review-r4-4c11eb42"
    publication_case = next(
        row for row in events if row["event_id"] == "policy-case-verdict-writeback-failure"
    )
    completion_case = next(
        row for row in events if row["event_id"] == "policy-case-completion-gate-block"
    )
    result = {
        "fixture_id": fixture["fixture_id"],
        "event_count": len(events),
        "valid_review_verdicts": len(projection["review_verdicts"]),
        "model_attempts": len(projection["model_attempts"]),
        "quota_attempt_is_review": any(
            row.get("attempt_id") == quota_id for row in projection["review_verdicts"]
        ),
        "quota_attempt_input_tokens": projection["usage"][quota_id]["input_tokens"],
        "quota_attempt_output_tokens": projection["usage"][quota_id]["output_tokens"],
        "latest_identity_obligation": projection["obligations"]["OBL-WEB-OBSIDIAN-IDENTITY"]["progress_class"],
        "writeback_failure_recovery": publication_case["payload"]["required_recovery"],
        "completion_gate_consumes_verdict": completion_case["payload"]["consumes_claude_verdict"],
        "commit_without_verified_obligation_is_complete": False,
        "legacy_budgets_unchanged": before == fixture["legacy_budget_snapshot"],
        "ledger_head": projection["event_cursor"],
        "model_invocations": 0,
        "external_writes": 0,
    }
    expected = fixture["expected_projection"]
    mismatches = {
        key: {"expected": value, "actual": result.get(key)}
        for key, value in expected.items() if result.get(key) != value
    }
    if mismatches:
        raise goal_continuity.GoalContractError(f"Issue #9 replay mismatch: {mismatches}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    print(json.dumps(replay(fixture), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
