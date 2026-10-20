import importlib.util, json, signal, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("entry",ROOT/"scripts/successor_codex_entrypoint.py")
ENTRY=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ENTRY)

class Process:
    def __init__(self,*a,returncode=0,stdout="",stderr="",**k):
        self.terminated=False; self.returncode=returncode; self.stdout=stdout; self.stderr=stderr
    def communicate(self): return self.stdout,self.stderr
    def terminate(self): self.terminated=True

class SuccessorEntrypointTest(unittest.TestCase):
    def test_existing_exact_worktree_runs_codex_and_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/".git").mkdir(); process=Process()
            with patch.object(ENTRY.subprocess,"check_output",side_effect=["codex/successor\n","a"*40+"\n","codex-cli 0.146.0\n","b"*40+"\n"]), patch.object(ENTRY.subprocess,"Popen",return_value=process) as popen:
                self.assertEqual(0,ENTRY.run("owner/repo","codex/successor","a"*40,"prompt",root,goal_id="goal",pull_request=26,cycle=7))
            checkpoint=json.loads((root/".git/kgnote-successor-worker-checkpoint.json").read_text())
            self.assertEqual("COMPLETED",checkpoint["status"])
            self.assertEqual("gpt-5.6-terra",checkpoint["execution_evidence"]["requested_model"])
            self.assertEqual("medium",checkpoint["execution_evidence"]["requested_effort"])
            self.assertEqual("EFFECTIVE_UNKNOWN",checkpoint["execution_evidence"]["effective_status"])
            self.assertIn("--ephemeral",popen.call_args.args[0])
            self.assertEqual(ENTRY.NODE,popen.call_args.args[0][0])
            self.assertEqual(ENTRY.CODEX_JS,popen.call_args.args[0][1])
            self.assertEqual("gpt-5.6-terra",popen.call_args.args[0][popen.call_args.args[0].index("--model")+1])
            self.assertIn('model_reasoning_effort="medium"',popen.call_args.args[0])
            self.assertIn("--strict-config",popen.call_args.args[0])

    def test_usage_limit_is_checkpointed_as_quota_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/".git").mkdir()
            process=Process(returncode=1,stderr="usage limit reached")
            with patch.object(ENTRY.subprocess,"check_output",side_effect=["codex/successor\n","a"*40+"\n","codex-cli 0.146.0\n","a"*40+"\n"]), patch.object(ENTRY.subprocess,"Popen",return_value=process):
                self.assertEqual(1,ENTRY.run("owner/repo","codex/successor","a"*40,"prompt",root))
            checkpoint=json.loads((root/".git/kgnote-successor-worker-checkpoint.json").read_text())
            self.assertEqual("FAILED_CLOSED",checkpoint["status"])
            self.assertEqual("quota_exhausted",checkpoint["reason"])

    def test_first_run_rejects_wrong_inherited_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/".git").mkdir()
            with patch.object(ENTRY.subprocess,"check_output",side_effect=["codex/successor\n","b"*40+"\n"]):
                with self.assertRaisesRegex(RuntimeError,"inherited HEAD mismatch"):
                    ENTRY.run("owner/repo","codex/successor","a"*40,"prompt",root)

if __name__=="__main__": unittest.main()
