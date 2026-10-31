from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    ROOT
    / "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json"
)
PREDECESSOR_SPEC_PATH = (
    ROOT
    / "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json"
)
SCHEMA_PATH = (
    ROOT / "schemas/codex-app-engineering-goal/v1/goal-spec.schema.json"
)
PACKAGE_PATH = (
    ROOT
    / "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261031.md"
)
PLAN_PATH = ROOT / "PLAN.md"
STATUS_PATH = ROOT / "CODEX_STATUS.md"
EXPECTED_DIGEST = "8f3036ec6429e2f8f1e546aea3a8b3bf1c0cb1459e742991a4228612836958cd"
PREDECESSOR_DIGEST = "f78a49397822bf17a89f7477be2efe840c0dddfa58cf767153cf31281bdcdce4"
AUTHORITY_MARKER = "<!-- kgnote-codex-app-engineering-goal-authority:v1 -->"
OWNER_APPROVAL_COMMENT_ID = 6537070839
OWNER_APPROVAL_BODY_SHA256 = (
    "d01c5fe57c73f99750ff2ec145f4d495897b4062c4e20a97950b4b00d8507e92"
)
OWNER_APPROVAL_COMMAND_SHA256 = (
    "6bc2d545b3c116c17d66de592780cd685f0c004306c20dd109ec74b95c4931fc"
)


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def embedded_json(path: Path, label: str) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- BEGIN {re.escape(label)} -->\s*```json\s*(\{{.*?\}})\s*```"
        rf"\s*<!-- END {re.escape(label)} -->",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing embedded JSON block {label} in {path}")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise AssertionError(f"embedded JSON block {label} must be an object")
    return value


