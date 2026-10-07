"""Pure Graph Read Model + Guided Map Spec projection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from kgnote.contracts.graph_read_model import (
    GraphReadModelValidationError,
    validate_graph_read_model,
)
from kgnote.contracts.guided_map import (
    READ_MODEL_SCHEMA_VERSION,
    GuidedMapValidationError,
    validate_guided_map_read_model,
    validate_guided_map_spec,
)


GUIDED_MAP_PROJECTOR_VERSION = "kgnote.guided-map-projector.v1"


@dataclass(frozen=True)
class GuidedMapProjectionProblem:
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class GuidedMapProjectionResult:
    status: Literal["projected", "rejected"]
    projector_version: str = GUIDED_MAP_PROJECTOR_VERSION
    _model_json: str = field(default="{}", repr=False)
    problem: GuidedMapProjectionProblem | None = None

    @property
    def model(self) -> dict[str, Any] | None:
        return json.loads(self._model_json) if self.status == "projected" else None

    def __repr__(self) -> str:
        return (
            "GuidedMapProjectionResult("
            f"status={self.status!r}, projector_version={self.projector_version!r}, "
            f"problem={self.problem!r})"
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject(code: str, path: tuple[object, ...] = ()) -> GuidedMapProjectionResult:
    return GuidedMapProjectionResult(
        status="rejected",
        problem=GuidedMapProjectionProblem(code=code, path=path),
    )


def _build_model(graph: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    graph_concepts = {
        node["id"]: node for node in graph["nodes"] if node["kind"] == "concept"
    }
    graph_links = {link["id"]: link for link in graph["links"]}
    graph_evidence = {record["id"]: record for record in graph["evidence"]}
    graph_sources = {source["id"]: source for source in graph["sources"]}

    selected_concepts = {
        concept_id
        for group in spec["groups"]
        for concept_id in group["concept_ids"]
    }
    group_for = {
        concept_id: group["id"]
        for group in spec["groups"]
        for concept_id in group["concept_ids"]
    }
    source = graph_sources.get(spec["source_id"])
    if source is None:
        raise GuidedMapValidationError("dangling_source_reference", ("source_id",))

    concepts: list[dict[str, Any]] = []
    for concept_id in sorted(selected_concepts):
        node = graph_concepts.get(concept_id)
        if node is None:
            raise GuidedMapValidationError("dangling_concept_reference", ("groups",))
        concepts.append({
            "id": node["id"],
            "label": node["label"],
            "aliases": node["aliases"],
            "summary": node["summary"],
            "status": node["status"],
            "evidence_ids": node["evidence_ids"],
            "group_id": group_for[concept_id],
        })

    propositions: list[dict[str, Any]] = []
    selected_evidence = {
        evidence_id for concept in concepts for evidence_id in concept["evidence_ids"]
    }
    for index, teaching in enumerate(spec["teaching_propositions"]):
        link = graph_links.get(teaching["edge_id"])
        if link is None:
            raise GuidedMapValidationError(
                "dangling_edge_reference", ("teaching_propositions", index, "edge_id")
            )
        if link["edge_class"] != "canonical":
            raise GuidedMapValidationError(
                "non_canonical_teaching_edge", ("teaching_propositions", index, "edge_id")
            )
        if link["source_id"] not in selected_concepts or link["target_id"] not in selected_concepts:
            raise GuidedMapValidationError(
                "unselected_teaching_edge_endpoint", ("teaching_propositions", index, "edge_id")
            )
        if teaching["evidence_ids"] != link["evidence_ids"]:
            raise GuidedMapValidationError(
                "teaching_evidence_drift", ("teaching_propositions", index, "evidence_ids")
            )
        selected_evidence.update(teaching["evidence_ids"])
        subject = graph_concepts[link["source_id"]]
        object_ = graph_concepts[link["target_id"]]
        propositions.append({
            "edge_id": link["id"],
            "subject_concept_id": subject["id"],
            "subject_label": subject["label"],
            "linking_phrase": teaching["linking_phrase"],
            "object_concept_id": object_["id"],
            "object_label": object_["label"],
            "canonical_relation": link["relation"],
            "evidence_ids": link["evidence_ids"],
            "review_status": teaching["review_status"],
            "projection_version": spec["projection_version"],
        })

    evidence: list[dict[str, Any]] = []
    for evidence_id in sorted(selected_evidence):
        record = graph_evidence.get(evidence_id)
        if record is None:
            raise GuidedMapValidationError("dangling_evidence_reference", ("evidence",))
        if record["source_id"] != source["id"]:
            raise GuidedMapValidationError("evidence_outside_learning_unit_source", ("evidence",))
        if record["review_status"] not in {"accepted", "corrected"}:
            raise GuidedMapValidationError("unreviewed_teaching_evidence", ("evidence",))
        evidence.append(json.loads(_canonical_json(record)))

    groups = json.loads(_canonical_json(spec["groups"]))
    groups.sort(key=lambda group: (group["order"], group["id"]))
    propositions.sort(key=lambda proposition: proposition["edge_id"])
    return {
        "schema_version": READ_MODEL_SCHEMA_VERSION,
        "projection_version": spec["projection_version"],
        "graph_snapshot_sha256": graph["snapshot_sha256"],
        "source": json.loads(_canonical_json(source)),
        "learning_unit": {
            "id": spec["id"],
            "display_locale": spec["display_locale"],
            "title": spec["title"],
            "focus_question": spec["focus_question"],
            "source_locator": json.loads(_canonical_json(spec["source_locator"])),
        },
        "groups": groups,
        "concepts": concepts,
        "propositions": propositions,
        "evidence": evidence,
    }


def project_guided_map(
    graph_read_model: Mapping[str, Any], spec: Mapping[str, Any]
) -> GuidedMapProjectionResult:
    """Resolve a versioned teaching spec against one exact graph snapshot."""

    try:
        validate_graph_read_model(graph_read_model)
    except (GraphReadModelValidationError, TypeError):
        return _reject("invalid_graph_read_model")
    try:
        validate_guided_map_spec(spec)
        if spec["graph_snapshot_sha256"] != graph_read_model["snapshot_sha256"]:
            return _reject("stale_graph_snapshot", ("graph_snapshot_sha256",))
        model = _build_model(graph_read_model, spec)
        validate_guided_map_read_model(model)
    except GuidedMapValidationError as error:
        return _reject(error.code, error.path)
    return GuidedMapProjectionResult(status="projected", _model_json=_canonical_json(model))


__all__ = [
    "GUIDED_MAP_PROJECTOR_VERSION",
    "GuidedMapProjectionProblem",
    "GuidedMapProjectionResult",
    "project_guided_map",
]
