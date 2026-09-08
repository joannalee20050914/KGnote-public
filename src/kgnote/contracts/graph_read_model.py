"""Validation for the versioned, read-only graph projection boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_VERSION = "kgnote.graph-read-model.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "graph-read-model" / "v1" / "graph-read-model.schema.json"
)

_CANONICAL_RELATIONS = {
    "is_a", "part_of", "prerequisite_of", "contrasts_with", "causes", "related_to"
}
_LEARNING_RELATIONS = {
    "asked_about", "explained", "applied", "confused_with", "encountered", "reviewed"
}


class GraphReadModelValidationError(ValueError):
    """A stable error that never includes untrusted payload values."""

    def __init__(self, code: str, path: tuple[object, ...] = (), validator: str = "semantic"):
        self.code = code
        self.path = path
        self.validator = validator
        pointer = "/" + "/".join(str(part) for part in path) if path else "/"
        super().__init__(f"{code} at {pointer} ({validator})")


with SCHEMA_PATH.open(encoding="utf-8") as _handle:
    _VALIDATOR = Draft202012Validator(json.load(_handle), format_checker=FormatChecker())


def _reject(code: str, *path: object) -> None:
    raise GraphReadModelValidationError(code, tuple(path))


def _require_sorted_unique(values: list[Any], path: tuple[object, ...]) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        raise GraphReadModelValidationError("non_deterministic_order", path)


def validate_graph_read_model(payload: Mapping[str, Any]) -> None:
    """Validate schema, references, graph-layer policy, and deterministic ordering."""

    errors = sorted(
        _VALIDATOR.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if errors:
        error = errors[0]
        raise GraphReadModelValidationError(
            "invalid_graph_read_model",
            tuple(error.absolute_path),
            str(error.validator),
        )

    collections = ("nodes", "links", "evidence", "sources")
    all_records = [record for name in collections for record in payload[name]]
    all_ids = [record["id"] for record in all_records]
    if len(all_ids) != len(set(all_ids)):
        _reject("duplicate_record_id")
    for collection in collections:
        ids = [record["id"] for record in payload[collection]]
        _require_sorted_unique(ids, (collection,))

    nodes = {node["id"]: node for node in payload["nodes"]}
    concepts = {node_id for node_id, node in nodes.items() if node["kind"] == "concept"}
    events = {node_id for node_id, node in nodes.items() if node["kind"] == "learning_event"}
    evidence = {record["id"] for record in payload["evidence"]}
    sources = {record["id"] for record in payload["sources"]}

    for index, node in enumerate(payload["nodes"]):
        for field in ("aliases", "spaces", "evidence_ids") if node["kind"] == "concept" else ("concept_ids", "evidence_ids", "source_ids"):
            _require_sorted_unique(node[field], ("nodes", index, field))
        for evidence_id in node["evidence_ids"]:
            if evidence_id not in evidence:
                _reject("dangling_evidence_reference", "nodes", index, "evidence_ids")
        if node["kind"] == "learning_event":
            if not set(node["concept_ids"]).issubset(concepts):
                _reject("invalid_event_concept_reference", "nodes", index, "concept_ids")
            if not set(node["source_ids"]).issubset(sources):
                _reject("dangling_source_reference", "nodes", index, "source_ids")

    for index, link in enumerate(payload["links"]):
        _require_sorted_unique(link["evidence_ids"], ("links", index, "evidence_ids"))
        if link["source_id"] not in nodes or link["target_id"] not in nodes:
            _reject("dangling_link_endpoint", "links", index)
        if not set(link["evidence_ids"]).issubset(evidence):
            _reject("dangling_evidence_reference", "links", index, "evidence_ids")
        if link["edge_class"] in {"canonical", "soft_association"}:
            if link["source_id"] not in concepts or link["target_id"] not in concepts:
                _reject("invalid_concept_edge_endpoint", "links", index)
        elif link["source_id"] not in events or link["target_id"] not in concepts:
            _reject("invalid_learning_edge_endpoint", "links", index)

    for index, record in enumerate(payload["evidence"]):
        if record["source_id"] not in sources:
            _reject("dangling_source_reference", "evidence", index, "source_id")

    facets = payload["filter_facets"]
    for name in ("node_kinds", "edge_classes", "relations", "spaces"):
        _require_sorted_unique(facets[name], ("filter_facets", name))
    expected = {
        "node_kinds": sorted({node["kind"] for node in payload["nodes"]}),
        "edge_classes": sorted({link["edge_class"] for link in payload["links"]}),
        "relations": sorted({link["relation"] for link in payload["links"] if link["relation"]}),
        "spaces": sorted({space for node in payload["nodes"] if node["kind"] == "concept" for space in node["spaces"]}),
    }
    if facets != expected:
        _reject("facet_values_do_not_match_records", "filter_facets")


__all__ = ["GraphReadModelValidationError", "SCHEMA_VERSION", "validate_graph_read_model"]
