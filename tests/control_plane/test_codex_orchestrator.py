import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("kgnote_codex_orchestrator", ROOT / "scripts/codex_orchestrator.py")
ORCH = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ORCH)
CONTROL_TEST_SPEC = importlib.util.spec_from_file_location(
    "kgnote_control_test_fixture", ROOT / "tests/control_plane/test_codex_control.py"
)
CONTROL_TESTS = importlib.util.module_from_spec(CONTROL_TEST_SPEC)
assert CONTROL_TEST_SPEC and CONTROL_TEST_SPEC.loader
CONTROL_TEST_SPEC.loader.exec_module(CONTROL_TESTS)


class OrchestrationSimulationTests(unittest.TestCase):
    def base_state(self, review_cycle=0, max_cycles=5):
        return {
            "schema_version": "kgnote.orchestrator-state.v1",
            "run_id": "orch-test",
            "active_goal": "G",
            "work_package": "WP-1",
            "state": "READY_FOR_AI_REVIEW",
            "current_agent": None,
            "candidate_fingerprint": "a" * 64,
            "review_id": "review-example-001",
            "review_cycle": review_cycle,
            "max_review_cycles": max_cycles,
            "agent_failures": 0,
            "max_agent_failures": 3,
            "empty_reviewer_results": 0,
            "blockers": [],
            "next_action": "review",
            "human_action_required": False,
            "candidate_custody": {
                "status": "SEALED", "owner": None,
                "review_id": "review-example-001", "fingerprint": "a" * 64,
            },
            "next_human_checkpoint": {"id": "PA-HUMAN-1", "status": "pending_human_review"},
            "last_agent_run": None,
            "created_at": "2026-09-23T00:00:00+08:00",
            "updated_at": "2026-09-23T00:00:00+08:00",
        }

    def harness(self, root, verdicts, *, initial="READY_FOR_REVIEW", advance_to="GOAL_COMPLETE"):
        request = {
            "status": initial,
            "review_id": "review-example-001",
            "candidate_fingerprint": "a" * 64,
            "candidate_revision": "h+worktree:" + "a" * 64,
        }
        result = {"artifact_state": "EMPTY", "verdict": None, "findings": []}
        decisions = {"decisions": []}
        queue = list(verdicts)
        review_number = {"value": 0}

        def load(_repo):
            return request, result, decisions

        def accept(_repo, _identity):
            request["status"] = "UNDER_REVIEW"

        def archive(_repo):
            request["status"] = result["verdict"]
            return {"verdict": result["verdict"]}

        def resume(_repo):
            request["status"] = "IMPLEMENTING"

        def validate(_repo, state):
            request["status"] = "READY_FOR_REVIEW"
            request["review_id"] = f"review-example-{review_number['value'] + 1:03d}"
            request["candidate_fingerprint"] = chr(98 + review_number["value"]) * 64
            result.update({"artifact_state": "EMPTY", "verdict": None, "findings": []})
            state["state"] = "READY_FOR_AI_REVIEW"
            state["review_id"] = request["review_id"]
            state["candidate_fingerprint"] = request["candidate_fingerprint"]
            ORCH.write_state(root, state)
            return True

        def advance(_repo, state):
            if advance_to == "IMPLEMENTING":
                state["work_package"] = "WP-2"
                ORCH.update_state(root, state, "IMPLEMENTING", "Automatically begin WP-2.")
            else:
                ORCH.update_state(root, state, "GOAL_COMPLETE", "Goal complete; report next HUMAN checkpoint.")

        def runner(_repo, role, _state):
            if role == "reviewer":
                verdict = queue.pop(0)
                review_number["value"] += 1
                result.update({"artifact_state": "SUBMITTED", "verdict": verdict})
                if verdict == "CHANGES_REQUIRED":
                    result["findings"] = [{"finding_id": f"R-{review_number['value']:03d}", "status": "OPEN"}]
                elif verdict == "PRODUCT_DECISION_REQUIRED":
                    decisions["decisions"] = [{"decision_id": "D-001", "status": "PENDING_HUMAN"}]
            return {"role": role, "exit_code": 0, "output_tail": "", "transcript_path": f"{role}.json"}

        patches = mock.patch.multiple(
            ORCH.control,
            preflight=mock.DEFAULT,
            load_review_artifacts=mock.DEFAULT,
            accept_review_custody=mock.DEFAULT,
            archive_submitted_result=mock.DEFAULT,
            resume_implementation=mock.DEFAULT,
            history_unresolved_finding_ids=mock.DEFAULT,
        )
        context = patches.start()
        self.addCleanup(patches.stop)
        context["preflight"].return_value = {"status": "pass", "errors": []}
        context["load_review_artifacts"].side_effect = load
        context["accept_review_custody"].side_effect = accept
        context["archive_submitted_result"].side_effect = archive
        context["resume_implementation"].side_effect = resume
        context["history_unresolved_finding_ids"].side_effect = lambda _repo: [
            item["finding_id"] for item in result.get("findings", []) if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
        ]
        validate_patch = mock.patch.object(ORCH, "validate_and_request", side_effect=validate)
        advance_patch = mock.patch.object(ORCH, "advance_after_pass", side_effect=advance)
        stale_patch = mock.patch.object(ORCH, "recover_stale_candidate", return_value=False)
        validate_patch.start()
        advance_patch.start()
        stale_patch.start()
        self.addCleanup(validate_patch.stop)
        self.addCleanup(advance_patch.stop)
        self.addCleanup(stale_patch.stop)
        return request, result, decisions, runner

    def step_until_terminal(self, root, state, runner, limit=30):
        for _ in range(limit):
            if state["state"] in ORCH.TERMINAL_STATES:
                return
            ORCH.orchestrate_step(root, state, runner)
        self.fail(f"orchestrator did not reach a terminal state: {state}")

    def test_1_implement_review_pass_automatically_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state()
            _, _, _, runner = self.harness(root, ["PASS"], advance_to="IMPLEMENTING")
            ORCH.orchestrate_step(root, state, runner)
            self.assertEqual(state["state"], "IMPLEMENTING")
            self.assertEqual(state["work_package"], "WP-2")
            self.assertFalse(state["human_action_required"])

    def test_2_review_fix_rereview_pass_without_human(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state()
            _, _, _, runner = self.harness(root, ["CHANGES_REQUIRED", "PASS"])
            self.step_until_terminal(root, state, runner)
            self.assertEqual(state["state"], "GOAL_COMPLETE")
            self.assertEqual(state["review_cycle"], 2)
            self.assertFalse(any(item.get("type") == "human_continue" for item in state["blockers"]))

    def test_3_multiple_repair_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state()
            _, _, _, runner = self.harness(root, ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "PASS"])
            self.step_until_terminal(root, state, runner)
            self.assertEqual(state["state"], "GOAL_COMPLETE")
            self.assertEqual(state["review_cycle"], 4)

    def test_4_true_product_decision_stops_for_human(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state()
            _, _, decisions, runner = self.harness(root, ["PRODUCT_DECISION_REQUIRED"])
            ORCH.orchestrate_step(root, state, runner)
            self.assertEqual(state["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(state["human_action_required"])
            self.assertEqual(decisions["decisions"][0]["status"], "PENDING_HUMAN")

    def test_5_stale_review_is_rejected_and_routed_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state()
            request = {"status": "UNDER_REVIEW", "candidate_fingerprint": "a" * 64}
            with mock.patch.object(ORCH.control, "load_review_artifacts", return_value=(request, {}, {})), \
                 mock.patch.object(ORCH.control, "repository_fingerprint", return_value={"value": "b" * 64}), \
                 mock.patch.object(ORCH.control, "invalidate_stale_review", return_value={
                     "replacement_fingerprint": "b" * 64, "next_review_id": "review-example-002"
                 }) as invalidate:
                self.assertTrue(ORCH.recover_stale_candidate(root, state))
            invalidate.assert_called_once()
            self.assertEqual(state["state"], "REPAIRING")
            self.assertIsNone(state["candidate_custody"]["owner"])

    def test_6_crash_context_restart_resumes_existing_reviewer_custody(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state(review_cycle=1)
            state["state"] = "REVIEWING"
            request, _, _, runner = self.harness(root, ["PASS"], initial="UNDER_REVIEW")
            ORCH.orchestrate_step(root, state, runner)
            self.assertEqual(request["status"], "PASS")
            self.assertEqual(state["state"], "GOAL_COMPLETE")
            self.assertEqual(state["review_cycle"], 1, "resuming custody must not spend a new review cycle")

    def test_7_repair_budget_exhaustion_has_structured_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state(max_cycles=5)
            _, _, _, runner = self.harness(root, ["CHANGES_REQUIRED"] * 5)
            self.step_until_terminal(root, state, runner)
            self.assertEqual(state["state"], "AUTOMATION_BLOCKED")
            self.assertTrue(state["human_action_required"])
            self.assertEqual(state["blockers"][0]["type"], "repair_budget_exhausted")
            self.assertEqual(state["blockers"][0]["review_cycle"], 5)

    def test_external_review_handoff_is_machine_owned_and_does_not_busy_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self.base_state(review_cycle=1)
            state["state"] = "AWAITING_EXTERNAL_PRODUCT_REVIEW"
            with mock.patch.object(ORCH, "acquire_lock", return_value={}), \
                 mock.patch.object(ORCH, "release_lock"), \
                 mock.patch.object(ORCH, "orchestrate_step") as step:
                result = ORCH.run_loop(root, state, lambda *_args: {}, max_steps=None)
            step.assert_not_called()
            self.assertFalse(result["human_action_required"])
            self.assertEqual(result["state"], "AWAITING_EXTERNAL_PRODUCT_REVIEW")

    def test_internal_pass_executes_exact_publication_before_external_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            state = self.base_state(review_cycle=1)
            plan = {
                "active_milestone_id": "AR-EXTERNAL-REVIEW",
                "milestones": [
                    {"id": "AR-EXTERNAL-REVIEW", "status": "active", "dependencies": [], "human_gate": "none"},
                    {"id": "AR-HUMAN-ELIGIBILITY", "status": "pending", "dependencies": ["AR-EXTERNAL-REVIEW"], "human_gate": "PA-HUMAN-1"},
                ],
            }
            external = {
                "canonical_repository": "owner/repo", "pull_request": 1,
                "review_round": 3, "external_review": {"status": "CHANGES_REQUIRED"},
            }
            completed = mock.Mock(stdout=("a" * 40 + "\n").encode())
            with mock.patch.object(ORCH.control, "load_plan_status", return_value=(plan, {})), \
                 mock.patch.object(ORCH.external_review_control, "load_json", return_value=external), \
                 mock.patch.object(ORCH.control, "load_review_artifacts", return_value=({"review_id": "review-010"}, {}, {})), \
                 mock.patch.object(ORCH.control, "repository_fingerprint", return_value={"value": "b" * 64}), \
                 mock.patch.object(ORCH.control, "run_git", return_value=completed), \
                 mock.patch.object(ORCH.publish_external_candidate, "publish", return_value={"artifact_url": "https://example.test/pr/1"}) as publish:
                ORCH.advance_after_pass(root, state)

            publish.assert_called_once_with(root)
            self.assertEqual(state["state"], "AWAITING_EXTERNAL_PRODUCT_REVIEW")
            self.assertFalse(state["human_action_required"])
            prepared = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(prepared["review_round"], 4)
            self.assertEqual(prepared["internal_review"]["status"], "PASS")

    def test_real_loop_lock_publisher_and_schema_complete_machine_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            (root / ".git").mkdir()
            config = {
                "enabled": True, "canonical_repository": "owner/public",
                "candidate_repository": "owner/public", "trigger_repository": "owner/public",
                "review_request_repository": "owner/public", "archive_repository": "owner/archive",
                "review_pr_number": 1, "request_marker": "REQUEST_V2",
                "max_product_review_rounds": 8,
            }
            external = {
                "canonical_repository": "owner/public", "candidate_repository": "owner/public",
                "trigger_repository": "owner/public", "review_request_repository": "owner/public",
                "archive_repository": "owner/archive", "pull_request": 1, "review_round": 3,
                "external_review": {"status": "CHANGES_REQUIRED", "blocking_findings": ["R-004"]},
            }
            (root / ".ai/github-product-reviewer.json").write_text(json.dumps(config))
            (root / ".ai/external-review-state.json").write_text(json.dumps(external))
            state = self.base_state(review_cycle=1)
            state["state"] = "VALIDATING"
            state["candidate_fingerprint"] = "b" * 64
            request = {"status": "PASS", "review_id": "review-011", "candidate_fingerprint": "b" * 64}
            plan = {
                "active_milestone_id": "AR-EXTERNAL-REVIEW",
                "milestones": [{"id": "AR-EXTERNAL-REVIEW", "status": "active"}],
            }
            marker = (
                "<!-- REQUEST_V2 candidate_commit=" + "a" * 40
                + " candidate_fingerprint=" + "b" * 64 + " review_round=4 -->"
            )
            remote_commands = []

            def remote_runner(command, *, cwd):
                remote_commands.append(command)
                if command[:3] == ["git", "rev-parse", "HEAD"]: return "a" * 40
                if command[:3] == ["git", "status", "--porcelain"]:
                    self.assertTrue((root / ".ai/ORCHESTRATOR.lock").exists())
                    return "?? .ai/ORCHESTRATOR.lock"
                if command[:4] == ["git", "remote", "get-url", "origin"]: return "https://github.com/owner/public.git"
                if command[:3] == ["git", "branch", "--show-current"]: return "codex/candidate"
                if command[:3] == ["gh", "pr", "view"] and command[-1] == "body": return json.dumps({"body": "PR"})
                if command[:3] == ["gh", "pr", "edit"]: return ""
                if command[:3] == ["git", "push", "origin"]: return ""
                if command[:3] == ["gh", "pr", "view"]:
                    return json.dumps({"headRefOid": "a" * 40, "body": "PR\n" + marker, "state": "OPEN", "url": "https://example/pr/1"})
                raise AssertionError(command)

            completed = mock.Mock(stdout=("a" * 40 + "\n").encode())
            with mock.patch.object(ORCH, "recover_stale_candidate", return_value=False), \
                 mock.patch.object(ORCH.control, "preflight", return_value={"status": "pass", "errors": []}), \
                 mock.patch.object(ORCH.control, "load_review_artifacts", return_value=(request, {}, {})), \
                 mock.patch.object(ORCH.control, "load_plan_status", return_value=(plan, {})), \
                 mock.patch.object(ORCH.control, "repository_fingerprint", return_value={"value": "b" * 64}), \
                 mock.patch.object(ORCH.control, "run_git", return_value=completed), \
                 mock.patch.object(ORCH.publish_external_candidate, "_run", side_effect=remote_runner):
                result = ORCH.run_loop(root, state, lambda *_args: self.fail("no agent should run"), max_steps=None)

            self.assertEqual(result["state"], "AWAITING_EXTERNAL_PRODUCT_REVIEW")
            self.assertFalse(result["human_action_required"])
            self.assertTrue(any(command[:3] == ["git", "push", "origin"] for command in remote_commands))
            schema = json.loads((ROOT / ".ai/schemas/orchestrator-state.schema.json").read_text())
            Draft202012Validator(schema).validate(json.loads((root / ".ai/ORCHESTRATOR_STATE.json").read_text()))


class OrchestratorDurabilityTests(unittest.TestCase):
    def copy_repository_snapshot(self, source_root, root):
        shutil.copytree(
            source_root,
            root,
            dirs_exist_ok=True,
            symlinks=True,
            ignore=shutil.ignore_patterns(".venv", "node_modules", "output"),
        )

    def make_completed_source_snapshot(self, root):
        self.copy_repository_snapshot(ROOT, root)
        plan, status = ORCH.control.load_plan_status(root)
        plan["status"] = "complete"
        plan["active_milestone_id"] = None
        for milestone in plan["milestones"]:
            milestone["status"] = "complete"
        ORCH.write_plan(
            root,
            plan,
            "GOAL_COMPLETE",
            "Goal complete; report the next preserved HUMAN checkpoint, not another machine action.",
        )
        status["goal_status"] = "complete"
        status["active_milestone_id"] = None
        status["milestone_status"] = "complete"
        ORCH.control.write_status(root, status)

    def make_repository_complete_fixture(self, root, fixture, *, source_root=ROOT):
        self.copy_repository_snapshot(source_root, root)
        (root / ".venv/bin").mkdir(parents=True)
        os.symlink(ROOT / ".venv/bin/python", root / ".venv/bin/python")
        shutil.rmtree(root / ".ai/REVIEW_HISTORY", ignore_errors=True)
        shutil.rmtree(root / ".ai/ORCHESTRATION_HISTORY", ignore_errors=True)
        (root / ".ai/ORCHESTRATOR_STATE.json").unlink(missing_ok=True)
        (root / ".ai/ORCHESTRATOR.lock").unlink(missing_ok=True)

        plan, status = ORCH.control.load_plan_status(root)
        active_milestones = [
            milestone for milestone in plan["milestones"]
            if milestone["status"] == "active"
        ]
        target_milestone = (
            active_milestones[0]
            if len(active_milestones) == 1
            else next(
                milestone for milestone in plan["milestones"]
                if milestone.get("human_gate", "none") in {"none", "complete"}
            )
        )
        target_milestone_id = target_milestone["id"]
        plan["status"] = "active"
        plan["active_milestone_id"] = target_milestone_id
        for milestone in plan["milestones"]:
            if milestone["id"] == target_milestone_id:
                milestone["status"] = "active"
            elif milestone["status"] == "active":
                milestone["status"] = "complete"
        ORCH.control.replace_embedded_json(
            root / "PLAN.md", ORCH.control.PLAN_BEGIN, ORCH.control.PLAN_END, plan
        )
        fingerprint = ORCH.control.repository_fingerprint(root)
        request = fixture.fixture.base_review_request()
        request.update({
            "goal_id": plan["goal_id"],
            "milestone_id": plan["active_milestone_id"],
            "base_revision": fingerprint["head"],
            "candidate_revision": f"{fingerprint['head']}+worktree:{fingerprint['value']}",
            "candidate_fingerprint": fingerprint["value"],
            "candidate_manifest": ORCH.control.repository_manifest(root),
            "authoritative_specs": ["docs/control-plane/AUTHORITY.md"],
        })
        result = fixture.fixture.empty_review_result()
        decisions = {
            "schema_version": "kgnote.review-decisions.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "decisions": [],
        }
        fixture.write_embedded(
            root / ".ai/REVIEW_REQUEST.md", "Request",
            ORCH.control.REVIEW_REQUEST_BEGIN, ORCH.control.REVIEW_REQUEST_END, request,
        )
        (root / ".ai/REVIEW_REQUEST.md").write_text(
            (root / ".ai/REVIEW_REQUEST.md").read_text() + "\n## Human-readable status\n\nplaceholder\n"
        )
        ORCH.control.write_review_request(root, request)
        fixture.write_embedded(
            root / ".ai/REVIEW_RESULT.md", "Result",
            ORCH.control.REVIEW_RESULT_BEGIN, ORCH.control.REVIEW_RESULT_END, result,
        )
        fixture.write_embedded(
            root / ".ai/DECISIONS.md", "Decisions",
            ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions,
        )
        history = root / ".ai/REVIEW_HISTORY"
        history.mkdir(parents=True)
        (history / "events.jsonl").write_text(json.dumps({
            "event_id": "evt-0001",
            "event_type": "PROTOCOL_INITIALIZED",
            "review_id": request["review_id"],
            "actor_role": "CODEX_IMPLEMENTER",
            "candidate_fingerprint": None,
            "snapshot_path": None,
            "snapshot_sha256": None,
            "created_at": "2026-09-23T09:00:00+08:00",
        }, separators=(",", ":")) + "\n")
        (history / "index.json").write_text(json.dumps({
            "schema_version": "kgnote.review-history-index.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "event_count": 1,
            "last_event_id": "evt-0001",
            "reviews": {},
            "findings": {},
        }, indent=2) + "\n")

        status["updated_at"] = "2026-09-23T09:00:00+08:00"
        status["goal_status"] = "active"
        status["active_milestone_id"] = target_milestone_id
        status["milestone_status"] = "active"
        status["git"]["branch"] = fingerprint["branch"]
        status["git"]["head"] = fingerprint["head"]
        status["working_state"]["fingerprint"] = fingerprint["value"]
        status["working_state"]["unexpected_dirty_paths"] = []
        status["implementation_state"] = "READY_FOR_REVIEW"
        status["review"] = {
            "state": "READY_FOR_REVIEW",
            "current_review_id": request["review_id"],
            "candidate_revision": request["candidate_revision"],
            "candidate_fingerprint": request["candidate_fingerprint"],
            "unresolved_findings": [],
            "human_decision_blockers": [],
        }
        status["verification"]["candidate_verified"] = True
        status["verification"]["release_verified"] = False
        status["verification"]["control_plane_ready"] = True
        status["verification"]["last_verified_fingerprint"] = fingerprint["value"]
        status["next_action"] = "Reviewer accepts exact-fingerprint custody."
        ORCH.control.write_status(root, status)
        return request, decisions

    def test_successful_but_empty_reviewer_is_bounded_and_persists_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = OrchestrationSimulationTests().base_state(review_cycle=1)
            state["state"] = "REVIEWING"
            request = {"status": "UNDER_REVIEW", "review_id": "review-example-001"}
            result = {"artifact_state": "EMPTY", "verdict": None, "findings": []}
            calls = {"count": 0}

            def runner(_repo, role, _state):
                calls["count"] += 1
                return {"role": role, "exit_code": 0, "output_tail": "", "transcript_path": "empty.json"}

            with mock.patch.object(ORCH.control, "load_review_artifacts", return_value=(request, result, {"decisions": []})), \
                 mock.patch.object(ORCH, "recover_stale_candidate", return_value=False):
                for expected in (1, 2, 3):
                    ORCH.execute_reviewer(root, state, runner)
                    self.assertEqual(state["empty_reviewer_results"], expected)
            self.assertEqual(calls["count"], 3)
            self.assertEqual(state["state"], "AUTOMATION_BLOCKED")
            self.assertEqual(state["blockers"][0]["type"], "reviewer_produced_no_result")
            self.assertEqual(state["blockers"][0]["attempts"], 3)

    def test_pending_changes_result_validates_and_crash_resume_archives_before_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = CONTROL_TESTS.ReviewHelperIntegrationTests()
            fixture.setUp()
            fixture.make_repo(root)
            ORCH.control.accept_review_custody(root, "independent-reviewer")
            request, _, _ = ORCH.control.load_review_artifacts(root)
            fixture.write_result(root, request, "CHANGES_REQUIRED", [fixture.finding()])
            self.assertEqual(ORCH.control.validate_pending_review_result(root)[0], [])
            self.assertTrue(any(
                "unresolved_findings" in error
                for error in ORCH.control.validate_review_artifacts(root)[0]
            ))
            state = ORCH.derive_state(root)
            state["review_cycle"] = 1
            ORCH.write_state(root, state)
            with mock.patch.object(ORCH.control, "preflight", return_value={"status": "pass", "errors": []}):
                ORCH.orchestrate_step(root, state, lambda *_args: self.fail("no agent should run"))
            current_request, current_result, _ = ORCH.control.load_review_artifacts(root)
            _, status = ORCH.control.load_plan_status(root)
            self.assertEqual(current_request["status"], "IMPLEMENTING")
            self.assertEqual(current_result["verdict"], "CHANGES_REQUIRED")
            self.assertIsNone(status["review"]["current_review_id"])
            self.assertEqual(status["review"]["unresolved_findings"], ["R-001"])
            self.assertEqual(state["state"], "REPAIRING")
            self.assertEqual(ORCH.control.validate_review_artifacts(root)[0], [])

    def exercise_product_decision_resume_validates_authority_and_seals_new_review(
        self, root, fixture, *, source_root
    ):
        with self.subTest(source_root=source_root.name):
            self.make_repository_complete_fixture(root, fixture, source_root=source_root)
            self.assertEqual(ORCH.control.preflight(root)["status"], "pass")
            ORCH.control.accept_review_custody(root, "independent-reviewer")
            request, _, decisions = ORCH.control.load_review_artifacts(root)
            decision = {
                "decision_id": "D-001", "question": "Which behavior?",
                "why_existing_authority_is_insufficient": "Two sources conflict.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
                "observable_consequences": ["Behavior A", "Behavior B"],
                "blocking_scope": ["implementation"], "linked_findings": [],
                "status": "PENDING_HUMAN", "review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "selected_option": None, "decided_by": None, "decided_at": None,
                "authority_record": None,
            }
            decisions["decisions"] = [decision]
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions
            )
            fixture.write_result(root, request, "PRODUCT_DECISION_REQUIRED", decisions=["D-001"])
            ORCH.control.archive_submitted_result(root)
            state = ORCH.derive_state(root)
            ORCH.write_state(root, state)

            def resume_artifact_snapshot():
                orchestrator_state = json.loads((root / ".ai/ORCHESTRATOR_STATE.json").read_text())
                return {
                    "request": (root / ".ai/REVIEW_REQUEST.md").read_bytes(),
                    "status": (root / "CODEX_STATUS.md").read_bytes(),
                    "history": (root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes(),
                    "custody": orchestrator_state["candidate_custody"],
                }

            def assert_resume_artifacts_unchanged(before):
                self.assertEqual((root / ".ai/REVIEW_REQUEST.md").read_bytes(), before["request"])
                self.assertEqual((root / "CODEX_STATUS.md").read_bytes(), before["status"])
                self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes(), before["history"])
                orchestrator_state = json.loads((root / ".ai/ORCHESTRATOR_STATE.json").read_text())
                self.assertEqual(orchestrator_state["candidate_custody"], before["custody"])

            decisions["decisions"] = []
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions
            )
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertEqual(blocked["blockers"][0]["type"], "human_decision_evidence_invalid")
            self.assertTrue(any("missing required human decisions" in error for error in blocked["blockers"][0]["errors"]))

            decision.update({
                "status": "DECIDED", "selected_option": "A", "decided_by": "product owner",
                "decided_at": "2026-09-23T12:00:00+08:00",
                "authority_record": "docs/control-plane/AUTHORITY.md",
            })
            decisions["decisions"] = [decision]
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions
            )
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any("dedicated canonical record" in error for error in blocked["blockers"][0]["errors"]))

            decision["authority_record"] = "PLAN.md"
            plan_bytes = (root / "PLAN.md").read_bytes()
            plan, _ = ORCH.control.load_plan_status(root)
            active = next(item for item in plan["milestones"] if item["status"] == "active")
            active["acceptance"][0] = "forged replacement acceptance"
            ORCH.control.replace_embedded_json(
                root / "PLAN.md", ORCH.control.PLAN_BEGIN, ORCH.control.PLAN_END, plan
            )
            temporary_authority = root / "docs/requirements/human-decisions/D-001.md"
            CONTROL_TESTS.write_human_decision_authority(temporary_authority, decision)
            with (root / "PLAN.md").open("a", encoding="utf-8") as plan_file:
                plan_file.write("\n" + temporary_authority.read_text())
            temporary_authority.unlink()
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN,
                ORCH.control.DECISIONS_END, decisions,
            )
            before = resume_artifact_snapshot()
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any("dedicated canonical record" in error for error in blocked["blockers"][0]["errors"]))
            assert_resume_artifacts_unchanged(before)
            (root / "PLAN.md").write_bytes(plan_bytes)

            for forbidden_path in (
                "scripts/codex_control.py",
                "tests/control_plane/test_codex_control.py",
                ".ai/REVIEW_PROTOCOL.md",
            ):
                decision["authority_record"] = forbidden_path
                ORCH.control.replace_embedded_json(
                    root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN,
                    ORCH.control.DECISIONS_END, decisions,
                )
                before = resume_artifact_snapshot()
                blocked = ORCH.start(
                    root, resume=True, max_review_cycles=5, max_steps=1,
                    runner=lambda *_: self.fail(),
                )
                self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
                self.assertTrue(any(
                    "dedicated canonical record" in error
                    for error in blocked["blockers"][0]["errors"]
                ))
                assert_resume_artifacts_unchanged(before)

            decision["authority_record"] = "docs/requirements/human-decisions/D-001.md"
            decision["decided_by"] = "codex-independent-reviewer:forged-human-label"
            CONTROL_TESTS.write_human_decision_authority(
                root / decision["authority_record"], decision
            )
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions
            )
            review_history_before = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes()
            status_before = (root / "CODEX_STATUS.md").read_bytes()
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any(
                "not a positively authorized human identity" in error
                for error in blocked["blockers"][0]["errors"]
            ))
            self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes(), review_history_before)
            self.assertEqual((root / "CODEX_STATUS.md").read_bytes(), status_before)

            decision["decided_by"] = "product owner"
            CONTROL_TESTS.write_human_decision_authority(
                root / decision["authority_record"], decision
            )
            ORCH.control.replace_embedded_json(
                root / ".ai/DECISIONS.md", ORCH.control.DECISIONS_BEGIN, ORCH.control.DECISIONS_END, decisions
            )

            plan_bytes = (root / "PLAN.md").read_bytes()
            plan, _ = ORCH.control.load_plan_status(root)
            plan["explicit_direction"]["speaker"] = "codex-independent-reviewer:forged-human-label"
            decision["decided_by"] = "codex-independent-reviewer:forged-human-label"
            CONTROL_TESTS.write_human_decision_authority(
                root / decision["authority_record"], decision
            )
            ORCH.control.replace_embedded_json(
                root / "PLAN.md", ORCH.control.PLAN_BEGIN, ORCH.control.PLAN_END, plan
            )
            review_history_before = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes()
            status_before = (root / "CODEX_STATUS.md").read_bytes()
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any(
                "identity anchor differs from the sealed reviewed candidate" in error
                for error in blocked["blockers"][0]["errors"]
            ))
            self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes(), review_history_before)
            self.assertEqual((root / "CODEX_STATUS.md").read_bytes(), status_before)

            decision["decided_by"] = "product owner"
            (root / "PLAN.md").write_bytes(plan_bytes)
            CONTROL_TESTS.write_human_decision_authority(
                root / decision["authority_record"], decision
            )
            authority_path = root / decision["authority_record"]
            canonical_authority_bytes = authority_path.read_bytes()
            authority_path.write_bytes(canonical_authority_bytes + b"\nUnrelated same-file mutation.\n")
            before = resume_artifact_snapshot()
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any(
                "non-canonical or unrelated content" in error
                for error in blocked["blockers"][0]["errors"]
            ))
            assert_resume_artifacts_unchanged(before)
            authority_path.write_bytes(canonical_authority_bytes)

            unrelated = root / "docs/control-plane/unrelated-drift.txt"
            unrelated.write_text("not authorized by the human decision\n")
            review_history_before = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes()
            status_before = (root / "CODEX_STATUS.md").read_bytes()
            blocked = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=lambda *_: self.fail())
            self.assertEqual(blocked["state"], "PRODUCT_DECISION_REQUIRED")
            self.assertTrue(any(
                "unrelated candidate drift" in error and "unrelated-drift.txt" in error
                for error in blocked["blockers"][0]["errors"]
            ))
            self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_bytes(), review_history_before)
            self.assertEqual((root / "CODEX_STATUS.md").read_bytes(), status_before)
            unrelated.unlink()

            self.assertEqual(
                ORCH.control.validate_human_decision_delta(root, request, decisions, {"D-001"}),
                [],
            )

            runner_calls = []

            def runner(_repo, role, _state):
                runner_calls.append(role)
                self.assertEqual(role, "implementer")
                actual = ORCH.control.repository_fingerprint(root)
                _, resumed_status = ORCH.control.load_plan_status(root)
                self.assertEqual(resumed_status["working_state"]["fingerprint"], actual["value"])
                self.assertIn("fresh implementer", resumed_status["next_action"])
                self.assertEqual(_state["candidate_fingerprint"], actual["value"])
                self.assertEqual(ORCH.control.preflight(root)["status"], "pass")
                (root / "docs/control-plane/test-decision-implementation.txt").write_text(
                    "candidate after human decision\n"
                )
                return {"role": role, "exit_code": 0, "output_tail": "", "transcript_path": "implementer.json"}

            def validate_and_request(_repo, resumed_state):
                ORCH.control.sync_implementing_fingerprint(root, "Decision-authorized implementation completed.")
                evidence = fixture.evidence_for_current_candidate(root)
                prepared = ORCH.control.prepare_review_request(
                    root, evidence, ["implementation"], ["review decision"], [], []
                )
                resumed_state["review_id"] = prepared["review_id"]
                resumed_state["candidate_fingerprint"] = prepared["candidate_fingerprint"]
                resumed_state["candidate_custody"] = {
                    "status": "SEALED", "owner": None,
                    "review_id": prepared["review_id"], "fingerprint": prepared["candidate_fingerprint"],
                }
                ORCH.update_state(root, resumed_state, "READY_FOR_AI_REVIEW", "New decision-authorized review sealed.")
                return True

            stale_before_resume = ORCH.control.repository_fingerprint(root)
            _, stale_status = ORCH.control.load_plan_status(root)
            self.assertNotEqual(stale_status["working_state"]["fingerprint"], stale_before_resume["value"])
            with mock.patch.object(ORCH, "validate_and_request", side_effect=validate_and_request):
                resumed = ORCH.start(root, resume=True, max_review_cycles=5, max_steps=1, runner=runner)
            current_request, current_result, _ = ORCH.control.load_review_artifacts(root)
            self.assertEqual(runner_calls, ["implementer"])
            self.assertEqual(resumed["state"], "READY_FOR_AI_REVIEW")
            self.assertEqual(current_request["status"], "READY_FOR_REVIEW")
            self.assertEqual(current_result["artifact_state"], "EMPTY")
            self.assertFalse(resumed["human_action_required"])
            self.assertEqual(ORCH.control.preflight(root)["status"], "pass")

    def test_product_decision_resume_validates_authority_and_seals_new_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = CONTROL_TESTS.ReviewHelperIntegrationTests()
            fixture.setUp()
            self.exercise_product_decision_resume_validates_authority_and_seals_new_review(
                root, fixture, source_root=ROOT
            )

    def test_product_decision_flow_is_isolated_from_completed_root_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source_root = base / "completed-source"
            root = base / "fixture"
            self.make_completed_source_snapshot(source_root)
            source_plan, source_status = ORCH.control.load_plan_status(source_root)
            self.assertEqual(source_plan["status"], "complete")
            self.assertIsNone(source_plan["active_milestone_id"])
            self.assertEqual(source_status["goal_status"], "complete")
            self.assertIsNone(source_status["active_milestone_id"])
            self.assertEqual(source_status["milestone_status"], "complete")

            fixture = CONTROL_TESTS.ReviewHelperIntegrationTests()
            fixture.setUp()
            self.exercise_product_decision_resume_validates_authority_and_seals_new_review(
                root, fixture, source_root=source_root
            )

    def test_codex_command_places_global_flags_before_exec_and_uses_ephemeral_context(self):
        command = ORCH.codex_agent_command(ROOT, "reviewer", ROOT / "output/last.txt")
        exec_index = command.index("exec")
        self.assertLess(command.index("-a"), exec_index)
        self.assertLess(command.index("-s"), exec_index)
        self.assertLess(command.index("-C"), exec_index)
        self.assertGreater(command.index("--ephemeral"), exec_index)
        self.assertIn("YOU are the required independent reviewer", command[-1])

    def test_real_pass_consumption_completes_plan_and_preserves_auditable_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = CONTROL_TESTS.ReviewHelperIntegrationTests()
            fixture.setUp()
            fixture.make_repo(root)
            ORCH.control.accept_review_custody(root, "independent-reviewer")
            request, _, _ = ORCH.control.load_review_artifacts(root)
            fixture.write_result(root, request, "PASS")
            ORCH.control.archive_submitted_result(root)
            state = ORCH.derive_state(root)
            ORCH.advance_after_pass(root, state)
            plan, status = ORCH.control.load_plan_status(root)
            current_request, current_result, _ = ORCH.control.load_review_artifacts(root)
            self.assertEqual(plan["status"], "complete")
            self.assertIsNone(plan["active_milestone_id"])
            self.assertEqual(status["goal_status"], "complete")
            self.assertEqual(state["state"], "GOAL_COMPLETE")
            self.assertEqual(current_request["status"], "IMPLEMENTING")
            self.assertEqual(current_result["artifact_state"], "EMPTY")
            self.assertEqual(ORCH.control.validate_plan_status(plan, status), [])
            self.assertEqual(ORCH.control.validate_review_artifacts(root)[0], [])

    def test_status_schema_contains_required_resume_fields_and_default_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = OrchestrationSimulationTests().base_state()
            ORCH.write_state(root, state)
            restored = ORCH.read_state(root)
            self.assertEqual(restored["max_review_cycles"], 5)
            for field in (
                "active_goal", "work_package", "state", "current_agent", "candidate_fingerprint",
                "review_cycle", "empty_reviewer_results", "blockers", "next_action", "human_action_required", "candidate_custody",
            ):
                self.assertIn(field, restored)

    def test_stale_process_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            (root / ORCH.LOCK_PATH).write_text('{"pid":99999999,"run_id":"dead"}')
            state = OrchestrationSimulationTests().base_state()
            descriptor = ORCH.acquire_lock(root, state)
            ORCH.release_lock(root, descriptor)
            self.assertFalse((root / ORCH.LOCK_PATH).exists())

    def test_quota_failure_maps_to_budget_exhausted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = OrchestrationSimulationTests().base_state()
            ORCH.handle_agent_failure(root, state, {
                "role": "reviewer", "exit_code": 1,
                "output_tail": "Usage limit reached", "transcript_path": "evidence.json",
            })
            self.assertEqual(state["state"], "BUDGET_EXHAUSTED")
            self.assertTrue(state["human_action_required"])


if __name__ == "__main__":
    unittest.main()
