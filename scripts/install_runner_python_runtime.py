#!/usr/bin/env python3
"""Install or verify one commit-bound Mac Runner Python runtime.

The installer never copies an existing virtual environment and never replaces an
existing destination.  The install report records exact package sources and
hashes; the read-back proves the Runner imports use the requested clean
deployment rather than a retired worktree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_SCHEMA = "kgnote.runner-python-runtime.v1"
LOCKFILE = "requirements-runtime.lock"
REQUIRED_IMPORTS = (
    "jsonschema",
    "yaml",
    "rfc3339_validator",
    "local_autonomy_runner",
    "goal_runner_adapter",
    "linux_worker_router",
    "epoch_scope_admission",
)


class RuntimeInstallError(RuntimeError):
    pass


def locked_packages(lock: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in lock.read_text(encoding="utf-8").splitlines():
        row = raw.strip()
        if not row or row.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", row)
        if match is None:
            raise RuntimeInstallError("runtime lockfile contains an unpinned or invalid requirement")
        normalized = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        if normalized in result:
            raise RuntimeInstallError("runtime lockfile contains a duplicate package")
        result[normalized] = match.group(2)
    if not result:
        raise RuntimeInstallError("runtime lockfile is empty")
    return result


def _probe_locked_packages(probe: dict[str, Any], expected: dict[str, str]) -> None:
    installed = {
        re.sub(r"[-_.]+", "-", str(name)).lower(): str(version)
        for name, version in probe.get("packages", {}).items()
    }
    mismatches = {
        name: {"expected": version, "observed": installed.get(name)}
        for name, version in expected.items()
        if installed.get(name) != version
    }
    if mismatches:
        raise RuntimeInstallError(
            "runtime package versions differ from the exact lock: "
            + json.dumps(mismatches, sort_keys=True)
        )


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "")[-1200:]
        raise RuntimeInstallError(f"command failed ({command[0]}): {detail}")
    return completed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *arguments: str) -> str:
    return _run(["/usr/bin/git", *arguments], cwd=repo).stdout.strip()


def repository_identity(repo: Path, expected_commit: str) -> dict[str, str]:
    if _git(repo, "rev-parse", "HEAD") != expected_commit:
        raise RuntimeInstallError("deployment repository HEAD differs from expected commit")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeInstallError("deployment repository must be clean")
    branch = _git(repo, "branch", "--show-current")
    if branch:
        raise RuntimeInstallError("deployment repository must be detached")
    return {
        "commit": expected_commit,
        "tree": _git(repo, "rev-parse", "HEAD^{tree}"),
        "git_common_dir": str(
            (repo / _git(repo, "rev-parse", "--git-common-dir")).resolve()
        ),
    }


def runtime_probe(
    python: Path,
    repo: Path,
    forbidden_prefixes: list[str],
) -> dict[str, Any]:
    source = (
        "import importlib, importlib.metadata, json, os, sys;"
        f"sys.path.insert(0,{str(repo / 'scripts')!r});"
        f"names={list(REQUIRED_IMPORTS)!r};"
        "mods={name:importlib.import_module(name).__file__ for name in names};"
        "packages={dist.metadata['Name']:dist.version for dist in importlib.metadata.distributions() if dist.metadata['Name']};"
        "print(json.dumps({'sys_executable':sys.executable,'sys_path':sys.path,'imports':mods,'packages':packages},sort_keys=True))"
    )
    completed = _run([str(python), "-I", "-c", source], cwd=repo)
    try:
        probe = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeInstallError("runtime probe did not return JSON") from exc
    executable = Path(str(probe.get("sys_executable", "")))
    if executable != python:
        raise RuntimeInstallError("runtime sys.executable differs from the installed interpreter")
    paths = [str(item) for item in probe.get("sys_path", [])]
    imported = [str(item) for item in probe.get("imports", {}).values()]
    for prefix in forbidden_prefixes:
        normalized = str(Path(prefix).resolve())
        if any(path == normalized or path.startswith(normalized + os.sep) for path in paths + imported):
            raise RuntimeInstallError(f"runtime imports or sys.path include forbidden prefix: {normalized}")
    scripts_root = str((repo / "scripts").resolve())
    for name in REQUIRED_IMPORTS[3:]:
        location = str(probe["imports"].get(name, ""))
        if not (location == scripts_root or location.startswith(scripts_root + os.sep)):
            raise RuntimeInstallError(f"runtime imported {name} outside the deployment")
    return probe


def validate_runtime_directory(destination: Path) -> dict[str, Any]:
    if destination.is_symlink() or not destination.is_dir():
        raise RuntimeInstallError("runtime destination must be a real directory")
    metadata = destination.lstat()
    if metadata.st_uid != os.geteuid() or metadata.st_gid != os.getegid():
        raise RuntimeInstallError("runtime destination owner differs from the deploying user")
    if stat.S_IMODE(metadata.st_mode) & 0o022:
        raise RuntimeInstallError("runtime destination must not be group/world writable")
    python = destination / "bin/python"
    if not python.exists() or not os.access(python, os.X_OK):
        raise RuntimeInstallError("runtime Python is missing or not executable")
    return {
        "owner_uid": metadata.st_uid,
        "owner_gid": metadata.st_gid,
        "mode": oct(stat.S_IMODE(metadata.st_mode)),
        "python": str(python),
        "python_realpath": str(python.resolve()),
    }


def install_runtime(
    *,
    repo: Path,
    destination: Path,
    base_python: Path,
    expected_commit: str,
    forbidden_prefixes: list[str],
) -> dict[str, Any]:
    repo = repo.resolve()
    destination = destination.absolute()
    base_python = base_python.resolve()
    identity = repository_identity(repo, expected_commit)
    lock = repo / LOCKFILE
    if not lock.is_file():
        raise RuntimeInstallError("pinned runtime lockfile is unavailable")
    expected_packages = locked_packages(lock)
    if destination.exists() or destination.is_symlink():
        raise RuntimeInstallError("runtime destination already exists; use --check instead of replacing it")
    if not base_python.is_file() or not os.access(base_python, os.X_OK):
        raise RuntimeInstallError("base Python is unavailable")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise RuntimeInstallError("runtime parent must be a real directory")
    _run([str(base_python), "-m", "venv", str(destination)], cwd=repo)
    os.chmod(destination, 0o755)
    runtime_python = destination / "bin/python"
    install_report = destination / "pip-install-report.json"
    _run(
        [
            str(runtime_python), "-m", "pip", "install",
            "--disable-pip-version-check", "--no-deps",
            "--report", str(install_report),
            "--requirement", str(lock),
        ],
        cwd=repo,
    )
    _run([str(runtime_python), "-m", "pip", "check"], cwd=repo)
    file_identity = validate_runtime_directory(destination)
    probe = runtime_probe(runtime_python, repo, forbidden_prefixes)
    _probe_locked_packages(probe, expected_packages)
    install_data = json.loads(install_report.read_text(encoding="utf-8"))
    sources = [
        {
            "name": row.get("metadata", {}).get("name"),
            "version": row.get("metadata", {}).get("version"),
            "url": row.get("download_info", {}).get("url"),
            "archive_hashes": row.get("download_info", {}).get("archive_info", {}).get("hashes", {}),
        }
        for row in install_data.get("install", [])
    ]
    receipt = {
        "schema_version": RUNTIME_SCHEMA,
        "status": "INSTALLED_VERIFIED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deployment_repository": str(repo),
        "deployment": identity,
        "lockfile": str(lock),
        "lockfile_sha256": _sha256(lock),
        "base_python": str(base_python),
        "base_python_version": _run([str(base_python), "--version"], cwd=repo).stdout.strip(),
        "runtime": file_identity,
        "runtime_python_version": _run([str(runtime_python), "--version"], cwd=repo).stdout.strip(),
        "pip_version": _run([str(runtime_python), "-m", "pip", "--version"], cwd=repo).stdout.strip(),
        "install_report": str(install_report),
        "install_report_sha256": _sha256(install_report),
        "package_sources": sources,
        "locked_packages": expected_packages,
        "probe": probe,
        "forbidden_prefixes": [str(Path(item).resolve()) for item in forbidden_prefixes],
        "rollback": "Restore the backed-up LaunchAgent plist and reload it; retain this runtime directory and receipt for audit.",
    }
    receipt_path = destination / "INSTALL_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def check_runtime(
    *, repo: Path, destination: Path, expected_commit: str,
    forbidden_prefixes: list[str],
) -> dict[str, Any]:
    identity = repository_identity(repo.resolve(), expected_commit)
    file_identity = validate_runtime_directory(destination)
    lock = repo.resolve() / LOCKFILE
    expected_packages = locked_packages(lock)
    receipt_path = destination / "INSTALL_RECEIPT.json"
    if not receipt_path.is_file():
        raise RuntimeInstallError("runtime install receipt is unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != RUNTIME_SCHEMA or receipt.get("deployment") != identity:
        raise RuntimeInstallError("runtime receipt deployment identity is stale")
    if (
        receipt.get("lockfile_sha256") != _sha256(lock)
        or receipt.get("locked_packages") != expected_packages
    ):
        raise RuntimeInstallError("runtime receipt lock identity is stale")
    normalized_forbidden = [str(Path(item).resolve()) for item in forbidden_prefixes]
    if receipt.get("forbidden_prefixes") != normalized_forbidden:
        raise RuntimeInstallError("runtime receipt forbidden-prefix policy is stale")
    install_report = Path(str(receipt.get("install_report", "")))
    if not install_report.is_file() or _sha256(install_report) != receipt.get("install_report_sha256"):
        raise RuntimeInstallError("runtime pip install report digest is stale")
    probe = runtime_probe(Path(file_identity["python"]), repo.resolve(), forbidden_prefixes)
    _probe_locked_packages(probe, expected_packages)
    _run([file_identity["python"], "-m", "pip", "check"], cwd=repo.resolve())
    return {
        "schema_version": RUNTIME_SCHEMA,
        "status": "READ_BACK_VERIFIED",
        "deployment": identity,
        "runtime": file_identity,
        "receipt_sha256": _sha256(receipt_path),
        "probe": probe,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--base-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--forbidden-prefix", action="append", default=[])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            result = check_runtime(
                repo=args.repo, destination=args.destination,
                expected_commit=args.expected_commit,
                forbidden_prefixes=args.forbidden_prefix,
            )
        else:
            result = install_runtime(
                repo=args.repo, destination=args.destination,
                base_python=args.base_python,
                expected_commit=args.expected_commit,
                forbidden_prefixes=args.forbidden_prefix,
            )
    except (OSError, ValueError, json.JSONDecodeError, RuntimeInstallError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
