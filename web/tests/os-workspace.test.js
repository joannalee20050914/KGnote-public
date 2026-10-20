import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {validateGuidedMap} from "../guided-map.js";
import {buildLearningWorkspace, projectGraphFromGuidedMap, selectEvidence} from "../learning-workspace.js";

const modelUrl = new URL("../fixtures/os-overview-guided-map.json", import.meta.url);
const sourceUrl = new URL("../fixtures/os-overview-review.md", import.meta.url);
const model = JSON.parse(await readFile(modelUrl, "utf8"));
const source = await readFile(sourceUrl, "utf8");

test("OS review fixture keeps the supplied source byte-bound and builds all three views", () => {
  assert.deepEqual(validateGuidedMap(model), {status: "ready"});
  assert.equal(createHash("sha256").update(source).digest("hex"), model.source.content_sha256);
  const graph = projectGraphFromGuidedMap(model, "operating-systems");
  const workspace = buildLearningWorkspace(model, graph, source);
  assert.equal(workspace.status, "ready");
  assert.equal(workspace.groups.length, 5);
  assert.equal(workspace.concepts.length, 16);
  assert.equal(workspace.propositions.length, 10);
  assert.equal(workspace.evidence.length, 8);
  assert.deepEqual(workspace.graph.nodes.map(({id}) => id), workspace.concepts.map(({id}) => id));
  assert.deepEqual(workspace.graph.links.map(({id}) => id), workspace.propositions.map(({edge_id}) => edge_id));
});

test("legacy Evidence focus no longer picks an arbitrary first proposition", () => {
  const workspace = buildLearningWorkspace(model, projectGraphFromGuidedMap(model), source);
  const expected = selectEvidence(workspace, "evidence_os_scheduling");
  assert.equal(expected.status, "ready");
  assert.equal(expected.selection.edge_id, null);
  assert.equal(expected.selection.concept_id, null);
  assert.deepEqual(expected.selection.candidate_edge_ids, ["edge_os_aging_starvation", "edge_os_quantum_context"]);
  const reversed = structuredClone(workspace);
  reversed.propositions.reverse();
  assert.deepEqual(selectEvidence(reversed, "evidence_os_scheduling"), expected);
  const unmapped = structuredClone(workspace);
  unmapped.evidence.push({id: "evidence_unmapped"});
  assert.deepEqual(selectEvidence(unmapped, "evidence_unmapped").selection.candidate_edge_ids, []);
});

test("OS review map stays focused and every relation returns to accepted source evidence", () => {
  const workspace = buildLearningWorkspace(model, projectGraphFromGuidedMap(model), source);
  assert.equal(workspace.learning_unit.focus_question, "OS 如何在安全與效率之間管理程式、CPU 與硬體？");
  assert.deepEqual(workspace.groups.map(({label}) => label), [
    "建立保護邊界", "回應硬體事件", "保存與切換執行現場", "平衡排程公平", "保護共享狀態",
  ]);
  for (const proposition of workspace.propositions) {
    assert.ok(proposition.sentence.includes(proposition.linking_phrase));
    assert.ok(proposition.evidence.length >= 1);
    assert.ok(proposition.evidence.every(({review_status, source_excerpt}) => review_status === "accepted" && source_excerpt.length >= 1));
  }
});

test("OS teaching propositions read as complete learner-facing sentences", () => {
  const workspace = buildLearningWorkspace(model, projectGraphFromGuidedMap(model), source);
  assert.ok(workspace.propositions.some(({sentence}) => sentence === "應用程式 向核心提出 系統呼叫"));
  assert.ok(workspace.propositions.some(({sentence}) => sentence === "程序 的執行現場由 OS 記錄在 程序控制區塊"));
  assert.ok(workspace.propositions.some(({sentence}) => sentence === "直接記憶體存取 讓下列元件只處理設定與完成通知： CPU"));
});
