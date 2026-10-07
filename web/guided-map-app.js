import {buildGuidedReviewRequest, buildLearningWorkspace, buildLinkingPhraseExercise, compareLinkingPhrase, evidenceLineNumbers, projectGraphFromGuidedMap, selectConcept, selectEdge, selectEvidence} from "./learning-workspace.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const outline = document.querySelector("#map-outline");
const relations = document.querySelector("#relationship-list");
const readerEvidence = document.querySelector("#reader-evidence");
const readerSource = document.querySelector("#reader-source");
const graphSvg = document.querySelector("#exploration-graph");
const graphDetail = document.querySelector("#graph-detail");
const status = document.querySelector("#map-status");
const focusQuestion = document.querySelector("#focus-question");
const mapTitle = document.querySelector("#map-title");
const counts = document.querySelector("#map-counts");
const readerTitle = document.querySelector("#reader-title");
const outlineTitle = document.querySelector("#outline-title");
const relationTitle = document.querySelector("#relation-title");
const explorationCanvas = document.querySelector("#exploration-canvas");
const selectionSummary = document.querySelector("#selection-summary");
const selectionCandidates = document.querySelector("#selection-candidates");
const practiceEdge = document.querySelector("#practice-edge");
const practicePrompt = document.querySelector("#practice-prompt");
const practiceInput = document.querySelector("#practice-input");
const practiceHintButton = document.querySelector("#practice-hint");
const practiceCheckButton = document.querySelector("#practice-check");
const practiceSaveButton = document.querySelector("#practice-save");
const practiceHintText = document.querySelector("#practice-hint-text");
const practiceMessage = document.querySelector("#practice-message");
const practiceResult = document.querySelector("#practice-result");
const tabs = [...document.querySelectorAll('[role="tab"]')];
const panels = [...document.querySelectorAll('[role="tabpanel"]')];
let workspace;
let selection;
let currentExercise;
let hintUsed = false;
let lastComparison = null;

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function textElement(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  return node;
}

function showView(name, {focus = false} = {}) {
  for (const tab of tabs) {
    const active = tab.dataset.view === name;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    if (active && focus) tab.focus();
  }
  for (const panel of panels) panel.hidden = panel.id !== `${name}-view`;
}

function renderGroup(group) {
  const article = document.createElement("article");
  article.className = "skeleton-stage";
  article.id = `stage-${group.order}`;
  const number = textElement("span", String(group.order).padStart(2, "0"), "stage-number");
  const content = document.createElement("div");
  content.append(textElement("h3", group.label));
  const concepts = document.createElement("div");
  concepts.className = "concept-list";
  for (const concept of group.concepts) {
    const details = document.createElement("details");
    details.className = "concept-card";
    details.dataset.conceptId = concept.id;
    const summary = document.createElement("summary");
    summary.textContent = concept.label;
    summary.addEventListener("click", () => setSelection(selectConcept(workspace, concept.id)));
    details.append(summary, textElement("p", concept.summary));
    concepts.append(details);
  }
  content.append(concepts);
  article.append(number, content);
  return article;
}

function renderEvidence(item) {
  const card = document.createElement("section");
  card.className = "evidence-card";
  card.dataset.evidenceId = item.id;
  card.append(textElement("p", item.proposition, "evidence-proposition"));
  const locator = textElement("p", `原文 ${item.locator.value}`, "source-locator");
  const excerpt = document.createElement("div");
  excerpt.className = "source-excerpt";
  for (const line of item.source_excerpt) {
    const row = document.createElement("div");
    row.className = "source-line";
    row.append(textElement("span", String(line.number), "line-number"), textElement("code", line.text || " "));
    excerpt.append(row);
  }
  card.append(locator, excerpt);
  return card;
}

