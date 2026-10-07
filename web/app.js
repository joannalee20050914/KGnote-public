import {buildScene, validateApplicationResult} from "./graph.js";
import {buildNodeDetails} from "./panel.js";
import {buildGraphViewQuery, defaultViewState, modeDescription} from "./filters.js";

const SVG_NS = "http://www.w3.org/2000/svg";
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
  const labels = {
    is_a: "是一種", part_of: "屬於", requires: "需要", maps_to: "對應",
    causes: "造成", contrasts_with: "對比", related_to: "相關",
    encountered: "曾接觸", asked_about: "曾提問", confused_with: "曾混淆",
    explained: "曾解釋", applied: "曾應用", demonstrated: "曾展現",
  };
  return link.relation ? (labels[link.relation] ?? link.relation.replaceAll("_", " ")) : "關係未定";
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
  row.append(textElement("strong", `學習證據 · ${item.locator.value}`), textElement("p", item.proposition));
  row.append(textElement("small", `教材位置：${item.locator.value}`));
  return row;
}

function eventLabel(eventType, fallback) {
  const labels = {exposure: "接觸紀錄", question: "提問紀錄", confusion: "困惑紀錄", explanation: "解釋紀錄", application: "應用紀錄", assessment: "複習紀錄"};
  return labels[eventType] ?? fallback;
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
  detailTitle.textContent = detail.kind === "learning_event" ? eventLabel(detail.event_type, detail.label) : detail.label;
  detailKind.textContent = detail.kind === "concept" ? "概念內容" : "學習事件";
  detailContent.replaceChildren();
  if (detail.kind === "concept") {
    detailContent.append(textElement("p", detail.summary, "detail-summary"));
    detailContent.append(textElement("p", `主題：${detail.spaces.join(", ") || "未分類"}`, "detail-meta"));
    const reviewButton = textElement("button", "複習這個概念", "review-start");
    reviewButton.type = "button";
    reviewButton.addEventListener("click", () => openReview(nodeId));
    detailContent.append(reviewButton);
  } else {
    detailContent.append(textElement("p", detail.context, "detail-summary"));
    detailContent.append(textElement("p", detail.occurred_at ?? "未記錄時間", "detail-meta"));
    detailContent.append(section("相關概念", detail.concepts, (item) => textElement("li", item.label), "這個畫面沒有相關概念。"));
  }
  detailContent.append(section("學習證據", detail.evidence, evidenceItem, "這個畫面沒有學習證據。"));
  detailContent.append(section("教材來源", detail.sources, (source) => {
    const row = document.createElement("li");
    const sourceKind = source.source_kind === "chatgpt_conversation" ? "ChatGPT 對話" : source.source_kind.replaceAll("_", " ");
    row.append(textElement("strong", source.label), textElement("small", `${sourceKind} · ${source.captured_at ?? "未記錄時間"}`));
    return row;
  }, "這個畫面沒有教材來源。"));
  detailContent.append(section("學習紀錄", detail.history, (event) => {
    const row = document.createElement("li");
    row.append(textElement("strong", eventLabel(event.event_type, event.label)), textElement("p", event.context), textElement("small", event.occurred_at ?? "未記錄時間"));
    return row;
  }, "這個畫面沒有學習紀錄。"));
  detailContent.append(section("曾出現的困惑", detail.known_confusion.evidence, evidenceItem, "目前沒有明確記錄的困惑。"));
  detailPanel.hidden = false;
  document.body.classList.add("detail-open");
  closeDetailButton.focus();
}

async function openReview(conceptId) {
  const old = detailContent.querySelector(".review-card");
  if (old) old.remove();
  const card = document.createElement("section");
  card.className = "review-card";
  card.append(textElement("p", "正在準備複習…", "review-status"));
  detailContent.prepend(card);
  try {
    const response = await fetch(`/api/review-prompt?concept_id=${encodeURIComponent(conceptId)}`, {cache: "no-store"});
    const prompt = await response.json();
    if (!response.ok || prompt.status !== "ready") throw new Error("prompt_unavailable");
    renderReviewForm(card, prompt);
  } catch {
    card.replaceChildren(textElement("p", "目前無法安全地準備這次複習。", "review-status"));
  }
}

