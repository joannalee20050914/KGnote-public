from __future__ import annotations

import importlib.util
import json
import subprocess
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
import goal_continuity
import github_product_goal_control

MODULE_SPEC = importlib.util.spec_from_file_location(
    "collaboration_goal_wakeup", ROOT / "scripts/collaboration_goal_wakeup.py"
)
WAKEUP = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(WAKEUP)

FIXED_NOW = datetime(2026, 10, 30, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


def authority_comment(spec: dict, *, comment_id: int = 4701) -> dict:
    payload = {
        "schema_version": "kgnote.product-goal-authority-command.v1",
        "action": "APPROVE",
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "permissions": spec["allowed_operations"],
    }
    return {
        "id": comment_id,
        "html_url": (
            f"https://github.com/{spec['repository']}/issues/"
            f"{spec['github_issue']}#issuecomment-{comment_id}"
        ),
        "issue_url": (
            f"https://api.github.com/repos/{spec['repository']}/issues/"
            f"{spec['github_issue']}"
        ),
        "created_at": "2026-10-30T01:00:00Z",
        "author_association": "OWNER",
        "user": {"login": spec["owner_logins"][0]},
        "body": (
            github_product_goal_control.MARKER
            + "\n```json\n"
            + json.dumps(payload)
            + "\n```"
        ),
    }


class CollaborationGoalWakeupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "-b", "codex/issue47-test")
        self._git("config", "user.name", "KGnote Test")
        self._git("config", "user.email", "test@example.invalid")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self._git("add", "README.md")
        self._git("commit", "-m", "fixture")

        fixture = ROOT / "tests/fixtures/control_plane/product_goal_isolated_trial_spec.json"
        self.spec = json.loads(fixture.read_text(encoding="utf-8"))
        self._git(
            "remote",
            "add",
            "origin",
            f"https://github.com/{self.spec['repository']}.git",
        )
        self.spec_path = self.root / "goal.json"
        self.state_path = self.root / "state.json"
        self.ledger_path = self.root / "ledger.jsonl"
        self.comments_path = self.root / "comments.json"
        self._write_inputs([])

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _write_inputs(self, comments: list[dict]) -> None:
        state = goal_continuity.initial_runner_state(
            self.spec,
            now="2026-10-30T09:00:00+08:00",
        )
        self.spec_path.write_text(
            json.dumps(self.spec, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.ledger_path.write_text("", encoding="utf-8")
        self.comments_path.write_text(
            json.dumps(comments, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _inspect(self, **changes):
        arguments = {
            "repo": self.repo,
            "spec_path": self.spec_path,
            "state_path": self.state_path,
            "ledger_path": self.ledger_path,
            "comments_path": self.comments_path,
            "stop_marker": None,
            "now": FIXED_NOW,
        }
        arguments.update(changes)
        return WAKEUP.inspect_once(**arguments)

    def test_missing_owner_authority_waits_without_mutating_inputs(self):
        before = {
            path: path.read_bytes()
            for path in (self.spec_path, self.state_path, self.ledger_path)
        }
        result = self._inspect()
        self.assertEqual("WAITING_AUTHORIZATION", result["status"])
        self.assertEqual("WAIT_AUTHORITY", result["source_status"])
        self.assertEqual(0, result["goal"]["ledger_cursor"]["sequence"])
        self.assertTrue(all(not result["safety"][key] for key in (
            "execution_started", "dispatch_performed", "reservation_created",
            "model_launch_started", "schedule_enabled", "github_write_performed",
            "legacy_o2_runner_used", "input_mutation_detected",
        )))
        for path, content in before.items():
            self.assertEqual(content, path.read_bytes())

    def test_valid_owner_marker_does_not_apply_or_activate_authority(self):
        self._write_inputs([authority_comment(self.spec)])
        original_state = self.state_path.read_bytes()
        with (
            mock.patch.object(
                WAKEUP.goal_runner_adapter,
                "reserve_dispatch",
                side_effect=AssertionError("reservation must not run"),
            ),
            mock.patch.object(
                WAKEUP.goal_runner_adapter.linux_worker_router,
                "route",
                side_effect=AssertionError("router must not run"),
            ),
        ):
            result = self._inspect()
        self.assertEqual("WAITING_AUTHORIZATION", result["status"])
        self.assertEqual("TRIAL_ONLY", result["source_status"])
        self.assertEqual("ACTIVE", result["authority"]["authority_lease"])
        self.assertEqual(1, result["authority"]["valid_record_count"])
        self.assertEqual(original_state, self.state_path.read_bytes())

    def test_stop_marker_skips_github_fetch_and_planning(self):
        marker = self.root / "STOP"
        marker.write_text("stop\n", encoding="utf-8")

        def forbidden_fetch(_spec):
            raise AssertionError("stop must not fetch GitHub")

        with mock.patch.object(
            WAKEUP.goal_runner_adapter,
            "next_action",
            side_effect=AssertionError("stop must not plan"),
        ):
            result = WAKEUP.inspect_once(
                repo=self.repo,
                spec_path=self.spec_path,
                state_path=self.state_path,
                ledger_path=self.ledger_path,
                comments_path=None,
                stop_marker=marker,
                now=FIXED_NOW,
                comments_fetcher=forbidden_fetch,
            )
        self.assertEqual("STOPPED", result["status"])
        self.assertEqual("STOP_MARKER", result["source_status"])
        self.assertIsNone(result["comments_sha256"])

    def test_fixed_inputs_and_time_are_byte_identical(self):
        first = self._inspect()
        second = self._inspect()
        self.assertEqual(first, second)
        self.assertEqual(WAKEUP.serialize_result(first), WAKEUP.serialize_result(second))

    def test_protected_o2_goal_is_rejected_before_planning(self):
        protected = deepcopy(self.spec)
        protected["goal_id"] = "GOAL-KGNOTE-O2-READING-EXPERIENCE"
        protected["active_goal"] = protected["goal_id"]
        self.spec_path.write_text(
            json.dumps(protected, indent=2) + "\n", encoding="utf-8"
        )
        with mock.patch.object(
            WAKEUP.goal_runner_adapter,
            "next_action",
            side_effect=AssertionError("protected Goal must not plan"),
        ):
            with self.assertRaises(WAKEUP.ProtectedGoalError):
                self._inspect()

    def test_wrong_repository_and_broken_ledger_fail_closed(self):
        wrong = deepcopy(self.spec)
        wrong["repository"] = "wrong-owner/wrong-repository"
        self.spec_path.write_text(json.dumps(wrong) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(
            WAKEUP.CollaborationWakeupError,
            "Goal repository differs",
        ):
            self._inspect()

        self._write_inputs([])
        self.ledger_path.write_text('{"not":"a ledger event"}\n', encoding="utf-8")
        with self.assertRaises(goal_continuity.GoalContractError):
            self._inspect()

    def test_input_drift_during_planning_fails_closed(self):
        original = WAKEUP.goal_runner_adapter.next_action

        def mutating_planner(*args, **kwargs):
            result = original(*args, **kwargs)
            self.state_path.write_text(
                self.state_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            return result

        with mock.patch.object(
            WAKEUP.goal_runner_adapter,
            "next_action",
            side_effect=mutating_planner,
        ):
            with self.assertRaisesRegex(
                WAKEUP.CollaborationWakeupError,
                "input bytes changed",
            ):
                self._inspect()

    def test_candidate_identity_must_match_current_checkout(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["candidate_identity"] = {
            "commit": "0" * 40,
            "fingerprint": "1" * 64,
            "branch": "codex/issue47-test",
            "pull_request": None,
        }
        self.state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(
            WAKEUP.CollaborationWakeupError,
            "candidate commit differs",
        ):
            self._inspect()

    def test_public_status_mapping_is_explicit_and_bounded(self):
        cases = [
            ({"status": "WAIT_AUTHORITY"}, "WAITING_AUTHORIZATION"),
            ({"status": "TRIAL_ACTION_READY", "action": "DISPATCH_IMPLEMENTATION"}, "RUNNING"),
            ({"status": "ACTION_READY", "action": "DISPATCH_REVIEW"}, "REVIEWING"),
            ({"status": "HUMAN_ACCEPTANCE_REQUIRED"}, "READY_FOR_ACCEPTANCE"),
            ({"status": "WAIT_WORK_WINDOW"}, "STOPPED"),
            ({"status": "WAIT_GOAL_RESOURCE_LIMIT"}, "BLOCKED"),
            ({"status": "HUMAN_DECISION_REQUIRED"}, "BLOCKED"),
            ({"status": "TRIAL_ACTIVATION_MISSED"}, "BLOCKED"),
        ]
        for planner, expected in cases:
            with self.subTest(planner=planner):
                actual = WAKEUP.public_status(planner)
                self.assertEqual(expected, actual)
                self.assertIn(actual, WAKEUP.PUBLIC_STATUSES)

    def test_blocked_result_reports_detected_input_mutation(self):
        result = WAKEUP.blocked_result(
            "one-shot input bytes changed during planning",
            now=FIXED_NOW,
        )
        self.assertEqual("BLOCKED", result["status"])
        self.assertTrue(result["safety"]["input_mutation_detected"])
        self.assertFalse(result["safety"]["model_launch_started"])

    def test_time_requires_an_explicit_offset_when_supplied(self):
        with self.assertRaisesRegex(
            WAKEUP.CollaborationWakeupError,
            "timezone offset",
        ):
            WAKEUP.parse_observation_time("2026-10-30T10:00:00")


if __name__ == "__main__":
    unittest.main()
