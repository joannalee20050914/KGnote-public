export function parseMarkdownBlocks(markdown) {
  const blocks = [];
  let paragraph = [];
  let list = [];
  const flushParagraph = () => { if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ") }); paragraph = []; };
  const flushList = () => { if (list.length) blocks.push({ type: "list", items: list }); list = []; };
  for (const rawLine of String(markdown).split(/\r?\n/)) {
    const heading = /^(#{1,6})\s+(.+)$/.exec(rawLine);
    const item = /^\s*[-*+]\s+(.+)$/.exec(rawLine);
    if (heading) { flushParagraph(); flushList(); blocks.push({ type: "heading", level: heading[1].length, text: heading[2] }); }
    else if (item) { flushParagraph(); list.push(item[1]); }
    else if (!rawLine.trim()) { flushParagraph(); flushList(); }
    else { flushList(); paragraph.push(rawLine.trim()); }
  }
  flushParagraph(); flushList();
  return blocks;
}

export function buildSaveRequest(values, saveId) {
  return {
    schema_version: "kgnote.learning-note-save.v1",
    note_id: values.noteId,
    notebook_id: values.notebookId,
    learning_unit_id: values.learningUnitId,
    title: values.title,
    source_anchors: values.sourceId && values.locator && values.anchorLabel ? [{
      id: "anchor_primary", source_id: values.sourceId,
      locator: { kind: "line_range", value: values.locator }, label: values.anchorLabel,
    }] : [],
    markdown: values.markdown,
    save_id: saveId,
  };
}

export function noteApiPath(noteId) {
  return `/api/notes/${encodeURIComponent(noteId)}`;
}

function renderPreview(container, markdown) {
  container.replaceChildren();
  for (const block of parseMarkdownBlocks(markdown)) {
    let element;
    if (block.type === "heading") element = document.createElement(`h${block.level}`);
    else if (block.type === "list") {
      element = document.createElement("ul");
      for (const text of block.items) { const item = document.createElement("li"); item.textContent = text; element.append(item); }
    } else element = document.createElement("p");
    if (block.type !== "list") element.textContent = block.text;
    container.append(element);
  }
}

function init() {
  const byId = id => document.getElementById(id);
  const fields = {
    noteId: byId("note-id"), notebookId: byId("notebook-id"), learningUnitId: byId("learning-unit-id"),
    title: byId("note-title"), markdown: byId("note-markdown"), sourceId: byId("anchor-source-id"),
    locator: byId("anchor-locator"), anchorLabel: byId("anchor-label"),
  };
  const status = byId("note-status");
  const revision = byId("revision-label");
  const conflict = byId("conflict-box");
  let etag = "*";
  let currentRevision = null;
  let pendingSave = null;
  let pendingSignature = null;

  const parameters = new URLSearchParams(location.search);
  const parameterFields = {
    note_id: fields.noteId, notebook_id: fields.notebookId,
    learning_unit_id: fields.learningUnitId, title: fields.title,
    source_id: fields.sourceId, locator: fields.locator, source_label: fields.anchorLabel,
  };
  for (const [name, field] of Object.entries(parameterFields)) {
    const value = parameters.get(name);
    if (value !== null && value.length <= 240) field.value = value;
  }

  const values = () => Object.fromEntries(Object.entries(fields).map(([key, element]) => [key, element.value]));
  const preview = () => renderPreview(byId("note-preview"), fields.markdown.value);
  const setStatus = (message, isError = false) => { status.textContent = message; status.style.color = isError ? "#8c3f28" : ""; };
  const newSaveId = () => `save_${crypto.randomUUID().replaceAll("-", "")}`;

  async function loadNote(noteId = fields.noteId.value) {
    setStatus("正在讀取…");
    const response = await fetch(noteApiPath(noteId), { headers: { Accept: "application/json" } });
    const body = await response.json();
    if (response.status === 404) { etag = "*"; currentRevision = null; revision.textContent = "新筆記"; setStatus("尚未建立，可直接保存"); return; }
    if (!response.ok || body.status !== "ready") throw new Error(body.problem?.code || "note_load_failed");
    const note = body.note;
    fields.noteId.value = note.id; fields.notebookId.value = note.notebook_id; fields.learningUnitId.value = note.learning_unit_id;
    fields.title.value = note.title; fields.markdown.value = note.markdown;
    const anchor = note.source_anchors[0];
    fields.sourceId.value = anchor?.source_id || ""; fields.locator.value = anchor?.locator?.value || ""; fields.anchorLabel.value = anchor?.label || "";
    etag = response.headers.get("ETag") || body.etag; currentRevision = note.revision;
    pendingSave = null; pendingSignature = null;
    revision.textContent = `revision ${currentRevision}`; conflict.hidden = true; preview(); setStatus("已重開目前版本");
  }

  async function save() {
    conflict.hidden = true; setStatus("正在保存…");
    const currentValues = values();
    const signature = JSON.stringify(currentValues);
    const request = pendingSave && pendingSignature === signature
      ? pendingSave
      : buildSaveRequest(currentValues, newSaveId());
    pendingSave = request; pendingSignature = signature;
    let response;
    try {
      response = await fetch(noteApiPath(request.note_id), {
        method: "PUT", headers: { "Content-Type": "application/json", "If-Match": etag }, body: JSON.stringify(request),
      });
    } catch { setStatus("網路中斷；文字仍在編輯器。請稍後以同一畫面再保存。", true); return; }
    const body = await response.json();
    if (response.status === 412) { pendingSave = null; pendingSignature = null; conflict.hidden = false; setStatus("保存衝突，未覆寫伺服器版本", true); return; }
    if (!response.ok || !["saved", "unchanged"].includes(body.status)) { pendingSave = null; pendingSignature = null; setStatus(`保存失敗：${body.problem?.code || response.status}`, true); return; }
    etag = response.headers.get("ETag") || body.etag; currentRevision = body.note.revision;
    pendingSave = null; pendingSignature = null;
    revision.textContent = `revision ${currentRevision}`; setStatus(body.status === "unchanged" ? "已確認先前保存成功" : "保存完成");
  }

  async function openSource(anchor = null) {
    const sourceId = anchor?.source_id || fields.sourceId.value;
    const locator = anchor?.locator?.value || fields.locator.value;
    if (!sourceId || !locator) { setStatus("請先填來源 ID 與 locator", true); return; }
    const response = await fetch(`/api/note-sources/${encodeURIComponent(sourceId)}?locator=${encodeURIComponent(locator)}`);
    const body = await response.json();
    if (!response.ok || body.status !== "ready") { setStatus(`來源無法讀取：${body.problem?.code || response.status}`, true); return; }
    byId("source-title").textContent = `${body.document.source.label} · ${locator}`;
    byId("source-excerpt").textContent = body.document.focus.excerpt;
    byId("source-panel").hidden = false; byId("source-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  fields.markdown.addEventListener("input", preview);
  byId("note-load").addEventListener("click", () => loadNote().catch(error => setStatus(`讀取失敗：${error.message}`, true)));
  byId("note-save").addEventListener("click", save);
  byId("source-open").addEventListener("click", () => openSource());
  byId("note-new").addEventListener("click", () => { etag = "*"; currentRevision = null; pendingSave = null; pendingSignature = null; fields.markdown.value = "## 我目前的解釋\n\n\n\n## 問題或不確定\n\n"; revision.textContent = "新筆記"; conflict.hidden = true; preview(); setStatus("新稿尚未保存"); });
  byId("note-search-form").addEventListener("submit", async event => {
    event.preventDefault();
    const query = byId("note-search").value;
    const response = await fetch(`/api/notes?notebook_id=${encodeURIComponent(fields.notebookId.value)}&q=${encodeURIComponent(query)}`);
    const body = await response.json(); const list = byId("search-results"); list.replaceChildren();
    if (!response.ok) { setStatus(`搜尋失敗：${body.problem?.code || response.status}`, true); return; }
    for (const hit of body.results) {
      const item = document.createElement("li"); const button = document.createElement("button"); const detail = document.createElement("p");
      button.type = "button"; button.textContent = hit.heading ? `${hit.title} · ${hit.heading}` : hit.title;
      detail.textContent = hit.snippet; button.addEventListener("click", () => loadNote(hit.note_id).catch(error => setStatus(error.message, true)));
      item.append(button, detail);
      if (hit.source_anchors[0]) { const source = document.createElement("button"); source.type = "button"; source.textContent = " · 回來源"; source.addEventListener("click", () => openSource(hit.source_anchors[0])); item.append(source); }
      list.append(item);
    }
    if (!body.results.length) { const empty = document.createElement("li"); empty.textContent = "沒有找到符合的筆記內容。"; list.append(empty); }
  });
  preview();
}

if (typeof document !== "undefined" && document.getElementById("note-markdown")) init();
