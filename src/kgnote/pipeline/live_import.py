"""Consent-gated single-Markdown provider extraction through canonical dry-run."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from kgnote.extraction import (
    ExtractionPreview,
    ExtractionRunResult,
    ExtractionTransport,
    TransportConfig,
    build_extraction_preview,
    run_extraction,
)
from kgnote.ingestion import SourceMetadata, import_markdown_source
from kgnote.pipeline.offline_import import (
    OfflineImportPreview,
    build_candidate_import_preview,
)


LIVE_IMPORT_VERSION = "kgnote.live-import.v1"


@dataclass(frozen=True, repr=False)
class LiveImportPreview:
    pipeline_version: str
    extraction: ExtractionPreview
    _extraction_input: dict = field(repr=False)

    @property
    def extraction_input(self) -> dict:
        source = self._extraction_input["source"]
        return {"schema_version": self._extraction_input["schema_version"], "source": dict(source)}


@dataclass(frozen=True)
class LiveImportResult:
    status: Literal["planned", "rejected", "error"]
    extraction: ExtractionRunResult = field(repr=False)
    import_preview: OfflineImportPreview | None = field(default=None, repr=False)
    problem_code: str | None = None


def build_live_import_preview(
    *, source_path: str | os.PathLike[str], metadata: SourceMetadata,
    extractor_version: str, prompt_version: str, config: TransportConfig,
) -> LiveImportPreview:
    """Read one explicit Markdown file and build its exact outbound preview."""

    extraction_input = import_markdown_source(source_path, metadata=metadata)
    extraction = build_extraction_preview(
        extraction_input=extraction_input,
        extractor_version=extractor_version,
        prompt_version=prompt_version,
        config=config,
    )
    return LiveImportPreview(
        pipeline_version=LIVE_IMPORT_VERSION,
        extraction=extraction,
        _extraction_input=extraction_input,
    )


def run_live_import(
    *, preview: LiveImportPreview, run_id: str,
    ledger_root: str | os.PathLike[str], store_root: str | os.PathLike[str],
    config: TransportConfig, generated_at: str, transport: ExtractionTransport,
    allow_external_send: bool, approved_consent_digest: str | None,
) -> LiveImportResult:
    """Run at most one extraction request, then produce a no-write canonical preview."""

    if not isinstance(preview, LiveImportPreview):
        raise ValueError("invalid_live_import_preview")
    extraction = run_extraction(
        run_id=run_id,
        ledger_root=ledger_root,
        extraction_input=preview._extraction_input,
        preview=preview.extraction,
        config=config,
        generated_at=generated_at,
        transport=transport,
        allow_external_send=allow_external_send,
        approved_consent_digest=approved_consent_digest,
    )
    if extraction.status != "accepted":
        return LiveImportResult(
            status=extraction.status,
            extraction=extraction,
            problem_code=extraction.problem.code if extraction.problem else "extraction_failed",
        )
    import_preview = build_candidate_import_preview(
        extraction_input=preview._extraction_input,
        candidate_result=extraction.candidate_result,
        generated_at=generated_at,
        store_root=store_root,
    )
    if import_preview.status != "planned":
        return LiveImportResult(
            status="rejected",
            extraction=extraction,
            import_preview=import_preview,
            problem_code=import_preview.problem_code,
        )
    return LiveImportResult(
        status="planned", extraction=extraction, import_preview=import_preview
    )
