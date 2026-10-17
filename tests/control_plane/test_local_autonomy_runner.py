from __future__ import annotations
import importlib.util, json, subprocess, tempfile, unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "scripts/local_autonomy_runner.py")
RUNNER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(RUNNER)

class RunnerTests(unittest.TestCase):
    def fixture(self, state="IMPLEMENTING", approved=True):
        tmp = tempfile.TemporaryDirectory(); repo = Path(tmp.name)
        (repo / ".ai").mkdir(); (repo / "scripts").mkdir(); (repo / "scripts/codex_orchestrator.py").write_text("")
        (repo / ".ai/ORCHESTRATOR_STATE.json").write_text(json.dumps({"active_goal":"goal","work_package":"package","state":state}))
        envelope={"schema_version":"kgnote.work-package-envelope.v1","status":"APPROVED" if approved else "PENDING_OWNER_APPROVAL","goal_id":"goal","work_package_id":"package","authority_record":"approval","work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:30"},"budgets":{name:{"authorized":2,"used":0} for name in ("local_repairs","internal_reviews","external_reviews")}}
        (repo / ".ai/work-package-envelope.json").write_text(json.dumps(envelope))
        return tmp, repo

    def test_approved_package_runs_one_bounded_resume(self):
        tmp, repo=self.fixture(); calls=[]
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake))
            self.assertEqual(["resume","--max-steps","1"],calls[0][-3:])
        finally: tmp.cleanup()

    def test_terminal_unapproved_outside_hours_and_overspend_do_not_run(self):
        cases=[("AUTOMATION_BLOCKED",True,10,0),("IMPLEMENTING",False,10,2),("IMPLEMENTING",True,20,0)]
        for state, approved, hour, expected in cases:
            tmp, repo=self.fixture(state,approved)
            try:
                result=RUNNER.run_once(repo,datetime(2026,10,17,hour,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"))
                self.assertEqual(expected,result)
            finally: tmp.cleanup()
        tmp, repo=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope["budgets"]["internal_reviews"]={"authorized":1,"used":2}; (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run")))
        finally: tmp.cleanup()

if __name__ == "__main__": unittest.main()
