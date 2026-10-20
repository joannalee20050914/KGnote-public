import {renderSourceCard} from "./source-library-ui.js";

const root = document.getElementById("source-list");
try {
  const response = await fetch("/api/library/sources", {cache: "no-store"});
  const body = await response.json();
  if (!response.ok || body.status !== "ready") throw new Error(body.problem?.code ?? "source_library_unavailable");
  root.replaceChildren();
  if (!body.sources.length) {
    const empty = document.createElement("p");
    empty.textContent = "尚未匯入來源。";
    root.append(empty);
  } else {
    for (const source of body.sources) renderSourceCard(document, root, source);
  }
} catch (error) {
  root.textContent = `來源資料庫無法讀取：${error.message}`;
}
