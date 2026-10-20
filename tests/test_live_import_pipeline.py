import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kgnote.extraction import TransportConfig, TransportResponse
from kgnote.ingestion import SourceMetadata
from kgnote.pipeline import build_live_import_preview, run_live_import


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "fixtures/phase0-obsidian/raw/synthetic-causality-chat.md"
RAW_RESPONSE = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
DIRECTORIES = ("sources", "concepts", "evidence", "learning-events", "edges", "raw")
GENERATED_AT = "2026-09-08T12:00:00+08:00"


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in Path(root).rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class FakeTransport:
    def __init__(self, raw_response):
        self.raw_response = raw_response
        self.calls = 0

    def __call__(self, envelope, config):
        self.calls += 1
        return TransportResponse(
            raw_response=self.raw_response,
            provider=config.provider,
            model=config.model,
            request_id="live_fixture_response",
            usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        )


class LiveImportPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = SourceMetadata(
            source_id="src_synthetic_causality_chat",
            source_kind="chatgpt_conversation",
            title="Synthetic causality learning conversation",
            captured_at=None,
            locator_basis="line_range",
        )
        cls.config = TransportConfig("fake-provider", "fake-model", 10)

    def make_directories(self, root):
        for name in DIRECTORIES:
            (Path(root) / name).mkdir()

    def preview(self):
        return build_live_import_preview(
            source_path=SOURCE,
            metadata=self.metadata,
            extractor_version="live-fixture-extractor.v1",
            prompt_version="live-fixture-prompt.v1",
            config=self.config,
        )

    def test_consent_to_provider_candidate_to_dry_run_is_no_write(self):
        preview = self.preview()
        original_input = copy.deepcopy(preview.extraction_input)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            ledger = base / "ledger"
            store = base / "store"
            ledger.mkdir()
            store.mkdir()
            self.make_directories(store)
            store_before = tree_digest(store)
            transport = FakeTransport(RAW_RESPONSE.read_bytes())

            result = run_live_import(
                preview=preview,
                run_id="live_fixture_1",
                ledger_root=ledger,
                store_root=store,
                config=self.config,
                generated_at=GENERATED_AT,
                transport=transport,
                allow_external_send=True,
                approved_consent_digest=preview.extraction.consent_digest,
            )

            self.assertEqual(result.status, "planned")
            self.assertEqual(transport.calls, 1)
            self.assertEqual(result.extraction.status, "accepted")
            self.assertEqual(result.extraction.transport_calls, 1)
            self.assertEqual(result.import_preview.status, "planned")
            self.assertEqual(len(result.import_preview.plan.items), 11)
            self.assertEqual(
                {item["operation"] for item in result.import_preview.plan.items}, {"CREATE"}
            )
            self.assertEqual(tree_digest(store), store_before)
            self.assertEqual(list((store / "raw").iterdir()), [])
            self.assertEqual(preview.extraction_input, original_input)
            self.assertTrue((ledger / "live_fixture_1/manifest.json").is_file())
            self.assertNotIn(SOURCE.read_text(), repr(preview))
            self.assertNotIn(SOURCE.read_text(), repr(result))

    def test_missing_or_wrong_consent_never_calls_transport_or_writes(self):
        preview = self.preview()
        for index, consent in enumerate((None, "0" * 64)):
            with self.subTest(consent=consent), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                ledger = base / "ledger"
                store = base / "store"
                ledger.mkdir()
                store.mkdir()
                self.make_directories(store)
                transport = FakeTransport(RAW_RESPONSE.read_bytes())
                with mock.patch.dict(os.environ, {}, clear=True):
                    result = run_live_import(
                        preview=preview,
                        run_id=f"denied_{index}",
                        ledger_root=ledger,
                        store_root=store,
                        config=self.config,
                        generated_at=GENERATED_AT,
                        transport=transport,
                        allow_external_send=True,
                        approved_consent_digest=consent,
                    )
                self.assertEqual(result.status, "error")
                self.assertEqual(transport.calls, 0)
                self.assertEqual(list(ledger.iterdir()), [])
                self.assertEqual(tree_digest(store), hashlib.sha256().hexdigest())

    def test_provider_rejection_stops_before_normalization_and_store_read(self):
        preview = self.preview()
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "ledger"
            ledger.mkdir()
            transport = FakeTransport(b"{not json")
            with mock.patch(
                "kgnote.pipeline.live_import.build_candidate_import_preview",
                side_effect=AssertionError("must not plan"),
            ):
                result = run_live_import(
                    preview=preview,
                    run_id="rejected_fixture",
                    ledger_root=ledger,
                    store_root=Path(temporary) / "missing-store",
                    config=self.config,
                    generated_at=GENERATED_AT,
                    transport=transport,
                    allow_external_send=True,
                    approved_consent_digest=preview.extraction.consent_digest,
                )
            self.assertEqual(result.status, "rejected")
            self.assertEqual(result.problem_code, "invalid_json")
            self.assertEqual(transport.calls, 1)


if __name__ == "__main__":
    unittest.main()
