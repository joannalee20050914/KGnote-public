import {buildScene, validateApplicationResult} from "./graph.js";
import {buildNodeDetails} from "./panel.js";
import {buildGraphViewQuery, defaultViewState, modeDescription} from "./filters.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const fixtureUrl = "./fixtures/phase0-graph-view.json";
const svg = document.querySelector("#graph");
const stage = document.querySelector("#graph-stage");
const message = document.querySelector("#graph-message");
const modeLabel = document.querySelector("#view-mode");
const countLabel = document.querySelector("#graph-count");
let payload;
let catalogView;
let activeQuery;
let baseBox = {x: 0, y: 0, width: 1200, height: 720};
let viewBox = {...baseBox};
const detailPanel = document.querySelector("#detail-panel");
const detailTitle = document.querySelector("#detail-title");
const detailKind = document.querySelector("#detail-kind");
const detailContent = document.querySelector("#detail-content");
const closeDetailButton = document.querySelector("#close-detail");
const focusSelect = document.querySelector("#focus-node");
const hopSelect = document.querySelector("#hop-depth");
const filterGroups = document.querySelector("#filter-groups");
const filterCount = document.querySelector("#filter-count");
const queryMessage = document.querySelector("#query-message");
let detailTrigger = null;

function element(name, attributes = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

function relationLabel(link) {
  return link.relation ? link.relation.replaceAll("_", " ") : "unresolved";
}

function textElement(name, text, className) {
  const node = document.createElement(name);
  if (className) node.className = className;
  node.textContent = text;
  return node;
}

function section(title, items, renderItem, emptyText) {
  const container = document.createElement("section");
  container.className = "detail-section";
  container.append(textElement("h3", title));
  if (!items.length) container.append(textElement("p", emptyText, "empty-state"));
  else {
    const list = document.createElement("ul");
    for (const item of items) list.append(renderItem(item));
    container.append(list);
  }
  return container;
}

function evidenceItem(item) {
  const row = document.createElement("li");
  row.append(textElement("strong", item.label), textElement("p", item.proposition));
  row.append(textElement("small", `${item.locator.kind.replaceAll("_", " ")} · ${item.locator.value} · ${item.extraction_confidence} confidence · ${item.review_status} · ${item.extractor_version}`));
  return row;
}

function closeDetails({restoreFocus = true} = {}) {
  detailPanel.hidden = true;
  document.body.classList.remove("detail-open");
  if (restoreFocus && detailTrigger?.isConnected) detailTrigger.focus();
}

function openDetails(nodeId, trigger) {
  const result = buildNodeDetails(payload.view, nodeId);
  if (result.status !== "ready") return;
  const detail = result.detail;
  detailTrigger = trigger;
  detailTitle.textContent = detail.label;
  detailKind.textContent = detail.kind === "concept" ? "Concept details" : "Learning event details";
  detailContent.replaceChildren();
  if (detail.kind === "concept") {
    detailContent.append(textElement("p", detail.summary, "detail-summary"));
    detailContent.append(textElement("p", `Status: ${detail.status.replaceAll("_", " ")} · Spaces: ${detail.spaces.join(", ") || "None"}`, "detail-meta"));
  } else {
    detailContent.append(textElement("p", detail.context, "detail-summary"));
    detailContent.append(textElement("p", `${detail.event_type.replaceAll("_", " ")} · ${detail.occurred_at ?? "Time not recorded"}`, "detail-meta"));
    detailContent.append(section("Concepts", detail.concepts, (item) => textElement("li", item.label), "No concepts in this view."));
  }
  detailContent.append(section("Evidence", detail.evidence, evidenceItem, "No evidence in this view."));
  detailContent.append(section("Sources", detail.sources, (source) => {
    const row = document.createElement("li");
    row.append(textElement("strong", source.label), textElement("small", `${source.source_kind.replaceAll("_", " ")} · ${source.captured_at ?? "Capture time not recorded"}`));
    return row;
  }, "No sources in this view."));
  detailContent.append(section("Learning history", detail.history, (event) => {
    const row = document.createElement("li");
    row.append(textElement("strong", event.label), textElement("p", event.context), textElement("small", `${event.event_type} · ${event.occurred_at ?? "Time not recorded"}`));
    return row;
  }, "No learning events in this view."));
  detailContent.append(section("Known confusion", detail.known_confusion.evidence, evidenceItem, "No explicitly evidenced confusion in this view."));
  detailPanel.hidden = false;
  document.body.classList.add("detail-open");
  closeDetailButton.focus();
}

function render(scene) {
  svg.replaceChildren();
  baseBox = {x: 0, y: 0, width: scene.width, height: scene.height};
  viewBox = {...baseBox};
  svg.setAttribute("viewBox", `0 0 ${scene.width} ${scene.height}`);
  svg.dataset.mode = scene.mode;

  const defs = element("defs");
  const marker = element("marker", {id: "arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth"});
  marker.append(element("path", {d: "M 0 0 L 8 4 L 0 8 z"}));
  defs.append(marker);
  svg.append(defs);

  const links = element("g", {class: "links"});
  for (const link of scene.links) {
    const group = element("g", {class: `graph-link ${link.edge_class}`, "data-id": link.id});
    group.append(element("line", {x1: link.x1, y1: link.y1, x2: link.x2, y2: link.y2, "marker-end": "url(#arrow)"}));
    const label = element("text", {x: (link.x1 + link.x2) / 2, y: (link.y1 + link.y2) / 2 - 9});
    label.textContent = relationLabel(link);
    group.append(label);
    links.append(group);
  }
  svg.append(links);

  const nodes = element("g", {class: "nodes"});
  for (const node of scene.nodes) {
    const group = element("g", {
      class: `graph-node ${node.kind}${node.focused ? " focused" : ""}`,
      transform: `translate(${node.x} ${node.y})`,
      "data-id": node.id,
      tabindex: 0,
      role: "img",
      "aria-label": `${node.kind === "concept" ? "Concept" : "Learning event"}: ${node.label}`,
    });
    group.append(element(node.kind === "concept" ? "circle" : "rect", node.kind === "concept" ? {r: 52} : {x: -74, y: -38, width: 148, height: 76, rx: 19}));
    const title = element("title");
    title.textContent = `${node.label} · ${node.id}`;
    group.append(title);
    const label = element("text", {class: "node-label", y: node.kind === "concept" ? 74 : 61});
    label.textContent = node.label;
    group.append(label);
    nodes.append(group);
    const activate = () => openDetails(node.id, group);
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); }
    });
  }
  svg.append(nodes);
  modeLabel.textContent = activeQuery ? modeDescription(activeQuery) : (scene.mode === "local" ? "Local · 1 hop" : "Full graph");
  countLabel.textContent = `${scene.nodes.length} nodes · ${scene.links.length} links`;
  message.hidden = scene.nodes.length > 0;
  if (!scene.nodes.length) message.textContent = "No nodes match this view.";
}

