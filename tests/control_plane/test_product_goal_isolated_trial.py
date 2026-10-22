from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "run_product_goal_isolated_trial", ROOT / "scripts/run_product_goal_isolated_trial.py"
)
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)


class ProductGoalIsolatedTrialTests(unittest.TestCase):
    def test_paths_a_and_b_are_no_model_no_write_and_pass(self):
        load = lambda path: json.loads((ROOT / path).read_text())
        result = TRIAL.run_trial(
            load("tests/fixtures/control_plane/product_goal_isolated_trial_spec.json"),
            load("docs/control-plane/PRODUCT_GOAL_BACKLOG.json"),
            load("tests/fixtures/control_plane/issue9_pr29_goal_history.json"),
        )
        self.assertEqual("PASS", result["result"])
        self.assertEqual(0, result["model_invocations"])
        self.assertEqual(0, result["external_writes"])
        self.assertFalse(result["production_activation"])
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
