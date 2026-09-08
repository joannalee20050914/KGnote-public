"""Pure canonical-record to graph-read-model projection."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

from kgnote.contracts.graph_read_model import (
    SCHEMA_VERSION,
    GraphReadModelValidationError,
    validate_graph_read_model,
)
from kgnote.planning import validate_existing_snapshot


GRAPH_PROJECTOR_VERSION = "kgnote.graph-projector.v1"
_SET_LIKE_FIELDS = {
    "concept": ("aliases", "spaces", "evidence_ids"),
    "learning_event": ("source_ids", "concept_ids", "evidence_ids"),
    "edge": ("evidence_ids",),
}


@dataclass(frozen=True)
class GraphProjectionProblem:
    code: str
    path: tuple[object, ...] = ()
    record_id: str | None = None


@dataclass(frozen=True, repr=False)
class GraphProjectionResult:
    status: Literal["projected", "rejected"]
    projector_version: str = GRAPH_PROJECTOR_VERSION
    _model_json: str = field(default="{}", repr=False)
    problem: GraphProjectionProblem | None = None

    @property
    def model(self) -> dict[str, Any] | None:
        return json.loads(self._model_json) if self.status == "projected" else None

    def __repr__(self) -> str:
        return (
            "GraphProjectionResult("
            f"status={self.status!r}, projector_version={self.projector_version!r}, "
            f"problem={self.problem!r})"
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject(code: str, path: tuple[object, ...] = (), record_id: str | None = None) -> GraphProjectionResult:
    return GraphProjectionResult(
        status="rejected",
        problem=GraphProjectionProblem(code=code, path=path, record_id=record_id),
    )


def _normalized_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    copied = json.loads(_canonical_json(records))
    for record in copied:
        for field_name in _SET_LIKE_FIELDS.get(record["type"], ()):
            record[field_name] = sorted(record[field_name])
    return sorted(copied, key=lambda record: (record["type"], record["id"]))


def _safe_label(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    label = re.sub(r"[\[\]|#^]", " ", value)
    label = re.sub(r"\s+", " ", label).strip()
    if not label:
        return fallback
    return label if len(label) <= 64 else f"{label[:61].rstrip()}..."


def _base_label(record: Mapping[str, Any]) -> str:
    fallback = f"Record {hashlib.sha256(record['id'].encode('utf-8')).hexdigest()[:8]}"
    if record["type"] == "concept":
        return _safe_label(record.get("canonical_name"), fallback)
    if record["type"] == "source":
        return _safe_label(record.get("title"), fallback)
    if record["type"] == "evidence":
        locator = record.get("locator")
        value = locator.get("value") if isinstance(locator, Mapping) else None
        return _safe_label(f"Evidence {value}" if value else None, fallback)
    event_type = record.get("event_type")
    return _safe_label(
        f"{str(event_type).replace('_', ' ').title()} event" if event_type else None,
        fallback,
    )


def _labels(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    label_records = [record for record in records if record["type"] != "edge"]
    bases = {record["id"]: _base_label(record) for record in label_records}
    counts: dict[str, int] = {}
    for label in bases.values():
        counts[label.casefold()] = counts.get(label.casefold(), 0) + 1
    labels: dict[str, str] = {}
    for record_id, label in bases.items():
        if counts[label.casefold()] > 1:
            token = hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:8]
            label = f"{label[:53].rstrip()} · {token}"
        labels[record_id] = label
    return labels


def _build_model(records: list[dict[str, Any]]) -> dict[str, Any]:
    labels = _labels(records)
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for record in records:
        record_type = record["type"]
        if record_type == "concept":
            nodes.append({
                "id": record["id"], "kind": "concept", "label": labels[record["id"]],
                "aliases": record["aliases"], "spaces": record["spaces"],
                "summary": record["summary"], "status": record["status"],
                "evidence_ids": record["evidence_ids"],
            })
        elif record_type == "learning_event":
            nodes.append({
                "id": record["id"], "kind": "learning_event", "label": labels[record["id"]],
                "event_type": record["event_type"], "occurred_at": record["occurred_at"],
                "context": record["context"], "concept_ids": record["concept_ids"],
                "evidence_ids": record["evidence_ids"], "source_ids": record["source_ids"],
            })
        elif record_type == "edge":
            links.append({key: record[key] for key in (
                "id", "source_id", "target_id", "relation", "edge_class", "confidence", "evidence_ids"
            )})
        elif record_type == "evidence":
            evidence.append({
                "id": record["id"], "label": labels[record["id"]],
                "source_id": record["source_id"], "locator": record["locator"],
                "proposition": record["proposition"], "observed_at": record["observed_at"],
                "extractor_version": record["extractor_version"],
                "extraction_confidence": record["extraction_confidence"],
                "review_status": record["review_status"],
            })
        elif record_type == "source":
            sources.append({
                "id": record["id"], "label": labels[record["id"]],
                "source_kind": record["source_kind"], "captured_at": record["captured_at"],
                "content_sha256": record["content_sha256"],
            })
    for collection in (nodes, links, evidence, sources):
        collection.sort(key=lambda item: item["id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_sha256": hashlib.sha256(_canonical_json(records).encode("utf-8")).hexdigest(),
        "nodes": nodes,
        "links": links,
        "evidence": evidence,
        "sources": sources,
        "filter_facets": {
            "node_kinds": sorted({node["kind"] for node in nodes}),
            "edge_classes": sorted({link["edge_class"] for link in links}),
            "relations": sorted({link["relation"] for link in links if link["relation"]}),
            "spaces": sorted({space for node in nodes if node["kind"] == "concept" for space in node["spaces"]}),
        },
    }


def project_graph_read_model(records: Sequence[Mapping[str, Any]]) -> GraphProjectionResult:
    """Project caller-owned canonical records without filesystem, network, or clock access."""

    validation = validate_existing_snapshot(records)
    if validation.status == "rejected":
        problem = validation.problem
        return _reject(
            f"snapshot_{problem.code}",
            problem.path,
            problem.record_id,
        )
    normalized = _normalized_records(records)
    model = _build_model(normalized)
    try:
        validate_graph_read_model(model)
    except GraphReadModelValidationError as error:
        return _reject("projected_model_invalid", error.path)
    return GraphProjectionResult(status="projected", _model_json=_canonical_json(model))
