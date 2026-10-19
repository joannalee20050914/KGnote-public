import {buildLearnWorkspace, claimsForEvidence, conceptDetail, glossesForScope, sourceLines, structureChildren} from "./learn-workspace.js";

const byId = id => document.getElementById(id);
const unitSlug = new URLSearchParams(location.search).get("unit") || "os";
let workspace;
let currentNode = null; let currentBreadcrumb = []; let currentSelected = null;
const resumeNodeId = new URLSearchParams(location.search).get("resume");

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function locatorStart(locator) { return Number(/^L(\d+)-L\d+$/.exec(locator?.value ?? "")?.[1] ?? 1); }
function eventId(){return `resume_${crypto.randomUUID().replaceAll("-","")}`;}
async function persistResume(question = null) {
  if (!currentNode) return;
  const request={schema_version:"kgnote.resume-context-save-request.v1",event_id:eventId(),learning_unit_id:workspace.learning_unit.id,unit_slug:unitSlug,source_scope:{source_id:workspace.source.id,locator:currentNode.source_anchors[0].locator.value},structural_breadcrumb:currentBreadcrumb.map(item=>({node_id:item.id,title:item.title})),selected:currentSelected,unresolved_question:question?.trim()||null,occurred_at:new Date().toISOString()};
  const response=await fetch("/api/resume-contexts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(request)}); const body=await response.json(); if(!response.ok) throw new Error(body.problem?.code??"resume unavailable");
}
function selectForResume(kind,id,label){currentSelected={kind,id,label};void persistResume(byId("resume-question")?.value).catch(()=>{});}

function evidenceCard(item) {
  const card = element("article", undefined, "evidence-card");
  const heading = element("div", undefined, "evidence-heading");
  heading.append(element("strong", "Supporting Evidence"), element("code", item.locator.value));
  card.append(heading, element("p", item.proposition));
  const lines = element("div", undefined, "evidence-lines");
  for (const line of sourceLines(workspace.source_text, item.locator)) {
    const row = element("div", undefined, "source-line");
    row.append(element("span", String(line.number)), element("code", line.text || " ")); lines.append(row);
  }
  card.append(lines);
  const mapping = claimsForEvidence(workspace, item.id);
  card.append(element("p", mapping.claims.length ? `對應 ${mapping.claims.length} 個 Claim：${mapping.claims.map(claim => claim.sentence).join("；")}` : "沒有對應 Claim；Evidence 仍可獨立閱讀。", "mapping-note"));
  return card;
}

function renderConcept(conceptId) {
  const result = conceptDetail(workspace, conceptId); if (result.status !== "ready") return;
  const panel = byId("detail-panel");
  selectForResume("concept",conceptId,result.concept.label);
  panel.replaceChildren(element("p", "CONCEPT · 你主動開啟", "eyebrow"), element("h2", result.concept.label), element("p", result.concept.summary, "concept-summary"));
  if (result.claims.length) {
    panel.append(element("h3", "可展開的 reviewed 關係"));
    for (const claim of result.claims) { const button = element("button", claim.sentence, "claim-button"); button.type = "button"; button.addEventListener("click", () => renderClaim(claim.edge_id)); panel.append(button); }
  }
  panel.append(element("h3", "來源與 Evidence"), ...result.evidence.map(evidenceCard));
}

function renderClaim(edgeId) {
  const claim = workspace.propositions.find(item => item.edge_id === edgeId); if (!claim) return;
  const panel = byId("detail-panel"); const blocked = claim.review?.teaching_answer_status !== "ready";
  selectForResume("claim",edgeId,claim.sentence);
  panel.replaceChildren(element("p", "CLAIM · 你主動開啟", "eyebrow"), element("h2", claim.sentence), element("p", blocked ? "此主張仍可讀，但不可作為 Practice 答案或 Local Graph 的可靠關係。" : "這條關係已通過目前人工審查。", blocked ? "warning-inline" : "concept-summary"));
  if (blocked) panel.append(element("p", claim.review?.reason ?? "審查資料不足。", "review-reason"));
  panel.append(element("h3", "Supporting Evidence 與 exact locator"), ...claim.evidence.map(evidenceCard));
}

function renderGloss(gloss) {
  const panel = byId("detail-panel");
  selectForResume("gloss",gloss.id,gloss.term);
  panel.replaceChildren(element("p", "CONTEXT GLOSS", "eyebrow"), element("h2", gloss.term), element("p", `目前只需要：${gloss.required_depth.toUpperCase()}`, "depth-badge"), element("p", gloss.minimum_explanation, "concept-summary"), element("h3", "為什麼此處需要"), element("p", gloss.why_needed_here), element("p", `${gloss.provenance.label} · ${gloss.locator.value}`, "mapping-note"));
  const detail = element("details"); detail.append(element("summary", "較深入解說（按需）"), element("p", gloss.detailed_explanation)); panel.append(detail);
  const deferred = element("details"); deferred.append(element("summary", "現在可先不學"), element("p", gloss.defer_for_now.join("、"))); panel.append(deferred);
  const prior = workspace.reading_assist.prior_knowledge.filter(item => item.current_gloss_id === gloss.id);
  if (prior.length) { panel.append(element("h3", "先備知識連結")); for (const item of prior) { const card = element("article", undefined, "evidence-card"); card.append(element("strong", item.prior_title), element("p", item.summary), element("blockquote", item.source_excerpt), element("p", `${item.provenance.kind} · ${item.source_locator.value}`, "mapping-note")); panel.append(card); } }
  const encounters = (workspace.reading_assist.prior_encounters??[]).filter(item=>item.gloss_id===gloss.id);
  if(encounters.length){panel.append(element("h3","先前實際接觸"));for(const item of encounters){const card=element("article",undefined,"evidence-card");card.append(element("strong",`${item.kind} · ${item.occurred_at}`),element("p",`來自另一學習單元的事件紀錄：${item.source_refs.join("、")}`),element("p","只表示曾發生此事件，不代表已理解。","mapping-note"));panel.append(card);}}
}

function renderLocalGraph(node) {
  const section = element("section", undefined, "local-graph"); section.append(element("h3", "Local Graph · 此閱讀 scope"));
  const claims = workspace.propositions.filter(item => node.claim_refs.includes(item.edge_id) && item.review?.teaching_answer_status === "ready");
  if (!claims.length) section.append(element("p", "此 scope 沒有可安全投影的 reviewed relation。"));
  for (const claim of claims) { const button = element("button", claim.sentence, "graph-edge"); button.type = "button"; button.addEventListener("click", () => renderClaim(claim.edge_id)); section.append(button); }
  const excluded = node.claim_refs.length - claims.length; if (excluded) section.append(element("p", `${excluded} 條 disputed／未完成關係已排除。`, "warning-inline")); byId("detail-panel").append(section);
}

function focusStructure(node, shouldPersist = true) {
  const ancestors = []; let current = node;
  while (current) { ancestors.unshift(current); current = workspace.structure.nodes.find(item => item.id === current.parent_id); }
  currentNode=node; currentBreadcrumb=ancestors; currentSelected={kind:"structure",id:node.id,label:node.title};
  byId("breadcrumb").textContent = `${workspace.source.label} / ${ancestors.map(item=>item.title).join(" / ")}`;
  document.querySelectorAll(".structure-button").forEach(button => button.setAttribute("aria-current", button.dataset.nodeId === node.id ? "true" : "false"));
  byId("source-body").querySelector(`[data-line="${locatorStart(node.source_anchors[0]?.locator)}"]`)?.scrollIntoView({behavior: "smooth", block: "start"});
  document.querySelectorAll(".source-line.active-scope").forEach(item => item.classList.remove("active-scope"));
  for (const anchor of node.source_anchors) { const match = /^L(\d+)-L(\d+)$/.exec(anchor.locator.value); if (!match) continue; for (let line = Number(match[1]); line <= Number(match[2]); line += 1) byId("source-body").querySelector(`[data-line="${line}"]`)?.classList.add("active-scope"); }
  const panel = byId("detail-panel"); panel.replaceChildren(element("p", "READING ASSIST · CURRENT SCOPE", "eyebrow"), element("h2", node.title), element("p", `${node.organizing_relation} · ${node.source_anchors.map(item => item.locator.value).join(", ")}`, "mapping-note"));
  const relevantGlosses = glossesForScope(workspace, node);
  if (relevantGlosses.length) { panel.append(element("h3", "此段需要的 Context Gloss")); for (const gloss of relevantGlosses) { const button = element("button", `${gloss.term} · ${gloss.required_depth}`, "claim-button"); button.type = "button"; button.addEventListener("click", () => renderGloss(gloss)); panel.append(button); } } else panel.append(element("p", "這一段沒有必要的額外 gloss；不因為出現 Concept 就自動加入字典。"));
  if (node.concept_refs.length) { panel.append(element("h3", "此 scope 的 Concept（按需開啟）")); for (const id of node.concept_refs) { const concept = workspace.concepts.find(item => item.id === id); if (!concept) continue; const button = element("button", concept.label, "claim-button"); button.type = "button"; button.addEventListener("click", () => renderConcept(id)); panel.append(button); } }
  renderLocalGraph(node);
  if (shouldPersist) void persistResume(byId("resume-question")?.value).catch(()=>{byId("resume-status").textContent="續學點暫時無法保存；閱讀仍可繼續。";});
}

function renderTree(parentId, container, depth = 0) {
  for (const node of structureChildren(workspace, parentId)) { const row = element("div", undefined, "structure-row"); row.style.setProperty("--depth", depth); const button = element("button", node.title, "structure-button"); button.type = "button"; button.dataset.nodeId = node.id; button.addEventListener("click", () => focusStructure(node)); row.append(button); container.append(row); renderTree(node.id, container, depth + 1); }
}

function renderSource() {
  const lines = workspace.source_text.split("\n"); if (lines.at(-1) === "") lines.pop();
  for (const [index, text] of lines.entries()) { const row = element("div", undefined, "source-line"); row.dataset.line = String(index + 1); row.append(element("span", String(index + 1)), element("code", text || " ")); for (const gloss of workspace.reading_assist.glosses.filter(item => locatorStart(item.locator) === index + 1)) { const button = element("button", `解釋 ${gloss.term}`, "inline-gloss"); button.type = "button"; button.addEventListener("click", () => renderGloss(gloss)); row.append(button); } byId("source-body").append(row); }
  const disputed = workspace.propositions.find(item => item.review?.teaching_answer_status === "blocked");
  if (disputed) { const warning = byId("claim-warning"); warning.hidden = false; warning.append(element("strong", "教材勘誤提醒："), document.createTextNode(`「${disputed.sentence}」待修訂，保留原文但不出題。`)); warning.addEventListener("click", () => renderClaim(disputed.edge_id)); }
}

try {
  const response = await fetch(`/api/learning-units/${encodeURIComponent(unitSlug)}`, {cache: "no-store"}); const bundle = await response.json();
  if (!response.ok || bundle.status !== "ready") throw new Error(bundle.problem?.code ?? "unit_unavailable");
  const result = buildLearnWorkspace(bundle.model, bundle.claim_reviews, bundle.source_text, bundle.structure, bundle.reading_assist); if (result.status !== "ready") throw new Error(result.problem.code); workspace = result;
  document.title = `KGnote · ${workspace.source.label}`; byId("source-title").textContent = workspace.source.label; byId("focus-question").textContent = workspace.learning_unit.focus_question;
  const practiceHref = `./practice.html?unit=${encodeURIComponent(unitSlug)}`; byId("practice-link").href = practiceHref; byId("top-practice-link").href = practiceHref;
  const noteParameters = new URLSearchParams({note_id: `note_${unitSlug}_learning_workspace`, notebook_id: "notebook_local", learning_unit_id: workspace.learning_unit.id, title: `${workspace.source.label}閱讀筆記與疑問`, source_id: workspace.source.id, locator: workspace.learning_unit.source_locator.value, source_label: workspace.source.label}); byId("note-link").href = `./learning-note.html?${noteParameters}`;
  renderSource(); renderTree(null, byId("structure-tree")); const resumeNode=workspace.structure.nodes.find(item=>item.id===resumeNodeId); focusStructure(resumeNode??structureChildren(workspace, null)[0],false);
  if(resumeNode){try{const resumeResponse=await fetch(`/api/resume-contexts?learning_unit_id=${encodeURIComponent(workspace.learning_unit.id)}`,{cache:"no-store"});const resumeBody=await resumeResponse.json();const saved=resumeBody.context;if(resumeResponse.ok&&saved?.structural_breadcrumb?.at(-1)?.node_id===resumeNode.id)byId("resume-question").value=saved.unresolved_question??"";}catch{} }
  const degraded = bundle.degradations?.map(item => item.component) ?? [];
  byId("load-status").textContent = degraded.length ? `閱讀可繼續 · ${degraded.join("、")} 暫時降級` : resumeNode?"已回到上次的精確閱讀位置":"閱讀模式 · 結構導航不改寫知識圖";
} catch (error) { byId("load-status").textContent = "教材未能安全載入"; byId("learn-root").replaceChildren(element("p", `請確認 KGnote server 正在運行，再重新載入。（${error.message}）`, "fatal")); }
byId("save-resume")?.addEventListener("click",async()=>{try{await persistResume(byId("resume-question").value);byId("resume-status").textContent="已保存此位置與未解問題；下次可從這裡接續。";}catch{byId("resume-status").textContent="續學點暫時無法保存；你的輸入仍留在畫面，可先複製或稍後重試。";}});
