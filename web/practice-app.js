import {buildAttemptRequest, groupedItems, newAttemptId, safePracticeItem} from "./practice-workspace.js";

const byId = id => document.getElementById(id);
const parameters = new URLSearchParams(location.search);
const unitSlug = parameters.get("unit") || "os";
const entryKind = parameters.get("entry") === "scheduled" ? "scheduled_review" : "voluntary_practice";
const dueId = entryKind === "scheduled_review" ? parameters.get("due") : null;
const requestedItemId = parameters.get("item");
let practiceSet;
let activeItems = [];
let currentItem;
let attemptId = null;
let startedAt = null;
let hintEvents = [];
let submitted = false;
let submissionAt = null;
let draftTimer = null;

function element(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function now() { return new Date().toISOString(); }

function ensureAttempt() {
  if (!attemptId) { attemptId = newAttemptId(); startedAt = now(); }
}

function currentOutcome(response) {
  return response.trim() === "不知道" ? "INCORRECT" : "INSUFFICIENT_EVIDENCE";
}

async function persist(state) {
  ensureAttempt();
  const responseText = byId("practice-answer").value;
  if (state === "submitted" && !submissionAt) submissionAt = now();
  const submittedAt = state === "submitted" ? submissionAt : null;
  const built = buildAttemptRequest({
    attemptId, item: currentItem, startedAt, response: responseText, confidence: byId("confidence").value,
    hintEvents, state, submittedAt, outcome: state === "submitted" ? currentOutcome(responseText) : null,
    entryKind, dueId,
  });
  if (built.status !== "ready") throw new Error(built.problem.code);
  const response = await fetch(`/api/attempts/${encodeURIComponent(attemptId)}`, {
    method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(built.request),
  });
  const body = await response.json();
  if (!response.ok || !["saved", "unchanged"].includes(body.status)) throw new Error(body.problem?.code ?? `http_${response.status}`);
  return body;
}

function resetAttempt() {
  attemptId = null; startedAt = null; hintEvents = []; submitted = false; submissionAt = null;
  byId("practice-answer").value = ""; byId("confidence").value = "";
  byId("hint-text").hidden = true; byId("hint-text").textContent = "";
  byId("hint-button").disabled = false; byId("submit-button").disabled = false;
  byId("reveal-panel").hidden = true; byId("attempt-status").textContent = "尚未建立 Attempt；開始輸入或要求提示後才會建立。";
  byId("assessment-status").textContent = ""; byId("disagree").checked = false; byId("correction").value = ""; byId("correction-label").hidden = true;
  document.querySelectorAll("[data-outcome]").forEach(item => { item.disabled = false; });
}

function selectItem() {
  currentItem = activeItems.find(item => item.item_id === byId("item-select").value);
  if (!currentItem) return;
  byId("practice-prompt").textContent = currentItem.prompt;
  resetAttempt();
}

function startActivity(activity) {
  activeItems = groupedItems(practiceSet.items)[activity];
  byId("item-select").replaceChildren(...activeItems.map(item => new Option(item.label, item.item_id)));
  byId("activity-label").textContent = {relation_recall: "關係／概念回想", free_explanation: "自由解釋", application_prediction: "應用／預測", distinction: "辨別差異"}[activity];
  byId("practice-picker").hidden = true; byId("attempt-panel").hidden = false;
  selectItem(); byId("practice-answer").focus();
}

async function loadHistory() {
  const response = await fetch(`/api/attempts?learning_unit_id=${encodeURIComponent(practiceSet.learning_unit_id)}`, {cache: "no-store"});
  const body = await response.json();
  if (!response.ok || body.status !== "ready") throw new Error(body.problem?.code ?? "history_unavailable");
  const container = byId("attempt-history"); container.replaceChildren();
  if (!body.attempts.length) { container.append(element("p", "目前沒有 Attempt。只閱讀不會自動建立紀錄。")); return; }
  for (const attempt of body.attempts) {
    const card = element("article", undefined, "history-card");
    const assessed = attempt.feedback?.latest?.outcome;
    const state = attempt.state === "submitted" ? `已提交 · ${assessed ? `自評 ${assessed}` : "等待自評"}` : attempt.state === "draft" ? "未提交 draft（不算錯）" : "已取消";
    card.append(element("strong", `${attempt.activity_type} · ${state}`), element("p", attempt.raw_response || "（尚未輸入文字）"));
    if (attempt.feedback?.latest) card.append(element("p", `自評：${attempt.feedback.latest.outcome}${attempt.feedback.latest.disagrees ? " · 已提出修正" : ""}`, "mapping-note"));
    card.append(element("code", attempt.attempt_id));
    card.dataset.attemptId = attempt.attempt_id;
    container.append(card);
  }
}

function renderReveal(reveal) {
  byId("canonical-answer").textContent = reveal.canonical_answer;
  byId("feedback").textContent = reveal.feedback;
  byId("rubric-list").replaceChildren(...reveal.rubric.map(text => element("li", text)));
  const evidenceContainer = byId("reveal-evidence"); evidenceContainer.replaceChildren();
  for (const item of reveal.evidence) {
    const card = element("article", undefined, "evidence-card");
    card.append(element("strong", `Evidence · ${item.locator.value}`), element("p", item.proposition));
    evidenceContainer.append(card);
  }
  byId("reveal-panel").hidden = false;
}

for (const button of document.querySelectorAll("[data-activity]")) button.addEventListener("click", () => startActivity(button.dataset.activity));
byId("item-select").addEventListener("change", selectItem);
byId("practice-answer").addEventListener("input", () => {
  if (submitted) return;
  ensureAttempt(); byId("attempt-status").textContent = "正在保存 draft…";
  clearTimeout(draftTimer);
  draftTimer = setTimeout(() => persist("draft").then(() => { byId("attempt-status").textContent = "Draft 已保存；離開不會算錯。"; loadHistory(); }).catch(error => { byId("attempt-status").textContent = `Draft 尚未保存：${error.message}`; }), 250);
});
byId("hint-button").addEventListener("click", async () => {
  if (submitted) return;
  ensureAttempt(); hintEvents.push({kind: "requested", occurred_at: now()});
  byId("hint-text").textContent = currentItem.hint; byId("hint-text").hidden = false; byId("hint-button").disabled = true;
  try { await persist("draft"); byId("attempt-status").textContent = "提示使用已記錄，draft 已保存。"; await loadHistory(); }
  catch (error) { byId("attempt-status").textContent = `提示紀錄尚未保存：${error.message}`; }
});
byId("submit-button").addEventListener("click", async () => {
  clearTimeout(draftTimer);
  if (!byId("practice-answer").value.trim()) { byId("attempt-status").textContent = "請輸入回答；也可以直接寫「不知道」。"; return; }
  byId("submit-button").disabled = true; byId("attempt-status").textContent = "正在提交並保存…";
  try {
    const body = await persist("submitted"); submitted = true; renderReveal(body.reveal);
    byId("attempt-status").textContent = "Attempt 已保存。答案與 Evidence 現在才揭露。";
    await loadHistory();
  } catch (error) { byId("submit-button").disabled = false; byId("attempt-status").textContent = `提交失敗，回答仍在畫面上：${error.message}`; }
});
byId("retry-button").addEventListener("click", () => { resetAttempt(); byId("practice-answer").focus(); });
byId("disagree").addEventListener("change", () => { byId("correction-label").hidden = !byId("disagree").checked; });
for (const button of document.querySelectorAll("[data-outcome]")) button.addEventListener("click", async () => {
  if (!submitted || !attemptId) return;
  const disagrees = byId("disagree").checked, correction = byId("correction").value.trim();
  if (disagrees && !correction) { byId("assessment-status").textContent = "提出異議時請留下修正理由。"; return; }
  button.disabled = true; byId("assessment-status").textContent = "正在追加自評…";
  const payload = {schema_version: "kgnote.attempt-feedback-request.v1", assessment_id: `assessment_${crypto.randomUUID().replaceAll("-", "")}`, attempt_id: attemptId, outcome: button.dataset.outcome, disagrees, correction: correction || null, occurred_at: now()};
  try {
    const response = await fetch(`/api/attempts/${encodeURIComponent(attemptId)}/feedback`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)}); const body = await response.json();
    if (!response.ok || !["recorded", "unchanged"].includes(body.status)) throw new Error(body.problem?.code ?? `http_${response.status}`);
    byId("assessment-status").textContent = `自評已保存；下一次排程：${body.schedule?.due?.due_at ?? "本組 milestones 已完成"}。`;
    document.querySelectorAll("[data-outcome]").forEach(item => { item.disabled = true; }); await loadHistory();
  } catch (error) { button.disabled = false; byId("assessment-status").textContent = `自評未保存：${error.message}`; }
});
byId("refresh-history").addEventListener("click", () => loadHistory().catch(error => { byId("attempt-history").textContent = `讀取失敗：${error.message}`; }));

try {
  byId("back-to-learn").href = `./learn.html?unit=${encodeURIComponent(unitSlug)}`;
  const response = await fetch(`/api/practice-items?unit=${encodeURIComponent(unitSlug)}`, {cache: "no-store"});
  const body = await response.json();
  if (!response.ok || body.status !== "ready" || !body.items.every(safePracticeItem)) throw new Error(body.problem?.code ?? "unsafe_practice_set");
  practiceSet = body;
  await loadHistory();
  if (requestedItemId) {
    const requested = body.items.find(item => item.item_id === requestedItemId);
    if (!requested) throw new Error("scheduled_item_unavailable");
    startActivity(requested.activity_type); byId("item-select").value = requested.item_id; selectItem();
  }
} catch (error) {
  byId("practice-picker").replaceChildren(element("p", `Practice 無法安全載入：${error.message}`, "fatal"));
  byId("attempt-history").replaceChildren();
}
