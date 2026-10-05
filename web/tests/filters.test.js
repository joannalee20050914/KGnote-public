import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildGraphViewQuery, defaultViewState, modeDescription} from "../filters.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/phase0-graph-view.json", import.meta.url), "utf8"));
const view = fixture.view;

test("builds deterministic full and 1/2/3-hop versioned queries", () => {
  const desktop = defaultViewState(view);
  assert.equal(buildGraphViewQuery(view, desktop).query.hop_depth, null);
  for (const hop_depth of [1, 2, 3]) {
    const state = {...desktop, focus_node_id: "concept_correlation", hop_depth};
    const first = buildGraphViewQuery(view, state);
    const second = buildGraphViewQuery(structuredClone(view), structuredClone(state));
    assert.deepEqual(first, second);
    assert.equal(first.query.hop_depth, hop_depth);
    assert.equal(modeDescription(first.query), `Local · ${hop_depth} hop${hop_depth === 1 ? "" : "s"}`);
  }
});

test("normalizes OR-within filter values for planner AND-across groups", () => {
  const state = defaultViewState(view);
  state.filters = {
    node_kinds: ["learning_event", "concept", "concept"],
    edge_classes: ["learning", "canonical"],
    relations: ["related_to", "asked_about"],
    spaces: ["causal-inference"],
  };
  assert.deepEqual(buildGraphViewQuery(view, state).query.filters, {
    node_kinds: ["concept", "learning_event"],
    edge_classes: ["canonical", "learning"],
    relations: ["asked_about", "related_to"],
    spaces: ["causal-inference"],
  });
});

test("mobile default is planner-bound one hop and reset is copy-safe", () => {
  const state = defaultViewState(view, {mobile: true, mobileFocusId: "concept_confounder"});
  assert.equal(state.focus_node_id, "concept_confounder");
  assert.equal(state.hop_depth, 1);
  state.filters.node_kinds.push("concept");
  assert.deepEqual(defaultViewState(view).filters.node_kinds, []);
});

test("rejects malformed, stale/unavailable, unknown focus, and invalid hops safely", () => {
  assert.equal(buildGraphViewQuery(view, null).status, "rejected");
  const unknown = defaultViewState(view);
  Object.assign(unknown, {focus_node_id: "private path", hop_depth: 1});
  assert.deepEqual(buildGraphViewQuery(view, unknown), {status: "rejected", problem: {code: "invalid_focus_or_hop"}});
  const unavailable = defaultViewState(view);
  unavailable.filters.spaces = ["private space"];
  assert.deepEqual(buildGraphViewQuery(view, unavailable), {status: "rejected", problem: {code: "unavailable_filter_value"}});
});

test("UI exposes all query controls and delegates execution to the read-only endpoint", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  const app = await readFile(new URL("../app.js", import.meta.url), "utf8");
  for (const id of ["focus-node", "hop-depth", "filter-groups", "update-view", "reset-query"]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(app, /fetch\("\/api\/graph-view"/);
  assert.match(app, /body: "null"/);
  assert.doesNotMatch(app, /phase0-graph-view\.json|fixtureUrl/);
  assert.match(app, /closeDetails\(\{restoreFocus: false\}\)/);
  assert.match(app, /function rejectView/);
  assert.match(app, /payload = null/);
  assert.match(app, /modeLabel\.textContent = "畫面無法使用"/);
  assert.match(app, /rejectView\("無法顯示要求的知識圖。 /);
  assert.doesNotMatch(html + app, /contenteditable|\b(delete|merge|rename|apply canonical)\b/i);
});
