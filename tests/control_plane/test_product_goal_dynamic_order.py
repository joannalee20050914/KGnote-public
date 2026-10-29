from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import github_product_goal_control as CONTROL
import codex_control as CODEX
import goal_continuity as GOAL
import goal_runner_adapter as ADAPTER
import local_autonomy_runner as RUNNER
from tests.control_plane.test_github_product_goal_control import comment
from tests.control_plane.runtime_admission_fixtures import runtime_identity
NOW = "2026-10-28T10:00:00+08:00"


class ProductGoalDynamicOrderTest(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(
            (ROOT / "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json").read_text()
        )
        self.state = GOAL.initial_runner_state(self.spec, now=NOW)
        authority_comment = comment(self.spec, login="joannalee20050914")
        authority_comment["html_url"] = "https://github.com/joannalee20050914/KGnote-public/issues/9#issuecomment-100"
        authority_comment["issue_url"] = "https://api.github.com/repos/joannalee20050914/KGnote-public/issues/9"
        authority = CONTROL.resolve_authority([authority_comment], self.spec)["record"]
        self.state.update({
            "authority_record": authority, "authority_lease": "ACTIVE",
            "go_live_authorized": True,
            "lifecycle": {"state":"ACTIVE","revision":1,"changed_at":NOW,"reason":"test authority"},
            "candidate_identity": {
                "commit":"1"*40, "fingerprint":"2"*64,
                "branch":"codex/o2-reading-experience", "pull_request":33,
            },
            "event_cursor": {"sequence": 1, "event_sha256": "3" * 64},
        })
        self.action = {
            "status":"ACTION_READY", "action":"DISPATCH_IMPLEMENTATION",
            "work_item_id":"WI-O2-A-IMPLEMENT", "requires_model":True,
            "provider":"codex", "total_launches_before":0,
        }
        self.runtime_identity = runtime_identity()

    def ensure_bound_order(self, spec, state, action, **kwargs):
        return ADAPTER.ensure_bound_order(
            spec,
            state,
            action,
            runtime_identity=(
                self.runtime_identity if action.get("requires_model") else None
            ),
            **kwargs,
        )

    def write_state(self, repo: Path, state=None):
        path=repo/"state.json"; GOAL.atomic_write_json(path,state or self.state); return path

    def test_runner_creates_seals_and_reuses_same_attempt_order(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            updated,path,order,attempt=self.ensure_bound_order(
                self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            self.assertEqual("RUNNER_DYNAMIC_V1",updated["work_items"][0]["dispatch_binding"]["builder"])
            self.assertEqual(attempt,updated["work_items"][0]["dispatch_binding"]["attempt_id"])
            self.assertIn("product_goal_worker_result.py",order["command"][1])
            context=order["execution_context"]
            self.assertEqual("kgnote.product-goal-worker-context.v2",context["schema_version"])
            self.assertEqual("MAC_RUNNER_DURABLE_STATE",context["runner_context"]["source"])
            self.assertFalse(context["runner_context"]["repository_plan_status_authoritative"])
            self.assertEqual(self.state["authority_record"],context["runner_context"]["authority_record"])
            self.assertEqual(self.state["event_cursor"],context["runner_context"]["event_cursor"])
            self.assertEqual("PLANNED",context["runner_context"]["work_item"]["status"])
            lane_command=json.loads(order["command"][-1])
            nested=json.loads(lane_command[-1])
            prompt=nested[-1]
            self.assertIn("Runner-verified execution authority",prompt)
            self.assertIn("MUST NOT be used",prompt)
            self.assertEqual(
                "/home/kgnote/.local/share/kgnote/runtime-state/product-goal",
                order["handoff_directory"],
            )
            replay=self.ensure_bound_order(
                self.spec,updated,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            self.assertEqual(path,replay[1]); self.assertEqual(order["event_id"],replay[2]["event_id"])

    def test_resume_authority_is_preserved_in_runtime_context(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state=deepcopy(self.state)
            state["authority_record"]["action"]="RESUME"
            state_path=self.write_state(repo,state)
            _,_,order,_=self.ensure_bound_order(
                self.spec,state,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            self.assertEqual("RESUME",order["bootstrap_identity"]["authority_action"])
            self.assertEqual("RESUME",order["execution_context"]["runner_context"]["authority_record"]["action"])

    def test_detached_first_seed_binding_is_remote_verified_ledgered_and_restart_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/"source"; origin=root/"origin.git"; central=root/"central"; deploy=root/"deploy"
            source.mkdir()
            subprocess.run(["git","init","-b","codex/o2-reading-experience"],cwd=source,check=True,capture_output=True)
            subprocess.run(["git","config","user.email","test@example.invalid"],cwd=source,check=True)
            subprocess.run(["git","config","user.name","Test"],cwd=source,check=True)
            (source/"seed.txt").write_text("seed\n")
            subprocess.run(["git","add","seed.txt"],cwd=source,check=True)
            subprocess.run(["git","commit","-m","seed"],cwd=source,check=True,capture_output=True)
            seed=subprocess.check_output(["git","rev-parse","HEAD"],cwd=source,text=True).strip()
            subprocess.run(["git","clone","--bare",str(source),str(origin)],check=True,capture_output=True)
            subprocess.run(["git","clone",str(origin),str(central)],check=True,capture_output=True)
            subprocess.run(["git","config","user.email","test@example.invalid"],cwd=central,check=True)
            subprocess.run(["git","config","user.name","Test"],cwd=central,check=True)
            (central/"hotfix.txt").write_text("runner hotfix\n")
            subprocess.run(["git","add","hotfix.txt"],cwd=central,check=True)
            subprocess.run(["git","commit","-m","runner hotfix"],cwd=central,check=True,capture_output=True)
            hotfix=subprocess.check_output(["git","rev-parse","HEAD"],cwd=central,text=True).strip()
            subprocess.run(["git","worktree","add","--detach",str(deploy),hotfix],cwd=central,check=True,capture_output=True)
            state=deepcopy(self.state); state.pop("candidate_identity")
            runtime=root/"runtime"; runtime.mkdir(); state_path=runtime/"state.json"; ledger_path=runtime/"ledger.jsonl"
            authority_event,_=GOAL.append_ledger_event(
                ledger_path,event_id="goal-authority-test",event_type="GOAL_AUTHORITY_VERIFIED",
                occurred_at=NOW,goal_id=self.spec["goal_id"],goal_version=self.spec["goal_version"],
                logical_work_id=None,attempt_id=None,payload={"accepted":True,"action":"APPROVE"},
            )
            state["event_cursor"]={
                "sequence":authority_event["sequence"],
                "event_sha256":authority_event["event_sha256"],
            }
            GOAL.atomic_write_json(state_path,state)
            with patch.object(ADAPTER.product_goal_worker_identity,"PRODUCT_REPOSITORY_URL",str(origin)), patch.object(ADAPTER.product_goal_worker_identity,"PRODUCT_SEED_COMMIT",seed):
                updated,path,order,attempt=self.ensure_bound_order(
                    self.spec,state,self.action,repo=deploy,state_path=state_path,
                    ledger_path=ledger_path,occurred_at=NOW,
                )
                self.assertEqual(seed,updated["candidate_identity"]["commit"])
                self.assertNotEqual(hotfix,updated["candidate_identity"]["commit"])
                self.assertIsNone(updated["candidate_identity"]["pull_request"])
                self.assertEqual(seed,order["bootstrap_identity"]["candidate_commit"])
                branch_clone=root/"branch-clone"
                subprocess.run(
                    ["git","clone","--branch","codex/o2-reading-experience","--single-branch",str(origin),str(branch_clone)],
                    check=True,capture_output=True,
                )
                self.assertEqual(
                    CODEX.repository_fingerprint(branch_clone)["value"],
                    updated["candidate_identity"]["fingerprint"],
                )
                events=GOAL.read_ledger(ledger_path)
                self.assertEqual(2,len(events))
                self.assertEqual("INITIAL_CANDIDATE_AND_ORDER_BOUND",events[1]["payload"]["operation"])
                restarted=ADAPTER.synchronize_state_from_ledger(self.spec,state,events)
                self.assertEqual(updated["candidate_identity"],restarted["candidate_identity"])
                replay=self.ensure_bound_order(
                    self.spec,updated,self.action,repo=deploy,state_path=state_path,
                    ledger_path=ledger_path,occurred_at=NOW,
                )
                self.assertEqual(path,replay[1]); self.assertEqual(attempt,replay[3])
                self.assertEqual(2,len(GOAL.read_ledger(ledger_path)))

                subprocess.run(["git","config","user.email","test@example.invalid"],cwd=source,check=True)
                (source/"later.txt").write_text("later\n")
                subprocess.run(["git","add","later.txt"],cwd=source,check=True)
                subprocess.run(["git","commit","-m","later"],cwd=source,check=True,capture_output=True)
                subprocess.run(["git","push",str(origin),"HEAD:refs/heads/codex/o2-reading-experience"],cwd=source,check=True,capture_output=True)
                deploy2=root/"deploy2"
                subprocess.run(["git","worktree","add","--detach",str(deploy2),hotfix],cwd=central,check=True,capture_output=True)
                fresh=deepcopy(state); GOAL.atomic_write_json(state_path,fresh)
                ledger_path.unlink()
                with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"no longer points"):
                    self.ensure_bound_order(
                        self.spec,fresh,self.action,repo=deploy2,state_path=state_path,
                        ledger_path=ledger_path,occurred_at=NOW,
                    )
                self.assertFalse(ledger_path.exists())

    def test_tampered_order_stale_binding_stop_marker_and_exhausted_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            updated,path,_,_=self.ensure_bound_order(
                self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            path.write_text("{}")
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"digest"):
                ADAPTER.validated_bound_order(self.spec,updated,self.action,repo=repo)
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); (repo/".ai").mkdir(); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop")
            state_path=self.write_state(repo)
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"Stop Marker"):
                self.ensure_bound_order(self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW)
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            exhausted={**self.action,"total_launches_before":8}
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"ceiling"):
                self.ensure_bound_order(self.spec,self.state,exhausted,repo=repo,state_path=state_path,occurred_at=NOW)

    def test_dependency_stage_and_output_path_escape_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state=deepcopy(self.state)
            state["work_items"][0]["status"]="VERIFIED"
            verify=next(row for row in state["work_items"] if row["work_item_id"]=="WI-O2-A-VERIFY")
            verify["status"]="READY"
            state_path=self.write_state(repo,state)
            wrong={"status":"ACTION_READY","action":"DISPATCH_REVIEW","work_item_id":"WI-O2-A-VERIFY","requires_model":True,"provider":"claude","total_launches_before":0}
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"stale"):
                self.ensure_bound_order(self.spec,state,wrong,repo=repo,state_path=state_path,occurred_at=NOW)
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            repo=Path(directory); (repo/"output").symlink_to(Path(outside),target_is_directory=True)
            state_path=self.write_state(repo)
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"escapes"):
                self.ensure_bound_order(self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW)

    def test_a_review_repair_and_b_lanes_are_built_without_prefilled_orders(self):
        cases = [
            ("WI-O2-A-VERIFY","RUN_DETERMINISTIC_VERIFICATION",False,None,"publisher"),
            ("WI-O2-A-PUBLISH","RETRY_PUBLICATION",False,None,"push"),
            ("WI-O2-A-REVIEW","DISPATCH_REVIEW",True,"claude","claude"),
            ("WI-O2-A-REPAIR","DISPATCH_REPAIR",True,"codex","codex"),
            ("WI-O2-B-IMPLEMENT","DISPATCH_IMPLEMENTATION",True,"codex","codex"),
            ("WI-O2-B-VERIFY","RUN_DETERMINISTIC_VERIFICATION",False,None,"publisher"),
            ("WI-O2-B-PUBLISH","RETRY_PUBLICATION",False,None,"push"),
            ("WI-O2-B-REVIEW","DISPATCH_REVIEW",True,"claude","claude"),
            ("WI-O2-B-REPAIR","DISPATCH_REPAIR",True,"codex","codex"),
        ]
        for work_item,action_name,requires_model,provider,stage in cases:
            with self.subTest(work_item=work_item), tempfile.TemporaryDirectory() as directory:
                repo=Path(directory); state=deepcopy(self.state)
                target=next(row for row in state["work_items"] if row["work_item_id"]==work_item)
                for dependency in target["dependencies"]:
                    next(row for row in state["work_items"] if row["work_item_id"]==dependency)["status"]="VERIFIED"
                target["status"]="READY"
                state_path=self.write_state(repo,state)
                action={"status":"ACTION_READY","action":action_name,"work_item_id":work_item,"requires_model":requires_model}
                if provider is not None:
                    action.update({"provider":provider,"total_launches_before":0})
                built=self.ensure_bound_order(
                    self.spec,state,action,repo=repo,state_path=state_path,occurred_at=NOW,
                )
                self.assertEqual(stage,built[2]["stage"])
                self.assertEqual(work_item,built[2]["bootstrap_identity"]["work_item_id"])

    def test_first_publication_is_bound_to_one_mac_created_draft_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state=deepcopy(self.state)
            state["event_cursor"]={"sequence":0,"event_sha256":None}
            state["candidate_identity"]["pull_request"]=None
            publish=next(row for row in state["work_items"] if row["work_item_id"]=="WI-O2-A-PUBLISH")
            publish["status"]="VERIFIED"
            state_path=self.write_state(repo,state); ledger_path=repo/"ledger.jsonl"
            calls=[]

            def fake(command,**kwargs):
                calls.append(command)
                if command[1:3] == ["pr","list"]:
                    return subprocess.CompletedProcess(command,0,"[]","")
                if command[1:3] == ["pr","create"]:
                    return subprocess.CompletedProcess(command,0,"https://example.invalid/pr/44\n","")
                observed={
                    "number":44,"headRefOid":"1"*40,
                    "headRefName":"codex/o2-reading-experience",
                    "state":"OPEN","isDraft":True,"url":"https://example.invalid/pr/44",
                }
                return subprocess.CompletedProcess(command,0,json.dumps(observed),"")

            updated=RUNNER.ensure_product_goal_pull_request(
                repo,self.spec,state,state_path=state_path,ledger_path=ledger_path,
                occurred_at=NOW,command_runner=fake,
            )
            self.assertEqual(44,updated["candidate_identity"]["pull_request"])
            self.assertEqual(["list","create","view"],[row[2] for row in calls])
            events=GOAL.read_ledger(ledger_path)
            self.assertEqual("CANDIDATE_PULL_REQUEST_BOUND",events[-1]["payload"]["operation"])


if __name__ == "__main__": unittest.main()
