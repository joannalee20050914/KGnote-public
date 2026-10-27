from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import codex_control
import product_goal_worker_lane as LANE
import claude_reviewer_adapter as CLAUDE
from product_goal_worker_result import adapt_worker_result


class ProductGoalWorkerLaneTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.evidence_temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        self.evidence_root = Path(self.evidence_temporary.name)
        subprocess.run(["git", "init", "-b", "codex/o2-product"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        (self.repo / "seed.txt").write_text("seed\n")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=self.repo, check=True, capture_output=True)
        identity = codex_control.repository_fingerprint(self.repo)
        self.context = {
            "schema_version": "kgnote.product-goal-worker-context.v1",
            "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
            "goal_version": "2026-10-23.2-s0-s2-proposal",
            "goal_spec_sha256": "a" * 64,
            "work_item_id": "WI-O2-A-IMPLEMENT",
            "order_event_id": "o2-wi-o2-a-implement-codex-0123456789abcdef",
            "attempt_id": "attempt-o2-a-1", "stage": "codex", "provider": "codex",
            "action": "DISPATCH_IMPLEMENTATION", "repository": "owner/repo", "issue": 9,
            "candidate_commit": identity["head"], "candidate_fingerprint": identity["value"],
            "branch": "codex/o2-product", "pull_request": 33,
            "obligation_ids": ["OBL-O2-A"],
            "total_launches_before": 0, "max_total_launches": 8,
        }

    def tearDown(self):
        self.temporary.cleanup()
        self.evidence_temporary.cleanup()

    def test_codex_lane_materializes_successor_evidence_from_real_checkout(self):
        evidence = self.evidence_root / "evidence.json"

        def worker(command, **kwargs):
            (self.repo / "change.txt").write_text("changed\n")
            subprocess.run(["git", "add", "change.txt"], cwd=self.repo, check=True)
            subprocess.run(["git", "commit", "-m", "change"], cwd=self.repo, check=True, capture_output=True)
            return subprocess.CompletedProcess(command, 0, "worker output\n", "")

        verification = {
            "schema_version": "kgnote.verification-evidence.v1",
            "verification_id": "verification-test", "result": "pass",
        }
        code = LANE.run_codex(
            self.repo, self.context, evidence,
            ["/home/kgnote/.local/bin/kgnote-successor-codex"],
            runner=worker, verifier=lambda _repo: (verification, 0),
        )
        artifact = json.loads(evidence.read_text())
        self.assertEqual(0, code)
        self.assertEqual(self.context["candidate_commit"], artifact["candidate_parent"])
        self.assertNotEqual(self.context["candidate_commit"], artifact["candidate_commit"])
        self.assertEqual("PASS", artifact["verification"]["status"])

    def test_verify_and_publish_require_exact_candidate_and_github_readback(self):
        evidence = self.evidence_root / "evidence.json"
        verify_context = {**self.context, "work_item_id": "WI-O2-A-VERIFY", "stage": "publisher", "provider": "NONE", "action": "RUN_DETERMINISTIC_VERIFICATION"}
        verification = {
            "schema_version": "kgnote.verification-evidence.v1", "result": "pass",
            "fingerprint_before": {"head": self.context["candidate_commit"], "value": self.context["candidate_fingerprint"]},
            "fingerprint_after": {"head": self.context["candidate_commit"], "value": self.context["candidate_fingerprint"]},
            "fingerprint_stable": True, "evidence_readback": True,
        }
        self.assertEqual(0, LANE.run_verify(self.repo, verify_context, evidence, verifier=lambda _repo: (verification, 0)))

        publish_context = {**verify_context, "work_item_id": "WI-O2-A-PUBLISH", "stage": "push", "action": "RETRY_PUBLICATION"}
        calls = []

        def publisher(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

        readback = lambda _repository, _pull_request: {
            "headRefOid": self.context["candidate_commit"],
            "headRefName": "codex/o2-product", "state": "OPEN",
            "isDraft": True, "url": "https://example.invalid/pr/33",
        }

        self.assertEqual(0, LANE.run_publish(
            self.repo, publish_context, evidence,
            runner=publisher, github_reader=readback,
        ))
        published = json.loads(evidence.read_text())
        self.assertEqual("READ_BACK_VERIFIED", published["status"])
        self.assertEqual("/usr/bin/git", calls[0][0])
        no_pr = {**publish_context, "pull_request": None}
        branch_readback = lambda _repository, _branch: {
            "headRefOid": self.context["candidate_commit"],
            "headRefName": "codex/o2-product",
        }
        self.assertEqual(0, LANE.run_publish(
            self.repo, no_pr, evidence, runner=publisher,
            branch_reader=branch_readback,
        ))
        self.assertEqual("PUBLISHED", json.loads(evidence.read_text())["status"])
        mismatch = {**publish_context, "candidate_fingerprint": "f" * 64}
        with self.assertRaisesRegex(LANE.LaneError, "sealed candidate"):
            LANE.run_publish(
                self.repo, mismatch, evidence,
                runner=publisher, github_reader=readback,
            )

    def test_real_claude_schema_gets_deterministic_review_identity(self):
        evidence = self.evidence_root / "review.json"
        context = {**self.context, "work_item_id": "WI-O2-A-REVIEW", "stage": "claude", "provider": "claude", "action": "DISPATCH_REVIEW"}
        structured = {
            "protocol": "kgnote.product-review.v1", "repository": "owner/repo",
            "pull_request": 33, "program_id": context["goal_version"],
            "goal_id": context["goal_id"], "candidate_commit": context["candidate_commit"],
            "candidate_fingerprint": context["candidate_fingerprint"],
            "review_round": 1, "verdict": "PASS", "findings": [],
            "human_decisions": [], "native_ui_observed": False,
        }
        checkpoint = {
            "status": "COMPLETED", "review_result": structured,
            "execution_evidence": {"token_usage": None},
        }
        runtime=self.evidence_root/"runtime"; runtime.mkdir()
        checkout=runtime/"agent-loop-checkout"; checkout.mkdir()
        paths={
            "agent_loop":str(runtime/"agent-loop"),
            "agent_loop_checkout":str(checkout),
            "claude_cmd":str(runtime/"claude"),
            "codex_cmd":str(runtime/"codex"),
        }
        for name in ("agent_loop","claude_cmd","codex_cmd"):
            path=Path(paths[name]); path.write_text("#!/bin/sh\nexit 0\n"); path.chmod(0o755)
        captured=[]

        def preflight(order):
            captured.append(order)
            command, metadata=CLAUDE.build_command_with_metadata(order)
            self.assertIn("--json-schema",command)
            self.assertEqual(order.claude_facing_schema_sha256,metadata["claude_facing_schema_sha256"])
            return checkpoint

        code = LANE.run_review(
            self.repo, context, evidence,
            executor=preflight, runtime_paths=paths,
        )
        self.assertEqual(0, code)
        self.assertEqual(CLAUDE.FORMAL_REVIEW_SCHEMA_SHA256,captured[0].formal_consumer_schema_sha256)
        self.assertEqual(CLAUDE.CLAUDE_SCHEMA_PROJECTION_VERSION,captured[0].schema_projection_version)
        adapted = adapt_worker_result(context, checkpoint, returncode=0)
        self.assertEqual("REVIEW_PASS", adapted["outcome"])
        self.assertTrue(adapted["review_verdict"]["review_id"].startswith(context["order_event_id"]))
        self.assertEqual(64, len(adapted["review_verdict"]["candidate_identity_sha256"]))

    def test_review_schema_projection_mismatch_fails_before_executor(self):
        evidence=self.evidence_root/"review-mismatch.json"
        context={**self.context,"work_item_id":"WI-O2-A-REVIEW","stage":"claude","provider":"claude","action":"DISPATCH_REVIEW"}
        called=[]
        bad={
            "formal_schema_sha256":"0"*64,
            "claude_facing_schema_sha256":"1"*64,
            "projection_version":CLAUDE.CLAUDE_SCHEMA_PROJECTION_VERSION,
        }
        with patch.object(LANE,"build_claude_schema_projection",return_value=({},bad)):
            with self.assertRaisesRegex(LANE.LaneError,"metadata is inconsistent"):
                LANE.run_review(self.repo,context,evidence,executor=lambda order:called.append(order))
        self.assertEqual([],called)


if __name__ == "__main__":
    unittest.main()