function renderReviewForm(card, prompt) {
  const question = textElement("h3", prompt.question);
  const hint = textElement("p", prompt.hint, "review-hint");
  hint.hidden = true;
  const hintButton = textElement("button", "顯示提示", "review-secondary");
  hintButton.type = "button";
  let hintUsed = false;
  hintButton.addEventListener("click", () => { hintUsed = true; hint.hidden = false; hintButton.disabled = true; });
  const answer = document.createElement("textarea");
  answer.maxLength = 4000;
  answer.rows = 5;
  answer.placeholder = "用自己的話寫下答案…";
  answer.setAttribute("aria-label", "你的答案");
  const outcomes = document.createElement("select");
  outcomes.setAttribute("aria-label", "這次回答的結果");
  outcomes.append(new Option("對照證據後選擇…", ""), new Option("正確", "CORRECT"), new Option("部分正確", "PARTIAL"), new Option("不正確", "INCORRECT"), new Option("現有證據不足", "INSUFFICIENT_EVIDENCE"));
  const evidence = section("對照學習證據", prompt.evidence, evidenceItem, "目前沒有可對照的證據。 ");
  const save = textElement("button", "保存複習紀錄", "review-save");
  save.type = "button";
  const status = textElement("p", "先回答，再和證據比較並選擇結果。", "review-status");
  save.addEventListener("click", async () => {
    if (!answer.value.trim() || !outcomes.value) { status.textContent = "請填寫答案並選擇結果。"; return; }
    save.disabled = true;
    status.textContent = "正在保存…";
    try {
      const response = await fetch("/api/reviews", {method: "POST", headers: {"Content-Type": "application/json"}, cache: "no-store", body: JSON.stringify({concept_id: prompt.concept_id, question: prompt.question, response: answer.value, hint_used: hintUsed, outcome: outcomes.value, snapshot_sha256: prompt.snapshot_sha256, evidence_ids: prompt.evidence_ids})});
      const result = await response.json();
      if (!response.ok || !["recorded", "unchanged"].includes(result.status)) throw new Error("save_rejected");
      status.textContent = result.status === "recorded" ? "已保存為新的學習紀錄。" : "這筆複習已經保存。";
      answer.disabled = outcomes.disabled = hintButton.disabled = save.disabled = true;
    } catch { status.textContent = "複習尚未保存，請重新載入後再試一次。"; save.disabled = false; }
  });
  const previous = section("過去的複習", prompt.previous_reviews ?? [], (item) => {
    const row = document.createElement("li");
    row.append(textElement("strong", `${item.outcome.replaceAll("_", " ")} · ${item.occurred_at}`), textElement("p", item.response), textElement("small", item.hint_used ? "使用過提示" : "未使用提示"));
    return row;
  }, "還沒有這個概念的複習紀錄。 ");
  card.replaceChildren(question, hintButton, hint, answer, outcomes, evidence, save, status, previous);
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
    const displayLabel = node.kind === "learning_event" ? eventLabel(node.event_type, node.label) : node.label;
    const group = element("g", {
      class: `graph-node ${node.kind}${node.focused ? " focused" : ""}`,
      transform: `translate(${node.x} ${node.y})`,
      "data-id": node.id,
      tabindex: 0,
      role: "img",
      "aria-label": `${node.kind === "concept" ? "概念" : "學習事件"}：${displayLabel}`,
    });
    group.append(element(node.kind === "concept" ? "circle" : "rect", node.kind === "concept" ? {r: 52} : {x: -74, y: -38, width: 148, height: 76, rx: 19}));
    const title = element("title");
    title.textContent = `${displayLabel} · ${node.id}`;
    group.append(title);
    const label = element("text", {class: "node-label", y: node.kind === "concept" ? 74 : 61});
    label.textContent = displayLabel;
    group.append(label);
    nodes.append(group);
    const activate = () => openDetails(node.id, group);
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); }
    });
  }
  svg.append(nodes);
  modeLabel.textContent = activeQuery ? (activeQuery.focus_node_id ? `局部 · ${activeQuery.hop_depth} 層` : "完整知識圖") : (scene.mode === "local" ? "局部 · 1 層" : "完整知識圖");
  countLabel.textContent = `${scene.nodes.length} 個節點 · ${scene.links.length} 條關係`;
  message.hidden = scene.nodes.length > 0;
  if (!scene.nodes.length) message.textContent = "沒有符合目前條件的節點。";
}

closeDetailButton.addEventListener("click", () => closeDetails());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !detailPanel.hidden) closeDetails();
});

function showError(text) {
  message.textContent = text;
  message.hidden = false;
  svg.replaceChildren();
  countLabel.textContent = "知識圖無法使用";
}

function rejectView(text) {
  closeDetails({restoreFocus: false});
  payload = null;
  activeQuery = null;
  modeLabel.textContent = "畫面無法使用";
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
  focusSelect.replaceChildren(new Option("完整知識圖", ""));
  for (const node of catalogView.nodes) focusSelect.append(new Option(`${node.kind === "learning_event" ? eventLabel(node.event_type, node.label) : node.label} · ${node.kind === "concept" ? "概念" : "學習事件"}`, node.id));
  const labels = {node_kinds: "節點種類", edge_classes: "關係分類", relations: "關係", spaces: "主題"};
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
    if (!values.length) options.append(textElement("span", "目前沒有選項", "empty-state"));
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
  filterCount.textContent = count ? `已啟用 ${count} 項` : "未啟用";
}

async function applyState(state) {
  const built = buildGraphViewQuery(catalogView, state);
  if (built.status !== "ready") {
    queryMessage.textContent = "目前無法使用這組檢視條件。";
    rejectView("無法顯示要求的知識圖。 ");
    return;
  }
  queryMessage.textContent = "正在載入知識圖…";
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
    queryMessage.textContent = next.view.nodes.length ? "畫面已更新。" : "沒有符合目前條件的節點。";
  } catch {
    queryMessage.textContent = "目前無法安全載入這個畫面。";
    rejectView("無法顯示要求的知識圖。 ");
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
  const response = await fetch("/api/graph-view", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: "null", cache: "no-store",
  });
  if (!response.ok) throw new Error("catalog_load_failed");
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
  showError("目前無法安全載入知識圖。 ");
}
