import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {buildExposureRequest, makeId, soakHasAssessmentFields, supportProgression} from "../soak-workspace.js";

const item={item_id:"soak_os_aging_starvation",concept_id:"concept_aging",source_refs:["src_os_overview_review"]};

test("SC-02 Soak event carries observation identity without assessment fields",()=>{
  assert.equal(makeId("soak",()=>"01234567-89ab-cdef-0123-456789abcdef"),"soak_0123456789abcdef0123456789abcdef");
  const built=buildExposureRequest({eventId:"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",sessionId:"soak_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",unitId:"unit",item,kind:"skipped",occurredAt:"2026-09-20T02:30:00Z"});
  assert.equal(built.status,"ready"); assert.equal(soakHasAssessmentFields(built.request),false);
});

test("SC-18 Soak page states no debt and never submits an Attempt",async()=>{
  const html=await readFile(new URL("../soak.html",import.meta.url),"utf8");
  const app=await readFile(new URL("../soak-app.js",import.meta.url),"utf8");
  assert.match(html,/不產生答錯、分數或積欠/);
  assert.equal(app.includes("/api/attempts"),false);
  assert.equal(app.includes("/api/due-actions"),false);
  assert.match(app,/\/api\/exposures/);
});

test("SC-17 support fading is a deterministic representation progression, not one permanent prompt",async()=>{
  const fixture=JSON.parse(await readFile(new URL("../fixtures/bitepacer-soak.json",import.meta.url)));
  const result=supportProgression(fixture.items[0]);
  assert.equal(result.status,"ready");
  assert.deepEqual(result.steps.map(step=>step.stage),["high_similarity","cued","changed_context","explanation","application"]);
  assert.deepEqual(result.steps.map(step=>step.response_expected),[false,false,false,true,true]);
  result.steps[0].content="mutated";
  assert.notEqual(fixture.items[0].support_progression[0].content,"mutated");
  const reordered=structuredClone(fixture.items[0]);reordered.support_progression.reverse();
  assert.equal(supportProgression(reordered).status,"ready","the fixture order is deterministic but not a universal progression lock");
  const duplicate=structuredClone(fixture.items[0]);duplicate.support_progression[1].stage=duplicate.support_progression[0].stage;
  assert.equal(supportProgression(duplicate).status,"rejected");
  const app=await readFile(new URL("../soak-app.js",import.meta.url),"utf8");
  assert.match(app,/next-support/);
});
