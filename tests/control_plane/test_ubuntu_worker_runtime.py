from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import install_ubuntu_worker_runtime as RUNTIME

ROOT = Path(__file__).resolve().parents[2]


class UbuntuWorkerRuntimeTest(unittest.TestCase):
    def _worker_release(
        self, root: Path, *, import_failure: bool = False,
        help_failure: bool = False,
    ):
        release = root / "release"
        (release / "scripts").mkdir(parents=True)
        files = {}
        for name, relative in RUNTIME.WORKER_RUNTIME_SOURCES.items():
            source = release / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            if name == "requirements-runtime.lock":
                source.write_text("jsonschema==4.26.0\n")
            elif import_failure and name == "codex_control.py":
                source.write_text("raise RuntimeError('forced import failure')\n")
            elif help_failure and name == "product_goal_worker_result.py":
                source.write_text(
                    "import argparse,sys\n"
                    "if __name__ == '__main__' and '--help' in sys.argv: raise SystemExit(17)\n"
                    "argparse.ArgumentParser().parse_args()\n"
                )
            elif name in RUNTIME.WORKER_RUNTIME_ENTRYPOINTS:
                source.write_text(
                    "import argparse\n"
                    "parser=argparse.ArgumentParser()\n"
                    "parser.parse_args()\n"
                )
            else:
                source.write_text("VALUE = True\n")
            files[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest = release / RUNTIME.WORKER_RUNTIME_MANIFEST_RELATIVE
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({
            "schema_version": RUNTIME.WORKER_RUNTIME_MANIFEST_SCHEMA,
            "files": files,
        }))
        subprocess.run(["git", "init", "-q"], cwd=release, check=True)
        subprocess.run(["git", "config", "user.name", "KGnote Test"], cwd=release, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=release, check=True)
        subprocess.run(["git", "add", "."], cwd=release, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture release"],
            cwd=release, check=True,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=release, check=True,
            text=True, capture_output=True,
        ).stdout.strip()
        return release, manifest, files, revision

    def _seed_flat_runtime(
        self, runtime: Path, *, missing: set[str] | None = None,
    ) -> tuple[Path, dict[str, bytes]]:
        target = runtime / RUNTIME.WORKER_RUNTIME_RELATIVE
        target.mkdir(parents=True)
        old = {}
        missing = missing or set()
        for name in RUNTIME.WORKER_RUNTIME_SOURCES:
            if name in missing:
                continue
            old[name] = f"OLD:{name}\n".encode()
            (target / name).write_bytes(old[name])
        return target, old

    def test_repository_worker_runtime_manifest_matches_sources(self):
        manifest = RUNTIME._load_worker_runtime_manifest(
            ROOT / RUNTIME.WORKER_RUNTIME_MANIFEST_RELATIVE,
        )
        observed = {
            name: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for name, relative in RUNTIME.WORKER_RUNTIME_SOURCES.items()
        }
        self.assertEqual(manifest["files"], observed)

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
            release,manifest,runtime_files,revision=self._worker_release(root)
            gh=runtime/"bin/gh"; gh.parent.mkdir(parents=True); gh.write_text("gh\n"); gh.chmod(0o755)
            uv=runtime/RUNTIME.UV_RELATIVE; uv.write_text("uv\n"); uv.chmod(0o755)
            python=checkout/".venv/bin/python"; python.parent.mkdir(parents=True); python.write_text("python\n"); python.chmod(0o755)
            identity={"branch":"codex/o2-reading-experience","head":"a"*40,"tree":"b"*40}
            uv_identity={"version":RUNTIME.UV_VERSION,"path":str(uv),"sha256":RUNTIME.UV_SHA256}
            def command(command, *, cwd=None, env=None):
                if command[:2] == [str(node),str(codex_js)]: return RUNTIME.CODEX_VERSION
                if command[0] == str(node): return RUNTIME.NODE_VERSION
                if command[0] == str(npm): return RUNTIME.NPM_VERSION
                if command[0] == str(python): return RUNTIME.PYTHON_VERSION
                self.fail(command)
            receipt_path=root/"receipt.json"
            runtime_receipt={"target":str(root),"files":runtime_files,"model_launches":0}
            with patch.object(RUNTIME.platform,"machine",return_value="aarch64"), patch.object(RUNTIME,"_validate_checkout",return_value=identity) as checkout_check, patch.object(RUNTIME,"_install_gh",return_value=gh), patch.object(RUNTIME,"_validate_uv",return_value=uv_identity), patch.object(RUNTIME,"_install_worker_runtime",return_value=runtime_receipt), patch.object(RUNTIME,"_install_venv",return_value=(python,"4.26.0:6.0.3")), patch.object(RUNTIME,"_run",side_effect=command):
                receipt=RUNTIME.install(
                    archive=archive,checkout=checkout,expected_head="a"*40,
                    runtime_root=runtime,release_root=release,
                    runtime_manifest=manifest,reviewed_revision=revision,
                    receipt_path=receipt_path,
                )
            self.assertEqual("PASS",receipt["status"])
            self.assertEqual(0,receipt["model_launches"])
            self.assertEqual("2.103.2",receipt["gh"]["version"])
            self.assertEqual(RUNTIME.UV_SHA256,receipt["uv"]["sha256"])
            self.assertEqual("Python 3.12.3",receipt["python"]["version"])
            self.assertEqual(runtime_receipt,receipt["worker_runtime"])
            self.assertEqual(2,checkout_check.call_count)
            self.assertTrue(receipt_path.is_file())

    def test_worker_runtime_install_attests_files_and_cold_starts_entrypoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); release,manifest,files,revision=self._worker_release(root)
            runtime=root/"runtime-root"
            receipt=RUNTIME._install_worker_runtime(
                release_root=release,runtime_root=runtime,
                manifest_path=manifest,reviewed_revision=revision,
                python=Path(sys.executable),
            )
            self.assertEqual(files,receipt["files"])
            self.assertEqual(0,receipt["model_launches"])
            self.assertEqual(0,receipt["installed_cold_start"]["model_launches"])
            self.assertEqual(
                set(RUNTIME.WORKER_RUNTIME_ENTRYPOINTS),
                set(receipt["installed_cold_start"]["entrypoints"]),
            )

    def test_worker_runtime_missing_module_fails_before_target_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); release,manifest,_files,revision=self._worker_release(root)
            (release/RUNTIME.WORKER_RUNTIME_SOURCES["codex_jsonl_evidence.py"]).unlink()
            runtime=root/"runtime-root"
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError,"source is absent"):
                RUNTIME._install_worker_runtime(
                    release_root=release,runtime_root=runtime,
                    manifest_path=manifest,reviewed_revision=revision,
                    python=Path(sys.executable),
                )
            self.assertFalse((runtime/RUNTIME.WORKER_RUNTIME_RELATIVE).exists())

    def test_worker_runtime_source_hash_drift_fails_before_target_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); release,manifest,_files,revision=self._worker_release(root)
            (release/RUNTIME.WORKER_RUNTIME_SOURCES["codex_jsonl_evidence.py"]).write_text("TAMPERED=True\n")
            runtime=root/"runtime-root"
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError,"SHA-256 differs"):
                RUNTIME._install_worker_runtime(
                    release_root=release,runtime_root=runtime,
                    manifest_path=manifest,reviewed_revision=revision,
                    python=Path(sys.executable),
                )
            self.assertFalse((runtime/RUNTIME.WORKER_RUNTIME_RELATIVE).exists())

    def test_matching_hash_import_failure_preserves_active_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, _files, revision = self._worker_release(
                root, import_failure=True,
            )
            runtime = root / "runtime-root"
            target, old = self._seed_flat_runtime(runtime)
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError, "forced import failure"):
                RUNTIME._install_worker_runtime(
                    release_root=release, runtime_root=runtime,
                    manifest_path=manifest, reviewed_revision=revision,
                    python=Path(sys.executable),
                )
            self.assertEqual(
                old,
                {name: (target / name).read_bytes() for name in RUNTIME.WORKER_RUNTIME_SOURCES},
            )
            self.assertFalse((target / RUNTIME.WORKER_RUNTIME_CURRENT).exists())

    def test_entrypoint_help_failure_preserves_active_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, _files, revision = self._worker_release(
                root, help_failure=True,
            )
            runtime = root / "runtime-root"
            target, old = self._seed_flat_runtime(runtime)
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError, "runtime command failed"):
                RUNTIME._install_worker_runtime(
                    release_root=release, runtime_root=runtime,
                    manifest_path=manifest, reviewed_revision=revision,
                    python=Path(sys.executable),
                )
            self.assertEqual(
                old,
                {name: (target / name).read_bytes() for name in RUNTIME.WORKER_RUNTIME_SOURCES},
            )
            self.assertFalse((target / RUNTIME.WORKER_RUNTIME_CURRENT).exists())

    def test_third_flat_shim_interruption_keeps_complete_old_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, files, revision = self._worker_release(root)
            runtime = root / "runtime-root"
            target, old = self._seed_flat_runtime(runtime)
            original = RUNTIME._atomic_symlink
            promoted = []

            def interrupt_third(source, destination):
                if destination.name in RUNTIME.WORKER_RUNTIME_SOURCES:
                    promoted.append(destination.name)
                    if len(promoted) == 3:
                        raise RUNTIME.UbuntuRuntimeError("forced third-file interruption")
                return original(source, destination)

            with patch.object(RUNTIME, "_atomic_symlink", side_effect=interrupt_third):
                with self.assertRaisesRegex(
                    RUNTIME.UbuntuRuntimeError, "forced third-file interruption",
                ):
                    RUNTIME._install_worker_runtime(
                        release_root=release, runtime_root=runtime,
                        manifest_path=manifest, reviewed_revision=revision,
                        python=Path(sys.executable),
                    )
            self.assertEqual(3, len(promoted))
            self.assertEqual(
                old,
                {name: (target / name).read_bytes() for name in RUNTIME.WORKER_RUNTIME_SOURCES},
            )
            self.assertFalse(any(
                hashlib.sha256((target / name).read_bytes()).hexdigest() == files[name]
                for name in RUNTIME.WORKER_RUNTIME_SOURCES
            ))
            receipt = RUNTIME._install_worker_runtime(
                release_root=release, runtime_root=runtime,
                manifest_path=manifest, reviewed_revision=revision,
                python=Path(sys.executable),
            )
            self.assertEqual(files, receipt["files"])
            self.assertTrue(all((target / name).is_symlink() for name in files))

    def test_formal_partial_flat_runtime_interruption_keeps_safe_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, files, revision = self._worker_release(root)
            runtime = root / "runtime-root"
            target, old = self._seed_flat_runtime(
                runtime, missing={"requirements-runtime.lock"},
            )
            original = RUNTIME._atomic_symlink
            promoted = []

            def interrupt_third(source, destination):
                if destination.name in RUNTIME.WORKER_RUNTIME_SOURCES:
                    promoted.append(destination.name)
                    if len(promoted) == 3:
                        raise RUNTIME.UbuntuRuntimeError("forced partial-baseline interruption")
                return original(source, destination)

            with patch.object(RUNTIME, "_atomic_symlink", side_effect=interrupt_third):
                with self.assertRaisesRegex(
                    RUNTIME.UbuntuRuntimeError, "partial-baseline interruption",
                ):
                    RUNTIME._install_worker_runtime(
                        release_root=release, runtime_root=runtime,
                        manifest_path=manifest, reviewed_revision=revision,
                        python=Path(sys.executable),
                    )
            self.assertEqual(3, len(promoted))
            self.assertEqual(
                old,
                {name: (target / name).read_bytes() for name in old},
            )
            self.assertEqual(
                (release / "requirements-runtime.lock").read_bytes(),
                (target / "requirements-runtime.lock").read_bytes(),
            )
            self.assertFalse(any(
                hashlib.sha256((target / name).read_bytes()).hexdigest() == files[name]
                for name in old
            ))
            receipt = RUNTIME._install_worker_runtime(
                release_root=release, runtime_root=runtime,
                manifest_path=manifest, reviewed_revision=revision,
                python=Path(sys.executable),
            )
            self.assertEqual(files, receipt["files"])
            self.assertTrue(all((target / name).is_symlink() for name in files))

    def test_post_switch_cold_start_failure_rolls_back_current_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, _files, revision = self._worker_release(root)
            runtime = root / "runtime-root"
            target, old = self._seed_flat_runtime(runtime)
            staged = {
                "python": str(sys.executable), "imports": [],
                "import_stdout": "", "entrypoints": {}, "model_launches": 0,
            }
            with patch.object(
                RUNTIME, "_cold_start_worker_runtime",
                side_effect=[
                    staged,
                    RUNTIME.UbuntuRuntimeError("forced post-switch cold-start failure"),
                ],
            ):
                with self.assertRaisesRegex(
                    RUNTIME.UbuntuRuntimeError, "post-switch cold-start failure",
                ):
                    RUNTIME._install_worker_runtime(
                        release_root=release, runtime_root=runtime,
                        manifest_path=manifest, reviewed_revision=revision,
                        python=Path(sys.executable),
                    )
            self.assertEqual(
                old,
                {name: (target / name).read_bytes() for name in RUNTIME.WORKER_RUNTIME_SOURCES},
            )
            current = target / RUNTIME.WORKER_RUNTIME_CURRENT
            self.assertTrue(current.is_symlink())
            self.assertTrue(Path(current.resolve()).name.startswith("legacy-"))

    def test_reviewed_revision_must_equal_clean_release_git_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, _files, _revision = self._worker_release(root)
            runtime = root / "runtime-root"
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError, "HEAD differs"):
                RUNTIME._install_worker_runtime(
                    release_root=release, runtime_root=runtime,
                    manifest_path=manifest, reviewed_revision="f" * 40,
                    python=Path(sys.executable),
                )
            self.assertFalse((runtime / RUNTIME.WORKER_RUNTIME_RELATIVE).exists())

    def test_non_git_release_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, _files, revision = self._worker_release(root)
            shutil.rmtree(release / ".git")
            runtime = root / "runtime-root"
            with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError, "Git checkout"):
                RUNTIME._install_worker_runtime(
                    release_root=release, runtime_root=runtime,
                    manifest_path=manifest, reviewed_revision=revision,
                    python=Path(sys.executable),
                )
            self.assertFalse((runtime / RUNTIME.WORKER_RUNTIME_RELATIVE).exists())

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

    def test_missing_venv_uses_pinned_uv_and_checks_before_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); checkout=root/"checkout"; checkout.mkdir()
            uv=root/"uv"; uv.write_text("uv\n"); uv.chmod(0o755)
            lock=root/"requirements-runtime.lock"; lock.write_text("jsonschema==4.26.0\n")
            calls=[]
            def command(command, *, cwd=None, env=None):
                calls.append(command)
                if command[:2] == [str(uv),"venv"]:
                    python=Path(command[-1])/"bin/python"
                    python.parent.mkdir(parents=True)
                    python.write_text("python\n"); python.chmod(0o755)
                    return ""
                if command[:3] == [str(uv),"pip","install"]:
                    return ""
                if command[1:4] == ["-m","pip","check"]:
                    return "No broken requirements found."
                if command[1] == "-c":
                    return json.dumps({"jsonschema":"4.26.0","pip":"26.2.2"})
                self.fail(command)
            with patch.object(RUNTIME,"_run",side_effect=command):
                python, evidence=RUNTIME._install_venv(checkout,lock,uv)
            self.assertEqual(checkout/".venv/bin/python",python)
            self.assertTrue(any(call[:2] == [str(uv),"venv"] for call in calls))
            self.assertTrue(any(call[:3] == [str(uv),"pip","install"] for call in calls))
            self.assertEqual("No broken requirements found.",evidence["pip_check"])

    def test_uv_identity_is_version_and_digest_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Path(directory); uv=runtime/RUNTIME.UV_RELATIVE
            uv.parent.mkdir(parents=True); uv.write_text("uv\n"); uv.chmod(0o755)
            with patch.object(RUNTIME,"_sha256",return_value=RUNTIME.UV_SHA256), patch.object(RUNTIME,"_run",return_value=RUNTIME.UV_VERSION):
                self.assertEqual(RUNTIME.UV_SHA256,RUNTIME._validate_uv(runtime)["sha256"])
            with patch.object(RUNTIME,"_sha256",return_value="0"*64), patch.object(RUNTIME,"_run",return_value=RUNTIME.UV_VERSION):
                with self.assertRaisesRegex(RUNTIME.UbuntuRuntimeError,"uv version or SHA-256"):
                    RUNTIME._validate_uv(runtime)


if __name__ == "__main__":
    unittest.main()
