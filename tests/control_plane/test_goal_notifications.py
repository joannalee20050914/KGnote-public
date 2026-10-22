from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "goal_notifications", ROOT / "scripts/goal_notifications.py"
)
NOTIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOTIFY)
import goal_continuity as GOAL


class GoalNotificationTests(unittest.TestCase):
    def notice(self):
        return NOTIFY.build_notification(
            goal_id="GOAL-KGNOTE-O2-READING-EXPERIENCE",
            goal_version="2026-10-22.1",
            event_kind="NEXT_GOAL_APPROVAL_REQUIRED",
            decision_key="o2-v1",
            summary="前一 Goal 已正式結案，O2 可提出核准。",
            decision_requested="核准、延後或要求調整 O2。",
            github_issue=42,
        )

    def ack_comment(self, notice, *, login="owner", association="OWNER"):
        payload = {
            "schema_version": "kgnote.product-goal-notification-ack.v1",
            "notification_id": notice["notification_id"],
            "goal_id": notice["goal_id"],
            "goal_version": notice["goal_version"],
        }
        return {
            "id": 999,
            "html_url": "https://github.com/owner/repo/issues/42#issuecomment-999",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
            "author_association": association,
            "user": {"login": login},
            "body": NOTIFY.ACK_MARKER + "\n```json\n" + json.dumps(payload) + "\n```",
        }

    def test_operational_events_do_not_notify_owner(self):
        for kind in NOTIFY.IGNORED_OPERATIONAL_KINDS:
            with self.subTest(kind=kind):
                with self.assertRaises(NOTIFY.NotificationError):
                    NOTIFY.notification_id("GOAL-1", kind, "same")

    def test_work_is_unverified_and_github_is_default_fallback(self):
        notice = self.notice()
        self.assertEqual("UNVERIFIED", notice["chatgpt_work_status"])
        self.assertEqual("GITHUB_NATIVE", notice["transport"])
        self.assertEqual("NONE", notice["authority_effect"])

    def test_notification_queue_is_deduplicated_and_acknowledgeable(self):
        notice = self.notice()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            _, first = NOTIFY.queue_decision_notification(
                path, notice, occurred_at="2026-10-22T10:00:00+08:00"
            )
            _, second = NOTIFY.queue_decision_notification(
                path, notice, occurred_at="2026-10-22T10:00:00+08:00"
            )
            self.assertTrue(first)
            self.assertFalse(second)
            sent, _ = GOAL.append_ledger_event(
                path, event_id=notice["notification_id"] + "-sent",
                event_type="NOTIFICATION_SENT",
                occurred_at="2026-10-22T10:01:00+08:00",
                goal_id=notice["goal_id"], goal_version=notice["goal_version"],
                logical_work_id=None, attempt_id=None,
                payload={"notification_id": notice["notification_id"], "transport": "GITHUB_NATIVE"},
            )
            self.assertEqual("SENT", NOTIFY.notification_state(GOAL.read_ledger(path), notice["notification_id"]))
            _, acknowledged = NOTIFY.acknowledge_notification(
                path, notice, self.ack_comment(notice), repository="owner/repo",
                owner_logins=["owner"], occurred_at="2026-10-22T10:02:00+08:00",
            )
            self.assertTrue(acknowledged)
            self.assertEqual("ACKNOWLEDGED", NOTIFY.notification_state(GOAL.read_ledger(path), notice["notification_id"]))

    def test_notification_ack_rejects_non_owner_and_stale_identity(self):
        notice = self.notice()
        with self.assertRaisesRegex(NOTIFY.NotificationError, "allowed repository Owner"):
            NOTIFY.acknowledgement_record_from_comment(
                self.ack_comment(notice, login="automation-bot", association="MEMBER"),
                notice, repository="owner/repo", owner_logins=["owner"],
            )
        stale = self.ack_comment(notice)
        stale["body"] = stale["body"].replace(notice["goal_version"], "stale")
        with self.assertRaisesRegex(NOTIFY.NotificationError, "exact notification"):
            NOTIFY.acknowledgement_record_from_comment(
                stale, notice, repository="owner/repo", owner_logins=["owner"],
            )

    def test_github_publish_is_readback_idempotent(self):
        notice = self.notice()
        body = NOTIFY.github_notification_body(notice)
        rows = []
        calls = []

        def fake(command, **kwargs):
            calls.append(command)
            if "-f" in command:
                rows.append({"id": 77, "html_url": "https://example/77", "body": body})
                return subprocess.CompletedProcess(command, 0, json.dumps(rows), "")
            return subprocess.CompletedProcess(command, 0, json.dumps(rows), "")

        first = NOTIFY.publish_github_notification("owner/repo", notice, command_runner=fake)
        before = len(calls)
        second = NOTIFY.publish_github_notification("owner/repo", notice, command_runner=fake)
        self.assertEqual(77, first["comment_id"])
        self.assertEqual(first, second)
        self.assertEqual(before + 1, len(calls))


if __name__ == "__main__":
    unittest.main()
