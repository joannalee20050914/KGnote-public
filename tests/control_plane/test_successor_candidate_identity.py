import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SuccessorCandidateIdentityTest(unittest.TestCase):
    def test_legacy_review_is_preserved_but_never_rebound_to_pr26(self):
        value = json.loads((ROOT / ".ai/SUCCESSOR_CANDIDATE_IDENTITY.json").read_text())
        legacy = value["legacy_identity"]
        successor = value["successor_initial_identity"]
        self.assertEqual(23, legacy["pull_request"])
        self.assertEqual("CHANGES_REQUIRED", legacy["verdict"])
        self.assertFalse(legacy["applies_to_successor"])
        self.assertEqual(26, successor["pull_request"])
        self.assertEqual(legacy["head"], successor["inherited_head"])
        self.assertEqual(legacy["fingerprint"], successor["inherited_bytes_fingerprint"])
        self.assertFalse(successor["legacy_pass_inherited"])
        self.assertFalse(successor["existing_exact_candidate_result"])
        self.assertEqual("INHERITED_BYTES_PENDING_NEW_CANDIDATE", successor["identity_status"])

    def test_legacy_and_successor_budgets_are_separate_and_unspent(self):
        budget = json.loads((ROOT / ".ai/SUCCESSOR_CANDIDATE_IDENTITY.json").read_text())["budget_inheritance"]
        self.assertEqual((17, 15), (budget["legacy_supplemental_authorized"], budget["legacy_supplemental_used"]))
        self.assertEqual((12, 0), (budget["successor_codex_authorized"], budget["successor_codex_used"]))
        self.assertEqual((6, 0), (budget["successor_claude_authorized"], budget["successor_claude_used"]))


if __name__ == "__main__": unittest.main()