function renderProposition(proposition, index) {
  const article = document.createElement("article");
  article.className = "relation-card";
  article.dataset.edgeId = proposition.edge_id;
  const choose = document.createElement("button");
  choose.type = "button";
  choose.className = "relation-header";
  choose.setAttribute("aria-label", `選取關係：${proposition.sentence}`);
  choose.append(textElement("span", String(index + 1).padStart(2, "0"), "relation-number"));
  const sentence = document.createElement("span");
  sentence.className = "teaching-sentence";
  sentence.append(
    textElement("strong", proposition.subject_label),
    textElement("span", proposition.linking_phrase, "linking-phrase"),
    textElement("strong", proposition.object_label),
  );
  choose.append(sentence);
  choose.addEventListener("click", () => setSelection(selectEdge(workspace, proposition.edge_id)));
  const details = document.createElement("details");
  details.className = "evidence-details";
  const summary = document.createElement("summary");
  summary.textContent = `查看原文證據（${proposition.evidence.length}）`;
  summary.addEventListener("click", () => setSelection(selectEdge(workspace, proposition.edge_id)));
  details.append(summary, ...proposition.evidence.map(renderEvidence));
  article.append(choose, details);
  return article;
}

function renderReader() {
  readerEvidence.replaceChildren(...workspace.evidence.map((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.evidenceId = item.id;
    button.append(textElement("strong", item.locator.value), textElement("span", item.proposition));
    button.addEventListener("click", () => setSelection(selectEvidence(workspace, item.id)));
    return button;
  }));
  const lines = workspace.source_text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  readerSource.replaceChildren(...lines.map((text, index) => {
    const row = document.createElement("div");
    row.className = "reader-line";
    row.dataset.line = String(index + 1);
    row.append(textElement("span", String(index + 1), "line-number"), textElement("code", text || " "));
    return row;
  }));
}

function graphPositions() {
  const positions = new Map();
  for (const group of workspace.groups) {
    const ids = new Set(group.concepts.map(({id}) => id));
    const neighbors = new Map(group.concepts.map(({id}) => [id, new Set()]));
    const outgoing = new Map(group.concepts.map(({id}) => [id, []]));
    const indegree = new Map(group.concepts.map(({id}) => [id, 0]));
    for (const proposition of workspace.propositions) {
      const {subject_concept_id: subject, object_concept_id: object} = proposition;
      if (!ids.has(subject) || !ids.has(object)) continue;
      neighbors.get(subject).add(object);
      neighbors.get(object).add(subject);
      outgoing.get(subject).push(object);
      indegree.set(object, indegree.get(object) + 1);
    }

    const remaining = new Set(ids);
    const components = [];
    while (remaining.size) {
      const start = [...remaining].sort()[0];
      const component = [];
      const stack = [start];
      remaining.delete(start);
      while (stack.length) {
        const id = stack.pop();
        component.push(id);
        for (const neighbor of neighbors.get(id)) {
          if (!remaining.has(neighbor)) continue;
          remaining.delete(neighbor);
          stack.push(neighbor);
        }
      }
      components.push(component.sort());
    }

    components.forEach((component, componentIndex) => {
      const componentIds = new Set(component);
      const componentIndegree = new Map(component.map((id) => [id, [...neighbors.get(id)].filter((candidate) => componentIds.has(candidate) && outgoing.get(candidate).includes(id)).length]));
      const ranks = new Map(component.map((id) => [id, 0]));
      const queue = component.filter((id) => componentIndegree.get(id) === 0).sort();
      const visited = new Set();
      while (queue.length) {
        const id = queue.shift();
        visited.add(id);
        for (const target of outgoing.get(id).filter((candidate) => componentIds.has(candidate)).sort()) {
          ranks.set(target, Math.max(ranks.get(target), ranks.get(id) + 1));
          componentIndegree.set(target, componentIndegree.get(target) - 1);
          if (componentIndegree.get(target) === 0) queue.push(target);
        }
        queue.sort();
      }
      if (visited.size !== component.length) component.forEach((id) => ranks.set(id, 0));
      const maxRank = Math.max(...ranks.values());
      const componentY = 70 + (group.order - 1) * 115 + (componentIndex - (components.length - 1) / 2) * 60;
      const byRank = new Map();
      for (const id of component) {
        const rank = ranks.get(id);
        if (!byRank.has(rank)) byRank.set(rank, []);
        byRank.get(rank).push(id);
      }
      for (const [rank, rankIds] of byRank) {
        rankIds.sort().forEach((id, index) => positions.set(id, {
          x: maxRank === 0 ? 500 : 150 + rank * (700 / maxRank),
          y: componentY + (index - (rankIds.length - 1) / 2) * 60,
        }));
      }
    });
  }
  return positions;
}

