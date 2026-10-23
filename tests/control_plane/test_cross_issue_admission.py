from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import json
import importlib.util
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("cross_issue_admission", ROOT / "scripts/cross_issue_admission.py")
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class CrossIssueAdmissionTests(unittest.TestCase):
    def item(self):
        body = "approved body"
        return {
            "status":"ADMISSION_PENDING", "authority":{"status":"APPROVED"},
            "budget":{"authorized":1,"used":0},
            "safety":{"isolated_worktree":True,"automatic_merge":False},
            "admission":{
                "repository":"joannalee20050914/KGnote-public", "issue":14,
                "goal_id":"GOAL-KGNOTE-TUTOR-HANDOFF", "work_item_id":"D2-T07",
                "branch":"codex/issue-14-tutor-handoff-feasibility", "worktree_slug":"issue-14-d2-t07",
                "authority_record":"https://github.com/joannalee20050914/KGnote-public/issues/14",
                "authority_sha256":hashlib.sha256(body.encode()).hexdigest(),
                "source_commit":"a"*40, "local_worktree":"${HOME}/KGnote-public-issue14-tutor-handoff",
            },
        }

    def test_sealed_authority_and_single_dispatch_are_required(self):
        current=datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")); item=self.item()
        self.assertEqual(14,MODULE.validate_item(item,current)["issue"])
        item["budget"]["authorized"]=2
        with self.assertRaisesRegex(MODULE.AdmissionError,"exactly one"):
            MODULE.validate_item(item,current)

    def test_ready_label_alone_does_not_replace_authority_bytes(self):
        item=self.item(); admission=item["admission"]
        def fake(command,**kwargs):
            value='{"number":14,"state":"OPEN","labels":[{"name":"queue:ready"}],"body":"changed","title":"x","url":"https://github.com/joannalee20050914/KGnote-public/issues/14"}'
            return subprocess.CompletedProcess(command,0,value,"")
        with self.assertRaisesRegex(MODULE.AdmissionError,"authority bytes changed"):
            MODULE._live_issue(ROOT,admission,fake)

    def test_only_exact_sealed_legacy_home_identity_is_preserved(self):
        admission=self.item()["admission"]
        with patch.dict(os.environ,{"HOME":"/opt/test-home"}):
            self.assertEqual(Path("/opt/test-home/KGnote-public-issue14-tutor-handoff"),MODULE._authorized_local_worktree(admission))
        changed=dict(admission); changed["issue"]=99
        with self.assertRaisesRegex(MODULE.AdmissionError,"CENTRALIZED_V1"):
            MODULE._authorized_local_worktree(changed)

    def test_new_worktree_is_derived_from_concentrated_policy_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=(Path(directory)/"worktrees"); root.mkdir(); root=root.resolve()
            policy=Path(directory)/"path-policy.json"
            policy.write_text(json.dumps({
                "schema_version":"kgnote.local-path-policy.v1",
                "worktree_root":str(root),
                "require_direct_child":True,
                "reject_root_inside_git_repository":True,
                "reject_symlink_escape":True,
            }))
            admission=self.item()["admission"]
            admission["worktree_layout"]=MODULE.CENTRALIZED_LAYOUT
            admission["local_worktree"]=f"{MODULE.CENTRALIZED_PREFIX}{admission['worktree_slug']}"
            self.assertEqual(root/admission["worktree_slug"],MODULE._authorized_local_worktree(admission,path_policy=policy))
            admission["local_worktree"]="${KGNOTE_WORKTREE_ROOT}/worker-chosen"
            with self.assertRaisesRegex(MODULE.AdmissionError,"derived from"):
                MODULE._authorized_local_worktree(admission,path_policy=policy)

    def test_concentrated_policy_rejects_git_nested_root_and_symlink_target(self):
        with tempfile.TemporaryDirectory() as directory:
            repository=(Path(directory)/"repository"); repository.mkdir(); repository=repository.resolve()
            subprocess.run(["git","init",str(repository)],check=True,capture_output=True)
            nested=repository/"worktrees"; nested.mkdir(); nested=nested.resolve()
            policy=Path(directory)/"nested-policy.json"
            policy.write_text(json.dumps({
                "schema_version":"kgnote.local-path-policy.v1","worktree_root":str(nested),
                "require_direct_child":True,"reject_root_inside_git_repository":True,"reject_symlink_escape":True,
            }))
            admission=self.item()["admission"]; admission["worktree_layout"]=MODULE.CENTRALIZED_LAYOUT
            admission["local_worktree"]=f"{MODULE.CENTRALIZED_PREFIX}{admission['worktree_slug']}"
            with self.assertRaisesRegex(MODULE.AdmissionError,"inside a non-bare"):
                MODULE._authorized_local_worktree(admission,path_policy=policy)

            safe=Path(directory)/"safe"; safe.mkdir(); safe=safe.resolve()
            outside=Path(directory)/"outside"; outside.mkdir(); outside=outside.resolve()
            (safe/admission["worktree_slug"]).symlink_to(outside,target_is_directory=True)
            policy.write_text(json.dumps({
                "schema_version":"kgnote.local-path-policy.v1","worktree_root":str(safe),
                "require_direct_child":True,"reject_root_inside_git_repository":True,"reject_symlink_escape":True,
            }))
            with self.assertRaisesRegex(MODULE.AdmissionError,"must not be a symlink"):
                MODULE._authorized_local_worktree(admission,path_policy=policy)

    def test_worker_identity_carries_the_versioned_generic_contract(self):
        admission=self.item()["admission"]
        identity={"schema_version":"kgnote.authorized-work-identity.v1",**{k:admission[k] for k in ("repository","issue","goal_id","work_item_id","branch","worktree_slug","authority_record","authority_sha256")}}
        self.assertEqual("kgnote.authorized-work-identity.v1",identity["schema_version"])

    def test_prepare_order_round_trips_through_real_router_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); admission=self.item()["admission"]; worktree=repo.parent/"fixture-worktree"
            pr={"number":27,"state":"OPEN","isDraft":True,"headRefName":admission["branch"],"baseRefName":"main","url":"https://example/pr/27"}
            def fake_run(command,**kwargs):
                joined=" ".join(str(v) for v in command)
                if "git/ref/heads" in joined: return json.dumps({"object":{"sha":"c"*40}})
                if "pr list" in joined: return json.dumps([pr])
                if "fingerprint" in joined: return json.dumps({"value":"d"*64})
                return ""
            with patch.object(MODULE,"_live_issue",return_value={"title":"Issue"}), patch.object(MODULE,"_initialize_worktree",return_value=(worktree,"c"*40)), patch.object(MODULE,"_run",side_effect=fake_run):
                receipt=MODULE.prepare(repo,self.item(),datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),runner=lambda *a,**k:None)
            order=json.loads((repo/receipt["order_path"]).read_text())
            integration=ROOT/"scripts"/"linux_worker_router.py"
            self.assertTrue(integration.is_file(),"candidate router contract is required for the cross-worktree test")
            spec=importlib.util.spec_from_file_location("integration_router",integration)
            router=importlib.util.module_from_spec(spec); sys.modules[spec.name]=router; spec.loader.exec_module(router)
            self.assertEqual("issue-14-d2-t07-codex-20261019",router.WorkerOrder.from_dict(order).event_id)
            order.pop("schema_version")
            invalid=repo/"invalid-order.json"; invalid.write_text(json.dumps(order))
            completed=subprocess.run([sys.executable,str(integration),"--order",str(invalid)],capture_output=True,text=True)
            self.assertEqual(2,completed.returncode); self.assertTrue(completed.stderr.strip())


if __name__ == "__main__":
    unittest.main()
