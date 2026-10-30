#!/usr/bin/env python3
"""Install and attest the pinned Ubuntu Product Goal development runtime.

Run this on the Ubuntu worker during reviewed deployment, before the Mac Runner
is reloaded.  The release archive must be supplied by the deployer; this helper
never trusts an unpinned network response and never starts a model process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


GH_VERSION = "2.103.2"
GH_ARCHIVE = f"gh_{GH_VERSION}_linux_arm64.tar.gz"
GH_ARCHIVE_SHA256 = "4c3e99a50bd8b181a3fe9d69b25dd978bac768148d88f01507c6b4d1ef61a443"
GH_RELEASE_URL = f"https://github.com/cli/cli/releases/download/v{GH_VERSION}/{GH_ARCHIVE}"
NODE_VERSION = "v24.12.0"
NPM_VERSION = "11.6.2"
PYTHON_VERSION = "Python 3.12.3"
CODEX_VERSION = "codex-cli 0.146.0"
UV_VERSION = "uv 0.13.1 (aarch64-unknown-linux-gnu)"
UV_SHA256 = "43c648f0632c625bf5c70ae844cdd69a44c2d4461ef2d4acf08e0720ccdfdf22"
NODE_RELATIVE = Path("lib/node-v24.12.0/bin/node")
NPM_RELATIVE = Path("lib/node-v24.12.0/bin/npm")
CODEX_JS_RELATIVE = Path("lib/node-v24.12.0/lib/node_modules/@openai/codex/bin/codex.js")
UV_RELATIVE = Path("bin/uv")
VENV_BOOTSTRAP_DISTRIBUTIONS = {"pip"}
WORKER_RUNTIME_MANIFEST_SCHEMA = "kgnote.ubuntu-worker-runtime-manifest.v1"
WORKER_RUNTIME_RECEIPT_SCHEMA = "kgnote.ubuntu-worker-runtime-receipt.v2"
WORKER_RUNTIME_RELATIVE = Path("share/kgnote/runtime")
WORKER_RUNTIME_RELEASES = ".worker-runtime-releases"
WORKER_RUNTIME_CURRENT = ".worker-runtime-current"
WORKER_RUNTIME_MANIFEST_RELATIVE = Path("config/ubuntu-worker-runtime-manifest.json")
WORKER_RUNTIME_SOURCES = {
    "requirements-runtime.lock": Path("requirements-runtime.lock"),
    "codex_jsonl_evidence.py": Path("scripts/codex_jsonl_evidence.py"),
    "linux_landlock_exec.py": Path("scripts/linux_landlock_exec.py"),
    "linux_worker_bootstrap.py": Path("scripts/linux_worker_bootstrap.py"),
    "linux_worker_guard.py": Path("scripts/linux_worker_guard.py"),
    "product_goal_runtime_admission.py": Path("scripts/product_goal_runtime_admission.py"),
    "product_goal_worker_identity.py": Path("scripts/product_goal_worker_identity.py"),
    "product_goal_worker_result.py": Path("scripts/product_goal_worker_result.py"),
    "o2_prepublication_control_tests.py": Path("scripts/o2_prepublication_control_tests.py"),
    "codex_control.py": Path("scripts/codex_control.py"),
    "claude_billing_preflight.py": Path("scripts/claude_billing_preflight.py"),
    "claude_reviewer_adapter.py": Path("scripts/claude_reviewer_adapter.py"),
    "product_goal_worker_lane.py": Path("scripts/product_goal_worker_lane.py"),
}
WORKER_RUNTIME_COMPATIBILITY = {
    "requirements-runtime.lock",
    "codex_jsonl_evidence.py",
    "product_goal_worker_identity.py",
    "product_goal_worker_result.py",
    "o2_prepublication_control_tests.py",
    "codex_control.py",
    "claude_billing_preflight.py",
    "claude_reviewer_adapter.py",
    "product_goal_worker_lane.py",
}
WORKER_RUNTIME_GENERATION_ONLY = set(WORKER_RUNTIME_SOURCES) - WORKER_RUNTIME_COMPATIBILITY
WORKER_RUNTIME_IMPORTS = (
    "codex_jsonl_evidence", "linux_landlock_exec", "linux_worker_bootstrap",
    "linux_worker_guard", "product_goal_runtime_admission", "product_goal_worker_identity",
    "product_goal_worker_result", "o2_prepublication_control_tests", "codex_control",
    "claude_billing_preflight", "claude_reviewer_adapter",
    "product_goal_worker_lane",
)
WORKER_RUNTIME_ENTRYPOINTS = (
    "product_goal_worker_result.py", "product_goal_worker_lane.py",
    "o2_prepublication_control_tests.py",
)


class UbuntuRuntimeError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str], *, cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True,
        timeout=300, check=False,
    )
    if completed.returncode:
        raise UbuntuRuntimeError(
            f"runtime command failed: {Path(command[0]).name}: "
            f"{(completed.stderr or completed.stdout).strip()}"
        )
    return completed.stdout.strip() or completed.stderr.strip()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_copy(source: Path, target: Path) -> None:
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise UbuntuRuntimeError(f"worker runtime target is not a regular file: {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        os.chmod(temporary, source.stat().st_mode & 0o777)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_symlink(target: str, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary = link.parent / f".{link.name}.{os.getpid()}.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise UbuntuRuntimeError(f"stale worker runtime symlink exists: {temporary.name}")
    try:
        os.symlink(target, temporary)
        os.replace(temporary, link)
        _fsync_directory(link.parent)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _load_worker_runtime_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise UbuntuRuntimeError("worker runtime manifest is absent or not a regular file")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UbuntuRuntimeError("worker runtime manifest is not valid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != WORKER_RUNTIME_MANIFEST_SCHEMA:
        raise UbuntuRuntimeError("worker runtime manifest schema differs")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(WORKER_RUNTIME_SOURCES):
        raise UbuntuRuntimeError("worker runtime manifest file set differs")
    if any(
        not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
        for digest in files.values()
    ):
        raise UbuntuRuntimeError("worker runtime manifest contains an invalid SHA-256")
    return manifest


def _git_blob_sha256(repository: Path, revision: str, relative: Path) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "show", f"{revision}:{relative.as_posix()}"],
        cwd=repository, capture_output=True, timeout=30, check=False,
    )
    if completed.returncode:
        raise UbuntuRuntimeError(
            f"reviewed release commit lacks worker runtime source: {relative}"
        )
    return hashlib.sha256(completed.stdout).hexdigest()


def _validate_reviewed_release(
    release_root: Path, manifest_path: Path, reviewed_revision: str,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, str]]:
    if not re.fullmatch(r"[0-9a-f]{40}", reviewed_revision):
        raise UbuntuRuntimeError("reviewed release revision is not a full Git commit")
    if not release_root.is_dir() or release_root.is_symlink():
        raise UbuntuRuntimeError("reviewed release root is absent or is a symlink")
    expected_manifest = release_root.resolve() / WORKER_RUNTIME_MANIFEST_RELATIVE
    if manifest_path.resolve() != expected_manifest:
        raise UbuntuRuntimeError("worker runtime manifest is outside the reviewed release")
    try:
        repository_root = Path(
            _run(["/usr/bin/git", "rev-parse", "--show-toplevel"], cwd=release_root)
        ).resolve()
        head = _run(["/usr/bin/git", "rev-parse", "HEAD"], cwd=release_root)
        tree = _run(["/usr/bin/git", "rev-parse", "HEAD^{tree}"], cwd=release_root)
        status = _run(
            ["/usr/bin/git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=release_root,
        )
    except UbuntuRuntimeError as exc:
        raise UbuntuRuntimeError("reviewed release root is not a readable Git checkout") from exc
    if repository_root != release_root.resolve() or head != reviewed_revision:
        raise UbuntuRuntimeError(
            "reviewed release checkout root or HEAD differs"
        )

    manifest = _load_worker_runtime_manifest(manifest_path)
    if _git_blob_sha256(
        release_root, reviewed_revision, WORKER_RUNTIME_MANIFEST_RELATIVE
    ) != _sha256(manifest_path):
        raise UbuntuRuntimeError("worker runtime manifest differs from the reviewed Git commit")
    source_files: dict[str, Path] = {}
    for name, relative in WORKER_RUNTIME_SOURCES.items():
        source = release_root / relative
        if not source.is_file() or source.is_symlink():
            raise UbuntuRuntimeError(f"reviewed worker runtime source is absent: {relative}")
        observed = _sha256(source)
        if observed != manifest["files"][name]:
            raise UbuntuRuntimeError(f"reviewed worker runtime source SHA-256 differs: {relative}")
        if _git_blob_sha256(release_root, reviewed_revision, relative) != observed:
            raise UbuntuRuntimeError(
                f"reviewed worker runtime source differs from the Git commit: {relative}"
            )
        source_files[name] = source
    if status:
        raise UbuntuRuntimeError("reviewed release checkout is not clean")
    return manifest, source_files, {
        "head": head,
        "tree": tree,
        "manifest_sha256": _sha256(manifest_path),
    }


def _worker_generation_hashes(
    directory: Path, names: set[str] | None = None,
) -> dict[str, str]:
    if directory.is_symlink() or not directory.is_dir():
        raise UbuntuRuntimeError("worker runtime generation is not a real directory")
    observed: dict[str, str] = {}
    for name in sorted(names or set(WORKER_RUNTIME_SOURCES)):
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise UbuntuRuntimeError(
                f"worker runtime generation file is absent or not regular: {name}"
            )
        observed[name] = _sha256(path)
    return observed


def _generation_from_link(releases: Path, link: Path) -> Path:
    if not link.is_symlink():
        raise UbuntuRuntimeError("worker runtime current pointer is not a symlink")
    generation = (link.parent / os.readlink(link)).resolve()
    try:
        generation.relative_to(releases.resolve())
    except ValueError as exc:
        raise UbuntuRuntimeError("worker runtime current pointer leaves releases") from exc
    if generation.parent != releases.resolve() or not generation.is_dir():
        raise UbuntuRuntimeError("worker runtime current pointer is invalid")
    return generation


def _prepare_legacy_generation(
    target: Path, releases: Path, fallback_generation: Path,
) -> Path | None:
    existing = [
        (target / name).exists() or (target / name).is_symlink()
        for name in WORKER_RUNTIME_SOURCES
    ]
    if not any(existing):
        return None
    missing = {
        name for name, present in zip(WORKER_RUNTIME_SOURCES, existing)
        if not present
    }
    # The formal legacy runtime may lack the dependency lock and files first
    # introduced as generation-pinned admission components.  Only those exact
    # reviewed candidate bytes may bridge the first pointer migration; an
    # absent historical Worker module remains unsupported drift.
    allowed_missing = {"requirements-runtime.lock"} | WORKER_RUNTIME_GENERATION_ONLY
    if missing - allowed_missing:
        raise UbuntuRuntimeError("existing flat worker runtime is incomplete")
    sources: dict[str, Path] = {}
    digests: dict[str, str] = {}
    for name in WORKER_RUNTIME_SOURCES:
        path = (
            fallback_generation / name
            if name in missing
            else target / name
        )
        if not path.is_file() or path.is_symlink():
            raise UbuntuRuntimeError(
                f"existing flat worker runtime is not a regular file: {name}"
            )
        sources[name] = path
        digests[name] = _sha256(path)
    identity = hashlib.sha256(
        json.dumps(digests, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    legacy = releases / f"legacy-{identity}"
    if legacy.exists() or legacy.is_symlink():
        if _worker_generation_hashes(legacy) != digests:
            raise UbuntuRuntimeError("existing legacy worker runtime generation differs")
        return legacy
    with tempfile.TemporaryDirectory(prefix=".legacy-", dir=releases) as temporary:
        staging = Path(temporary)
        for name, source in sources.items():
            _atomic_copy(source, staging / name)
        _fsync_directory(staging)
        os.replace(staging, legacy)
        _fsync_directory(releases)
    return legacy


def _promote_worker_generation(
    *, target: Path, generation: Path, manifest: dict[str, Any], python: Path,
) -> None:
    releases = target / WORKER_RUNTIME_RELEASES
    current = target / WORKER_RUNTIME_CURRENT
    releases.mkdir(parents=True, exist_ok=True)
    if current.exists() and not current.is_symlink():
        raise UbuntuRuntimeError("worker runtime current pointer is not a symlink")
    if current.is_symlink():
        visible_generation = _generation_from_link(releases, current)
    else:
        visible_generation = _prepare_legacy_generation(
            target, releases, generation,
        )
        if visible_generation is None:
            visible_generation = generation
        relative = os.path.relpath(visible_generation, target)
        _atomic_symlink(relative, current)

    visible_hashes: dict[str, str] = {}
    introduced_compatibility: set[str] = set()
    for name in sorted(WORKER_RUNTIME_COMPATIBILITY):
        generation_path = visible_generation / name
        shim_path = target / name
        if generation_path.is_symlink():
            raise UbuntuRuntimeError(
                f"worker runtime generation file is not regular: {name}"
            )
        if generation_path.is_file():
            visible_hashes[name] = _sha256(generation_path)
            continue
        if generation_path.exists():
            raise UbuntuRuntimeError(
                f"worker runtime generation file is not regular: {name}"
            )
        # A compatibility entrypoint may be introduced by the reviewed next
        # generation.  It is distinguishable from deletion/drift in the active
        # generation only when no legacy shim exists for that name.  Existing
        # (including dangling) shims remain fail-closed.
        if shim_path.exists() or shim_path.is_symlink():
            raise UbuntuRuntimeError(
                "worker runtime compatibility shim exists for an absent "
                f"generation file: {name}"
            )
        introduced_compatibility.add(name)
    # Add any missing compatibility bridge (notably the historical lock) first.
    # An interrupted first migration therefore remains fail-closed but complete
    # enough for the still-visible legacy entrypoint to validate its environment.
    compatibility_order = sorted(
        set(visible_hashes),
        key=lambda name: (
            (target / name).exists() or (target / name).is_symlink(),
            name,
        ),
    )
    for name in compatibility_order:
        path = target / name
        expected_link = f"{WORKER_RUNTIME_CURRENT}/{name}"
        if path.is_symlink():
            if os.readlink(path) != expected_link:
                raise UbuntuRuntimeError(f"worker runtime shim differs: {name}")
            continue
        if path.exists():
            if not path.is_file() or _sha256(path) != visible_hashes[name]:
                raise UbuntuRuntimeError(f"existing worker runtime file differs: {name}")
        _atomic_symlink(expected_link, path)

    previous_pointer = os.readlink(current)
    switched = visible_generation != generation
    created_compatibility: list[str] = []
    if visible_generation != generation:
        _atomic_symlink(os.path.relpath(generation, target), current)
    try:
        if _worker_generation_hashes(generation) != manifest["files"]:
            raise UbuntuRuntimeError("promoted worker runtime generation differs")
        installed = _worker_generation_hashes(generation)
        if installed != manifest["files"]:
            raise UbuntuRuntimeError("installed worker runtime differs from the reviewed manifest")
        _cold_start_worker_runtime(generation, python)
        for name in sorted(introduced_compatibility):
            path = target / name
            if path.exists() or path.is_symlink():
                raise UbuntuRuntimeError(
                    f"new worker runtime compatibility path appeared during promotion: {name}"
                )
            _atomic_symlink(f"{WORKER_RUNTIME_CURRENT}/{name}", path)
            created_compatibility.append(name)
    except Exception:
        if switched:
            _atomic_symlink(previous_pointer, current)
        removed_compatibility = False
        for name in reversed(created_compatibility):
            path = target / name
            expected_link = f"{WORKER_RUNTIME_CURRENT}/{name}"
            if not path.is_symlink() or os.readlink(path) != expected_link:
                raise UbuntuRuntimeError(
                    f"new worker runtime compatibility shim changed during rollback: {name}"
                )
            path.unlink()
            removed_compatibility = True
        if removed_compatibility:
            _fsync_directory(target)
        raise


def _cold_start_worker_runtime(directory: Path, python: Path) -> dict[str, Any]:
    environment = {
        "HOME": os.environ.get("HOME", "/home/kgnote"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(directory),
    }
    imports = _run(
        [str(python), "-c", "import " + ",".join(WORKER_RUNTIME_IMPORTS)],
        cwd=directory, env=environment,
    )
    entrypoints = {}
    for name in WORKER_RUNTIME_ENTRYPOINTS:
        entrypoints[name] = _run(
            [str(python), str(directory / name), "--help"],
            cwd=directory, env=environment,
        )
    return {
        "python": str(python),
        "imports": list(WORKER_RUNTIME_IMPORTS),
        "import_stdout": imports,
        "entrypoints": {
            name: {"argument": "--help", "status": "PASS"}
            for name in entrypoints
        },
        "model_launches": 0,
    }


def _install_worker_runtime(
    *, release_root: Path, runtime_root: Path, manifest_path: Path,
    reviewed_revision: str, python: Path = Path("/usr/bin/python3"),
) -> dict[str, Any]:
    if not python.is_file() or not os.access(python, os.X_OK):
        raise UbuntuRuntimeError("formal Ubuntu Python is absent or not executable")
    manifest, source_files, source_identity = _validate_reviewed_release(
        release_root, manifest_path, reviewed_revision,
    )

    target = runtime_root / WORKER_RUNTIME_RELATIVE
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise UbuntuRuntimeError("worker runtime target directory is invalid")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".worker-runtime-staging-", dir=target.parent,
    ) as temporary:
        staging = Path(temporary)
        for name, source in source_files.items():
            _atomic_copy(source, staging / name)
        staged_cold_start = _cold_start_worker_runtime(staging, python)
        _fsync_directory(staging)
        target.mkdir(parents=True, exist_ok=True)
        releases = target / WORKER_RUNTIME_RELEASES
        releases.mkdir(parents=True, exist_ok=True)
        generation = releases / reviewed_revision
        if generation.exists() or generation.is_symlink():
            if _worker_generation_hashes(generation) != manifest["files"]:
                raise UbuntuRuntimeError("existing reviewed worker runtime generation differs")
        else:
            os.replace(staging, generation)
            _fsync_directory(releases)
    _promote_worker_generation(
        target=target, generation=generation, manifest=manifest, python=python,
    )
    installed = _worker_generation_hashes(generation)
    if installed != manifest["files"]:
        raise UbuntuRuntimeError("installed worker runtime differs from the reviewed manifest")
    installed_cold_start = _cold_start_worker_runtime(generation, python)
    return {
        "reviewed_revision": reviewed_revision,
        "reviewed_source": source_identity,
        "release_root": str(release_root),
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "target": str(target),
        "generation": str(generation),
        "current_pointer": str(target / WORKER_RUNTIME_CURRENT),
        "files": installed,
        "staged_cold_start": staged_cold_start,
        "installed_cold_start": installed_cold_start,
        "model_launches": 0,
    }


def _validate_checkout(checkout: Path, expected_head: str) -> dict[str, str]:
    if checkout.is_symlink() or not (checkout / ".git").is_dir():
        raise UbuntuRuntimeError("Ubuntu checkout is not a private real Git repository")
    branch = _run(["/usr/bin/git", "branch", "--show-current"], cwd=checkout)
    head = _run(["/usr/bin/git", "rev-parse", "HEAD"], cwd=checkout)
    tree = _run(["/usr/bin/git", "rev-parse", "HEAD^{tree}"], cwd=checkout)
    status = _run(
        ["/usr/bin/git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=checkout,
    )
    if branch != "codex/o2-reading-experience" or head != expected_head or status:
        raise UbuntuRuntimeError("Ubuntu checkout branch, HEAD, or cleanliness differs")
    return {"branch": branch, "head": head, "tree": tree}


def _install_gh(archive: Path, runtime_root: Path) -> Path:
    if archive.name != GH_ARCHIVE or _sha256(archive) != GH_ARCHIVE_SHA256:
        raise UbuntuRuntimeError("GitHub CLI archive identity or SHA-256 differs")
    target = runtime_root / f"lib/gh-{GH_VERSION}"
    expected_top = f"gh_{GH_VERSION}_linux_arm64"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="kgnote-gh-install-", dir=target.parent) as directory:
            temporary = Path(directory)
            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                if not members or any(
                    member.name.startswith(("/", "../"))
                    or "/../" in member.name
                    or member.issym()
                    or member.islnk()
                    or member.name.split("/", 1)[0] != expected_top
                    for member in members
                ):
                    raise UbuntuRuntimeError("GitHub CLI archive contains an unsafe member")
                bundle.extractall(temporary, filter="data")
            extracted = temporary / expected_top
            if not (extracted / "bin/gh").is_file():
                raise UbuntuRuntimeError("GitHub CLI archive lacks the expected binary")
            os.replace(extracted, target)
    gh = target / "bin/gh"
    if not gh.is_file() or not os.access(gh, os.X_OK):
        raise UbuntuRuntimeError("GitHub CLI installation is not executable")
    bin_directory = runtime_root / "bin"
    bin_directory.mkdir(parents=True, exist_ok=True)
    link = bin_directory / "gh"
    if link.exists() or link.is_symlink():
        if not link.is_symlink() or link.resolve() != gh.resolve():
            raise UbuntuRuntimeError("existing gh entrypoint differs from the pinned runtime")
    else:
        link.symlink_to(gh)
    if not _run([str(link), "--version"]).splitlines()[0].startswith(f"gh version {GH_VERSION}"):
        raise UbuntuRuntimeError("GitHub CLI version read-back differs")
    return link


def _validate_uv(runtime_root: Path) -> dict[str, str]:
    uv = runtime_root / UV_RELATIVE
    if not uv.is_file() or not os.access(uv, os.X_OK):
        raise UbuntuRuntimeError("pinned uv runtime is absent or not executable")
    digest = _sha256(uv)
    version = _run([str(uv), "--version"])
    if digest != UV_SHA256 or version != UV_VERSION:
        raise UbuntuRuntimeError("uv version or SHA-256 differs from the pinned runtime")
    return {"version": version, "path": str(uv), "sha256": digest}


def _install_venv(
    checkout: Path, lock: Path, uv: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    if not lock.is_file():
        raise UbuntuRuntimeError("requirements-runtime.lock is missing")
    target = checkout / ".venv"
    if not target.exists():
        if uv is None:
            raise UbuntuRuntimeError("pinned uv is required to create the Ubuntu repository venv")
        temporary = checkout / f".venv.installing-{os.getpid()}"
        if temporary.exists():
            raise UbuntuRuntimeError("stale Ubuntu venv installation directory exists")
        try:
            _run(
                [str(uv), "venv", "--python", "/usr/bin/python3", "--seed", str(temporary)],
                cwd=checkout,
            )
            _run(
                [
                    str(uv), "pip", "install", "--python",
                    str(temporary / "bin/python"), "--no-deps", "--requirement", str(lock),
                ],
                cwd=checkout,
            )
            _run([str(temporary / "bin/python"), "-m", "pip", "check"], cwd=checkout)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    python = target / "bin/python"
    if not python.is_file() or not os.access(python, os.X_OK):
        raise UbuntuRuntimeError("Ubuntu repository venv is not executable")
    expected: dict[str, str] = {}
    for line in lock.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.count("==") != 1:
            raise UbuntuRuntimeError("requirements-runtime.lock contains a non-exact pin")
        raw_name, version = value.split("==", 1)
        name = re.sub(r"[-_.]+", "-", raw_name.strip()).lower()
        if not name or not version.strip() or name in expected:
            raise UbuntuRuntimeError("requirements-runtime.lock contains an invalid or duplicate pin")
        expected[name] = version.strip()
    if not expected:
        raise UbuntuRuntimeError("requirements-runtime.lock contains no pinned dependencies")
    observed = json.loads(_run([
        str(python), "-c",
        "import importlib.metadata,json,re; "
        "normalize=lambda value:re.sub(r'[-_.]+','-',value).lower(); "
        "print(json.dumps({normalize(dist.metadata['Name']):dist.version "
        "for dist in importlib.metadata.distributions() if dist.metadata['Name']}))",
    ], cwd=checkout))
    if not isinstance(observed, dict) or any(
        not isinstance(name, str) or not isinstance(version, str)
        for name, version in observed.items()
    ):
        raise UbuntuRuntimeError("Ubuntu repository venv inventory is malformed")
    missing = sorted(set(expected) - set(observed))
    mismatched = sorted(
        name for name in set(expected) & set(observed)
        if observed[name] != expected[name]
    )
    unexpected = sorted(set(observed) - set(expected) - VENV_BOOTSTRAP_DISTRIBUTIONS)
    if missing or mismatched or unexpected:
        raise UbuntuRuntimeError("Ubuntu repository venv differs from requirements-runtime.lock")
    pip_check = _run([str(python), "-m", "pip", "check"], cwd=checkout)
    return python, {
        "requirements_lock_sha256": _sha256(lock),
        "expected": expected,
        "observed": {name: observed[name] for name in sorted(expected)},
        "allowed_bootstrap_distributions": sorted(
            set(observed) & VENV_BOOTSTRAP_DISTRIBUTIONS
        ),
        "pip_check": pip_check,
    }


def install(
    *, archive: Path, checkout: Path, expected_head: str,
    runtime_root: Path, release_root: Path, runtime_manifest: Path,
    reviewed_revision: str, receipt_path: Path,
) -> dict[str, Any]:
    if platform.machine().lower() not in {"aarch64", "arm64"}:
        raise UbuntuRuntimeError("pinned Ubuntu runtime supports only arm64")
    checkout_identity = _validate_checkout(checkout, expected_head)
    node = runtime_root / NODE_RELATIVE
    npm = runtime_root / NPM_RELATIVE
    codex_js = runtime_root / CODEX_JS_RELATIVE
    if not node.is_file() or not npm.is_file() or not codex_js.is_file():
        raise UbuntuRuntimeError("pinned Node/npm/Codex runtime is absent")
    tool_env = dict(os.environ)
    tool_env["PATH"] = f"{node.parent}:/usr/bin:/bin"
    node_version = _run([str(node), "--version"])
    npm_version = _run([str(npm), "--version"], env=tool_env)
    codex_version = _run([str(node), str(codex_js), "--version"])
    if (
        node_version != NODE_VERSION
        or npm_version != NPM_VERSION
        or codex_version != CODEX_VERSION
    ):
        raise UbuntuRuntimeError("Node/npm/Codex version differs from the pinned runtime")
    gh = _install_gh(archive, runtime_root)
    uv = _validate_uv(runtime_root)
    worker_runtime = _install_worker_runtime(
        release_root=release_root, runtime_root=runtime_root,
        manifest_path=runtime_manifest, reviewed_revision=reviewed_revision,
    )
    requirements_lock = Path(worker_runtime["target"]) / "requirements-runtime.lock"
    python, dependencies = _install_venv(
        checkout, requirements_lock, Path(uv["path"]),
    )
    python_version = _run([str(python), "--version"])
    if python_version != PYTHON_VERSION:
        raise UbuntuRuntimeError("Python version differs from the pinned runtime")
    # The venv path is ignored by Git; prove installer activity did not alter candidate bytes.
    checkout_after = _validate_checkout(checkout, expected_head)
    if checkout_after != checkout_identity:
        raise UbuntuRuntimeError("Ubuntu checkout identity changed during runtime installation")
    receipt = {
        "schema_version": WORKER_RUNTIME_RECEIPT_SCHEMA,
        "status": "PASS",
        "checkout": checkout_after,
        "architecture": platform.machine(),
        "gh": {
            "version": GH_VERSION,
            "path": str(gh),
            "release_url": GH_RELEASE_URL,
            "archive": archive.name,
            "archive_sha256": GH_ARCHIVE_SHA256,
        },
        "node": {"version": node_version, "path": str(node)},
        "npm": {"version": npm_version, "path": str(npm)},
        "codex": {"version": codex_version, "path": str(codex_js)},
        "uv": uv,
        "worker_runtime": worker_runtime,
        "python": {
            "version": python_version,
            "path": str(python),
            "requirements_lock_sha256": _sha256(requirements_lock),
            "dependencies": dependencies,
        },
        "model_launches": 0,
    }
    _atomic_json(receipt_path, receipt)
    if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
        raise UbuntuRuntimeError("Ubuntu runtime receipt read-back differs")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gh-archive", type=Path, required=True)
    parser.add_argument(
        "--checkout", type=Path,
        default=Path("/home/kgnote/.local/share/kgnote/work-items/goal-o2-reading-experience"),
    )
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--runtime-root", type=Path, default=Path("/home/kgnote/.local"))
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--reviewed-revision", required=True)
    parser.add_argument(
        "--receipt", type=Path,
        default=Path("/home/kgnote/.local/share/kgnote/runtime/ubuntu-worker-runtime-receipt.json"),
    )
    args = parser.parse_args()
    try:
        receipt = install(
            archive=args.gh_archive, checkout=args.checkout,
            expected_head=args.expected_head, runtime_root=args.runtime_root,
            release_root=args.release_root,
            runtime_manifest=args.runtime_manifest,
            reviewed_revision=args.reviewed_revision,
            receipt_path=args.receipt,
        )
    except (OSError, tarfile.TarError, UbuntuRuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
