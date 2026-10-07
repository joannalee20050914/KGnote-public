import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildExpertSkeleton, excerptForLocator, teachingSentence, validateGuidedMap} from "../guided-map.js";
import {buildGuidedReviewRequest, buildLearningWorkspace, buildLinkingPhraseExercise, compareLinkingPhrase, evidenceLineNumbers, selectConcept, selectEdge, selectEvidence} from "../learning-workspace.js";

const webFixtureUrl = new URL("../fixtures/bitepacer-guided-map.json", import.meta.url);
const contractFixtureUrl = new URL("../../tests/fixtures/guided-map/v1/bitepacer-golden.json", import.meta.url);
const sourceUrl = new URL("../fixtures/bitepacer-mini-network-lesson.md", import.meta.url);
const graphFixtureUrl = new URL("../fixtures/bitepacer-graph.json", import.meta.url);
const contractGraphUrl = new URL("../../tests/fixtures/guided-map/v1/bitepacer-graph.json", import.meta.url);
const model = JSON.parse(await readFile(webFixtureUrl, "utf8"));
const graph = JSON.parse(await readFile(graphFixtureUrl, "utf8"));
const source = await readFile(sourceUrl, "utf8");

test("web map is the exact versioned Guided Map read model", async () => {
  const contractFixture = JSON.parse(await readFile(contractFixtureUrl, "utf8"));
  assert.deepEqual(model, contractFixture);
  assert.deepEqual(validateGuidedMap(model), {status: "ready"});
  assert.equal(model.groups.length, 5);
  assert.equal(model.concepts.length, 9);
  assert.equal(model.propositions.length, 7);
});

test("web graph is exact and all three views build from one cross-view identity", async () => {
  assert.deepEqual(graph, JSON.parse(await readFile(contractGraphUrl, "utf8")));
  const workspace = buildLearningWorkspace(model, graph, source);
  assert.equal(workspace.status, "ready");
  assert.equal(workspace.source.id, model.source.id);
  assert.equal(workspace.learning_unit.focus_question, model.learning_unit.focus_question);
  assert.deepEqual(workspace.graph.nodes.map(({id}) => id), workspace.concepts.map(({id}) => id));
  assert.deepEqual(workspace.graph.links.map(({id}) => id), workspace.propositions.map(({edge_id}) => edge_id));
});

test("concept, edge, and evidence selections preserve source and focus across views", () => {
  const workspace = buildLearningWorkspace(model, graph, source);
  const proposition = workspace.propositions[0];
  const conceptSelection = selectConcept(workspace, proposition.subject_concept_id);
  const edgeSelection = selectEdge(workspace, proposition.edge_id);
  const evidenceSelection = selectEvidence(workspace, proposition.evidence_ids[0]);
  for (const result of [conceptSelection, edgeSelection, evidenceSelection]) {
    assert.equal(result.status, "ready");
    assert.equal(result.selection.source_id, model.source.id);
    assert.equal(result.selection.focus_question, model.learning_unit.focus_question);
  }
  assert.equal(edgeSelection.selection.edge_id, proposition.edge_id);
  assert.equal(evidenceSelection.selection.edge_id, null);
  assert.ok(evidenceSelection.selection.candidate_edge_ids.includes(proposition.edge_id));
  assert.ok(evidenceLineNumbers(workspace, edgeSelection.selection).length > 0);
});

test("cross-view drift and unknown selections fail closed", () => {
  const labelDrift = structuredClone(graph);
  labelDrift.nodes[0].label = "不同名稱";
  assert.equal(buildLearningWorkspace(model, labelDrift, source).problem.code, "cross_view_concept_drift");
  const directionDrift = structuredClone(graph);
  [directionDrift.links[0].source_id, directionDrift.links[0].target_id] = [directionDrift.links[0].target_id, directionDrift.links[0].source_id];
  assert.equal(buildLearningWorkspace(model, directionDrift, source).problem.code, "cross_view_edge_drift");
  const workspace = buildLearningWorkspace(model, graph, source);
  assert.equal(selectConcept(workspace, "concept_missing").problem.code, "unknown_selection_concept");
  assert.equal(selectEdge(workspace, "edge_missing").problem.code, "unknown_selection_edge");
  assert.equal(selectEvidence(workspace, "evidence_missing").problem.code, "unknown_selection_evidence");
});

test("linking-phrase exercise compares one reviewed proposition without mastery scoring", () => {
  const workspace = buildLearningWorkspace(model, graph, source);
  const proposition = workspace.propositions.find(({subject_label}) => subject_label === "用戶端");
  const built = buildLinkingPhraseExercise(workspace, proposition.edge_id);
  assert.equal(built.status, "ready");
  assert.equal(built.exercise.prompt, "用戶端＿＿＿＿HTTP 請求");
  assert.equal(compareLinkingPhrase(built.exercise, "主動送出").comparison.matches_reviewed_phrase, true);
  const mismatch = compareLinkingPhrase(built.exercise, "傳送");
  assert.equal(mismatch.comparison.matches_reviewed_phrase, false);
  assert.equal(mismatch.comparison.canonical_sentence, proposition.sentence);
  assert.deepEqual(mismatch.comparison.evidence.map(({id}) => id), proposition.evidence.map(({id}) => id));
  assert.equal(compareLinkingPhrase(built.exercise, "  ").problem.code, "invalid_exercise_answer");
  assert.equal(buildLinkingPhraseExercise(workspace, "edge_missing").problem.code, "unknown_exercise_edge");
  assert.equal("mastery" in mismatch.comparison, false);
});

