import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { buildSaveRequest, noteApiPath, parseMarkdownBlocks } from "../learning-note.js";

test("preview parser only emits allowlisted structural blocks and keeps HTML as text", () => {
  const blocks = parseMarkdownBlocks("## 解釋\n\n<script>alert(1)</script>\n\n- A\n- B");
  assert.deepEqual(blocks, [
    { type: "heading", level: 2, text: "解釋" },
    { type: "paragraph", text: "<script>alert(1)</script>" },
    { type: "list", items: ["A", "B"] },
  ]);
});

test("save request keeps note identity, body and note-level source anchor explicit", () => {
  const request = buildSaveRequest({
    noteId: "note_test", notebookId: "notebook_a", learningUnitId: "unit_a", title: "測試",
    markdown: "## 我的解釋", sourceId: "src_a", locator: "L1-L2", anchorLabel: "原文",
  }, "save_12345678");
  assert.equal(request.schema_version, "kgnote.learning-note-save.v1");
  assert.equal(request.source_anchors[0].locator.value, "L1-L2");
  assert.equal(request.markdown, "## 我的解釋");
  assert.equal(noteApiPath("note_test"), "/api/notes/note_test");
});

test("H0 learning-note page accepts bounded session parameters without an experiment-specific fork", () => {
  const source = readFileSync(new URL("../learning-note.js", import.meta.url), "utf8");
  assert.match(source, /new URLSearchParams\(location\.search\)/);
  for (const parameter of ["note_id", "notebook_id", "learning_unit_id", "source_id", "locator", "source_label"]) {
    assert.match(source, new RegExp(`${parameter}:`));
  }
});
