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


if __name__ == "__main__":
    unittest.main()
