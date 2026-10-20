from __future__ import annotations

import copy,json,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from kgnote.learning import latest_resume_context,record_resume_context

def request()->dict:
    return {"schema_version":"kgnote.resume-context-save-request.v1","event_id":"resume_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":"unit_os","unit_slug":"os","source_scope":{"source_id":"source_os","locator":"L10-L20"},"structural_breadcrumb":[{"node_id":"root","title":"OS"},{"node_id":"scheduling","title":"排程"}],"selected":{"kind":"structure","id":"scheduling","label":"排程"},"unresolved_question":"Round Robin 的時間片和 context switch 如何連起來？","occurred_at":"2026-09-20T03:00:00Z"}

class ResumeContextTests(unittest.TestCase):
    def test_sc03_exact_context_is_append_only_idempotent_and_read_back(self)->None:
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);value=request()
            self.assertEqual(record_resume_context(root,value).status,"recorded")
            self.assertEqual(record_resume_context(root,value).status,"unchanged")
            changed=copy.deepcopy(value);changed["unresolved_question"]="different"
            self.assertEqual(record_resume_context(root,changed).status,"conflict")
            context=latest_resume_context(root,"unit_os").payload["context"]
            self.assertEqual(context["source_scope"]["locator"],"L10-L20")
            self.assertEqual([item["title"] for item in context["structural_breadcrumb"]],["OS","排程"])
            self.assertIn("context switch",context["unresolved_question"])

    def test_schema_and_corrupt_derived_context_fail_without_source_mutation(self)->None:
        schema=json.loads((Path(__file__).parents[1]/"schemas/resume-context/v1/save-request.schema.json").read_text());Draft202012Validator.check_schema(schema)
        self.assertEqual(list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(request())),[])
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);directory=root/"resume-contexts";directory.mkdir();path=directory/"resume_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json";path.write_text("bad")
            self.assertEqual(latest_resume_context(root,"unit_os").problem_code,"resume_read_failed")
            self.assertEqual(path.read_text(),"bad")

    def test_concurrent_same_context_is_idempotent_and_conflict_cannot_overwrite(self)->None:
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            with ThreadPoolExecutor(max_workers=12) as pool:statuses=list(pool.map(lambda value:record_resume_context(root,value).status,[request() for _ in range(12)]))
            self.assertEqual(statuses.count("recorded"),1);self.assertEqual(statuses.count("unchanged"),11)
            changed=copy.deepcopy(request());changed["unresolved_question"]="conflicting writer"
            self.assertEqual(record_resume_context(root,changed).status,"conflict")
            self.assertIn("context switch",latest_resume_context(root,"unit_os").payload["context"]["unresolved_question"])

if __name__=="__main__":unittest.main()
