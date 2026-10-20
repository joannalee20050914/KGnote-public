import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from trusted_candidate_publisher import PublishError, PublishRequest, publish


class TrustedCandidatePublisherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-b", "codex/integration", self.repo], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.name", "Fixture"], check=True)
        (self.repo / "src").mkdir()
        (self.repo / "src/value.txt").write_text("base\n")
        subprocess.run(["git", "-C", self.repo, "add", "src/value.txt"], check=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-m", "fixture base"], check=True, capture_output=True)
        self.parent = subprocess.check_output(["git", "-C", self.repo, "rev-parse", "HEAD"], text=True).strip()

    def tearDown(self): self.temp.cleanup()

    def request(self, changed=("src/value.txt",)):
        receipt = Path(self.temp.name) / "receipt.json"
        receipt.write_text(json.dumps({"status": "PASS", "candidate_parent": self.parent, "changed_paths": list(changed)}))
        return PublishRequest.from_dict({
            "worktree": str(self.repo), "branch": "codex/integration", "expected_parent": self.parent,
            "allowed_paths": ["src"], "test_receipt": str(receipt),
            "test_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            "message": "test: trusted candidate",
        })

    def test_commits_exact_allowed_diff_without_push(self):
        (self.repo / "src/value.txt").write_text("changed\n")
        result = publish(self.request())
        self.assertEqual("COMMITTED_LOCAL_ONLY", result["status"])
        self.assertFalse(result["remote_push_authorized"])
        self.assertEqual(["src/value.txt"], result["changed_paths"])

    def test_rejects_out_of_scope_path(self):
        (self.repo / "outside.txt").write_text("no\n")
        with self.assertRaisesRegex(PublishError, "outside the work order"):
            publish(self.request(("outside.txt",)))

    def test_rejects_control_plane_path_even_if_requested(self):
        with self.assertRaisesRegex(PublishError, "unsafe allowed path"):
            PublishRequest.from_dict({
                "worktree": str(self.repo), "branch": "codex/integration", "expected_parent": self.parent,
                "allowed_paths": ["PLAN.md"], "test_receipt": str(self.repo / "x"),
                "test_receipt_sha256": "a" * 64, "message": "test: forbidden path",
            })

    def test_rejects_stale_parent(self):
        (self.repo / "src/value.txt").write_text("changed\n")
        request = self.request()
        object.__setattr__(request, "expected_parent", "f" * 40)
        with self.assertRaisesRegex(PublishError, "identity mismatch"):
            publish(request)