closeDetailButton.addEventListener("click", () => closeDetails());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !detailPanel.hidden) closeDetails();
});

function showError(text) {
  message.textContent = text;
  message.hidden = false;
  svg.replaceChildren();
  countLabel.textContent = "Graph unavailable";
}

function rejectView(text) {
  closeDetails({restoreFocus: false});
  payload = null;
  activeQuery = null;
  modeLabel.textContent = "View unavailable";
  showError(text);
}

function setViewBox(next) {
  viewBox = next;
  svg.setAttribute("viewBox", `${next.x} ${next.y} ${next.width} ${next.height}`);
}

function zoom(factor) {
  const width = Math.max(360, Math.min(baseBox.width * 1.5, viewBox.width * factor));
  const height = width * baseBox.height / baseBox.width;
  setViewBox({x: viewBox.x + (viewBox.width - width) / 2, y: viewBox.y + (viewBox.height - height) / 2, width, height});
}

document.querySelector("#zoom-in").addEventListener("click", () => zoom(0.82));
document.querySelector("#zoom-out").addEventListener("click", () => zoom(1.22));
document.querySelector("#reset-view").addEventListener("click", () => setViewBox({...baseBox}));
stage.addEventListener("wheel", (event) => { event.preventDefault(); zoom(event.deltaY > 0 ? 1.12 : 0.9); }, {passive: false});

let drag;
stage.addEventListener("pointerdown", (event) => { drag = {x: event.clientX, y: event.clientY, box: {...viewBox}}; stage.setPointerCapture(event.pointerId); });
stage.addEventListener("pointermove", (event) => {
  if (!drag) return;
  const scale = viewBox.width / stage.clientWidth;
  setViewBox({...drag.box, x: drag.box.x - (event.clientX - drag.x) * scale, y: drag.box.y - (event.clientY - drag.y) * scale});
});
stage.addEventListener("pointerup", () => { drag = null; });

