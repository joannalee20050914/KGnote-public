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

    def pending(self, repo, status="PENDING_ELIGIBLE"):
        path=repo/"pending.json"
        value={"schema_version":"kgnote.pending-successor-goal.v1","goal_id":"GOAL-KGNOTE-SOURCE-LIBRARY-SUCCESSOR-20261019","status":status,"activation_not_before":"2026-10-19T09:00:00+08:00","work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},"authority":{"status":"APPROVED_FOR_FUTURE_WINDOW","source":"owner"},"scope":{"repository":"joannalee20050914/KGnote-public"},"legacy_inheritance":{"pull_request":23,"review_round":8,"cycle":20,"head":"4b6e6eebcddcbd4ef21259a3ece6d92b276473ea","candidate_fingerprint":"38eae708123a99a7abd04327ce079b05248e18646402285a6f83fb49f69a2330"},"continuous_budget":{"new_prs":{"authorized":3,"used":0},"claude_product_reviews":{"authorized":6,"used":0},"codex_implementation_or_repair_cycles":{"authorized":12,"used":0}},"cutover_epoch":"epoch","product_work_started":False,"new_product_pr_created":False}
        path.write_text(json.dumps(value)); return path

    def test_approved_package_routes_one_linux_worker_order_without_host_fallback(self):
        tmp, repo, router=self.fixture(); calls=[]
        (repo / ".ai/linux-worker-order.json").write_text("{}")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertIn("--epoch",calls[0]); self.assertIn("--order",calls[0])
            self.assertEqual(["--order",str(repo/".ai/linux-worker-order.json")],calls[2][-2:])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_stop_marker_is_preserved_and_only_routes_idempotent_idle_health(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,20,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertTrue(marker.exists())
            self.assertEqual("production-idle-health-v2",json.loads((repo/"output/control-plane/production-runner/linux-idle-health-order.json").read_text())["event_id"])
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

    def test_stop_marker_allows_only_private_smoke_canary_order(self):
        tmp, repo, router=self.fixture(); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        canary=Path("/Users/joanna/KGnote-claude-reviewer-integration/output/claude-reviewer-final/test-order.json")
        original_exists=canary.exists(); original=canary.read_bytes() if original_exists else None
        canary.parent.mkdir(parents=True,exist_ok=True)
        canary.write_text(json.dumps({"event_id":"production-canary-test","working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo","checkpoint_path":str(canary.with_name("test-checkpoint.json"))}))
        calls=[]
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,canary))
            self.assertEqual(str(canary),calls[1][-1]); self.assertTrue((repo/".ai/ORCHESTRATOR_STOP").exists())
        finally:
            if original_exists: canary.write_bytes(original)
            else: canary.unlink(missing_ok=True)
            tmp.cleanup()

    def test_missing_linux_order_fails_closed_without_host_execution(self):
        tmp, repo, router=self.fixture()
        try:
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_terminal_unapproved_outside_hours_and_overspend_do_not_run(self):
        cases=[("AUTOMATION_BLOCKED",True,10,0),("IMPLEMENTING",False,10,2),("IMPLEMENTING",True,8,0),("IMPLEMENTING",True,18,0),("IMPLEMENTING",True,20,0)]
        for state, approved, hour, expected in cases:
            tmp, repo, router=self.fixture(state,approved)
            try:
                result=RUNNER.run_once(repo,datetime(2026,10,19,hour,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router)
                self.assertEqual(expected,result)
            finally: tmp.cleanup()
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope["budgets"]["internal_reviews"]={"authorized":1,"used":2}; (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_manually_flipped_approved_status_without_transition_receipt_does_not_run(self):
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope.pop("approval"); (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_weekend_never_dispatches_product_work(self):
        for day in (17, 18):
            tmp, repo, router=self.fixture()
            try:
                self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,day,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
            finally: tmp.cleanup()

    def test_0859_keeps_successor_pending_and_does_not_create_pr(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,8,59,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            self.assertEqual("PENDING_ELIGIBLE",json.loads(pending.read_text())["status"])
            self.assertFalse(any("pr" in command for command in calls))
        finally: tmp.cleanup()

    def test_0900_creates_one_successor_pr_and_dispatches_same_checkpoint(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        head="4b6e6eebcddcbd4ef21259a3ece6d92b276473ea"
        def fake(command,**kwargs):
            calls.append(command); joined=" ".join(command)
            if "git/ref/heads" in joined and "--method" not in command:
                count=sum(1 for item in calls if "git/ref/heads" in " ".join(item) and "--method" not in item)
                return subprocess.CompletedProcess(command,1 if count==1 else 0,"" if count==1 else json.dumps({"object":{"sha":head}}),"")
            if "git/refs" in joined: return subprocess.CompletedProcess(command,0,"{}","")
            if "pr list" in joined: return subprocess.CompletedProcess(command,0,"[]","")
            if "pr create" in joined: return subprocess.CompletedProcess(command,0,"https://github.com/joannalee20050914/KGnote-public/pull/26\n","")
            if "pr view" in joined: return subprocess.CompletedProcess(command,0,json.dumps({"number":26,"state":"OPEN","isDraft":True,"headRefName":"codex/source-library-successor-20261019","baseRefName":"codex/issue-19-real-review","url":"https://github.com/joannalee20050914/KGnote-public/pull/26"}),"")
            return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,9,0,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            value=json.loads(pending.read_text()); self.assertEqual("ACTIVE",value["status"]); self.assertEqual(26,value["successor_pull_request"])
            order=json.loads((repo/".ai/linux-worker-order.json").read_text()); self.assertEqual("2026-10-19T18:00:00+08:00",order["deadline_at"])
            self.assertEqual("CODEX_DISPATCHED",json.loads((repo/".ai/SUCCESSOR_HANDOFF.json").read_text())["status"])
        finally: tmp.cleanup()

    def test_repeated_pending_read_reuses_existing_pr(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); calls=[]; head="4b6e6eebcddcbd4ef21259a3ece6d92b276473ea"
        def fake(command,**kwargs):
            calls.append(command); joined=" ".join(command)
            if "git/ref/heads" in joined: return subprocess.CompletedProcess(command,0,json.dumps({"object":{"sha":head}}),"")
            if "pr list" in joined: return subprocess.CompletedProcess(command,0,json.dumps([{"number":26,"state":"OPEN","isDraft":True,"headRefName":"codex/source-library-successor-20261019","baseRefName":"codex/issue-19-real-review","url":"url"}]),"")
            return subprocess.CompletedProcess(command,0,"","")
        try:
            order,errors=RUNNER.prepare_successor_handoff(repo,pending,datetime(2026,10,19,9,tzinfo=ZoneInfo("Asia/Taipei")),fake)
            self.assertFalse(errors); self.assertIsNotNone(order); self.assertFalse(any("pr create" in " ".join(command) for command in calls))
        finally: tmp.cleanup()

if __name__ == "__main__": unittest.main()
