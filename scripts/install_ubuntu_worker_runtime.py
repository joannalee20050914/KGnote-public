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
    runtime_root: Path, requirements_lock: Path, receipt_path: Path,
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
        "schema_version": "kgnote.ubuntu-worker-runtime-receipt.v1",
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
    parser.add_argument("--requirements-lock", type=Path, required=True)
    parser.add_argument(
        "--receipt", type=Path,
        default=Path("/home/kgnote/.local/share/kgnote/runtime/ubuntu-worker-runtime-receipt.json"),
    )
    args = parser.parse_args()
    try:
        receipt = install(
            archive=args.gh_archive, checkout=args.checkout,
            expected_head=args.expected_head, runtime_root=args.runtime_root,
            requirements_lock=args.requirements_lock,
            receipt_path=args.receipt,
        )
    except (OSError, tarfile.TarError, UbuntuRuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
