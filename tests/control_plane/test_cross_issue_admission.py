from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
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

    def test_only_public_safe_home_placeholder_is_expanded(self):
        with patch.dict(os.environ,{"HOME":"/opt/test-home"}):
            self.assertEqual(Path("/opt/test-home/KGnote-public-issue14-tutor-handoff"),MODULE._authorized_local_worktree("${HOME}/KGnote-public-issue14-tutor-handoff"))
        with self.assertRaises(MODULE.AdmissionError):
            MODULE._authorized_local_worktree("/opt/test-home/KGnote-public-issue14-tutor-handoff")

    def test_worker_identity_carries_the_versioned_generic_contract(self):
        admission=self.item()["admission"]
        identity={"schema_version":"kgnote.authorized-work-identity.v1",**{k:admission[k] for k in ("repository","issue","goal_id","work_item_id","branch","worktree_slug","authority_record","authority_sha256")}}
        self.assertEqual("kgnote.authorized-work-identity.v1",identity["schema_version"])


if __name__ == "__main__":
    unittest.main()
