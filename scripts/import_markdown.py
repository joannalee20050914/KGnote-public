#!/usr/bin/env python3
"""Consent-gated entry point for one Markdown extraction, dry-run, and apply."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kgnote.extraction import (  # noqa: E402
    GEMINI_MODEL,
    GEMINI_PROVIDER,
    GeminiExtractionTransport,
    GeminiLinkingPhraseTransport,
    TransportConfig,
)
from kgnote.ingestion import SourceMetadata  # noqa: E402
from kgnote.pipeline import (  # noqa: E402
    apply_offline_import,
    build_import_review_preview,
    build_linking_phrase_context,
    build_linking_phrase_run_preview,
    run_linking_phrase,
    build_phrase_review_preview,
    apply_phrase_review,
    build_live_import_preview,
    run_live_import,
)


EXTRACTOR_VERSION = "kgnote.gemini-extractor.v1"
PROMPT_VERSION = "kgnote.gemini-candidate-prompt.v1"
DEFAULT_TIMEOUT_SECONDS = 30.0
API_KEY_ENV = "GEMINI_API_KEY"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview, extract, or separately approve one Markdown canonical apply."
    )
    parser.add_argument("command", choices=("preview", "extract", "apply", "phrase-preview", "phrase-extract", "phrase-review"))
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-kind", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--captured-at")
    parser.add_argument("--locator-basis", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--approve-send")
    parser.add_argument("--approve-apply")
    parser.add_argument("--approve-phrase-send")
    parser.add_argument("--phrase-decisions")
    parser.add_argument("--approve-phrase-review")
    return parser


def _write(payload: Mapping[str, object], stream) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _safe_error(code: str) -> dict[str, object]:
    return {"schema_version": "kgnote.live-import-cli.v1", "status": "error", "problem_code": code}


def _must_not_transport(*_args, **_kwargs):
    raise AssertionError("apply_must_replay_ledger_without_transport")


def _dry_run_payload(result, extraction_input) -> dict[str, object]:
    import_preview = result.import_preview
    operations: dict[str, int] = {}
    for item in import_preview.plan.items:
        operation = item["operation"]
        operations[operation] = operations.get(operation, 0) + 1
    return {
        "schema_version": "kgnote.live-import-cli.v1",
        "status": "awaiting_apply_approval",
        "run_id": result.extraction.run_id,
        "replayed": result.extraction.replayed,
        "transport_calls": result.extraction.transport_calls,
        "raw_response_sha256": result.extraction.raw_response_sha256,
        "operations": operations,
        "items": import_preview.plan.items,
        "source_bytes": import_preview.source_bytes,
        "source_sha256": import_preview.source_sha256,
        "raw_relative_path": import_preview.raw_relative_path,
        "apply_approval_digest": import_preview.approval_digest,
        "review_preview": build_import_review_preview(
            extraction_input=extraction_input,
            candidate_result=result.extraction.candidate_result,
            import_preview=import_preview,
        ),
    }


def _phrase_preview_payload(result, extraction_input, config) -> dict[str, object]:
    review = build_import_review_preview(
        extraction_input=extraction_input,
        candidate_result=result.extraction.candidate_result,
        import_preview=result.import_preview,
    )
    context = build_linking_phrase_context(
        review, graph_snapshot_sha256=result.import_preview.approval_digest,
    )
    phrase_preview = build_linking_phrase_run_preview(context, config)
    return {
        "schema_version": "kgnote.live-import-cli.v1",
        "status": "awaiting_phrase_send_consent",
        "run_id": result.extraction.run_id,
        "replayed": result.extraction.replayed,
        "transport_calls": result.extraction.transport_calls,
        "destination": {"provider": config.provider, "model": config.model},
        "prompt_version": phrase_preview.prompt_version,
        "outbound_bytes": phrase_preview.outbound_bytes, "outbound_sha256": phrase_preview.outbound_sha256,
        "consent_digest": phrase_preview.consent_digest, "context": context,
        "notice": "No phrase request was sent. Candidate Evidence remains unreviewed and any future phrase output must remain pending.",
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    transport_factory: Callable[[str], object] = GeminiExtractionTransport,
    phrase_transport_factory: Callable[[str], object] = GeminiLinkingPhraseTransport,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> int:
    args = _parser().parse_args(argv)
    config = TransportConfig(GEMINI_PROVIDER, GEMINI_MODEL, DEFAULT_TIMEOUT_SECONDS)
    metadata = SourceMetadata(
        source_id=args.source_id,
        source_kind=args.source_kind,
        title=args.title,
        captured_at=args.captured_at,
        locator_basis=args.locator_basis,
    )
    try:
        preview = build_live_import_preview(
            source_path=args.source,
            metadata=metadata,
            extractor_version=EXTRACTOR_VERSION,
            prompt_version=PROMPT_VERSION,
            config=config,
        )
    except (OSError, ValueError) as error:
        code = getattr(error, "code", "preview_failed")
        _write(_safe_error(code), stderr)
        return 2

    outbound = preview.extraction
    preview_payload = {
        "schema_version": "kgnote.live-import-cli.v1",
        "status": "awaiting_send_consent",
        "destination": {"provider": config.provider, "model": config.model},
        "source_id": outbound.source_id,
        "source_content_sha256": outbound.source_content_sha256,
        "outbound_bytes": outbound.outbound_bytes,
        "outbound_sha256": outbound.outbound_sha256,
        "redaction": {
            "transform_version": outbound.redaction.transform_version,
            "changed": outbound.redaction.changed,
            "outbound_content_sha256": outbound.redaction.outbound_content_sha256,
        },
        "request_limits": {"requests": 1, "max_output_tokens": 8192, "timeout_seconds": config.timeout_seconds},
        "cost_notice": "No currency ceiling is enforced; verify current provider pricing before approval.",
        "consent_digest": outbound.consent_digest,
        "next_command": "extract",
    }
    if args.command == "preview":
        _write(preview_payload, stdout)
        return 0
    if args.command in {"apply", "phrase-preview", "phrase-extract", "phrase-review"}:
        try:
            result = run_live_import(
                preview=preview,
                run_id=args.run_id,
                ledger_root=args.ledger,
                store_root=args.store,
                config=config,
                generated_at=args.generated_at,
                transport=_must_not_transport,
                allow_external_send=False,
                approved_consent_digest=None,
            )
        except (OSError, ValueError):
            _write(_safe_error("apply_preview_failed"), stderr)
            return 5
        if result.status != "planned":
            _write(_safe_error(result.problem_code or "apply_preview_failed"), stderr)
            return 5
        if args.command == "phrase-preview":
            try:
                _write(_phrase_preview_payload(result, preview.extraction_input, config), stdout)
            except (KeyError, TypeError, ValueError):
                _write(_safe_error("phrase_preview_failed"), stderr)
                return 5
            return 0
        if args.command == "phrase-extract":
            phrase_payload = _phrase_preview_payload(result, preview.extraction_input, config)
            phrase_preview = build_linking_phrase_run_preview(phrase_payload["context"], config)
            replay = run_linking_phrase(
                preview=phrase_preview, run_id=args.run_id, ledger_root=args.ledger,
                generated_at=args.generated_at, transport=_must_not_transport, config=config,
                allow_external_send=False, approved_consent_digest=None,
            )
            if replay.replayed:
                if replay.status != "accepted":
                    _write(_safe_error(replay.problem_code or "phrase_execution_failed"), stderr)
                    return 9
                _write({
                    "schema_version": "kgnote.live-import-cli.v1",
                    "status": "awaiting_phrase_review", "run_id": args.run_id,
                    "replayed": True, "transport_calls": 0,
                    "candidate_set": replay.candidate_set,
                }, stdout)
                return 0
            if args.approve_phrase_send != phrase_payload["consent_digest"]:
                _write(phrase_payload, stdout)
                _write(_safe_error("phrase_consent_required" if not args.approve_phrase_send else "phrase_consent_mismatch"), stderr)
                return 8
            active_environ = os.environ if environ is None else environ
            api_key = active_environ.get(API_KEY_ENV)
            if not isinstance(api_key, str) or not api_key.strip():
                _write(_safe_error("gemini_api_key_required"), stderr); return 4
            phrase_result = run_linking_phrase(preview=phrase_preview,run_id=args.run_id,ledger_root=args.ledger,generated_at=args.generated_at,transport=phrase_transport_factory(api_key),config=config,allow_external_send=True,approved_consent_digest=args.approve_phrase_send)
            if phrase_result.status != "accepted":
                _write(_safe_error(phrase_result.problem_code or "phrase_execution_failed"), stderr); return 9
            _write({"schema_version":"kgnote.live-import-cli.v1","status":"awaiting_phrase_review","run_id":args.run_id,"replayed":phrase_result.replayed,"transport_calls":phrase_result.transport_calls,"candidate_set":phrase_result.candidate_set},stdout)
            return 0
        if args.command == "phrase-review":
            try:
                phrase_payload = _phrase_preview_payload(result, preview.extraction_input, config)
                phrase_preview = build_linking_phrase_run_preview(phrase_payload["context"], config)
                phrase_result = run_linking_phrase(
                    preview=phrase_preview, run_id=args.run_id, ledger_root=args.ledger,
                    generated_at=args.generated_at, transport=_must_not_transport, config=config,
                    allow_external_send=False, approved_consent_digest=None,
                )
                if not phrase_result.replayed or phrase_result.status != "accepted":
                    raise ValueError
                candidate = phrase_result.candidate_set
                decisions_path=Path(args.phrase_decisions) if args.phrase_decisions else None
                if decisions_path is None or decisions_path.is_symlink() or not decisions_path.is_file(): raise ValueError
                decisions=json.loads(decisions_path.read_text())
                review=build_phrase_review_preview(candidate,decisions,reviewed_at=args.generated_at)
            except (OSError,ValueError,json.JSONDecodeError):
                _write(_safe_error("invalid_phrase_review"),stderr); return 10
            review_payload={"schema_version":"kgnote.live-import-cli.v1","status":"awaiting_phrase_review_approval","review":review.payload,"approval_digest":review.approval_digest}
            if args.approve_phrase_review!=review.approval_digest:
                _write(review_payload,stdout); _write(_safe_error("phrase_review_approval_required" if not args.approve_phrase_review else "phrase_review_digest_mismatch"),stderr); return 11
            status=apply_phrase_review(args.ledger,args.run_id,review,args.approve_phrase_review)
            if status not in {"recorded","unchanged"}: _write(_safe_error(status),stderr); return 12
            _write({"schema_version":"kgnote.live-import-cli.v1","status":status,"review":review.payload},stdout); return 0
        dry_run_payload = _dry_run_payload(result, preview.extraction_input)
        if dry_run_payload["review_preview"]["summary"]["apply_blocked"]:
            _write(dry_run_payload, stdout)
            _write(_safe_error("apply_preview_blocked"), stderr)
            return 5
        if args.approve_apply != result.import_preview.approval_digest:
            _write(dry_run_payload, stdout)
            _write(_safe_error("apply_digest_mismatch" if args.approve_apply else "apply_approval_required"), stderr)
            return 6
        applied = apply_offline_import(
            result.import_preview, approved_digest=args.approve_apply
        )
        if applied.status != "applied":
            _write(_safe_error(applied.problem_code or "apply_failed"), stderr)
            return 7
        _write({
            "schema_version": "kgnote.live-import-cli.v1",
            "status": "applied",
            "run_id": result.extraction.run_id,
            "replayed": result.extraction.replayed,
            "transport_calls": result.extraction.transport_calls,
            "write_count": applied.write_count,
            "raw_write_count": applied.raw_write_count,
            "read_back_records": len(applied.audit_snapshot.records),
            "viewer_command": [
                str(PROJECT_ROOT / ".venv/bin/python"),
                str(PROJECT_ROOT / "scripts/serve_graph_view.py"),
                "--store", str(Path(args.store).resolve()), "--port", "4173",
            ],
            "viewer_url": "http://127.0.0.1:4173/",
        }, stdout)
        return 0
    if args.approve_send != outbound.consent_digest:
        _write(preview_payload, stdout)
        _write(_safe_error("consent_digest_mismatch" if args.approve_send else "consent_required"), stderr)
        return 3

    active_environ = os.environ if environ is None else environ
    api_key = active_environ.get(API_KEY_ENV)
    if not isinstance(api_key, str) or not api_key.strip():
        _write(_safe_error("gemini_api_key_required"), stderr)
        return 4
    try:
        transport = transport_factory(api_key)
        result = run_live_import(
            preview=preview,
            run_id=args.run_id,
            ledger_root=args.ledger,
            store_root=args.store,
            config=config,
            generated_at=args.generated_at,
            transport=transport,
            allow_external_send=True,
            approved_consent_digest=args.approve_send,
        )
    except (OSError, ValueError):
        _write(_safe_error("execution_failed"), stderr)
        return 5
    if result.status != "planned":
        _write(_safe_error(result.problem_code or "execution_failed"), stderr)
        return 5

    _write(_dry_run_payload(result, preview.extraction_input), stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
