from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import github_product_goal_control as CONTROL
import goal_continuity as GOAL
import goal_runner_adapter as ADAPTER
import linux_worker_router as ROUTER
import product_goal_runtime_admission as RUNTIME_ADMISSION
from product_goal_worker_result import adapt_worker_result
from tests.control_plane.test_github_product_goal_control import comment
from tests.control_plane.runtime_admission_fixtures import (
    activation_dependency_receipts,
    product_goal_spec,
    runtime_identity,
    write_reservation_receipt,
)


NOW=datetime(2026,11,2,10,0,tzinfo=ZoneInfo("Asia/Taipei"))


class Process:
    def __init__(self,stdout): self.stdout=stdout; self.returncode=0
    def communicate(self,timeout=None): return self.stdout,""
    def terminate(self): pass
    def kill(self): pass


class ProductGoalRuntimeWiringTest(unittest.TestCase):
    def setup_goal(self,repo:Path):
        spec=product_goal_spec()
        authority_comment=comment(spec,login="joannalee20050914")
        authority_comment["html_url"]="https://github.com/joannalee20050914/KGnote-public/issues/9#issuecomment-100"
        authority_comment["issue_url"]="https://api.github.com/repos/joannalee20050914/KGnote-public/issues/9"
        authority=CONTROL.resolve_authority([authority_comment],spec)
        state=GOAL.initial_runner_state(
            spec,now=NOW.isoformat(),
            dependency_receipts=activation_dependency_receipts(spec),
        )
        state.update({
            "authority_record":authority["record"],"authority_lease":"ACTIVE","go_live_authorized":True,
            "lifecycle":{"state":"ACTIVE","revision":1,"changed_at":NOW.isoformat(),"reason":"isolated authority"},
            "candidate_identity":{"commit":"1"*40,"fingerprint":"2"*64,"branch":"codex/o2-reading-experience","pull_request":33},
        })
        state_path=repo/"state.json"; ledger_path=repo/"ledger.jsonl"; GOAL.atomic_write_json(state_path,state)
        record=authority["record"]
        authority_event,_=GOAL.append_ledger_event(
            ledger_path,event_id="goal-authority-isolated",event_type="GOAL_AUTHORITY_VERIFIED",
            occurred_at=authority["record"]["created_at"],goal_id=spec["goal_id"],goal_version=spec["goal_version"],
            logical_work_id=None,attempt_id=None,payload={
                "accepted":True,"action":"APPROVE","go_live_authorized":True,
                "authority_comment_id":record["comment_id"],"authority_body_sha256":record["body_sha256"],
                "goal_spec_sha256":GOAL.goal_spec_sha256(spec),
                "activation_observed_at":"2026-10-29T14:00:00+08:00",
            },
        )
        state["event_cursor"]={
            "sequence":authority_event["sequence"],
            "event_sha256":authority_event["event_sha256"],
        }
        GOAL.atomic_write_json(state_path,state)
        return spec,state,authority,state_path,ledger_path

    def test_pre_reservation_receipt_failures_preserve_formal_state_and_ledger(self):
        for failure in (
            "missing", "stale", "identity", "order_hash", "formal_authority",
            "checkpoint_missing", "checkpoint_hash", "bootstrap_evidence",
            "worker_evidence",
        ):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                repo=Path(directory)
                spec,state,authority,state_path,ledger_path=self.setup_goal(repo)
                action=ADAPTER.next_action(
                    spec,state,GOAL.read_ledger(ledger_path),authority,
                    now=NOW,trial=False,
                )
                bound,order_path,_,_=ADAPTER.ensure_bound_order(
                    spec,state,action,repo=repo,state_path=state_path,
                    occurred_at=NOW.isoformat(),runtime_identity=runtime_identity(),
                    persist_binding=False,
                )
                receipt_path=write_reservation_receipt(
                    repo,order_path,observed_at=NOW,
                )
                if failure == "missing":
                    receipt_path.unlink()
                elif failure == "stale":
                    receipt=json.loads(receipt_path.read_text())
                    receipt["issued_at"]="2026-10-28T09:00:00+08:00"
                    receipt["expires_at"]="2026-10-28T09:02:00+08:00"
                    receipt_path.write_text(json.dumps(receipt))
                elif failure == "identity":
                    receipt=json.loads(receipt_path.read_text())
                    receipt["work_item_id"]="WI-O2-WRONG"
                    receipt_path.write_text(json.dumps(receipt))
                elif failure == "order_hash":
                    order=json.loads(order_path.read_text())
                    order["memory_max"]="3G"
                    order_path.write_text(json.dumps(order))
                elif failure == "formal_authority":
                    order=json.loads(order_path.read_text())
                    order["execution_context"]["runner_context"][
                        "state_projection_sha256"
                    ]="0"*64
                    order_path.write_text(json.dumps(order))
                    receipt=json.loads(receipt_path.read_text())
                    receipt["work_order_sha256"]=hashlib.sha256(
                        order_path.read_bytes()
                    ).hexdigest()
                    receipt["authority"]["state_projection_sha256"]="0"*64
                    receipt_path.write_text(json.dumps(receipt))
                else:
                    receipt=json.loads(receipt_path.read_text())
                    checkpoint_path=Path(receipt["router_checkpoint_path"])
                    if failure == "checkpoint_missing":
                        checkpoint_path.unlink()
                    elif failure == "checkpoint_hash":
                        checkpoint_path.write_text(
                            checkpoint_path.read_text()+"\n",
                        )
                    elif failure == "bootstrap_evidence":
                        checkpoint=json.loads(checkpoint_path.read_text())
                        checkpoint["bootstrap_receipt_sha256"]="7"*64
                        checkpoint_path.write_text(json.dumps(checkpoint))
                        receipt["router_checkpoint_sha256"]=hashlib.sha256(
                            checkpoint_path.read_bytes()
                        ).hexdigest()
                        receipt_path.write_text(json.dumps(receipt))
                    else:
                        checkpoint=json.loads(checkpoint_path.read_text())
                        checkpoint["execution_evidence"]["challenge"]="6"*64
                        checkpoint_path.write_text(json.dumps(checkpoint))
                        receipt["router_checkpoint_sha256"]=hashlib.sha256(
                            checkpoint_path.read_bytes()
                        ).hexdigest()
                        receipt["worker_receipt_sha256"]=hashlib.sha256(
                            RUNTIME_ADMISSION.canonical_json_bytes(
                                checkpoint["execution_evidence"]
                            )
                        ).hexdigest()
                        receipt_path.write_text(json.dumps(receipt))
                before_state=hashlib.sha256(state_path.read_bytes()).hexdigest()
                before_ledger=hashlib.sha256(ledger_path.read_bytes()).hexdigest()
                with self.assertRaises(ADAPTER.GoalRunnerError):
                    ADAPTER.reserve_dispatch(
                        spec,bound,action,state_path=state_path,
                        ledger_path=ledger_path,repo=repo,
                        occurred_at=NOW.isoformat(),prepared_order_path=order_path,
                        admission_receipt_path=receipt_path,
                    )
                self.assertEqual(
                    before_state,hashlib.sha256(state_path.read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    before_ledger,hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                )
                projection=GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
                self.assertEqual({},projection["dispatch_reservations"])
                self.assertEqual({},projection["model_attempts"])
                durable=GOAL.load_json(state_path)
                self.assertEqual(0,durable["work_items"][0]["attempts"])
                self.assertEqual(
                    0,durable.get("resource_accounting",{}).get(
                        "codex",{},
                    ).get("total_launches",0),
                )

    def test_dynamic_order_to_real_router_checkpoint_result_state_and_next_work(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            spec,state,authority,state_path,ledger_path=self.setup_goal(repo)
            decision=ADAPTER.next_action(spec,state,GOAL.read_ledger(ledger_path),authority,now=NOW,trial=False)
            self.assertEqual("DISPATCH_IMPLEMENTATION",decision["action"])
            state,order_path,order,attempt=ADAPTER.ensure_bound_order(
                spec,state,decision,repo=repo,state_path=state_path,occurred_at=NOW.isoformat(),
                runtime_identity=runtime_identity(),
                persist_binding=False,
            )
            receipt_path=write_reservation_receipt(repo,order_path,observed_at=NOW)
            reserved,_,attempt=ADAPTER.reserve_dispatch(
                spec,state,decision,state_path=state_path,ledger_path=ledger_path,
                repo=repo,occurred_at=NOW.isoformat(),prepared_order_path=order_path,
                admission_receipt_path=receipt_path,
            )
            context=order["execution_context"]
            artifact={
                "schema_version":"kgnote.codex-product-goal-result.v1","status":"COMPLETED",
                "candidate_parent":"1"*40,"candidate_commit":"3"*40,
                "candidate_fingerprint":"4"*64,"branch":"codex/o2-reading-experience",
                "pull_request":33,"verification":{"status":"PASS"},
                "usage":{"input_tokens":11,"output_tokens":7},
            }
            product_result=adapt_worker_result(context,artifact,returncode=0,stdout=b"real structured evidence")
            execution={"schema_version":"kgnote.model-execution-evidence.v1","product_goal_result":product_result}
            marker=ROUTER.EVIDENCE_PREFIX+json.dumps(execution,separators=(",",":"))
            def guest_run(command,**kwargs):
                if "linux_worker_bootstrap.py" in command[-1]:
                    return subprocess.CompletedProcess(command,0,json.dumps({
                        "status":"READY",
                        "development_environment":{"status":"DEVELOPMENT_ENVIRONMENT_READY"},
                    }),"")
                return subprocess.CompletedProcess(command,0,"active","")

            routed=ROUTER.route(
                ROUTER.WorkerOrder.from_dict(order),
                run=guest_run,
                popen=lambda *args,**kwargs: Process(marker), now=lambda:NOW,
            )
            self.assertEqual("COMPLETED",routed["status"])
            dispatched=ADAPTER.record_route_outcome(
                spec,reserved,state_path=state_path,work_item_id=decision["work_item_id"],
                attempt_id=attempt,route_exit_code=0,occurred_at=NOW.isoformat(),
            )
            reconciled=ADAPTER.reconcile_dispatch_checkpoint(
                spec,dispatched,state_path=state_path,ledger_path=ledger_path,
                repo=repo,attempt_id=attempt,occurred_at=NOW.isoformat(),
            )
            self.assertEqual("WORK_COMPLETED",reconciled["outcome"])
            durable=GOAL.load_json(state_path)
            self.assertEqual("VERIFIED",durable["work_items"][0]["status"])
            self.assertEqual("3"*40,durable["candidate_identity"]["commit"])
            ledger=GOAL.read_ledger(ledger_path)
            projection=GOAL.reduce_ledger(ledger)
            self.assertTrue(projection["dispatch_reservations"][attempt]["reconciled"])
            self.assertEqual("OBSERVED",projection["usage"][attempt]["status"])
            next_decision=ADAPTER.next_action(spec,durable,ledger,authority,now=NOW,trial=False)
            self.assertEqual("WI-O2-A-VERIFY",next_decision["work_item_id"])
            successor=ADAPTER.ensure_bound_order(
                spec,durable,next_decision,repo=repo,state_path=state_path,occurred_at=NOW.isoformat(),
            )
            self.assertEqual("publisher",successor[2]["stage"])
            self.assertNotEqual(order["event_id"],successor[2]["event_id"])

    def test_o2_trial_schedule_boundaries_gate_planning_from_runner_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            spec,state,authority,_state_path,ledger_path=self.setup_goal(repo)
            ledger=GOAL.read_ledger(ledger_path)
            cases=(
                (datetime(2026,10,29,16,59,59,tzinfo=ZoneInfo("Asia/Taipei")),"WAIT_TRIAL_START"),
                (datetime(2026,10,29,17,0,tzinfo=ZoneInfo("Asia/Taipei")),"ACTION_READY"),
                (datetime(2026,11,11,17,59,59,tzinfo=ZoneInfo("Asia/Taipei")),"ACTION_READY"),
                (datetime(2026,11,11,18,0,tzinfo=ZoneInfo("Asia/Taipei")),"GOAL_HARD_STOP"),
                (datetime(2026,11,12,10,0,tzinfo=ZoneInfo("Asia/Taipei")),"GOAL_HARD_STOP"),
            )
            for observed,expected in cases:
                with self.subTest(observed=observed.isoformat()):
                    decision=ADAPTER.next_action(
                        spec,state,ledger,authority,now=observed,trial=False,
                    )
                    self.assertEqual(expected,decision["status"])

            restarted=json.loads(json.dumps(state))
            reset_window=datetime(2026,11,16,9,0,tzinfo=ZoneInfo("Asia/Taipei"))
            self.assertEqual(
                "GOAL_HARD_STOP",
                ADAPTER.next_action(
                    spec,restarted,ledger,authority,now=reset_window,trial=False,
                )["status"],
            )

    def test_o2_dynamic_order_and_reservation_recheck_schedule_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            spec,state,authority,state_path,ledger_path=self.setup_goal(repo)
            start=datetime(2026,10,29,17,0,tzinfo=ZoneInfo("Asia/Taipei"))
            before=datetime(2026,10,29,16,59,59,tzinfo=ZoneInfo("Asia/Taipei"))
            hard_stop=datetime(2026,11,11,18,0,tzinfo=ZoneInfo("Asia/Taipei"))
            action=ADAPTER.next_action(
                spec,state,GOAL.read_ledger(ledger_path),authority,
                now=start,trial=False,
            )
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"WAIT_TRIAL_START"):
                ADAPTER.ensure_bound_order(
                    spec,state,action,repo=repo,state_path=state_path,
                    occurred_at=before.isoformat(),
                    runtime_identity=runtime_identity(),
                )
            bound,order_path,_,_=ADAPTER.ensure_bound_order(
                spec,state,action,repo=repo,state_path=state_path,
                occurred_at=start.isoformat(),
                runtime_identity=runtime_identity(),
                persist_binding=False,
            )
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError,"GOAL_HARD_STOP"):
                ADAPTER.reserve_dispatch(
                    spec,bound,action,state_path=state_path,ledger_path=ledger_path,
                    repo=repo,occurred_at=hard_stop.isoformat(),
                )

    def test_o2_hard_stop_allows_existing_dispatch_evidence_reconciliation_only(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            spec,state,authority,state_path,ledger_path=self.setup_goal(repo)
            before_stop=datetime(2026,11,11,17,59,tzinfo=ZoneInfo("Asia/Taipei"))
            hard_stop=datetime(2026,11,11,18,0,tzinfo=ZoneInfo("Asia/Taipei"))
            action=ADAPTER.next_action(
                spec,state,GOAL.read_ledger(ledger_path),authority,
                now=before_stop,trial=False,
            )
            bound,order_path,_,attempt=ADAPTER.ensure_bound_order(
                spec,state,action,repo=repo,state_path=state_path,
                occurred_at=before_stop.isoformat(),
                runtime_identity=runtime_identity(),
                persist_binding=False,
            )
            receipt_path=write_reservation_receipt(
                repo,order_path,observed_at=before_stop,
            )
            reserved,_,reserved_attempt=ADAPTER.reserve_dispatch(
                spec,bound,action,state_path=state_path,ledger_path=ledger_path,
                repo=repo,occurred_at=before_stop.isoformat(),
                prepared_order_path=order_path,admission_receipt_path=receipt_path,
            )
            self.assertEqual(attempt,reserved_attempt)
            decision=ADAPTER.next_action(
                spec,reserved,GOAL.read_ledger(ledger_path),authority,
                now=hard_stop,trial=False,
            )
            self.assertEqual("RECOVERY_READY",decision["status"])
            self.assertEqual("RECONCILE_CHECKPOINT",decision["action"])
            self.assertEqual(attempt,decision["attempt_id"])


if __name__=="__main__": unittest.main()
