import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kgnote.extraction import TransportResponse
from scripts import import_markdown
from scripts.serve_graph_view import execute_query


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "fixtures/phase0-obsidian/raw/synthetic-causality-chat.md"
RAW_RESPONSE = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
DIRECTORIES = ("sources", "concepts", "evidence", "learning-events", "edges", "raw")


class FakeTransport:
    def __init__(self, response, calls):
        self.response = response
        self.calls = calls

    def __call__(self, envelope, config):
        self.calls.append((envelope, config))
        return TransportResponse(
            raw_response=self.response,
            provider=config.provider,
            model=config.model,
            request_id="cli-fixture",
            usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )


class FakePhraseTransport:
    def __init__(self, calls): self.calls = calls
    def __call__(self, envelope, config):
        self.calls.append((envelope, config))
        proposals = [{"edge_id": edge["edge_id"], "linking_phrase": "與……形成對比"} for edge in envelope["context"]["edges"]]
        return TransportResponse(raw_response=json.dumps({"proposals": proposals}, ensure_ascii=False).encode(),provider=config.provider,model=config.model,request_id="phrase-fixture",usage={"input_tokens":5,"output_tokens":3,"total_tokens":8})


class ImportMarkdownCliTest(unittest.TestCase):
    def args(self, command, base, approval=None, apply_approval=None):
        result = [
            command,
            "--source", str(SOURCE),
            "--source-id", "src_synthetic_causality_chat",
            "--source-kind", "chatgpt_conversation",
            "--title", "Synthetic causality learning conversation",
            "--locator-basis", "line_range",
            "--generated-at", "2026-09-08T12:00:00+08:00",
            "--run-id", "cli_fixture_1",
            "--ledger", str(base / "ledger"),
            "--store", str(base / "store"),
        ]
        if approval is not None:
            result.extend(("--approve-send", approval))
        if apply_approval is not None:
            result.extend(("--approve-apply", apply_approval))
        return result

    def setup_roots(self, base):
        (base / "ledger").mkdir()
        (base / "store").mkdir()
        for name in DIRECTORIES:
            (base / "store" / name).mkdir()

    def test_preview_discloses_boundary_without_key_transport_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.setup_roots(base)
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(
                import_markdown.os, "environ", side_effect=AssertionError("must not read env")
            ):
                code = import_markdown.main(
                    self.args("preview", base), stdout=stdout, stderr=stderr,
                    transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
                )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(payload["status"], "awaiting_send_consent")
            self.assertEqual(payload["request_limits"]["requests"], 1)
            self.assertEqual(payload["request_limits"]["max_output_tokens"], 8192)
            self.assertFalse(payload["redaction"]["changed"])
            self.assertIn("No currency ceiling", payload["cost_notice"])
            self.assertEqual(list((base / "ledger").iterdir()), [])
            self.assertEqual(list((base / "store/raw").iterdir()), [])
            self.assertNotIn(SOURCE.read_text(), stdout.getvalue())

    def test_extract_requires_exact_digest_before_key_or_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.setup_roots(base)
            stdout, stderr = io.StringIO(), io.StringIO()
            code = import_markdown.main(
                self.args("extract", base, "0" * 64),
                environ={"GEMINI_API_KEY": "must-not-be-used"},
                stdout=stdout,
                stderr=stderr,
                transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            )
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(stderr.getvalue())["problem_code"], "consent_digest_mismatch")
            self.assertEqual(list((base / "ledger").iterdir()), [])

    def test_exact_consent_executes_once_and_returns_no_write_apply_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.setup_roots(base)
            first_out = io.StringIO()
            self.assertEqual(
                import_markdown.main(self.args("preview", base), stdout=first_out, stderr=io.StringIO()),
                0,
            )
            consent = json.loads(first_out.getvalue())["consent_digest"]
            calls = []
            stdout, stderr = io.StringIO(), io.StringIO()
            code = import_markdown.main(
                self.args("extract", base, consent),
                environ={"GEMINI_API_KEY": "fixture-secret"},
                stdout=stdout,
                stderr=stderr,
                transport_factory=lambda key: FakeTransport(RAW_RESPONSE.read_bytes(), calls),
            )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(len(calls), 1)
            self.assertEqual(payload["status"], "awaiting_apply_approval")
            self.assertEqual(payload["transport_calls"], 1)
            self.assertEqual(payload["operations"], {"CREATE": 11})
            self.assertEqual(len(payload["apply_approval_digest"]), 64)
            review = payload["review_preview"]
            self.assertEqual(review["schema_version"], "kgnote.import-review-preview.v1")
            self.assertEqual(review["summary"]["concepts"], 4)
            self.assertEqual(review["summary"]["relationships"], 3)
            self.assertFalse(review["summary"]["apply_blocked"])
            self.assertTrue(all(item["linking_phrase_status"] == "not_proposed" for item in review["relationships"]))
            self.assertTrue(all(item["source_excerpts"] for item in review["relationships"]))
            self.assertEqual(list((base / "store/raw").iterdir()), [])
            self.assertEqual(list((base / "store/concepts").iterdir()), [])
            manifest = json.loads((base / "ledger/cli_fixture_1/manifest.json").read_text())
            self.assertEqual(manifest["usage"]["total_tokens"], 15)
            self.assertNotIn("fixture-secret", stdout.getvalue())

    def test_apply_replays_ledger_requires_separate_digest_and_writes_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.setup_roots(base)
            preview_out = io.StringIO()
            import_markdown.main(self.args("preview", base), stdout=preview_out, stderr=io.StringIO())
            send_digest = json.loads(preview_out.getvalue())["consent_digest"]
            extract_out = io.StringIO()
            calls = []
            self.assertEqual(import_markdown.main(
                self.args("extract", base, send_digest),
                environ={"GEMINI_API_KEY": "fixture-secret"},
                stdout=extract_out,
                stderr=io.StringIO(),
                transport_factory=lambda key: FakeTransport(RAW_RESPONSE.read_bytes(), calls),
            ), 0)
            apply_digest = json.loads(extract_out.getvalue())["apply_approval_digest"]

            denied_out, denied_err = io.StringIO(), io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("apply", base),
                environ={}, stdout=denied_out, stderr=denied_err,
                transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            ), 6)
            self.assertEqual(json.loads(denied_err.getvalue())["problem_code"], "apply_approval_required")
            self.assertEqual(list((base / "store/concepts").iterdir()), [])

            apply_out, apply_err = io.StringIO(), io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("apply", base, apply_approval=apply_digest),
                environ={}, stdout=apply_out, stderr=apply_err,
                transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            ), 0)
            applied = json.loads(apply_out.getvalue())
            self.assertEqual(applied["status"], "applied")
            self.assertEqual(applied["transport_calls"], 0)
            self.assertEqual(applied["write_count"], 12)
            self.assertEqual(applied["raw_write_count"], 1)
            self.assertEqual(applied["read_back_records"], 11)
            self.assertEqual(applied["viewer_url"], "http://127.0.0.1:4173/")
            self.assertEqual(len(calls), 1)
            status, bootstrap = execute_query(base / "store", b"null")
            self.assertEqual(status, 200)
            self.assertEqual(bootstrap["status"], "ready")
            self.assertEqual(len(bootstrap["view"]["nodes"]), 5)
            self.assertEqual(len(bootstrap["view"]["links"]), 3)
            self.assertEqual(len(bootstrap["view"]["evidence"]), 2)
            self.assertEqual(len(bootstrap["view"]["sources"]), 1)

            second_preview_out = io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("apply", base),
                environ={}, stdout=second_preview_out, stderr=io.StringIO(),
            ), 6)
            second_digest = json.loads(second_preview_out.getvalue())["apply_approval_digest"]
            second_out = io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("apply", base, apply_approval=second_digest),
                environ={}, stdout=second_out, stderr=io.StringIO(),
            ), 0)
            second = json.loads(second_out.getvalue())
            self.assertEqual(second["write_count"], 0)
            self.assertEqual(second["raw_write_count"], 0)

    def test_phrase_preview_replays_ledger_without_transport_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.setup_roots(base)
            preview_out = io.StringIO()
            import_markdown.main(self.args("preview", base), stdout=preview_out, stderr=io.StringIO())
            send_digest = json.loads(preview_out.getvalue())["consent_digest"]
            calls = []
            import_markdown.main(
                self.args("extract", base, send_digest), environ={"GEMINI_API_KEY": "fixture-secret"},
                stdout=io.StringIO(), stderr=io.StringIO(),
                transport_factory=lambda key: FakeTransport(RAW_RESPONSE.read_bytes(), calls),
            )
            before = {path.relative_to(base): path.read_bytes() for path in base.rglob("*") if path.is_file()}
            stdout, stderr = io.StringIO(), io.StringIO()
            code = import_markdown.main(
                self.args("phrase-preview", base), environ={}, stdout=stdout, stderr=stderr,
                transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            )
            payload = json.loads(stdout.getvalue())
            after = {path.relative_to(base): path.read_bytes() for path in base.rglob("*") if path.is_file()}
            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(payload["status"], "awaiting_phrase_send_consent")
            self.assertEqual(payload["transport_calls"], 0)
            self.assertEqual(len(payload["consent_digest"]), 64)
            self.assertEqual(len(payload["context"]["edges"]), 1)
            self.assertEqual(payload["context"]["edges"][0]["canonical_relation"], "contrasts_with")
            self.assertTrue(all(item["review_status"] == "unreviewed" for item in payload["context"]["edges"][0]["evidence"]))
            self.assertEqual(before, after)
            self.assertEqual(len(calls), 1)

    def test_phrase_extract_ledger_and_human_review_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary); self.setup_roots(base)
            first=io.StringIO(); import_markdown.main(self.args("preview",base),stdout=first,stderr=io.StringIO())
            send=json.loads(first.getvalue())["consent_digest"]
            import_markdown.main(self.args("extract",base,send),environ={"GEMINI_API_KEY":"fixture"},stdout=io.StringIO(),stderr=io.StringIO(),transport_factory=lambda _:FakeTransport(RAW_RESPONSE.read_bytes(),[]))
            phrase=io.StringIO(); import_markdown.main(self.args("phrase-preview",base),stdout=phrase,stderr=io.StringIO())
            phrase_digest=json.loads(phrase.getvalue())["consent_digest"]
            denied_out, denied_err = io.StringIO(), io.StringIO()
            denied_args = self.args("phrase-extract", base) + ["--approve-phrase-send", "0" * 64]
            self.assertEqual(import_markdown.main(
                denied_args, environ={"GEMINI_API_KEY": "must-not-be-used"},
                stdout=denied_out, stderr=denied_err,
                phrase_transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            ), 8)
            self.assertEqual(json.loads(denied_err.getvalue())["problem_code"], "phrase_consent_mismatch")
            self.assertFalse((base / "ledger/cli_fixture_1/linking-phrase").exists())
            calls=[]; out=io.StringIO(); err=io.StringIO()
            args=self.args("phrase-extract",base)+["--approve-phrase-send",phrase_digest]
            code=import_markdown.main(args,environ={"GEMINI_API_KEY":"fixture"},stdout=out,stderr=err,phrase_transport_factory=lambda _:FakePhraseTransport(calls))
            payload=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(payload["status"],"awaiting_phrase_review"); self.assertEqual(len(calls),1)
            stage=base/"ledger/cli_fixture_1/linking-phrase"
            self.assertTrue((stage/"raw-response.json").is_file()); self.assertTrue((stage/"candidate-set.json").is_file())
            replay_out = io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("phrase-extract", base), environ={}, stdout=replay_out, stderr=io.StringIO(),
                phrase_transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            ), 0)
            replay = json.loads(replay_out.getvalue())
            self.assertTrue(replay["replayed"])
            self.assertEqual(replay["transport_calls"], 0)
            candidate=payload["candidate_set"]; decisions={"candidate_set_id":candidate["id"],"decisions":[{"edge_id":candidate["candidates"][0]["edge_id"],"action":"correct","corrected_linking_phrase":"清楚區分"}]}
            decisions_path=base/"decisions.json"; decisions_path.write_text(json.dumps(decisions))
            preview_out=io.StringIO(); preview_err=io.StringIO(); review_args=self.args("phrase-review",base)+["--phrase-decisions",str(decisions_path)]
            self.assertEqual(import_markdown.main(review_args,stdout=preview_out,stderr=preview_err),11)
            approval=json.loads(preview_out.getvalue())["approval_digest"]
            final_out=io.StringIO(); final_args=review_args+["--approve-phrase-review",approval]
            self.assertEqual(import_markdown.main(final_args,stdout=final_out,stderr=io.StringIO()),0)
            reviewed=json.loads(final_out.getvalue()); self.assertEqual(reviewed["status"],"recorded"); self.assertEqual(reviewed["review"]["decisions"][0]["effective_linking_phrase"],"清楚區分")
            self.assertEqual(reviewed["review"]["summary"]["guided_map_ready"], 0)
            self.assertFalse(reviewed["review"]["decisions"][0]["guided_map_promotion_eligible"])
            self.assertTrue((stage/"reviewed-set.json").is_file())

            tampered = json.loads((stage / "candidate-set.json").read_text())
            tampered["candidates"][0]["linking_phrase_candidate"] = "遭到竄改"
            (stage / "candidate-set.json").write_text(json.dumps(tampered))
            tamper_err = io.StringIO()
            self.assertEqual(import_markdown.main(
                self.args("phrase-extract", base), environ={}, stdout=io.StringIO(), stderr=tamper_err,
                phrase_transport_factory=lambda _: (_ for _ in ()).throw(AssertionError("must not build")),
            ), 9)
            self.assertEqual(json.loads(tamper_err.getvalue())["problem_code"], "phrase_ledger_invalid")


if __name__ == "__main__":
    unittest.main()
