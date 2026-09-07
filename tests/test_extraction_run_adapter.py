import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kgnote.extraction.run_adapter as run_module
from kgnote.extraction import (
    TransportConfig,
    TransportFailure,
    TransportResponse,
    build_extraction_preview,
    run_extraction,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_INPUT = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/input.json"
RAW_RESPONSE = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
GOLDEN = PROJECT_ROOT / "tests/fixtures/extraction-run/v1/golden.json"
GENERATED_AT = "2026-09-07T00:00:00+08:00"


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = 0
        self.envelopes = []

    def __call__(self, envelope, config):
        self.calls += 1
        self.envelopes.append(copy.deepcopy(envelope))
        if self.error:
            raise self.error
        return self.response


class ExtractionRunAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_input = load_json(VALID_INPUT)
        cls.raw_response = RAW_RESPONSE.read_bytes()
        cls.config = TransportConfig("fake-provider", "fake-model-v1", 12.5)

    def preview(self, **kwargs):
        return build_extraction_preview(
            extraction_input=self.extraction_input,
            extractor_version="fake-extractor.v1",
            prompt_version="fake-prompt.v1",
            config=self.config,
            **kwargs,
        )

    def response(self, raw=None, usage=True):
        return TransportResponse(
            raw_response=self.raw_response if raw is None else raw,
            provider="fake-provider",
            model="fake-model-v1",
            request_id="req_fixture_1",
            usage={"input_tokens": 123, "output_tokens": 45} if usage else None,
        )

    def execute(self, ledger, transport, *, run_id="run_fixture_1", preview=None, config=None,
                allow=True, consent="exact"):
        preview = preview or self.preview()
        approved = preview.consent_digest if consent == "exact" else consent
        return run_extraction(
            run_id=run_id,
            ledger_root=ledger,
            extraction_input=self.extraction_input,
            preview=preview,
            config=config or self.config,
            generated_at=GENERATED_AT,
            transport=transport,
            allow_external_send=allow,
            approved_consent_digest=approved,
        )

    def test_golden_preview_consent_accepted_ledger_and_replay(self):
        golden = load_json(GOLDEN)
        preview = self.preview()
        self.assertEqual(
            {
                "outbound_bytes": preview.outbound_bytes,
                "outbound_sha256": preview.outbound_sha256,
                "consent_digest": preview.consent_digest,
            },
            golden["preview"],
        )
        with tempfile.TemporaryDirectory() as ledger:
            transport = FakeTransport(self.response())
            result = self.execute(ledger, transport, preview=preview)
            self.assertEqual(result.status, "accepted")
            self.assertEqual(result.transport_calls, 1)
            self.assertEqual(transport.calls, 1)
            self.assertIsNotNone(result.candidate_result)

            run_dir = Path(ledger) / "run_fixture_1"
            manifest = json.loads((run_dir / "manifest.json").read_text())
            self.assertEqual(manifest, golden["manifest"])
            self.assertEqual((run_dir / "response.raw").read_bytes(), self.raw_response)
            self.assertEqual(
                hashlib.sha256((run_dir / "outbound.json").read_bytes()).hexdigest(),
                preview.outbound_sha256,
            )
            self.assertEqual(run_dir.stat().st_mode & 0o777, 0o700)
            for path in run_dir.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

            replay_transport = FakeTransport(error=AssertionError("must not call"))
            replay = self.execute(ledger, replay_transport, preview=preview)
            self.assertEqual(replay.status, "accepted")
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.transport_calls, 0)
            self.assertEqual(replay_transport.calls, 0)
            self.assertEqual(replay.candidate_result, result.candidate_result)

    def test_consent_failures_never_invoke_transport_or_write(self):
        with tempfile.TemporaryDirectory() as ledger:
            cases = (
                (False, "exact", "external_send_not_allowed"),
                (1, "exact", "external_send_not_allowed"),
                (True, None, "consent_required"),
                (True, "0" * 64, "consent_digest_mismatch"),
            )
            for index, (allow, consent, code) in enumerate(cases):
                with self.subTest(code=code):
                    transport = FakeTransport(error=AssertionError("must not call"))
                    result = self.execute(
                        ledger, transport, run_id=f"consent_{index}",
                        allow=allow, consent=consent,
                    )
                    self.assertEqual(result.problem.code, code)
                    self.assertEqual(transport.calls, 0)
            self.assertEqual(list(Path(ledger).iterdir()), [])

    def test_redaction_changes_only_outbound_copy(self):
        original = copy.deepcopy(self.extraction_input)
        redacted_marker = "Synthetic causality"
        preview = self.preview(
            redactor=lambda content: content.replace(redacted_marker, "[REDACTED]"),
            redaction_version="literal-redaction.v1",
        )
        self.assertTrue(preview.redaction.changed)
        self.assertIn("[REDACTED]", preview.envelope["source"]["content"])
        self.assertEqual(self.extraction_input, original)
        self.assertNotIn(self.extraction_input["source"]["content"], repr(preview))
        self.assertEqual(preview, self.preview(
            redactor=lambda content: content.replace(redacted_marker, "[REDACTED]"),
            redaction_version="literal-redaction.v1",
        ))
        with self.assertRaisesRegex(ValueError, "redaction_transform_version_required"):
            self.preview(redactor=lambda content: content)
        with self.assertRaisesRegex(ValueError, "redaction_version_without_transform"):
            self.preview(redaction_version="claimed-transform.v1")

    def test_rejected_responses_are_persisted_and_replayed(self):
        malformed = b"{not json"
        schema_invalid = json.loads(self.raw_response)
        schema_invalid["concepts"][0]["name"] = ""
        cases = (("malformed", malformed, "invalid_json"), (
            "schema", json.dumps(schema_invalid).encode(), "invalid_candidate_result"
        ))
        for run_id, raw, code in cases:
            with self.subTest(run_id=run_id), tempfile.TemporaryDirectory() as ledger:
                transport = FakeTransport(self.response(raw=raw))
                result = self.execute(ledger, transport, run_id=run_id)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertEqual((Path(ledger) / run_id / "response.raw").read_bytes(), raw)
                replay_transport = FakeTransport(error=AssertionError("must not call"))
                replay = self.execute(ledger, replay_transport, run_id=run_id)
                self.assertEqual(replay.status, "rejected")
                self.assertEqual(replay.problem.code, code)
                self.assertEqual(replay_transport.calls, 0)

    def test_transport_errors_are_classified_persisted_and_replayed(self):
        errors = (
            (TimeoutError("private timeout detail"), "timeout"),
            (TransportFailure("authentication_error"), "authentication_error"),
            (TransportFailure("rate_limit"), "rate_limit"),
            (TransportFailure("provider_error"), "provider_error"),
            (OSError("private network detail"), "transport_error"),
        )
        for index, (error, code) in enumerate(errors):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as ledger:
                run_id = f"error_{index}"
                transport = FakeTransport(error=error)
                result = self.execute(ledger, transport, run_id=run_id)
                self.assertEqual(result.status, "error")
                self.assertEqual(result.problem.code, code)
                self.assertEqual(transport.calls, 1)
                self.assertTrue((Path(ledger) / run_id / "response.raw").exists())
                replay = self.execute(
                    ledger, FakeTransport(error=AssertionError("must not call")), run_id=run_id
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.problem.code, code)

    def test_non_utf8_and_missing_usage_are_safe(self):
        with tempfile.TemporaryDirectory() as ledger:
            result = self.execute(ledger, FakeTransport(self.response(raw=b"\xff\xfe")), run_id="utf8")
            self.assertEqual(result.problem.code, "invalid_response_utf8")
            self.assertEqual((Path(ledger) / "utf8/response.raw").read_bytes(), b"\xff\xfe")
        with tempfile.TemporaryDirectory() as ledger:
            result = self.execute(ledger, FakeTransport(self.response(usage=False)), run_id="no_usage")
            self.assertEqual(result.status, "accepted")
            manifest = json.loads((Path(ledger) / "no_usage/manifest.json").read_text())
            self.assertIsNone(manifest["usage"])

        with tempfile.TemporaryDirectory() as ledger:
            mismatched = TransportResponse(
                raw_response=self.raw_response,
                provider="unexpected-provider",
                model="fake-model-v1",
            )
            result = self.execute(
                ledger, FakeTransport(mismatched), run_id="metadata_mismatch"
            )
            self.assertEqual(result.problem.code, "transport_metadata_mismatch")
            self.assertEqual(
                (Path(ledger) / "metadata_mismatch/response.raw").read_bytes(),
                self.raw_response,
            )

    def test_ledger_failure_cannot_report_accepted(self):
        with tempfile.TemporaryDirectory() as ledger, mock.patch.object(
            run_module, "_persist_run", side_effect=OSError("private disk detail")
        ):
            transport = FakeTransport(self.response())
            result = self.execute(ledger, transport)
            self.assertEqual(result.status, "error")
            self.assertEqual(result.problem.code, "ledger_write_failed")
            self.assertEqual(result.transport_calls, 1)
            self.assertEqual(transport.calls, 1)

    def test_run_id_conflict_and_unsafe_paths_never_call_transport(self):
        with tempfile.TemporaryDirectory() as ledger:
            first = self.execute(ledger, FakeTransport(self.response()))
            self.assertEqual(first.status, "accepted")
            changed = TransportConfig("fake-provider", "different-model", 12.5)
            changed_preview = build_extraction_preview(
                extraction_input=self.extraction_input,
                extractor_version="fake-extractor.v1",
                prompt_version="fake-prompt.v1",
                config=changed,
            )
            transport = FakeTransport(error=AssertionError("must not call"))
            conflict = self.execute(
                ledger, transport, config=changed, preview=changed_preview
            )
            self.assertEqual(conflict.problem.code, "run_id_conflict")
            self.assertEqual(transport.calls, 0)

        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / "target"
            target.mkdir()
            symlink = Path(parent) / "ledger-link"
            symlink.symlink_to(target, target_is_directory=True)
            transport = FakeTransport(error=AssertionError("must not call"))
            result = self.execute(symlink, transport, run_id="safe")
            self.assertEqual(result.problem.code, "ledger_root_symlink")
            self.assertEqual(transport.calls, 0)

        with tempfile.TemporaryDirectory() as ledger:
            target = Path(ledger) / "target"
            target.mkdir()
            (Path(ledger) / "run_link").symlink_to(target, target_is_directory=True)
            transport = FakeTransport(error=AssertionError("must not call"))
            result = self.execute(ledger, transport, run_id="run_link")
            self.assertEqual(result.problem.code, "unsafe_run_path")
            self.assertEqual(transport.calls, 0)

        with tempfile.TemporaryDirectory() as ledger:
            self.execute(ledger, FakeTransport(self.response()), run_id="recorded")
            response_path = Path(ledger) / "recorded/response.raw"
            original = response_path.read_bytes()
            response_path.unlink()
            outside = Path(ledger) / "outside.raw"
            outside.write_bytes(original)
            response_path.symlink_to(outside)
            transport = FakeTransport(error=AssertionError("must not call"))
            result = self.execute(ledger, transport, run_id="recorded")
            self.assertEqual(result.problem.code, "unsafe_ledger_file")
            self.assertEqual(transport.calls, 0)

    def test_preview_mismatch_unsafe_id_and_repr_do_not_expose_content(self):
        preview = self.preview()
        forged = copy.copy(preview)
        object.__setattr__(forged, "outbound_sha256", "0" * 64)
        source_content = self.extraction_input["source"]["content"]
        with tempfile.TemporaryDirectory() as ledger:
            transport = FakeTransport(error=AssertionError("must not call"))
            mismatch = self.execute(ledger, transport, preview=forged, consent=forged.consent_digest)
            self.assertEqual(mismatch.problem.code, "preview_input_mismatch")
            unsafe = self.execute(ledger, transport, run_id="../escape")
            self.assertEqual(unsafe.problem.code, "unsafe_run_id")
            self.assertEqual(transport.calls, 0)
            self.assertNotIn(source_content, repr(mismatch))


if __name__ == "__main__":
    unittest.main()
