"""Pure deterministic neighborhood and filter planning."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping
from kgnote.contracts import GraphReadModelValidationError, validate_graph_read_model

QUERY_VERSION = "kgnote.graph-view-query.v1"
PLAN_VERSION = "kgnote.graph-view-plan.v1"
FILTERS = ("node_kinds", "edge_classes", "relations", "spaces")

@dataclass(frozen=True)
class GraphViewProblem:
    code: str
    path: tuple[object, ...] = ()

@dataclass(frozen=True, repr=False)
class GraphViewPlanResult:
    status: Literal["planned", "rejected"]
    _plan_json: str = field(default="{}", repr=False)
    problem: GraphViewProblem | None = None
    @property
    def plan(self) -> dict[str, Any] | None:
        return json.loads(self._plan_json) if self.status == "planned" else None
    def __repr__(self) -> str:
        return f"GraphViewPlanResult(status={self.status!r}, problem={self.problem!r})"

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _reject(code: str, *path: object) -> GraphViewPlanResult:
    return GraphViewPlanResult("rejected", problem=GraphViewProblem(code, tuple(path)))

def _validate_query(query: Any, model: Mapping[str, Any]) -> GraphViewPlanResult | None:
    if not isinstance(query, Mapping): return _reject("query_not_object")
    required = {"schema_version", "snapshot_sha256", "focus_node_id", "hop_depth", "filters"}
    if set(query) != required: return _reject("invalid_query_fields")
    if query["schema_version"] != QUERY_VERSION: return _reject("unsupported_query_version", "schema_version")
    if query["snapshot_sha256"] != model["snapshot_sha256"]: return _reject("snapshot_digest_mismatch", "snapshot_sha256")
    focus, hops = query["focus_node_id"], query["hop_depth"]
    if focus is not None and not isinstance(focus, str): return _reject("invalid_focus", "focus_node_id")
    if (focus is None and hops is not None) or (focus is not None and (type(hops) is not int or hops not in (1,2,3))):
        return _reject("invalid_hop_depth", "hop_depth")
    filters = query["filters"]
    if not isinstance(filters, Mapping) or set(filters) != set(FILTERS): return _reject("invalid_filters", "filters")
    for name in FILTERS:
        values = filters[name]
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or values != sorted(set(values)):
            return _reject("invalid_filter_values", "filters", name)
        if not set(values) <= set(model["filter_facets"][name]): return _reject("unavailable_filter_value", "filters", name)
    return None

def plan_graph_view(model: Mapping[str, Any], query: Mapping[str, Any]) -> GraphViewPlanResult:
    try: validate_graph_read_model(model)
    except GraphReadModelValidationError: return _reject("invalid_graph_read_model")
    rejected = _validate_query(query, model)
    if rejected: return rejected
    nodes={n["id"]:n for n in model["nodes"]}; links={e["id"]:e for e in model["links"]}; f=query["filters"]
    space_concepts={n["id"] for n in nodes.values() if n["kind"]=="concept" and (not f["spaces"] or set(n["spaces"])&set(f["spaces"]))}
    eligible_nodes=set()
    node_reason={}
    for nid,n in nodes.items():
        if f["node_kinds"] and n["kind"] not in f["node_kinds"]: node_reason[nid]="filtered_node_kind"
        elif f["spaces"] and (n["kind"]=="concept" and nid not in space_concepts or n["kind"]=="learning_event" and not set(n["concept_ids"])&space_concepts): node_reason[nid]="filtered_space"
        else: eligible_nodes.add(nid)
    eligible_links=set(); link_reason={}
    for eid,e in links.items():
        if f["edge_classes"] and e["edge_class"] not in f["edge_classes"]: link_reason[eid]="filtered_edge_class"
        elif f["relations"] and e["relation"] not in f["relations"]: link_reason[eid]="filtered_relation"
        elif e["source_id"] not in eligible_nodes or e["target_id"] not in eligible_nodes: link_reason[eid]="endpoint_excluded"
        else: eligible_links.add(eid)
    focus=query["focus_node_id"]
    if focus is not None and focus not in nodes: return _reject("unknown_focus_node", "focus_node_id")
    if focus is not None and focus not in eligible_nodes: return _reject("focus_excluded_by_filters", "focus_node_id")
    selected=set(eligible_nodes)
    if focus is not None:
        selected={focus}; frontier={focus}
        adjacency={nid:set() for nid in eligible_nodes}
        for eid in eligible_links:
            e=links[eid]; adjacency[e["source_id"]].add(e["target_id"]); adjacency[e["target_id"]].add(e["source_id"])
        for _ in range(query["hop_depth"]):
            frontier={v for u in frontier for v in adjacency[u]}-selected; selected |= frontier
    selected_links={eid for eid in eligible_links if links[eid]["source_id"] in selected and links[eid]["target_id"] in selected}
    for nid in eligible_nodes-selected: node_reason[nid]="outside_hop"
    for eid in eligible_links-selected_links: link_reason[eid]="outside_hop"
    evidence_ids={x for nid in selected for x in nodes[nid]["evidence_ids"]}|{x for eid in selected_links for x in links[eid]["evidence_ids"]}
    evidence={e["id"]:e for e in model["evidence"]}
    source_ids={evidence[x]["source_id"] for x in evidence_ids}|{x for nid in selected if nodes[nid]["kind"]=="learning_event" for x in nodes[nid]["source_ids"]}
    plan={"schema_version":PLAN_VERSION,"snapshot_sha256":model["snapshot_sha256"],"query_sha256":hashlib.sha256(_json(query).encode()).hexdigest(),"selected":{"node_ids":sorted(selected),"link_ids":sorted(selected_links),"evidence_ids":sorted(evidence_ids),"source_ids":sorted(source_ids)},"excluded":sorted(([{"kind":"node","id":k,"reason":v} for k,v in node_reason.items()]+[{"kind":"link","id":k,"reason":v} for k,v in link_reason.items()]),key=lambda x:(x["kind"],x["id"]))}
    return GraphViewPlanResult("planned", _plan_json=_json(plan))
