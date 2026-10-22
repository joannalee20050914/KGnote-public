#!/usr/bin/env python3
"""Run B-scheme paths A/B entirely in memory with no model or external writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import github_product_goal_control as github_control
import goal_continuity
import goal_notifications
import goal_runner_adapter
import linux_worker_router
import replay_issue9_goal_history


ZONE = ZoneInfo("Asia/Taipei")
FIXED_NOW = datetime(2026, 10, 22, 10, 0, tzinfo=ZONE)


def owner_comment(spec: dict, *, action: str = "APPROVE", comment_id: int = 1) -> dict:
    payload = {
        "schema_version": "kgnote.product-goal-authority-command.v1",
        "action": action,
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "permissions": spec["allowed_operations"],
    }
    return {
        "id": comment_id,
        "html_url": f"https://example.invalid/kgnote-isolated-trial/issues/1#issuecomment-{comment_id}",
        "issue_url": "https://api.example.invalid/repos/example.invalid/kgnote-isolated-trial/issues/1",
        "created_at": f"2026-10-22T02:{comment_id:02d}:00Z",
        "author_association": "OWNER",
        "user": {"login": "isolated-owner-fixture"},
        "body": (
            github_control.MARKER + "\n```json\n"
            + json.dumps(payload, sort_keys=True) + "\n```"
        ),
    }


def _order(root: Path, event_id: str, stage: str) -> tuple[Path, dict]:
    order_path = root / f"{event_id}.json"
    value = {
        "schema_version": "kgnote.linux-worker-order.v1", "event_id": event_id,
        "stage": stage,
        "working_directory": f"/home/kgnote/.local/share/kgnote/work-items/{event_id}",
        "command": ["/usr/bin/true"],
        "checkpoint_path": str(root / f"{event_id}-checkpoint.json"),
    }
    order_path.write_text(json.dumps(value), encoding="utf-8")
    return order_path, value


def _binding(root: Path, order_path: Path, order: dict) -> dict:
    return {
        "order_path": str(order_path.relative_to(root)),
        "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
        "order_event_id": order["event_id"],
    }


def _worker_result(
    spec: dict, order: dict, *, work_item_id: str, outcome: str,
    progress_class: str, verdict: str | None,
) -> dict:
    return {
        "schema_version": "kgnote.product-goal-worker-result.v1",
        "goal_id": spec["goal_id"], "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "work_item_id": work_item_id, "order_event_id": order["event_id"],
        "outcome": outcome,
        "obligation_evaluations": [{
            "obligation_id": "OBL-TRIAL-CONTINUITY",
            "progress_class": progress_class, "evidence_sha256": "e" * 64,
        }],
        "usage": {
            "status": "UNKNOWN", "input_tokens": None, "output_tokens": None,
            "source": "isolated_fixture_no_model",
        },
        "review_verdict": (
            {"review_id": f"isolated-{verdict.lower()}", "verdict": verdict,
             "candidate_identity_sha256": "f" * 64}
            if verdict else None
        ),
        "publication": None,
    }


def _write_checkpoint(order: dict, *, status: str, result: dict | None = None,
                      failure_class: str | None = None) -> None:
    evidence = (
        {"product_goal_result": result}
        if result else {
            "failure_class": failure_class,
            "token_usage": {
                "input_tokens": 0, "output_tokens": 0,
                "source": "isolated_429_checkpoint",
            },
        }
    )
    checkpoint = {
        "schema_version": "kgnote.linux-worker-route.v1", "status": status,
        "reason": None if status == "COMPLETED" else "guest_worker_failed",
        "event_id": order["event_id"],
        "command_digest": linux_worker_router.command_digest(
            linux_worker_router.WorkerOrder.from_dict(order)
        ),
        "execution_evidence": evidence,
    }
    Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")


def _dispatch_and_reconcile(
    spec: dict, authority: dict, root: Path, state_path: Path, ledger_path: Path,
    *, now: datetime, order: dict, result: dict | None = None,
    failure_class: str | None = None,
) -> tuple[dict, dict]:
    state = goal_continuity.load_json(state_path)
    action = goal_runner_adapter.next_action(
        spec, state, goal_continuity.read_ledger(ledger_path), authority,
        now=now, trial=False,
    )
    quota_resume = None
    if (
        action.get("status") == "RECOVERY_READY"
        and action.get("action") == "RESUME_AFTER_QUOTA"
    ):
        quota_resume = goal_runner_adapter.resume_after_quota_backoff(
            spec, state, state_path=state_path, ledger_path=ledger_path, now=now,
        )
        state = goal_continuity.load_json(state_path)
        action = goal_runner_adapter.next_action(
            spec, state, goal_continuity.read_ledger(ledger_path), authority,
            now=now, trial=False,
        )
        action = {**action, "pre_dispatch_recovery": quota_resume}
    reserved, _, attempt_id = goal_runner_adapter.reserve_dispatch(
        spec, state, action, state_path=state_path, ledger_path=ledger_path,
        repo=root, occurred_at=now.isoformat(),
    )
    status = "COMPLETED" if result else "FAILED_CLOSED"
    _write_checkpoint(order, status=status, result=result, failure_class=failure_class)
    routed = goal_runner_adapter.record_route_outcome(
        spec, reserved, state_path=state_path, work_item_id=action["work_item_id"],
        attempt_id=attempt_id, route_exit_code=0 if result else 2,
        occurred_at=now.isoformat(),
    )
    reconciled = goal_runner_adapter.reconcile_dispatch_checkpoint(
        spec, routed, state_path=state_path, ledger_path=ledger_path, repo=root,
        attempt_id=attempt_id, occurred_at=now.isoformat(),
    )
    return action, reconciled


def run_trial(spec: dict, backlog: dict, issue9_fixture: dict) -> dict:
    goal_continuity.validate_goal_spec(spec)
    approval = owner_comment(spec)
    authority = github_control.resolve_authority([approval], spec)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        review_one_path, review_one = _order(root, "isolated-review-one", "claude")
        review_two_path, review_two = _order(root, "isolated-review-two", "claude")
        repair_path, repair_order = _order(root, "isolated-repair-one", "codex")
        state = goal_continuity.initial_runner_state(
            spec, now=FIXED_NOW.isoformat(),
            codex_app_goal_provenance={
                "goal_id": "CODEX-APP-GOAL-B-CONTINUOUS-DELEGATION-20261022",
                "status": "complete", "authority_effect": "NONE",
            },
        )
        state["work_items"][0]["dispatch_bindings"] = {
            "DISPATCH_REVIEW": [
                _binding(root, review_one_path, review_one),
                _binding(root, review_two_path, review_two),
            ]
        }
        state["work_items"][1]["dispatch_bindings"] = {
            "DISPATCH_REPAIR": [_binding(root, repair_path, repair_order)]
        }
        state_path, ledger_path = root / "state.json", root / "ledger.jsonl"
        goal_continuity.atomic_write_json(state_path, state)
        active = goal_runner_adapter.reconcile_owner_authority(
            spec, state, authority, state_path=state_path, ledger_path=ledger_path,
        )["state"]

        path_a: dict[str, dict] = {
            "authority": {"lifecycle": active["lifecycle"]["state"], "lease": active["authority_lease"]}
        }
        first_action, quota = _dispatch_and_reconcile(
            spec, authority, root, state_path, ledger_path, now=FIXED_NOW,
            order=review_one, failure_class="USAGE_LIMIT_REACHED",
        )
        path_a["initial"] = first_action
        path_a["quota"] = quota
        quota_wait = goal_runner_adapter.next_action(
            spec, goal_continuity.load_json(state_path), goal_continuity.read_ledger(ledger_path),
            authority, now=FIXED_NOW, trial=False,
        )
        path_a["quota_wait"] = quota_wait
        next_window = goal_runner_adapter.next_action(
            spec, goal_continuity.load_json(state_path), goal_continuity.read_ledger(ledger_path),
            authority, now=datetime(2026, 10, 23, 8, 0, tzinfo=ZONE), trial=False,
        )
        path_a["next_window"] = next_window

        changes_result = _worker_result(
            spec, review_one, work_item_id="WI-TRIAL-REVIEW",
            outcome="REVIEW_CHANGES_REQUIRED", progress_class="NO_OBLIGATION_PROGRESS",
            verdict="CHANGES_REQUIRED",
        )
        changes_action, changes = _dispatch_and_reconcile(
            spec, authority, root, state_path, ledger_path,
            now=datetime(2026, 10, 23, 10, 5, tzinfo=ZONE),
            order=review_one, result=changes_result,
        )
        path_a["changes_required"] = {"action": changes_action, "result": changes}
        repair_result = _worker_result(
            spec, repair_order, work_item_id="WI-TRIAL-REPAIR",
            outcome="WORK_COMPLETED", progress_class="FUNCTIONAL_PROGRESS_UNVERIFIED",
            verdict=None,
        )
        repair_action, repair = _dispatch_and_reconcile(
            spec, authority, root, state_path, ledger_path,
            now=datetime(2026, 10, 23, 10, 15, tzinfo=ZONE),
            order=repair_order, result=repair_result,
        )
        path_a["repair"] = {"action": repair_action, "result": repair}
        pass_result = _worker_result(
            spec, review_two, work_item_id="WI-TRIAL-REVIEW",
            outcome="REVIEW_PASS", progress_class="VERIFIED_RESOLVED", verdict="PASS",
        )
        pass_action, passed = _dispatch_and_reconcile(
            spec, authority, root, state_path, ledger_path,
            now=datetime(2026, 10, 23, 10, 25, tzinfo=ZONE),
            order=review_two, result=pass_result,
        )
        path_a["review_pass"] = {"action": pass_action, "result": passed}
        accepted_authority = github_control.resolve_authority(
            [approval, owner_comment(spec, action="ACCEPT", comment_id=2)], spec
        )
        closed = goal_runner_adapter.reconcile_owner_authority(
            spec, goal_continuity.load_json(state_path), accepted_authority,
            state_path=state_path, ledger_path=ledger_path,
        )["state"]
        path_a["closed"] = {"lifecycle": closed["lifecycle"]["state"]}
        path_b = goal_runner_adapter.prepare_next_goal_handoff(
            backlog, closed, ledger_path=ledger_path,
            occurred_at=datetime(2026, 10, 23, 10, 30, tzinfo=ZONE).isoformat(),
            github_issue=spec["github_issue"],
        )
        events = goal_continuity.read_ledger(ledger_path)
        projection = goal_continuity.reduce_ledger(events)

    notice_a = path_b["notification"]
    notice_b = goal_notifications.build_notification(
        goal_id=path_b["goal_id"], goal_version=path_b["goal_version"],
        event_kind="NEXT_GOAL_APPROVAL_REQUIRED", decision_key=path_b["goal_version"],
        summary=notice_a["summary"],
        decision_requested=notice_a["decision_requested"], github_issue=1,
    )
    replay = replay_issue9_goal_history.replay(issue9_fixture)
    checks = {
        "path_a_owner_approval_activates_runner": path_a["authority"] == {"lifecycle": "ACTIVE", "lease": "ACTIVE"},
        "path_a_initial_review_dispatched": path_a["initial"]["action"] == "DISPATCH_REVIEW",
        "path_a_quota_is_reconciled_attempt": path_a["quota"]["outcome"] == "USAGE_LIMIT_REACHED",
        "path_a_quota_waits_without_model": path_a["quota_wait"]["status"] == "WAIT_QUOTA_BACKOFF" and not path_a["quota_wait"]["requires_model"],
        "path_a_quota_resume_is_durable_no_model": (
            path_a["changes_required"]["action"].get("pre_dispatch_recovery", {}).get("status")
            == "QUOTA_BACKOFF_RESUMED"
            and not path_a["changes_required"]["action"]["pre_dispatch_recovery"]["requires_model"]
            and sum(
                row["payload"].get("operation") == "QUOTA_BACKOFF_RESUMED"
                for row in events
            ) == 1
        ),
        "path_a_cross_window_waits": path_a["next_window"]["status"] == "WAIT_WORK_WINDOW",
        "path_a_changes_required_routes_repair": path_a["repair"]["action"]["action"] == "DISPATCH_REPAIR",
        "path_a_review_pass_reaches_acceptance": path_a["review_pass"]["result"]["lifecycle"] == "ACCEPTANCE_REQUIRED",
        "path_a_exact_owner_accept_closes": path_a["closed"]["lifecycle"] == "CLOSED",
        "path_a_accounting_separate": len(projection["model_attempts"]) == 4 and len(projection["review_verdicts"]) == 2,
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
        "goal_ledger": {
            "event_count": projection["event_count"],
            "model_attempts": len(projection["model_attempts"]),
            "valid_review_verdicts": len(projection["review_verdicts"]),
            "notifications": len(projection["notifications"]),
            "final_lifecycle": path_a["closed"]["lifecycle"],
        },
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
