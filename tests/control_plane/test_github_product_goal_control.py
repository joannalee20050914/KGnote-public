from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from tests.control_plane.test_goal_continuity import product_goal_spec

SPEC = importlib.util.spec_from_file_location(
    "github_product_goal_control", ROOT / "scripts/github_product_goal_control.py"
)
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


def comment(spec: dict, *, action="APPROVE", comment_id=100, login="owner", **changes):
    import goal_continuity

    payload = {
        "schema_version": "kgnote.product-goal-authority-command.v1",
        "action": action,
        "goal_id": spec["goal_id"],
        "goal_version": spec["goal_version"],
        "goal_spec_sha256": goal_continuity.goal_spec_sha256(spec),
        "permissions": spec["allowed_operations"],
    }
    payload.update(changes.pop("payload", {}))
    return {
        "id": comment_id,
        "html_url": f"https://github.com/owner/repo/issues/42#issuecomment-{comment_id}",
        "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
        "created_at": f"2026-10-22T10:{comment_id % 60:02d}:00Z",
        "author_association": changes.pop("author_association", "OWNER"),
        "user": {"login": login},
        "body": CONTROL.MARKER + "\n```json\n" + json.dumps(payload) + "\n```",
        **changes,
    }


class GitHubProductGoalControlTests(unittest.TestCase):
    def setUp(self):
        self.spec = product_goal_spec()

    def test_exact_owner_record_authorizes_and_preserves_identity(self):
        record = CONTROL.authority_record_from_comment(comment(self.spec), self.spec)
        self.assertEqual("KGNOTE_PRODUCT_GOAL", record["identity_kind"])
        self.assertEqual("GITHUB_OWNER_APPROVAL", record["authority_kind"])
        self.assertEqual(self.spec["goal_id"], record["goal_id"])
        self.assertEqual(self.spec["allowed_operations"], record["permissions"])

    def test_wrong_actor_stale_version_and_changed_permissions_are_rejected(self):
        cases = [
            comment(self.spec, login="automation-bot", author_association="MEMBER"),
            comment(self.spec, payload={"goal_version": "stale"}),
            comment(self.spec, payload={"permissions": self.spec["allowed_operations"] + ["merge"]}),
        ]
        for value in cases:
            with self.subTest(value=value["id"], body=value["body"]):
                with self.assertRaises(CONTROL.GitHubAuthorityError):
                    CONTROL.authority_record_from_comment(value, self.spec)

    def test_later_pause_and_revoke_win_without_app_goal_input(self):
        comments = [
            comment(self.spec, action="APPROVE", comment_id=100),
            comment(self.spec, action="PAUSE", comment_id=101),
            comment(self.spec, action="RESUME", comment_id=102),
            comment(self.spec, action="REVOKE", comment_id=103),
        ]
        result = CONTROL.resolve_authority(comments, self.spec)
        self.assertEqual("REVOKED", result["authority_lease"])
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual("REVOKE", result["record"]["action"])
        self.assertEqual([], result["rejected_records"])

    def test_non_owner_marker_is_a_rejected_record_not_silent_authority(self):
        result = CONTROL.resolve_authority(
            [comment(self.spec, login="codex-bot", author_association="CONTRIBUTOR")],
            self.spec,
        )
        self.assertEqual("APPROVAL_REQUIRED", result["status"])
        self.assertIsNone(result["record"])
        self.assertEqual(1, len(result["rejected_records"]))

    def test_revocation_is_terminal_for_the_exact_goal_version(self):
        comments = [
            comment(self.spec, action="APPROVE", comment_id=100),
            comment(self.spec, action="REVOKE", comment_id=101),
            comment(self.spec, action="APPROVE", comment_id=102),
            comment(self.spec, action="RESUME", comment_id=103),
        ]
        result = CONTROL.resolve_authority(comments, self.spec)
        self.assertEqual("REVOKED", result["authority_lease"])
        self.assertEqual("REVOKE", result["record"]["action"])


if __name__ == "__main__":
    unittest.main()
