from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import codex_control
import product_goal_worker_lane as LANE
import linux_worker_router as ROUTER
import product_goal_runtime_admission as RUNTIME_ADMISSION
import claude_reviewer_adapter as CLAUDE
from product_goal_worker_result import adapt_worker_result
from tests.control_plane.runtime_admission_fixtures import runtime_identity


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
            admitter=lambda _repo, _context, _evidence: ({
                "status":"PASS", "context_sha256":"a"*64,
                "runner_context_sha256":"b"*64, "versions":{},
            }, {}),
        )
        artifact = json.loads(evidence.read_text())
        self.assertEqual(0, code)
        self.assertEqual(self.context["candidate_commit"], artifact["candidate_parent"])
        self.assertNotEqual(self.context["candidate_commit"], artifact["candidate_commit"])
        self.assertEqual("PASS", artifact["verification"]["status"])

    def test_codex_environment_admission_seals_context_and_pinned_tools(self):
        evidence = self.evidence_root / "evidence" / "attempt.json"
        tools = self.evidence_root / "tools"; tools.mkdir()
        node=tools/"node"; npm=tools/"npm"; gh=tools/"gh"; codex_js=tools/"codex.js"
        python=self.repo/".venv/bin/python"; python.parent.mkdir(parents=True)
        for path in (node,npm,gh,codex_js,python):
            path.write_text("#!/bin/sh\nexit 0\n"); path.chmod(0o755)
        lock = self.repo / LANE.REQUIREMENTS_LOCK
        lock.write_text((ROOT / "requirements-runtime.lock").read_text())
        locked = LANE._locked_dependencies(lock)
        identity = codex_control.repository_fingerprint(self.repo)
        self.context.update({
            "candidate_commit": identity["head"],
            "candidate_fingerprint": identity["value"],
        })
        sealed_context = {
            **self.context,
            "schema_version": LANE.CONTEXT_SCHEMA,
            "runner_context": {"source": "test-runner-projection"},
            "runtime_identity": runtime_identity(),
        }
        def probe(command, *, repo):
            if command[0] == str(python) and command[1] == "--version": return "Python 3.12.3"
            if command[0] == str(node) and command[1] == "--version": return "v24.12.0"
            if command[0] == str(node): return "codex-cli 0.146.0"
            if command[0] == str(npm): return "11.6.2"
            if command[0] == str(gh): return "gh version 2.103.2 (test)"
            if command[0] == "/usr/bin/git": return "git version 2.43.0"
            if command[:4] == [str(python), "-m", "pip", "check"]:
                return "No broken requirements found."
            if command[0] == str(python):
                return json.dumps({**locked, "pip": "24.0"})
            self.fail(command)
        generation=Path(sealed_context["runtime_identity"]["generation"])
        observed_checkout={
            **identity,"commit":identity["head"],"fingerprint":identity["value"],
            "pull_request":33,
        }
        with patch.object(LANE,"GUEST_NODE",str(node)), patch.object(LANE,"GUEST_NPM",str(npm)), patch.object(LANE,"GUEST_GH",str(gh)), patch.object(LANE,"GUEST_CODEX_JS",str(codex_js)), patch.object(LANE,"_probe",side_effect=probe), patch.object(LANE,"validate_context",return_value=sealed_context), patch.object(LANE,"require_live_runtime_identity",return_value=sealed_context["runtime_identity"]), patch.object(LANE,"_observed_checkout",return_value=observed_checkout), patch.object(LANE,"__file__",str(generation/"product_goal_worker_lane.py")):
            receipt,env=LANE.admit_codex_development_environment(self.repo,sealed_context,evidence)
        self.assertEqual("PASS",receipt["status"])
        self.assertEqual("v24.12.0",receipt["versions"]["node"])
        self.assertEqual(receipt["context_sha256"],env["KGNOTE_PRODUCT_GOAL_CONTEXT_SHA256"])
        self.assertTrue(Path(env["KGNOTE_PRODUCT_GOAL_CONTEXT"]).is_file())
        self.assertEqual(str(python),env["KGNOTE_TEST_PYTHON"])
        self.assertEqual(locked, receipt["dependency_probe"]["observed"])
        self.assertEqual(
            hashlib.sha256(lock.read_bytes()).hexdigest(),
            receipt["dependency_probe"]["requirements_lock_sha256"],
        )
        self.assertEqual(str(lock), receipt["dependency_probe"]["requirements_lock_path"])

    def test_codex_environment_admission_uses_deployed_lock_when_checkout_has_none(self):
        runtime = self.evidence_root / "runtime"
        runtime.mkdir()
        lane = runtime / "product_goal_worker_lane.py"
        lane.write_text("# deployed lane\n")
        lock = runtime / LANE.REQUIREMENTS_LOCK
        lock.write_text("jsonschema==4.26.0\n")
        with patch.object(LANE, "__file__", str(lane)):
            self.assertEqual(lock.resolve(), LANE._runtime_requirements_lock(self.repo))

    def test_codex_environment_admission_rejects_missing_deployed_lock(self):
        runtime = self.evidence_root / "runtime"
        runtime.mkdir()
        lane = runtime / "product_goal_worker_lane.py"
        lane.write_text("# deployed lane\n")
        with patch.object(LANE, "__file__", str(lane)):
            with self.assertRaisesRegex(LANE.LaneError, "deployed requirements-runtime.lock"):
                LANE._runtime_requirements_lock(self.repo)

    def test_codex_environment_admission_rejects_dependency_lock_drift(self):
        python = self.repo / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\nexit 0\n"); python.chmod(0o755)
        (self.repo / LANE.REQUIREMENTS_LOCK).write_text("jsonschema==4.26.0\n")
        with patch.object(
            LANE, "_probe",
            return_value=json.dumps({"jsonschema": "4.25.0", "unexpected": "1.0", "pip": "24.0"}),
        ):
            with self.assertRaisesRegex(
                LANE.LaneError,
                "mismatched=\\['jsonschema'\\].*unexpected=\\['unexpected'\\]",
            ):
                LANE._admit_locked_dependencies(python, self.repo)

    def test_exact_environment_rejects_wrong_checkout_before_tool_probe(self):
        observed = {
            "commit": "f" * 40,
            "fingerprint": self.context["candidate_fingerprint"],
            "branch": self.context["branch"],
            "pull_request": self.context["pull_request"],
            "tree": "e" * 40,
        }
        with patch.object(LANE, "_observed_checkout", return_value=observed), patch.object(
            LANE, "_probe",
        ) as probe:
            with self.assertRaisesRegex(LANE.LaneError, "admitted candidate"):
                LANE._admit_exact_environment(self.repo, {
                    "commit": self.context["candidate_commit"],
                    "fingerprint": self.context["candidate_fingerprint"],
                    "branch": self.context["branch"],
                    "pull_request": self.context["pull_request"],
                })
        probe.assert_not_called()

    def test_admission_landlock_probe_failure_never_writes_pass_or_starts_model(self):
        runtime = runtime_identity()
        request = {
            "schema_version": RUNTIME_ADMISSION.DEPLOYMENT_REQUEST_SCHEMA,
            "admission_kind": RUNTIME_ADMISSION.DEPLOYMENT_ACCEPTANCE,
            "execution_direction_id": RUNTIME_ADMISSION.EXECUTION_DIRECTION_ID,
            "product_goal_id": RUNTIME_ADMISSION.PRODUCT_GOAL_ID,
            "product_goal_version": RUNTIME_ADMISSION.PRODUCT_GOAL_VERSION,
            "authority_lease": "PAUSED",
            "go_live_authorized": False,
            "formal_dispatch_authorized": False,
            "working_directory": str(RUNTIME_ADMISSION.PRODUCT_WORKING_DIRECTORY),
            "challenge": "5" * 64,
            "candidate": {
                "commit": self.context["candidate_commit"],
                "fingerprint": self.context["candidate_fingerprint"],
                "branch": self.context["branch"],
            },
            "runtime_identity": runtime,
        }
        order = ROUTER.admission_order_for_deployment(
            request, receipt_path=self.evidence_root / "mac-receipt.json",
        )
        evidence = self.evidence_root / "worker-receipt.json"
        visible_ssh = self.evidence_root / "visible-ssh"
        visible_ssh.mkdir()
        generation = Path(runtime["generation"])
        with patch.object(
            LANE, "require_live_runtime_identity", return_value=runtime,
        ), patch.object(
            LANE, "validate_admission_identity", return_value=order.bootstrap_identity,
        ), patch.object(
            LANE, "_admit_exact_environment",
            return_value=(request["candidate"], {"status": "READY"}),
        ), patch.object(
            LANE, "_probe", return_value="ok",
        ), patch.object(
            LANE, "__file__", str(generation / "product_goal_worker_lane.py"),
        ):
            with self.assertRaisesRegex(LANE.LaneError, "exposed the excluded SSH"):
                LANE.run_admission(
                    self.repo, order.execution_context, evidence,
                    process_reader=lambda: [],
                    cgroup_reader=lambda: "0::/user.slice/kgnote-test.service\n",
                    denied_path=visible_ssh,
                )
        self.assertFalse(evidence.exists())

    def test_codex_environment_admission_rejects_legacy_context(self):
        with self.assertRaisesRegex(LANE.LaneError, "context v2"):
            LANE.admit_codex_development_environment(
                self.repo, self.context, self.evidence_root / "legacy.json",
            )

    def test_codex_environment_failure_never_invokes_nested_model(self):
        calls=[]
        with self.assertRaisesRegex(LANE.LaneError,"environment denied"):
            evidence=self.evidence_root/"never.json"
            LANE.run_codex(
                self.repo,self.context,evidence,
                ["/home/kgnote/.local/bin/kgnote-successor-codex"],
                runner=lambda *args,**kwargs:calls.append(args),
                admitter=lambda *_args: (_ for _ in ()).throw(LANE.LaneError("environment denied")),
            )
        self.assertEqual([],calls)
        self.assertEqual(
            "WORKER_ENVIRONMENT_ADMISSION_FAILED",
            json.loads(evidence.read_text())["failure_class"],
        )

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
