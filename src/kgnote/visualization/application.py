"""Read-only canonical-store to graph-view application boundary."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from kgnote.contracts import GraphReadModelValidationError, validate_graph_read_model
from kgnote.storage import read_canonical_store

from .query_plan import QUERY_VERSION, plan_graph_view
from .read_model import project_graph_read_model


APPLICATION_VERSION = "kgnote.graph-view-application.v1"
_FILTER_NAMES = ("node_kinds", "edge_classes", "relations", "spaces")


@dataclass(frozen=True)
class GraphViewApplicationProblem:
    component: Literal["store", "projector", "planner"]
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class GraphViewApplicationResult:
    status: Literal["ready", "rejected"]
    _response_json: str = field(default="{}", repr=False)
    problem: GraphViewApplicationProblem | None = None

    @property
    def response(self) -> dict[str, Any]:
        return json.loads(self._response_json)

    def __repr__(self) -> str:
        return f"GraphViewApplicationResult(status={self.status!r}, problem={self.problem!r})"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _result(payload: Mapping[str, Any], problem: GraphViewApplicationProblem | None = None) -> GraphViewApplicationResult:
    return GraphViewApplicationResult(payload["status"], _canonical_json(payload), problem)


def _reject(component: Literal["store", "projector", "planner"], code: str, path: tuple[object, ...] = ()) -> GraphViewApplicationResult:
    problem = GraphViewApplicationProblem(component, code, path)
    return _result({
        "schema_version": APPLICATION_VERSION,
        "status": "rejected",
        "problem": {"component": component, "code": code, "path": list(path)},
    }, problem)


def _default_query(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": QUERY_VERSION,
        "snapshot_sha256": model["snapshot_sha256"],
        "focus_node_id": None,
        "hop_depth": None,
        "filters": {name: [] for name in _FILTER_NAMES},
    }


def _materialize(model: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    selected = plan["selected"]
    ids = {name: set(selected[name]) for name in selected}
    nodes = []
    for item in model["nodes"]:
        if item["id"] not in ids["node_ids"]:
            continue
        copied = dict(item)
        if copied["kind"] == "learning_event":
            copied["concept_ids"] = [concept_id for concept_id in copied["concept_ids"] if concept_id in ids["node_ids"]]
        nodes.append(copied)
    links = [item for item in model["links"] if item["id"] in ids["link_ids"]]
    evidence = [item for item in model["evidence"] if item["id"] in ids["evidence_ids"]]
    sources = [item for item in model["sources"] if item["id"] in ids["source_ids"]]
    view = {
        "schema_version": model["schema_version"],
        "snapshot_sha256": model["snapshot_sha256"],
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
    validate_graph_read_model(view)
    return view


def load_graph_view(root: str | os.PathLike[str], query: Mapping[str, Any] | None = None) -> GraphViewApplicationResult:
    """Read an explicit store and return a deterministic materialized graph view."""

    if not isinstance(root, (str, os.PathLike)):
        return _reject("store", "invalid_store_root")
    snapshot = read_canonical_store(root)
    if snapshot.status != "loaded":
        store_problem = snapshot.problem
        safe_path = (store_problem.path,) if store_problem and store_problem.path and not os.path.isabs(store_problem.path) else ()
        return _reject("store", store_problem.code if store_problem else "store_rejected", safe_path)
    projection = project_graph_read_model(snapshot.records)
    if projection.status != "projected":
        projection_problem = projection.problem
        return _reject(
            "projector",
            projection_problem.code if projection_problem else "projection_rejected",
            projection_problem.path if projection_problem else (),
        )
    model = projection.model
    selected_query = _default_query(model) if query is None else query
    planning = plan_graph_view(model, selected_query)
    if planning.status != "planned":
        planning_problem = planning.problem
        return _reject(
            "planner",
            planning_problem.code if planning_problem else "planning_rejected",
            planning_problem.path if planning_problem else (),
        )
    plan = planning.plan
    try:
        materialized = _materialize(model, plan)
    except GraphReadModelValidationError as error:
        return _reject("projector", "materialized_view_invalid", error.path)
    payload = {
        "schema_version": APPLICATION_VERSION,
        "status": "ready",
        "view": materialized,
        "plan": plan,
    }
    return _result(payload)


__all__ = [
    "APPLICATION_VERSION",
    "GraphViewApplicationProblem",
    "GraphViewApplicationResult",
    "load_graph_view",
]
