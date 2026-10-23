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
import github_product_goal_control as AUTHORITY


class ProductGoalBacklogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backlog = json.loads(
            (ROOT / "docs/control-plane/PRODUCT_GOAL_BACKLOG.json").read_text()
        )
        cls.o2_spec = json.loads(
            (ROOT / "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json").read_text()
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

    def test_o2_bounded_trial_spec_is_exact_and_never_inherits_legacy_budget(self):
        GOAL.validate_goal_spec(self.o2_spec)
        first=self.backlog["items"][0]
        self.assertEqual(first["goal_id"],self.o2_spec["goal_id"])
        self.assertEqual(first["goal_version"],self.o2_spec["goal_version"])
        self.assertEqual("BLOCKED_WITH_SPECIFIC_GAPS",first["approval_eligibility"]["status"])
        self.assertEqual(8,self.o2_spec["resource_policy"]["providers"]["codex"]["fallback"]["max_total_launches"])
        self.assertEqual(8,self.o2_spec["resource_policy"]["providers"]["claude"]["fallback"]["max_total_launches"])
        self.assertEqual(5,len(self.o2_spec["trial_schedule"]["observation_work_dates"]))
        self.assertEqual(600,self.o2_spec["trial_schedule"]["transition_start_slo_seconds"])
        self.assertEqual(0,self.o2_spec["trial_schedule"]["ordinary_human_relay_limit"])
        ids={item["work_item_id"] for item in self.o2_spec["work_items"]}
        self.assertIn("WI-O2-A-IMPLEMENT",ids)
        self.assertIn("WI-O2-B-IMPLEMENT",ids)
        self.assertNotIn("WI-O2-IMPLEMENT",ids)
        by_id={item["work_item_id"]:item for item in self.o2_spec["work_items"]}
        self.assertEqual(
            ["WI-O2-A-REVIEW","WI-O2-A-REPAIR"],
            by_id["WI-O2-B-IMPLEMENT"]["dependencies"],
        )
        self.assertEqual(
            ["WI-O2-A-REVIEW","WI-O2-A-REPAIR","WI-O2-B-REVIEW","WI-O2-B-REPAIR"],
            by_id["WI-O2-ACCEPTANCE"]["dependencies"],
        )
        self.assertNotIn("legacy_budget",self.o2_spec)

    def test_prepared_owner_command_binds_exact_spec_and_permissions(self):
        package=(ROOT/"docs/control-plane/O2_BOUNDED_TRIAL_AUTHORIZATION_PACKAGE_20261023.md").read_text()
        payload=AUTHORITY.parse_marker_payload(package)
        self.assertEqual(GOAL.goal_spec_sha256(self.o2_spec),payload["goal_spec_sha256"])
        self.assertEqual(self.o2_spec["goal_version"],payload["goal_version"])
        self.assertEqual(self.o2_spec["allowed_operations"],payload["permissions"])

    def test_legacy_disposition_preserves_open_findings_and_all_named_budgets(self):
        disposition=(ROOT/"docs/control-plane/LEGACY_ISSUE9_DISPOSITION_20261023.md").read_text()
        for finding in (
            "finding-render-click-evidence-stale-and-untracked",
            "finding-control-plane-state-stale-vs-candidate",
            "finding-unsupported-clause-not-gap-and-leaks-into-brief",
        ):
            self.assertIn(finding,disposition)
        for counter in ("`3/3` used","`8/8` used","`2/2` used","`0/1` used","`1/1` used"):
            self.assertIn(counter,disposition)
        self.assertIn("does not close Issue #9",disposition)
        self.assertIn("They are not marked fixed",disposition)

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
