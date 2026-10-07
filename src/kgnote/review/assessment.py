"""Pure one-question/one-answer reviewer prompt and offline response contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .context import REVIEWER_CONTEXT_VERSION


ASSESSMENT_PROMPT_VERSION = "kgnote.review-assessment-prompt.v1"
ASSESSMENT_RESPONSE_VERSION = "kgnote.review-assessment-response.v1"
OUTCOMES = {"CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_text(value: Any, code: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(code)
    return value


def _validate_context(context: Any) -> None:
    required = {
        "schema_version", "snapshot_sha256", "focus", "evidence", "sources",
        "neighborhood", "previous_confusion",
    }
    if not isinstance(context, Mapping) or set(context) != required:
        raise ValueError("invalid_reviewer_context")
    if context.get("schema_version") != REVIEWER_CONTEXT_VERSION:
        raise ValueError("invalid_reviewer_context")
    if re.fullmatch(r"[a-f0-9]{64}", str(context.get("snapshot_sha256"))) is None:
        raise ValueError("invalid_reviewer_context")
    focus = context.get("focus")
    if not isinstance(focus, Mapping) or focus.get("kind") != "concept":
        raise ValueError("invalid_reviewer_context")
    if not all(isinstance(context.get(name), list) for name in ("evidence", "sources")):
        raise ValueError("invalid_reviewer_context")
    if not isinstance(context.get("neighborhood"), Mapping) or not isinstance(context.get("previous_confusion"), Mapping):
        raise ValueError("invalid_reviewer_context")


@dataclass(frozen=True, repr=False)
class AssessmentPrompt:
    prompt_version: str
    prompt_sha256: str
    concept_id: str
    snapshot_sha256: str
    _envelope_json: str = field(repr=False)

    @property
    def envelope(self) -> dict[str, Any]:
        return json.loads(self._envelope_json)

    def __repr__(self) -> str:
        return (
            f"AssessmentPrompt(prompt_version={self.prompt_version!r}, "
            f"prompt_sha256={self.prompt_sha256!r}, concept_id={self.concept_id!r}, "
            f"snapshot_sha256={self.snapshot_sha256!r})"
        )


@dataclass(frozen=True)
class AssessmentProblem:
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class AssessmentResult:
    status: Literal["accepted", "rejected"]
    raw_response_sha256: str
    _assessment_json: str | None = field(default=None, repr=False)
    problem: AssessmentProblem | None = None

    @property
    def assessment(self) -> dict[str, Any] | None:
        return json.loads(self._assessment_json) if self._assessment_json else None

    def __repr__(self) -> str:
        return f"AssessmentResult(status={self.status!r}, raw_response_sha256={self.raw_response_sha256!r}, problem={self.problem!r})"


def build_assessment_prompt(
    *, context: Mapping[str, Any], question: str, answer: str,
    hint_used: bool, reviewer_version: str,
) -> AssessmentPrompt:
    """Build exact model input without transport, persistence, clock, or canonical mutation."""

    _validate_context(context)
    question = _safe_text(question, "invalid_question", 1000)
    answer = _safe_text(answer, "invalid_answer", 4000)
    reviewer_version = _safe_text(reviewer_version, "invalid_reviewer_version", 128)
    if not isinstance(hint_used, bool):
        raise ValueError("invalid_hint_used")
    envelope = {
        "schema_version": ASSESSMENT_PROMPT_VERSION,
        "reviewer_version": reviewer_version,
        "instruction": (
            "Judge only from the supplied evidence. Return exactly one outcome from "
            "CORRECT, PARTIAL, INCORRECT, INSUFFICIENT_EVIDENCE and a correction of at most two sentences. "
            "Do not infer mastery or understanding."
        ),
        "context": context,
        "question": question,
        "answer": answer,
        "hint_used": hint_used,
        "response_contract": {
            "schema_version": ASSESSMENT_RESPONSE_VERSION,
            "fields": ["outcome", "correction"],
            "max_correction_sentences": 2,
        },
    }
    encoded = _canonical_json(envelope)
    return AssessmentPrompt(
        ASSESSMENT_PROMPT_VERSION,
        hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        context["focus"]["id"], context["snapshot_sha256"], encoded,
    )


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?。！？]+[.!?。！？]+|[^.!?。！？]+$", text.strip())) if text.strip() else 0


def replay_assessment_response(raw_response: str | bytes) -> AssessmentResult:
    """Strictly validate a mock/provider response without model or filesystem access."""

    raw = raw_response.encode("utf-8") if isinstance(raw_response, str) else raw_response
    if not isinstance(raw, bytes):
        raw = b""
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return AssessmentResult("rejected", digest, problem=AssessmentProblem("invalid_json"))
    if not isinstance(payload, dict) or set(payload) != {"outcome", "correction"}:
        return AssessmentResult("rejected", digest, problem=AssessmentProblem("invalid_response_fields"))
    if payload["outcome"] not in OUTCOMES:
        return AssessmentResult("rejected", digest, problem=AssessmentProblem("invalid_outcome", ("outcome",)))
    correction = payload["correction"]
    if not isinstance(correction, str) or len(correction) > 500 or _sentence_count(correction) > 2:
        return AssessmentResult("rejected", digest, problem=AssessmentProblem("invalid_correction", ("correction",)))
    accepted = {"outcome": payload["outcome"], "correction": correction}
    return AssessmentResult("accepted", digest, _assessment_json=_canonical_json(accepted))
