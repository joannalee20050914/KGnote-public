"""Append-only persistence for one Guided Map linking-phrase retrieval."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from kgnote.contracts.guided_map import GuidedMapValidationError, validate_guided_map_read_model


GUIDED_REVIEW_REQUEST_VERSION = "kgnote.guided-review-request.v1"
GUIDED_REVIEW_RECORD_VERSION = "kgnote.guided-review-interaction.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "guided-review" / "v1"


def _validator(name: str) -> Draft202012Validator:
    with (SCHEMA_ROOT / name).open(encoding="utf-8") as handle:
        return Draft202012Validator(json.load(handle), format_checker=FormatChecker())


_REQUEST_VALIDATOR = _validator("request.schema.json")
_RECORD_VALIDATOR = _validator("record.schema.json")


@dataclass(frozen=True, repr=False)
class GuidedReviewResult:
    status: Literal["ready", "recorded", "unchanged", "rejected"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: dict[str, Any] | None = None, problem: str | None = None) -> GuidedReviewResult:
    return GuidedReviewResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _schema_valid(validator: Draft202012Validator, payload: Any) -> bool:
    return isinstance(payload, Mapping) and not any(validator.iter_errors(payload))


def _normalize(value: str) -> str:
    return " ".join(value.strip().split())


def _proposition(model: Mapping[str, Any], edge_id: str) -> Mapping[str, Any] | None:
    return next((item for item in model["propositions"] if item["edge_id"] == edge_id), None)


def build_guided_review_prompt(model: Mapping[str, Any], edge_id: str) -> GuidedReviewResult:
    """Reconstruct the exercise entirely from one trusted Guided Map read model."""

    try:
        validate_guided_map_read_model(model)
    except (GuidedMapValidationError, TypeError):
        return _result("rejected", problem="invalid_guided_map")
    if not isinstance(edge_id, str):
        return _result("rejected", problem="invalid_edge")
    item = _proposition(model, edge_id)
    if item is None:
        return _result("rejected", problem="unknown_edge")
    evidence = {record["id"]: record for record in model["evidence"]}
    phrase = item["linking_phrase"]
    return _result("ready", {
        "schema_version": "kgnote.guided-review-prompt.v1",
        "learning_unit_id": model["learning_unit"]["id"],
        "source_id": model["source"]["id"],
        "graph_snapshot_sha256": model["graph_snapshot_sha256"],
        "edge_id": item["edge_id"],
        "question": f"請補上關係詞：「{item['subject_label']} ＿＿＿＿ {item['object_label']}」。",
        "hint": f"第一個字是「{phrase[0]}」，共 {len(phrase)} 個字。",
        "canonical_sentence": f"{item['subject_label']} {phrase} {item['object_label']}",
        "evidence": [evidence[evidence_id] for evidence_id in item["evidence_ids"]],
    })


def validate_guided_review_record(record: Mapping[str, Any]) -> bool:
    return _schema_valid(_RECORD_VALIDATOR, record)


def append_guided_review(
    review_root: str | os.PathLike[str],
    model: Mapping[str, Any],
    request: Any,
    *,
    recorded_at: str | None = None,
) -> GuidedReviewResult:
    """Validate context and atomically append one evidence-bound Edge review."""

    if not _schema_valid(_REQUEST_VALIDATOR, request):
        return _result("rejected", problem="invalid_request")
    prompt = build_guided_review_prompt(model, request["edge_id"])
    if prompt.status != "ready":
        return prompt
    expected = prompt.payload
    bound_fields = ("learning_unit_id", "source_id", "graph_snapshot_sha256", "edge_id")
    if any(request[field] != expected[field] for field in bound_fields):
        return _result("rejected", problem="stale_guided_review")

    timestamp = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return _result("rejected", problem="invalid_recorded_at")
    proposition = _proposition(model, request["edge_id"])
    assert proposition is not None
    evidence = {record["id"]: record for record in model["evidence"]}
    response = request["response"].strip()
    identity = json.dumps({**request, "response": response, "recorded_at": timestamp}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    review_id = "review_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    record = {
        "schema_version": GUIDED_REVIEW_RECORD_VERSION,
        "id": review_id,
        "type": "review_interaction",
        "learning_unit_id": model["learning_unit"]["id"],
        "source_ids": [model["source"]["id"]],
        "concept_ids": sorted([proposition["subject_concept_id"], proposition["object_concept_id"]]),
        "edge_ids": [proposition["edge_id"]],
        "evidence_ids": list(proposition["evidence_ids"]),
        "evidence_locators": [evidence[item]["locator"] for item in proposition["evidence_ids"]],
        "graph_snapshot_sha256": model["graph_snapshot_sha256"],
        "prompt_stage": "linking_phrase_retrieval",
        "question": expected["question"],
        "response": response,
        "hint_used": request["hint_used"],
        "comparison": "matched_reviewed_phrase" if _normalize(response) == _normalize(proposition["linking_phrase"]) else "different_from_reviewed_phrase",
        "canonical_proposition": {
            key: proposition[key] for key in (
                "subject_concept_id", "subject_label", "linking_phrase", "object_concept_id", "object_label", "canonical_relation"
            )
        },
        "view_context": {"view": "guided_map", "focus_question": model["learning_unit"]["focus_question"]},
        "occurred_at": timestamp,
        "reviewer_version": "human-phrase-comparison.v1",
        "recorded_at": timestamp,
    }
    if not validate_guided_review_record(record):
        return _result("rejected", problem="invalid_record")

    root = Path(review_root)
    if root.is_symlink() or not root.exists() or not root.is_dir():
        return _result("rejected", problem="unsafe_review_root")
    directory = root / "reviews"
    if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
        return _result("rejected", problem="unsafe_reviews_directory")
    try:
        directory.mkdir(mode=0o700, exist_ok=True)
    except OSError:
        return _result("rejected", problem="review_write_failed")
    target = directory / f"{review_id}.md"
    front_matter = yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=4096)
    content = f"---\n{front_matter}---\n\n# 關係提取練習 · {proposition['subject_label']} → {proposition['object_label']}\n".encode("utf-8")
    if target.exists():
        try:
            existing = target.read_bytes()
        except OSError:
            return _result("rejected", problem="review_read_failed")
        return _result("unchanged" if existing == content else "rejected", {"review_id": review_id}, None if existing == content else "review_id_conflict")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{review_id}.", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except OSError:
        return _result("rejected", problem="review_write_failed")
    finally:
        temporary.unlink(missing_ok=True)
    return _result("recorded", {"review_id": review_id, "recorded_at": timestamp, "comparison": record["comparison"]})


__all__ = [
    "GUIDED_REVIEW_RECORD_VERSION", "GUIDED_REVIEW_REQUEST_VERSION", "GuidedReviewResult",
    "append_guided_review", "build_guided_review_prompt", "validate_guided_review_record",
]
