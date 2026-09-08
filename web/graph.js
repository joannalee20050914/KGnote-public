const WIDTH = 1200;
const HEIGHT = 720;

export function validateApplicationResult(payload) {
  if (!payload || payload.schema_version !== "kgnote.graph-view-application.v1" || payload.status !== "ready") {
    return {ok: false, code: "invalid_application_result"};
  }
  const view = payload.view;
  const plan = payload.plan;
  if (!view || view.schema_version !== "kgnote.graph-read-model.v1" || !Array.isArray(view.nodes) || !Array.isArray(view.links)) {
    return {ok: false, code: "invalid_graph_view"};
  }
  if (!plan || plan.schema_version !== "kgnote.graph-view-plan.v1" || plan.snapshot_sha256 !== view.snapshot_sha256) {
    return {ok: false, code: "invalid_graph_plan"};
  }
  const ids = new Set();
  for (const node of view.nodes) {
    if (!node || !node.id || !node.label || !["concept", "learning_event"].includes(node.kind) || ids.has(node.id)) {
      return {ok: false, code: "invalid_graph_node"};
    }
    ids.add(node.id);
  }
  for (const link of view.links) {
    if (!link || !link.id || !ids.has(link.source_id) || !ids.has(link.target_id) ||
        !["canonical", "learning", "soft_association"].includes(link.edge_class)) {
      return {ok: false, code: "invalid_graph_link"};
    }
    if (link.edge_class === "soft_association" && (link.relation !== null || link.confidence !== "unresolved")) {
      return {ok: false, code: "invalid_soft_association"};
    }
  }
  return {ok: true};
}

export function selectLocalNeighborhood(view) {
  const concepts = view.nodes.filter((node) => node.kind === "concept");
  if (!concepts.length) return {nodes: view.nodes.slice(), links: view.links.slice(), focusId: null};
  const degrees = new Map(concepts.map((node) => [node.id, 0]));
  for (const link of view.links) {
    if (degrees.has(link.source_id)) degrees.set(link.source_id, degrees.get(link.source_id) + 1);
    if (degrees.has(link.target_id)) degrees.set(link.target_id, degrees.get(link.target_id) + 1);
  }
  const focusId = concepts.map((node) => node.id).sort((a, b) => degrees.get(b) - degrees.get(a) || a.localeCompare(b))[0];
  const selected = new Set([focusId]);
  for (const link of view.links) {
    if (link.source_id === focusId) selected.add(link.target_id);
    if (link.target_id === focusId) selected.add(link.source_id);
  }
  return {
    focusId,
    nodes: view.nodes.filter((node) => selected.has(node.id)),
    links: view.links.filter((link) => selected.has(link.source_id) && selected.has(link.target_id)),
  };
}

function ellipsePositions(nodes, rx, ry, centerX, centerY, offset = -Math.PI / 2) {
  return new Map(nodes.map((node, index) => {
    const angle = offset + (Math.PI * 2 * index) / Math.max(nodes.length, 1);
    return [node.id, {x: centerX + Math.cos(angle) * rx, y: centerY + Math.sin(angle) * ry}];
  }));
}

export function buildScene(view, {mobile = false} = {}) {
  const selected = mobile ? selectLocalNeighborhood(view) : {nodes: view.nodes, links: view.links, focusId: null};
  const nodes = selected.nodes.slice().sort((a, b) => a.id.localeCompare(b.id));
  const concepts = nodes.filter((node) => node.kind === "concept");
  const events = nodes.filter((node) => node.kind === "learning_event");
  const width = mobile ? 720 : WIDTH;
  const height = mobile ? 900 : HEIGHT;
  const positions = ellipsePositions(concepts, mobile ? 245 : 455, mobile ? 320 : 250, width / 2, height / 2);
  const eventPositions = ellipsePositions(events, 90, 105, width / 2, height / 2, Math.PI / 2);
  for (const [id, position] of eventPositions) positions.set(id, position);
  const sceneNodes = nodes.map((node) => ({...node, ...positions.get(node.id), focused: node.id === selected.focusId}));
  const byId = new Map(sceneNodes.map((node) => [node.id, node]));
  const sceneLinks = selected.links.slice().sort((a, b) => a.id.localeCompare(b.id)).map((link) => ({
    ...link,
    x1: byId.get(link.source_id).x,
    y1: byId.get(link.source_id).y,
    x2: byId.get(link.target_id).x,
    y2: byId.get(link.target_id).y,
  }));
  return {width, height, nodes: sceneNodes, links: sceneLinks, mode: mobile ? "local" : "full", focusId: selected.focusId};
}
