import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest import mock

from kgnote.extraction import (
    GEMINI_MODEL,
    GEMINI_PROVIDER,
    GeminiExtractionTransport,
    TransportConfig,
    TransportFailure,
    build_extraction_preview,
    run_extraction,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_INPUT = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/input.json"
RAW_RESPONSE = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
GENERATED_AT = "2026-09-07T00:00:00+08:00"


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


class RecordingOpener:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def __call__(self, request, *, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return FakeHTTPResponse(self.payload)


class GeminiTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_input = json.loads(VALID_INPUT.read_text(encoding="utf-8"))
        cls.raw_text = RAW_RESPONSE.read_text(encoding="utf-8")
        cls.config = TransportConfig(GEMINI_PROVIDER, GEMINI_MODEL, 15.0)

    def provider_payload(self, text=None):
        return {
            "candidates": [{"content": {"parts": [{"text": text or self.raw_text}]}}],
            "modelVersion": "gemini-3.7-flash-2026-08",
            "responseId": "resp_fixture_9",
            "usageMetadata": {
                "promptTokenCount": 321,
                "candidatesTokenCount": 87,
                "totalTokenCount": 408,
            },
        }

    def test_exact_single_nonstream_request_and_metadata(self):
        opener = RecordingOpener(self.provider_payload())
        transport = GeminiExtractionTransport(api_key="secret-fixture", opener=opener)
        envelope = {"source": {"content": "synthetic"}, "response_contract": {}}
        response = transport(envelope, self.config)

        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(timeout, 15.0)
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent",
        )
        self.assertEqual(request.headers["X-goog-api-key"], "secret-fixture")
        body = json.loads(request.data)
        self.assertEqual(json.loads(body["contents"][0]["parts"][0]["text"]), envelope)
        self.assertEqual(body["generationConfig"]["candidateCount"], 1)
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 8192)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        self.assertFalse(body["generationConfig"]["responseJsonSchema"]["additionalProperties"])
        self.assertNotIn("secret-fixture", repr(transport))
        self.assertEqual(response.raw_response, self.raw_text.encode("utf-8"))
        self.assertEqual(response.request_id, "resp_fixture_9")
        self.assertEqual(
            response.usage,
            {"input_tokens": 321, "output_tokens": 87, "total_tokens": 408},
        )

    def test_missing_usage_is_none_and_transport_has_no_ambient_reads(self):
        payload = self.provider_payload()
        del payload["usageMetadata"]
        opener = RecordingOpener(payload)
        transport = GeminiExtractionTransport(api_key="secret", opener=opener)
        with mock.patch("builtins.open", side_effect=AssertionError("must not read files")), mock.patch(
            "os.getenv", side_effect=AssertionError("must not read environment")
        ):
            response = transport({"synthetic": True}, self.config)
        self.assertIsNone(response.usage)
        self.assertEqual(len(opener.calls), 1)

    def test_requires_explicit_key_and_selected_destination(self):
        with self.assertRaisesRegex(ValueError, "gemini_api_key_required"):
            GeminiExtractionTransport(api_key="")
        transport = GeminiExtractionTransport(api_key="secret", opener=RecordingOpener())
        for config in (
            TransportConfig("other", GEMINI_MODEL, 1),
            TransportConfig(GEMINI_PROVIDER, "other", 1),
        ):
            with self.subTest(config=config), self.assertRaises(TransportFailure) as raised:
                transport({}, config)
            self.assertEqual(raised.exception.code, "transport_error")

    def test_http_and_network_errors_are_safely_classified_without_retry(self):
        cases = (
            (HTTPError("https://example.invalid", 401, "private", {}, io.BytesIO()), "authentication_error"),
            (HTTPError("https://example.invalid", 403, "private", {}, io.BytesIO()), "authentication_error"),
            (HTTPError("https://example.invalid", 429, "private", {}, io.BytesIO()), "rate_limit"),
            (HTTPError("https://example.invalid", 500, "private", {}, io.BytesIO()), "provider_error"),
            (URLError("private DNS detail"), "transport_error"),
        )
        for error, code in cases:
            with self.subTest(code=code):
                opener = RecordingOpener(error=error)
                transport = GeminiExtractionTransport(api_key="secret", opener=opener)
                with self.assertRaises(TransportFailure) as raised:
                    transport({}, self.config)
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(len(opener.calls), 1)

    def test_timeout_malformed_and_blocked_responses_fail_closed(self):
        timeout_opener = RecordingOpener(error=TimeoutError("private"))
        with self.assertRaises(TimeoutError):
            GeminiExtractionTransport(api_key="secret", opener=timeout_opener)({}, self.config)
        self.assertEqual(len(timeout_opener.calls), 1)

        for payload in ({"promptFeedback": {"blockReason": "SAFETY"}}, {"candidates": []}):
            with self.subTest(payload=payload), self.assertRaises(TransportFailure) as raised:
                GeminiExtractionTransport(
                    api_key="secret", opener=RecordingOpener(payload)
                )({}, self.config)
            self.assertEqual(raised.exception.code, "provider_error")

    def test_synthetic_end_to_end_uses_existing_validation_and_ledger(self):
        opener = RecordingOpener(self.provider_payload())
        transport = GeminiExtractionTransport(api_key="secret-fixture", opener=opener)
        preview = build_extraction_preview(
            extraction_input=self.extraction_input,
            extractor_version="gemini-extractor.v1",
            prompt_version="gemini-candidate-prompt.v1",
            config=self.config,
        )
        with tempfile.TemporaryDirectory() as ledger, mock.patch.dict("os.environ", {}, clear=True):
            result = run_extraction(
                run_id="gemini_fixture_1", ledger_root=ledger,
                extraction_input=self.extraction_input, preview=preview,
                config=self.config, generated_at=GENERATED_AT, transport=transport,
                allow_external_send=True,
                approved_consent_digest=preview.consent_digest,
            )
            self.assertEqual(result.status, "accepted")
            self.assertEqual(result.transport_calls, 1)
            self.assertEqual(len(opener.calls), 1)
            manifest = json.loads((Path(ledger) / "gemini_fixture_1/manifest.json").read_text())
            self.assertEqual(manifest["request_id"], "resp_fixture_9")
            self.assertEqual(manifest["usage"]["total_tokens"], 408)
            self.assertEqual(
                (Path(ledger) / "gemini_fixture_1/response.raw").read_bytes(),
                self.raw_text.encode("utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
