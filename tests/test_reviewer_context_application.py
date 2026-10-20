from __future__ import annotations

import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kgnote.review import load_reviewer_context


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures/phase0-obsidian"


def tree_digest(root):
    return tuple((path.relative_to(root).as_posix(), path.read_bytes()) for path in sorted(Path(root).rglob("*")) if path.is_file())


class ReviewerContextApplicationTest(unittest.TestCase):
    def test_explicit_store_to_correlation_context_read_back(self):
        result = load_reviewer_context(STORE, "concept_correlation")
        self.assertEqual(result.status, "ready")
        response = result.response
        self.assertEqual(response["schema_version"], "kgnote.reviewer-context-application.v1")
        self.assertEqual(response["context"]["focus"]["label"], "Correlation")
        self.assertEqual(len(response["context"]["neighborhood"]["nodes"]), 3)
        self.assertEqual(len(response["context"]["neighborhood"]["links"]), 3)
        self.assertEqual(len(response["context"]["evidence"]), 3)
        self.assertEqual(len(response["context"]["sources"]), 1)

    def test_maps_store_and_context_failures_without_private_echo(self):
        missing = Path(tempfile.gettempdir()) / "private-review-store-does-not-exist"
        store_result = load_reviewer_context(missing, "concept_correlation")
        self.assertEqual(store_result.problem.component, "graph")
        self.assertNotIn(str(missing), json.dumps(store_result.response))
        concept_result = load_reviewer_context(STORE, "private concept body")
        self.assertEqual(concept_result.problem.component, "context")
        self.assertEqual(concept_result.problem.code, "unknown_concept")
        self.assertNotIn("private concept body", repr(concept_result))
        self.assertEqual(load_reviewer_context(STORE, "").problem.code, "invalid_concept_id")

    def test_boundary_is_deterministic_and_read_only_without_external_io(self):
        before = tree_digest(STORE)
        with mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             mock.patch("subprocess.run", side_effect=AssertionError("process forbidden")):
            first = load_reviewer_context(STORE, "concept_correlation")
            second = load_reviewer_context(STORE, "concept_correlation")
        self.assertEqual(first, second)
        self.assertEqual(tree_digest(STORE), before)


if __name__ == "__main__":
    unittest.main()
