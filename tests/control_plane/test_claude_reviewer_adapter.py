import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("adapter", ROOT / "scripts/claude_reviewer_adapter.py")
ADAPTER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = ADAPTER
SPEC.loader.exec_module(ADAPTER)


class ClaudeReviewerAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        for name in ("agent-loop", "claude", "codex"):
            path = root / name
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        self.value = {
            "goal_id":"goal", "repository": "example/repo", "issue": 7, "pull_request": 9,
            "candidate_commit": "a" * 40, "candidate_fingerprint": "b" * 64,
            "review_round_used": 2, "review_round_limit": 5, "timeout_seconds": 10,
            "checkpoint_path": str(root / "checkpoint.json"),
            "agent_loop": str(root / "agent-loop"), "agent_loop_checkout": str(root),
            "claude_cmd": str(root / "claude"), "codex_cmd": str(root / "codex"),
            "allow_live_write": False, "safety_baseline_verified": False,
            "review_only_live": False,
            "requested_model":"sonnet", "requested_effort":"medium", "requested_provider":"Anthropic",
        }

    def tearDown(self):
        self.temp.cleanup()

    def order(self, **changes):
        return ADAPTER.WorkOrder.from_dict({**self.value, **changes})

    def test_command_has_bounded_roles_rounds_and_no_merge(self):
        command = ADAPTER.build_command(self.order())
        self.assertIn("codex", command)
        self.assertIn("claude", command)
        self.assertEqual("3", command[command.index("--max-rounds") + 1])
        self.assertIn("--dry-run", command)
        self.assertNotIn("--auto-merge", command)
        self.assertNotIn("--dangerous-agent-permissions", command)

    def test_pr_23_is_always_rejected(self):
        with self.assertRaisesRegex(ADAPTER.AdapterError, "PR #23"):
            self.order(pull_request=23)

    def test_review_only_live_requires_verified_baseline_and_omits_dry_run(self):
        with self.assertRaisesRegex(ADAPTER.AdapterError, "verified safety baseline"):
            self.order(review_only_live=True)
        command = ADAPTER.build_command(self.order(review_only_live=True, safety_baseline_verified=True))
        self.assertEqual("sonnet", command[command.index("--model") + 1])
        self.assertEqual("medium", command[command.index("--effort") + 1])
        self.assertNotIn("--dry-run", command)
        self.assertNotIn("--auto-merge", command)
        self.assertFalse(self.order(review_only_live=True, safety_baseline_verified=True).allow_live_write)

    def test_exhausted_budget_is_rejected(self):
        with self.assertRaisesRegex(ADAPTER.AdapterError, "budget"):
            self.order(review_round_used=5)

    def test_live_agent_loop_coder_write_is_always_rejected(self):
        with self.assertRaisesRegex(ADAPTER.AdapterError, "trusted_candidate_publisher"):
            self.order(allow_live_write=True)

    def test_wrong_pin_is_rejected_before_agent_launch(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "0" * 40 + "\n", "")
        with self.assertRaisesRegex(ADAPTER.AdapterError, "pinned commit"):
            ADAPTER.execute(self.order(), runner, auth_checker=lambda _path: {"status": "PASS"})
        self.assertEqual(1, len(calls))

    def test_timeout_writes_fail_closed_checkpoint(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            if command[0] == "git":
                return subprocess.CompletedProcess(command, 0, ADAPTER.PINNED_AGENT_LOOP_COMMIT + "\n", "")
            if command[-1] == "--version":
                return subprocess.CompletedProcess(command, 0, "2.1.302 (Claude Code)\n", "")
            raise subprocess.TimeoutExpired(command, 10, output="partial", stderr="late")
        order = self.order()
        result = ADAPTER.execute(order, runner, auth_checker=lambda _path: {"status": "PASS"})
        self.assertEqual("FAILED_CLOSED", result["status"])
        self.assertEqual("timeout", result["reason"])
        saved = json.loads(order.checkpoint_path.read_text())
        self.assertFalse(saved["product_review_accepted"])
        self.assertEqual(3, len(calls))

    def test_exit_zero_never_claims_product_acceptance(self):
        def runner(command, **kwargs):
            stdout = ADAPTER.PINNED_AGENT_LOOP_COMMIT + "\n" if command[0] == "git" else ("2.1.302 (Claude Code)\n" if command[-1] == "--version" else "ok")
            return subprocess.CompletedProcess(command, 0, stdout, "")
        result = ADAPTER.execute(self.order(), runner, auth_checker=lambda _path: {"status": "PASS"})
        self.assertEqual("COMPLETED", result["status"])
        self.assertFalse(result["product_review_accepted"])

    def test_exact_candidate_round_is_single_use_and_resume_safe(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            stdout = ADAPTER.PINNED_AGENT_LOOP_COMMIT + "\n" if command[0] == "git" else ("2.1.302 (Claude Code)\n" if command[-1] == "--version" else "ok")
            return subprocess.CompletedProcess(command, 0, stdout, "")
        order = self.order()
        first = ADAPTER.execute(order, runner, auth_checker=lambda _path: {"status":"PASS"})
        second = ADAPTER.execute(order, runner, auth_checker=lambda _path: {"status":"PASS"})
        self.assertEqual("COMPLETED", first["status"])
        self.assertEqual("ALREADY_COMPLETED", second["status"])
        self.assertEqual(3, len(calls))
        with self.assertRaisesRegex(ADAPTER.AdapterError, "different exact candidate"):
            ADAPTER.execute(self.order(candidate_commit="c" * 40), runner, auth_checker=lambda _path: {"status":"PASS"})

    def test_model_usage_confirms_sonnet_and_preserves_token_usage(self):
        order=self.order(review_only_live=True,safety_baseline_verified=True)
        envelope={"usage":{"input_tokens":3,"output_tokens":5},"modelUsage":{"claude-sonnet-5-5":{"canonicalModel":"claude-sonnet-5-5","provider":"firstParty"}}}
        evidence=ADAPTER.model_execution_evidence(order,cli_version="2.1.302 (Claude Code)",auth={"auth_method":"claude.ai"},envelope=envelope)
        self.assertEqual("EFFECTIVE_CONFIRMED",evidence["effective_status"])
        self.assertEqual(["claude-sonnet-5-5"],evidence["actual_models"])
        self.assertEqual(5,evidence["token_usage"]["output_tokens"])

    def test_model_usage_mismatch_is_explicit(self):
        order=self.order(review_only_live=True,safety_baseline_verified=True)
        envelope={"usage":{},"modelUsage":{"claude-opus-5-5":{"canonicalModel":"claude-opus-5-5","provider":"firstParty"}}}
        evidence=ADAPTER.model_execution_evidence(order,cli_version="2.1.302 (Claude Code)",auth={},envelope=envelope)
        self.assertEqual("MODEL_MISMATCH",evidence["effective_status"])
        self.assertIn("claude-opus-5-5",evidence["effective_reason"])

    def test_completed_review_with_model_mismatch_fails_closed_before_consumption(self):
        envelope={
            "structured_output":{"verdict":"PASS"}, "usage":{"output_tokens":1},
            "modelUsage":{"claude-opus-5-5":{"canonicalModel":"claude-opus-5-5","provider":"firstParty"}},
        }
        def runner(command, **kwargs):
            if command[0] == "git":
                stdout=ADAPTER.PINNED_AGENT_LOOP_COMMIT+"\n"
            elif command[-1] == "--version":
                stdout="2.1.302 (Claude Code)\n"
            else:
                stdout=json.dumps(envelope)
            return subprocess.CompletedProcess(command,0,stdout,"")
        result=ADAPTER.execute(
            self.order(review_only_live=True,safety_baseline_verified=True), runner,
            auth_checker=lambda _path:{"auth_method":"claude.ai","api_provider":"firstParty","subscription_type":"pro"},
        )
        self.assertEqual("FAILED_CLOSED",result["status"])
        self.assertEqual("MODEL_MISMATCH",result["execution_evidence"]["effective_status"])
        self.assertFalse(result["product_review_accepted"])


if __name__ == "__main__":
    unittest.main()
