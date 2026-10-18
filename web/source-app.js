export function sourceReadConfig(search) {
  const parameters = new URLSearchParams(search);
  const sourceId = parameters.get("id") ?? "";
  const revisionId = parameters.get("revision");
  if (!/^src_[0-9a-f]{24}$/.test(sourceId)) throw new Error("invalid_source_id");
  if (revisionId !== null && !/^revision_[0-9a-f]{24}$/.test(revisionId)) throw new Error("invalid_revision_id");
  return {sourceId, revisionId};
}

export function sourceReadUrl(config) {
  const base = `/api/library/sources/${encodeURIComponent(config.sourceId)}`;
  return config.revisionId ? `${base}?revision=${encodeURIComponent(config.revisionId)}` : base;
}

async function init() {
  const status = document.getElementById("source-status");
  try {
    const config = sourceReadConfig(location.search);
    const response = await fetch(sourceReadUrl(config), {cache: "no-store"});
    const body = await response.json();
    if (!response.ok || body.status !== "ready") throw new Error(body.problem?.code ?? "source_unavailable");
    document.getElementById("source-title").textContent = body.source.title;
    document.getElementById("source-meta").textContent = `${body.source.source_kind} · ${body.source.locator.value} · ${body.source.revision_count} 個版本`;
    document.getElementById("source-content").textContent = body.content;
    const revisions = document.getElementById("revision-list");
    for (const revision of body.source.revisions) {
      const link = document.createElement("a");
      link.className = revision.revision_id === body.revision.revision_id ? "primary" : "secondary";
      link.textContent = `${revision.revision_id.slice(-8)} · ${revision.line_count} 行`;
      link.href = `./source.html?id=${encodeURIComponent(body.source.source_id)}&revision=${encodeURIComponent(revision.revision_id)}`;
      revisions.append(link);
    }
    const speakers = body.revision.speaker_spans.map(item => `${item.speaker} ${item.locator.value}`).join("；");
    status.textContent = `SHA-256 ${body.revision.content_sha256} 已驗證${speakers ? ` · 發言者：${speakers}` : ""}`;
  } catch (error) {
    status.textContent = `來源無法載入：${error.message}`;
  }
}

if (typeof document !== "undefined" && document.getElementById("source-content")) init();
