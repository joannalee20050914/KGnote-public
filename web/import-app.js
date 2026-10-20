import {fileImportPayload, renderImportCompletion, sourceImportRequest} from "./source-library-ui.js";

const byId = id => document.getElementById(id);
let sources = [];

function selectedExisting() {
  return sources.find(source => source.source_id === byId("existing-source").value) ?? null;
}

try {
  const response = await fetch("/api/library/sources", {cache: "no-store"});
  const body = await response.json();
  if (response.ok && body.status === "ready") {
    sources = body.sources;
    for (const source of sources) {
      const option = document.createElement("option");
      option.value = source.source_id;
      option.textContent = `${source.title}（${source.revision_count} 版）`;
      byId("existing-source").append(option);
    }
  }
} catch {
  byId("status").textContent = "目前無法讀取既有來源；仍可準備新匯入，送出時會再次驗證。";
}

byId("existing-source").addEventListener("change", () => {
  const existing = selectedExisting();
  byId("source-kind").disabled = Boolean(existing);
  if (existing) {
    byId("source-kind").value = existing.source_kind;
    byId("title").value = existing.title;
  }
});

byId("source-files").addEventListener("change", event => {
  const files = [...(event.target.files ?? [])];
  byId("file-status").textContent = files.length ? `已選擇 ${files.length} 個檔案；尚未寫入。` : "可選多檔；全部驗證成功才會一起保存。";
});

byId("source-form").addEventListener("submit", async event => {
  event.preventDefault();
  const status = byId("status");
  status.textContent = "正在本機驗證來源與版本…";
  try {
    const files = [...(byId("source-files").files ?? [])];
    const existing = selectedExisting();
    let payload;
    if (files.length) {
      payload = await fileImportPayload(files, byId("source-kind").value, existing);
    } else {
      const title = byId("title").value.trim();
      const content = byId("content").value;
      if (!title || !content.trim()) throw new Error("no_source_selected");
      payload = sourceImportRequest({
        title,
        content,
        sourceKind: existing?.source_kind ?? byId("source-kind").value,
        locatorValue: title,
        existingSource: existing,
      });
      if (!existing) payload.locator = {kind: "pasted", value: title};
    }
    const response = await fetch("/api/library/sources", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.problem?.code ?? "source_import_failed");
    byId("source-form").hidden = true;
    const completion = byId("completion");
    completion.hidden = false;
    renderImportCompletion(document, completion, body);
  } catch (error) {
    status.textContent = `無法保存：${error.message}`;
  }
});
