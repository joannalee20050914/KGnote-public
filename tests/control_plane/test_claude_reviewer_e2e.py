import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from claude_review_ingestion import ingest
from trusted_candidate_publisher import PublishRequest, publish


class ClaudeReviewerFixtureE2E(unittest.TestCase):
    def test_coder_publish_finding_repair_republish_review_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / "repo"
            subprocess.run(["git", "init", "-b", "codex/fixture", repo], check=True, capture_output=True)
            subprocess.run(["git", "-C", repo, "config", "user.email", "fixture@example.invalid"], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.name", "Fixture"], check=True)
            (repo / "src").mkdir(); target = repo / "src/value.txt"; target.write_text("base\n")
            subprocess.run(["git", "-C", repo, "add", "src/value.txt"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "base"], check=True, capture_output=True)
            parent = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()

            def commit(value, message):
                nonlocal parent
                target.write_text(value)
                receipt = root / "tests.json"
                receipt.write_text(json.dumps({"status": "PASS", "candidate_parent": parent,
                                               "changed_paths": ["src/value.txt"]}))
                request = PublishRequest.from_dict({
                    "worktree": str(repo), "branch": "codex/fixture", "expected_parent": parent,
                    "allowed_paths": ["src"], "test_receipt": str(receipt),
                    "test_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(), "message": message,
                })
                result = publish(request); parent = result["commit"]; return result

            first = commit("bad\n", "test: coder candidate")
            schema = json.loads((ROOT / "schemas/product-review/v1/review-result.schema.json").read_text())
            config = {"enabled": True, "result_marker": "kgnote-ai-product-review:v1",
                      "trusted_reviewer_author_login": "claude-code-local",
                      "trusted_reviewer_identities": ["claude-code:fixture"],
                      "product_contract_review_scope": "KGNOTE_PRODUCT_CONTRACT",
                      "last_reviewed_candidate_fingerprint": None}
            checkpoint = root / "review.json"
            common = {"repository": "fixture/repo", "issue": 1, "pull_request": 2,
                      "program_id": "fixture", "goal_id": "fixture-goal",
                      "candidate_fingerprint": "b" * 64, "cumulative_round_limit": 3,
                      "reviewer_identity": "claude-code:fixture", "status": "REVIEW_SUBMITTED"}
            common["review_scope"] = "KGNOTE_PRODUCT_CONTRACT"
            finding = {
                "id": "finding-r-004", "severity": "blocking", "category": "semantic",
                "observation": "A real post-block-quote speaker heading is treated as quoted continuation.",
                "expected_behavior": "A real ATX speaker heading after a block quote starts a new attributed span.",
                "authority_refs": ["KG-ING-01", "KG-ING-03", "SC-21"],
                "candidate_evidence": ["src/value.txt"],
            }
            round_one = ingest(event={**common, "event_id": "round-1", "candidate_commit": first["commit"],
                "review_round": 1, "review": {"verdict": "CHANGES_REQUIRED", "findings": [finding],
                                                "native_ui_observed": False}},
                config=config, schema=schema, checkpoint_path=checkpoint)
            self.assertEqual("VALIDATED_PENDING_GITHUB_WRITEBACK", round_one["status"])
            self.assertEqual("CHANGES_REQUIRED", round_one["validated_verdict"])
            self.assertEqual("finding-r-004", round_one["findings"][0]["id"])

            second = commit("good\n", "fix: reviewer finding")
            round_two_event = {**common, "event_id": "round-2", "candidate_commit": second["commit"],
                "candidate_fingerprint": "c" * 64, "review_round": 2,
                "review": {"verdict": "PASS", "findings": [], "native_ui_observed": False}}
            passed = ingest(event=round_two_event, config=config, schema=schema, checkpoint_path=checkpoint)
            resumed = ingest(event=round_two_event, config=config, schema=schema, checkpoint_path=checkpoint)
            self.assertEqual("VALIDATED_PENDING_GITHUB_WRITEBACK", passed["status"])
            self.assertEqual("PASS", passed["validated_verdict"]); self.assertEqual(2, passed["review_round"])
            self.assertEqual(passed, resumed)
            self.assertEqual("good\n", target.read_text())
            self.assertFalse(first["remote_push_authorized"]); self.assertFalse(second["remote_push_authorized"])
