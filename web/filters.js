const FILTER_NAMES = ["node_kinds", "edge_classes", "relations", "spaces"];

function reject(code) {
  return {status: "rejected", problem: {code}};
}

export function defaultViewState(view, {mobile = false, mobileFocusId = null} = {}) {
  if (!view?.snapshot_sha256) return null;
  return {
    focus_node_id: mobile ? mobileFocusId : null,
    hop_depth: mobile ? 1 : null,
    filters: Object.fromEntries(FILTER_NAMES.map((name) => [name, []])),
  };
}

export function buildGraphViewQuery(view, state) {
  if (!view?.snapshot_sha256 || !state || !state.filters) return reject("invalid_query_state");
  const nodeIds = new Set((view.nodes ?? []).map(({id}) => id));
  const focus = state.focus_node_id;
  const hops = state.hop_depth;
  if (focus !== null && (!nodeIds.has(focus) || ![1, 2, 3].includes(hops))) return reject("invalid_focus_or_hop");
  if (focus === null && hops !== null) return reject("invalid_focus_or_hop");
  const filters = {};
  for (const name of FILTER_NAMES) {
    const values = state.filters[name];
    const available = new Set(view.filter_facets?.[name] ?? []);
    if (!Array.isArray(values) || values.some((value) => typeof value !== "string" || !available.has(value))) {
      return reject("unavailable_filter_value");
    }
    filters[name] = [...new Set(values)].sort((a, b) => a.localeCompare(b));
  }
  return {
    status: "ready",
    query: {
      schema_version: "kgnote.graph-view-query.v1",
      snapshot_sha256: view.snapshot_sha256,
      focus_node_id: focus,
      hop_depth: hops,
      filters,
    },
  };
}

export function modeDescription(query) {
  return query.focus_node_id === null ? "Full filtered graph" : `Local · ${query.hop_depth} hop${query.hop_depth === 1 ? "" : "s"}`;
}
