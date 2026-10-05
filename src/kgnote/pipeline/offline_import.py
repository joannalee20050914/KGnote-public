"""Explicit-path offline replay through approved canonical apply and read-back."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from kgnote.extraction import replay_extraction_response
from kgnote.ingestion import SourceMetadata, import_markdown_source
from kgnote.normalization import normalize_candidate_result
from kgnote.planning import DryRunPlan, plan_dry_run
from kgnote.storage import (
    ApplyResult,
    StoreSnapshot,
    apply_approved_plan,
    plan_digest,
    read_canonical_store,
)


OFFLINE_IMPORT_VERSION = "kgnote.offline-import.v1"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True, repr=False)
class OfflineImportPreview:
    status: Literal["planned", "rejected"]
    store_root: str
    source_id: str
    source_bytes: int
    source_sha256: str
    raw_relative_path: str
    plan: DryRunPlan
    approval_digest: str | None = None
    problem_code: str | None = None
    _source_bytes: bytes = field(default=b"", repr=False)

    def __repr__(self) -> str:
        return (
            "OfflineImportPreview("
            f"status={self.status!r}, store_root={self.store_root!r}, "
            f"source_id={self.source_id!r}, source_bytes={self.source_bytes!r}, "
            f"source_sha256={self.source_sha256!r}, raw_relative_path={self.raw_relative_path!r}, "
            f"approval_digest={self.approval_digest!r}, problem_code={self.problem_code!r})"
        )


@dataclass(frozen=True)
class OfflineImportApplyResult:
    status: Literal["applied", "rejected", "failed"]
    write_count: int = 0
    raw_write_count: int = 0
    canonical_result: ApplyResult | None = field(default=None, repr=False)
    audit_snapshot: StoreSnapshot | None = field(default=None, repr=False)
    problem_code: str | None = None


def _rejected(root: Path, source_id: str, code: str) -> OfflineImportPreview:
    return OfflineImportPreview(
        status="rejected", store_root=str(root), source_id=source_id,
        source_bytes=0, source_sha256="", raw_relative_path="", plan=DryRunPlan(status="rejected"),
        problem_code=code,
    )


def _source_record(extraction_input: dict[str, Any], registered_at: str) -> dict[str, Any]:
    source = extraction_input["source"]
    raw_name = source["id"].removeprefix("src_").replace("_", "-")
    return {
        "schema_version": "kgnote.v0.1",
        "id": source["id"],
        "type": "source",
        "source_kind": source["source_kind"],
        "title": source["title"],
        "uri_or_path": f"raw/{raw_name}.md",
        "content_sha256": source["content_sha256"],
        "captured_at": source["captured_at"],
        "registered_at": registered_at,
    }


def _locator_problem(candidate_result: Mapping[str, Any], content: str) -> str | None:
    line_count = len(content.splitlines())
    for collection in ("evidence", "learning_events"):
        items = candidate_result.get(collection)
        if not isinstance(items, list):
            return "source_locator_invalid"
        for item in items:
            locator = item.get("locator") if isinstance(item, Mapping) else None
            if not isinstance(locator, Mapping) or locator.get("kind") != "line_range":
                return "source_locator_invalid"
            match = re.fullmatch(r"L([1-9][0-9]*)-L([1-9][0-9]*)", str(locator.get("value", "")))
            if match is None:
                return "source_locator_invalid"
            start, end = map(int, match.groups())
            if start > end or end > line_count:
                return "source_locator_out_of_bounds"
    return None


def build_candidate_import_preview(
    *, extraction_input: Mapping[str, Any], candidate_result: Mapping[str, Any],
    generated_at: str, store_root: str | os.PathLike[str],
) -> OfflineImportPreview:
    """Plan canonical integration for an already validated provider candidate."""

    root = Path(store_root)
    try:
        source = extraction_input["source"]
        source_id = source["id"]
        source_bytes = source["content"].encode("utf-8")
    except (KeyError, TypeError, AttributeError, UnicodeError):
        return _rejected(root, "", "invalid_extraction_input")
    locator_problem = _locator_problem(candidate_result, source["content"])
    if locator_problem:
        return _rejected(root, source_id, locator_problem)
    normalized = normalize_candidate_result(candidate_result)
    if normalized.status != "normalized":
        return _rejected(root, source_id, f"normalization_{normalized.status}")
    snapshot = read_canonical_store(root)
    if snapshot.status != "loaded":
        return _rejected(root, source_id, f"store_{snapshot.problem.code}")
    raw_directory = root / "raw"
    if raw_directory.is_symlink() or not raw_directory.is_dir():
        return _rejected(root, source_id, "unsafe_raw_directory")
    source_record = _source_record(dict(extraction_input), generated_at)
    plan = plan_dry_run(normalized, snapshot.records, source_candidate=source_record)
    if plan.status != "planned":
        return _rejected(root, source_id, f"plan_{plan.problem.code}")
    raw_relative_path = source_record["uri_or_path"]
    raw_target = root / raw_relative_path
    if raw_target.is_symlink():
        return _rejected(root, source_id, "unsafe_raw_target")
    if raw_target.exists() and raw_target.read_bytes() != source_bytes:
        return _rejected(root, source_id, "raw_source_conflict")
    approval_payload = {
        "pipeline_version": OFFLINE_IMPORT_VERSION,
        "plan_digest": plan_digest(plan),
        "raw_relative_path": raw_relative_path,
        "source_sha256": _sha256(source_bytes),
        "store_root": snapshot.root,
    }
    approval_digest = _sha256(_canonical_json(approval_payload))
    return OfflineImportPreview(
        status="planned", store_root=snapshot.root, source_id=source_id,
        source_bytes=len(source_bytes), source_sha256=_sha256(source_bytes),
        raw_relative_path=raw_relative_path, plan=plan, approval_digest=approval_digest,
        _source_bytes=source_bytes,
    )


def build_offline_import_preview(
    *, source_path: str | os.PathLike[str], response_path: str | os.PathLike[str],
    metadata: SourceMetadata, extractor_version: str, generated_at: str,
    store_root: str | os.PathLike[str],
) -> OfflineImportPreview:
    """Read explicit inputs and produce a content-bound plan without writing."""

    root = Path(store_root)
    extraction_input = import_markdown_source(source_path, metadata=metadata)
    source_bytes = extraction_input["source"]["content"].encode("utf-8")
    response = Path(response_path)
    if response.is_symlink() or not response.is_file():
        return _rejected(root, metadata.source_id, "unsafe_response_path")
    try:
        raw_response = response.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return _rejected(root, metadata.source_id, "response_read_failed")
    attempt = replay_extraction_response(
        extraction_input=extraction_input, raw_response=raw_response,
        extractor_version=extractor_version, generated_at=generated_at,
    )
    if attempt.status != "accepted":
        return _rejected(root, metadata.source_id, f"response_{attempt.rejection.code}")
    return build_candidate_import_preview(
        extraction_input=extraction_input,
        candidate_result=attempt.candidate_result,
        generated_at=generated_at,
        store_root=root,
    )


def apply_offline_import(
    preview: OfflineImportPreview, *, approved_digest: str | None,
) -> OfflineImportApplyResult:
    """Apply the exact preview, including an immutable raw copy, then read back."""

    if preview.status != "planned":
        return OfflineImportApplyResult(status="rejected", problem_code="preview_not_planned")
    if approved_digest is None:
        return OfflineImportApplyResult(status="rejected", problem_code="approval_required")
    if approved_digest != preview.approval_digest:
        return OfflineImportApplyResult(status="rejected", problem_code="approval_digest_mismatch")
    root = Path(preview.store_root)
    snapshot = read_canonical_store(root)
    if snapshot.status != "loaded":
        return OfflineImportApplyResult(status="rejected", problem_code="store_changed")
    raw_target = root / preview.raw_relative_path
    if raw_target.is_symlink():
        return OfflineImportApplyResult(status="rejected", problem_code="unsafe_raw_target")
    raw_created = False
    try:
        if raw_target.exists():
            if raw_target.read_bytes() != preview._source_bytes:
                return OfflineImportApplyResult(status="rejected", problem_code="raw_source_conflict")
        else:
            descriptor = os.open(raw_target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(preview._source_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            raw_created = True
        canonical = apply_approved_plan(
            root, snapshot, preview.plan, plan_digest(preview.plan)
        )
        if canonical.status != "applied":
            if raw_created:
                raw_target.unlink()
            return OfflineImportApplyResult(
                status=canonical.status, raw_write_count=0,
                canonical_result=canonical, problem_code=canonical.problem.code,
            )
    except OSError:
        if raw_created:
            try:
                raw_target.unlink()
            except OSError:
                pass
        return OfflineImportApplyResult(status="failed", problem_code="raw_write_failed")
    audit = read_canonical_store(root)
    if audit.status != "loaded":
        return OfflineImportApplyResult(status="failed", problem_code="read_back_failed")
    raw_writes = 1 if raw_created else 0
    return OfflineImportApplyResult(
        status="applied", write_count=canonical.write_count + raw_writes,
        raw_write_count=raw_writes, canonical_result=canonical, audit_snapshot=audit,
    )
