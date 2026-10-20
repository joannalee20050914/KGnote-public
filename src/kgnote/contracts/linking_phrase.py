"""Fail-closed staging adapter for learner-facing linking phrase proposals."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from jsonschema import Draft202012Validator, FormatChecker


CONTEXT_VERSION = "kgnote.linking-phrase-context.v1"
CANDIDATE_SET_VERSION = "kgnote.linking-phrase-candidate-set.v1"
SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "schemas/linking-phrase/v1"
GENERIC_PHRASES = frozenset({"related_to", "related to", "maps_to", "maps to", "相關", "有關", "對應", "關聯", "連結"})


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_ROOT / name).read_text()), format_checker=FormatChecker())


_CONTEXT = _validator("context.schema.json")
_RESPONSE = _validator("response.schema.json")
_CANDIDATE_SET = _validator("candidate-set.schema.json")


@dataclass(frozen=True, repr=False)
class LinkingPhraseCandidateResult:
    status: Literal["accepted", "rejected"]
    _payload_json: str | None = field(default=None, repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any] | None:
        return json.loads(self._payload_json) if self._payload_json else None


def _result(status: str, payload: Mapping[str, Any] | None = None, code: str | None = None) -> LinkingPhraseCandidateResult:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if payload else None
    return LinkingPhraseCandidateResult(status, encoded, code)


def _valid(validator: Draft202012Validator, value: Any) -> bool:
    return isinstance(value, Mapping) and not any(validator.iter_errors(value))


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def validate_linking_phrase_context(context: Any) -> None:
    """Validate trusted context before it can be previewed or sent."""

    if not _valid(_CONTEXT, context):
        raise ValueError("invalid_context")
    edge_ids = [item["edge_id"] for item in context["edges"]]
    if edge_ids != sorted(edge_ids) or len(edge_ids) != len(set(edge_ids)):
        raise ValueError("non_deterministic_context")
    for edge in context["edges"]:
        evidence_ids = [item["id"] for item in edge["evidence"]]
        if evidence_ids != sorted(evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("non_deterministic_context")
        for evidence in edge["evidence"]:
            if evidence["locator"]["kind"] == "line_range":
                match = re.fullmatch(r"L([1-9][0-9]*)-L([1-9][0-9]*)", evidence["locator"]["value"])
                numbers = [line["number"] for line in evidence["source_excerpt"]]
                if match is None or numbers != list(range(int(match.group(1)), int(match.group(2)) + 1)):
                    raise ValueError("evidence_excerpt_drift")


def build_linking_phrase_candidates(
    context: Any, raw_response: str, *, provider: str, model: str,
    prompt_version: str, generated_at: str,
) -> LinkingPhraseCandidateResult:
    """Bind untrusted phrase-only proposals to trusted Edge and Evidence context."""

    try:
        validate_linking_phrase_context(context)
    except ValueError as error:
        return _result("rejected", code=str(error))
    edge_ids = [item["edge_id"] for item in context["edges"]]
    try:
        response = json.loads(raw_response, object_pairs_hook=_strict_object, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")))
    except (TypeError, UnicodeError, ValueError, json.JSONDecodeError):
        return _result("rejected", code="invalid_json")
    if not _valid(_RESPONSE, response):
        return _result("rejected", code="invalid_response")
    proposals = response["proposals"]
    proposal_ids = [item["edge_id"] for item in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        return _result("rejected", code="duplicate_edge_proposal")
    if set(proposal_ids) != set(edge_ids):
        return _result("rejected", code="proposal_set_mismatch")
    if any(item["linking_phrase"].strip().casefold() in GENERIC_PHRASES for item in proposals):
        return _result("rejected", code="generic_linking_phrase")
    if not all(isinstance(value, str) and value.strip() for value in (provider, model, prompt_version)):
        return _result("rejected", code="invalid_provenance")
    try:
        dt.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return _result("rejected", code="invalid_generated_at")
    by_edge = {item["edge_id"]: item for item in proposals}
    candidates = []
    for edge in context["edges"]:
        candidates.append({
            "edge_id": edge["edge_id"], "subject_concept_id": edge["subject_concept_id"],
            "subject_label": edge["subject_label"], "canonical_relation": edge["canonical_relation"],
            "linking_phrase_candidate": by_edge[edge["edge_id"]]["linking_phrase"].strip(),
            "object_concept_id": edge["object_concept_id"], "object_label": edge["object_label"],
            "evidence_ids": [item["id"] for item in edge["evidence"]],
            "evidence_locators": [item["locator"] for item in edge["evidence"]], "review_status": "pending",
            "evidence_review_statuses": [item["review_status"] for item in edge["evidence"]],
        })
    context_sha256 = hashlib.sha256(_canonical_bytes(context)).hexdigest()
    raw_response_sha256 = hashlib.sha256(raw_response.encode()).hexdigest()
    identity = json.dumps({"context_sha256": context_sha256, "raw_response_sha256": raw_response_sha256, "proposals": candidates, "provider": provider, "model": model, "prompt_version": prompt_version, "generated_at": generated_at}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload = {
        "schema_version": CANDIDATE_SET_VERSION,
        "id": "linking_phrase_candidates_" + hashlib.sha256(identity.encode()).hexdigest(),
        "learning_unit_id": context["learning_unit_id"], "graph_snapshot_sha256": context["graph_snapshot_sha256"],
        "context_sha256": context_sha256, "raw_response_sha256": raw_response_sha256,
        "display_locale": context["display_locale"], "focus_question": context["focus_question"],
        "provider": provider, "model": model, "prompt_version": prompt_version, "generated_at": generated_at,
        "candidates": candidates,
    }
    if not _valid(_CANDIDATE_SET, payload):
        return _result("rejected", code="invalid_candidate_set")
    return _result("accepted", payload)


__all__ = [
    "CANDIDATE_SET_VERSION", "CONTEXT_VERSION", "LinkingPhraseCandidateResult",
    "build_linking_phrase_candidates", "validate_linking_phrase_context",
]
