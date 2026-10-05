import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildAttemptRequest, groupedItems, newAttemptId, safePracticeItem} from "../practice-workspace.js";

const item = {
  item_id: "item_relation_edge_os_application_system_call", revision: 1,
  learning_unit_id: "guided_map_os_safety_efficiency_review", activity_type: "relation_recall",
  prompt: "請補上一個合理的關係：應用程式 ＿＿＿＿ 系統呼叫", hint: "想想方向",
  source_refs: ["src_os_overview_review"], claim_ref: {claim_id: "edge_os_application_system_call", revision: 1},
  evidence_refs: ["evidence_os_protection"],
};

test("Attempt starts with stable client identity and records hints, raw response, exposure, and refs", () => {
  assert.equal(newAttemptId(() => "01234567-89ab-cdef-0123-456789abcdef"), "attempt_0123456789abcdef0123456789abcdef");
  const built = buildAttemptRequest({
    attemptId: "attempt_0123456789abcdef0123456789abcdef", item,
    startedAt: "2026-09-20T01:00:00.000Z", submittedAt: "2026-09-20T01:01:00.000Z",
    response: "不知道", confidence: "low", hintEvents: [{kind: "requested", occurred_at: "2026-09-20T01:00:30.000Z"}],
    state: "submitted", outcome: "INCORRECT",
  });
  assert.equal(built.status, "ready");
  assert.equal(built.request.raw_response, "不知道");
  assert.equal(built.request.support_state, "hinted");
  assert.equal(built.request.answer_exposure_state, "revealed_after_submission");
  assert.deepEqual(built.request.claim_refs, [item.claim_ref]);
});

test("practice grouping preserves all four reviewed activity types", () => {
  const items = ["relation_recall", "free_explanation", "application_prediction", "distinction"].map((activity_type, index) => ({activity_type, item_id: String(index)}));
  const groups = groupedItems(items);
  assert.deepEqual(Object.keys(groups), ["relation_recall", "free_explanation", "application_prediction", "distinction"]);
  assert.ok(Object.values(groups).every(group => group.length === 1));
});

test("isolated Practice document contains no hidden Reader, graph, selection summary, answer, or source excerpt", async () => {
  const html = await readFile(new URL("../practice.html", import.meta.url), "utf8");
  const script = await readFile(new URL("../practice-app.js", import.meta.url), "utf8");
  for (const forbidden of ["reader-source", "exploration-graph", "selection-summary", "canonical_sentence", "source_excerpt", "os-overview-guided-map.json", "os-overview-review.md"]) {
    assert.equal(html.includes(forbidden), false, `HTML leaked ${forbidden}`);
    assert.equal(script.includes(forbidden), false, `script loaded ${forbidden}`);
  }
  assert.equal(safePracticeItem(item), true);
  assert.equal(safePracticeItem({...item, canonical_answer: "答案"}), false);
});
