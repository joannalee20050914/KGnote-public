from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest import mock

from kgnote.contracts.reader import validate_reader_application_result
from kgnote.reader import READER_RESPONSE_HEADERS, ReaderApplicationProblem, load_reader
from kgnote.storage import read_canonical_store
from kgnote.visualization import project_graph_read_model


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "reader" / "v1"
STORE = FIXTURES / "store"
RAW = STORE / "raw" / "bitepacer-mini-network-lesson.md"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def tree_bytes(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


_DEFAULT_LOCATOR = object()


def query_for(
    root: Path,
    *,
    source_id: str = "src_bitepacer_mini_network_lesson",
    locator=_DEFAULT_LOCATOR,
) -> dict:
    snapshot = read_canonical_store(root)
    if snapshot.status != "loaded":
        raise AssertionError(snapshot.problem)
    projection = project_graph_read_model(snapshot.records)
    if projection.status != "projected":
        raise AssertionError(projection.problem)
    return {
        "schema_version": "kgnote.reader-query.v1",
        "snapshot_sha256": projection.model["snapshot_sha256"],
        "source_id": source_id,
        "locator": (
            {"kind": "line_range", "value": "L3-L18"}
            if locator is _DEFAULT_LOCATOR
            else locator
        ),
    }


class ReaderApplicationTests(unittest.TestCase):
    def test_bitepacer_exact_text_focus_and_cross_view_refs_match_golden(self) -> None:
        result = load_reader(STORE, load("bitepacer-query.json"))
        self.assertEqual(result.status, "ready")
        self.assertIsNone(result.problem)
        self.assertEqual(result.response, load("bitepacer-golden.json"))
        document = result.response["document"]
        self.assertEqual(document["content"].encode("utf-8"), RAW.read_bytes())
        self.assertEqual(
            hashlib.sha256(document["content"].encode("utf-8")).hexdigest(),
            document["source"]["content_sha256"],
        )
        self.assertEqual(document["focus"]["evidence_ids"], [
            "evidence_b1861d12c500f976ca0364f6ec0ac869851ab741a5cc2110cd5714c39d4f3bed"
        ])
        self.assertEqual(document["focus"]["concept_ids"], [
            "concept_d18b2812af2ceef6d4d683eb766686b01b608336e89cc608b30c687218d858cf"
        ])
        self.assertEqual(document["focus"]["edge_ids"], [
            "edge_80042c4f448d92b2d8311f064b6189e7259615ff1c0babd38bb817adcf561c4a"
        ])
        self.assertEqual(result.response["response_headers"], READER_RESPONSE_HEADERS)
        snapshot = read_canonical_store(STORE)
        graph = project_graph_read_model(snapshot.records).model
        self.assertEqual(
            document["source"]["label"],
            next(item["label"] for item in graph["sources"] if item["id"] == document["source"]["id"]),
        )
        validate_reader_application_result(result.response)

    def test_whole_source_is_ready_and_lists_all_line_annotations(self) -> None:
        query = query_for(STORE, locator=None)
        result = load_reader(STORE, query)
        self.assertEqual(result.status, "ready")
        self.assertIsNone(result.response["document"]["focus"])
        self.assertEqual(
            [item["locator"]["value"] for item in result.response["document"]["annotations"]],
            ["L51-L66", "L3-L18"],
        )

    def test_stale_unknown_malformed_and_out_of_range_queries_fail_closed(self) -> None:
        cases = []
        query = load("bitepacer-query.json")
        query["snapshot_sha256"] = "0" * 64
        cases.append((query, "stale_graph_snapshot"))
        query = load("bitepacer-query.json")
        query["source_id"] = "src_missing"
        cases.append((query, "source_not_registered"))
        query = load("bitepacer-query.json")
        query["locator"]["value"] = "L1-L999"
        cases.append((query, "locator_out_of_range"))
        query = load("bitepacer-query.json")
        query["private_path"] = "local-source-withheld"
        cases.append((query, "invalid_reader_query"))

        for query, code in cases:
            with self.subTest(code=code):
                result = load_reader(STORE, query)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertEqual(result.response["response_headers"], READER_RESPONSE_HEADERS)
                validate_reader_application_result(result.response)
                serialized = json.dumps(result.response)
                self.assertNotIn("do-not-echo", serialized)
                self.assertNotIn(str(STORE), serialized)

    def test_registered_path_traversal_absolute_path_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for name, replacement in (
                ("traversal", "../../private.md"),
                ("absolute", "/tmp/private.md"),
            ):
                with self.subTest(name=name):
                    copied = Path(directory) / name
                    shutil.copytree(STORE, copied)
                    source_note = next((copied / "sources").glob("*.md"))
                    source_note.write_text(
                        source_note.read_text(encoding="utf-8").replace(
                            "raw/bitepacer-mini-network-lesson.md", replacement
                        ),
                        encoding="utf-8",
                    )
                    result = load_reader(copied, query_for(copied))
                    self.assertEqual(result.status, "rejected")
                    self.assertEqual(result.problem.code, "unsafe_registered_source_path")
                    self.assertNotIn(replacement, json.dumps(result.response))

            copied = Path(directory) / "symlink"
            shutil.copytree(STORE, copied)
            outside = Path(directory) / "outside.md"
            outside.write_text("PRIVATE_SIBLING_MARKER", encoding="utf-8")
            raw = copied / "raw" / "bitepacer-mini-network-lesson.md"
            raw.unlink()
            raw.symlink_to(outside)
            result = load_reader(copied, query_for(copied))
            self.assertEqual(result.status, "rejected")
            self.assertEqual(result.problem.code, "unsafe_registered_source_path")
            self.assertNotIn("PRIVATE_SIBLING_MARKER", json.dumps(result.response))

    def test_hash_mismatch_and_invalid_utf8_fail_without_content_echo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "hash"
            shutil.copytree(STORE, copied)
            raw = copied / "raw" / "bitepacer-mini-network-lesson.md"
            raw.write_bytes(raw.read_bytes() + b"PRIVATE_CHANGED_MARKER")
            result = load_reader(copied, query_for(copied))
            self.assertEqual(result.problem.code, "source_content_digest_mismatch")
            self.assertNotIn("PRIVATE_CHANGED_MARKER", json.dumps(result.response))

            copied = Path(directory) / "utf8"
            shutil.copytree(STORE, copied)
            raw = copied / "raw" / "bitepacer-mini-network-lesson.md"
            private_bytes = b"PRIVATE_PREFIX\xffPRIVATE_SUFFIX"
            raw.write_bytes(private_bytes)
            source_note = next((copied / "sources").glob("*.md"))
            source_note.write_text(
                source_note.read_text(encoding="utf-8").replace(
                    "bbef6549c2381ee729c355b69151777bbdbda459ca16079055316f52318792db",
                    hashlib.sha256(private_bytes).hexdigest(),
                ),
                encoding="utf-8",
            )
            result = load_reader(copied, query_for(copied))
            self.assertEqual(result.problem.code, "source_invalid_utf8")
            self.assertNotIn("PRIVATE", json.dumps(result.response))

    def test_unreviewed_evidence_is_not_promoted_to_reader_annotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "unreviewed"
            shutil.copytree(STORE, copied)
            evidence = copied / "evidence" / "evidence_b1861d12c500f976ca0364f6ec0ac869851ab741a5cc2110cd5714c39d4f3bed.md"
            evidence.write_text(
                evidence.read_text(encoding="utf-8").replace(
                    "review_status: accepted", "review_status: unreviewed"
                ),
                encoding="utf-8",
            )
            result = load_reader(copied, query_for(copied))
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.response["document"]["annotations"], [])
        self.assertEqual(result.response["document"]["focus"]["evidence_ids"], [])
        self.assertEqual(result.response["document"]["focus"]["concept_ids"], [])
        self.assertEqual(result.response["document"]["focus"]["edge_ids"], [])

    def test_malformed_registered_evidence_locator_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "bad-locator"
            shutil.copytree(STORE, copied)
            evidence = copied / "evidence" / "evidence_b1861d12c500f976ca0364f6ec0ac869851ab741a5cc2110cd5714c39d4f3bed.md"
            evidence.write_text(
                evidence.read_text(encoding="utf-8").replace("value: L3-L18", "value: L3-L999"),
                encoding="utf-8",
            )
            result = load_reader(copied, query_for(copied))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.code, "invalid_registered_evidence_locator")

    def test_boundary_is_read_only_without_network_write_process_or_clock(self) -> None:
        before = tree_bytes(STORE)
        with (
            mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")),
            mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")),
            mock.patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")),
            mock.patch("subprocess.run", side_effect=AssertionError("process forbidden")),
            mock.patch("time.time", side_effect=AssertionError("clock forbidden")),
        ):
            result = load_reader(STORE, load("bitepacer-query.json"))
        self.assertEqual(result.status, "ready")
        self.assertEqual(before, tree_bytes(STORE))

    def test_result_is_deterministic_frozen_and_copy_safe(self) -> None:
        query = load("bitepacer-query.json")
        first = load_reader(STORE, query)
        second = load_reader(STORE, copy.deepcopy(query))
        self.assertEqual(first, second)
        changed = first.response
        changed["document"]["content"] = "changed"
        self.assertEqual(first.response, load("bitepacer-golden.json"))
        with self.assertRaises(FrozenInstanceError):
            first.status = "rejected"
        problem = ReaderApplicationProblem("query", "example")
        with self.assertRaises(FrozenInstanceError):
            problem.code = "changed"

    def test_missing_or_invalid_store_root_is_safe(self) -> None:
        missing = Path(tempfile.gettempdir()) / "private-reader-store-that-does-not-exist"
        result = load_reader(missing, load("bitepacer-query.json"))
        self.assertEqual(result.status, "rejected")
        self.assertNotIn(str(missing), json.dumps(result.response))
        self.assertEqual(load_reader(None, load("bitepacer-query.json")).problem.code, "invalid_store_root")


if __name__ == "__main__":
    unittest.main()