function renderGraph() {
  graphSvg.replaceChildren();
  const positions = graphPositions();
  const defs = svgElement("defs");
  const marker = svgElement("marker", {id: "workspace-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto"});
  marker.append(svgElement("path", {d: "M 0 0 L 8 4 L 0 8 z"}));
  defs.append(marker);
  graphSvg.append(defs);
  const links = svgElement("g", {class: "workspace-links"});
  for (const proposition of workspace.propositions) {
    const start = positions.get(proposition.subject_concept_id);
    const end = positions.get(proposition.object_concept_id);
    const group = svgElement("g", {class: "workspace-link", tabindex: "0", role: "button", "aria-label": proposition.sentence, "data-edge-id": proposition.edge_id});
    group.append(svgElement("line", {x1: start.x, y1: start.y, x2: end.x, y2: end.y, "marker-end": "url(#workspace-arrow)"}));
    group.append(svgElement("line", {class: "hit-area", x1: start.x, y1: start.y, x2: end.x, y2: end.y}));
    const label = svgElement("text", {x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 - 9});
    label.textContent = proposition.linking_phrase;
    group.append(label);
    const activate = () => setSelection(selectEdge(workspace, proposition.edge_id));
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); }
    });
    links.append(group);
  }
  graphSvg.append(links);
  const nodes = svgElement("g", {class: "workspace-nodes"});
  for (const concept of workspace.concepts) {
    const position = positions.get(concept.id);
    const group = svgElement("g", {class: "workspace-node", transform: `translate(${position.x} ${position.y})`, tabindex: "0", role: "button", "aria-label": `概念：${concept.label}`, "data-concept-id": concept.id});
    group.append(svgElement("rect", {x: -66, y: -25, width: 132, height: 50, rx: 14}));
    const label = svgElement("text", {y: 5});
    label.textContent = concept.label;
    group.append(label);
    const activate = () => setSelection(selectConcept(workspace, concept.id));
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); }
    });
    nodes.append(group);
  }
  graphSvg.append(nodes);
}

function renderGraphDetail() {
  graphDetail.replaceChildren();
  if (!selection?.concept_id) {
    graphDetail.append(textElement("p", "點一個概念或關係，這裡會顯示與另外兩個視圖相同的焦點。"));
    return;
  }
  const concept = workspace.concepts.find(({id}) => id === selection.concept_id);
  const proposition = workspace.propositions.find(({edge_id}) => edge_id === selection.edge_id);
  graphDetail.append(textElement("p", proposition ? "目前關係" : "目前概念", "detail-kicker"));
  graphDetail.append(textElement("h3", proposition?.sentence ?? concept.label));
  graphDetail.append(textElement("p", proposition ? `支持證據：${proposition.evidence.map(({locator}) => locator.value).join("、")}` : concept.summary));
  const sourceButton = textElement("button", "在閱讀中查看原文");
  sourceButton.type = "button";
  sourceButton.addEventListener("click", () => showView("reader", {focus: true}));
  graphDetail.append(sourceButton);
}

function setPracticeEdge(edgeId, {clear = true} = {}) {
  const built = buildLinkingPhraseExercise(workspace, edgeId);
  if (built.status !== "ready") return;
  currentExercise = built.exercise;
  practiceEdge.value = edgeId;
  practicePrompt.replaceChildren(
    textElement("strong", currentExercise.subject_label),
    textElement("span", "＿＿＿＿", "practice-blank"),
    textElement("strong", currentExercise.object_label),
  );
  practiceHintText.textContent = currentExercise.hint;
  if (clear) {
    practiceInput.value = "";
    practiceHintText.hidden = true;
    practiceHintButton.disabled = false;
    practiceSaveButton.disabled = true;
    hintUsed = false;
    lastComparison = null;
    practiceMessage.textContent = "";
    practiceResult.hidden = true;
    practiceResult.replaceChildren();
  }
}

