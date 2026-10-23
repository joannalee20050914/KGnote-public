from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.product_goal_worker_result import (
    WorkerResultError, adapt_worker_result, execute_and_adapt,
)


class ProductGoalWorkerResultTest(unittest.TestCase):
    def context(self, **changes):
        value = {
            "schema_version":"kgnote.product-goal-worker-context.v1",
            "goal_id":"GOAL-KGNOTE-O2-READING-EXPERIENCE",
            "goal_version":"2026-10-23.2-s0-s2-proposal",
            "goal_spec_sha256":"a"*64, "work_item_id":"WI-O2-A-IMPLEMENT",
            "order_event_id":"o2-wi-o2-a-implement-codex-0123456789abcdef",
            "attempt_id":"attempt-o2-a-1", "stage":"codex", "provider":"codex",
            "candidate_commit":"1"*40, "candidate_fingerprint":"2"*64,
            "obligation_ids":["OBL-O2-A"],
        }
        value.update(changes)
        return value

    def test_codex_success_requires_persisted_verification_and_successor_identity(self):
        artifact = {
            "schema_version":"kgnote.codex-product-goal-result.v1", "status":"COMPLETED",
            "candidate_parent":"1"*40, "candidate_commit":"3"*40,
            "candidate_fingerprint":"4"*64, "verification":{"status":"PASS"},
            "usage":{"input_tokens":10,"output_tokens":20},
        }
        result = adapt_worker_result(self.context(), artifact, returncode=0)
        self.assertEqual("COMPLETED", result["result_state"])
        self.assertEqual("WORK_COMPLETED", result["outcome"])
        self.assertEqual("3"*40, result["candidate"]["commit"])
        self.assertEqual("OBSERVED", result["usage"]["status"])
        missing = adapt_worker_result(self.context(), None, returncode=0)
        self.assertEqual("EVIDENCE_INSUFFICIENT", missing["failure_class"])

    def test_publisher_success_failure_and_candidate_mismatch(self):
        context = self.context(
            work_item_id="WI-O2-A-PUBLISH", stage="push", provider="NONE",
        )
        artifact = {
            "schema_version":"kgnote.product-goal-publication-result.v1",
            "status":"READ_BACK_VERIFIED", "candidate_commit":"1"*40,
            "candidate_fingerprint":"2"*64, "receipt_sha256":"5"*64,
        }
        result = adapt_worker_result(context, artifact, returncode=0)
        self.assertEqual("READ_BACK_VERIFIED", result["publication"]["status"])
        branch_only = adapt_worker_result(
            {**context, "pull_request": None},
            {**artifact, "status": "PUBLISHED", "pull_request": None},
            returncode=0,
        )
        self.assertEqual("PUBLISHED", branch_only["publication"]["status"])
        failed = adapt_worker_result(context, {**artifact,"status":"FAILED"}, returncode=0)
        self.assertEqual("PUBLICATION_FAILED", failed["failure_class"])
        failed_process = adapt_worker_result(context, None, returncode=2, stderr=b"push failed")
        self.assertEqual("PUBLICATION_FAILED", failed_process["failure_class"])
        mismatch = adapt_worker_result(context, {**artifact,"candidate_commit":"6"*40}, returncode=0)
        self.assertEqual("EVIDENCE_INSUFFICIENT", mismatch["failure_class"])

    def test_claude_pass_changes_required_429_and_missing_verdict(self):
        context = self.context(
            work_item_id="WI-O2-A-REVIEW", stage="claude", provider="claude",
        )
        base = {
            "review_id":"review-o2-a-1", "reviewed_commit":"1"*40,
            "reviewed_fingerprint":"2"*64, "candidate_identity_sha256":"7"*64,
            "findings":[],
        }
        passed = adapt_worker_result(context, {**base,"verdict":"PASS"}, returncode=0)
        self.assertEqual("REVIEW_PASS", passed["outcome"])
        changed = adapt_worker_result(
            context, {**base,"verdict":"CHANGES_REQUIRED","findings":[{"id":"f-1"}]},
            returncode=0,
        )
        self.assertEqual("REVIEW_CHANGES_REQUIRED", changed["outcome"])
        self.assertEqual([{"id":"f-1"}], changed["review_findings"])
        limited = adapt_worker_result(context, None, returncode=1, stderr=b"HTTP 429 rate limit")
        self.assertEqual("RATE_LIMITED", limited["failure_class"])
        no_verdict = adapt_worker_result(context, base, returncode=0)
        self.assertEqual("EVIDENCE_INSUFFICIENT", no_verdict["failure_class"])

    def test_saved_result_replays_without_duplicate_worker_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); evidence=root/"evidence.json"; result_path=root/"result.json"
            artifact = {
                "schema_version":"kgnote.codex-product-goal-result.v1", "status":"COMPLETED",
                "candidate_parent":"1"*40, "candidate_commit":"3"*40,
                "candidate_fingerprint":"4"*64, "verification":{"status":"PASS"},
            }
            evidence.write_text(json.dumps(artifact))
            calls=[]
            runner=lambda command,**kwargs: calls.append(command) or subprocess.CompletedProcess(command,0,"raw","err")
            args = dict(
                context=self.context(), command=["/usr/bin/true"], evidence_path=evidence,
                result_path=result_path, stdout_path=root/"stdout", stderr_path=root/"stderr",
                runner=runner,
            )
            first=execute_and_adapt(**args); second=execute_and_adapt(**args)
            self.assertEqual(first,second); self.assertEqual(1,len(calls))

    def test_saved_result_with_different_attempt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); result_path=root/"result.json"
            result_path.write_text(json.dumps({
                "schema_version":"kgnote.product-goal-worker-result.v1",
                **{key:value for key,value in self.context().items() if key != "schema_version"},
                "attempt_id":"other-attempt",
            }))
            with self.assertRaisesRegex(WorkerResultError,"different attempt"):
                execute_and_adapt(
                    self.context(), ["/usr/bin/true"], evidence_path=root/"missing",
                    result_path=result_path, stdout_path=root/"stdout", stderr_path=root/"stderr",
                )


if __name__ == "__main__":
    unittest.main()
