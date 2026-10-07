"""Snapshot-bound practice planning and post-submit answer reveal."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


PRACTICE_SET_VERSION = "kgnote.practice-set.v1"
OVERLAY_VERSION = "kgnote.claim-review-overlay.v1"


@dataclass(frozen=True, repr=False)
class PracticeResult:
    status: Literal["ready", "rejected"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> PracticeResult:
    return PracticeResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def proposition_digest(proposition: Mapping[str, Any]) -> str:
    value = {key: proposition[key] for key in ("subject_concept_id", "linking_phrase", "object_concept_id", "evidence_ids")}
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _review_index(model: Mapping[str, Any], overlay: Any) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(overlay, Mapping) or overlay.get("schema_version") != OVERLAY_VERSION:
        return None
    if overlay.get("learning_unit_id") != model.get("learning_unit", {}).get("id") or overlay.get("graph_snapshot_sha256") != model.get("graph_snapshot_sha256"):
        return None
    reviews = overlay.get("reviews")
    if not isinstance(reviews, list):
        return None
    index: dict[str, Mapping[str, Any]] = {}
    required = {"claim_id", "claim_revision", "proposition_sha256", "source_support", "factual_status", "teaching_answer_status", "reason"}
    for review in reviews:
        if not isinstance(review, Mapping) or set(review) != required or review["claim_id"] in index:
            return None
        if not isinstance(review["claim_revision"], int) or review["claim_revision"] < 1:
            return None
        if review["source_support"] not in {"supported", "unsupported", "unknown"}:
            return None
        if review["factual_status"] not in {"unreviewed", "needs_revision", "verified", "corrected", "rejected", "insufficient_evidence"}:
            return None
        if review["teaching_answer_status"] not in {"candidate", "ready", "blocked", "retired"}:
            return None
        index[review["claim_id"]] = review
    return index


def build_practice_set(model: Mapping[str, Any], overlay: Any, supplement: Any = None) -> PracticeResult:
    """Return prompts and provenance only; canonical answers remain server-side."""
    index = _review_index(model, overlay)
    if index is None:
        return _result("rejected", problem="invalid_or_stale_claim_review_overlay")
    evidence = {item["id"]: item for item in model.get("evidence", [])}
    items: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for proposition in model.get("propositions", []):
        review = index.get(proposition.get("edge_id"))
        if review is None or review["proposition_sha256"] != proposition_digest(proposition):
            blocked.append({"claim_id": proposition.get("edge_id"), "reason": "缺少或不符合目前版本的審查。"})
            continue
        if review["factual_status"] not in {"verified", "corrected"} or review["teaching_answer_status"] != "ready":
            blocked.append({"claim_id": proposition["edge_id"], "reason": review["reason"]})
            continue
        common = {
            "revision": review["claim_revision"],
            "learning_unit_id": model["learning_unit"]["id"],
            "claim_ref": {"claim_id": proposition["edge_id"], "revision": review["claim_revision"]},
            "source_refs": [model["source"]["id"]],
            "evidence_refs": list(proposition["evidence_ids"]),
            "required_context": {"subject": proposition["subject_label"], "object": proposition["object_label"]},
        }
        items.append({
            **common,
            "item_id": f"item_relation_{proposition['edge_id']}",
            "activity_type": "relation_recall",
            "label": f"{proposition['subject_label']} → {proposition['object_label']}",
            "prompt": f"請補上一個合理的關係：{proposition['subject_label']} ＿＿＿＿ {proposition['object_label']}",
            "hint": f"想想「{proposition['subject_label']}」如何影響或連到「{proposition['object_label']}」。不必逐字相同。",
        })
        items.append({
            **common,
            "item_id": f"item_explain_{proposition['edge_id']}",
            "activity_type": "free_explanation",
            "label": f"解釋：{proposition['subject_label']} × {proposition['object_label']}",
            "prompt": f"請用自己的話解釋「{proposition['subject_label']}」與「{proposition['object_label']}」的關係。",
            "hint": "可以說明方向、發生條件，以及這個關係為什麼重要。",
        })
    if supplement is not None:
        if not isinstance(supplement, Mapping) or supplement.get("schema_version") != "kgnote.practice-supplement.v1" or supplement.get("learning_unit_id") != model["learning_unit"]["id"] or not isinstance(supplement.get("items"), list):
            return _result("rejected", problem="invalid_practice_supplement")
        ready_claims = {item["claim_ref"]["claim_id"]: item["claim_ref"]["revision"] for item in items}
        ready_evidence = {
            proposition["edge_id"]: set(proposition["evidence_ids"])
            for proposition in model.get("propositions", [])
            if proposition.get("edge_id") in ready_claims
        }
        known_evidence = set(evidence)
        known_item_ids = {item["item_id"] for item in items}
        for supplied in supplement["items"]:
            required = {"item_id", "revision", "activity_type", "label", "prompt", "hint", "claim_ref", "source_refs", "evidence_refs", "canonical_answer", "rubric"}
            if not isinstance(supplied, Mapping) or set(supplied) != required or supplied["activity_type"] not in {"application_prediction", "distinction"}:
                return _result("rejected", problem="invalid_practice_supplement")
            claim_ref = supplied["claim_ref"]
            if ready_claims.get(claim_ref.get("claim_id")) != claim_ref.get("revision"):
                return _result("rejected", problem="supplement_claim_not_ready")
            item_id = supplied.get("item_id")
            evidence_refs = supplied.get("evidence_refs")
            if not isinstance(item_id, str) or not item_id or item_id in known_item_ids:
                return _result("rejected", problem="duplicate_practice_item_id")
            if supplied.get("source_refs") != [model["source"]["id"]]:
                return _result("rejected", problem="invalid_practice_supplement")
            if (
                not isinstance(evidence_refs, list)
                or not evidence_refs
                or any(not isinstance(value, str) for value in evidence_refs)
                or not set(evidence_refs) <= known_evidence
                or not set(evidence_refs) <= ready_evidence.get(claim_ref["claim_id"], set())
            ):
                return _result("rejected", problem="supplement_evidence_not_ready")
            if not isinstance(supplied.get("canonical_answer"), str) or not supplied["canonical_answer"].strip():
                return _result("rejected", problem="invalid_practice_supplement")
            if not isinstance(supplied.get("rubric"), list) or not supplied["rubric"] or any(
                not isinstance(row, str) or not row.strip() for row in supplied["rubric"]
            ):
                return _result("rejected", problem="invalid_practice_supplement")
            known_item_ids.add(item_id)
            items.append({key: json.loads(json.dumps(supplied[key], ensure_ascii=False)) for key in ("item_id", "revision", "activity_type", "label", "prompt", "hint", "claim_ref", "source_refs", "evidence_refs") } | {
                "learning_unit_id": model["learning_unit"]["id"], "required_context": {},
            })
    return _result("ready", {
        "schema_version": PRACTICE_SET_VERSION,
        "learning_unit_id": model["learning_unit"]["id"],
        "source": {"id": model["source"]["id"], "label": model["source"]["label"]},
        "items": items,
        "blocked_claims": blocked,
    })


def reveal_practice_answer(model: Mapping[str, Any], overlay: Any, item_id: str, supplement: Any = None) -> PracticeResult:
    practice = build_practice_set(model, overlay, supplement)
    if practice.status != "ready":
        return practice
    item = next((candidate for candidate in practice.payload["items"] if candidate["item_id"] == item_id), None)
    if item is None:
        return _result("rejected", problem="unknown_or_blocked_practice_item")
    if supplement is not None:
        supplied = next((candidate for candidate in supplement.get("items", []) if candidate.get("item_id") == item_id), None)
        if supplied is not None:
            evidence_index = {candidate["id"]: candidate for candidate in model["evidence"]}
            return _result("ready", {"item_id": item_id, "canonical_answer": supplied["canonical_answer"], "rubric": supplied["rubric"], "evidence": [evidence_index[evidence_id] for evidence_id in supplied["evidence_refs"]], "feedback": "請依 rubric 比較自己的推理；合理同義說法不要求逐字匹配。"})
    edge_id = item["claim_ref"]["claim_id"]
    proposition = next(candidate for candidate in model["propositions"] if candidate["edge_id"] == edge_id)
    evidence_index = {candidate["id"]: candidate for candidate in model["evidence"]}
    return _result("ready", {
        "item_id": item_id,
        "canonical_answer": f"{proposition['subject_label']} {proposition['linking_phrase']} {proposition['object_label']}",
        "rubric": [
            "方向與兩個概念的角色是否正確",
            "是否說出關係成立的機制或條件",
            "用詞可不同，不要求逐字匹配",
        ],
        "evidence": [evidence_index[evidence_id] for evidence_id in proposition["evidence_ids"]],
        "feedback": "請依方向、角色與條件比較；不同措辭不等於答錯。若答案省略關鍵條件，可標為 PARTIAL 後再試一次。",
    })


def validate_attempt_against_practice_set(model: Mapping[str, Any], overlay: Any, request: Mapping[str, Any], supplement: Any = None) -> str | None:
    practice = build_practice_set(model, overlay, supplement)
    if practice.status != "ready":
        return "practice_set_unavailable"
    item = next((candidate for candidate in practice.payload["items"] if candidate["item_id"] == request.get("review_item_id")), None)
    if item is None:
        return "unknown_or_blocked_practice_item"
    checks = (
        request.get("item_revision") == item["revision"],
        request.get("learning_unit_id") == item["learning_unit_id"],
        request.get("activity_type") == item["activity_type"],
        request.get("source_refs") == item["source_refs"],
        request.get("claim_refs") == [item["claim_ref"]],
        request.get("evidence_refs") == item["evidence_refs"],
    )
    return None if all(checks) else "stale_practice_item"


__all__ = [
    "OVERLAY_VERSION", "PRACTICE_SET_VERSION", "PracticeResult", "build_practice_set",
    "proposition_digest", "reveal_practice_answer", "validate_attempt_against_practice_set",
]
