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
        envelope={"schema_version":"kgnote.work-package-envelope.v1","status":"APPROVED" if approved else "PENDING_OWNER_APPROVAL","goal_id":"goal","work_package_id":"package","authority_record":"approval","approval":{"source_status":"RECONCILING","receipt":".ai/reconciliation-receipt.json"},"work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:30"},"budgets":{name:{"authorized":2,"used":0} for name in ("local_repairs","internal_reviews","external_reviews")}}
        (repo / ".ai/work-package-envelope.json").write_text(json.dumps(envelope))
        router = repo / "linux_worker_router.py"; router.write_text("")
        return tmp, repo, router

    def test_approved_package_routes_one_linux_worker_order_without_host_fallback(self):
        tmp, repo, router=self.fixture(); calls=[]
        (repo / ".ai/linux-worker-order.json").write_text("{}")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertEqual(["--order",str(repo/".ai/linux-worker-order.json")],calls[1][-2:])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_stop_marker_is_preserved_and_only_routes_idempotent_idle_health(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,20,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertTrue(marker.exists())
            self.assertEqual("production-idle-health-v1",json.loads((repo/"output/control-plane/production-runner/linux-idle-health-order.json").read_text())["event_id"])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_guest_unavailable_fails_closed_before_router(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs):
            calls.append(command); return subprocess.CompletedProcess(command,255,"","offline")
        try:
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertEqual("ssh",calls[0][0]); self.assertEqual(1,len(calls)); self.assertTrue(marker.exists())
        finally: tmp.cleanup()

    def test_missing_linux_order_fails_closed_without_host_execution(self):
        tmp, repo, router=self.fixture()
        try:
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_terminal_unapproved_outside_hours_and_overspend_do_not_run(self):
        cases=[("AUTOMATION_BLOCKED",True,10,0),("IMPLEMENTING",False,10,2),("IMPLEMENTING",True,20,0)]
        for state, approved, hour, expected in cases:
            tmp, repo, router=self.fixture(state,approved)
            try:
                result=RUNNER.run_once(repo,datetime(2026,10,17,hour,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router)
                self.assertEqual(expected,result)
            finally: tmp.cleanup()
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope["budgets"]["internal_reviews"]={"authorized":1,"used":2}; (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_manually_flipped_approved_status_without_transition_receipt_does_not_run(self):
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope.pop("approval"); (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

if __name__ == "__main__": unittest.main()
