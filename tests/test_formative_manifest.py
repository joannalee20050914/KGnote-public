from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from kgnote.experiments import (
    FormativeManifestError,
    load_formative_manifest,
    validate_formative_manifest,
    validate_formative_run_record,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "experiments" / "manifests" / "h0-bitepacer-p4-backup-v1.yaml"
RECORD_PATH = ROOT / "experiments" / "templates" / "h0-bitepacer-run-record-v1.yaml"


class FormativeManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.record = yaml.safe_load(RECORD_PATH.read_text(encoding="utf-8"))

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        schema_root = ROOT / "schemas" / "formative-test-manifest" / "v1"
        for path in sorted(schema_root.glob("*.schema.json")):
            with self.subTest(schema=path.name):
                Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_manifest_and_planned_record_read_back_deterministically(self) -> None:
        first = load_formative_manifest(MANIFEST_PATH)
        second = load_formative_manifest(MANIFEST_PATH)
        self.assertEqual(first, second)
        self.assertEqual(first["hypothesis_id"], "H0")
        self.assertEqual(
            {item["condition_id"] for item in first["conditions"]},
            {"baseline_markdown", "kgnote_no_graph"},
        )
        self.assertEqual(first["pretest"]["eligible_ratings"], [0])
        validate_formative_run_record(self.record, first)

    def test_digest_range_condition_and_pretest_drift_fail_closed(self) -> None:
        cases = []
        changed = copy.deepcopy(self.manifest)
        changed["source"]["content_sha256"] = "0" * 64
        cases.append((changed, "source_digest_mismatch"))
        changed = copy.deepcopy(self.manifest)
        changed["source"]["selected_range"] = "L52-L1"
        cases.append((changed, "reversed_line_range"))
        changed = copy.deepcopy(self.manifest)
        changed["conditions"][1]["condition_id"] = "baseline_markdown"
        cases.append((changed, "missing_required_condition"))
        changed = copy.deepcopy(self.manifest)
        changed["pretest"]["rating_scale"] = list(reversed(changed["pretest"]["rating_scale"]))
        cases.append((changed, "invalid_pretest_scale"))
        for payload, code in cases:
            with self.subTest(code=code), self.assertRaises(FormativeManifestError) as raised:
                validate_formative_manifest(payload)
            self.assertEqual(raised.exception.code, code)

    def test_run_record_is_snapshot_bound_and_cannot_fake_eligibility_or_completion(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["source_sha256"] = "0" * 64
        with self.assertRaises(FormativeManifestError) as raised:
            validate_formative_run_record(changed, self.manifest)
        self.assertEqual(raised.exception.code, "run_manifest_mismatch")

        changed = copy.deepcopy(self.record)
        changed["status"] = "pretest_excluded"
        changed["pretest"] = {
            "recorded_at": "2026-09-19T12:00:00+08:00", "rating": 0,
            "raw_response": "完全陌生", "eligible": False,
        }
        with self.assertRaises(FormativeManifestError) as raised:
            validate_formative_run_record(changed, self.manifest)
        self.assertEqual(raised.exception.code, "pretest_eligibility_mismatch")

        changed = copy.deepcopy(self.record)
        changed["status"] = "completed"
        changed["completed_at"] = "2026-09-19T13:00:00+08:00"
        changed["decision"] = {"outcome": "continue", "rationale": "placeholder"}
        with self.assertRaises(FormativeManifestError) as raised:
            validate_formative_run_record(changed, self.manifest)
        self.assertEqual(raised.exception.code, "incomplete_completed_run")


if __name__ == "__main__":
    unittest.main()
