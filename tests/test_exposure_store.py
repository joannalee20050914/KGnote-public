from __future__ import annotations

import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from kgnote.review import list_exposures, record_exposure


def event(kind: str = "presented") -> dict:
    return {
        "schema_version":"kgnote.exposure-save-request.v1",
        "event_id":"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "exposure_session_id":"soak_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "learning_unit_id":"guided_map_os_safety_efficiency_review",
        "item_id":"soak_os_aging_starvation",
        "concept_id":"concept_aging",
        "kind":kind,
        "occurred_at":"2026-09-20T02:30:00Z",
        "source_refs":["src_os_overview_review"],
    }


class ExposureStoreTests(unittest.TestCase):
    def test_sc02_append_only_exposure_is_not_attempt_or_retrieval_result(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); request=event()
            self.assertEqual(record_exposure(root,request).status,"recorded")
            self.assertEqual(record_exposure(root,request).status,"unchanged")
            changed=copy.deepcopy(request); changed["kind"]="skipped"
            self.assertEqual(record_exposure(root,changed).status,"conflict")
            stored=list_exposures(root,request["learning_unit_id"]).payload["events"]
            self.assertEqual([item["kind"] for item in stored],["presented"])
            self.assertFalse((root/"attempts").exists())
            for forbidden in ("outcome","correct","incorrect","score","attempt_id"):
                self.assertNotIn(forbidden,stored[0])

    def test_natural_exposure_kinds_remain_typed_without_correctness(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for index,kind in enumerate(("encountered","recognized","applied")):
                request=event(kind); request["event_id"]=f"exposure_{index:032x}"
                self.assertEqual(record_exposure(root,request).status,"recorded")
            self.assertEqual({item["kind"] for item in list_exposures(root,event()["learning_unit_id"]).payload["events"]},{"encountered","recognized","applied"})
            self.assertFalse((root/"due-items").exists())

    def test_schema_and_corrupt_store_fail_closed(self) -> None:
        schema=json.loads((Path(__file__).parents[1]/"schemas/exposure/v1/save-request.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        self.assertEqual(list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(event())),[])
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); directory=root/"exposures"; directory.mkdir(); (directory/"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json").write_text("bad")
            self.assertEqual(list_exposures(root,event()["learning_unit_id"]).problem_code,"exposure_read_failed")

    def test_concurrent_same_identity_is_idempotent_and_cannot_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            same=[event() for _ in range(12)]
            with ThreadPoolExecutor(max_workers=12) as pool:
                statuses=list(pool.map(lambda value: record_exposure(root,value).status,same))
            self.assertEqual(statuses.count("recorded"),1)
            self.assertEqual(statuses.count("unchanged"),11)
            conflict=copy.deepcopy(event());conflict["kind"]="skipped"
            self.assertEqual(record_exposure(root,conflict).status,"conflict")
            self.assertEqual(list_exposures(root,event()["learning_unit_id"]).payload["events"][0]["kind"],"presented")


if __name__ == "__main__": unittest.main()
