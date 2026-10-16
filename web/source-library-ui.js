export const SOURCE_IMPORT_VERSION = "kgnote.source-import.v2";
export const SOURCE_BATCH_VERSION = "kgnote.source-import-batch.v1";
export const MAX_SOURCE_BYTES = 1_000_000;

function element(document, tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

export function sourceImportRequest({title, content, sourceKind, locatorValue, existingSource = null}) {
  const locator = existingSource?.locator ?? {kind: "file_name", value: locatorValue};
  return {
    schema_version: SOURCE_IMPORT_VERSION,
    source_id: existingSource?.source_id ?? null,
    expected_revision_id: existingSource?.current_revision_id ?? null,
    title,
    content,
    source_kind: sourceKind,
    locator,
  };
}

export async function readMarkdownFile(file) {
  if (!/\.md$/i.test(file.name)) throw new Error("unsupported_extension");
  if (file.size > MAX_SOURCE_BYTES) throw new Error("source_too_large");
  const bytes = await file.arrayBuffer();
  try {
    return new TextDecoder("utf-8", {fatal: true}).decode(bytes);
  } catch {
    throw new Error("invalid_utf8");
  }
}

export async function fileImportPayload(files, sourceKind, existingSource = null) {
  if (!files.length) throw new Error("no_source_selected");
  if (existingSource && files.length !== 1) throw new Error("update_requires_one_file");
  const sources = [];
  for (const file of files) {
    const content = await readMarkdownFile(file);
    sources.push(sourceImportRequest({
      title: existingSource?.title ?? file.name.replace(/\.md$/i, ""),
      content,
      sourceKind: existingSource?.source_kind ?? sourceKind,
      locatorValue: file.name,
      existingSource,
    }));
  }
  return sources.length === 1 ? sources[0] : {schema_version: SOURCE_BATCH_VERSION, sources};
}

function sourceLink(document, source, label = "讀回已保存原文") {
  const link = element(document, "a", label, "secondary");
  link.href = `./source.html?id=${encodeURIComponent(source.source_id)}`;
  return link;
}

export function renderImportCompletion(document, root, payload) {
  root.replaceChildren();
  const results = payload.results ?? [{action: payload.status, source: payload.source}];
  root.append(
    element(document, "h2", results.length === 1 ? "來源已安全保存" : `${results.length} 份來源已原子保存`),
    element(document, "p", "原始 Markdown 以不可變版本保存；重複內容不會新增版本，更新可讀回前一版。", "mapping-note"),
  );
  for (const result of results) {
    const source = result.source;
    const card = element(document, "article", undefined, "evidence-card");
    card.append(
      element(document, "h3", source.title),
      element(document, "p", `${result.action} · ${source.revision_count} 個版本 · ${source.source_kind}`, "mapping-note"),
      sourceLink(document, source),
    );
    root.append(card);
  }
}

export function renderSourceCard(document, root, source) {
  const card = element(document, "article", undefined, "evidence-card");
  card.append(
    element(document, "h3", source.title),
    element(document, "p", `${source.revision_count} 個不可變版本 · ${source.source_kind} · ${source.locator.value}`, "mapping-note"),
    sourceLink(document, source, "開啟來源與版本紀錄"),
  );
  root.append(card);
  return card;
}
