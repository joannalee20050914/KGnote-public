import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("adapter", ROOT / "scripts/claude_reviewer_adapter.py")
ADAPTER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = ADAPTER
SPEC.loader.exec_module(ADAPTER)


class ClaudeReviewerAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        _, projection = ADAPTER.build_claude_schema_projection()
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
            "program_id":"program-test-goal-review-v1",
            "review_scope":"the exact sealed B-scheme acceptance criteria",
            "review_authority_paths":["AGENTS.md","PLAN.md",".ai/REVIEW_REQUEST.md"],
            "formal_consumer_schema_sha256":ADAPTER.FORMAL_REVIEW_SCHEMA_SHA256,
            "claude_facing_schema_sha256":projection["claude_facing_schema_sha256"],
            "schema_projection_version":ADAPTER.CLAUDE_SCHEMA_PROJECTION_VERSION,
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

    def _deployed_schema_layout(self, *, formal: bytes | None = None):
        root = Path(self.temp.name) / "deployed"
        adapter_path = root / "runtime" / "claude_reviewer_adapter.py"
        adapter_path.parent.mkdir(parents=True)
        adapter_path.write_text("# deployed adapter placeholder\n")
        legacy_path = root / "final-smoke" / "review-result.cli.schema.json"
        legacy_path.parent.mkdir(parents=True)
        legacy_path.write_text(json.dumps({"type": "object", "$defs": {}, "properties": {}}))
        if formal is not None:
            formal_path = adapter_path.parent / ADAPTER.FORMAL_REVIEW_SCHEMA_RELATIVE_PATH
            formal_path.parent.mkdir(parents=True)
            formal_path.write_bytes(formal)
        return adapter_path, legacy_path

    def test_o2_projects_formal_schema_when_legacy_schema_also_exists(self):
        formal = (ROOT / ADAPTER.FORMAL_REVIEW_SCHEMA_RELATIVE_PATH).read_bytes()
        adapter_path, legacy_path = self._deployed_schema_layout(formal=formal)
        self.assertTrue(legacy_path.is_file())
        with mock.patch.object(ADAPTER, "__file__", str(adapter_path)):
            _, metadata = ADAPTER.build_claude_schema_projection(adapter_path)
            command = ADAPTER.build_command(
                self.order(
                    review_only_live=True,
                    safety_baseline_verified=True,
                    claude_facing_schema_sha256=metadata["claude_facing_schema_sha256"],
                )
            )
        selected = json.loads(command[command.index("--json-schema") + 1])
        self.assertEqual("object", selected["type"])
        self.assertFalse(selected["additionalProperties"])
        self.assertNotIn("allOf", selected)
        self.assertNotIn("$defs", selected)
        self.assertTrue(ADAPTER.CLAUDE_REQUIRED_REVIEW_FIELDS <= set(selected["required"]))
        self.assertIn("human_decisions", selected["properties"])

    def test_o2_rejects_missing_or_damaged_formal_schema_without_legacy_fallback(self):
        adapter_path, legacy_path = self._deployed_schema_layout()
        self.assertTrue(legacy_path.is_file())
        with mock.patch.object(ADAPTER, "__file__", str(adapter_path)):
            with self.assertRaisesRegex(ADAPTER.AdapterError, "formal review schema unavailable"):
                ADAPTER.build_command(
                    self.order(review_only_live=True, safety_baseline_verified=True)
                )
            formal_path = adapter_path.parent / ADAPTER.FORMAL_REVIEW_SCHEMA_RELATIVE_PATH
            formal_path.parent.mkdir(parents=True)
            formal_path.write_text("{damaged")
            with self.assertRaisesRegex(ADAPTER.AdapterError, "digest mismatch"):
                ADAPTER.build_command(
                    self.order(review_only_live=True, safety_baseline_verified=True)
                )

    def test_projected_schema_defers_conditional_rules_to_formal_consumer_schema(self):
        command = ADAPTER.build_command(
            self.order(review_only_live=True, safety_baseline_verified=True)
        )
        facing_schema = json.loads(command[command.index("--json-schema") + 1])
        facing_validator = Draft202012Validator(facing_schema)
        formal_validator = Draft202012Validator(ADAPTER.load_formal_consumer_schema())
        result = {
            "protocol": "kgnote.product-review.v1",
            "repository": "example/repo",
            "pull_request": 9,
            "program_id": "program-test-goal-review-v1",
            "goal_id": "goal",
            "candidate_fingerprint": "b" * 64,
            "candidate_commit": "a" * 40,
            "review_round": 3,
            "verdict": "PRODUCT_DECISION_REQUIRED",
            "findings": [{
                "id": "finding-decision",
                "severity": "blocking",
                "category": "product_intent",
                "observation": "authority is insufficient",
                "expected_behavior": "obtain a human decision",
                "authority_refs": ["PLAN.md"],
                "candidate_evidence": ["candidate evidence"],
            }],
            "human_decisions": [{
                "decision_id": "D-100",
                "question": "Which behavior is intended?",
                "why_existing_authority_is_insufficient": "The alternatives conflict.",
                "affected_requirements": ["KG-GOV-04"],
                "available_options": ["A", "B"],
                "observable_consequences": ["Outcome A", "Outcome B"],
                "blocking_scope": ["O2 review"],
                "linked_findings": ["finding-decision"],
            }],
            "native_ui_observed": False,
        }
        self.assertEqual([], list(facing_validator.iter_errors(result)))
        self.assertEqual([], list(formal_validator.iter_errors(result)))
        missing = {**result}
        missing.pop("human_decisions")
        self.assertTrue(list(facing_validator.iter_errors(missing)))
        self.assertTrue(list(formal_validator.iter_errors(missing)))
        empty_decision = {**result, "human_decisions": []}
        self.assertEqual([], list(facing_validator.iter_errors(empty_decision)))
        self.assertTrue(list(formal_validator.iter_errors(empty_decision)))
        for verdict in ("PASS", "CHANGES_REQUIRED"):
            invalid = {**result, "verdict": verdict}
            self.assertEqual([], list(facing_validator.iter_errors(invalid)))
            self.assertTrue(list(formal_validator.iter_errors(invalid)))

    def test_projection_recursively_removes_unsupported_keywords_and_is_deterministic(self):
        first, first_metadata = ADAPTER.build_claude_schema_projection()
        second, second_metadata = ADAPTER.build_claude_schema_projection()
        self.assertEqual(first, second)
        self.assertEqual(first_metadata, second_metadata)

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & ADAPTER.CLAUDE_UNSUPPORTED_SCHEMA_KEYWORDS)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(first)
        self.assertEqual(ADAPTER.FORMAL_REVIEW_SCHEMA_SHA256, first_metadata["formal_schema_sha256"])
        self.assertEqual(ADAPTER.CLAUDE_SCHEMA_PROJECTION_VERSION, first_metadata["projection_version"])
        self.assertEqual(64, len(first_metadata["claude_facing_schema_sha256"]))
        self.assertGreater(first_metadata["removed_keyword_counts"]["allOf"], 0)
        self.assertIn("#/$defs/finding", first_metadata["inlined_local_refs"])

    def test_projection_rejects_external_cyclic_and_unknown_schema_shapes(self):
        cases = (
            ({"type":"object","properties":{"x":{"$ref":"https://example.test/x"}},"required":["x"],"additionalProperties":False}, "external reference"),
            ({"type":"object","properties":{"x":{"$ref":"#/$defs/x"}},"required":["x"],"additionalProperties":False,"$defs":{"x":{"$ref":"#/$defs/x"}}}, "cyclic reference"),
            ({"type":"object","properties":{"x":{"type":"string","format":"mystery"}},"required":["x"],"additionalProperties":False}, "no rule for format"),
        )
        for formal, message in cases:
            with self.subTest(message=message), mock.patch.object(
                ADAPTER, "load_formal_consumer_schema", return_value=formal
            ), self.assertRaisesRegex(ADAPTER.AdapterError, message):
                ADAPTER.build_claude_schema_projection()

    def test_projection_or_digest_failure_precedes_auth_and_model_process(self):
        calls = []
        auth_calls = []
        order = self.order(review_only_live=True, safety_baseline_verified=True)
        with mock.patch.object(
            ADAPTER, "build_claude_schema_projection",
            side_effect=ADAPTER.AdapterError("projection failed"),
        ), self.assertRaisesRegex(ADAPTER.AdapterError, "projection failed"):
            ADAPTER.execute(
                order,
                lambda command, **kwargs: calls.append(command),
                auth_checker=lambda path: auth_calls.append(path),
            )
        self.assertEqual([], calls)
        self.assertEqual([], auth_calls)

        with self.assertRaisesRegex(ADAPTER.AdapterError, "digest admission"):
            self.order(
                review_only_live=True,
                safety_baseline_verified=True,
                formal_consumer_schema_sha256="0" * 64,
            )

    def test_legacy_agent_loop_order_remains_dry_run_compatible(self):
        command = ADAPTER.build_command(self.order(review_only_live=False))
        self.assertIn("--dry-run", command)
        self.assertNotIn("--json-schema", command)

    def test_review_only_prompt_uses_exact_order_scope_without_legacy_hardcoding(self):
        command = ADAPTER.build_command(
            self.order(review_only_live=True, safety_baseline_verified=True)
        )
        prompt = command[-1]
        self.assertIn("program_id=program-test-goal-review-v1", prompt)
        self.assertIn("the exact sealed B-scheme acceptance criteria", prompt)
        self.assertIn(".ai/REVIEW_REQUEST.md", prompt)
        self.assertNotIn("finding-r-004", prompt)
        self.assertNotIn("source-library-successor", prompt)

    def test_review_authority_paths_reject_escape(self):
        with self.assertRaisesRegex(ADAPTER.AdapterError, "repository-relative"):
            self.order(review_authority_paths=["../other-repo"])

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

    def test_structured_429_preserves_usage_but_never_creates_a_verdict(self):
        order = self.order(review_only_live=True, safety_baseline_verified=True)
        envelope = {
            "api_error_status": 429,
            "api_error": "usage_limit_reached",
            "is_error": True,
            "usage": {"input_tokens": 4, "output_tokens": 12},
            "modelUsage": {
                "claude-sonnet-5-5": {
                    "canonicalModel": "claude-sonnet-5-5", "provider": "firstParty"
                }
            },
        }
        def runner(command, **kwargs):
            if command[0] == "git":
                return subprocess.CompletedProcess(
                    command, 0, ADAPTER.PINNED_AGENT_LOOP_COMMIT + "\n", ""
                )
            if command[-1] == "--version":
                return subprocess.CompletedProcess(command, 0, "2.1.302 (Claude Code)\n", "")
            return subprocess.CompletedProcess(command, 1, json.dumps(envelope), "")
        result = ADAPTER.execute(
            order, runner,
            auth_checker=lambda _path: {
                "auth_method": "claude.ai", "api_provider": "firstParty",
                "subscription_type": "pro",
            },
        )
        self.assertEqual("FAILED_CLOSED", result["status"])
        self.assertEqual("quota_exhausted", result["reason"])
        self.assertEqual(12, result["execution_evidence"]["token_usage"]["output_tokens"])
        self.assertEqual("EFFECTIVE_CONFIRMED", result["execution_evidence"]["effective_status"])
        self.assertNotIn("review_result", result)
        self.assertFalse(result["product_review_accepted"])

    def test_structured_schema_400_is_interface_admission_failure_without_inference(self):
        order = self.order(review_only_live=True, safety_baseline_verified=True)
        envelope = {
            "api_error_status": 400,
            "is_error": True,
            "result": "API Error: 400 tools.8.custom.input_schema: input_schema does not support allOf at the top level",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "modelUsage": {},
        }
        def runner(command, **kwargs):
            if command[0] == "git":
                return subprocess.CompletedProcess(
                    command, 0, ADAPTER.PINNED_AGENT_LOOP_COMMIT + "\n", ""
                )
            if command[-1] == "--version":
                return subprocess.CompletedProcess(command, 0, "2.1.302 (Claude Code)\n", "")
            return subprocess.CompletedProcess(command, 1, json.dumps(envelope), "")
        result = ADAPTER.execute(
            order,
            runner,
            auth_checker=lambda _path: {
                "auth_method": "claude.ai", "api_provider": "firstParty",
                "subscription_type": "pro",
            },
        )
        self.assertEqual("FAILED_CLOSED", result["status"])
        self.assertEqual("schema_provider_interface_admission_failure", result["reason"])
        self.assertTrue(result["model_invocation_started"])
        self.assertFalse(result["model_inference_occurred"])
        self.assertEqual(400, result["provider_error_status"])
        self.assertNotIn("review_result", result)
        self.assertFalse(result["product_review_accepted"])


if __name__ == "__main__":
    unittest.main()
