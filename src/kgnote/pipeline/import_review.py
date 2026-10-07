"""Human-readable, source-grounded preview of one canonical import plan."""

from __future__ import annotations

import re
from typing import Any, Mapping

from kgnote.normalization import normalize_candidate_result
from kgnote.pipeline.offline_import import OfflineImportPreview


IMPORT_REVIEW_PREVIEW_VERSION = "kgnote.import-review-preview.v1"
LINKING_PHRASE_CONTEXT_VERSION = "kgnote.linking-phrase-context.v1"


def _excerpt(content: str, locator: Mapping[str, Any]) -> list[dict[str, Any]]:
    if locator.get("kind") != "line_range":
        raise ValueError("unsupported_review_locator")
    match = re.fullmatch(r"L([1-9][0-9]*)-L([1-9][0-9]*)", str(locator.get("value", "")))
    if match is None:
        raise ValueError("invalid_review_locator")
    start, end = map(int, match.groups())
    lines = content.splitlines()
    if start > end or end > len(lines):
        raise ValueError("review_locator_out_of_bounds")
    return [{"number": number, "text": lines[number - 1]} for number in range(start, end + 1)]


def build_import_review_preview(
    *, extraction_input: Mapping[str, Any], candidate_result: Mapping[str, Any],
    import_preview: OfflineImportPreview,
) -> dict[str, Any]:
    """Resolve one plan into names, directions, and exact source excerpts without I/O."""

    if not isinstance(import_preview, OfflineImportPreview) or import_preview.status != "planned":
        raise ValueError("import_preview_not_planned")
    try:
        source = extraction_input["source"]
        content = source["content"]
    except (KeyError, TypeError):
        raise ValueError("invalid_review_source") from None
    normalized = normalize_candidate_result(candidate_result)
    if normalized.status != "normalized":
        raise ValueError("review_candidate_not_normalized")
    records = normalized.records
    operations = {item["record_id"]: item["operation"] for item in import_preview.plan.items if item["record_id"]}
    concepts_by_id = {item["id"]: item for item in records["concepts"]}
    events_by_id = {item["id"]: item for item in records["learning_events"]}
    evidence_by_id = {item["id"]: item for item in records["evidence"]}

    concepts = [{
        "id": item["id"], "operation": operations[item["id"]], "name": item["canonical_name"],
        "aliases": item["aliases"], "summary": item["summary"], "evidence_ids": item["evidence_ids"],
    } for item in records["concepts"]]
    evidence = [{
        "id": item["id"], "operation": operations[item["id"]], "proposition": item["proposition"],
        "locator": item["locator"], "source_excerpt": _excerpt(content, item["locator"]),
    } for item in records["evidence"]]

    def endpoint(record_id: str) -> dict[str, str]:
        if record_id in concepts_by_id:
            return {"id": record_id, "label": concepts_by_id[record_id]["canonical_name"], "type": "concept"}
        event = events_by_id[record_id]
        return {"id": record_id, "label": event["context"], "type": "learning_event"}

    relationships = []
    for item in records["edges"]:
        excerpts = [{
            "evidence_id": evidence_id,
            "locator": evidence_by_id[evidence_id]["locator"]["value"],
            "lines": _excerpt(content, evidence_by_id[evidence_id]["locator"]),
        } for evidence_id in item["evidence_ids"]]
        relationships.append({
            "id": item["id"], "operation": operations[item["id"]], "edge_class": item["edge_class"],
            "subject": endpoint(item["source_id"]), "relation": item["relation"],
            "linking_phrase": None, "linking_phrase_status": "not_proposed",
            "object": endpoint(item["target_id"]), "evidence_ids": item["evidence_ids"],
            "source_excerpts": excerpts,
        })
    learning_events = [{
        "id": item["id"], "operation": operations[item["id"]], "event_type": item["event_type"],
        "context": item["context"], "concept_ids": item["concept_ids"], "evidence_ids": item["evidence_ids"],
    } for item in records["learning_events"]]
    blocking_items = [{
        "operation": item["operation"], "record_id": item["record_id"], "record_type": item["record_type"],
        "problem_code": (item["problem"] or {}).get("code", "blocked_operation"),
    } for item in import_preview.plan.items if item["operation"] in {"CONFLICT", "REJECT"}]
    conflicts = sum(item["operation"] == "CONFLICT" for item in import_preview.plan.items)
    rejects = sum(item["operation"] == "REJECT" for item in import_preview.plan.items)
    return {
        "schema_version": IMPORT_REVIEW_PREVIEW_VERSION,
        "source": {"id": source["id"], "title": source["title"], "content_sha256": source["content_sha256"], "line_count": len(content.splitlines())},
        "summary": {"concepts": len(concepts), "evidence": len(evidence), "relationships": len(relationships), "learning_events": len(learning_events), "conflicts": conflicts, "rejects": rejects, "apply_blocked": bool(blocking_items)},
        "concepts": concepts, "evidence": evidence, "relationships": relationships,
        "learning_events": learning_events, "blocking_items": blocking_items,
    }


def build_linking_phrase_context(review_preview: Mapping[str, Any], *, graph_snapshot_sha256: str) -> dict[str, Any]:
    """Project canonical Edge candidates into a phrase-only, source-grounded context."""

    if review_preview.get("schema_version") != IMPORT_REVIEW_PREVIEW_VERSION:
        raise ValueError("invalid_import_review_preview")
    if not isinstance(graph_snapshot_sha256, str) or len(graph_snapshot_sha256) != 64:
        raise ValueError("invalid_linking_phrase_snapshot")
    evidence = {item["id"]: item for item in review_preview["evidence"]}
    edges = []
    for relation in review_preview["relationships"]:
        if relation["edge_class"] != "canonical":
            continue
        supporting = []
        for evidence_id in relation["evidence_ids"]:
            item = evidence[evidence_id]
            supporting.append({
                "id": evidence_id, "source_id": review_preview["source"]["id"],
                "locator": item["locator"], "proposition": item["proposition"],
                "review_status": "unreviewed", "source_excerpt": item["source_excerpt"],
            })
        edges.append({
            "edge_id": relation["id"], "edge_class": "canonical",
            "subject_concept_id": relation["subject"]["id"], "subject_label": relation["subject"]["label"],
            "canonical_relation": relation["relation"],
            "object_concept_id": relation["object"]["id"], "object_label": relation["object"]["label"],
            "evidence": supporting,
        })
    if not edges:
        raise ValueError("no_canonical_edges_for_linking_phrase")
    edges.sort(key=lambda item: item["edge_id"])
    return {
        "schema_version": LINKING_PHRASE_CONTEXT_VERSION,
        "learning_unit_id": f"import_{review_preview['source']['id']}",
        "graph_snapshot_sha256": graph_snapshot_sha256,
        "display_locale": "und", "focus_question": f"{review_preview['source']['title']} 的核心概念如何連接？",
        "edges": edges,
    }


__all__ = ["IMPORT_REVIEW_PREVIEW_VERSION", "LINKING_PHRASE_CONTEXT_VERSION", "build_import_review_preview", "build_linking_phrase_context"]
