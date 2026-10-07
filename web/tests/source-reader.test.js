import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { sourceReaderApiUrl, sourceReaderConfig } from "../source-reader.js";

test("source-only H0 reader accepts one explicit source range", () => {
  const config = sourceReaderConfig("?source_id=src_demo&locator=L8-L22&title=Phase+A");
  assert.deepEqual(config, { sourceId: "src_demo", locator: "L8-L22", title: "Phase A", startLine: 8 });
  assert.equal(sourceReaderApiUrl(config), "/api/note-sources/src_demo?locator=L8-L22");
});

test("source-only H0 reader rejects traversal and reversed ranges", () => {
  assert.throws(() => sourceReaderConfig("?source_id=../../x&locator=L1-L2"), /invalid_source_id/);
  assert.throws(() => sourceReaderConfig("?source_id=src_demo&locator=L9-L2"), /invalid_locator/);
});

test("source reader contains no note editor, graph or AI controls", () => {
  const html = readFileSync(new URL("../source-reader.html", import.meta.url), "utf8");
  assert.doesNotMatch(html, /textarea|learning-note|guided-map|graph-view/);
  assert.match(html, /SOURCE ONLY · NO GRAPH · NO AI/);
});
