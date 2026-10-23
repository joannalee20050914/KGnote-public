import copy, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"scripts"))
from epoch_scope_admission import AdmissionError, validate, validate_product_goal

class EpochAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.epoch=json.loads((ROOT/".ai/CLAUDE_REVIEWER_CUTOVER_EPOCH.json").read_text())
        self.order={"review_admission":{"repository":"joannalee20050914/KGnote-public","pull_request":24,"head_sha":"a"*40,"candidate_fingerprint":"b"*64,"review_round":1,"authority":{"status":"APPROVED","goal_id":"goal-new","authority_record":"docs/control-plane/new.md"},"budget":{"authorized":2,"used":0},"work_window_allowed":True,"stop_marker_clear":True,"existing_exact_candidate_result":False}}
        self.pr={"number":24,"created_at":"2026-10-18T14:36:02Z","head":{"sha":"a"*40}}
    def test_post_epoch_authorized_pr_is_admitted(self): self.assertEqual("ADMITTED",validate(self.epoch,self.order,self.pr)["status"])
    def test_epoch_new_implementation_uses_separate_single_dispatch_budget(self):
        order=copy.deepcopy(self.order); admission=order["review_admission"]
        admission.pop("review_round"); admission.pop("budget")
        admission.update({"admission_kind":"IMPLEMENTATION","implementation_budget":{"authorized":1,"used":0}})
        self.assertEqual("IMPLEMENTATION",validate(self.epoch,order,self.pr)["admission_kind"])
        admission["implementation_budget"]["used"]=1
        with self.assertRaisesRegex(AdmissionError,"implementation budget"):
            validate(self.epoch,order,self.pr)
    def test_pr23_and_all_legacy_prs_are_permanently_rejected(self):
        for number in (1,22,23):
            order=copy.deepcopy(self.order); order["review_admission"]["pull_request"]=number
            with self.assertRaisesRegex(AdmissionError,"legacy PR"): validate(self.epoch,order,{"number":number,"created_at":"2026-10-19T00:00:00Z","head":{"sha":"a"*40}})
    def test_old_pr_remains_rejected_after_head_or_comment_time_changes(self):
        order=copy.deepcopy(self.order); order["review_admission"]["pull_request"]=25
        with self.assertRaisesRegex(AdmissionError,"predates"): validate(self.epoch,order,{"number":25,"created_at":"2026-10-18T03:00:00Z","updated_at":"2026-10-19T00:00:00Z","head":{"sha":"a"*40}})
    def test_missing_or_forged_created_at_fails_closed(self):
        for value in (None,"2026-10-18 14:36:02","not-a-time"):
            pr=copy.deepcopy(self.pr); pr["created_at"]=value
            with self.assertRaises(AdmissionError): validate(self.epoch,self.order,pr)
    def test_authority_budget_stop_result_and_identity_gates(self):
        mutations=[("authority",{}),("budget",{"authorized":1,"used":1}),("work_window_allowed",False),("stop_marker_clear",False),("existing_exact_candidate_result",True),("head_sha","c"*40)]
        for key,value in mutations:
            order=copy.deepcopy(self.order); order["review_admission"][key]=value
            with self.assertRaises(AdmissionError): validate(self.epoch,order,self.pr)
    def test_product_goal_admission_is_exact_and_budget_bound(self):
        identity={"goal_id":"GOAL-KGNOTE-O2-READING-EXPERIENCE","goal_version":"v1","goal_spec_sha256":"d"*64,"work_item_id":"WI-O2-A-IMPLEMENT","provider":"codex","stage":"codex","order_event_id":"o2-event"}
        order={"event_id":"o2-event","stage":"codex","bootstrap_identity":identity,"product_goal_admission":{
            **identity,"repository":"joannalee20050914/KGnote-public","order_event_id":"o2-event",
            "candidate":{"commit":"a"*40,"fingerprint":"b"*64},"authority_status":"APPROVED",
            "go_live_authorized":True,"stop_marker_clear":True,"requires_model":True,
            "total_launches_before":0,"max_total_launches":8,
        }}
        self.assertEqual("PRODUCT_GOAL",validate_product_goal(self.epoch,order)["admission_kind"])
        for key,value in (("goal_spec_sha256","0"*64),("stop_marker_clear",False),("total_launches_before",8)):
            changed=copy.deepcopy(order); changed["product_goal_admission"][key]=value
            with self.assertRaises(AdmissionError): validate_product_goal(self.epoch,changed)

if __name__ == "__main__": unittest.main()