test("guided review request sends only snapshot-bound learner facts", () => {
  const workspace = buildLearningWorkspace(model, graph, source);
  const built = buildLinkingPhraseExercise(workspace, workspace.propositions[0].edge_id);
  const comparison = compareLinkingPhrase(built.exercise, "主動送出").comparison;
  const result = buildGuidedReviewRequest(workspace, comparison, true);
  assert.equal(result.status, "ready");
  assert.deepEqual(Object.keys(result.request).sort(), [
    "edge_id", "graph_snapshot_sha256", "hint_used", "learning_unit_id", "response", "schema_version", "source_id",
  ]);
  assert.equal(result.request.graph_snapshot_sha256, model.graph_snapshot_sha256);
  assert.equal(result.request.hint_used, true);
  assert.equal("canonical_sentence" in result.request, false);
  assert.equal("evidence" in result.request, false);
  assert.equal("mastery" in result.request, false);
  assert.equal(buildGuidedReviewRequest(workspace, {...comparison, edge_id: "edge_missing"}, false).problem.code, "stale_guided_review_edge");
});

test("expert skeleton preserves group order without turning groups into concepts", () => {
  const result = buildExpertSkeleton(model, source);
  assert.equal(result.status, "ready");
  assert.deepEqual(result.groups.map(({order, label}) => [order, label]), [
    [1, "誰在溝通"], [2, "如何找到位置"], [3, "如何交換資料"], [4, "程式如何處理"], [5, "外部如何進入"],
  ]);
  const conceptIds = new Set(model.concepts.map(({id}) => id));
  for (const group of model.groups) assert.equal(conceptIds.has(group.id), false);
});

test("all relationships remain readable, directional, accepted, and evidence-backed", () => {
  const result = buildExpertSkeleton(model, source);
  assert.equal(result.status, "ready");
  assert.deepEqual(result.propositions.map(({sentence}) => sentence), model.propositions.map(teachingSentence));
  for (const proposition of result.propositions) {
    assert.equal(proposition.review_status, "accepted");
    assert.ok(proposition.evidence.length >= 1);
    assert.ok(proposition.evidence.every(({source_excerpt}) => source_excerpt.length >= 1));
  }
});

test("source fixture is byte-exact and every locator resolves to numbered original lines", () => {
  assert.equal(createHash("sha256").update(source).digest("hex"), model.source.content_sha256);
  for (const evidence of model.evidence) {
    const result = excerptForLocator(source, evidence.locator);
    assert.equal(result.status, "ready");
    assert.equal(result.excerpt[0].number, Number(evidence.locator.value.match(/^L(\d+)/)[1]));
    assert.ok(result.excerpt.some(({text}) => text.trim().length > 0));
  }
});

test("malformed references and out-of-bounds source locators fail closed", () => {
  const drift = structuredClone(model);
  drift.propositions[0].subject_label = "悄悄改名";
  assert.equal(validateGuidedMap(drift).problem.code, "proposition_label_drift");

  const missing = structuredClone(model);
  missing.propositions[0].evidence_ids = ["evidence_missing"];
  assert.equal(validateGuidedMap(missing).problem.code, "invalid_proposition_evidence");
  assert.equal(excerptForLocator(source, {kind: "line_range", value: "L80-L999"}).problem.code, "invalid_source_locator");
});

test("workspace page exposes three tabs, shared selection, hierarchy, graph, and source", async () => {
  const html = await readFile(new URL("../guided-map.html", import.meta.url), "utf8");
  const app = await readFile(new URL("../guided-map-app.js", import.meta.url), "utf8");
  assert.match(html, /id="outline-title"/);
  assert.match(html, /id="relation-title"/);
  assert.match(html, /id="focus-question"/);
  assert.match(html, /role="tab"[^>]+data-view="reader"/);
  assert.match(html, /role="tab"[^>]+data-view="map"/);
  assert.match(html, /role="tab"[^>]+data-view="graph"/);
  assert.match(html, /id="reader-source"/);
  assert.match(html, /id="exploration-graph"/);
  assert.match(html, /補上中間的關係詞/);
  assert.match(html, /不換算理解分數/);
  assert.match(html, /id="practice-save"/);
  assert.match(app, /查看原文證據/);
  assert.match(app, /source_excerpt/);
  assert.match(app, /updateSelectionUI/);
  assert.match(app, /compareLinkingPhrase/);
  assert.match(app, /workspace\.groups\.length/);
  assert.match(app, /workspace\.propositions\.length/);
  assert.match(app, /\/api\/guided-reviews/);
  assert.match(app, /crypto\.subtle\.digest\("SHA-256"/);
  assert.doesNotMatch(html + app, /contenteditable|理解\s*\d+%|熟練度/);
});