function renderResponsive() {
  if (!payload) return;
  render(buildScene(payload.view, {mobile: window.innerWidth <= 600, materialized: true}));
}

function pretty(value) { return value.replaceAll("_", " "); }

function populateControls() {
  focusSelect.replaceChildren(new Option("Full graph", ""));
  for (const node of catalogView.nodes) focusSelect.append(new Option(`${node.label} · ${node.kind === "concept" ? "Concept" : "Learning event"}`, node.id));
  const labels = {node_kinds: "Node kinds", edge_classes: "Edge classes", relations: "Relations", spaces: "Spaces"};
  filterGroups.replaceChildren();
  for (const [name, values] of Object.entries(catalogView.filter_facets)) {
    const group = document.createElement("section");
    group.className = "filter-group";
    group.dataset.filter = name;
    group.append(textElement("h3", labels[name]));
    const options = document.createElement("div");
    options.className = "filter-options";
    for (const value of values) {
      const label = document.createElement("label");
      label.className = "filter-option";
      const input = document.createElement("input");
      Object.assign(input, {type: "checkbox", value});
      label.append(input, document.createTextNode(pretty(value)));
      options.append(label);
    }
    if (!values.length) options.append(textElement("span", "Unavailable", "empty-state"));
    group.append(options);
    filterGroups.append(group);
  }
}

function writeState(state) {
  focusSelect.value = state.focus_node_id ?? "";
  hopSelect.value = String(state.hop_depth ?? 1);
  hopSelect.disabled = state.focus_node_id === null;
  for (const group of filterGroups.querySelectorAll("[data-filter]")) {
    for (const input of group.querySelectorAll("input")) input.checked = state.filters[group.dataset.filter].includes(input.value);
  }
  updateFilterCount();
}

function readState() {
  const focus = focusSelect.value || null;
  return {
    focus_node_id: focus,
    hop_depth: focus === null ? null : Number(hopSelect.value),
    filters: Object.fromEntries([...filterGroups.querySelectorAll("[data-filter]")].map((group) => [
      group.dataset.filter, [...group.querySelectorAll("input:checked")].map(({value}) => value),
    ])),
  };
}

function updateFilterCount() {
  const count = filterGroups.querySelectorAll("input:checked").length;
  filterCount.textContent = count ? `${count} active` : "None active";
}

async function applyState(state) {
  const built = buildGraphViewQuery(catalogView, state);
  if (built.status !== "ready") {
    queryMessage.textContent = "This view request is not available.";
    rejectView("The requested view is unavailable.");
    return;
  }
  queryMessage.textContent = "Loading view…";
  try {
    const response = await fetch("/api/graph-view", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(built.query), cache: "no-store",
    });
    const next = await response.json();
    const validation = validateApplicationResult(next);
    if (!response.ok || !validation.ok) throw new Error("query_rejected");
    closeDetails({restoreFocus: false});
    payload = next;
    activeQuery = built.query;
    writeState(state);
    renderResponsive();
    queryMessage.textContent = next.view.nodes.length ? "View updated." : "No nodes match this view.";
  } catch {
    queryMessage.textContent = "This view could not be loaded safely.";
    rejectView("The requested view is unavailable.");
  }
}

focusSelect.addEventListener("change", () => { hopSelect.disabled = !focusSelect.value; });
filterGroups.addEventListener("change", updateFilterCount);
document.querySelector("#update-view").addEventListener("click", () => applyState(readState()));
document.querySelector("#reset-query").addEventListener("click", () => {
  const mobile = window.innerWidth <= 600;
  const mobileFocusId = mobile ? buildScene(catalogView, {mobile: true}).focusId : null;
  applyState(defaultViewState(catalogView, {mobile, mobileFocusId}));
});

try {
  const response = await fetch(fixtureUrl, {cache: "no-store"});
  if (!response.ok) throw new Error("fixture_load_failed");
  const initial = await response.json();
  const validation = validateApplicationResult(initial);
  if (!validation.ok) throw new Error(validation.code);
  catalogView = structuredClone(initial.view);
  populateControls();
  const mobile = window.innerWidth <= 600;
  const mobileFocusId = mobile ? buildScene(catalogView, {mobile: true}).focusId : null;
  await applyState(defaultViewState(catalogView, {mobile, mobileFocusId}));
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderResponsive, 80); });
} catch (error) {
  showError("This graph could not be loaded safely.");
}
