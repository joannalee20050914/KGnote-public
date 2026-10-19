"""Human accept/correct/reject promotion for pending linking-phrase candidates."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from kgnote.contracts.linking_phrase import GENERIC_PHRASES


SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "schemas/linking-phrase/v1"
REVIEWER_VERSION = "human-linking-phrase-review.v1"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_ROOT / name).read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


_CANDIDATE_SET = _validator("candidate-set.schema.json")
_DECISIONS = _validator("decisions.schema.json")
_REVIEWED_SET = _validator("reviewed-set.schema.json")


def _bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _valid(validator: Draft202012Validator, value: Any) -> bool:
    return isinstance(value, Mapping) and not any(validator.iter_errors(value))


def _safe_stage(ledger_root: str | os.PathLike[str], run_id: str) -> Path | None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id) is None:
        return None
    root = Path(ledger_root)
    if root.is_symlink() or not root.is_dir():
        return None
    run = root / run_id
    if run.is_symlink() or not run.is_dir():
        return None
    stage = run / "linking-phrase"
    if stage.is_symlink() or not stage.is_dir():
        return None
    return stage


@dataclass(frozen=True, repr=False)
class PhraseReviewPreview:
    payload: Mapping[str, Any] = field(repr=False)
    approval_digest: str


def build_phrase_review_preview(
    candidate_set: Mapping[str, Any], decisions: Any, *, reviewed_at: str,
) -> PhraseReviewPreview:
    """Bind one complete human decision set to one immutable candidate set."""

    if not _valid(_CANDIDATE_SET, candidate_set) or not _valid(_DECISIONS, decisions):
        raise ValueError("invalid_phrase_decisions")
    if decisions["candidate_set_id"] != candidate_set["id"]:
        raise ValueError("invalid_phrase_decisions")

    by_id = {item["edge_id"]: item for item in candidate_set["candidates"]}
    if len(by_id) != len(candidate_set["candidates"]):
        raise ValueError("invalid_candidate_set")
    seen: set[str] = set()
    reviewed: list[dict[str, Any]] = []
    counts = {"accepted": 0, "corrected": 0, "rejected": 0, "guided_map_ready": 0}

    for decision in decisions["decisions"]:
        edge_id = decision["edge_id"]
        action = decision["action"]
        if edge_id not in by_id or edge_id in seen:
            raise ValueError("invalid_phrase_decisions")
        seen.add(edge_id)
        candidate = by_id[edge_id]
        phrase = None
        if action == "accept":
            phrase = candidate["linking_phrase_candidate"]
            counts["accepted"] += 1
        elif action == "correct":
            phrase = decision["corrected_linking_phrase"].strip()
            if phrase.casefold() in GENERIC_PHRASES:
                raise ValueError("invalid_phrase_correction")
            counts["corrected"] += 1
        else:
            counts["rejected"] += 1

        evidence_statuses = list(candidate["evidence_review_statuses"])
        promotion_eligible = (
            action in {"accept", "correct"}
            and all(status in {"accepted", "corrected"} for status in evidence_statuses)
        )
        if promotion_eligible:
            counts["guided_map_ready"] += 1
        reviewed.append({
            "edge_id": edge_id,
            "action": action,
            "candidate_linking_phrase": candidate["linking_phrase_candidate"],
            "effective_linking_phrase": phrase,
            "subject_concept_id": candidate["subject_concept_id"],
            "object_concept_id": candidate["object_concept_id"],
            "evidence_ids": list(candidate["evidence_ids"]),
            "evidence_review_statuses": evidence_statuses,
            "guided_map_promotion_eligible": promotion_eligible,
        })

    if seen != set(by_id):
        raise ValueError("phrase_decision_set_mismatch")
    reviewed.sort(key=lambda item: item["edge_id"])
    payload = {
        "schema_version": "kgnote.linking-phrase-reviewed-set.v1",
        "candidate_set_id": candidate_set["id"],
        "graph_snapshot_sha256": candidate_set["graph_snapshot_sha256"],
        "reviewer_version": REVIEWER_VERSION,
        "reviewed_at": reviewed_at,
        "summary": counts,
        "decisions": reviewed,
    }
    if not _valid(_REVIEWED_SET, payload):
        raise ValueError("invalid_phrase_review")
    return PhraseReviewPreview(payload, _sha(_bytes(payload)))


def apply_phrase_review(
    ledger_root: str | os.PathLike[str], run_id: str,
    preview: PhraseReviewPreview, approved_digest: str | None,
) -> str:
    if approved_digest != preview.approval_digest:
        return "approval_required" if approved_digest is None else "approval_digest_mismatch"
    stage = _safe_stage(ledger_root, run_id)
    if stage is None:
        return "unsafe_phrase_ledger"
    target = stage / "reviewed-set.json"
    if target.is_symlink():
        return "unsafe_phrase_ledger"
    content = _bytes(preview.payload)
    if target.exists():
        try:
            return "unchanged" if target.is_file() and target.read_bytes() == content else "review_conflict"
        except OSError:
            return "review_read_failed"
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return "review_write_failed"
    return "recorded"


__all__ = [
    "PhraseReviewPreview",
    "apply_phrase_review",
    "build_phrase_review_preview",
]
