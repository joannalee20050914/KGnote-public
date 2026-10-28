from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import install_ubuntu_worker_runtime as RUNTIME


class UbuntuWorkerRuntimeTest(unittest.TestCase):
    def test_install_receipt_binds_checkout_python_node_npm_and_gh(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); runtime=root/".local"; checkout=root/"checkout"; checkout.mkdir()
            node=runtime/RUNTIME.NODE_RELATIVE; npm=runtime/RUNTIME.NPM_RELATIVE
            codex_js=runtime/RUNTIME.CODEX_JS_RELATIVE
            node.parent.mkdir(parents=True)
            codex_js.parent.mkdir(parents=True)
            for path in (node,npm,codex_js): path.write_text("tool\n"); path.chmod(0o755)
            archive=root/RUNTIME.GH_ARCHIVE; archive.write_bytes(b"pinned archive")
            lock=root/"requirements-runtime.lock"; lock.write_text("jsonschema==4.26.0\n")
            gh=runtime/"bin/gh"; gh.parent.mkdir(parents=True); gh.write_text("gh\n"); gh.chmod(0o755)
            python=checkout/".venv/bin/python"; python.parent.mkdir(parents=True); python.write_text("python\n"); python.chmod(0o755)
            identity={"branch":"codex/o2-reading-experience","head":"a"*40,"tree":"b"*40}
            def command(command, *, cwd=None, env=None):
                if command[:2] == [str(node),str(codex_js)]: return RUNTIME.CODEX_VERSION
                if command[0] == str(node): return RUNTIME.NODE_VERSION
                if command[0] == str(npm): return RUNTIME.NPM_VERSION
                if command[0] == str(python): return RUNTIME.PYTHON_VERSION
                self.fail(command)
            receipt_path=root/"receipt.json"
            with patch.object(RUNTIME.platform,"machine",return_value="aarch64"), patch.object(RUNTIME,"_validate_checkout",return_value=identity) as checkout_check, patch.object(RUNTIME,"_install_gh",return_value=gh), patch.object(RUNTIME,"_install_venv",return_value=(python,"4.26.0:6.0.3")), patch.object(RUNTIME,"_run",side_effect=command):
                receipt=RUNTIME.install(
                    archive=archive,checkout=checkout,expected_head="a"*40,
                    runtime_root=runtime,requirements_lock=lock,receipt_path=receipt_path,
                )
            self.assertEqual("PASS",receipt["status"])
            self.assertEqual(0,receipt["model_launches"])
            self.assertEqual("2.103.2",receipt["gh"]["version"])
            self.assertEqual("Python 3.12.3",receipt["python"]["version"])
            self.assertEqual(2,checkout_check.call_count)
            self.assertTrue(receipt_path.is_file())

    def test_gh_archive_digest_mismatch_fails_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); archive=root/RUNTIME.GH_ARCHIVE; archive.write_bytes(b"wrong")
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError,"SHA-256"):
                RUNTIME._install_gh(archive,root/"runtime")

    def test_existing_venv_with_unexpected_distribution_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); checkout=root/"checkout"; checkout.mkdir()
            python=checkout/".venv/bin/python"; python.parent.mkdir(parents=True)
            python.write_text("python\n"); python.chmod(0o755)
            lock=root/"requirements-runtime.lock"; lock.write_text("jsonschema==4.26.0\n")
            inventory=json.dumps({"jsonschema":"4.26.0","unexpected":"1.0","pip":"24.0"})
            with patch.object(RUNTIME,"_run",return_value=inventory):
                with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError,"differs"):
                    RUNTIME._install_venv(checkout,lock)


if __name__ == "__main__":
    unittest.main()
