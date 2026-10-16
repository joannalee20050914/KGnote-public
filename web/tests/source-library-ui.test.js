import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {
  SOURCE_BATCH_VERSION,
  SOURCE_IMPORT_VERSION,
  fileImportPayload,
  readMarkdownFile,
  sourceImportRequest,
} from "../source-library-ui.js";
import {sourceReadConfig, sourceReadUrl} from "../source-app.js";

function markdownFile(name, text, size = new TextEncoder().encode(text).length) {
  return {
    name,
    size,
    async arrayBuffer() { return new TextEncoder().encode(text).buffer; },
  };
}

test("builds a version-bound update without changing the existing source identity", () => {
  const existing = {
    source_id: "src_0123456789abcdef01234567",
    current_revision_id: "revision_0123456789abcdef01234567",
    source_kind: "document",
    title: "DNS",
    locator: {kind: "file_name", value: "dns.md"},
  };
  assert.deepEqual(sourceImportRequest({
    title: "DNS updated",
    content: "# DNS\n",
    sourceKind: "document",
    locatorValue: "renamed.md",
    existingSource: existing,
  }), {
    schema_version: SOURCE_IMPORT_VERSION,
    source_id: existing.source_id,
    expected_revision_id: existing.current_revision_id,
    title: "DNS updated",
    content: "# DNS\n",
    source_kind: "document",
    locator: existing.locator,
  });
});

test("one file stays a single request and multiple files become one atomic batch", async () => {
  const one = await fileImportPayload([markdownFile("one.md", "# One\n")], "document");
  assert.equal(one.schema_version, SOURCE_IMPORT_VERSION);
  assert.equal(one.locator.value, "one.md");
  const many = await fileImportPayload([
    markdownFile("one.md", "# One\n"),
    markdownFile("two.md", "# Two\n"),
  ], "document");
  assert.equal(many.schema_version, SOURCE_BATCH_VERSION);
  assert.equal(many.sources.length, 2);
});

test("browser boundary rejects extensions, oversized bytes and invalid UTF-8", async () => {
  await assert.rejects(readMarkdownFile(markdownFile("private.txt", "x")), /unsupported_extension/);
  await assert.rejects(readMarkdownFile(markdownFile("large.md", "x", 1_000_001)), /source_too_large/);
  const invalid = {name: "bad.md", size: 1, async arrayBuffer() { return Uint8Array.from([0xff]).buffer; }};
  await assert.rejects(readMarkdownFile(invalid), /invalid_utf8/);
});

test("source read URL binds source and optional immutable revision and rejects traversal", () => {
  const current = sourceReadConfig("?id=src_0123456789abcdef01234567");
  assert.equal(sourceReadUrl(current), "/api/library/sources/src_0123456789abcdef01234567");
  const exact = sourceReadConfig("?id=src_0123456789abcdef01234567&revision=revision_abcdefabcdefabcdefabcdef");
  assert.equal(sourceReadUrl(exact), "/api/library/sources/src_0123456789abcdef01234567?revision=revision_abcdefabcdefabcdefabcdef");
  assert.throws(() => sourceReadConfig("?id=../../private"), /invalid_source_id/);
  assert.throws(() => sourceReadConfig("?id=src_0123456789abcdef01234567&revision=latest"), /invalid_revision_id/);
});

test("product UI exposes multi-file, conversation, version update and read-back controls", async () => {
  const html = await readFile(new URL("../import.html", import.meta.url), "utf8");
  const app = await readFile(new URL("../import-app.js", import.meta.url), "utf8");
  assert.match(html, /id="source-files"[^>]*multiple/);
  assert.match(html, /value="chatgpt_conversation"/);
  assert.match(html, /id="existing-source"/);
  assert.match(app, /\/api\/library\/sources/);
  assert.doesNotMatch(html + app, /innerHTML|eval\(/);
});
