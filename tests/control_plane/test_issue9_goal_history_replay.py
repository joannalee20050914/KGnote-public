from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "replay_issue9_goal_history", ROOT / "scripts/replay_issue9_goal_history.py"
)
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


class Issue9GoalHistoryReplayTests(unittest.TestCase):
    def test_live_history_replays_without_model_write_or_budget_reset(self):
        fixture = json.loads((
            ROOT / "tests/fixtures/control_plane/issue9_pr29_goal_history.json"
        ).read_text())
        result = REPLAY.replay(fixture)
        self.assertEqual(4, result["valid_review_verdicts"])
        self.assertEqual(5, result["model_attempts"])
        self.assertFalse(result["quota_attempt_is_review"])
        self.assertEqual(0, result["quota_attempt_input_tokens"])
        self.assertEqual(0, result["quota_attempt_output_tokens"])
        self.assertEqual("NO_OBLIGATION_PROGRESS", result["latest_identity_obligation"])
        self.assertEqual("RETRY_PUBLICATION_WITHOUT_MODEL", result["writeback_failure_recovery"])
        self.assertFalse(result["completion_gate_consumes_verdict"])
        self.assertFalse(result["commit_without_verified_obligation_is_complete"])
        self.assertTrue(result["legacy_budgets_unchanged"])
        self.assertEqual(0, result["model_invocations"])
        self.assertEqual(0, result["external_writes"])


if __name__ == "__main__":
    unittest.main()
