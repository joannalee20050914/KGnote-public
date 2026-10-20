from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PublicationReceiptContractTests(unittest.TestCase):
    def test_receipt_uses_live_pr_indirection_not_self_referential_sha(self):
        text = (ROOT / ".ai/PUBLICATION_RECEIPT.md").read_text()
        self.assertIn("candidate_commit` to equal the live PR head SHA", text)
        self.assertIn("recompute the repository fingerprint", text)
        self.assertIn("must never be required inside the bytes of that same commit", text)
        self.assertNotIn("4ea057c174dd4f048a72716dcd902407884787dc", text)

    def test_checkpoint_and_post_commit_identity_have_distinct_authority(self):
        protocol = (ROOT / ".ai/REVIEW_PROTOCOL.md").read_text()
        receipt = (ROOT / ".ai/PUBLICATION_RECEIPT.md").read_text()
        audit = (ROOT / "docs/control-plane/PR28_ROUND6_CANDIDATE_COMPLETE_AUDIT.md").read_text()
        self.assertIn("cannot contain its own final SHA", protocol)
        self.assertIn("live PR marker supplies final HEAD plus fingerprint", receipt)
        self.assertIn("ignored post-commit receipt", audit)
        self.assertIn("READY_FOR_REVIEW_BUDGET_BLOCKED", audit)

    def test_review_budget_namespaces_are_not_merged_or_reset(self):
        receipt = (ROOT / ".ai/PUBLICATION_RECEIPT.md").read_text()
        self.assertIn("successor PR #26 Claude budget (6 authorized / 6 consumed)", receipt)
        self.assertIn("integration-local review ID/cycle", receipt)
        self.assertIn("must not be renumbered, merged, or reset", receipt)


if __name__ == "__main__":
    unittest.main()
