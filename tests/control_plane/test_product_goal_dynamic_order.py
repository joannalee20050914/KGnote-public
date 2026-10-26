from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import github_product_goal_control as CONTROL
import goal_continuity as GOAL
import goal_runner_adapter as ADAPTER
import local_autonomy_runner as RUNNER
from tests.control_plane.test_github_product_goal_control import comment
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
        })
        self.action = {
            "status":"ACTION_READY", "action":"DISPATCH_IMPLEMENTATION",
            "work_item_id":"WI-O2-A-IMPLEMENT", "requires_model":True,
            "provider":"codex", "total_launches_before":0,
        }

    def write_state(self, repo: Path, state=None):
        path=repo/"state.json"; GOAL.atomic_write_json(path,state or self.state); return path

    def test_runner_creates_seals_and_reuses_same_attempt_order(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            updated,path,order,attempt=ADAPTER.ensure_bound_order(
                self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            self.assertEqual("RUNNER_DYNAMIC_V1",updated["work_items"][0]["dispatch_binding"]["builder"])
            self.assertEqual(attempt,updated["work_items"][0]["dispatch_binding"]["attempt_id"])
            self.assertIn("product_goal_worker_result.py",order["command"][1])
            self.assertEqual(
                "/home/kgnote/.local/share/kgnote/runtime-state/product-goal",
                order["handoff_directory"],
            )
            replay=ADAPTER.ensure_bound_order(
                self.spec,updated,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            self.assertEqual(path,replay[1]); self.assertEqual(order["event_id"],replay[2]["event_id"])

    def test_tampered_order_stale_binding_stop_marker_and_exhausted_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            updated,path,_,_=ADAPTER.ensure_bound_order(
                self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW,
            )
            path.write_text("{}")
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"digest"):
                ADAPTER.validated_bound_order(self.spec,updated,self.action,repo=repo)
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); (repo/".ai").mkdir(); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop")
            state_path=self.write_state(repo)
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"Stop Marker"):
                ADAPTER.ensure_bound_order(self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW)
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state_path=self.write_state(repo)
            exhausted={**self.action,"total_launches_before":8}
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"ceiling"):
                ADAPTER.ensure_bound_order(self.spec,self.state,exhausted,repo=repo,state_path=state_path,occurred_at=NOW)

    def test_dependency_stage_and_output_path_escape_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state=deepcopy(self.state)
            state["work_items"][0]["status"]="VERIFIED"
            verify=next(row for row in state["work_items"] if row["work_item_id"]=="WI-O2-A-VERIFY")
            verify["status"]="READY"
            state_path=self.write_state(repo,state)
            wrong={"status":"ACTION_READY","action":"DISPATCH_REVIEW","work_item_id":"WI-O2-A-VERIFY","requires_model":True,"provider":"claude","total_launches_before":0}
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"stale"):
                ADAPTER.ensure_bound_order(self.spec,state,wrong,repo=repo,state_path=state_path,occurred_at=NOW)
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            repo=Path(directory); (repo/"output").symlink_to(Path(outside),target_is_directory=True)
            state_path=self.write_state(repo)
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"escapes"):
                ADAPTER.ensure_bound_order(self.spec,self.state,self.action,repo=repo,state_path=state_path,occurred_at=NOW)

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
                built=ADAPTER.ensure_bound_order(
                    self.spec,state,action,repo=repo,state_path=state_path,occurred_at=NOW,
                )
                self.assertEqual(stage,built[2]["stage"])
                self.assertEqual(work_item,built[2]["bootstrap_identity"]["work_item_id"])

    def test_first_publication_is_bound_to_one_mac_created_draft_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); state=deepcopy(self.state)
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
