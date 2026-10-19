import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildNodeDetails} from "../panel.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/phase0-graph-view.json", import.meta.url), "utf8"));

test("projects concept summary, deduplicated provenance, history, and explicit empty confusion", () => {
  const result = buildNodeDetails(fixture.view, "concept_confounder");
  assert.equal(result.status, "ready");
  assert.equal(result.detail.label, "Confounder");
  assert.equal(result.detail.summary, "同時影響所觀察變數、可能造成表面相關的第三個變數。");
  assert.deepEqual(result.detail.evidence.map(({id}) => id), ["evidence_apply_confounder", "evidence_define_correlation_causation"]);
  assert.deepEqual(result.detail.sources.map(({label}) => label), ["Synthetic causality learning conversation"]);
  assert.deepEqual(result.detail.history.map(({id}) => id), ["event_causality_question"]);
  assert.deepEqual(result.detail.known_confusion, {events: [], links: [], evidence: []});
});

test("projects a learning event with concepts, evidence, sources, and occurrence", () => {
  const result = buildNodeDetails(fixture.view, "event_causality_question");
  assert.equal(result.status, "ready");
  assert.equal(result.detail.event_type, "question");
  assert.equal(result.detail.occurred_at, null);
  assert.equal(result.detail.concepts.length, 6);
  assert.equal(result.detail.evidence.length, 4);
  assert.equal(result.detail.sources.length, 1);
});

test("only explicit confusion semantics become known confusion", () => {
  const view = structuredClone(fixture.view);
  const event = view.nodes.find(({kind}) => kind === "learning_event");
  event.event_type = "confusion";
  const link = view.links.find(({edge_class}) => edge_class === "learning");
  link.relation = "confused_with";
  const result = buildNodeDetails(view, link.target_id);
  assert.equal(result.status, "ready");
  assert.deepEqual(result.detail.known_confusion.events.map(({id}) => id), [event.id]);
  assert.deepEqual(result.detail.known_confusion.links.map(({id}) => id), [link.id]);
  assert.ok(result.detail.known_confusion.evidence.length > 0);

  for (const relation of ["asked_about", "encountered", null]) {
    const neutral = structuredClone(fixture.view);
    neutral.links.find(({edge_class}) => edge_class === "learning").relation = relation;
    const neutralResult = buildNodeDetails(neutral, link.target_id);
    assert.deepEqual(neutralResult.detail.known_confusion, {events: [], links: [], evidence: []});
  }
});

test("history ordering is newest-first, null-last, then stable ID", () => {
  const view = structuredClone(fixture.view);
  const original = view.nodes.find(({kind}) => kind === "learning_event");
  for (const [id, occurred_at] of [["event_earlier", "2026-01-01T00:00:00Z"], ["event_later", "2026-02-01T00:00:00Z"]]) {
    view.nodes.push({...structuredClone(original), id, occurred_at});
  }
  const result = buildNodeDetails(view, "concept_confounder");
  assert.deepEqual(result.detail.history.map(({id}) => id), ["event_later", "event_earlier", original.id]);
});

test("fails closed for unknown or malformed references without echoing input", () => {
  assert.deepEqual(buildNodeDetails(fixture.view, "private secret"), {status: "rejected", problem: {code: "unknown_detail_node"}});
  const missingEvidence = structuredClone(fixture.view);
  missingEvidence.evidence = missingEvidence.evidence.slice(1);
  assert.deepEqual(buildNodeDetails(missingEvidence, "concept_confounder"), {status: "rejected", problem: {code: "missing_detail_evidence"}});
  const missingSource = structuredClone(fixture.view);
  missingSource.sources = [];
  assert.deepEqual(buildNodeDetails(missingSource, "concept_confounder"), {status: "rejected", problem: {code: "missing_detail_source"}});
  const danglingConcept = structuredClone(fixture.view);
  danglingConcept.nodes.find(({kind}) => kind === "learning_event").concept_ids.push("concept_missing");
  assert.deepEqual(buildNodeDetails(danglingConcept, "event_causality_question"), {status: "rejected", problem: {code: "invalid_detail_event_reference"}});
});

test("is deterministic, copy-safe, and does not mutate the read model", () => {
  const before = structuredClone(fixture.view);
  const first = buildNodeDetails(fixture.view, "concept_correlation");
  const second = buildNodeDetails(structuredClone(fixture.view), "concept_correlation");
  assert.deepEqual(first, second);
  first.detail.evidence[0].proposition = "changed";
  assert.deepEqual(fixture.view, before);
});

test("HTML and app expose accessible details with append-only review", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  const app = await readFile(new URL("../app.js", import.meta.url), "utf8");
  assert.match(html, /<aside id="detail-panel"/);
  assert.match(html, /aria-label="關閉詳細內容"/);
  assert.match(app, /event\.key === "Enter"/);
  assert.match(app, /event\.key === "Escape"/);
  assert.match(app, /detailTrigger\.focus\(\)/);
  assert.match(app, /複習這個概念/);
  assert.match(app, /保存複習紀錄/);
  assert.doesNotMatch(html + app, /contenteditable|\b(delete|merge|rename|apply canonical)\b/i);
});