function renderPracticeResult(comparison) {
  practiceMessage.textContent = comparison.matches_reviewed_phrase
    ? "你的關係詞和目前人工審核版本一致。"
    : "兩個說法目前不一致；先比較完整句子與原文，不把這次回答換算成理解分數。";
  practiceResult.replaceChildren(
    textElement("p", "教材中的完整關係", "detail-kicker"),
    textElement("h3", comparison.canonical_sentence),
    ...comparison.evidence.map(renderEvidence),
  );
  practiceResult.hidden = false;
  updateSelectionUI();
}

function updateSelectionUI() {
  if (!workspace || !selection) return;
  const proposition = workspace.propositions.find(({edge_id}) => edge_id === selection.edge_id);
  const concept = workspace.concepts.find(({id}) => id === selection.concept_id);
  const focusedEvidence = workspace.evidence.find(({id}) => selection.evidence_ids.length === 1 && id === selection.evidence_ids[0]);
  selectionSummary.textContent = proposition?.sentence ?? concept?.label ?? focusedEvidence?.label ?? "尚未選取概念或關係";
  selectionCandidates.replaceChildren();
  if (selection.candidate_edge_ids) {
    if (!selection.candidate_edge_ids.length) selectionCandidates.textContent = "此 Evidence 沒有對應 Claim，仍可獨立閱讀。";
    else {
      selectionCandidates.append(document.createTextNode(`對應 ${selection.candidate_edge_ids.length} 個 Claim：`));
      for (const edgeId of selection.candidate_edge_ids) {
        const candidate = workspace.propositions.find(({edge_id}) => edge_id === edgeId);
        const button = textElement("button", candidate.sentence);
        button.type = "button";
        button.addEventListener("click", () => setSelection(selectEdge(workspace, edgeId)));
        selectionCandidates.append(button);
      }
    }
  }
  for (const node of document.querySelectorAll("[data-concept-id]")) node.classList.toggle("is-selected", node.dataset.conceptId === selection.concept_id);
  for (const node of document.querySelectorAll("[data-edge-id]")) node.classList.toggle("is-selected", node.dataset.edgeId === selection.edge_id);
  const selectedEvidence = new Set(selection.evidence_ids);
  for (const node of document.querySelectorAll("[data-evidence-id]")) node.classList.toggle("is-selected", selectedEvidence.has(node.dataset.evidenceId));
  const selectedLines = new Set(evidenceLineNumbers(workspace, selection));
  for (const line of document.querySelectorAll(".reader-line")) line.classList.toggle("is-selected", selectedLines.has(Number(line.dataset.line)));
  if (selection.edge_id && practiceEdge.value !== selection.edge_id) setPracticeEdge(selection.edge_id);
  renderGraphDetail();
}

function setSelection(result) {
  if (result?.status !== "ready") return;
  selection = result.selection;
  updateSelectionUI();
}

for (const tab of tabs) {
  tab.addEventListener("click", () => showView(tab.dataset.view));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const index = tabs.indexOf(tab);
    const offset = event.key === "ArrowRight" ? 1 : -1;
    const next = tabs[(index + offset + tabs.length) % tabs.length];
    showView(next.dataset.view, {focus: true});
  });
}

