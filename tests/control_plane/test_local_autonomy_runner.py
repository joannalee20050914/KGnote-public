from __future__ import annotations
import importlib.util, json, subprocess, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "scripts/local_autonomy_runner.py")
RUNNER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(RUNNER)

class RunnerTests(unittest.TestCase):
    def test_admission_pending_item_is_prepared_then_dispatched_once(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); item["status"]="ADMISSION_PENDING"; item["admission"]={"sealed":True}
            pending=self.scheduler_pending([item]); pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text(""); epoch=repo/"epoch.json"; epoch.write_text("{}"); admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"{}\n","")
            receipt={"status":"READY","order_path":item["order_path"],"pull_request":27,"head":"a"*40,"fingerprint":"b"*64,"worktree":"/tmp/w","pull_request_url":"https://example/pr/27","issue_title":"Issue"}
            with patch.object(RUNNER.cross_issue_admission,"prepare",return_value=receipt) as prepare:
                result=RUNNER.route_next_ready_work(repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake)
            self.assertEqual(0,result); prepare.assert_called_once()
            saved=json.loads(pending_path.read_text()); self.assertEqual("DISPATCHED",saved["runner_status"])
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
        finally: tmp.cleanup()
    def ready_item(self, work_item_id="D2-T07", dependencies=None):
        return {
            "work_item_id":work_item_id, "status":"READY",
            "authority":{"status":"APPROVED","source":"owner-approved issue"},
            "dependencies":dependencies or [], "order_path":f"output/{work_item_id}.json",
            "budget":{"authorized":2,"used":0},
            "safety":{"isolated_worktree":True,"automatic_merge":False},
        }

    def scheduler_pending(self, items=None):
        return {
            "work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},
            "ready_queue":items or [], "work_item_states":{}, "global_constraints":[],
            "stop_marker_policy":{"scope":"WORK_ITEM","affected_work":["legacy-pr-23"],"release_condition":"legacy owner gate"},
        }

    def test_a_waiting_pr_allows_independent_authorized_ready_work(self):
        pending=self.scheduler_pending([self.ready_item()]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("DISPATCH_READY",decision["status"])
        self.assertEqual("D2-T07",decision["selected"]["work_item_id"])

    def test_a_selected_independent_work_routes_existing_sealed_order(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); pending=self.scheduler_pending([item]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
            pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text("")
            epoch=repo/"epoch.json"; epoch.write_text("{}")
            admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"{}\n","")
            result=RUNNER.route_next_ready_work(
                repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),
                stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake,
            )
            self.assertEqual(0,result)
            saved=json.loads(pending_path.read_text())
            self.assertEqual("DISPATCHED",saved["runner_status"])
            self.assertEqual("DISPATCHED",saved["ready_queue"][0]["status"])
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
            self.assertEqual(3,len(calls))
        finally: tmp.cleanup()

    def test_route_failure_consumes_the_single_reserved_dispatch(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); item["budget"]={"authorized":1,"used":0}
            pending=self.scheduler_pending([item]); pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text(""); epoch=repo/"epoch.json"; epoch.write_text("{}")
            admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs):
                calls.append(command)
                code=7 if command and command[0]==sys.executable and str(router) in command else 0
                return subprocess.CompletedProcess(command,code,"{}\n","")
            result=RUNNER.route_next_ready_work(repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake)
            self.assertEqual(7,result)
            saved=json.loads(pending_path.read_text())
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
            self.assertEqual("DISPATCHING",saved["ready_queue"][0]["status"])
            self.assertEqual("WORK_ITEM_BLOCKED",saved["runner_status"])
        finally: tmp.cleanup()

    def test_b_dependency_on_waiting_pr_is_not_dispatchable(self):
        pending=self.scheduler_pending([self.ready_item("D2-T02",["PR-26"])]); pending["work_item_states"]={"PR-26":"WAITING_HUMAN_ACCEPTANCE"}
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("NO_ELIGIBLE_READY_WORK",decision["status"])
        self.assertEqual("DEPENDENCY_BLOCKED",decision["blocks"][0]["kind"])
        self.assertEqual("DEPENDENCY_SUBGRAPH",decision["blocks"][0]["scope"])

    def test_c_no_eligible_work_is_normal_idle_with_reason(self):
        decision=RUNNER.select_ready_work(self.scheduler_pending(),datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual({"status":"NO_ELIGIBLE_READY_WORK","selected":None,"blocks":[]},decision)

    def test_d_global_window_or_safety_constraint_stops_every_dispatch(self):
        pending=self.scheduler_pending([self.ready_item()])
        outside=RUNNER.select_ready_work(pending,datetime(2026,10,19,20,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("GLOBAL_BLOCKED",outside["status"])
        pending["global_constraints"]=[{"active":True,"reason":"safety isolation unavailable","release_condition":"restore isolation"}]
        safety=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("GLOBAL_BLOCKED",safety["status"])

    def test_e_same_candidate_cannot_flip_changes_required_to_pass_without_new_evidence(self):
        identity={"candidate_commit":"a"*40,"candidate_fingerprint":"b"*64}
        previous={**identity,"verdict":"CHANGES_REQUIRED","findings":[{"id":"finding-r-004","severity":"blocking"}]}
        current={**identity,"verdict":"PASS","findings":[]}
        self.assertIn("without structured new resolution evidence",RUNNER.review_progression_error(previous,current))
        current["resolution_evidence"]=[{"finding_ids":["finding-r-004"],"evidence_identity":"targeted-test:sha256:abc"}]
        self.assertIsNone(RUNNER.review_progression_error(previous,current))

    def test_component_pass_does_not_trigger_preserved_human_gates(self):
        pending=self.scheduler_pending()
        pending.update({
            "status":"ACTIVE",
            "scope":{"issue":8,"objective":"Source Library component"},
            "preserved_human_gates":["PA-HUMAN-1","NS-HUMAN-SMOKE"],
        })
        self.assertEqual("COMPONENT_REVIEW_COMPLETE",RUNNER.status_after_component_pass(pending))
        self.assertIn("not explicitly scheduled","; ".join(RUNNER.human_checkpoint_eligibility_errors(pending)))

    def final_checkpoint(self):
        return {
            "gate_id":"D2-T14-FINAL-HUMAN-ACCEPTANCE",
            "status":"READY",
            "candidate_scope":"COMPLETE_PRODUCT_DELIVERY",
            "candidate_commit":"a"*40,
            "candidate_fingerprint":"b"*64,
            "approved_required_scope_complete":True,
            "required_features_complete":True,
            "dependencies_complete":True,
            "cross_module_integration_complete":True,
            "required_scenarios_complete":True,
            "delivery_evidence_complete":True,
            "no_known_delivery_blockers":True,
            "rc_evidence_complete":True,
            "independent_review_complete":True,
            "integrated_verification_complete":True,
            "trial_entrypoint":"kgnote://final-candidate",
            "formal_human_acceptance_status":"NOT_EVALUATED",
            "authority_refs":[
                "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
                "https://github.com/joannalee20050914/KGnote-public/issues/21",
            ],
        }

    def test_only_explicit_complete_product_candidate_enters_final_acceptance(self):
        pending=self.scheduler_pending()
        pending.update({"candidate_commit":"a"*40,"candidate_fingerprint":"b"*64})
        pending["human_checkpoint"]=self.final_checkpoint()
        self.assertEqual([],RUNNER.human_checkpoint_eligibility_errors(pending))
        self.assertEqual("FINAL_HUMAN_ACCEPTANCE_REQUIRED",RUNNER.status_after_component_pass(pending))
        pending["human_checkpoint"].update({
            "evidence":["RC-01..RC-34 exact candidate receipt","independent review PASS"],
            "acceptance_scope":["installation","daily use","backup and restore"],
        })
        notice=RUNNER.final_human_acceptance_notification(pending["human_checkpoint"])
        self.assertTrue(notice["blocking"])
        self.assertIn("不會自動通過",notice["continuation_notice"])
        for field in ("dependencies_complete","required_features_complete","cross_module_integration_complete"):
            with self.subTest(field=field):
                candidate=json.loads(json.dumps(pending)); candidate["human_checkpoint"][field]=False
                self.assertEqual("COMPONENT_REVIEW_COMPLETE",RUNNER.status_after_component_pass(candidate))

    def test_soft_feedback_is_nonblocking_deduplicated_and_late_reply_bound(self):
        pending=self.scheduler_pending([self.ready_item()])
        event={
            "goal_id":"goal-1","candidate_version":"sha256:abc","experience_scope":"source-import",
            "entrypoint":"http://127.0.0.1:8080/source/1","actually_operable":True,
            "operable_evidence":["HTTP 200 and imported source read-back"],
            "suggested_steps":["Import the fixture","Open Source detail"],
            "experience_questions":["Can you find the imported source without learning internal IDs?"],
        }
        stored,created=RUNNER.register_soft_feedback_event(pending,event)
        self.assertTrue(created); self.assertFalse(stored["blocking"])
        duplicate,created_again=RUNNER.register_soft_feedback_event(pending,event)
        self.assertFalse(created_again); self.assertEqual(stored["notification_key"],duplicate["notification_key"])
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("DISPATCH_READY",decision["status"])
        notice=RUNNER.soft_feedback_notification(stored)
        self.assertTrue(notice["optional"]); self.assertFalse(notice["blocks_development"])
        followup=RUNNER.record_late_soft_feedback(
            pending,stored["notification_key"],feedback="The source is hard to locate",impact_scope=["source-library navigation"],
        )
        self.assertEqual("sha256:abc",followup["candidate_version"])
        self.assertEqual("source-library navigation",followup["impact_scope"][0])

    def test_soft_feedback_requires_operable_result_and_specific_question(self):
        pending=self.scheduler_pending()
        event={"goal_id":"g","candidate_version":"c","experience_scope":"s","entrypoint":"/tmp/demo",
               "actually_operable":False,"operable_evidence":[],"suggested_steps":[],"experience_questions":[]}
        stored,created=RUNNER.register_soft_feedback_event(pending,event)
        self.assertIsNone(stored); self.assertFalse(created)
        self.assertNotIn("soft_feedback_events",pending)

    def test_soft_feedback_silence_survives_restart_without_becoming_pass(self):
        pending=self.scheduler_pending()
        event={
            "goal_id":"goal-1","candidate_version":"sha256:abc","experience_scope":"source-import",
            "entrypoint":"/tmp/demo","actually_operable":True,"operable_evidence":["read-back"],
            "suggested_steps":["Open demo"],"experience_questions":["Is navigation clear?"],
        }
        stored,_=RUNNER.register_soft_feedback_event(pending,event)
        restarted=json.loads(json.dumps(pending))
        self.assertEqual("OPTIONAL_PENDING",restarted["soft_feedback_events"][0]["feedback_status"])
        self.assertEqual(stored["notification_key"],restarted["soft_feedback_events"][0]["notification_key"])

    def test_component_pass_without_ready_successor_is_normal_idle(self):
        pending=self.scheduler_pending(); pending["status"]=RUNNER.status_after_component_pass(pending)
        decision=RUNNER.select_ready_work(
            pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,
        )
        self.assertEqual("COMPONENT_REVIEW_COMPLETE",pending["status"])
        self.assertEqual("NO_ELIGIBLE_READY_WORK",decision["status"])

    def test_restart_of_locally_blocked_item_rechecks_independent_queue_and_idles(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo,status="WORK_ITEM_BLOCKED")
        (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        value=json.loads(pending.read_text())
        value.update({
            "work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},
            "review_result":{"verdict":"PASS","round":4,"consistency_audited":True},
            "ready_queue":[],"work_item_states":{},"global_constraints":[],
            "stop_marker_policy":{"scope":"WORK_ITEM","affected_work":["PR-26"]},
        })
        pending.write_text(json.dumps(value))
        try:
            result=RUNNER.run_once(
                repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),
                lambda *a,**k:self.fail("idle selection must not invoke an external command"),
                router,pending_goal=pending,
            )
            self.assertEqual(0,result)
            saved=json.loads(pending.read_text())
            self.assertEqual("WORK_ITEM_BLOCKED",saved["status"])
            self.assertEqual("NO_ELIGIBLE_READY_WORK",saved["runner_status"])
            self.assertEqual("NO_ELIGIBLE_READY_WORK",saved["scheduler"]["status"])
        finally: tmp.cleanup()

    def test_f_restart_does_not_redispatch_completed_work_or_reset_budget(self):
        item=self.ready_item(); item["status"]="DISPATCHED"; item["budget"]={"authorized":2,"used":1}
        pending=self.scheduler_pending([item])
        first=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        second=RUNNER.select_ready_work(json.loads(json.dumps(pending)),datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("NO_ELIGIBLE_READY_WORK",first["status"])
        self.assertEqual("NO_ELIGIBLE_READY_WORK",second["status"])
        self.assertEqual(1,pending["ready_queue"][0]["budget"]["used"])

    def test_g_work_item_human_gate_preserves_legacy_marker_and_merge_protection(self):
        independent=self.ready_item(); pending=self.scheduler_pending([independent]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("DISPATCH_READY",decision["status"])
        self.assertFalse(independent["safety"]["automatic_merge"])
        self.assertEqual(["legacy-pr-23"],pending["stop_marker_policy"]["affected_work"])

    def test_h_github_projection_distinguishes_all_scheduler_states(self):
        expected={
            "WORK_ITEM_BLOCKED":"queue:work-item-blocked", "DEPENDENCY_BLOCKED":"queue:dependency-blocked",
            "GLOBAL_BLOCKED":"queue:global-blocked", "WAITING_HUMAN_ACCEPTANCE":"queue:waiting-human",
            "NO_ELIGIBLE_READY_WORK":"queue:idle",
            "FINAL_HUMAN_ACCEPTANCE_REQUIRED":"queue:waiting-final-human",
        }
        self.assertEqual(expected,{state:RUNNER.github_queue_label(state) for state in expected})

    def test_formal_model_contexts_are_explicit_and_deterministic_role_has_no_model(self):
        codex=RUNNER.configured_execution_context("CODEX_IMPLEMENTER",pull_request=26,cycle=7)
        claude=RUNNER.configured_execution_context("CLAUDE_PRODUCT_REVIEWER",pull_request=26,review_round=5)
        deterministic=RUNNER.configured_execution_context("DETERMINISTIC_VERIFICATION",pull_request=26)
        self.assertEqual(("gpt-5.6-terra","medium"),(codex["requested_model"],codex["requested_effort"]))
        self.assertEqual(("sonnet","medium"),(claude["requested_model"],claude["requested_effort"]))
        self.assertEqual("NOT_APPLICABLE",deterministic["model_usage_status"])
        self.assertIsNone(deterministic["requested_model"])

    def test_publisher_accepts_only_verified_repair_child_of_last_published_head(self):
        old="a"*40; candidate="b"*40; legacy="c"*40
        verified={"status":"PASS","candidate_commit":candidate,"candidate_fingerprint":"d"*64}
        self.assertIsNone(RUNNER.publish_admission_error(old,candidate,legacy,old,verified))
        self.assertEqual("remote_head_mismatch",RUNNER.publish_admission_error("e"*40,candidate,legacy,old,verified))
        self.assertEqual("candidate_not_verified",RUNNER.publish_admission_error(old,candidate,legacy,old,{**verified,"status":"FAIL"}))
        self.assertEqual("candidate_not_verified",RUNNER.publish_admission_error(old,candidate,legacy,old,{**verified,"candidate_commit":"f"*40}))

    def test_full_verification_identity_requires_exact_head_stable_fingerprint_and_readback(self):
        candidate="a"*40
        evidence={"result":"pass","evidence_readback":True,"repository":{"head":candidate},"fingerprint_stable":True,"fingerprint_after":{"value":"b"*64}}
        self.assertEqual("b"*64,RUNNER.verified_candidate_fingerprint(evidence,candidate))
        for changed in ({"result":"fail"},{"evidence_readback":False},{"repository":{"head":"c"*40}},{"fingerprint_stable":False},{"fingerprint_after":{"value":"short"}}):
            self.assertIsNone(RUNNER.verified_candidate_fingerprint({**evidence,**changed},candidate))

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
        order_path=repo/".ai/linux-worker-order.json"; order_path.write_text("{}")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router))
            self.assertIn("--epoch",calls[0]); self.assertIn("--order",calls[0])
            self.assertEqual(["--order",str(order_path)],calls[2][-2:])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_stop_marker_is_preserved_and_only_routes_idempotent_idle_health(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,20,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=repo/"absent-pending.json"))
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
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=repo/"absent-pending.json"))
            self.assertEqual("ssh",calls[0][0]); self.assertEqual(1,len(calls)); self.assertTrue(marker.exists())
        finally: tmp.cleanup()

    def test_stop_marker_allows_only_private_smoke_canary_order(self):
        tmp, repo, router=self.fixture(); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        canary=ROOT.parent/"KGnote-claude-reviewer-integration/output/claude-reviewer-final/test-order.json"
        original_exists=canary.exists(); original=canary.read_bytes() if original_exists else None
        canary.parent.mkdir(parents=True,exist_ok=True)
        canary.write_text(json.dumps({"event_id":"production-canary-test","working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo","checkpoint_path":str(canary.with_name("test-checkpoint.json"))}))
        calls=[]
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,canary,pending_goal=repo/"absent-pending.json"))
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
            order=json.loads((repo/"output/control-plane/production-runner/successor-linux-worker-order.json").read_text()); self.assertEqual("2026-10-19T18:00:00+08:00",order["deadline_at"])
            self.assertTrue(order["bootstrap_working_directory"])
            self.assertEqual("gpt-5.6-terra",order["execution_context"]["requested_model"])
            self.assertEqual("medium",order["execution_context"]["requested_effort"])
            self.assertEqual("--goal-id",order["command"][1])
            self.assertEqual("26",order["command"][4])
            self.assertEqual("CODEX_DISPATCHED",json.loads((repo/"output/control-plane/production-runner/successor-handoff.json").read_text())["status"])
        finally: tmp.cleanup()

    def test_blocked_successor_keeps_launchagent_idle_without_redispatch(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo,status="BLOCKED"); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        value=json.loads(pending.read_text()); value["runtime_block"]={"retry_blocked":True,"failure_class":"DETERMINISTIC_WORKER_FAILURE"}; pending.write_text(json.dumps(value))
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            self.assertEqual(2,len(calls)); self.assertIn("linux-idle-health-order.json",calls[1][-1])
            self.assertEqual("BLOCKED",json.loads(pending.read_text())["status"])
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
