from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import goal_continuity as GOAL
import reconcile_o2_attempt_classification as RECONCILE


class O2ClassificationReconciliationTest(unittest.TestCase):
    def test_two_corrections_are_append_only_idempotent_and_preserve_launches(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            spec=json.loads((ROOT/"docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json").read_text())
            spec_path=root/"spec.json"; GOAL.atomic_write_json(spec_path,spec)
            state=GOAL.initial_runner_state(spec,now="2026-10-28T02:19:15Z")
            state.update({
                "lifecycle":{"state":"BLOCKED","revision":3,"changed_at":"2026-10-28T02:19:15Z","reason":"exact Owner pause applied"},
                "authority_lease":"PAUSED", "go_live_authorized":False,
                "authority_record":{
                    "schema_version":"kgnote.product-goal-authority.v1",
                    "identity_kind":"KGNOTE_PRODUCT_GOAL","authority_kind":"GITHUB_OWNER_APPROVAL",
                    "repository":spec["repository"],"issue":spec["github_issue"],
                    "comment_id":6458880366,"comment_url":"https://github.com/joannalee20050914/KGnote-public/issues/9#issuecomment-6458880366",
                    "author_login":"joannalee20050914","author_association":"OWNER",
                    "created_at":"2026-10-28T02:19:15Z","action":"PAUSE",
                    "goal_id":spec["goal_id"],"goal_version":spec["goal_version"],
                    "goal_spec_sha256":GOAL.goal_spec_sha256(spec),"permissions":[],
                    "expires_at":None,"body_sha256":"9"*64,
                },
                "resource_accounting":{"codex":{"total_launches":2,"launches_in_window":2,"last_launch_at":"2026-10-28T10:02:23+08:00","window_id":"2026-10-28@09:00-18:00","quota_retry_at":"2026-10-28T11:04:30+08:00"}},
                "runtime_block":{"failure_class":"RATE_LIMITED","work_item_id":RECONCILE.WORK_ITEM_ID,"attempt_id":"attempt-2","retry_at":"2026-10-28T11:04:30+08:00"},
            })
            work=next(row for row in state["work_items"] if row["work_item_id"]==RECONCILE.WORK_ITEM_ID)
            work["attempts"]=2; work["active_attempt_id"]=None; work["status"]="PLANNED"
            state_path=root/"state.json"; ledger_path=root/"ledger.jsonl"
            checkpoint_root=root/"checkpoints"; checkpoint_root.mkdir()
            manifests=[]; remote={}
            for number,event in enumerate(("event-first","event-second"),start=1):
                attempt=f"attempt-{number}"
                stdout_hash=hashlib.sha256(f"stdout-{number}".encode()).hexdigest()
                stderr_hash=hashlib.sha256(f"stderr-{number}".encode()).hexdigest()
                checkpoint={
                    "event_id":event,"status":"COMPLETED",
                    "execution_evidence":{"product_goal_result":{
                        "attempt_id":attempt,"failure_class":"RATE_LIMITED",
                        "execution":{"stdout_sha256":stdout_hash,"stderr_sha256":stderr_hash},
                    }},
                }
                checkpoint_path=checkpoint_root/f"{event}.json"; checkpoint_path.write_text(json.dumps(checkpoint,sort_keys=True))
                manifests.append({
                    "attempt_id":attempt,"event_id":event,
                    "checkpoint_sha256":hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
                    "stdout_sha256":stdout_hash,"stderr_sha256":stderr_hash,
                    "cause_codes":["CONTROL_PLANE_TEST_CAUSE"],
                })
                remote[str(RECONCILE.REMOTE_RAW_ROOT/f"{event}.stdout.log")]=stdout_hash
                remote[str(RECONCILE.REMOTE_RAW_ROOT/f"{event}.stderr.log")]=stderr_hash
                ledger_event,_=GOAL.append_ledger_event(
                    ledger_path,event_id=f"{attempt}-finished",event_type="MODEL_ATTEMPT_FINISHED",
                    occurred_at=f"2026-10-28T10:0{number}:00+08:00",goal_id=spec["goal_id"],
                    goal_version=spec["goal_version"],logical_work_id=RECONCILE.WORK_ITEM_ID,
                    attempt_id=attempt,payload={"failure_class":"RATE_LIMITED"},
                )
                state["event_cursor"]={"sequence":ledger_event["sequence"],"event_sha256":ledger_event["event_sha256"]}
            GOAL.atomic_write_json(state_path,state)
            original_ledger=ledger_path.read_bytes()
            review_result={
                "schema_version":"kgnote.review-result.v1",
                "protocol_version":"kgnote.review-protocol.v1",
                "artifact_state":"SUBMITTED",
                "review_id":"review-o2-recovery-test",
                "author_role":"UBUNTU_CLAUDE_REVIEWER",
                "reviewer_identity":"ubuntu-claude-test",
                "reviewed_revision":"b"*40+"+worktree:"+"c"*64,
                "reviewed_fingerprint":"c"*64,
                "verdict":"PASS","findings":[],
                "verified_requirements":["runtime-context-recovery"],
                "unverified_requirements":[],"human_decisions_required":[],
                "human_gates_preserved":sorted(RECONCILE.REQUIRED_HUMAN_GATES),
                "reviewed_at":"2026-10-28T11:50:00+08:00",
            }
            review=root/"review.md"; review.write_text(
                "<!-- BEGIN KGNOTE REVIEW RESULT JSON -->\n```json\n"
                +json.dumps(review_result)+
                "\n```\n<!-- END KGNOTE REVIEW RESULT JSON -->\n"
            )
            receipt=root/"receipt.json"
            state_sha=hashlib.sha256(state_path.read_bytes()).hexdigest()
            ledger_sha=hashlib.sha256(ledger_path.read_bytes()).hexdigest()
            arguments=dict(
                spec_path=spec_path,state_path=state_path,ledger_path=ledger_path,
                checkpoint_root=checkpoint_root,remote_host="test-ubuntu",
                reviewed_deployment_commit="a"*40,review_receipt=review,
                receipt_path=receipt,occurred_at="2026-10-28T12:00:00+08:00",
                remote_hash_reader=lambda _host,_paths:dict(remote),
            )
            with patch.object(RECONCILE,"ATTEMPTS",tuple(manifests)), patch.object(RECONCILE,"BASELINE_STATE_SHA256",state_sha), patch.object(RECONCILE,"BASELINE_LEDGER_SHA256",ledger_sha):
                result=RECONCILE.reconcile(**arguments)
                ledger_after=ledger_path.read_bytes()
                replay=RECONCILE.reconcile(**arguments)
            self.assertEqual("PASS",result["status"])
            self.assertEqual(2,result["work_item_attempts"])
            self.assertEqual(2,result["model_launches"])
            self.assertTrue(ledger_after.startswith(original_ledger))
            self.assertEqual(ledger_after,ledger_path.read_bytes())
            self.assertEqual(result["appended_event_ids"],replay["appended_event_ids"])
            durable=GOAL.load_json(state_path)
            self.assertNotIn("runtime_block",durable)
            self.assertNotIn("quota_retry_at",durable["resource_accounting"]["codex"])
            projection=GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertEqual({"attempt-1","attempt-2"},set(projection["classification_corrections"]))

    def test_arbitrary_pass_file_is_not_a_review_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"fake.json"; path.write_text('{"verdict":"PASS"}\n')
            with self.assertRaisesRegex(RECONCILE.ClassificationReconciliationError,"marker"):
                RECONCILE._validated_review_pass(path)


if __name__=="__main__":
    unittest.main()
