import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("codex_control", ROOT / "scripts/codex_control.py")
assert SPEC and SPEC.loader
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


def write_human_decision_authority(path, decision, evidence="Human explicitly selected the recorded option."):
    payload = {
        "schema_version": "kgnote.human-decision-authority.v1",
        "decision_id": decision["decision_id"],
        "review_id": decision["review_id"],
        "candidate_revision": decision["candidate_revision"],
        "candidate_fingerprint": decision["candidate_fingerprint"],
        "selected_option": decision["selected_option"],
        "decided_by": decision["decided_by"],
        "decided_at": decision["decided_at"],
        "decision_evidence": evidence,
        "linked_findings": decision["linked_findings"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONTROL.render_human_decision_authority_record(payload))


def write_plan_with_human_authority(path, speaker="product owner"):
    payload = {
        "schema_version": "kgnote.codex-plan.v1",
        "explicit_direction": {"speaker": speaker},
    }
    path.write_text(
        "# Plan\n\n"
        f"{CONTROL.PLAN_BEGIN}\n```json\n{json.dumps(payload, indent=2)}\n```\n{CONTROL.PLAN_END}\n"
    )


class ControlPlaneNegativeTests(unittest.TestCase):
    def base_plan(self):
        return {
            "schema_version": "kgnote.codex-plan.v1",
            "goal_id": "G",
            "status": "active",
            "active_milestone_id": "M2",
            "product_direction_id": "D",
            "milestones": [
                {"id": "M1", "status": "complete", "dependencies": [], "human_gate": "none", "owned_paths": ["a.txt"]},
                {"id": "M2", "status": "active", "dependencies": ["M1"], "human_gate": "none", "owned_paths": ["work/"], "acceptance": ["current milestone exact"]},
            ],
        }

    def base_status(self):
        return {
            "goal_id": "G",
            "goal_status": "active",
            "active_milestone_id": "M2",
            "product_direction_id": "D",
            "git": {"branch": "b", "head": "h"},
            "verification": {"release_verified": False},
        }

    def base_review_request(self):
        manifest = {
            "algorithm": "sha256-canonical-json-v2-review-bus-exclusions",
            "branch": "", "head": "c" * 40,
            "excluded_paths": sorted(CONTROL.FINGERPRINT_EXCLUDES),
            "excluded_prefixes": sorted(CONTROL.FINGERPRINT_EXCLUDE_PREFIXES),
            "entries": [],
        }
        fingerprint = CONTROL.fingerprint_from_manifest(manifest)
        return {
            "schema_version": "kgnote.review-request.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "review_id": "review-example-001",
            "goal_id": "G",
            "milestone_id": "M2",
            "status": "READY_FOR_REVIEW",
            "author_role": "CODEX_IMPLEMENTER",
            "base_revision": "b" * 40,
            "candidate_revision": f"{'c' * 40}+worktree:{fingerprint}",
            "candidate_fingerprint": fingerprint,
            "candidate_manifest": manifest,
            "authorized_human_decision_identities": ["product owner"],
            "authoritative_specs": ["authority.md"],
            "changed_areas": ["control plane"],
            "acceptance_criteria": ["exact identity"],
            "negative_requirements": ["no stale PASS"],
            "validation_performed": ["verify"],
            "validation_results": [{"name": "verify", "status": "PASS", "evidence": "e.json"}],
            "known_deviations": [],
            "known_uncertainties": [],
            "reviewer_focus": [],
            "preserved_human_gates": ["PA-HUMAN-1"],
            "requested_at": "2026-09-23T09:00:00+08:00",
        }

    def empty_review_result(self):
        return {
            "schema_version": "kgnote.review-result.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "artifact_state": "EMPTY",
            "review_id": None,
            "author_role": None,
            "reviewer_identity": None,
            "reviewed_revision": None,
            "reviewed_fingerprint": None,
            "verdict": None,
            "findings": [],
            "verified_requirements": [],
            "unverified_requirements": [],
            "human_decisions_required": [],
            "human_gates_preserved": [],
            "reviewed_at": None,
        }

    def submitted_result(self, verdict="PASS"):
        request = self.base_review_request()
        return {
            "schema_version": "kgnote.review-result.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "artifact_state": "SUBMITTED",
            "review_id": request["review_id"],
            "author_role": "CHATGPT_WORK_REVIEWER",
            "reviewer_identity": "work-session-1",
            "reviewed_revision": request["candidate_revision"],
            "reviewed_fingerprint": request["candidate_fingerprint"],
            "verdict": verdict,
            "findings": [],
            "verified_requirements": ["KG-GOV-07"],
            "unverified_requirements": [],
            "human_decisions_required": [],
            "human_gates_preserved": ["PA-HUMAN-1"],
            "reviewed_at": "2026-09-23T10:00:00+08:00",
        }

    def test_stale_python_selector_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "test_sample.py"
            path.write_text("class SampleTests:\n    def test_real(self): pass\n")
            error = CONTROL.validate_test_ref(root, {"path": "test_sample.py", "selector": "SampleTests.test_stale"})
            self.assertIn("no exact selector", error)

    def test_generated_view_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            for name in CONTROL.GENERATED_VIEWS:
                (Path(left) / name).write_text("same\n")
                (Path(right) / name).write_text("same\n")
            (Path(right) / CONTROL.GENERATED_VIEWS[0]).write_text("changed\n")
            self.assertTrue(any("differs" in e for e in CONTROL.compare_generated_files(Path(left), Path(right))))

    def test_authority_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "authority.md").write_text("marker\n")
            errors = CONTROL.validate_locked_entries(root, [{"path": "authority.md", "sha256": "0" * 64, "required_marker": "marker"}])
            self.assertTrue(any("hash mismatch" in e for e in errors))

    def test_two_active_milestones_are_rejected(self):
        plan = self.base_plan()
        plan["milestones"][0]["status"] = "active"
        errors = CONTROL.validate_plan_status(plan, self.base_status(), branch="b", head="h")
        self.assertTrue(any("exactly one active" in e for e in errors))

    def test_plan_status_mismatch_is_rejected(self):
        status = self.base_status()
        status["active_milestone_id"] = "M1"
        errors = CONTROL.validate_plan_status(self.base_plan(), status, branch="b", head="h")
        self.assertTrue(any("active milestone differs" in e for e in errors))

    def test_unexpected_dirty_path_is_rejected(self):
        self.assertEqual(CONTROL.unexpected_dirty_paths(["work/ok.py", "secret.txt"], self.base_plan()), ["secret.txt"])

    def test_local_verifier_never_promotes_release_verified(self):
        claims = CONTROL.verification_claims(True)
        self.assertTrue(claims["candidate_verified"])
        self.assertFalse(claims["release_verified"])

    def test_manual_gate_blocks_auto_advance(self):
        plan = self.base_plan()
        plan["milestones"][1]["human_gate"] = "user_approval"
        self.assertFalse(CONTROL.can_auto_advance(plan))

    def test_failed_verification_keeps_milestone_active(self):
        self.assertEqual(CONTROL.milestone_after_verification("M2", False), "active")

    def test_stale_status_fingerprint_is_rejected(self):
        status = {"working_state": {"fingerprint": "old"}}
        errors = CONTROL.validate_recorded_fingerprint(status, {"value": "new"})
        self.assertTrue(any("recorded working-state fingerprint" in error for error in errors))

    def test_pass_for_old_fingerprint_cannot_authorize_new_candidate(self):
        request = self.base_review_request()
        result = self.submitted_result()
        current = {"value": "f" * 64}
        blockers = CONTROL.review_progression_blockers(request, result, {"decisions": []}, self.base_plan(), current)
        self.assertTrue(any("stale" in blocker for blocker in blockers))

    def test_missing_review_result_is_not_pass(self):
        blockers = CONTROL.review_progression_blockers(
            self.base_review_request(), self.empty_review_result(), {"decisions": []}, self.base_plan(), {"value": "a" * 64}
        )
        self.assertTrue(any("missing review result" in blocker for blocker in blockers))

    def test_changes_required_blocks_progression(self):
        result = self.submitted_result("CHANGES_REQUIRED")
        result["findings"] = [{"finding_id": "R-001", "status": "OPEN"}]
        blockers = CONTROL.review_progression_blockers(
            self.base_review_request(), result, {"decisions": []}, self.base_plan(), {"value": "a" * 64}
        )
        self.assertTrue(any("CHANGES_REQUIRED" in blocker for blocker in blockers))
        self.assertTrue(any("R-001" in blocker for blocker in blockers))

    def test_product_decision_required_blocks_affected_scope(self):
        result = self.submitted_result("PRODUCT_DECISION_REQUIRED")
        result["human_decisions_required"] = ["D-001"]
        decisions = {"decisions": [{"decision_id": "D-001", "status": "PENDING_HUMAN"}]}
        blockers = CONTROL.review_progression_blockers(
            self.base_review_request(), result, decisions, self.base_plan(), {"value": "a" * 64}
        )
        self.assertTrue(any("PRODUCT_DECISION_REQUIRED" in blocker for blocker in blockers))

    def test_unresolved_finding_cannot_disappear_through_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / ".ai/REVIEW_HISTORY"
            history.mkdir(parents=True)
            (history / "events.jsonl").write_text(
                json.dumps({"event_id": "evt-0001", "snapshot_path": None, "snapshot_sha256": None}) + "\n"
            )
            (history / "index.json").write_text(
                json.dumps({
                    "schema_version": "kgnote.review-history-index.v1",
                    "protocol_version": "kgnote.review-protocol.v1",
                    "event_count": 1,
                    "last_event_id": "evt-0001",
                    "reviews": {},
                    "findings": {"R-001": {"status": "OPEN", "review_id": "review-example-001"}},
                })
            )
            result = self.submitted_result()
            errors = CONTROL.validate_review_history(root, result)
            self.assertTrue(any("R-001" in error and "disappeared" in error for error in errors))

    def test_codex_cannot_self_author_reviewer_pass(self):
        result = self.submitted_result()
        result["author_role"] = "CODEX_IMPLEMENTER"
        errors = CONTROL.validate_review_result(self.base_review_request(), result, {"decisions": []})
        self.assertTrue(any("CHATGPT_WORK_REVIEWER" in error for error in errors))

    def test_preserved_human_gate_is_not_silently_promoted_or_used_as_routine_continue_prompt(self):
        plan = self.base_plan()
        plan["preserved_human_gates"] = [{"id": "PA-HUMAN-1", "status": "pending_human_review"}]
        request = self.base_review_request()
        blockers = CONTROL.review_progression_blockers(
            request, self.submitted_result(), {"decisions": []}, plan,
            {"value": request["candidate_fingerprint"]}
        )
        self.assertEqual(blockers, [])
        self.assertEqual(plan["preserved_human_gates"][0]["status"], "pending_human_review")

    def test_mismatched_candidate_verification_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = {
                "result": "pass",
                "claims": {"candidate_verified": True, "release_verified": False},
                "fingerprint_stable": True,
                "fingerprint_before": {"value": "a" * 64},
                "fingerprint_after": {"value": "a" * 64},
            }
            (root / "evidence.json").write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "does not match current candidate"):
                CONTROL.load_verification_evidence(root, "evidence.json", {"value": "b" * 64})

    def test_only_exact_review_bus_paths_are_fingerprint_excluded(self):
        self.assertTrue(CONTROL.fingerprint_excluded(".ai/REVIEW_REQUEST.md"))
        self.assertTrue(CONTROL.fingerprint_excluded(".ai/external-review-state.json"))
        self.assertTrue(CONTROL.fingerprint_excluded(".ai/REVIEW_HISTORY/review-1/result.md"))
        self.assertFalse(CONTROL.fingerprint_excluded(".ai/REVIEW_PROTOCOL.md"))
        self.assertFalse(CONTROL.fingerprint_excluded("src/kgnote/review.py"))

    def test_status_writer_replaces_stale_human_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = self.base_status() | {
                "schema_version": "kgnote.codex-status.v1",
                "implementation_state": "READY_FOR_REVIEW",
                "active_milestone_id": "M2",
                "next_action": "Independent reviewer inspects review-001.",
                "review": {
                    "state": "READY_FOR_REVIEW",
                    "current_review_id": "review-001",
                    "candidate_revision": "rev",
                    "candidate_fingerprint": "a" * 64,
                    "unresolved_findings": ["R-001"],
                    "human_decision_blockers": [],
                },
            }
            (root / "CODEX_STATUS.md").write_text(
                "# Status\n\n<!-- BEGIN CODEX STATUS JSON -->\n```json\n{}\n```\n"
                "<!-- END CODEX STATUS JSON -->\n\n## Human-readable handoff\n\nNo reviewer request exists.\n"
            )
            CONTROL.write_status(root, status)
            rendered = (root / "CODEX_STATUS.md").read_text()
            self.assertNotIn("No reviewer request exists", rendered)
            self.assertIn("review-001", rendered)
            self.assertIn("R-001", rendered)
            self.assertIn(status["next_action"], rendered)
            (root / "CODEX_STATUS.md").write_text(rendered.replace(status["next_action"], "stale next action"))
            self.assertTrue(CONTROL.validate_status_handoff(root, status))

    def test_decided_human_decision_requires_existing_non_ai_authority_record(self):
        request = self.base_review_request()
        decision = {
            "decision_id": "D-001",
            "question": "Which behavior?",
            "why_existing_authority_is_insufficient": "Active sources conflict.",
            "affected_requirements": ["KG-GOV-07"],
            "available_options": ["A", "B"],
            "observable_consequences": ["Behavior A", "Behavior B"],
            "blocking_scope": ["affected scope"],
            "linked_findings": ["R-001"],
            "status": "DECIDED",
            "review_id": request["review_id"],
            "candidate_revision": request["candidate_revision"],
            "candidate_fingerprint": request["candidate_fingerprint"],
            "selected_option": "A",
            "decided_by": "product owner",
            "decided_at": "2026-09-23T12:00:00+08:00",
            "authority_record": "docs/requirements/human-decisions/D-001.md",
        }
        document = {
            "schema_version": "kgnote.review-decisions.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "decisions": [decision],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/requirements").mkdir(parents=True)
            write_plan_with_human_authority(root / "PLAN.md")
            write_human_decision_authority(root / decision["authority_record"], decision)
            self.assertEqual(CONTROL.validate_decisions(document, root), [])
            decision["selected_option"] = "not-offered"
            self.assertTrue(any("not an available option" in error for error in CONTROL.validate_decisions(document, root)))
            decision["selected_option"] = "A"
            original_plan = (root / "PLAN.md").read_bytes()
            for unauthorized_identity in (
                "CHATGPT_WORK_REVIEWER",
                "codex-independent-reviewer:forged-human-label",
                "Unknown Person",
            ):
                decision["decided_by"] = unauthorized_identity
                write_human_decision_authority(root / decision["authority_record"], decision)
                errors = CONTROL.validate_decisions(document, root)
                self.assertTrue(any("not a positively authorized human identity" in error for error in errors))
                self.assertEqual((root / "PLAN.md").read_bytes(), original_plan)
            decision["decided_by"] = "product owner"
            write_human_decision_authority(root / decision["authority_record"], decision)
            decision["authority_record"] = ".ai/DECISIONS.md"
            (root / ".ai").mkdir()
            (root / ".ai/DECISIONS.md").write_text("queue\n")
            self.assertTrue(any("dedicated canonical record" in error for error in CONTROL.validate_decisions(document, root)))
            decision["authority_record"] = "docs/requirements/MISSING.md"
            self.assertTrue(any("dedicated canonical record" in error for error in CONTROL.validate_decisions(document, root)))

    def test_human_decision_authority_rejects_candidate_control_paths_and_unrelated_content(self):
        request = self.base_review_request()
        decision = {
            "decision_id": "D-001", "question": "Which behavior?",
            "why_existing_authority_is_insufficient": "Active sources conflict.",
            "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
            "observable_consequences": ["Behavior A", "Behavior B"],
            "blocking_scope": ["affected scope"], "linked_findings": ["R-001"],
            "status": "DECIDED", "review_id": request["review_id"],
            "candidate_revision": request["candidate_revision"],
            "candidate_fingerprint": request["candidate_fingerprint"],
            "selected_option": "A", "decided_by": "product owner",
            "decided_at": "2026-09-23T12:00:00+08:00",
            "authority_record": "docs/requirements/human-decisions/D-001.md",
        }
        document = {
            "schema_version": "kgnote.review-decisions.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "decisions": [decision],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan_with_human_authority(root / "PLAN.md")
            write_human_decision_authority(root / decision["authority_record"], decision)
            self.assertEqual(CONTROL.validate_decisions(document, root), [])

            canonical_path = decision["authority_record"]
            for forbidden in (
                "PLAN.md",
                "scripts/codex_control.py",
                "tests/control_plane/test_codex_control.py",
                ".ai/REVIEW_PROTOCOL.md",
                "docs/requirements/DECISION.md",
            ):
                decision["authority_record"] = forbidden
                self.assertTrue(any(
                    "dedicated canonical record" in error
                    for error in CONTROL.validate_decisions(document, root)
                ))

            decision["authority_record"] = canonical_path
            authority_path = root / canonical_path
            canonical_bytes = authority_path.read_bytes()
            authority_path.write_bytes(canonical_bytes + b"\nUnrelated same-file mutation.\n")
            self.assertTrue(any(
                "non-canonical or unrelated content" in error
                for error in CONTROL.validate_decisions(document, root)
            ))

    def test_rereview_request_keeps_fixed_pending_finding_visible(self):
        request = self.base_review_request()
        request["status"] = "IMPLEMENTING"
        result = self.submitted_result("CHANGES_REQUIRED")
        result["findings"] = [{
            "finding_id": "R-001",
            "severity": "BLOCKER",
            "authority_source": "authority.md",
            "expected_behavior": "Finding persists.",
            "observed_behavior": "Finding was hidden.",
            "evidence": ["evidence"],
            "affected_files_or_behavior": ["status"],
            "required_resolution": "Keep it visible.",
            "verification_method": "read-back",
            "status": "FIXED_PENDING_REVIEW",
        }]
        plan = self.base_plan()
        status = self.base_status() | {
            "implementation_state": "IMPLEMENTING",
            "review": {
                "state": "IMPLEMENTING",
                "current_review_id": "review-example-001",
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "unresolved_findings": ["R-001"],
                "human_decision_blockers": [],
            },
            "verification": {"candidate_verified": False, "release_verified": False},
            "next_action": "fix",
        }
        evidence = {"gates": []}
        captured = {}
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(CONTROL, "preflight", return_value={"status": "pass"}), \
             mock.patch.object(CONTROL, "load_plan_status", return_value=(plan, status)), \
             mock.patch.object(CONTROL, "load_review_artifacts", return_value=(request, result, {"decisions": []})), \
             mock.patch.object(CONTROL, "repository_fingerprint", return_value={"value": "d" * 64, "head": "c" * 40}), \
             mock.patch.object(CONTROL, "repository_manifest", return_value=request["candidate_manifest"]), \
             mock.patch.object(CONTROL, "authorized_human_decision_identities", return_value=({"product owner"}, [])), \
             mock.patch.object(CONTROL, "load_verification_evidence", return_value=evidence), \
             mock.patch.object(CONTROL, "validate_review_request", return_value=[]), \
             mock.patch.object(CONTROL, "replace_embedded_json"), \
             mock.patch.object(CONTROL, "write_review_request"), \
             mock.patch.object(CONTROL, "archive_review_artifact", return_value="snapshot.md"), \
             mock.patch.object(CONTROL, "write_status", side_effect=lambda _repo, value: captured.update(value)):
            output = CONTROL.prepare_review_request(
                Path(tmp), "evidence.json", ["control plane"], ["review focus"], [], []
            )
        self.assertEqual(output["review_id"], "review-example-002")
        self.assertEqual(captured["review"]["unresolved_findings"], ["R-001"])
        self.assertTrue(any("R-001" in item for item in request["reviewer_focus"]))
        self.assertEqual(request["acceptance_criteria"], ["current milestone exact"])

    def test_verification_command_is_repository_relative(self):
        repo = Path("/private/example/KGnote")
        rendered = CONTROL.repository_relative_command(
            repo, ["/private/example/KGnote/.venv/bin/python", "verify.py"]
        )
        self.assertEqual(rendered, "./.venv/bin/python verify.py")

    def test_pre_custody_invalidation_allocates_new_review_and_audits_reason(self):
        request = self.base_review_request()
        status = self.base_status() | {
            "implementation_state": "READY_FOR_REVIEW",
            "review": {
                "state": "READY_FOR_REVIEW",
                "current_review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "unresolved_findings": [],
                "human_decision_blockers": [],
            },
            "verification": {"candidate_verified": True, "release_verified": False, "control_plane_ready": True},
            "next_action": "review",
        }
        captured_status = {}
        captured_events = []
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(CONTROL, "load_review_artifacts", return_value=(request, self.empty_review_result(), {"decisions": []})), \
             mock.patch.object(CONTROL, "replace_embedded_json"), \
             mock.patch.object(CONTROL, "write_review_request"), \
             mock.patch.object(CONTROL, "load_plan_status", return_value=(self.base_plan(), status)), \
             mock.patch.object(CONTROL, "history_unresolved_finding_ids", return_value=[]), \
             mock.patch.object(CONTROL, "write_status", side_effect=lambda _repo, value: captured_status.update(value)), \
             mock.patch.object(CONTROL, "append_history_event", side_effect=lambda _repo, value: captured_events.append(value)):
            output = CONTROL.invalidate_ready_request(Path(tmp), "completion audit found a gap")
        self.assertEqual(output["invalidated_review_id"], "review-example-001")
        self.assertEqual(output["next_review_id"], "review-example-002")
        self.assertEqual(request["status"], "IMPLEMENTING")
        self.assertIsNone(request["candidate_fingerprint"])
        self.assertEqual(captured_status["review"]["state"], "IMPLEMENTING")
        self.assertEqual(captured_events[0]["event_type"], "INVALIDATED")
        self.assertIn("completion audit", captured_events[0]["reason"])


class RepositoryIntegrityTests(unittest.TestCase):
    def test_current_selectors_resolve_exactly(self):
        self.assertEqual(CONTROL.validate_selectors(ROOT), [])

    def test_current_generated_views_are_fresh(self):
        self.assertEqual(CONTROL.validate_generated_views(ROOT), [])

    def test_generated_view_check_does_not_require_temp_directory(self):
        with mock.patch.object(CONTROL.tempfile, "TemporaryDirectory", side_effect=AssertionError("must not be used")):
            self.assertEqual(CONTROL.validate_generated_views(ROOT), [])

    def test_current_authority_lock_matches(self):
        errors, lock = CONTROL.validate_authority(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(lock["conflict_policy"], "fail_closed_authority_drift")

    def test_current_review_artifacts_are_valid(self):
        errors, artifacts = CONTROL.validate_review_artifacts(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(artifacts["request"]["protocol_version"], "kgnote.review-protocol.v1")

    def test_review_schemas_are_valid_and_current_artifacts_conform(self):
        schema_root = ROOT / ".ai/schemas"
        request, result, decisions = CONTROL.load_review_artifacts(ROOT)
        pairs = (
            ("review-request.schema.json", request),
            ("review-result.schema.json", result),
            ("review-decisions.schema.json", decisions),
            ("review-history-index.schema.json", json.loads((ROOT / ".ai/REVIEW_HISTORY/index.json").read_text())),
            ("orchestrator-state.schema.json", json.loads((ROOT / ".ai/ORCHESTRATOR_STATE.json").read_text())),
        )
        for name, artifact in pairs:
            schema = json.loads((schema_root / name).read_text())
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema).validate(artifact)

    def test_current_orchestrator_state_matches_plan_and_review_bus(self):
        plan, _ = CONTROL.load_plan_status(ROOT)
        request, _, _ = CONTROL.load_review_artifacts(ROOT)
        self.assertEqual(CONTROL.validate_orchestrator_state(ROOT, plan, request), [])

    def test_fresh_agent_can_reconstruct_resume_state_from_repository_only(self):
        plan, status = CONTROL.load_plan_status(ROOT)
        request, result, decisions = CONTROL.load_review_artifacts(ROOT)
        self.assertEqual(plan["goal_id"], status["goal_id"])
        self.assertEqual(plan["active_milestone_id"], status["active_milestone_id"])
        self.assertIn(status["implementation_state"], CONTROL.REVIEW_STATES)
        self.assertIn("current_review_id", status["review"])
        self.assertIn("candidate_fingerprint", status["review"])
        self.assertIsInstance(status["review"]["unresolved_findings"], list)
        self.assertIsInstance(status["review"]["human_decision_blockers"], list)
        self.assertTrue(status["next_action"])
        self.assertTrue(request["authoritative_specs"])
        self.assertIn(result["artifact_state"], {"EMPTY", "SUBMITTED"})
        self.assertIsInstance(decisions["decisions"], list)


class ReviewFlowSimulationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ControlPlaneNegativeTests()

    def finding(self, status="OPEN"):
        return {
            "finding_id": "R-001",
            "severity": "BLOCKER",
            "authority_source": "authority.md#rule",
            "expected_behavior": "Candidate binds to the exact fingerprint.",
            "observed_behavior": "A stale fingerprint was accepted.",
            "evidence": ["test evidence"],
            "affected_files_or_behavior": ["review guard"],
            "required_resolution": "Reject stale candidates.",
            "verification_method": "negative test",
            "status": status,
        }

    def test_implement_review_pass_flow(self):
        self.assertEqual(CONTROL.validate_review_transition("IMPLEMENTING", "READY_FOR_REVIEW", "CODEX_IMPLEMENTER"), [])
        self.assertEqual(CONTROL.validate_review_transition("READY_FOR_REVIEW", "UNDER_REVIEW", "CHATGPT_WORK_REVIEWER"), [])
        request = self.fixture.base_review_request()
        request["status"] = "UNDER_REVIEW"
        result = self.fixture.submitted_result("PASS")
        self.assertEqual(CONTROL.validate_review_result(request, result, {"decisions": []}), [])
        self.assertEqual(CONTROL.validate_review_transition("UNDER_REVIEW", "PASS", "CHATGPT_WORK_REVIEWER"), [])

    def test_changes_fix_rereview_pass_flow_preserves_finding(self):
        request = self.fixture.base_review_request()
        request["status"] = "UNDER_REVIEW"
        changes = self.fixture.submitted_result("CHANGES_REQUIRED")
        changes["findings"] = [self.finding("OPEN")]
        self.assertEqual(CONTROL.validate_review_result(request, changes, {"decisions": []}), [])
        self.assertEqual(CONTROL.validate_review_transition("UNDER_REVIEW", "CHANGES_REQUIRED", "CHATGPT_WORK_REVIEWER"), [])
        self.assertEqual(CONTROL.validate_review_transition("CHANGES_REQUIRED", "IMPLEMENTING", "CODEX_IMPLEMENTER"), [])
        self.assertEqual(CONTROL.validate_finding_transition("OPEN", "FIXED_PENDING_REVIEW", "CODEX_IMPLEMENTER"), [])
        changes["findings"][0]["status"] = "FIXED_PENDING_REVIEW"
        new_fingerprint = "d" * 64
        rerequest = copy.deepcopy(request)
        rerequest.update({
            "review_id": "review-example-002",
            "status": "UNDER_REVIEW",
            "candidate_fingerprint": new_fingerprint,
            "candidate_revision": f"{'c' * 40}+worktree:{new_fingerprint}",
        })
        passed = copy.deepcopy(changes)
        passed.update({
            "review_id": rerequest["review_id"],
            "reviewed_revision": rerequest["candidate_revision"],
            "reviewed_fingerprint": new_fingerprint,
            "verdict": "PASS",
            "unverified_requirements": [],
            "human_decisions_required": [],
        })
        passed["findings"][0]["status"] = "VERIFIED"
        self.assertEqual(CONTROL.validate_finding_transition("FIXED_PENDING_REVIEW", "VERIFIED", "CHATGPT_WORK_REVIEWER"), [])
        self.assertEqual(CONTROL.validate_review_result(rerequest, passed, {"decisions": []}), [])
        self.assertEqual(passed["findings"][0]["finding_id"], "R-001")

    def test_product_decision_human_implement_review_flow(self):
        request = self.fixture.base_review_request()
        request["status"] = "UNDER_REVIEW"
        decision = {
            "decision_id": "D-001",
            "question": "Which observable behavior is approved?",
            "why_existing_authority_is_insufficient": "Two active requirements conflict.",
            "affected_requirements": ["KG-GOV-07"],
            "available_options": ["A", "B"],
            "observable_consequences": ["Behavior A", "Behavior B"],
            "blocking_scope": ["affected renderer"],
            "linked_findings": [],
            "status": "PENDING_HUMAN",
            "review_id": request["review_id"],
            "candidate_revision": request["candidate_revision"],
            "candidate_fingerprint": request["candidate_fingerprint"],
            "selected_option": None,
            "decided_by": None,
            "decided_at": None,
            "authority_record": None,
        }
        decisions = {"schema_version": "kgnote.review-decisions.v1", "protocol_version": "kgnote.review-protocol.v1", "decisions": [decision]}
        result = self.fixture.submitted_result("PRODUCT_DECISION_REQUIRED")
        result["human_decisions_required"] = ["D-001"]
        self.assertEqual(CONTROL.validate_decisions(decisions), [])
        self.assertEqual(CONTROL.validate_review_result(request, result, decisions), [])
        self.assertEqual(CONTROL.validate_review_transition("UNDER_REVIEW", "PRODUCT_DECISION_REQUIRED", "CHATGPT_WORK_REVIEWER"), [])
        decision.update({
            "status": "DECIDED",
            "selected_option": "A",
            "decided_by": "product owner",
            "decided_at": "2026-09-23T11:00:00+08:00",
            "authority_record": "docs/requirements/decision.md",
        })
        self.assertEqual(CONTROL.validate_decisions(decisions), [])
        self.assertEqual(CONTROL.validate_review_transition("PRODUCT_DECISION_REQUIRED", "IMPLEMENTING", "HUMAN_DECISION_AUTHORITY"), [])
        self.assertEqual(CONTROL.validate_review_transition("IMPLEMENTING", "READY_FOR_REVIEW", "CODEX_IMPLEMENTER"), [])


class ReviewHelperIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ControlPlaneNegativeTests()

    def write_embedded(self, path, title, begin, end, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {title}\n\n{begin}\n```json\n{json.dumps(value, indent=2)}\n```\n{end}\n"
        )

    def make_repo(self, root):
        subprocess.run(["git", "init", "-b", "test"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        (root / ".gitignore").write_text("output/\n")
        (root / "authority.md").write_text("# Authority\n")
        (root / "implementation.txt").write_text("candidate one\n")
        (root / ".ai").mkdir()
        (root / ".ai/REVIEW_PROTOCOL.md").write_text("# Protocol\n")
        plan = {
            "schema_version": "kgnote.codex-plan.v1",
            "goal_id": "G",
            "status": "active",
            "active_milestone_id": "RP-X",
            "product_direction_id": "D",
            "explicit_direction": {"speaker": "product owner"},
            "preserved_human_gates": [],
            "milestones": [{
                "id": "RP-X", "status": "active", "dependencies": [], "human_gate": "none",
                "owned_paths": ["implementation.txt"], "acceptance": ["flow completes"],
            }],
        }
        self.write_embedded(root / "PLAN.md", "Plan", CONTROL.PLAN_BEGIN, CONTROL.PLAN_END, plan)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        fingerprint = CONTROL.repository_fingerprint(root)
        request = self.fixture.base_review_request()
        request.update({
            "milestone_id": "RP-X",
            "base_revision": fingerprint["head"],
            "candidate_revision": f"{fingerprint['head']}+worktree:{fingerprint['value']}",
            "candidate_fingerprint": fingerprint["value"],
            "candidate_manifest": CONTROL.repository_manifest(root),
            "authoritative_specs": ["authority.md"],
        })
        result = self.fixture.empty_review_result()
        decisions = {
            "schema_version": "kgnote.review-decisions.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "decisions": [],
        }
        self.write_embedded(root / ".ai/REVIEW_REQUEST.md", "Request", CONTROL.REVIEW_REQUEST_BEGIN, CONTROL.REVIEW_REQUEST_END, request)
        request_path = root / ".ai/REVIEW_REQUEST.md"
        request_path.write_text(request_path.read_text() + "\n## Human-readable status\n\nplaceholder\n")
        CONTROL.write_review_request(root, request)
        self.write_embedded(root / ".ai/REVIEW_RESULT.md", "Result", CONTROL.REVIEW_RESULT_BEGIN, CONTROL.REVIEW_RESULT_END, result)
        self.write_embedded(root / ".ai/DECISIONS.md", "Decisions", CONTROL.DECISIONS_BEGIN, CONTROL.DECISIONS_END, decisions)
        history = root / ".ai/REVIEW_HISTORY"
        history.mkdir()
        (history / "events.jsonl").write_text(json.dumps({
            "event_id": "evt-0001", "event_type": "PROTOCOL_INITIALIZED", "review_id": request["review_id"],
            "actor_role": "CODEX_IMPLEMENTER", "candidate_fingerprint": None, "snapshot_path": None,
            "snapshot_sha256": None, "created_at": "2026-09-23T09:00:00+08:00",
        }, separators=(",", ":")) + "\n")
        (history / "index.json").write_text(json.dumps({
            "schema_version": "kgnote.review-history-index.v1",
            "protocol_version": "kgnote.review-protocol.v1",
            "event_count": 1,
            "last_event_id": "evt-0001",
            "reviews": {},
            "findings": {},
        }, indent=2) + "\n")
        status = {
            "schema_version": "kgnote.codex-status.v1",
            "updated_at": "2026-09-23T09:00:00+08:00",
            "goal_id": "G", "goal_status": "active", "active_milestone_id": "RP-X",
            "milestone_status": "active", "product_direction_id": "D",
            "git": {"branch": "test", "head": fingerprint["head"]},
            "working_state": {"fingerprint": fingerprint["value"], "unexpected_dirty_paths": []},
            "implementation_state": "READY_FOR_REVIEW",
            "review": {
                "state": "READY_FOR_REVIEW", "current_review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "unresolved_findings": [], "human_decision_blockers": [],
            },
            "verification": {"candidate_verified": True, "release_verified": False, "control_plane_ready": True},
            "next_action": "Reviewer accepts custody.",
        }
        (root / "CODEX_STATUS.md").write_text(
            "# Status\n\n<!-- BEGIN CODEX STATUS JSON -->\n```json\n{}\n```\n"
            "<!-- END CODEX STATUS JSON -->\n\n## Human-readable handoff\n\nplaceholder\n"
        )
        CONTROL.write_status(root, status)
        return plan, status, request

    def finding(self, status="OPEN"):
        return {
            "finding_id": "R-001", "severity": "BLOCKER", "authority_source": "authority.md",
            "expected_behavior": "Finding remains visible.", "observed_behavior": "Finding disappeared.",
            "evidence": ["integration evidence"], "affected_files_or_behavior": ["review state"],
            "required_resolution": "Preserve finding identity.", "verification_method": "integration replay",
            "status": status,
        }

    def write_result(self, root, request, verdict, findings=None, decisions=None):
        result = self.fixture.submitted_result(verdict)
        result.update({
            "review_id": request["review_id"],
            "reviewed_revision": request["candidate_revision"],
            "reviewed_fingerprint": request["candidate_fingerprint"],
            "findings": findings or [],
            "human_decisions_required": decisions or [],
        })
        CONTROL.replace_embedded_json(
            root / ".ai/REVIEW_RESULT.md", CONTROL.REVIEW_RESULT_BEGIN, CONTROL.REVIEW_RESULT_END, result
        )
        return result

    def evidence_for_current_candidate(self, root):
        fingerprint = CONTROL.repository_fingerprint(root)
        evidence = {
            "result": "pass", "claims": {"candidate_verified": True, "release_verified": False},
            "fingerprint_stable": True, "fingerprint_before": fingerprint, "fingerprint_after": fingerprint,
            "gates": [],
        }
        path = root / "output/evidence.json"
        path.parent.mkdir()
        path.write_text(json.dumps(evidence))
        return "output/evidence.json"

    def test_helper_flow_implement_review_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            request, _, _ = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "PASS")
            submitted = CONTROL.archive_submitted_result(root)
            self.assertEqual(submitted["verdict"], "PASS")
            self.assertEqual(CONTROL.validate_review_artifacts(root)[0], [])

    def test_helper_flow_changes_fix_rereview_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            request, _, _ = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "CHANGES_REQUIRED", [self.finding()])
            CONTROL.archive_submitted_result(root)
            CONTROL.resume_implementation(root)
            CONTROL.mark_finding_fixed(root, "R-001", ["regression test passed"])
            (root / "implementation.txt").write_text("candidate two\n")
            evidence = self.evidence_for_current_candidate(root)
            with mock.patch.object(CONTROL, "preflight", return_value={"status": "pass"}):
                prepared = CONTROL.prepare_review_request(root, evidence, ["implementation"], ["recheck"], [], [])
            self.assertEqual(prepared["review_id"], "review-example-002")
            _, status = CONTROL.load_plan_status(root)
            self.assertEqual(status["review"]["unresolved_findings"], ["R-001"])
            CONTROL.accept_review_custody(root, "reviewer-2")
            request, _, _ = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "PASS", [self.finding("VERIFIED")])
            CONTROL.archive_submitted_result(root)
            self.assertEqual(CONTROL.validate_review_artifacts(root)[0], [])
            _, status = CONTROL.load_plan_status(root)
            self.assertEqual(status["review"]["unresolved_findings"], [])

    def test_reviewer_cannot_self_author_human_supersession(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            request, _, _ = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "CHANGES_REQUIRED", [self.finding()])
            CONTROL.archive_submitted_result(root)
            CONTROL.resume_implementation(root)
            CONTROL.mark_finding_fixed(root, "R-001", ["supersession regression prepared"])
            (root / "implementation.txt").write_text("candidate two\n")
            evidence = self.evidence_for_current_candidate(root)
            with mock.patch.object(CONTROL, "preflight", return_value={"status": "pass"}):
                CONTROL.prepare_review_request(root, evidence, ["finding lifecycle"], ["recheck R-001"], [], [])

            events, errors = CONTROL.read_history_events(root)
            self.assertEqual(errors, [])
            fixes_event = next(event for event in events if event.get("event_type") == "FIXES_PROPOSED")
            self.assertEqual(fixes_event["actor_role"], "CODEX_IMPLEMENTER")

            CONTROL.accept_review_custody(root, "reviewer-2")
            request, _, decisions = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "CHANGES_REQUIRED", [self.finding("OPEN")])
            self.assertEqual(CONTROL.validate_pending_review_result(root)[0], [])

            self.write_result(root, request, "PASS", [self.finding("SUPERSEDED_BY_HUMAN_DECISION")])
            pending_errors, _ = CONTROL.validate_pending_review_result(root)
            self.assertTrue(any("linked DECIDED human decision" in error for error in pending_errors))
            self.assertTrue(any("requires HUMAN_DECISION_AUTHORITY" in error for error in pending_errors))

            history_before = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_text()
            with self.assertRaisesRegex(ValueError, "linked DECIDED human decision"):
                CONTROL.archive_submitted_result(root)
            self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_text(), history_before)
            index = json.loads((root / ".ai/REVIEW_HISTORY/index.json").read_text())
            self.assertEqual(index["findings"]["R-001"]["status"], "FIXED_PENDING_REVIEW")
            _, status = CONTROL.load_plan_status(root)
            self.assertEqual(status["review"]["unresolved_findings"], ["R-001"])

            decisions["decisions"] = [{
                "decision_id": "D-001", "question": "May R-001 be superseded?",
                "why_existing_authority_is_insufficient": "A human ruling is required.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["supersede", "retain"],
                "observable_consequences": ["R-001 is superseded", "R-001 remains unresolved"],
                "blocking_scope": ["finding lifecycle"], "linked_findings": ["R-001"],
                "status": "DECIDED", "review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "selected_option": "supersede",
                "decided_by": "codex-independent-reviewer:forged-human-label",
                "decided_at": "2026-09-23T12:00:00+08:00",
                "authority_record": "docs/requirements/human-decisions/D-001.md",
            }]
            write_human_decision_authority(root / decisions["decisions"][0]["authority_record"], decisions["decisions"][0])
            CONTROL.replace_embedded_json(
                root / ".ai/DECISIONS.md", CONTROL.DECISIONS_BEGIN, CONTROL.DECISIONS_END, decisions
            )
            pending_errors, _ = CONTROL.validate_pending_review_result(root)
            self.assertTrue(any("not a positively authorized human identity" in error for error in pending_errors))
            history_before = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_text()
            status_before = (root / "CODEX_STATUS.md").read_text()
            with self.assertRaises(ValueError):
                CONTROL.archive_submitted_result(root)
            self.assertEqual((root / ".ai/REVIEW_HISTORY/events.jsonl").read_text(), history_before)
            self.assertEqual((root / "CODEX_STATUS.md").read_text(), status_before)

    def test_structured_human_authority_allows_supersession_on_new_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            decision_request, _, decisions = CONTROL.load_review_artifacts(root)
            self.write_result(root, decision_request, "CHANGES_REQUIRED", [self.finding()])
            CONTROL.archive_submitted_result(root)
            CONTROL.resume_implementation(root)
            CONTROL.mark_finding_fixed(root, "R-001", ["human supersession regression prepared"])
            decision = {
                "decision_id": "D-001", "question": "May R-001 be superseded?",
                "why_existing_authority_is_insufficient": "A human ruling is required.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["supersede", "retain"],
                "observable_consequences": ["R-001 is superseded", "R-001 remains unresolved"],
                "blocking_scope": ["finding lifecycle"], "linked_findings": ["R-001"],
                "status": "DECIDED", "review_id": decision_request["review_id"],
                "candidate_revision": decision_request["candidate_revision"],
                "candidate_fingerprint": decision_request["candidate_fingerprint"],
                "selected_option": "supersede", "decided_by": "product owner",
                "decided_at": "2026-09-23T12:00:00+08:00",
                "authority_record": "docs/requirements/human-decisions/D-001.md",
            }
            decisions["decisions"] = [decision]
            write_human_decision_authority(root / decision["authority_record"], decision)
            CONTROL.replace_embedded_json(
                root / ".ai/DECISIONS.md", CONTROL.DECISIONS_BEGIN, CONTROL.DECISIONS_END, decisions
            )
            (root / "implementation.txt").write_text("candidate after human decision\n")
            evidence = self.evidence_for_current_candidate(root)
            with mock.patch.object(CONTROL, "preflight", return_value={"status": "pass"}):
                CONTROL.prepare_review_request(root, evidence, ["finding lifecycle"], ["recheck R-001"], [], [])
            CONTROL.accept_review_custody(root, "reviewer-2")
            request, _, _ = CONTROL.load_review_artifacts(root)
            self.write_result(root, request, "PASS", [self.finding("SUPERSEDED_BY_HUMAN_DECISION")])
            self.assertEqual(CONTROL.validate_pending_review_result(root)[0], [])
            submitted = CONTROL.archive_submitted_result(root)
            self.assertEqual(submitted["verdict"], "PASS")
            index = json.loads((root / ".ai/REVIEW_HISTORY/index.json").read_text())
            self.assertEqual(index["findings"]["R-001"]["status"], "SUPERSEDED_BY_HUMAN_DECISION")

    def test_helper_flow_product_decision_human_implement_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            request, _, decisions = CONTROL.load_review_artifacts(root)
            decision = {
                "decision_id": "D-001", "question": "Which behavior?",
                "why_existing_authority_is_insufficient": "Two sources conflict.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
                "observable_consequences": ["Behavior A", "Behavior B"], "blocking_scope": ["implementation"],
                "linked_findings": [], "status": "PENDING_HUMAN", "review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"], "selected_option": None,
                "decided_by": None, "decided_at": None, "authority_record": None,
            }
            decisions["decisions"] = [decision]
            CONTROL.replace_embedded_json(root / ".ai/DECISIONS.md", CONTROL.DECISIONS_BEGIN, CONTROL.DECISIONS_END, decisions)
            self.write_result(root, request, "PRODUCT_DECISION_REQUIRED", decisions=["D-001"])
            CONTROL.archive_submitted_result(root)
            decision.update({
                "status": "DECIDED", "selected_option": "A", "decided_by": "product owner",
                "decided_at": "2026-09-23T12:00:00+08:00",
                "authority_record": "docs/requirements/human-decisions/D-001.md",
            })
            write_human_decision_authority(root / decision["authority_record"], decision)
            CONTROL.replace_embedded_json(root / ".ai/DECISIONS.md", CONTROL.DECISIONS_BEGIN, CONTROL.DECISIONS_END, decisions)
            CONTROL.resume_implementation(root)
            (root / "implementation.txt").write_text("candidate after decision\n")
            evidence = self.evidence_for_current_candidate(root)
            with mock.patch.object(CONTROL, "preflight", return_value={"status": "pass"}):
                prepared = CONTROL.prepare_review_request(root, evidence, ["implementation"], ["review decision"], [], [])
            self.assertEqual(prepared["review_id"], "review-example-002")
            request, result, _ = CONTROL.load_review_artifacts(root)
            self.assertEqual(request["status"], "READY_FOR_REVIEW")
            self.assertEqual(result["artifact_state"], "EMPTY")
            self.assertEqual(CONTROL.validate_review_artifacts(root)[0], [])

    def test_actor_mismatch_requires_append_only_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            CONTROL.accept_review_custody(root, "reviewer-1")
            request, _, _ = CONTROL.load_review_artifacts(root)
            finding = self.finding()
            self.write_result(root, request, "CHANGES_REQUIRED", [finding])
            CONTROL.archive_submitted_result(root)
            CONTROL.resume_implementation(root)
            CONTROL.mark_finding_fixed(root, "R-001", ["actor correction regression"])
            _, result, _ = CONTROL.load_review_artifacts(root)
            CONTROL.append_history_event(root, {
                "event_type": "FIXES_PROPOSED",
                "review_id": request["review_id"],
                "actor_role": "CHATGPT_WORK_REVIEWER",
                "candidate_fingerprint": request["candidate_fingerprint"],
                "snapshot_path": None,
                "snapshot_sha256": None,
                "findings": result["findings"],
                "created_at": "2026-09-23T12:00:00+08:00",
            })
            original_lines = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_text().splitlines()
            bad_event = json.loads(original_lines[-1])
            errors = CONTROL.validate_review_artifacts(root)[0]
            self.assertTrue(any("FIXES_PROPOSED requires actor CODEX_IMPLEMENTER" in error for error in errors))
            correction = CONTROL.append_history_actor_correction(root, bad_event["event_id"], "Repair actor attribution.")
            corrected_lines = (root / ".ai/REVIEW_HISTORY/events.jsonl").read_text().splitlines()
            self.assertEqual(corrected_lines[:-1], original_lines)
            self.assertEqual(correction["corrects_event_id"], bad_event["event_id"])
            self.assertEqual(correction["corrected_actor_role"], "CODEX_IMPLEMENTER")
            self.assertEqual(CONTROL.validate_review_artifacts(root)[0], [])


if __name__ == "__main__":
    unittest.main()
