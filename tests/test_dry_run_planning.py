import copy
import hashlib
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from kgnote.normalization import NormalizationResult, normalize_candidate_result
from kgnote.planning import DRY_RUN_RULESET_VERSION, plan_dry_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_OUTPUT = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/output.json"
GOLDEN = PROJECT_ROOT / "tests/fixtures/planning/v1/golden.json"
PHASE0_VAULT = PROJECT_ROOT / "fixtures/phase0-obsidian"


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def source_record():
    return {
        "schema_version": "kgnote.v0.1",
        "id": "src_synthetic_causality_chat",
        "type": "source",
        "source_kind": "chatgpt_conversation",
        "title": "Synthetic causality learning conversation",
        "uri_or_path": "raw/synthetic-causality-chat.md",
        "content_sha256": "0" * 64,
        "captured_at": None,
        "registered_at": "2026-09-07T00:00:00+08:00",
    }


def flatten(records):
    return [record for collection in records.values() for record in collection]


class DryRunPlanningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidate = load_json(VALID_OUTPUT)
        cls.normalized = normalize_candidate_result(candidate)
        cls.records = cls.normalized.records

    def planned_snapshot(self):
        by_id = {record["id"]: copy.deepcopy(record) for record in flatten(self.records)}
        ids = self.normalized.ref_map

        # One CREATE: omit Causation.
        by_id.pop(ids["c_causation"])

        # One UPDATE: only add evidence provenance to Causal inference.
        by_id[ids["c_causal_inference"]]["evidence_ids"] = []

        # One CONFLICT: a non-allowlisted human-facing summary differs.
        by_id[ids["c_correlation"]]["summary"] = "Human-edited summary"

        # Review state must be preserved and should not itself create a change.
        by_id[ids["c_counterfactual"]]["status"] = "active"
        first_evidence = ids["ev_difference"]
        by_id[first_evidence]["review_status"] = "accepted"
        return [source_record(), *by_id.values()]

    def test_golden_plan_covers_all_non_reject_operations(self):
        plan = plan_dry_run(self.normalized, self.planned_snapshot())
        golden = load_json(GOLDEN)

        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.ruleset_version, DRY_RUN_RULESET_VERSION)
        self.assertIsNone(plan.problem)
        self.assertEqual(plan.items, golden["planned_items"])
        self.assertEqual(
            sorted({item["operation"] for item in plan.items}),
            ["CONFLICT", "CREATE", "UNCHANGED", "UPDATE"],
        )

    def test_golden_reject_is_stable(self):
        snapshot = self.planned_snapshot()
        snapshot = [
            record
            for record in snapshot
            if record["id"] != "src_synthetic_causality_chat"
        ]
        first = plan_dry_run(self.normalized, snapshot)
        second = plan_dry_run(self.normalized, list(reversed(snapshot)))
        golden = load_json(GOLDEN)

        self.assertEqual(first, second)
        self.assertEqual(first.status, "rejected")
        self.assertEqual(first.items, golden["rejected_items"])

    def test_snapshot_shape_and_record_contract_reject_safely(self):
        valid = source_record()
        cases = []
        cases.append((None, "snapshot_not_list"))
        cases.append((["private record body"], "record_not_object"))

        missing = copy.deepcopy(valid)
        missing.pop("title")
        cases.append(([missing], "missing_record_field"))

        extra = copy.deepcopy(valid)
        extra["private_body"] = "must not appear in error"
        cases.append(([extra], "unexpected_record_field"))

        schema = copy.deepcopy(valid)
        schema["schema_version"] = "kgnote.future"
        cases.append(([schema], "unsupported_schema_version"))

        wrong_type = copy.deepcopy(valid)
        wrong_type["type"] = "concept"
        cases.append(([wrong_type], "record_id_type_mismatch"))

        invalid_enum = copy.deepcopy(self.records["concepts"][0])
        invalid_enum["status"] = "understood"
        cases.append(([invalid_enum], "invalid_record_enum"))

        invalid_reference = copy.deepcopy(self.records["evidence"][0])
        invalid_reference["source_id"] = ["src_not_scalar"]
        cases.append(([invalid_reference], "invalid_reference_format"))

        non_json = copy.deepcopy(valid)
        non_json["title"] = {"not-json"}
        cases.append(([non_json], "record_not_json"))

        for snapshot, code in cases:
            with self.subTest(code=code):
                plan = plan_dry_run(self.normalized, snapshot)
                self.assertEqual(plan.status, "rejected")
                self.assertEqual(plan.problem.code, code)
                self.assertNotIn("must not appear in error", repr(plan))

    def test_duplicate_existing_ids_reject(self):
        source = source_record()
        plan = plan_dry_run(self.normalized, [source, copy.deepcopy(source)])
        self.assertEqual(plan.problem.code, "duplicate_existing_id")
        self.assertEqual(plan.problem.record_id, source["id"])

    def test_unresolved_projected_references_reject(self):
        missing_source = [
            record
            for record in self.planned_snapshot()
            if record["id"] != "src_synthetic_causality_chat"
        ]
        unresolved = plan_dry_run(self.normalized, missing_source)
        self.assertEqual(unresolved.problem.code, "unresolved_projected_reference")
        self.assertEqual(unresolved.problem.reference, "src_synthetic_causality_chat")

    def test_removal_and_non_allowlisted_changes_are_conflicts(self):
        snapshot = [source_record(), *flatten(copy.deepcopy(self.records))]
        concept_id = self.normalized.ref_map["c_correlation"]
        concept = next(record for record in snapshot if record["id"] == concept_id)
        concept["evidence_ids"].append("evidence_existing_only")
        snapshot.append(
            {
                **copy.deepcopy(self.records["evidence"][0]),
                "id": "evidence_existing_only",
            }
        )
        plan = plan_dry_run(self.normalized, snapshot)
        item = next(item for item in plan.items if item["record_id"] == concept_id)
        self.assertEqual(item["operation"], "CONFLICT")

    def test_review_state_is_preserved(self):
        plan = plan_dry_run(self.normalized, self.planned_snapshot())
        ids = self.normalized.ref_map
        concept = next(item for item in plan.items if item["record_id"] == ids["c_counterfactual"])
        evidence = next(item for item in plan.items if item["record_id"] == ids["ev_difference"])
        self.assertEqual(concept["operation"], "UNCHANGED")
        self.assertEqual(evidence["operation"], "UNCHANGED")

    def test_repeated_and_reordered_snapshots_are_equal(self):
        snapshot = self.planned_snapshot()
        first = plan_dry_run(self.normalized, snapshot)
        self.assertEqual(first, plan_dry_run(self.normalized, copy.deepcopy(snapshot)))
        self.assertEqual(first, plan_dry_run(self.normalized, list(reversed(snapshot))))
        for item in first.items:
            self.assertEqual(
                [change["field"] for change in item["changes"]],
                sorted(change["field"] for change in item["changes"]),
            )

    def test_inputs_result_and_vault_are_unchanged_without_network(self):
        snapshot = self.planned_snapshot()
        before_snapshot = copy.deepcopy(snapshot)
        before_vault = tree_digest(PHASE0_VAULT)
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            plan = plan_dry_run(self.normalized, snapshot)
        returned = plan.items
        returned.clear()

        self.assertEqual(snapshot, before_snapshot)
        self.assertTrue(plan.items)
        self.assertEqual(tree_digest(PHASE0_VAULT), before_vault)
        with self.assertRaises(FrozenInstanceError):
            plan.status = "rejected"

    def test_rejected_normalization_cannot_be_planned(self):
        rejected = NormalizationResult(status="rejected")
        plan = plan_dry_run(rejected, [])
        self.assertEqual(plan.problem.code, "normalization_not_accepted")


if __name__ == "__main__":
    unittest.main()