practiceEdge.addEventListener("change", () => {
  setPracticeEdge(practiceEdge.value);
  setSelection(selectEdge(workspace, practiceEdge.value));
});
practiceHintButton.addEventListener("click", () => {
  if (!currentExercise) return;
  practiceHintText.hidden = false;
  practiceHintButton.disabled = true;
  hintUsed = true;
});
practiceInput.addEventListener("input", () => {
  lastComparison = null;
  practiceSaveButton.disabled = true;
});
practiceCheckButton.addEventListener("click", () => {
  const result = compareLinkingPhrase(currentExercise, practiceInput.value);
  if (result.status !== "ready") {
    practiceMessage.textContent = "先寫下一個關係詞，再和教材比較。";
    practiceResult.hidden = true;
    lastComparison = null;
    practiceSaveButton.disabled = true;
    return;
  }
  setSelection(selectEdge(workspace, currentExercise.edge_id));
  renderPracticeResult(result.comparison);
  lastComparison = result.comparison;
  practiceSaveButton.disabled = false;
});
practiceSaveButton.addEventListener("click", async () => {
  const built = buildGuidedReviewRequest(workspace, lastComparison, hintUsed);
  if (built.status !== "ready") {
    practiceMessage.textContent = "回答已變更，請先重新對照教材。";
    practiceSaveButton.disabled = true;
    return;
  }
  practiceSaveButton.disabled = true;
  practiceMessage.textContent = "正在保存這次練習…";
  try {
    const response = await fetch("/api/guided-reviews", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(built.request),
    });
    if (!response.ok) throw new Error("guided_review_rejected");
    const result = await response.json();
    if (!new Set(["recorded", "unchanged"]).has(result.status)) throw new Error("guided_review_invalid_response");
    practiceMessage.textContent = result.status === "recorded"
      ? "已保存為追加式練習紀錄；不會改寫教材或換算理解分數。"
      : "這次練習先前已保存；教材與既有紀錄都沒有被改寫。";
  } catch {
    practiceMessage.textContent = "尚未保存；請確認本機 KGnote 伺服器使用 Guided Review 設定。";
    practiceSaveButton.disabled = false;
  }
});

try {
  const [mapResponse, sourceResponse] = await Promise.all([
    fetch("./fixtures/os-overview-guided-map.json", {cache: "no-store"}),
    fetch("./fixtures/os-overview-review.md", {cache: "no-store"}),
  ]);
  if (!mapResponse.ok || !sourceResponse.ok) throw new Error("fixture_unavailable");
  const [mapModel, sourceText] = await Promise.all([mapResponse.json(), sourceResponse.text()]);
  if (await sha256Hex(sourceText) !== mapModel.source?.content_sha256) throw new Error("source_hash_mismatch");
  const graphModel = projectGraphFromGuidedMap(mapModel, "operating-systems");
  const result = buildLearningWorkspace(mapModel, graphModel, sourceText);
  if (result.status !== "ready") throw new Error(result.problem.code);
  workspace = result;
  selection = {source_id: workspace.source.id, focus_question: workspace.learning_unit.focus_question, concept_id: null, edge_id: null, evidence_ids: []};
  document.title = `KGnote · ${workspace.learning_unit.title}`;
  mapTitle.textContent = workspace.learning_unit.title;
  focusQuestion.textContent = workspace.learning_unit.focus_question;
  readerTitle.textContent = workspace.source.label;
  outlineTitle.textContent = `${workspace.groups.length} 階段輪廓`;
  relationTitle.textContent = `${workspace.propositions.length} 條核心關係`;
  explorationCanvas.setAttribute("aria-label", `${workspace.learning_unit.title}的局部知識圖`);
  counts.textContent = `${workspace.groups.length} 個階段 · ${workspace.concepts.length} 個概念 · ${workspace.propositions.length} 條關係`;
  outline.replaceChildren(...workspace.groups.map(renderGroup));
  relations.replaceChildren(...workspace.propositions.map(renderProposition));
  renderReader();
  renderGraph();
  practiceEdge.replaceChildren(...workspace.propositions.map((proposition) => new Option(`${proposition.subject_label} → ${proposition.object_label}`, proposition.edge_id)));
  setPracticeEdge(workspace.propositions[0].edge_id);
  updateSelectionUI();
  status.textContent = "三視圖已連接同一份教材";
} catch {
  status.textContent = "目前無法安全載入這份學習單元。";
  status.classList.add("error");
  outline.replaceChildren(textElement("p", "請確認本機 KGnote 伺服器仍在運行，再重新整理頁面。", "map-error"));
  relations.replaceChildren();
  readerEvidence.replaceChildren();
  readerSource.replaceChildren();
  graphSvg.replaceChildren();
}
