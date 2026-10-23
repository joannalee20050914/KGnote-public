from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "goal_continuity", ROOT / "scripts/goal_continuity.py"
)
GOAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOAL)


class ProductGoalBacklogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backlog = json.loads(
            (ROOT / "docs/control-plane/PRODUCT_GOAL_BACKLOG.json").read_text()
        )

    def test_backlog_is_ordered_unique_and_source_bound(self):
        GOAL.validate_backlog(self.backlog)
        self.assertEqual([1, 2, 3, 4, 5, 6], [row["sequence"] for row in self.backlog["items"]])
        self.assertEqual("PLANNING_ONLY_NO_EXECUTION_AUTHORITY", self.backlog["authority_kind"])

    def test_legacy_issue9_blocks_first_goal_without_migrating_authority(self):
        result = GOAL.select_next_backlog_goal(
            self.backlog, closed_goal_ids=set(), resolved_external_dependencies=set()
        )
        self.assertEqual("WAIT_DEPENDENCY", result["status"])
        self.assertEqual(["LEGACY-ISSUE-9-DISPOSITION"], result["missing_dependencies"])

    def test_dependency_resolution_only_requests_approval(self):
        result = GOAL.select_next_backlog_goal(
            self.backlog,
            closed_goal_ids=set(),
            resolved_external_dependencies={"LEGACY-ISSUE-9-DISPOSITION"},
        )
        self.assertEqual("APPROVAL_REQUIRED", result["status"])
        self.assertFalse(result["authority_granted"])

    def test_path_b_closed_goal_prepares_next_but_cannot_start_it(self):
        first = self.backlog["items"][0]["goal_id"]
        result = GOAL.select_next_backlog_goal(
            self.backlog,
            closed_goal_ids={first},
            resolved_external_dependencies={"LEGACY-ISSUE-9-DISPOSITION"},
        )
        self.assertEqual("APPROVAL_REQUIRED", result["status"])
        self.assertEqual("GOAL-KGNOTE-O3-EXACT-CONTINUATION", result["goal_id"])
        self.assertFalse(result["authority_granted"])


if __name__ == "__main__":
    unittest.main()
