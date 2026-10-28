from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("runtime_installer",ROOT/"scripts/install_runner_python_runtime.py")
INSTALLER=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(INSTALLER)


class RunnerPythonRuntimeTest(unittest.TestCase):
    def test_runtime_lock_pins_every_transitive_dependency(self):
        rows={
            line.split("==",1)[0].lower()
            for line in (ROOT/"requirements-runtime.lock").read_text().splitlines()
            if line and not line.startswith("#")
        }
        self.assertEqual(
            {"attrs","jsonschema","jsonschema-specifications","pyyaml","referencing","rfc3339-validator","rpds-py","six","typing-extensions"},
            rows,
        )
        self.assertEqual("6.0.3",INSTALLER.locked_packages(ROOT/"requirements-runtime.lock")["pyyaml"])
        self.assertEqual("4.16.0",INSTALLER.locked_packages(ROOT/"requirements-runtime.lock")["typing-extensions"])

    def test_runtime_lock_rejects_unpinned_and_probe_rejects_version_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/"lock.txt"; lock.write_text("jsonschema>=4\n")
            with self.assertRaisesRegex(INSTALLER.RuntimeInstallError,"unpinned"):
                INSTALLER.locked_packages(lock)
        with self.assertRaisesRegex(INSTALLER.RuntimeInstallError,"differ"):
            INSTALLER._probe_locked_packages(
                {"packages":{"jsonschema":"0.0.0"}}, {"jsonschema":"4.26.0"}
            )

    def test_runtime_probe_imports_runner_stack_and_rejects_retired_prefix(self):
        python=(ROOT/".venv/bin/python").absolute()
        probe=INSTALLER.runtime_probe(python,ROOT,["/retired/kgnote-worktree"])
        self.assertEqual(str(python),probe["sys_executable"])
        self.assertTrue(str(probe["imports"]["local_autonomy_runner"]).startswith(str(ROOT/"scripts")))
        with self.assertRaisesRegex(INSTALLER.RuntimeInstallError,"forbidden prefix"):
            INSTALLER.runtime_probe(python,ROOT,[str(ROOT)])

    def test_repository_identity_requires_exact_clean_detached_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            subprocess.run(["git","init","-b","main"],cwd=repo,check=True,capture_output=True)
            subprocess.run(["git","config","user.email","test@example.invalid"],cwd=repo,check=True)
            subprocess.run(["git","config","user.name","Test"],cwd=repo,check=True)
            (repo/"tracked.txt").write_text("clean\n")
            subprocess.run(["git","add","tracked.txt"],cwd=repo,check=True)
            subprocess.run(["git","commit","-m","seed"],cwd=repo,check=True,capture_output=True)
            head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
            subprocess.run(["git","checkout","--detach",head],cwd=repo,check=True,capture_output=True)
            identity=INSTALLER.repository_identity(repo,head)
            self.assertEqual(head,identity["commit"])
            (repo/"dirty.txt").write_text("dirty\n")
            with self.assertRaisesRegex(INSTALLER.RuntimeInstallError,"clean"):
                INSTALLER.repository_identity(repo,head)


if __name__=="__main__": unittest.main()
