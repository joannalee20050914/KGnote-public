from __future__ import annotations

import json
import tempfile
import unittest
import shutil
from pathlib import Path

from kgnote.learning import load_learning_unit_catalog


ROOT = Path(__file__).resolve().parents[1]


class LearningCatalogTests(unittest.TestCase):
    def test_three_units_load_with_structure_assist_and_three_or_more_activity_types(self) -> None:
        result = load_learning_unit_catalog(ROOT / "web/fixtures/learning-units.json")
        self.assertEqual(result.status, "ready")
        self.assertEqual(set(result.payload["bundles"]), {"os", "bitepacer", "pvz"})
        for bundle in result.payload["bundles"].values():
            self.assertGreaterEqual(len({item["activity_type"] for item in bundle["practice"]["items"]}), 3)
            self.assertEqual(len([node for node in bundle["structure"]["nodes"] if node["parent_id"] is None]), 1)
            self.assertGreaterEqual(len(bundle["soak"]["items"]), 1)
        os_bundle = result.payload["bundles"]["os"]
        self.assertEqual(os_bundle["reading_assist"]["glosses"][0]["required_depth"], "define")
        self.assertFalse(any(gloss["term"] == "DMA" for gloss in os_bundle["reading_assist"]["glosses"]))
        pvz_bundle = result.payload["bundles"]["pvz"]
        self.assertEqual(pvz_bundle["model"]["source"]["source_kind"], "synthetic_lesson")
        self.assertIn("original synthetic fixture", pvz_bundle["source_text"])
        self.assertEqual(pvz_bundle["reading_assist"]["prior_knowledge"], [])

    def test_traversal_missing_fixture_and_source_drift_fail_closed(self) -> None:
        original = json.loads((ROOT / "web/fixtures/learning-units.json").read_text())
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            invalid = {**original, "units": [{**original["units"][0], "map": "../secret.json"}]}
            (root / "catalog.json").write_text(json.dumps(invalid))
            self.assertEqual(load_learning_unit_catalog(root / "catalog.json").problem_code, "unit_fixture_unavailable")

    def test_structure_and_context_gloss_projection_failures_do_not_block_source_reader(self) -> None:
        original = json.loads((ROOT / "web/fixtures/learning-units.json").read_text())
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            entry = {**original["units"][0], "structure": "missing-structure.json", "reading_assist": "missing-assist.json"}
            for fixture in (entry["map"], entry["source"], entry["claim_reviews"], entry["practice"], entry["soak"]):
                shutil.copy2(ROOT / "web/fixtures" / fixture, root / fixture)
            (root / "catalog.json").write_text(json.dumps({"schema_version": original["schema_version"], "units": [entry]}))
            result = load_learning_unit_catalog(root / "catalog.json")
            self.assertEqual(result.status, "ready")
            bundle = result.payload["bundles"]["os"]
            self.assertTrue(bundle["source_text"].startswith("# "))
            self.assertEqual(bundle["reading_assist"]["glosses"], [])
            self.assertEqual(bundle["structure"]["provenance"]["basis"], "source_fallback")
            self.assertEqual({item["component"] for item in bundle["degradations"]}, {"learning_structure", "reading_assist"})

    def test_prior_knowledge_failure_does_not_remove_context_gloss(self) -> None:
        original = json.loads((ROOT / "web/fixtures/learning-units.json").read_text())
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); entry = original["units"][0]
            for fixture in (entry["map"], entry["source"], entry["claim_reviews"], entry["structure"], entry["practice"], entry["soak"]):
                shutil.copy2(ROOT / "web/fixtures" / fixture, root / fixture)
            assist = json.loads((ROOT / "web/fixtures" / entry["reading_assist"]).read_text()); assist["prior_knowledge"] = "corrupt-derived-value"
            (root / entry["reading_assist"]).write_text(json.dumps(assist)); (root / "catalog.json").write_text(json.dumps({"schema_version":original["schema_version"],"units":[entry]}))
            result = load_learning_unit_catalog(root / "catalog.json")
            self.assertEqual(result.status, "ready")
            bundle = result.payload["bundles"]["os"]
            self.assertEqual(bundle["reading_assist"]["glosses"][0]["term"], "PID")
            self.assertEqual(bundle["reading_assist"]["prior_knowledge"], [])
            self.assertEqual(bundle["degradations"], [{"component":"prior_knowledge","code":"unavailable"}])


if __name__ == "__main__":
    unittest.main()
