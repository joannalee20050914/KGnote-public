export function sourceReaderConfig(search) {
  const parameters = new URLSearchParams(search);
  const sourceId = parameters.get("source_id") || "";
  const locator = parameters.get("locator") || "";
  const title = parameters.get("title") || "指定來源片段";
  if (!/^src_[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(sourceId)) throw new Error("invalid_source_id");
  const match = /^L([1-9][0-9]*)-L([1-9][0-9]*)$/.exec(locator);
  if (!match || Number(match[1]) > Number(match[2])) throw new Error("invalid_locator");
  if (title.length > 240) throw new Error("invalid_title");
  return { sourceId, locator, title, startLine: Number(match[1]) };
}

export function sourceReaderApiUrl(config) {
  return `/api/note-sources/${encodeURIComponent(config.sourceId)}?locator=${encodeURIComponent(config.locator)}`;
}

async function init() {
  const status = document.getElementById("source-status");
  try {
    const config = sourceReaderConfig(location.search);
    document.getElementById("session-title").textContent = config.title;
    document.getElementById("source-locator").textContent = config.locator;
    const response = await fetch(sourceReaderApiUrl(config), { headers: { Accept: "application/json" } });
    const body = await response.json();
    if (!response.ok || body.status !== "ready") throw new Error(body.problem?.code || "source_unavailable");
    document.getElementById("source-heading").textContent = body.document.source.label;
    const list = document.getElementById("source-lines");
    list.style.setProperty("--start-line", String(config.startLine - 1));
    for (const line of body.document.focus.excerpt.split(/\n/)) {
      const item = document.createElement("li");
      const text = document.createElement("span");
      text.textContent = line || " ";
      item.append(text); list.append(item);
    }
    status.textContent = `Source SHA-256 已驗證 · ${body.document.focus.locator.value}`;
  } catch (error) {
    status.textContent = `來源無法載入：${error.message}`;
  }
}

if (typeof document !== "undefined" && document.getElementById("source-lines")) init();
