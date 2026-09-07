import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

import kgnote.storage.canonical_store as store_module
from kgnote.normalization import NormalizationResult, normalize_candidate_result
from kgnote.planning import DryRunPlan, plan_dry_run
from kgnote.storage import apply_approved_plan, plan_digest, read_canonical_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_OUTPUT = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/output.json"
GOLDEN = PROJECT_ROOT / "tests/fixtures/storage/v1/golden.json"
PHASE0_VAULT = PROJECT_ROOT / "fixtures/phase0-obsidian"
DIRECTORIES = ("sources", "concepts", "evidence", "learning-events", "edges")
TYPE_DIRECTORIES = {
    "source": "sources",
    "concept": "concepts",
    "evidence": "evidence",
    "learning_event": "learning-events",
    "edge": "edges",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def tree_digest(root, *, canonical_only=False):
    digest = hashlib.sha256()
    roots = [root / name for name in DIRECTORIES] if canonical_only else [root]
    for scan_root in roots:
        for path in sorted(item for item in scan_root.rglob("*") if item.is_file()):
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


def markdown(record, body):
    front = yaml.safe_dump(
        record,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=4096,
    )
    return f"---\n{front}---\n{body}".encode()


class CanonicalStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normalized = normalize_candidate_result(load_json(VALID_OUTPUT))
        ids = cls.normalized.ref_map
        cls.update_id = ids["c_causal_inference"]
        cls.update_body = "\n# Human Causal Inference Note\n\nKeep this body byte-for-byte.\n"

    def make_store(self, root):
        root = Path(root)
        for directory in DIRECTORIES:
            (root / directory).mkdir(parents=True)
        source = source_record()
        concept = next(
            copy.deepcopy(record)
            for record in self.normalized.records["concepts"]
            if record["id"] == self.update_id
        )
        concept["evidence_ids"] = []
        concept["status"] = "active"
        records_and_bodies = (
            (source, "\n# Immutable synthetic Source\n"),
            (concept, self.update_body),
        )
        for record, body in records_and_bodies:
            path = root / TYPE_DIRECTORIES[record["type"]] / f"{record['id']}.md"
            path.write_bytes(markdown(record, body))
        return root

    def read_and_plan(self, root):
        snapshot = read_canonical_store(root)
        self.assertEqual(snapshot.status, "loaded")
        plan = plan_dry_run(self.normalized, snapshot.records)
        self.assertEqual(plan.status, "planned")
        return snapshot, plan

    def test_golden_read_plan_apply_read_back_and_second_zero_write(self):
        golden = load_json(GOLDEN)
        phase0_before = tree_digest(PHASE0_VAULT)
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            digest = plan_digest(plan)
            self.assertEqual(digest, golden["plan_digest"])

            result = apply_approved_plan(root, snapshot, plan, digest)
            self.assertEqual(result.status, "applied")
            self.assertEqual(result.write_count, golden["first_apply"]["write_count"])
            self.assertEqual(list(result.created_paths), golden["first_apply"]["created_paths"])
            self.assertEqual(list(result.updated_paths), golden["first_apply"]["updated_paths"])
            self.assertEqual(list(result.backup_paths), golden["first_apply"]["backup_paths"])
            updated_document = next(
                document
                for document in result.audit_snapshot.documents
                if document.record_id == self.update_id
            )
            self.assertEqual(updated_document.body, self.update_body)
            updated_record = next(
                record for record in result.audit_snapshot.records if record["id"] == self.update_id
            )
            self.assertEqual(updated_record["status"], "active")

            second_plan = plan_dry_run(self.normalized, result.audit_snapshot.records)
            self.assertEqual({item["operation"] for item in second_plan.items}, {"UNCHANGED"})
            second = apply_approved_plan(
                root,
                result.audit_snapshot,
                second_plan,
                plan_digest(second_plan),
            )
            self.assertEqual(second.status, "applied")
            self.assertEqual(second.write_count, 0)
            self.assertEqual(tree_digest(PHASE0_VAULT), phase0_before)

    def test_approval_and_blocking_plan_fail_before_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            before = tree_digest(root)
            for approval, code in ((None, "approval_required"), ("0" * 64, "approval_digest_mismatch")):
                with self.subTest(code=code):
                    result = apply_approved_plan(root, snapshot, plan, approval)
                    self.assertEqual(result.problem.code, code)
                    self.assertEqual(tree_digest(root), before)

            conflicting_records = snapshot.records
            concept = next(record for record in conflicting_records if record["id"] == self.update_id)
            concept["summary"] = "Human conflict"
            conflict = plan_dry_run(self.normalized, conflicting_records)
            result = apply_approved_plan(root, snapshot, conflict, plan_digest(conflict))
            self.assertEqual(result.problem.code, "plan_contains_blocking_operation")
            self.assertEqual(tree_digest(root), before)

            rejected = NormalizationResult(status="rejected")
            rejected_plan = plan_dry_run(rejected, [])
            result = apply_approved_plan(root, snapshot, rejected_plan, plan_digest(rejected_plan))
            self.assertEqual(result.problem.code, "plan_not_applicable")
            self.assertEqual(tree_digest(root), before)

    def test_stale_precondition_and_existing_create_target_abort(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            update_path = root / "concepts" / f"{self.update_id}.md"
            update_path.write_bytes(update_path.read_bytes() + b"external edit\n")
            after_external_edit = tree_digest(root)
            result = apply_approved_plan(root, snapshot, plan, plan_digest(plan))
            self.assertEqual(result.problem.code, "stale_precondition")
            self.assertEqual(tree_digest(root), after_external_edit)

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            create = next(item for item in plan.items if item["operation"] == "CREATE")
            target = root / TYPE_DIRECTORIES[create["record_type"]] / f"{create['record_id']}.md"
            target.write_text("appeared after planning", encoding="utf-8")
            after_external_create = tree_digest(root)
            result = apply_approved_plan(root, snapshot, plan, plan_digest(plan))
            self.assertEqual(result.problem.code, "create_target_exists")
            self.assertEqual(tree_digest(root), after_external_create)

    def test_reader_rejects_malformed_unresolved_and_unsafe_stores(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            path = root / "sources/src_synthetic_causality_chat.md"
            path.write_text("not front matter", encoding="utf-8")
            self.assertEqual(read_canonical_store(root).problem.code, "missing_front_matter")

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            path = root / "sources/src_synthetic_causality_chat.md"
            path.write_text("---\ninvalid: [yaml\n---\nbody", encoding="utf-8")
            self.assertEqual(read_canonical_store(root).problem.code, "malformed_yaml")

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            path = root / "concepts" / f"{self.update_id}.md"
            record = next(record for record in read_canonical_store(root).records if record["id"] == self.update_id)
            record["evidence_ids"] = ["evidence_missing"]
            path.write_bytes(markdown(record, self.update_body))
            self.assertEqual(
                read_canonical_store(root).problem.code,
                "snapshot_unresolved_projected_reference",
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            target = root / "outside.md"
            target.write_text("outside", encoding="utf-8")
            (root / "edges" / "edge_symlink.md").symlink_to(target)
            self.assertEqual(read_canonical_store(root).problem.code, "store_symlink_not_allowed")

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            path = root / "concepts" / f"{self.update_id}.md"
            record = next(record for record in read_canonical_store(root).records if record["id"] == self.update_id)
            record["id"] = "concept_../../escape"
            path.write_bytes(markdown(record, self.update_body))
            self.assertEqual(read_canonical_store(root).problem.code, "filename_id_mismatch")

    def test_apply_rejects_forged_plan_and_directory_symlink_swaps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, _ = self.read_and_plan(root)
            forged = DryRunPlan(
                status="planned",
                _items_json=json.dumps([{"operation": "CREATE"}]),
            )
            result = apply_approved_plan(root, snapshot, forged, plan_digest(forged))
            self.assertEqual(result.problem.code, "invalid_plan_item")

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            concepts = root / "concepts"
            moved = root / "concepts-original"
            concepts.rename(moved)
            concepts.symlink_to(moved, target_is_directory=True)
            result = apply_approved_plan(root, snapshot, plan, plan_digest(plan))
            self.assertEqual(result.problem.code, "unsafe_canonical_directory")

        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            outside = root / "outside-backups"
            outside.mkdir()
            (root / ".kgnote-backups").symlink_to(outside, target_is_directory=True)
            result = apply_approved_plan(root, snapshot, plan, plan_digest(plan))
            self.assertEqual(result.problem.code, "unsafe_backup_directory")

    def test_mid_write_failure_rolls_back_canonical_files_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            before = tree_digest(root, canonical_only=True)

            def fail_update(path, content):
                raise OSError("simulated write failure")

            result = apply_approved_plan(
                root,
                snapshot,
                plan,
                plan_digest(plan),
                atomic_writer=fail_update,
            )
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.problem.code, "write_failed_recovered")
            self.assertTrue(result.recovered)
            self.assertEqual(tree_digest(root, canonical_only=True), before)
            self.assertTrue(result.backup_paths)

    def test_read_back_mismatch_is_detected_and_rolled_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            before = tree_digest(root, canonical_only=True)

            def corrupt_create(path, content):
                corrupted = content.replace(
                    b"status: needs_review", b"status: active", 1
                )
                store_module._atomic_create(path, corrupted)

            result = apply_approved_plan(
                root,
                snapshot,
                plan,
                plan_digest(plan),
                atomic_creator=corrupt_create,
            )
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.problem.code, "read_back_mismatch")
            self.assertTrue(result.recovered)
            self.assertEqual(tree_digest(root, canonical_only=True), before)

    def test_results_are_safe_and_copy_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            snapshot, plan = self.read_and_plan(root)
            records = snapshot.records
            records.clear()
            self.assertTrue(snapshot.records)
            self.assertNotIn(self.update_body, repr(snapshot))
            result = apply_approved_plan(root, snapshot, plan, None)
            self.assertNotIn(self.update_body, repr(result))


if __name__ == "__main__":
    unittest.main()
