import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "codex_control_completion_gate", ROOT / "scripts/codex_control.py"
)
assert SPEC and SPEC.loader
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


class ReviewCompletionGateTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        repo = Path(temporary.name)
        (repo / "web").mkdir()
        (repo / "src/kgnote/personal_alpha").mkdir(parents=True)
        (repo / "tests").mkdir()
        (repo / "docs/requirements").mkdir(parents=True)
        (repo / "docs/requirements/evidence").mkdir()
        (repo / "web/learn-workspace.js").write_text("export const learn = true;\n")
        (repo / "src/kgnote/personal_alpha/workspace.py").write_text("def project(): return True\n")
        (repo / "tests/test_issue9_gate.py").write_text(
            "class Issue9GateTests:\n"
            "    def test_real_web_and_obsidian_ids_match(self): pass\n"
            "    def test_mutated_web_id_is_rejected(self): pass\n"
            "    def test_exact_candidate_evidence_is_accepted(self): pass\n"
            "    def test_missing_exact_candidate_evidence_is_rejected(self): pass\n"
        )
        scenarios = {
            "schema_version": "kgnote.scenarios.v1",
            "status": "active",
            "scenarios": [
                {
                    "id": "SC-35",
                    "title": "需求追溯與驗證證據",
                    "test_binding": None,
                    "run_status": "not_run",
                }
            ],
        }
        (repo / "docs/requirements/scenarios.json").write_text(json.dumps(scenarios))
        plan = {
            "goal_id": "GOAL-ISSUE9-COMPLETION-GATE",
            "active_milestone_id": "M1",
            "milestones": [
                {
                    "id": "M1",
                    "status": "active",
                    "completion_gate": {
                        "evidence_path": "docs/requirements/evidence/completion.json",
                        "required_claims": [
                            {
                                "claim_id": "finding-web-identity-readback-missing",
                                "required_product_entrypoints": [
                                    "web/learn-workspace.js",
                                    "src/kgnote/personal_alpha/workspace.py",
                                ],
                                "required_evidence_kinds": [
                                    "positive_test",
                                    "negative_test",
                                    "render_click",
                                    "read_back",
                                ],
                                "required_scenarios": ["SC-35"],
                            },
                            {
                                "claim_id": "finding-no-render-click-or-tracked-evidence",
                                "required_product_entrypoints": ["web/learn-workspace.js"],
                                "required_evidence_kinds": [
                                    "positive_test",
                                    "negative_test",
                                    "candidate_identity",
                                    "read_back",
                                ],
                                "required_scenarios": ["SC-35"],
                            },
                        ],
                    },
                }
            ],
        }
        return temporary, repo, plan

    def claim(
        self,
        claim_id,
        *,
        entrypoints,
        positive_selector,
        negative_selector,
        evidence_kinds,
        finding_ids=None,
        disposition="FIXED_PENDING_REVIEW",
    ):
        return {
            "claim_id": claim_id,
            "finding_ids": finding_ids or [claim_id],
            "disposition": disposition,
            "authority_refs": ["FD-05", "FD-06", "RC-15", "RC-16", "SC-35"],
            "forbidden_substitutes": [
                "A generated static page or same-source JSON comparison is not the existing Web consumer."
            ],
            "product_entrypoints": entrypoints,
            "observable_behavior": "The existing Web surface and Obsidian projection expose the same canonical IDs.",
            "resolution_basis": "The check targets both real consumers and mutates the Web-side identity independently.",
            "acceptance_scenarios": [
                {
                    "scenario_id": "SC-35",
                    "polarity": "positive",
                    "test_refs": [
                        {
                            "path": "tests/test_issue9_gate.py",
                            "selector": positive_selector,
                        }
                    ],
                },
                {
                    "scenario_id": "SC-35",
                    "polarity": "negative",
                    "test_refs": [
                        {
                            "path": "tests/test_issue9_gate.py",
                            "selector": negative_selector,
                        }
                    ],
                },
            ],
            "evidence": [
                {
                    "kind": kind,
                    "status": "PASS",
                    "reference": f"test evidence for {kind}",
                }
                for kind in evidence_kinds
            ],
        }

    def valid_evidence(self):
        return {
            "schema_version": "kgnote.review-completion-evidence.v1",
            "goal_id": "GOAL-ISSUE9-COMPLETION-GATE",
            "milestone_id": "M1",
            "review_case": {
                "pull_request": 29,
                "candidate_commit": "be8fc7eeaac93d86b6921504ce11a1bac51a0dc0",
                "comment_ids": [6285208843, 6285487763, 6285693992],
            },
            "claims": [
                self.claim(
                    "finding-web-identity-readback-missing",
                    entrypoints=[
                        "web/learn-workspace.js",
                        "src/kgnote/personal_alpha/workspace.py",
                    ],
                    positive_selector="Issue9GateTests.test_real_web_and_obsidian_ids_match",
                    negative_selector="Issue9GateTests.test_mutated_web_id_is_rejected",
                    evidence_kinds=[
                        "positive_test",
                        "negative_test",
                        "render_click",
                        "read_back",
                    ],
                ),
                self.claim(
                    "finding-no-render-click-or-tracked-evidence",
                    entrypoints=["web/learn-workspace.js"],
                    positive_selector="Issue9GateTests.test_exact_candidate_evidence_is_accepted",
                    negative_selector="Issue9GateTests.test_missing_exact_candidate_evidence_is_rejected",
                    evidence_kinds=[
                        "positive_test",
                        "negative_test",
                        "candidate_identity",
                        "read_back",
                    ],
                ),
            ],
            "limits": [
                "Semantic teaching quality remains for the independent product reviewer."
            ],
        }

    def write_evidence(self, repo, evidence):
        path = repo / "docs/requirements/evidence/completion.json"
        path.write_text(json.dumps(evidence, indent=2) + "\n")

    def test_issue9_static_fake_web_surface_cannot_replace_required_entrypoints(self):
        temporary, repo, plan = self.fixture()
        try:
            evidence = self.valid_evidence()
            fake = repo / ".kgnote/web-learning.html"
            fake.parent.mkdir()
            fake.write_text("<html>same IDs</html>\n")
            evidence["claims"][0]["product_entrypoints"] = [
                ".kgnote/web-learning.html",
                "src/kgnote/personal_alpha/workspace.py",
            ]
            self.write_evidence(repo, evidence)
            summary, errors = CONTROL.validate_review_completion_gate(repo, plan)
            self.assertFalse(summary["passed"])
            self.assertTrue(
                any("web/learn-workspace.js" in error and "required product entrypoint" in error for error in errors),
                errors,
            )
        finally:
            temporary.cleanup()

    def test_required_render_click_not_verified_blocks_review_without_becoming_pass(self):
        temporary, repo, plan = self.fixture()
        try:
            evidence = self.valid_evidence()
            render = next(
                item
                for item in evidence["claims"][0]["evidence"]
                if item["kind"] == "render_click"
            )
            render["status"] = "NOT_VERIFIED"
            render["reference"] = "Browser environment unavailable; no click evidence exists."
            self.write_evidence(repo, evidence)
            summary, errors = CONTROL.validate_review_completion_gate(repo, plan)
            self.assertFalse(summary["passed"])
            self.assertIn(
                "finding-web-identity-readback-missing: required evidence render_click is NOT_VERIFIED",
                errors,
            )
            self.assertEqual("NOT_VERIFIED", summary["claims"][0]["evidence_status"]["render_click"])
        finally:
            temporary.cleanup()

    def test_valid_issue9_case_with_positive_negative_and_readback_evidence_passes(self):
        temporary, repo, plan = self.fixture()
        try:
            self.write_evidence(repo, self.valid_evidence())
            summary, errors = CONTROL.validate_review_completion_gate(repo, plan)
            self.assertEqual([], errors)
            self.assertTrue(summary["applicable"])
            self.assertTrue(summary["passed"])
            self.assertEqual(
                {
                    "finding-no-render-click-or-tracked-evidence",
                    "finding-web-identity-readback-missing",
                },
                {item["claim_id"] for item in summary["claims"]},
            )
        finally:
            temporary.cleanup()

    def test_milestone_without_completion_gate_is_not_blocked(self):
        temporary, repo, _ = self.fixture()
        try:
            plan = {
                "goal_id": "UNRELATED",
                "active_milestone_id": "M2",
                "milestones": [{"id": "M2", "status": "active"}],
            }
            summary, errors = CONTROL.validate_review_completion_gate(repo, plan)
            self.assertEqual([], errors)
            self.assertFalse(summary["applicable"])
            self.assertTrue(summary["passed"])
        finally:
            temporary.cleanup()

    def test_codex_cannot_mark_reviewer_finding_verified(self):
        temporary, repo, plan = self.fixture()
        try:
            evidence = self.valid_evidence()
            evidence["claims"][0]["disposition"] = "VERIFIED"
            self.write_evidence(repo, evidence)
            _, errors = CONTROL.validate_review_completion_gate(repo, plan)
            self.assertTrue(any("Codex may not declare VERIFIED" in error for error in errors), errors)
        finally:
            temporary.cleanup()

    def test_exact_candidate_evidence_accepts_matching_gate_and_readback(self):
        temporary, repo, plan = self.fixture()
        try:
            self.write_evidence(repo, self.valid_evidence())
            completion_summary, completion_errors = CONTROL.validate_review_completion_gate(
                repo, plan
            )
            self.assertEqual([], completion_errors)
            fingerprint = {
                "value": "a" * 64,
                "head": "b" * 40,
                "algorithm": "sha256-canonical-json-v3-branch-independent-review-bus-exclusions",
            }
            evidence = {
                "result": "pass",
                "claims": {"candidate_verified": True, "release_verified": False},
                "fingerprint_stable": True,
                "fingerprint_before": fingerprint,
                "fingerprint_after": fingerprint,
                "repository": {"head": fingerprint["head"]},
                "evidence_readback": True,
                "gates": [
                    {
                        "name": "review_completion_gate",
                        "passed": True,
                        "details": completion_summary,
                    }
                ],
            }
            (repo / "verification.json").write_text(json.dumps(evidence))
            self.assertEqual(
                evidence,
                CONTROL.load_verification_evidence(
                    repo, "verification.json", fingerprint, plan=plan
                ),
            )
        finally:
            temporary.cleanup()

    def test_exact_candidate_evidence_rejects_missing_gate_readback_and_head(self):
        temporary, repo, plan = self.fixture()
        try:
            fingerprint = {
                "value": "a" * 64,
                "head": "b" * 40,
                "algorithm": "sha256-canonical-json-v3-branch-independent-review-bus-exclusions",
            }
            path = repo / "verification.json"
            base = {
                "result": "pass",
                "claims": {"candidate_verified": True, "release_verified": False},
                "fingerprint_stable": True,
                "fingerprint_before": fingerprint,
                "fingerprint_after": fingerprint,
                "repository": {"head": fingerprint["head"]},
                "evidence_readback": True,
                "gates": [],
            }
            path.write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "review_completion_gate"):
                CONTROL.load_verification_evidence(
                    repo, "verification.json", fingerprint, plan=plan
                )
            base["gates"] = [{"name": "review_completion_gate", "passed": True}]
            base["evidence_readback"] = False
            path.write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "read-back"):
                CONTROL.load_verification_evidence(
                    repo, "verification.json", fingerprint, plan=plan
                )
            base["evidence_readback"] = True
            base["repository"]["head"] = "c" * 40
            path.write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "HEAD"):
                CONTROL.load_verification_evidence(
                    repo, "verification.json", fingerprint, plan=plan
                )
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
