import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from linux_worker_router import (
    GUEST_HOST, RoutingError, WorkerOrder, bootstrap_command, command_digest,
    execution_evidence, remote_command, route, sandbox_command,
    validate_bootstrap_identity,
)


class FakeProcess:
    def __init__(self, command, returncode=0):
        self.command = command; self.returncode = returncode
    def communicate(self, timeout=None): return "guest-output", ""
    def terminate(self): pass
    def kill(self): pass


class DeadlineProcess(FakeProcess):
    def __init__(self, command):
        super().__init__(command, returncode=-15); self.calls = 0; self.terminated = False
    def communicate(self, timeout=None):
        self.calls += 1
        if self.calls == 1: raise subprocess.TimeoutExpired(self.command, timeout)
        return "checkpoint-saved", ""
    def terminate(self): self.terminated = True


class LinuxWorkerRoutingTest(unittest.TestCase):
    def product_identity(self, **changes):
        identity = {
            "schema_version":"kgnote.authorized-product-goal-work-identity.v1",
            "identity_kind":"KGNOTE_PRODUCT_GOAL", "authority_kind":"GITHUB_OWNER_APPROVAL",
            "repository":"joannalee20050914/KGnote-public", "issue":9,
            "goal_id":"GOAL-KGNOTE-O2-READING-EXPERIENCE",
            "goal_version":"2026-10-23.2-s0-s2-proposal",
            "goal_spec_sha256":"82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604",
            "work_item_id":"WI-O2-A-IMPLEMENT", "provider":"codex", "stage":"codex",
            "order_event_id":"o2-wi-o2-a-implement-codex-0123456789abcdef",
            "branch":"codex/o2-reading-experience", "worktree_slug":"goal-o2-reading-experience",
            "authority_record":"https://github.com/joannalee20050914/KGnote-public/issues/9",
            "authority_sha256":"c"*64, "authority_status":"APPROVED",
            "authority_action":"APPROVE", "go_live_authorized":True,
        }
        identity.update(changes)
        return identity

    def test_o2_product_goal_lanes_are_identity_bound(self):
        cases = [
            ("WI-O2-A-IMPLEMENT", "codex", "codex", "o2-wi-o2-a-implement-codex-0123456789abcdef"),
            ("WI-O2-A-VERIFY", "publisher", "NONE", "o2-wi-o2-a-verify-publisher-0123456789abcdef"),
            ("WI-O2-A-PUBLISH", "push", "NONE", "o2-wi-o2-a-publish-push-0123456789abcdef"),
            ("WI-O2-A-REVIEW", "claude", "claude", "o2-wi-o2-a-review-claude-0123456789abcdef"),
            ("WI-O2-B-REPAIR", "codex", "codex", "o2-wi-o2-b-repair-codex-0123456789abcdef"),
        ]
        directory = Path("/home/kgnote/.local/share/kgnote/work-items/goal-o2-reading-experience")
        for work_item, stage, provider, event in cases:
            with self.subTest(work_item=work_item):
                identity = self.product_identity(
                    work_item_id=work_item, stage=stage, provider=provider,
                    order_event_id=event,
                )
                validate_bootstrap_identity(
                    identity, event_id=event, stage=stage,
                    working_directory=directory,
                )

    def test_o2_product_goal_handoff_is_fixed_and_writable_in_sandbox(self):
        event = "o2-wi-o2-a-implement-codex-0123456789abcdef"
        directory = Path("/home/kgnote/.local/share/kgnote/work-items/goal-o2-reading-experience")
        handoff = Path("/home/kgnote/.local/share/kgnote/runtime-state/product-goal")
        raw = {
            "schema_version": "kgnote.linux-worker-order.v1", "event_id": event,
            "stage": "codex", "working_directory": str(directory),
            "handoff_directory": str(handoff), "command": ["/usr/bin/true"],
            "checkpoint_path": "/tmp/checkpoint.json", "bootstrap_working_directory": True,
            "bootstrap_identity": self.product_identity(),
        }
        order = WorkerOrder.from_dict(raw)
        command = sandbox_command(order)
        self.assertIn(str(handoff), command)
        raw["handoff_directory"] = "/home/kgnote/.local/share/kgnote/runtime-state/foreign"
        with self.assertRaisesRegex(RoutingError, "handoff_directory"):
            WorkerOrder.from_dict(raw)

    def test_o2_product_goal_identity_rejects_cross_goal_stage_digest_event_and_path(self):
        event = "o2-wi-o2-a-implement-codex-0123456789abcdef"
        directory = Path("/home/kgnote/.local/share/kgnote/work-items/goal-o2-reading-experience")
        cases = [
            (self.product_identity(goal_id="GOAL-KGNOTE-FOREIGN"), directory),
            (self.product_identity(stage="claude"), directory),
            (self.product_identity(goal_spec_sha256="0"*64), directory),
            (self.product_identity(order_event_id="o2-wi-o2-a-implement-codex-fedcba9876543210"), directory),
            (self.product_identity(go_live_authorized=False), directory),
            (self.product_identity(work_item_id="WI-O2-C-IMPLEMENT"), directory),
            (self.product_identity(branch="codex/other-o2-branch"), directory),
            (self.product_identity(), Path("/home/kgnote/.local/share/kgnote/escape")),
        ]
        for identity, path in cases:
            with self.subTest(identity=identity, path=path), self.assertRaises(RoutingError):
                validate_bootstrap_identity(
                    identity, event_id=event, stage="codex",
                    working_directory=path,
                )

    def generic_identity(self):
        return {
            "schema_version":"kgnote.authorized-work-identity.v1",
            "repository":"joannalee20050914/KGnote-public", "issue":14,
            "goal_id":"GOAL-KGNOTE-D2-T07-TUTOR-HANDOFF-20261019", "work_item_id":"D2-T07",
            "branch":"codex/issue-14-tutor-handoff-feasibility", "worktree_slug":"issue-14-d2-t07",
            "authority_record":"https://github.com/joannalee20050914/KGnote-public/issues/14",
            "authority_sha256":"b"*64,
        }

    def test_generic_bootstrap_is_bound_to_exact_authorized_identity(self):
        order=self.order(
            event_id="issue-14-d2-t07-codex-20261019",
            stage="codex",
            working_directory="/home/kgnote/.local/share/kgnote/work-items/issue-14-d2-t07",
            bootstrap_working_directory=True,
            bootstrap_identity=self.generic_identity(),
        )
        self.assertIn("--identity-json",bootstrap_command(order))
        with self.assertRaisesRegex(RoutingError,"slug|directory|event"):
            self.order(
                event_id="issue-14-d2-t07-codex-20261019",
                stage="codex",
                working_directory="/home/kgnote/.local/share/kgnote/work-items/issue-14-d2-t07",
                bootstrap_working_directory=True,
                bootstrap_identity={**self.generic_identity(),"issue":15},
            )
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.checkpoint = Path(self.temp.name) / "route.json"
    def tearDown(self): self.temp.cleanup()

    def order(self, **changes):
        raw = {"schema_version": "kgnote.linux-worker-order.v1",
               "event_id": "smoke-round-1", "stage": "publisher",
               "working_directory": "/home/kgnote/.local/share/kgnote/smoke-repo",
               "command": ["/usr/bin/true"],
               "checkpoint_path": str(self.checkpoint), "memory_max": "512M",
               "tasks_max": 32, "timeout_seconds": 30, "lease_timeout_seconds": 5}
        return WorkerOrder.from_dict({**raw, **changes})

    def test_route_is_guest_only_and_cgroup_bounded(self):
        command = remote_command(self.order())
        self.assertIn("--property=MemoryMax=512M", command)
        self.assertIn("--property=TasksMax=32", command)
        self.assertIn("--property=KillMode=control-group", command)
        self.assertIn("--property=NoNewPrivileges=yes", command)
        self.assertEqual("/usr/bin/python3", command[command.index("--property=PrivateTmp=yes") + 1])
        self.assertIn("/home/kgnote/.local/share/kgnote/runtime/linux_landlock_exec.py", command)
        self.assertNotIn("/home/kgnote/.claude", command)
        self.assertNotIn("/home/kgnote/.codex", command)
        self.assertNotIn("/home/kgnote/.ssh", command)

    def test_stage_profiles_expose_only_their_own_credentials(self):
        codex = sandbox_command(self.order(stage="codex"))
        claude = sandbox_command(self.order(stage="claude"))
        push = sandbox_command(self.order(stage="push"))
        self.assertIn("/home/kgnote/.codex", codex)
        self.assertNotIn("/home/kgnote/.claude", codex)
        self.assertNotIn("/home/kgnote/.ssh", codex)
        self.assertIn("/home/kgnote/.claude", claude)
        self.assertNotIn("/home/kgnote/.codex", claude)
        self.assertNotIn("/home/kgnote/.ssh", claude)
        self.assertIn("/home/kgnote/.ssh", push)
        self.assertNotIn("/home/kgnote/.codex", push)
        self.assertNotIn("/home/kgnote/.claude", push)

    def test_claude_workspace_is_read_only(self):
        command = sandbox_command(self.order(stage="claude"))
        worktree = "/home/kgnote/.local/share/kgnote/smoke-repo"
        self.assertEqual("--ro", command[command.index(worktree) - 1])

    def test_claude_and_ingestion_can_share_separate_handoff_without_candidate_write(self):
        handoff = "/home/kgnote/.local/share/kgnote/final-smoke"
        for stage in ("claude", "ingestion"):
            command = sandbox_command(self.order(stage=stage, handoff_directory=handoff))
            self.assertEqual("--rw", command[command.index(handoff) - 1])
        with self.assertRaises(RoutingError):
            self.order(stage="codex", handoff_directory=handoff)

    def test_success_is_checkpointed_and_duplicate_does_not_launch(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command); return subprocess.CompletedProcess(command, 0, "", "")
        launches = []
        def popen(command, **kwargs): launches.append(command); return FakeProcess(command)
        first = route(self.order(), run=run, popen=popen)
        second = route(self.order(), run=run, popen=lambda *a, **k: self.fail("duplicate launched"))
        self.assertEqual("COMPLETED", first["status"])
        self.assertEqual("ALREADY_COMPLETED", second["status"])
        self.assertFalse(first["host_fallback_used"])
        self.assertEqual("guest-output",Path(first["stdout_path"]).read_text())
        self.assertEqual(1, len(launches))
        self.assertIn(GUEST_HOST, launches[0])

    def test_codex_execution_evidence_adds_terminal_token_footer(self):
        configured={"requested_model":"gpt-5.6-terra","requested_effort":"medium","effective_status":"EFFECTIVE_UNKNOWN"}
        order=self.order(stage="codex",execution_context=configured)
        stdout='KGNOTE_EXECUTION_EVIDENCE='+json.dumps(configured)+'\ntokens used\n12,345\n'
        evidence=execution_evidence(order,stdout,"")
        self.assertEqual("gpt-5.6-terra",evidence["requested_model"])
        self.assertEqual(12345,evidence["token_usage"]["total_tokens"])

    def test_deterministic_execution_evidence_is_preserved_without_model(self):
        context={"role":"DETERMINISTIC_VERIFICATION","model_usage_status":"NOT_APPLICABLE","requested_model":None}
        evidence=execution_evidence(self.order(stage="ingestion",execution_context=context),"ok","")
        self.assertEqual("NOT_APPLICABLE",evidence["model_usage_status"])
        self.assertIsNone(evidence["requested_model"])

    def test_successor_bootstrap_precedes_landlock_and_duplicate_still_launches_once(self):
        order = self.order(
            event_id="source-library-successor-codex-20261019", stage="codex",
            working_directory="/home/kgnote/.local/share/kgnote/source-library-successor-20261019",
            bootstrap_working_directory=True,
        )
        calls=[]; launches=[]
        def run(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"READY"}\n',"")
        first=route(order,run=run,popen=lambda command,**kwargs: launches.append(command) or FakeProcess(command))
        second=route(order,run=run,popen=lambda *a,**k:self.fail("duplicate launched"))
        self.assertEqual("COMPLETED",first["status"]); self.assertEqual("ALREADY_COMPLETED",second["status"])
        self.assertEqual(bootstrap_command(order),shlex.split(calls[0][-1])); self.assertEqual(1,len(launches))

    def test_bootstrap_failure_is_durable_blocked_and_never_enters_landlock(self):
        order = self.order(
            event_id="source-library-successor-codex-20261019", stage="codex",
            working_directory="/home/kgnote/.local/share/kgnote/source-library-successor-20261019",
            bootstrap_working_directory=True,
        )
        run=lambda command,**kwargs: subprocess.CompletedProcess(command,2,"","rejected")
        result=route(order,run=run,popen=lambda *a,**k:self.fail("worker launched"))
        self.assertEqual("BLOCKED",result["status"]); self.assertEqual("bootstrap_failed",result["reason"])

    def test_ssh_remote_command_round_trips_spaces_and_quotes(self):
        order = self.order(command=["/usr/bin/python3", "-c", "print('quoted value')"])
        launches = []
        run = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", "")
        route(order, run=run, popen=lambda command, **kwargs: launches.append(command) or FakeProcess(command))
        self.assertEqual(remote_command(order), shlex.split(launches[0][-1]))

    def test_event_reuse_with_different_command_fails_closed(self):
        self.checkpoint.write_text(json.dumps({"event_id": "smoke-round-1",
                                               "command_digest": "wrong", "status": "COMPLETED"}))
        with self.assertRaisesRegex(RoutingError, "different command bytes"):
            route(self.order())

    def test_guest_unavailable_has_no_host_fallback(self):
        def run(command, **kwargs): return subprocess.CompletedProcess(command, 255, "", "offline")
        with self.assertRaisesRegex(RoutingError, "dispatch denied"):
            route(self.order(), run=run, popen=lambda *a, **k: self.fail("launched"))

    def test_restart_does_not_relaunch_interrupted_event(self):
        order = self.order()
        self.checkpoint.write_text(json.dumps({
            "schema_version": "kgnote.linux-worker-route.v1", "status": "RUNNING",
            "event_id": order.event_id, "command_digest": command_digest(order),
        }))
        run = lambda command, **kwargs: subprocess.CompletedProcess(command, 3, "inactive", "")
        result = route(order, run=run, popen=lambda *a, **k: self.fail("relaunch"))
        self.assertEqual("FAILED_CLOSED", result["status"])
        self.assertEqual("controller_interrupted", result["reason"])

    def test_restart_refuses_duplicate_while_prior_unit_is_active(self):
        order = self.order()
        self.checkpoint.write_text(json.dumps({
            "schema_version": "kgnote.linux-worker-route.v1", "status": "RUNNING",
            "event_id": order.event_id, "command_digest": command_digest(order),
        }))
        run = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "active", "")
        with self.assertRaisesRegex(RoutingError, "duplicate dispatch denied"):
            route(order, run=run, popen=lambda *a, **k: self.fail("relaunch"))

    def test_next_window_resumes_same_event_after_deadline_stop(self):
        order = self.order(deadline_at="2026-10-20T18:00:00+08:00")
        self.checkpoint.write_text(json.dumps({
            "schema_version": "kgnote.linux-worker-route.v1", "status": "DEADLINE_STOPPED",
            "reason": "work_window_deadline", "event_id": order.event_id,
            "command_digest": command_digest(order),
        }))
        launches=[]
        run=lambda command,**kwargs: subprocess.CompletedProcess(command,0,"","")
        result=route(order,run=run,popen=lambda command,**kwargs: launches.append(command) or FakeProcess(command),now=lambda:datetime.fromisoformat("2026-10-20T09:00:00+08:00"))
        self.assertEqual("COMPLETED",result["status"])
        self.assertEqual(1,len(launches))

    def test_rejects_relative_or_unbounded_orders(self):
        for changes in ({"command": ["claude"]}, {"tasks_max": 513},
                        {"timeout_seconds": 3601}, {"lease_timeout_seconds": 2},
                        {"stage": "generic"}, {"working_directory": "/home/kgnote"}):
            with self.subTest(changes=changes), self.assertRaises(RoutingError):
                self.order(**changes)
        with self.assertRaisesRegex(RoutingError, "bootstrap is not authorized"):
            self.order(bootstrap_working_directory=True)

    def test_repeated_exit_126_becomes_blocked_after_three_attempts(self):
        order=self.order(); calls=[]
        def run(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        for expected in ("FAILED_CLOSED","FAILED_CLOSED","BLOCKED"):
            process=FakeProcess(["ssh"],returncode=126)
            result=route(order,run=run,popen=lambda *a,p=process,**k:p)
            self.assertEqual(expected,result["status"])
        self.assertEqual(3,result["attempt_count"])

    def test_repeated_exit_127_also_becomes_blocked_after_three_attempts(self):
        order=self.order()
        run=lambda command,**kwargs: subprocess.CompletedProcess(command,0,"","")
        for expected in ("FAILED_CLOSED","FAILED_CLOSED","BLOCKED"):
            process=FakeProcess(["ssh"],returncode=127)
            result=route(order,run=run,popen=lambda *a,p=process,**k:p)
            self.assertEqual(expected,result["status"])
        self.assertEqual("deterministic_worker_failure",result["reason"])

    def test_any_repeated_failed_closed_exit_becomes_blocked_after_three_attempts(self):
        order=self.order()
        run=lambda command,**kwargs: subprocess.CompletedProcess(command,0,"","")
        for expected in ("FAILED_CLOSED","FAILED_CLOSED","BLOCKED"):
            process=FakeProcess(["ssh"],returncode=42)
            result=route(order,run=run,popen=lambda *a,p=process,**k:p)
            self.assertEqual(expected,result["status"])
        self.assertEqual(3,result["attempt_count"])

    def test_missing_order_schema_version_is_rejected(self):
        raw={
            "event_id":"smoke-round-1", "stage":"publisher",
            "working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo",
            "command":["/usr/bin/true"], "checkpoint_path":str(self.checkpoint),
        }
        with self.assertRaisesRegex(RoutingError,"schema_version"):
            WorkerOrder.from_dict(raw)

    def test_1800_deadline_stops_worker_and_persists_resumable_checkpoint(self):
        deadline = datetime.fromisoformat("2026-10-19T18:00:00+08:00")
        process = DeadlineProcess(["ssh"])
        run = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", "")
        result = route(
            self.order(deadline_at=deadline.isoformat()), run=run,
            popen=lambda *a, **k: process,
            now=lambda: datetime.fromisoformat("2026-10-19T17:59:59+08:00"),
        )
        self.assertTrue(process.terminated)
        self.assertEqual("DEADLINE_STOPPED", result["status"])
        self.assertEqual("work_window_deadline", result["reason"])
        self.assertEqual(deadline.isoformat(), result["deadline_at"])

    def test_closed_deadline_never_launches_worker(self):
        deadline = "2026-10-19T18:00:00+08:00"
        run = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", "")
        with self.assertRaisesRegex(RoutingError, "deadline is already closed"):
            route(
                self.order(deadline_at=deadline), run=run,
                popen=lambda *a, **k: FakeProcess([]),
                now=lambda: datetime.fromisoformat("2026-10-19T18:00:01+08:00"),
            )
