import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildScene, selectLocalNeighborhood, validateApplicationResult} from "../graph.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/phase0-graph-view.json", import.meta.url), "utf8"));

test("accepts Issue #16 result and deterministically renders all typed records", () => {
  assert.deepEqual(validateApplicationResult(fixture), {ok: true});
  const first = buildScene(fixture.view);
  const second = buildScene(structuredClone(fixture.view));
  assert.deepEqual(first, second);
  assert.equal(first.nodes.length, 7);
  assert.equal(first.links.length, 8);
  assert.deepEqual(new Set(first.nodes.map((node) => node.kind)), new Set(["concept", "learning_event"]));
  assert.deepEqual(new Set(first.links.map((link) => link.edge_class)), new Set(["canonical", "learning", "soft_association"]));
});

test("preserves stable identity, direction, labels, and unresolved semantics", () => {
  const scene = buildScene(fixture.view);
  for (const link of scene.links) {
    const original = fixture.view.links.find((candidate) => candidate.id === link.id);
    assert.equal(link.source_id, original.source_id);
    assert.equal(link.target_id, original.target_id);
  }
  const unresolved = scene.links.find((link) => link.edge_class === "soft_association");
  assert.equal(unresolved.relation, null);
  assert.equal(unresolved.confidence, "unresolved");
  assert.ok(scene.nodes.every((node) => node.id && node.label));
});

test("mobile fallback is deterministic one-hop and bounded", () => {
  const local = selectLocalNeighborhood(fixture.view);
  const mobile = buildScene(fixture.view, {mobile: true});
  assert.equal(mobile.mode, "local");
  assert.deepEqual([mobile.width, mobile.height], [720, 900]);
  assert.equal(mobile.focusId, local.focusId);
  assert.ok(mobile.nodes.length < fixture.view.nodes.length);
  const selectedIds = new Set(mobile.nodes.map((node) => node.id));
  assert.ok(mobile.links.every((link) => selectedIds.has(link.source_id) && selectedIds.has(link.target_id)));
  for (const node of mobile.nodes.filter((candidate) => candidate.id !== local.focusId)) {
    assert.ok(mobile.links.some((link) => [link.source_id, link.target_id].includes(local.focusId) && [link.source_id, link.target_id].includes(node.id)));
  }
  assert.ok(mobile.nodes.find((node) => node.id === local.focusId).focused);
});

test("fails closed for malformed, dangling, duplicate, and false-confirmed soft links", () => {
  assert.equal(validateApplicationResult(null).ok, false);
  assert.equal(validateApplicationResult({schema_version: "wrong", status: "ready"}).ok, false);
  const stalePlan = structuredClone(fixture);
  stalePlan.plan.snapshot_sha256 = "0".repeat(64);
  assert.deepEqual(validateApplicationResult(stalePlan), {ok: false, code: "invalid_graph_plan"});
  const dangling = structuredClone(fixture);
  dangling.view.links[0].target_id = "concept_missing";
  assert.deepEqual(validateApplicationResult(dangling), {ok: false, code: "invalid_graph_link"});
  const duplicate = structuredClone(fixture);
  duplicate.view.nodes.push(structuredClone(duplicate.view.nodes[0]));
  assert.deepEqual(validateApplicationResult(duplicate), {ok: false, code: "invalid_graph_node"});
  const falseConfirmed = structuredClone(fixture);
  Object.assign(falseConfirmed.view.links.find((link) => link.edge_class === "soft_association"), {relation: "causes", confidence: "high"});
  assert.deepEqual(validateApplicationResult(falseConfirmed), {ok: false, code: "invalid_soft_association"});
});

test("empty graph is a valid read-only scene", () => {
  const empty = structuredClone(fixture);
  empty.view.nodes = [];
  empty.view.links = [];
  assert.deepEqual(validateApplicationResult(empty), {ok: true});
  assert.deepEqual(buildScene(empty.view).nodes, []);
});

test("HTML exposes navigation only and contains no mutation controls", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /Knowledge graph canvas/);
  assert.match(html, /Read-only/);
  assert.doesNotMatch(html, /<form|contenteditable|\b(save|delete|merge|rename|apply)\b/i);
});
