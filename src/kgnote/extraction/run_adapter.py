"""Consent-gated provider-neutral extraction runs with an immutable local ledger."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol

from rfc3339_validator import validate_rfc3339

from kgnote.contracts.extraction import validate_extraction_input
from kgnote.extraction.offline_response import ExtractionAttempt, replay_extraction_response


RUN_ADAPTER_VERSION = "kgnote.extraction-run.v1"
RESPONSE_CONTRACT = {
    "schema_version": "kgnote.extraction-output.v1",
    "root_fields": ["concepts", "edges", "evidence", "learning_events"],
    "adapter_owned_fields_forbidden": [
        "extractor_version", "generated_at", "schema_version", "source_id"
    ],
}
TRANSPORT_ERROR_CODES = {
    "authentication_error", "provider_error", "rate_limit", "timeout", "transport_error"
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class RedactionReport:
    transform_version: str
    changed: bool
    original_content_sha256: str
    outbound_content_sha256: str


@dataclass(frozen=True, repr=False)
class ExtractionPreview:
    adapter_version: str
    source_id: str
    source_content_sha256: str
    extractor_version: str
    prompt_version: str
    outbound_bytes: int
    outbound_sha256: str
    consent_digest: str
    redaction: RedactionReport
    _envelope_json: str = field(repr=False)

    @property
    def envelope(self) -> dict[str, Any]:
        return json.loads(self._envelope_json)

    def __repr__(self) -> str:
        return (
            "ExtractionPreview("
            f"adapter_version={self.adapter_version!r}, source_id={self.source_id!r}, "
            f"source_content_sha256={self.source_content_sha256!r}, "
            f"extractor_version={self.extractor_version!r}, "
            f"prompt_version={self.prompt_version!r}, outbound_bytes={self.outbound_bytes!r}, "
            f"outbound_sha256={self.outbound_sha256!r}, consent_digest={self.consent_digest!r}, "
            f"redaction={self.redaction!r})"
        )


@dataclass(frozen=True)
class TransportConfig:
    provider: str
    model: str
    timeout_seconds: float


@dataclass(frozen=True, repr=False)
class TransportResponse:
    raw_response: bytes = field(repr=False)
    provider: str
    model: str
    request_id: str | None = None
    usage: Mapping[str, int] | None = None


class ExtractionTransport(Protocol):
    def __call__(
        self, envelope: Mapping[str, Any], config: TransportConfig
    ) -> TransportResponse: ...


class TransportFailure(Exception):
    """A safe transport failure; message/body content is intentionally discarded."""

    def __init__(self, code: str):
        self.code = code if code in TRANSPORT_ERROR_CODES else "transport_error"
        super().__init__(self.code)


@dataclass(frozen=True)
class ExtractionRunProblem:
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class ExtractionRunResult:
    status: Literal["accepted", "rejected", "error"]
    run_id: str
    request_fingerprint: str
    transport_calls: int
    replayed: bool = False
    raw_response_sha256: str | None = None
    _candidate_result_json: str | None = field(default=None, repr=False)
    problem: ExtractionRunProblem | None = None

    @property
    def candidate_result(self) -> dict[str, Any] | None:
        if self._candidate_result_json is None:
            return None
        return json.loads(self._candidate_result_json)

    def __repr__(self) -> str:
        return (
            "ExtractionRunResult("
            f"status={self.status!r}, run_id={self.run_id!r}, "
            f"request_fingerprint={self.request_fingerprint!r}, "
            f"transport_calls={self.transport_calls!r}, replayed={self.replayed!r}, "
            f"raw_response_sha256={self.raw_response_sha256!r}, problem={self.problem!r})"
        )


def build_extraction_preview(
    *, extraction_input: Mapping[str, Any], extractor_version: str,
    prompt_version: str, config: TransportConfig,
    redactor: Callable[[str], str] | None = None,
    redaction_version: str = "none.v1",
) -> ExtractionPreview:
    """Build the exact deterministic outbound envelope without transport or persistence."""

    validate_extraction_input(extraction_input)
    if not isinstance(config, TransportConfig):
        raise ValueError("invalid_transport_config")
    for value, code in (
        (extractor_version, "invalid_extractor_version"),
        (prompt_version, "invalid_prompt_version"),
        (redaction_version, "invalid_redaction_version"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(code)
    if redactor is None and redaction_version != "none.v1":
        raise ValueError("redaction_version_without_transform")
    if redactor is not None and redaction_version == "none.v1":
        raise ValueError("redaction_transform_version_required")
    provider = _safe_text(config.provider, "invalid_provider")
    model = _safe_text(config.model, "invalid_model")
    if (
        not isinstance(config.timeout_seconds, (int, float))
        or isinstance(config.timeout_seconds, bool)
        or config.timeout_seconds <= 0
    ):
        raise ValueError("invalid_timeout")
    source = extraction_input["source"]
    original_content = source["content"]
    outbound_content = redactor(original_content) if redactor else original_content
    if not isinstance(outbound_content, str):
        raise ValueError("redactor_must_return_text")
    original_hash = _sha256(original_content.encode("utf-8"))
    outbound_hash = _sha256(outbound_content.encode("utf-8"))
    envelope = {
        "adapter_version": RUN_ADAPTER_VERSION,
        "extractor_version": extractor_version,
        "input_schema_version": extraction_input["schema_version"],
        "prompt_version": prompt_version,
        "destination": {
            "model": model,
            "provider": provider,
            "timeout_seconds": config.timeout_seconds,
        },
        "response_contract": RESPONSE_CONTRACT,
        "source": {
            "captured_at": source["captured_at"], "content": outbound_content,
            "content_sha256": source["content_sha256"], "id": source["id"],
            "locator_basis": source["locator_basis"], "source_kind": source["source_kind"],
            "title": source["title"],
        },
    }
    envelope_json = _canonical_json(envelope)
    envelope_bytes = envelope_json.encode("utf-8")
    digest = _sha256(envelope_bytes)
    return ExtractionPreview(
        adapter_version=RUN_ADAPTER_VERSION, source_id=source["id"],
        source_content_sha256=source["content_sha256"], extractor_version=extractor_version,
        prompt_version=prompt_version, outbound_bytes=len(envelope_bytes),
        outbound_sha256=digest, consent_digest=digest,
        redaction=RedactionReport(
            transform_version=redaction_version, changed=original_content != outbound_content,
            original_content_sha256=original_hash, outbound_content_sha256=outbound_hash,
        ),
        _envelope_json=envelope_json,
    )


def _safe_text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _request_fingerprint(
    preview: ExtractionPreview, config: TransportConfig, generated_at: str
) -> str:
    payload = {
        "adapter_version": RUN_ADAPTER_VERSION, "envelope_sha256": preview.outbound_sha256,
        "generated_at": generated_at, "model": config.model, "provider": config.provider,
        "redaction_version": preview.redaction.transform_version,
        "timeout_seconds": config.timeout_seconds,
    }
    return _sha256(_canonical_json(payload).encode("utf-8"))


def _error_result(
    run_id: str, fingerprint: str, code: str, *, transport_calls: int = 0,
    replayed: bool = False, raw_response_sha256: str | None = None,
    path: tuple[object, ...] = (),
) -> ExtractionRunResult:
    return ExtractionRunResult(
        status="error", run_id=run_id, request_fingerprint=fingerprint,
        transport_calls=transport_calls, replayed=replayed,
        raw_response_sha256=raw_response_sha256,
        problem=ExtractionRunProblem(code, path),
    )


def _result_from_attempt(
    run_id: str, fingerprint: str, attempt: ExtractionAttempt, *,
    transport_calls: int, replayed: bool = False,
) -> ExtractionRunResult:
    problem = (
        ExtractionRunProblem(attempt.rejection.code, attempt.rejection.path)
        if attempt.rejection else None
    )
    candidate_json = (
        _canonical_json(attempt.candidate_result) if attempt.candidate_result is not None else None
    )
    return ExtractionRunResult(
        status=attempt.status, run_id=run_id, request_fingerprint=fingerprint,
        transport_calls=transport_calls, replayed=replayed,
        raw_response_sha256=attempt.raw_response_sha256,
        _candidate_result_json=candidate_json, problem=problem,
    )


def _validate_ledger_root(root: Path) -> tuple[Path | None, str | None]:
    if root.is_symlink():
        return None, "ledger_root_symlink"
    try:
        resolved = root.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None, "ledger_root_missing"
    if not resolved.is_dir():
        return None, "ledger_root_not_directory"
    if (resolved / ".git").exists() or any(
        (resolved / name).exists()
        for name in ("sources", "concepts", "evidence", "learning-events", "edges")
    ):
        return None, "unsafe_ledger_root"
    return resolved, None


def _write_file(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _persist_run(
    ledger_root: Path, run_id: str, envelope_bytes: bytes,
    raw_response: bytes, manifest: Mapping[str, Any],
) -> None:
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=ledger_root))
    os.chmod(temporary, 0o700)
    final = ledger_root / run_id
    final_created = False
    try:
        _write_file(temporary / "outbound.json", envelope_bytes)
        _write_file(temporary / "response.raw", raw_response)
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        _write_file(temporary / "manifest.json", manifest_bytes)
        final.mkdir(mode=0o700)
        final_created = True
        for name in ("outbound.json", "response.raw", "manifest.json"):
            os.rename(temporary / name, final / name)
    except Exception:
        if final_created:
            for child in final.iterdir():
                child.unlink()
            final.rmdir()
        raise
    finally:
        if temporary.exists():
            for child in temporary.iterdir():
                child.unlink()
            temporary.rmdir()


def _load_replay(
    run_directory: Path, *, fingerprint: str,
    extraction_input: Mapping[str, Any], extractor_version: str, generated_at: str,
) -> ExtractionRunResult:
    if run_directory.is_symlink() or not run_directory.is_dir():
        return _error_result(run_directory.name, fingerprint, "unsafe_run_path")
    expected_paths = [
        run_directory / "manifest.json",
        run_directory / "response.raw",
        run_directory / "outbound.json",
    ]
    if any(path.is_symlink() or not path.is_file() for path in expected_paths):
        return _error_result(run_directory.name, fingerprint, "unsafe_ledger_file")
    try:
        manifest_bytes = (run_directory / "manifest.json").read_bytes()
        raw_response = (run_directory / "response.raw").read_bytes()
        envelope_bytes = (run_directory / "outbound.json").read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _error_result(run_directory.name, fingerprint, "ledger_corrupt")
    if not isinstance(manifest, dict) or manifest.get("request_fingerprint") != fingerprint:
        return _error_result(run_directory.name, fingerprint, "run_id_conflict")
    if manifest.get("outbound_sha256") != _sha256(envelope_bytes):
        return _error_result(run_directory.name, fingerprint, "ledger_corrupt")
    if manifest.get("raw_response_sha256") != _sha256(raw_response):
        return _error_result(run_directory.name, fingerprint, "ledger_corrupt")
    recorded_status = manifest.get("status")
    if recorded_status in {"accepted", "rejected"}:
        try:
            raw_text = raw_response.decode("utf-8")
        except UnicodeDecodeError:
            return _error_result(run_directory.name, fingerprint, "ledger_corrupt")
        attempt = replay_extraction_response(
            extraction_input=extraction_input, raw_response=raw_text,
            extractor_version=extractor_version, generated_at=generated_at,
        )
        if attempt.status != recorded_status:
            return _error_result(run_directory.name, fingerprint, "ledger_corrupt")
        return _result_from_attempt(
            run_directory.name, fingerprint, attempt, transport_calls=0, replayed=True
        )
    if recorded_status == "error" and isinstance(manifest.get("error_code"), str):
        return _error_result(
            run_directory.name, fingerprint, manifest["error_code"], replayed=True,
            raw_response_sha256=_sha256(raw_response),
        )
    return _error_result(run_directory.name, fingerprint, "ledger_corrupt")


def run_extraction(
    *, run_id: str, ledger_root: str | os.PathLike[str],
    extraction_input: Mapping[str, Any], preview: ExtractionPreview,
    config: TransportConfig, generated_at: str, transport: ExtractionTransport,
    allow_external_send: bool, approved_consent_digest: str | None,
) -> ExtractionRunResult:
    """Execute at most one consented transport call or replay an immutable prior run."""

    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id) is None:
        return _error_result(str(run_id), "", "unsafe_run_id")
    validate_extraction_input(extraction_input)
    if not isinstance(preview, ExtractionPreview):
        return _error_result(run_id, "", "invalid_preview")
    if not isinstance(config, TransportConfig):
        return _error_result(run_id, "", "invalid_transport_config")
    try:
        _safe_text(config.provider, "invalid_provider")
        _safe_text(config.model, "invalid_model")
        _safe_text(generated_at, "invalid_generated_at")
    except ValueError as error:
        return _error_result(run_id, "", str(error))
    if not validate_rfc3339(generated_at):
        return _error_result(run_id, "", "invalid_generated_at")
    if (
        not isinstance(config.timeout_seconds, (int, float))
        or isinstance(config.timeout_seconds, bool)
        or config.timeout_seconds <= 0
    ):
        return _error_result(run_id, "", "invalid_timeout")
    preview_envelope = preview.envelope
    replay_redactor = (
        None
        if preview.redaction.transform_version == "none.v1"
        else lambda _: preview_envelope["source"]["content"]
    )
    expected_preview = build_extraction_preview(
        extraction_input=extraction_input, extractor_version=preview.extractor_version,
        prompt_version=preview.prompt_version, config=config,
        redactor=replay_redactor,
        redaction_version=preview.redaction.transform_version,
    )
    if expected_preview.outbound_sha256 != preview.outbound_sha256:
        return _error_result(run_id, "", "preview_input_mismatch")
    fingerprint = _request_fingerprint(preview, config, generated_at)
    resolved_root, root_error = _validate_ledger_root(Path(ledger_root))
    if root_error:
        return _error_result(run_id, fingerprint, root_error)
    run_directory = resolved_root / run_id
    if run_directory.exists() or run_directory.is_symlink():
        return _load_replay(
            run_directory, fingerprint=fingerprint, extraction_input=extraction_input,
            extractor_version=preview.extractor_version, generated_at=generated_at,
        )
    if allow_external_send is not True:
        return _error_result(run_id, fingerprint, "external_send_not_allowed")
    if approved_consent_digest is None:
        return _error_result(run_id, fingerprint, "consent_required")
    if approved_consent_digest != preview.consent_digest:
        return _error_result(run_id, fingerprint, "consent_digest_mismatch")

    raw_response = b""
    metadata: dict[str, Any] = {
        "model": config.model, "provider": config.provider, "request_id": None, "usage": None
    }
    error_code = None
    attempt = None
    try:
        response = transport(preview.envelope, config)
        if not isinstance(response, TransportResponse) or not isinstance(response.raw_response, bytes):
            raise TransportFailure("transport_error")
        raw_response = response.raw_response
        metadata = {
            "model": response.model, "provider": response.provider,
            "request_id": response.request_id,
            "usage": dict(response.usage) if response.usage is not None else None,
        }
        if response.provider != config.provider or response.model != config.model:
            error_code = "transport_metadata_mismatch"
        else:
            try:
                raw_text = raw_response.decode("utf-8")
            except UnicodeDecodeError:
                error_code = "invalid_response_utf8"
            else:
                attempt = replay_extraction_response(
                    extraction_input=extraction_input, raw_response=raw_text,
                    extractor_version=preview.extractor_version, generated_at=generated_at,
                )
    except TimeoutError:
        error_code = "timeout"
    except TransportFailure as error:
        error_code = error.code
    except Exception:
        error_code = "transport_error"

    status = attempt.status if attempt is not None else "error"
    response_hash = _sha256(raw_response)
    manifest = {
        "adapter_version": RUN_ADAPTER_VERSION,
        "error_code": error_code if attempt is None else (attempt.rejection.code if attempt.rejection else None),
        "extractor_version": preview.extractor_version, "generated_at": generated_at,
        "model": metadata["model"], "outbound_sha256": preview.outbound_sha256,
        "prompt_version": preview.prompt_version, "provider": metadata["provider"],
        "raw_response_sha256": response_hash,
        "redaction_version": preview.redaction.transform_version,
        "request_fingerprint": fingerprint, "request_id": metadata["request_id"],
        "run_id": run_id, "schema_version": "kgnote.extraction-run-manifest.v1",
        "status": status, "usage": metadata["usage"],
    }
    try:
        _persist_run(
            resolved_root, run_id, preview._envelope_json.encode("utf-8"),
            raw_response, manifest,
        )
    except (OSError, ValueError, TypeError):
        return _error_result(
            run_id, fingerprint, "ledger_write_failed", transport_calls=1,
            raw_response_sha256=response_hash,
        )
    if attempt is not None:
        return _result_from_attempt(run_id, fingerprint, attempt, transport_calls=1)
    return _error_result(
        run_id, fingerprint, error_code or "provider_error", transport_calls=1,
        raw_response_sha256=response_hash,
    )
