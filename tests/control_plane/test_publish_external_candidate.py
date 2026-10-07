from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_external_candidate as PUBLISH  # noqa: E402


class PublicationTransitionTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "enabled": True, "canonical_repository": "owner/public",
            "candidate_repository": "owner/public", "trigger_repository": "owner/public",
            "review_request_repository": "owner/public", "archive_repository": "owner/archive",
            "review_pr_number": 1, "request_marker": "REQUEST_V2",
        }
        self.state = {"candidate_commit": "a" * 40, "candidate_fingerprint": "b" * 64, "review_round": 2}
        marker = PUBLISH.request_marker(self.config, self.state)
        self.snapshot = {
            "repository": "owner/public", "pull_request": 1, "remote_head": "a" * 40,
            "candidate_fingerprint": "b" * 64, "request_marker": "REQUEST_V2",
            "body": marker, "state": "OPEN", "artifact_url": "https://example/pr/1",
        }

    def test_exact_remote_snapshot_passes(self):
        self.assertEqual([], PUBLISH.remote_snapshot_errors(self.config, self.state, self.snapshot))

    def test_command_runner_preserves_leading_porcelain_status_column(self):
        completed = mock.Mock(returncode=0, stdout=" M .ai/ORCHESTRATION_HISTORY/events.jsonl\n", stderr="")
        with mock.patch.object(PUBLISH.subprocess, "run", return_value=completed):
            output = PUBLISH._run(["git", "status", "--porcelain"], cwd=ROOT)
        self.assertTrue(output.startswith(" M .ai/"))

    def test_fresh_process_resolves_exact_candidate_only_from_pr_and_recomputed_fingerprint(self):
        observed = {"headRefOid": "a" * 40, "body": self.snapshot["body"]}
        self.assertEqual(self.state, PUBLISH.resolve_pr_candidate(self.config, observed, "b" * 64))
        with self.assertRaises(PUBLISH.PublicationError):
            PUBLISH.resolve_pr_candidate(self.config, observed, "c" * 64)

    def test_republication_replaces_stale_request_marker(self):
        old_state = {**self.state, "candidate_commit": "c" * 40}
        body = "PR\n\n" + PUBLISH.request_marker(self.config, old_state) + "\n"
        cleaned = PUBLISH.without_request_markers(self.config, body)
        self.assertEqual("PR", cleaned)

    def test_wrong_repo_stale_head_missing_marker_and_fingerprint_fail_closed(self):
        for field, value in (("repository", "owner/archive"), ("remote_head", "c" * 40),
                             ("candidate_fingerprint", "d" * 64), ("body", "no marker")):
            with self.subTest(field=field):
                snapshot = {**self.snapshot, field: value}
                self.assertTrue(PUBLISH.remote_snapshot_errors(self.config, self.state, snapshot))

    def test_publish_executes_push_readback_and_durable_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir(); (repo / ".git").mkdir()
            (repo / ".ai/github-product-reviewer.json").write_text(json.dumps(self.config))
            state = {**self.state, "publication": {"status": "PENDING"}}
            (repo / ".ai/external-review-state.json").write_text(json.dumps(state))
            marker = PUBLISH.request_marker(self.config, state)
            calls = []
            def runner(command, *, cwd):
                calls.append(command)
                if command[:3] == ["git", "rev-parse", "HEAD"]: return "a" * 40
                if command[:3] == ["git", "status", "--porcelain"]:
                    return " M .ai/ORCHESTRATION_HISTORY/events.jsonl\n?? .ai/ORCHESTRATOR.lock"
                if command[:4] == ["git", "remote", "get-url", "origin"]: return "https://github.com/owner/public.git"
                if command[:3] == ["git", "branch", "--show-current"]: return "codex/candidate"
                if command[:3] == ["gh", "pr", "view"] and command[-1] == "body": return json.dumps({"body": "PR"})
                if command[:3] == ["gh", "pr", "edit"]: return ""
                if command[:3] == ["git", "push", "origin"]: return ""
                if command[:3] == ["gh", "pr", "view"]:
                    return json.dumps({"headRefOid": "a" * 40, "body": "PR\n" + marker, "state": "OPEN", "url": "https://example/pr/1"})
                raise AssertionError(command)
            with mock.patch.object(PUBLISH.codex_control, "repository_fingerprint", return_value={"value": "b" * 64}):
                result = PUBLISH.publish(repo, runner)
            self.assertEqual("PUBLISHED", result["status"])
            self.assertTrue(any(command[:3] == ["git", "push", "origin"] for command in calls))
            recorded = json.loads((repo / ".ai/external-review-state.json").read_text())
            self.assertEqual("AWAITING_EXTERNAL_PRODUCT_REVIEW", recorded["phase"])

    def test_failed_push_does_not_record_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / ".ai").mkdir(); (repo / ".git").mkdir()
            (repo / ".ai/github-product-reviewer.json").write_text(json.dumps(self.config))
            (repo / ".ai/external-review-state.json").write_text(json.dumps({**self.state, "publication": {"status": "PENDING"}}))
            def runner(command, *, cwd):
                if command[:3] == ["git", "rev-parse", "HEAD"]: return "a" * 40
                if command[:3] == ["git", "status", "--porcelain"]: return ""
                if command[:4] == ["git", "remote", "get-url", "origin"]: return "https://github.com/owner/public.git"
                if command[:3] == ["git", "branch", "--show-current"]: return "codex/candidate"
                if command[:3] == ["gh", "pr", "view"]: return json.dumps({"body": PUBLISH.request_marker(self.config, self.state)})
                if command[:3] == ["git", "push", "origin"]: raise PUBLISH.PublicationError("push failed")
                raise AssertionError(command)
            with mock.patch.object(PUBLISH.codex_control, "repository_fingerprint", return_value={"value": "b" * 64}), self.assertRaises(PUBLISH.PublicationError):
                PUBLISH.publish(repo, runner)
            recorded = json.loads((repo / ".ai/external-review-state.json").read_text())
            self.assertEqual("PENDING", recorded["publication"]["status"])

    def test_uncommitted_candidate_files_fail_before_remote_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / ".ai").mkdir(); (repo / ".git").mkdir()
            (repo / ".ai/github-product-reviewer.json").write_text(json.dumps(self.config))
            (repo / ".ai/external-review-state.json").write_text(json.dumps(self.state))
            commands = []
            def runner(command, *, cwd):
                commands.append(command)
                if command[:3] == ["git", "rev-parse", "HEAD"]: return "a" * 40
                if command[:3] == ["git", "status", "--porcelain"]:
                    return " M src/product.py\n M CODEX_STATUS.md\n?? .ai/REVIEW_HISTORY/review-001/result.md"
                raise AssertionError(command)
            with mock.patch.object(PUBLISH.codex_control, "repository_fingerprint", return_value={"value": "b" * 64}), self.assertRaisesRegex(PUBLISH.PublicationError, "src/product.py"):
                PUBLISH.publish(repo, runner)
            self.assertFalse(any(command[:2] == ["git", "push"] for command in commands))


if __name__ == "__main__":
    unittest.main()
