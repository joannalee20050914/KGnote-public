from __future__ import annotations

import fcntl
import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
MODULE_SPEC = importlib.util.spec_from_file_location(
    "issue47_engineering_wakeup", ROOT / "scripts/issue47_engineering_wakeup.py"
)
WAKEUP = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = WAKEUP
MODULE_SPEC.loader.exec_module(WAKEUP)
import codex_orchestrator as ORCHESTRATOR
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo("Asia/Taipei"))


def fenced(begin: str, end: str, value: dict) -> str:
    return f"{begin}\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```\n{end}\n"


class Issue47EngineeringWakeupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "repo"
        (self.repo / ".ai").mkdir(parents=True)
        self.output = self.repo / "output/control-plane/collaboration-goal"
        self.spec = json.loads(
            (ROOT / "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.4.json").read_text(encoding="utf-8")
        )
        self.spec_path = self.repo / "goal-v4.json"
        self.spec_path.write_text(json.dumps(self.spec, ensure_ascii=False), encoding="utf-8")
        self.review_id = "review-issue47-end-to-end-autonomous-collaboration-004"
        self.fingerprint = "a" * 64
        self.plan = {
            "goal_id": WAKEUP.GOAL_ID,
            "goal_spec": {
                "version": WAKEUP.GOAL_VERSION,
                "canonical_sha256": WAKEUP.GOAL_SPEC_SHA256,
            },
        }
        self.status = {
            "goal_id": WAKEUP.GOAL_ID,
            "git": {"head": "b" * 40},
            "working_state": {"fingerprint": self.fingerprint},
            "goal_spec": {
                "version": WAKEUP.GOAL_VERSION,
                "canonical_sha256": WAKEUP.GOAL_SPEC_SHA256,
            },
            "resource_accounting": {
                "codex": {
                    "consumed_total_conservative": 14,
                    "current_workday_launches": 7,
                    "ceiling": 18,
                    "daily_ceiling": 18,
                    "current_workday": "2026-10-31",
                },
                "claude": {
                    "consumed_total_conservative": 2,
                    "current_workday_launches": 2,
                    "ceiling": 12,
                    "daily_ceiling": 12,
                    "current_workday": "2026-10-31",
                },
            },
        }
        self.orchestrator = {
            "active_goal": WAKEUP.GOAL_ID,
            "state": "READY_FOR_AI_REVIEW",
            "review_id": self.review_id,
            "blockers": [],
        }
        self.request = {
            "status": "READY_FOR_REVIEW",
            "review_id": self.review_id,
            "candidate_fingerprint": self.fingerprint,
            "candidate_revision": "b" * 40 + "+worktree:" + self.fingerprint,
        }
        self.heartbeat = Path(self.temporary.name) / "automation.toml"
        self.heartbeat.write_text(
            'id = "kgnote-47-goal"\nstatus = "PAUSED"\nupdated_at = 1\n',
            encoding="utf-8",
        )
        command = {
            "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
            "action": "APPROVE",
            "goal_id": WAKEUP.GOAL_ID,
            "goal_version": WAKEUP.GOAL_VERSION,
            "goal_spec_sha256": WAKEUP.GOAL_SPEC_SHA256,
            "permissions": self.spec["allowed_operations"],
            "resource_acknowledgement": {
                "work_period": "2026-10-31T09:15:00+08:00/2026-11-20T18:00:00+08:00",
                "work_window": "MON-FRI 09:00-18:00 + OCT31 09:15-18:00 / NOV01 09:00-18:00 engineering-only Asia/Taipei",
                "max_model_concurrency": 1,
                "codex_max_per_workday": 18,
                "codex_max_total": 18,
                "codex_known_preapproval": 12,
                "claude_max_per_workday": 12,
                "claude_max_total": 12,
                "claude_known_preapproval": 2,
                "paid_api_fallback": False,
                "history_reset_forbidden": True,
            },
            "product_goal_coexistence": "BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE",
            "product_goal_authorized": False,
            "standing_b_scheme_go_live_authorized": False,
        }
        self.authority = self.repo / "authority.json"
        self.authority.write_text(json.dumps({
            "id": WAKEUP.OWNER_COMMENT_ID,
            "html_url": "https://github.com/example/comment",
            "author_association": "OWNER",
            "user": {"login": WAKEUP.OWNER_LOGIN},
            "body": WAKEUP.AUTHORITY_MARKER + "\n```json\n" + json.dumps(command) + "\n```",
        }), encoding="utf-8")
        self._write_runtime()

    def _write_runtime(self) -> None:
        (self.repo / "PLAN.md").write_text(fenced(
            "<!-- BEGIN CODEX PLAN JSON -->", "<!-- END CODEX PLAN JSON -->", self.plan
        ), encoding="utf-8")
        (self.repo / "CODEX_STATUS.md").write_text(fenced(
            "<!-- BEGIN CODEX STATUS JSON -->", "<!-- END CODEX STATUS JSON -->", self.status
        ), encoding="utf-8")
        (self.repo / ".ai/ORCHESTRATOR_STATE.json").write_text(
            json.dumps(self.orchestrator), encoding="utf-8"
        )
        (self.repo / ".ai/REVIEW_REQUEST.md").write_text(fenced(
            "<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->",
            "<!-- END KGNOTE REVIEW REQUEST JSON -->",
            self.request,
        ), encoding="utf-8")

    def inspect(self, **changes):
        arguments = {
            "repo": self.repo,
            "spec_path": self.spec_path,
            "heartbeat_path": self.heartbeat,
            "state_path": self.output / "wakeup-state.json",
            "writer_lock": self.output / "writer.lock",
            "authority_fixture": self.authority,
            "stop_marker": self.repo / ".ai/ORCHESTRATOR_STOP",
            "now": NOW,
        }
        arguments.update(changes)
        return WAKEUP.inspect(**arguments)

    def test_v4_gate_reserves_claude_review_without_launching_a_model(self) -> None:
        result = self.inspect(reserve=True)
        self.assertEqual("RESERVED", result["status"])
        self.assertEqual("DISPATCH_REVIEW", result["action"])
        self.assertEqual("claude", result["provider"])
        self.assertEqual(self.review_id, result["review_id"])
        self.assertFalse(result["safety"]["model_launch_started"])
        state = json.loads((self.output / "wakeup-state.json").read_text())
        self.assertEqual("RESERVED", state["events"][-1]["status"])
        self.assertFalse(state["events"][-1]["model_launch_started"])
        self.assertEqual(3, result["usage_after_charge"]["total"])
        self.assertEqual(3, result["usage_after_charge"]["today"])

    def test_duplicate_tick_does_not_reserve_or_launch_again(self) -> None:
        first = self.inspect(reserve=True)
        second = self.inspect(reserve=True)
        self.assertEqual("RESERVED", first["status"])
        self.assertEqual("WAITING_DUPLICATE", second["status"])
        self.assertEqual(first["dispatch_key"], second["existing_dispatch_key"])
        self.assertFalse(second["safety"]["model_launch_started"])

    def test_failed_same_key_is_charged_once_and_never_redispatched(self) -> None:
        first = self.inspect(reserve=True)
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text())
        state["events"].append({
            "dispatch_key": first["dispatch_key"], "status": "FAILED",
            "observed_at": NOW.isoformat(), "model_launch_started": True,
            "continuation_exit_code": 2,
        })
        state_path.write_text(json.dumps(state))
        second = self.inspect(reserve=True)
        self.assertEqual("WAITING_DUPLICATE", second["status"])
        self.assertEqual("FAILED", second["existing_status"])
        persisted = json.loads(state_path.read_text())
        self.assertEqual(1, len(persisted["dispatches"]))
        self.assertEqual(1, persisted["dispatches"][0]["usage_charge"])

    def test_unknown_history_status_fails_closed(self) -> None:
        first = self.inspect(reserve=True)
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text())
        state["events"].append({
            "dispatch_key": first["dispatch_key"], "status": "RETRY_ME",
            "observed_at": NOW.isoformat(), "model_launch_started": True,
        })
        state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(WAKEUP.WakeupError, "event status"):
            self.inspect(reserve=True)

    def test_dispatch_charge_persists_and_daily_count_rolls_by_date_only(self) -> None:
        first = self.inspect(reserve=True)
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text())
        state["events"].append({
            "dispatch_key": first["dispatch_key"], "status": "COMPLETED",
            "observed_at": NOW.isoformat(), "model_launch_started": True,
            "continuation_exit_code": 0,
        })
        state_path.write_text(json.dumps(state))
        self.review_id = "review-issue47-end-to-end-autonomous-collaboration-005"
        self.request["review_id"] = self.review_id
        self.orchestrator["review_id"] = self.review_id
        self._write_runtime()
        next_day = self.inspect(
            reserve=True,
            now=datetime(2026, 11, 1, 10, 0, tzinfo=ZONE),
        )
        self.assertEqual("RESERVED", next_day["status"])
        self.assertEqual(4, next_day["usage_after_charge"]["total"])
        self.assertEqual(1, next_day["usage_after_charge"]["today"])
        persisted = json.loads(state_path.read_text())
        self.assertEqual(2, len(persisted["dispatches"]))

    def test_legacy_completed_state_migrates_without_double_charging(self) -> None:
        state_path = self.output / "wakeup-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({
            "schema_version": WAKEUP.LEGACY_STATE_SCHEMA_VERSION,
            "status": "COMPLETED",
            "reserved_at": "2026-10-31T11:39:28+08:00",
            "completed_at": "2026-10-31T11:40:27+08:00",
            "dispatch_key": "d" * 64,
            "goal_id": WAKEUP.GOAL_ID,
            "goal_version": WAKEUP.GOAL_VERSION,
            "action": "DISPATCH_REVIEW",
            "provider": "claude",
            "review_id": "review-issue47-end-to-end-autonomous-collaboration-004",
            "candidate_fingerprint": self.fingerprint,
            "model_launch_started": True,
            "continuation_exit_code": 0,
        }), encoding="utf-8")
        self.review_id = "review-issue47-end-to-end-autonomous-collaboration-005"
        self.request["review_id"] = self.review_id
        self.orchestrator["review_id"] = self.review_id
        self._write_runtime()
        result = self.inspect(reserve=True)
        self.assertEqual("RESERVED", result["status"])
        self.assertEqual(3, result["usage_after_charge"]["total"])
        migrated = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(WAKEUP.LEGACY_STATE_SCHEMA_VERSION, migrated["migrated_from"])
        self.assertTrue(migrated["dispatches"][0]["accounting_included_in_baseline"])
        self.assertEqual(["RESERVED", "COMPLETED", "RESERVED"], [
            event["status"] for event in migrated["events"]
        ])

    def test_completed_dispatch_allows_new_identity_but_active_old_one_blocks(self) -> None:
        first = self.inspect(reserve=True)
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text())
        state["events"].append({
            "dispatch_key": first["dispatch_key"], "status": "COMPLETED",
            "observed_at": NOW.isoformat(), "model_launch_started": True,
            "continuation_exit_code": 0,
        })
        state_path.write_text(json.dumps(state))
        self.review_id = "review-issue47-end-to-end-autonomous-collaboration-005"
        self.request["review_id"] = self.review_id
        self.orchestrator["review_id"] = self.review_id
        self._write_runtime()
        second = self.inspect(reserve=True)
        self.assertEqual("RESERVED", second["status"])
        self.assertNotEqual(first["dispatch_key"], second["dispatch_key"])

        state = json.loads(state_path.read_text())
        state["events"].append({
            "dispatch_key": second["dispatch_key"], "status": "RUNNING",
            "observed_at": NOW.isoformat(), "model_launch_started": True,
            "continuation_exit_code": None,
        })
        state_path.write_text(json.dumps(state))
        self.review_id = "review-issue47-end-to-end-autonomous-collaboration-006"
        self.request["review_id"] = self.review_id
        self.orchestrator["review_id"] = self.review_id
        self._write_runtime()
        blocked = self.inspect(reserve=True)
        self.assertEqual("WAITING_ACTIVE_RESERVATION", blocked["status"])
        self.assertFalse(blocked["safety"]["model_launch_started"])

    def test_active_heartbeat_and_stale_v2_limits_fail_closed(self) -> None:
        self.heartbeat.write_text(
            'id = "kgnote-47-goal"\nstatus = "ACTIVE"\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(WAKEUP.WakeupError, "paused"):
            self.inspect()
        self.heartbeat.write_text(
            'id = "kgnote-47-goal"\nstatus = "PAUSED"\n', encoding="utf-8"
        )
        self.status["resource_accounting"]["claude"]["daily_ceiling"] = 2
        self._write_runtime()
        with self.assertRaisesRegex(WAKEUP.WakeupError, "do not implement v4"):
            self.inspect()

    def test_stop_and_outside_window_never_read_authority_or_reserve(self) -> None:
        (self.repo / ".ai/ORCHESTRATOR_STOP").write_text("stop\n", encoding="utf-8")
        with mock.patch.object(WAKEUP, "fetch_authority", side_effect=AssertionError):
            stopped = self.inspect(reserve=True)
        self.assertEqual("STOPPED", stopped["status"])
        self.assertFalse((self.output / "wakeup-state.json").exists())
        (self.repo / ".ai/ORCHESTRATOR_STOP").unlink()
        outside = self.inspect(now=datetime(2026, 11, 1, 8, 59, tzinfo=ZONE))
        self.assertEqual("WAITING_WORK_WINDOW", outside["status"])
        self.assertFalse((self.output / "wakeup-state.json").exists())

    def test_total_quota_and_provider_backoff_wait_without_reservation(self) -> None:
        self.status["resource_accounting"]["claude"]["consumed_total_conservative"] = 12
        self._write_runtime()
        quota = self.inspect(reserve=True)
        self.assertEqual("WAITING_QUOTA", quota["status"])
        self.assertFalse((self.output / "wakeup-state.json").exists())
        self.status["resource_accounting"]["claude"]["consumed_total_conservative"] = 2
        self.orchestrator["blockers"] = [{
            "type": "claude_provider_quota_backoff",
            "provider": "claude",
            "retry_at": "2026-10-31T13:00:00+08:00",
        }]
        self._write_runtime()
        backoff = self.inspect(reserve=True)
        self.assertEqual("WAITING_PROVIDER_BACKOFF", backoff["status"])
        self.assertFalse((self.output / "wakeup-state.json").exists())

    def test_writer_lock_and_review_identity_are_fail_closed(self) -> None:
        lock_path = self.output / "writer.lock"
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(WAKEUP.WakeupError, "another Issue #47 writer"):
                self.inspect(reserve=True)
        self.orchestrator["review_id"] = "review-wrong-999"
        self._write_runtime()
        with self.assertRaisesRegex(WAKEUP.WakeupError, "review identity differs"):
            self.inspect()

    def test_implementation_action_uses_codex_but_still_only_reserves(self) -> None:
        self.request = {
            "status": "IMPLEMENTING",
            "review_id": self.review_id,
            "candidate_fingerprint": None,
            "candidate_revision": None,
        }
        self.orchestrator["state"] = "REPAIRING"
        self._write_runtime()
        result = self.inspect(reserve=True)
        self.assertEqual("codex", result["provider"])
        self.assertEqual("DISPATCH_IMPLEMENTATION", result["action"])
        self.assertFalse(result["safety"]["model_launch_started"])

    def test_changes_required_repair_reservation_is_accepted_by_continuation(self) -> None:
        self.request = {
            "status": "CHANGES_REQUIRED",
            "review_id": self.review_id,
            "candidate_fingerprint": self.fingerprint,
            "candidate_revision": "b" * 40 + "+worktree:" + self.fingerprint,
        }
        self.orchestrator["state"] = "REPAIRING"
        self._write_runtime()
        reserved = self.inspect(reserve=True)
        self.assertEqual("DISPATCH_IMPLEMENTATION", reserved["action"])
        self.assertEqual(15, reserved["usage_after_charge"]["total"])
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["events"].append({
            "dispatch_key": reserved["dispatch_key"],
            "status": "RUNNING",
            "observed_at": NOW.isoformat(),
            "model_launch_started": True,
            "continuation_exit_code": None,
        })
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with mock.patch.object(
            ORCHESTRATOR.control, "repository_fingerprint",
            return_value={"head": "b" * 40, "value": self.fingerprint},
        ), mock.patch.object(
            ORCHESTRATOR.control, "load_review_artifacts",
            return_value=(self.request, {}, {}),
        ), mock.patch.object(
            ORCHESTRATOR, "read_state", return_value=self.orchestrator,
        ):
            ORCHESTRATOR.validate_engineering_reservation(
                self.repo,
                state_path,
                reserved["dispatch_key"],
                "DISPATCH_IMPLEMENTATION",
                "codex",
            )
        persisted = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(persisted["dispatches"]))
        self.assertEqual("RUNNING", persisted["events"][-1]["status"])

    def test_history_event_without_timezone_aware_timestamp_fails_closed(self) -> None:
        self.inspect(reserve=True)
        state_path = self.output / "wakeup-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["events"][-1]["observed_at"] = None
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(WAKEUP.WakeupError, "timestamp"):
            self.inspect(reserve=True)


ZONE = ZoneInfo("Asia/Taipei")


if __name__ == "__main__":
    unittest.main()
