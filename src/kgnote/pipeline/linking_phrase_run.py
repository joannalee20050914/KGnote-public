"""Consent-gated linking-phrase transport with an append-only local ledger."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from kgnote.contracts import build_linking_phrase_candidates, validate_linking_phrase_context
from kgnote.extraction import TransportConfig, TransportResponse


PROMPT_VERSION = "kgnote.linking-phrase-prompt.v1"
MAX_RAW_RESPONSE_BYTES = 1_048_576


def _bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_durable(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


@dataclass(frozen=True, repr=False)
class LinkingPhraseRunPreview:
    context: Mapping[str, Any] = field(repr=False)
    provider: str
    model: str
    prompt_version: str
    outbound_bytes: int
    outbound_sha256: str
    consent_digest: str
    _envelope_json: str = field(repr=False)

    @property
    def envelope(self) -> dict[str, Any]:
        return json.loads(self._envelope_json)


@dataclass(frozen=True, repr=False)
class LinkingPhraseRunResult:
    status: Literal["accepted", "rejected", "error"]
    run_id: str
    transport_calls: int
    replayed: bool
    candidate_set: Mapping[str, Any] | None = field(default=None, repr=False)
    problem_code: str | None = None


def build_linking_phrase_run_preview(context: Mapping[str, Any], config: TransportConfig) -> LinkingPhraseRunPreview:
    validate_linking_phrase_context(context)
    envelope = {"schema_version": "kgnote.linking-phrase-outbound.v1", "destination": {"provider": config.provider, "model": config.model}, "prompt_version": PROMPT_VERSION, "response_schema_version": "kgnote.linking-phrase-response.v1", "context": context}
    encoded = _bytes(envelope)
    digest = _sha(encoded)
    return LinkingPhraseRunPreview(context, config.provider, config.model, PROMPT_VERSION, len(encoded), digest, digest, encoded.decode())


def _safe_stage(ledger_root: str | os.PathLike[str], run_id: str) -> Path | None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id) is None:
        return None
    root = Path(ledger_root)
    if root.is_symlink() or not root.is_dir():
        return None
    run = root / run_id
    if run.is_symlink() or not run.is_dir():
        return None
    return run / "linking-phrase"


def run_linking_phrase(
    *, preview: LinkingPhraseRunPreview, run_id: str, ledger_root: str | os.PathLike[str],
    generated_at: str, transport: Callable[[Mapping[str, Any], TransportConfig], TransportResponse],
    config: TransportConfig, allow_external_send: bool, approved_consent_digest: str | None,
) -> LinkingPhraseRunResult:
    if not isinstance(config, TransportConfig):
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="invalid_phrase_config")
    if (
        not isinstance(config.timeout_seconds, (int, float))
        or isinstance(config.timeout_seconds, bool)
        or config.timeout_seconds <= 0
    ):
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="invalid_phrase_config")
    try:
        dt.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="invalid_generated_at")
    expected_preview = build_linking_phrase_run_preview(preview.context, config)
    if (
        expected_preview.outbound_sha256 != preview.outbound_sha256
        or expected_preview.consent_digest != preview.consent_digest
        or expected_preview.outbound_bytes != preview.outbound_bytes
    ):
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="phrase_preview_mismatch")
    stage = _safe_stage(ledger_root, run_id)
    if stage is None:
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="unsafe_phrase_ledger")
    fingerprint = _sha(_bytes({"outbound": preview.outbound_sha256, "generated_at": generated_at, "provider": config.provider, "model": config.model}))
    if stage.exists():
        try:
            if stage.is_symlink() or not stage.is_dir():
                raise ValueError
            manifest = json.loads((stage / "manifest.json").read_text())
            raw_bytes = (stage / "raw-response.json").read_bytes()
            raw = raw_bytes.decode("utf-8")
            if manifest["fingerprint"] != fingerprint or manifest["raw_response_sha256"] != _sha(raw_bytes):
                raise ValueError
            candidate = build_linking_phrase_candidates(preview.context, raw, provider=config.provider, model=config.model, prompt_version=preview.prompt_version, generated_at=generated_at)
            if candidate.status != manifest["status"]:
                raise ValueError
            candidate_path = stage / "candidate-set.json"
            if candidate.payload is None:
                if candidate_path.exists():
                    raise ValueError
            elif candidate_path.is_symlink() or candidate_path.read_bytes() != _bytes(candidate.payload):
                raise ValueError
            return LinkingPhraseRunResult(candidate.status, run_id, 0, True, candidate.payload, candidate.problem_code)
        except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError):
            return LinkingPhraseRunResult("error", run_id, 0, True, problem_code="phrase_ledger_invalid")
    if not allow_external_send or approved_consent_digest != preview.consent_digest:
        return LinkingPhraseRunResult("error", run_id, 0, False, problem_code="phrase_consent_required" if approved_consent_digest is None else "phrase_consent_mismatch")
    try:
        response = transport(preview.envelope, config)
        if response.provider != config.provider or response.model != config.model:
            raise ValueError
        if len(response.raw_response) > MAX_RAW_RESPONSE_BYTES:
            return LinkingPhraseRunResult("error", run_id, 1, False, problem_code="phrase_response_too_large")
        raw = response.raw_response.decode("utf-8")
    except Exception:
        return LinkingPhraseRunResult("error", run_id, 1, False, problem_code="phrase_transport_error")
    candidate = build_linking_phrase_candidates(preview.context, raw, provider=config.provider, model=config.model, prompt_version=preview.prompt_version, generated_at=generated_at)
    manifest = {
        "schema_version": "kgnote.linking-phrase-ledger.v1",
        "fingerprint": fingerprint,
        "outbound_sha256": preview.outbound_sha256,
        "raw_response_sha256": _sha(raw.encode()),
        "status": candidate.status,
        "problem_code": candidate.problem_code,
        "provider": response.provider,
        "model": response.model,
        "request_id": response.request_id,
        "usage": dict(response.usage) if response.usage else None,
    }
    temporary = Path(tempfile.mkdtemp(prefix=".linking-phrase-", dir=stage.parent))
    try:
        _write_durable(temporary / "manifest.json", _bytes(manifest))
        _write_durable(temporary / "raw-response.json", raw.encode())
        if candidate.payload:
            _write_durable(temporary / "candidate-set.json", _bytes(candidate.payload))
        os.rename(temporary, stage)
    except OSError:
        for item in temporary.glob("*"): item.unlink(missing_ok=True)
        temporary.rmdir()
        return LinkingPhraseRunResult("error", run_id, 1, False, problem_code="phrase_ledger_write_failed")
    return LinkingPhraseRunResult(candidate.status, run_id, 1, False, candidate.payload, candidate.problem_code)


__all__ = ["LinkingPhraseRunPreview", "LinkingPhraseRunResult", "build_linking_phrase_run_preview", "run_linking_phrase"]
