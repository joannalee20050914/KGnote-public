"""Pure projection of a bounded, evidence-grounded context for one Concept."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from kgnote.contracts import GraphReadModelValidationError, validate_graph_read_model


REVIEWER_CONTEXT_VERSION = "kgnote.reviewer-context.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ReviewerContextProblem:
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class ReviewerContextResult:
    status: Literal["ready", "rejected"]
    _context_json: str | None = field(default=None, repr=False)
    problem: ReviewerContextProblem | None = None

    @property
    def context(self) -> dict[str, Any] | None:
        return json.loads(self._context_json) if self._context_json is not None else None

    def __repr__(self) -> str:
        return f"ReviewerContextResult(status={self.status!r}, problem={self.problem!r})"


def _reject(code: str, path: tuple[object, ...] = ()) -> ReviewerContextResult:
    return ReviewerContextResult("rejected", problem=ReviewerContextProblem(code, path))


def build_reviewer_context(
    read_model: Mapping[str, Any], concept_id: str,
) -> ReviewerContextResult:
    """Select one Concept, direct evidence, one hop, and explicit prior confusion."""

    if not isinstance(read_model, Mapping) or not isinstance(concept_id, str):
        return _reject("invalid_context_request")
    try:
        validate_graph_read_model(read_model)
    except GraphReadModelValidationError as error:
        return _reject("invalid_read_model", error.path)

    nodes = {node["id"]: node for node in read_model["nodes"]}
    evidence = {item["id"]: item for item in read_model["evidence"]}
    sources = {item["id"]: item for item in read_model["sources"]}
    focus = nodes.get(concept_id)
    if focus is None:
        return _reject("unknown_concept")
    if focus["kind"] != "concept":
        return _reject("focus_not_concept")

    incident_links = sorted(
        (link for link in read_model["links"] if concept_id in {link["source_id"], link["target_id"]}),
        key=lambda item: item["id"],
    )
    neighbor_ids = sorted({
        link["target_id"] if link["source_id"] == concept_id else link["source_id"]
        for link in incident_links
    })
    neighbors = [nodes[node_id] for node_id in neighbor_ids]

    related_events_all = [
        node for node in read_model["nodes"] if node["kind"] == "learning_event" and (
            concept_id in node["concept_ids"] or node["id"] in neighbor_ids
        )
    ]
    related_events = sorted(
        (event for event in related_events_all if event["occurred_at"] is not None),
        key=lambda item: (item["occurred_at"], item["id"]), reverse=True,
    ) + sorted(
        (event for event in related_events_all if event["occurred_at"] is None),
        key=lambda item: item["id"],
    )
    confusion_events = [event for event in related_events if event["event_type"] == "confusion"]
    confusion_links = [
        link for link in incident_links
        if link["edge_class"] == "learning" and link["relation"] == "confused_with"
    ]

    direct_evidence_ids = set(focus["evidence_ids"])
    direct_evidence_ids.update(
        evidence_id for link in incident_links for evidence_id in link["evidence_ids"]
    )
    confusion_evidence_ids = {
        evidence_id for event in confusion_events for evidence_id in event["evidence_ids"]
    } | {
        evidence_id for link in confusion_links for evidence_id in link["evidence_ids"]
    }
    selected_evidence_ids = sorted(direct_evidence_ids | confusion_evidence_ids)
    selected_evidence = [evidence[evidence_id] for evidence_id in selected_evidence_ids]
    source_ids = sorted({item["source_id"] for item in selected_evidence})

    context = {
        "schema_version": REVIEWER_CONTEXT_VERSION,
        "snapshot_sha256": read_model["snapshot_sha256"],
        "focus": focus,
        "evidence": selected_evidence,
        "sources": [sources[source_id] for source_id in source_ids],
        "neighborhood": {"nodes": neighbors, "links": incident_links},
        "previous_confusion": {
            "events": confusion_events,
            "links": confusion_links,
            "evidence_ids": sorted(confusion_evidence_ids),
        },
    }
    return ReviewerContextResult("ready", _context_json=_canonical_json(context))
