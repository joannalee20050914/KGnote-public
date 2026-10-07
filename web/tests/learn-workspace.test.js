import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {buildLearnWorkspace, claimsForEvidence, glossesForScope, structureChildren} from "../learn-workspace.js";

const model = JSON.parse(await readFile(new URL("../fixtures/os-overview-guided-map.json", import.meta.url)));
const overlay = JSON.parse(await readFile(new URL("../fixtures/os-overview-claim-review-overlay.json", import.meta.url)));
const source = await readFile(new URL("../fixtures/os-overview-review.md", import.meta.url), "utf8");
const structure = JSON.parse(await readFile(new URL("../fixtures/os-learning-structure.json", import.meta.url)));
const assist = JSON.parse(await readFile(new URL("../fixtures/os-reading-assist.json", import.meta.url)));

test("Learn is read-first and keeps disputed source content visible with a warning", () => {
  const workspace = buildLearnWorkspace(model, overlay, source);
  assert.equal(workspace.status, "ready");
  assert.equal(workspace.groups.length, 5);
  const disputed = workspace.propositions.find(item => item.edge_id === "edge_os_interrupt_driver");
  assert.equal(disputed.review.factual_status, "needs_revision");
  assert.equal(disputed.review.teaching_answer_status, "blocked");
  assert.equal(disputed.evidence[0].locator.value, "L36-L39");
});

test("Learning Structure is recursive view navigation while Reading Assist stays explicit", () => {
  const workspace = buildLearnWorkspace(model, overlay, source, structure, assist);
  assert.equal(workspace.status, "ready");
  assert.deepEqual(structureChildren(workspace).map(item => item.id), ["os_root"]);
  assert.ok(structureChildren(workspace, "os_root").length > 3);
  assert.equal(workspace.reading_assist.glosses[0].term, "PID");
  assert.equal(workspace.reading_assist.glosses[0].required_depth, "define");
  assert.equal(workspace.reading_assist.glosses.some(item => item.term === "DMA"), false);
});

test("Evidence selection reports zero, one, or every candidate without array-order selection", () => {
  const workspace = buildLearnWorkspace(model, overlay, source);
  const first = claimsForEvidence(workspace, "evidence_os_scheduling");
  assert.deepEqual(first.claims.map(item => item.claim_id), ["edge_os_aging_starvation", "edge_os_quantum_context"]);
  const reversedModel = structuredClone(model);
  reversedModel.propositions.reverse();
  const reversed = claimsForEvidence(buildLearnWorkspace(reversedModel, overlay, source), "evidence_os_scheduling");
  assert.deepEqual(reversed, first);
  const zeroWorkspace = structuredClone(workspace);
  zeroWorkspace.evidence.push({id: "evidence_unmapped", locator: {kind: "line_range", value: "L1-L1"}});
  assert.deepEqual(claimsForEvidence(zeroWorkspace, "evidence_unmapped").claims, []);
});

test("SC-12 the same concept gets context-local depth without becoming a concept mastery label", () => {
  const contextual = structuredClone(assist);
  contextual.glosses = [
    {...contextual.glosses[0], id: "gloss_process_definition", concept_ref: "concept_process", locator: {kind: "line_range", value: "L18-L18"}, required_depth: "define"},
    {...contextual.glosses[0], id: "gloss_process_application", concept_ref: "concept_process", locator: {kind: "line_range", value: "L51-L51"}, required_depth: "apply"},
  ];
  const workspace = buildLearnWorkspace(model, overlay, source, structure, contextual);
  const definitionScope = {source_anchors: [{locator: {value: "L15-L20"}}]};
  const applicationScope = {source_anchors: [{locator: {value: "L49-L54"}}]};
  assert.deepEqual(glossesForScope(workspace, definitionScope).map(item => item.required_depth), ["define"]);
  assert.deepEqual(glossesForScope(workspace, applicationScope).map(item => item.required_depth), ["apply"]);
  assert.equal(workspace.concepts.find(item => item.id === "concept_process").required_depth, undefined);
});

test("SC-10 prior encounter rendering is event-backed and not inferred from Concept existence",async()=>{
  const app=await readFile(new URL("../learn-app.js",import.meta.url),"utf8");
  assert.match(app,/prior_encounters/);
  assert.match(app,/不代表已理解/);
});

test("SC-08 structural semantics remain typed view data and do not become canonical propositions",()=>{
  const before=structuredClone(model.propositions);
  const osWorkspace=buildLearnWorkspace(model,overlay,source,structure,assist);
  const relations=new Set(osWorkspace.structure.nodes.map(node=>node.organizing_relation));
  for(const relation of ["alternatives","contrast","sequence","problem_solution"])assert.ok(relations.has(relation));
  assert.deepEqual(model.propositions,before);
  assert.equal(osWorkspace.propositions.some(item=>relations.has(item.linking_phrase)),false);
});

test("SC-31 a third synthetic unit uses the same workspace renderer without unit-name branches",()=>{
  const syntheticModel=structuredClone(model);syntheticModel.learning_unit.id="synthetic_generic_unit";
  const syntheticOverlay=structuredClone(overlay);syntheticOverlay.learning_unit_id="synthetic_generic_unit";
  const syntheticStructure=structuredClone(structure);syntheticStructure.learning_unit_id="synthetic_generic_unit";syntheticStructure.structure_id="synthetic_structure";
  const syntheticAssist=structuredClone(assist);syntheticAssist.learning_unit_id="synthetic_generic_unit";
  const result=buildLearnWorkspace(syntheticModel,syntheticOverlay,source,syntheticStructure,syntheticAssist);
  assert.equal(result.status,"ready");assert.equal(result.learning_unit.id,"synthetic_generic_unit");
  assert.equal(result.structure.nodes.length,structure.nodes.length);
});
