import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

test("SC-03 Learn saves exact scope breadcrumb selection and unresolved question",async()=>{
  const learn=await readFile(new URL("../learn-app.js",import.meta.url),"utf8");
  const html=await readFile(new URL("../learn.html",import.meta.url),"utf8");
  for(const field of ["source_scope","structural_breadcrumb","selected","unresolved_question"]) assert.match(learn,new RegExp(field));
  assert.match(html,/我現在卡在哪/);assert.match(html,/保存這個續學點/);
  assert.match(learn,/resumeNodeId/);assert.match(learn,/已回到上次的精確閱讀位置/);
  assert.match(learn,/saved\.unresolved_question/);
});

test("SC-03 catalog prefers exact context but keeps Attempt fallback",async()=>{
  const home=await readFile(new URL("../home-app.js",import.meta.url),"utf8");
  assert.match(home,/回到上次卡住的位置/);assert.match(home,/未解：/);assert.match(home,/最近 Attempt/);
});