class Issue47EngineeringGoalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_identity_and_canonical_digest(self) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(self.spec)
        self.assertEqual(
            "CODEX_APP_EXECUTION_GOAL", self.spec["identity_kind"]
        )
        self.assertEqual(
            "GITHUB_OWNER_EXECUTION_APPROVAL_REQUIRED",
            self.spec["authority_kind"],
        )
        self.assertFalse(self.spec["product_goal_authorized"])
        self.assertEqual(EXPECTED_DIGEST, canonical_sha256(self.spec))

    def test_resource_totals_carry_known_preapproval_contexts(self) -> None:
        providers = self.spec["resource_policy"]["providers"]
        self.assertEqual(1, self.spec["resource_policy"]["max_model_concurrency"])
        self.assertEqual(18, providers["codex"]["max_total_launches"])
        self.assertEqual(7, providers["codex"]["known_preapproval_launches"])
        self.assertEqual(11, providers["codex"]["remaining_after_known_preapproval"])
        self.assertEqual(12, providers["claude"]["max_total_launches"])
        self.assertEqual(0, providers["claude"]["known_preapproval_launches"])
        self.assertEqual(12, providers["claude"]["remaining_after_known_preapproval"])
        for provider in providers.values():
            self.assertTrue(provider["subscription_only"])
            self.assertFalse(provider["paid_api_fallback"])
            self.assertEqual(
                provider["max_total_launches"]
                - provider["known_preapproval_launches"],
                provider["remaining_after_known_preapproval"],
            )

    def test_predecessor_stays_immutable_and_weekend_windows_are_narrow(self) -> None:
        predecessor = json.loads(PREDECESSOR_SPEC_PATH.read_text(encoding="utf-8"))
        self.assertEqual(PREDECESSOR_DIGEST, canonical_sha256(predecessor))
        self.assertEqual(predecessor["goal_id"], self.spec["goal_id"])
        self.assertEqual(predecessor["work_items"], self.spec["work_items"])
        self.assertEqual(
            predecessor["legacy_o2_protection"], self.spec["legacy_o2_protection"]
        )
        self.assertEqual(
            [
                {
                    "date": "2026-10-31",
                    "start": "09:15",
                    "end": "18:00",
                    "scope": "ISSUE47_INFRA_ENGINEERING_ONLY",
                },
                {
                    "date": "2026-11-01",
                    "start": "09:00",
                    "end": "18:00",
                    "scope": "ISSUE47_INFRA_ENGINEERING_ONLY",
                },
            ],
            self.spec["work_period"]["exception_work_windows"],
        )
        self.assertFalse(self.spec["product_goal_authorized"])
        self.assertIn(
            "use_weekend_exception_for_product_goal_canary_or_standing_go_live",
            self.spec["forbidden_operations"],
        )

    def test_work_item_dependencies_are_ordered_and_unique(self) -> None:
        seen: set[str] = set()
        for work_item in self.spec["work_items"]:
            work_item_id = work_item["work_item_id"]
            self.assertNotIn(work_item_id, seen)
            self.assertLessEqual(set(work_item["dependencies"]), seen)
            seen.add(work_item_id)
        self.assertEqual(
            {
                "WI-0-SEAL-READINESS",
                "WI-1-INDEPENDENT-REVIEW-AND-PR",
                "WI-2-ONESHOT-DISPATCH",
                "WI-3-ZERO-MODEL-E2E",
                "WI-4-TRUSTED-DEPLOYMENT",
                "WI-5-LIVE-CANARY",
                "WI-6-SCHEDULE-RESUME-ROLLBACK",
                "WI-7-OWNER-ACCEPTANCE",
            },
            seen,
        )

    def test_o2_and_product_goal_boundaries_remain_explicit(self) -> None:
        protection = self.spec["legacy_o2_protection"]
        self.assertEqual("ACTIVE", protection["lifecycle"])
        self.assertEqual(9, protection["ledger_cursor"])
        self.assertEqual("4/5", protection["codex_accounting"])
        self.assertEqual("DISABLED_UNLOADED", protection["formal_runner"])
        self.assertEqual(
            "IMMUTABLE_READ_ONLY",
            protection["authority_state_ledger_checkpoint_quota_archive"],
        )
        coexistence = self.spec["product_goal_coexistence"]
        self.assertEqual(
            "BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE", coexistence["policy"]
        )
        self.assertIn(
            "不批准任何 Product Goal",
            coexistence["effect_of_engineering_goal_approval"],
        )

    def test_authorization_template_matches_the_immutable_spec(self) -> None:
        text = PACKAGE_PATH.read_text(encoding="utf-8")
        self.assertEqual(1, text.count(AUTHORITY_MARKER))
        match = re.search(
            re.escape(AUTHORITY_MARKER) + r"\s*```json\s*(\{.*?\})\s*```",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        command = json.loads(match.group(1))
        self.assertEqual(self.spec["goal_id"], command["goal_id"])
        self.assertEqual(self.spec["goal_version"], command["goal_version"])
        self.assertEqual(EXPECTED_DIGEST, command["goal_spec_sha256"])
        self.assertEqual(self.spec["allowed_operations"], command["permissions"])
        self.assertFalse(command["product_goal_authorized"])
        self.assertFalse(command["standing_b_scheme_go_live_authorized"])
        self.assertEqual(
            self.spec["product_goal_coexistence"]["policy"],
            command["product_goal_coexistence"],
        )

    def test_owner_approval_receipt_advances_only_the_engineering_goal(self) -> None:
        plan = embedded_json(PLAN_PATH, "CODEX PLAN JSON")
        status = embedded_json(STATUS_PATH, "CODEX STATUS JSON")
        self.assertEqual(
            "EXACT_GITHUB_OWNER_APPROVED_CODEX_APP_EXECUTION_GOAL",
            plan["authority_kind"],
        )
        self.assertEqual(
            "EG-1-INDEPENDENT-REVIEW-AND-PR", plan["active_milestone_id"]
        )
        milestones = {item["id"]: item for item in plan["milestones"]}
        self.assertEqual("complete", milestones["EG-0-OWNER-AUTHORITY"]["status"])
        self.assertEqual("complete", milestones["EG-0-OWNER-AUTHORITY"]["human_gate"])
        self.assertEqual("active", milestones["EG-1-INDEPENDENT-REVIEW-AND-PR"]["status"])

        receipt = plan["goal_spec"]["authority_receipt"]
        self.assertEqual(OWNER_APPROVAL_COMMENT_ID, receipt["comment_id"])
        self.assertEqual(OWNER_APPROVAL_BODY_SHA256, receipt["body_sha256"])
        self.assertEqual(
            OWNER_APPROVAL_COMMAND_SHA256, receipt["command_canonical_sha256"]
        )
        self.assertEqual(
            "EXACT_GITHUB_OWNER_APPROVED", plan["goal_spec"]["authority_status"]
        )
        self.assertFalse(plan["product_goal_authorized"])

        authority = status["goal_spec"]["authority_comment"]
        self.assertEqual(OWNER_APPROVAL_COMMENT_ID, authority["comment_id"])
        self.assertEqual(OWNER_APPROVAL_BODY_SHA256, authority["body_sha256"])
        self.assertTrue(authority["authority_marker_present"])
        self.assertTrue(authority["command_exact_semantic_match"])
        self.assertFalse(status["product_goal_authorized"])
        gates = {item["id"]: item["status"] for item in status["external_or_human_gates"]}
        self.assertEqual(
            "complete_exact_owner_approval_comment_6537070839",
            gates["ISSUE47-ENGINEERING-GOAL-OWNER-APPROVAL"],
        )
        self.assertEqual(
            "not_started", gates["ISSUE47-EXACT-PRODUCT-GOAL-CANARY-APPROVAL"]
        )
        self.assertEqual(
            "not_started", gates["ISSUE47-FINAL-OWNER-ACCEPTANCE-AND-GO-LIVE"]
        )


if __name__ == "__main__":
    unittest.main()
