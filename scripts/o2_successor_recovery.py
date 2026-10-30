#!/usr/bin/env python3
"""One-time, append-only recovery for the exact O2 v4 attempt-1 successor.

This trusted operator helper never launches a model, publishes a branch, or
rewrites a prior event.  It validates the preserved attempt evidence and a new
O2 pre-publication verifier PASS before appending one idempotent
WORK_STATE_TRANSITION and advancing only the durable candidate/work-item state.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import plistlib
import re
import shlex
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import codex_control
import github_product_goal_control as github_control
import goal_continuity
import goal_runner_adapter
import install_runner_python_runtime
import product_goal_runtime_admission


ZONE = ZoneInfo("Asia/Taipei")
GOAL_ID = "GOAL-KGNOTE-O2-READING-EXPERIENCE"
GOAL_VERSION = "2026-10-29.4-bounded-trial-day0-proposal"
GOAL_SPEC_SHA256 = "7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f"
FORMAL_SPEC_FILE_SHA256 = "7e32c5000c6fc22d540db9afac3eb22679ca2ad5ae4de415067531485628549e"
FORMAL_STATE_SHA256 = "6c644af8ad65172dd3235e1f01fad429d11ea30864a823465bcfe226ac73f0ec"
FORMAL_LEDGER_SHA256 = "849301d3778faded3153101f318792ea390b109d7ff8f169e61c922bd9040328"
FORMAL_LEDGER_CURSOR = 8
INFRASTRUCTURE_BASE = "4388aa2a8d7c63cf2b81a7314176f646eec9a276"
DEPLOYMENT_EVIDENCE_SCHEMA = "kgnote.o2-successor-recovery-deployment.v1"
ATTEMPT_ID = "attempt-2026-10-29.4-bounded-trial-day0-proposal-WI-O2-A-IMPLEMENT-1"
WORK_ITEM_ID = "WI-O2-A-IMPLEMENT"
NEXT_WORK_ITEM_ID = "WI-O2-A-VERIFY"
ORIGINAL_COMMIT = "483f9e64066821d5d647d411e6da8ddb50ad88e5"
ORIGINAL_FINGERPRINT = "4fc43f5da4dc5af6037546b6c0e67ee22f6081bf8d509cae9a4f839d5dd240b4"
SUCCESSOR_COMMIT = "95d437a20ee31e48a49e2ee9b6f83ca3d4a931a6"
SUCCESSOR_TREE = "b2a66a296d2a76d8b79ce5343eb8447f6e9421ff"
SUCCESSOR_FINGERPRINT = "a08eccbee8f62560a8c5e279096b5a9befd94755b40e4b40f648e0ffa17a8904"
PRODUCT_BRANCH = "codex/o2-reading-experience"
OWNER_COMMENT_ID = 6490692466
OWNER_BODY_SHA256 = "0283409af9641e0b2fc16b53bcbcbd792906e30eacb72d4eea2420b7c1382b3d"
CHECKPOINT_SHA256 = "ce3ab4598ebf09b77c0dfe8d77073e090f6541cd6b6db3d34cd19d8cc7ad30dd"
BUNDLE_SHA256 = "08748df291a1038b76fe8afbe2c8264f627ef1ddd2b5091e296f653cf8c24874"
RECOVERY_EVENT_ID = f"{ATTEMPT_ID}-successor-recovery-{SUCCESSOR_COMMIT[:16]}"

RECOVERY_EVIDENCE_SHA256 = {
    "PRESERVATION_MANIFEST.md": "41c831ff86d9d3bdacdfea13dcd6ea16c1ec12af4b78c1fcba17011f2b6be78c",
    "ROOT_CAUSE_AND_RECOVERY_GAP.md": "6b978144f6c712f55d89e8ee4e3ba9d2cacff1b0901dd66c1ad0562d665a97f6",
    "formal/spec.json": FORMAL_SPEC_FILE_SHA256,
    "formal/state.json": FORMAL_STATE_SHA256,
    "formal/ledger.jsonl": FORMAL_LEDGER_SHA256,
    "formal/authorization/O2_V4_DAY0_AUTHORIZATION_PACKAGE_20261029.md": "6f060bca0db20ab9082029c3f23826ef360c477dbc60ccbb7028276abbf011d6",
    "formal/authorization/O2_V4_DEPLOYMENT_EVIDENCE_20261029.json": "6e20550299a68bae891efc729a9e573e6e959a7ec8db2f03731d0a5303b137af",
    "formal/authorization/O2_V4_NO_MODEL_ACCEPTANCE_20261029.json": "4aa87681a8c11e93e4e69a954ce580e33a773dcf836286939665bb34d9b4c2c4",
    "mac/order/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": "bd56771e3813f4f9e9f1978a87d04130d67d42e15caac8a7972bd5574a8a1d7d",
    "mac/context/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": "400cc84fedfc4152d9205a337f6cbb56fc0d5d0e7517e7a4092fd1475b5d6ff9",
    "mac/admission/0760a43e65015dfc925b494ffdc4a10e28815c9690666f05f687f1976bca650b.json": "f89babccb20a7b5473034616818773a4674a91d780487602f7866db3401a8d47",
    "mac/admission/o2-admission-b5dc61c13f6bb225.json": "4df9dc58af6ab071834a9b4773c7fa637796ab02345ebe4bf335dff45d047461",
    "mac/admission/o2-admission-b5dc61c13f6bb225.stdout.log": "487cec9af07d01bc45c3d27766c366aae7f81f98297236bace5f4779c7fcd9d4",
    "mac/admission/o2-admission-b5dc61c13f6bb225.stderr.log": "84abfbcdcbd0073c9d3052cd618e519737265b8a941ad5073a2e3907890afab3",
    "mac/checkpoint/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": CHECKPOINT_SHA256,
    "mac/checkpoint/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.stdout.log": "39ed33c32d60903910572e8b2a21afe6639d72a2ea948d237af38f695a8dfaa4",
    "mac/checkpoint/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.stderr.log": "67e3f69e69a0b8924b5f2d345c8faa3f5f64fdc01b9a1c7a82bad9411accb83f",
    "mac/runner/runner-at-snapshot.jsonl": "db6f40a12701452b169b58fbe76b2d5a9e39ab25b7a2f44f5edff6e900131acb",
    "mac/runner/launchd-at-snapshot.stdout.log": "dc7b444c04f123680627cf591848d97aabc44443c68be8bd16118a07a1f656af",
    "mac/runner/launchd-at-snapshot.stderr.log": "4d2685c889446d6d43da5049515df8d6395ac2e6ffb01b2fd27eb1637a287d4f",
    "ubuntu/git/o2-v4-attempt1-successor-95d437a.bundle": BUNDLE_SHA256,
    "ubuntu/git/0001-feat-add-source-bounded-prerequisite-reading-help.patch": "178ba6dc441469f2992102ad41f395504d2da5aac2978d723ea1695f3f2b48f0",
    "ubuntu/worker/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.stdout.log": "14aaf06577a91aba88825f42f47246ed42b1a76c4aa59fa3540fdc05be160d6b",
    "ubuntu/worker/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.stderr.log": "1613db98687afe58e622481956d68a66354f0adf0c762e70008bd486795fdc0a",
    "ubuntu/worker/evidence/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": "d238cc959aba6e47cf9ec7ac345ede832416f20ccdeb2c8d71fd3807b00c44e8",
    "ubuntu/worker/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": "385e6c6e439371d0ab5d34acf43b12743090c3e7f39470dc4e247820d5c04893",
    "ubuntu/worker/result/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json": "385e6c6e439371d0ab5d34acf43b12743090c3e7f39470dc4e247820d5c04893",
    "ubuntu/worker/verification-20261030T090613+0800.json": "51b13982e17b0e079a25c68f4fce460586ef910bd281a189641a56cd2525e2d8",
}


class RecoveryError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aware_timestamp(value: Any, description: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise RecoveryError(f"{description} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise RecoveryError(f"{description} must be timezone-aware")
    return parsed


def _load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{description} is unavailable or invalid") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{description} must be an object")
    return value


def validate_preserved_evidence(root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in RECOVERY_EVIDENCE_SHA256.items():
        path = root / relative
        if not path.is_file():
            raise RecoveryError(f"preserved evidence is missing: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise RecoveryError(f"preserved evidence SHA-256 drift: {relative}")
        observed[relative] = actual
    checkpoint = _load_json(
        root / "mac/checkpoint/o2-wi-o2-a-implement-codex-5b4a173c9ac48566.json",
        "preserved checkpoint",
    )
    if checkpoint.get("status") not in {"COMPLETED", "ALREADY_COMPLETED"}:
        raise RecoveryError("preserved checkpoint is not terminal")
    evidence = checkpoint.get("execution_evidence")
    result = evidence.get("product_goal_result") if isinstance(evidence, dict) else None
    if (
        not isinstance(result, dict)
        or result.get("attempt_id") != ATTEMPT_ID
        or result.get("result_state") != "FAILED"
        or result.get("failure_class") != "DETERMINISTIC_WORKER_FAILURE"
    ):
        raise RecoveryError("preserved checkpoint does not bind the exact failed attempt")
    return observed


def validate_bundle(bundle: Path) -> dict[str, str]:
    if sha256_file(bundle) != BUNDLE_SHA256:
        raise RecoveryError("successor bundle SHA-256 drift")
    with tempfile.TemporaryDirectory(prefix="kgnote-o2-recovery-bundle-") as directory:
        temporary = Path(directory)
        verifier = temporary / "verifier.git"
        initialized = subprocess.run(
            ["git", "init", "--bare", "--quiet", str(verifier)],
            capture_output=True,
            text=True,
            check=False,
        )
        verified = subprocess.run(
            ["git", "bundle", "verify", str(bundle)],
            cwd=verifier,
            capture_output=True,
            text=True,
            check=False,
        )
        if initialized.returncode or verified.returncode:
            raise RecoveryError("successor bundle verification failed")
        checkout = temporary / "checkout"
        cloned = subprocess.run(
            ["git", "clone", "--quiet", str(bundle), str(checkout)],
            capture_output=True,
            text=True,
            check=False,
        )
        if cloned.returncode:
            raise RecoveryError("successor bundle cannot be cloned for read-back")
        def git(*args: str) -> str:
            completed = subprocess.run(
                ["git", *args], cwd=checkout, capture_output=True, text=True, check=False
            )
            if completed.returncode:
                raise RecoveryError("successor bundle Git identity read-back failed")
            return completed.stdout.strip()
        commit = git("rev-parse", "HEAD")
        parent = git("rev-parse", "HEAD^")
        tree = git("rev-parse", "HEAD^{tree}")
        if git("status", "--porcelain=v1", "--untracked-files=all"):
            raise RecoveryError("successor bundle checkout is not clean")
        fingerprint = codex_control.repository_fingerprint(checkout)["value"]
    exact = {
        "commit": SUCCESSOR_COMMIT,
        "parent": ORIGINAL_COMMIT,
        "tree": SUCCESSOR_TREE,
        "fingerprint": SUCCESSOR_FINGERPRINT,
    }
    observed = {
        "commit": commit,
        "parent": parent,
        "tree": tree,
        "fingerprint": fingerprint,
    }
    if observed != exact:
        raise RecoveryError("successor bundle commit/parent/tree/fingerprint mismatch")
    return observed


def validate_verification_evidence(path: Path) -> tuple[dict[str, Any], str]:
    value = _load_json(path, "new O2 verification evidence")
    before = value.get("fingerprint_before")
    after = value.get("fingerprint_after")
    exact_identity = {
        "head": SUCCESSOR_COMMIT,
        "value": SUCCESSOR_FINGERPRINT,
    }
    if (
        value.get("schema_version") != "kgnote.verification-evidence.v1"
        or value.get("result") != "pass"
        or value.get("evidence_readback") is not True
        or value.get("fingerprint_stable") is not True
        or value.get("verification_profile") != codex_control.O2_PREPUBLICATION_PROFILE
        or not isinstance(before, dict)
        or not isinstance(after, dict)
        or any(before.get(key) != expected for key, expected in exact_identity.items())
        or any(after.get(key) != expected for key, expected in exact_identity.items())
    ):
        raise RecoveryError("new O2 verification does not pass exact identity/read-back")
    remote = value.get("remote_publication_identity")
    if not isinstance(remote, dict) or remote.get("required") is not True or remote.get("verified") is not False:
        raise RecoveryError("pre-publication verification must preserve the downstream remote identity gate")
    preflight = value.get("preflight")
    if (
        not isinstance(preflight, dict)
        or preflight.get("status") != "pass"
        or preflight.get("verification_profile") != codex_control.O2_PREPUBLICATION_PROFILE
    ):
        raise RecoveryError("new O2 verification preflight did not pass")
    gates = value.get("gates")
    if not isinstance(gates, list):
        raise RecoveryError("new O2 verification gates are missing")
    by_name = {
        row.get("name"): row
        for row in gates
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }
    required = {
        "requirements_guard",
        "requirements_guard_tests",
        "control_plane_negative_tests",
        "python_product_tests",
        "node_tests",
        "strict_git_diff_check",
        "o2_product_completion_gate",
        "review_completion_gate",
        "public_safety_scan",
        "untracked_whitespace",
    }
    missing_or_failed = sorted(
        name for name in required if by_name.get(name, {}).get("passed") is not True
    )
    if missing_or_failed:
        raise RecoveryError(
            "new O2 verification lacks passing required gates: " + ", ".join(missing_or_failed)
        )
    deferred = by_name["control_plane_negative_tests"].get("details")
    if (
        not isinstance(deferred, dict)
        or deferred.get("deferred_gate") != "trusted_remote_publication_identity"
        or deferred.get("deferred_tests")
        != list(codex_control.O2_DEFERRED_REMOTE_PUBLICATION_TESTS)
    ):
        raise RecoveryError("new O2 verification lacks the exact deferred remote-identity test set")
    return value, sha256_file(path)


def fetch_ubuntu_runtime_snapshot() -> dict[str, Any]:
    """Read the live immutable Ubuntu generation and its zero-model receipt."""
    source = (
        "import json,sys;"
        "sys.path.insert(0,'/home/kgnote/.local/share/kgnote/runtime/"
        ".worker-runtime-current');"
        "import product_goal_runtime_admission as admission;"
        "identity=admission.discover_runtime();"
        "receipt=json.load(open(identity['deployment_receipt_path'],encoding='utf-8'));"
        "print(json.dumps({'identity':identity,'receipt':receipt},sort_keys=True))"
    )
    completed = subprocess.run(
        ["ssh", "kgnote-ubuntu", f"/usr/bin/python3 -c {shlex.quote(source)}"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode:
        raise RecoveryError("live Ubuntu runtime read-back failed")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RecoveryError("live Ubuntu runtime read-back is not JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError("live Ubuntu runtime read-back must be an object")
    return value


def fetch_infrastructure_pull_request(number: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "/opt/homebrew/bin/gh", "pr", "view", str(number),
            "--repo", codex_control.O2_PRODUCT_REPOSITORY,
            "--json", "number,state,headRefOid,headRefName,baseRefName,mergeCommit,url",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode:
        raise RecoveryError("infrastructure PR live read-back failed")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RecoveryError("infrastructure PR live read-back is not JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError("infrastructure PR live read-back must be an object")
    return value


def _git_value(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )
    if completed.returncode:
        raise RecoveryError("deployed Mac Runner Git identity read-back failed")
    return completed.stdout.strip()


def validate_recovery_deployment_evidence(
    path: Path,
    *,
    ubuntu_fetcher: Callable[[], dict[str, Any]] = fetch_ubuntu_runtime_snapshot,
    github_fetcher: Callable[[int], dict[str, Any]] = fetch_infrastructure_pull_request,
) -> tuple[dict[str, Any], str]:
    """Require reviewed, merged, live Mac/Ubuntu deployment before append."""
    value = _load_json(path, "successor recovery deployment evidence")
    if (
        value.get("schema_version") != DEPLOYMENT_EVIDENCE_SCHEMA
        or value.get("status") != "PASS"
        or value.get("model_launches") != 0
    ):
        raise RecoveryError("successor recovery deployment evidence is not a zero-model PASS")
    infrastructure = value.get("infrastructure")
    mac = value.get("mac")
    ubuntu = value.get("ubuntu")
    if not all(isinstance(item, dict) for item in (infrastructure, mac, ubuntu)):
        raise RecoveryError("successor recovery deployment identities are incomplete")
    merged = str(infrastructure.get("merged_revision") or "")
    merged_tree = str(infrastructure.get("merged_tree") or "")
    if (
        infrastructure.get("base_revision") != INFRASTRUCTURE_BASE
        or re.fullmatch(r"[0-9a-f]{40}", merged) is None
        or re.fullmatch(r"[0-9a-f]{40}", merged_tree) is None
        or not isinstance(infrastructure.get("pull_request"), int)
        or infrastructure.get("pull_request", 0) < 1
        or re.fullmatch(r"[0-9a-f]{40}", str(infrastructure.get("reviewed_revision") or ""))
        is None
        or re.fullmatch(
            r"[0-9a-f]{64}", str(infrastructure.get("reviewed_fingerprint") or "")
        ) is None
        or re.fullmatch(
            r"[0-9a-f]{64}", str(infrastructure.get("claude_verdict_sha256") or "")
        ) is None
    ):
        raise RecoveryError("reviewed/merged infrastructure identity is invalid")
    live_pr = github_fetcher(infrastructure["pull_request"])
    if goal_continuity.canonical_json_bytes(live_pr) != goal_continuity.canonical_json_bytes(
        infrastructure.get("github_pull_request")
    ):
        raise RecoveryError("infrastructure PR evidence differs from live GitHub read-back")
    merge_commit = live_pr.get("mergeCommit")
    if (
        live_pr.get("state") != "MERGED"
        or live_pr.get("number") != infrastructure["pull_request"]
        or live_pr.get("headRefOid") != infrastructure["reviewed_revision"]
        or live_pr.get("baseRefName") != "main"
        or not isinstance(merge_commit, dict)
        or merge_commit.get("oid") != merged
    ):
        raise RecoveryError("infrastructure PR is not the exact normally merged candidate")

    runner_checkout = Path(str(mac.get("runner_checkout") or ""))
    runtime_destination = Path(str(mac.get("runner_python_destination") or ""))
    plist_path = Path(str(mac.get("launchagent_plist") or ""))
    forbidden = mac.get("forbidden_prefixes")
    if not isinstance(forbidden, list) or any(not isinstance(item, str) for item in forbidden):
        raise RecoveryError("Mac Runner forbidden-prefix policy is invalid")
    if (
        _git_value(runner_checkout, "rev-parse", "HEAD") != merged
        or _git_value(runner_checkout, "rev-parse", "HEAD^{tree}") != merged_tree
        or _git_value(runner_checkout, "status", "--porcelain=v1", "--untracked-files=all")
    ):
        raise RecoveryError("deployed Mac Runner checkout identity drift")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", INFRASTRUCTURE_BASE, merged],
        cwd=runner_checkout,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode:
        raise RecoveryError("deployed infrastructure is not descended from the authorized base")
    reviewed_ancestor = subprocess.run(
        [
            "git", "merge-base", "--is-ancestor",
            infrastructure["reviewed_revision"], merged,
        ],
        cwd=runner_checkout,
        capture_output=True,
        check=False,
    )
    if reviewed_ancestor.returncode:
        raise RecoveryError("merged infrastructure does not contain the reviewed PR candidate")
    observed_fingerprint = codex_control.repository_fingerprint(runner_checkout)
    if observed_fingerprint.get("head") != merged:
        raise RecoveryError("Mac Runner deployment fingerprint does not bind merged HEAD")
    try:
        runtime = install_runner_python_runtime.check_runtime(
            repo=runner_checkout,
            destination=runtime_destination,
            expected_commit=merged,
            forbidden_prefixes=forbidden,
        )
    except (OSError, install_runner_python_runtime.RuntimeInstallError) as exc:
        raise RecoveryError("deployed Mac Runner Python runtime read-back failed") from exc
    if runtime.get("receipt_sha256") != mac.get("runtime_receipt_sha256"):
        raise RecoveryError("Mac Runner runtime receipt SHA-256 drift")
    if not plist_path.is_file() or sha256_file(plist_path) != mac.get("launchagent_plist_sha256"):
        raise RecoveryError("Mac LaunchAgent plist SHA-256 drift")
    try:
        plist = plistlib.loads(plist_path.read_bytes())
    except (OSError, plistlib.InvalidFileException) as exc:
        raise RecoveryError("Mac LaunchAgent plist is invalid") from exc
    arguments = plist.get("ProgramArguments") if isinstance(plist, dict) else None
    expected_runner = str(runner_checkout / "scripts/local_autonomy_runner.py")
    if (
        not isinstance(plist, dict)
        or plist.get("Label") != "com.kgnote.local-autonomy-runner"
        or not isinstance(arguments, list)
        or str(runtime_destination / "bin/python") not in arguments
        or expected_runner not in arguments
    ):
        raise RecoveryError("Mac LaunchAgent does not point to the reviewed Runner runtime")

    live_ubuntu = ubuntu_fetcher()
    if goal_continuity.canonical_json_bytes(live_ubuntu) != goal_continuity.canonical_json_bytes(ubuntu):
        raise RecoveryError("live Ubuntu runtime differs from deployment evidence")
    identity = live_ubuntu.get("identity")
    receipt = live_ubuntu.get("receipt")
    try:
        product_goal_runtime_admission.validate_runtime_identity(identity)
    except product_goal_runtime_admission.RuntimeAdmissionError as exc:
        raise RecoveryError("live Ubuntu runtime identity is invalid") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version")
        != product_goal_runtime_admission.DEPLOYMENT_RECEIPT_SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("model_launches") != 0
        or receipt.get("checkout")
        != {
            "branch": PRODUCT_BRANCH,
            "head": SUCCESSOR_COMMIT,
            "tree": SUCCESSOR_TREE,
        }
        or identity.get("reviewed_revision") != merged
        or identity.get("reviewed_tree") != merged_tree
        or receipt.get("worker_runtime", {}).get("reviewed_revision") != merged
        or receipt.get("worker_runtime", {}).get("reviewed_source", {}).get("tree")
        != merged_tree
    ):
        raise RecoveryError("Ubuntu deployment does not bind exact infrastructure and successor")
    manifest_path = runner_checkout / "config/ubuntu-worker-runtime-manifest.json"
    if identity.get("manifest_sha256") != sha256_file(manifest_path):
        raise RecoveryError("Ubuntu runtime manifest differs from merged infrastructure")
    referenced_paths: dict[str, Path] = {}
    for label, path_field, sha_field in (
        (
            "infrastructure verification",
            "infrastructure_verification_path",
            "infrastructure_verification_sha256",
        ),
        ("Claude verdict", "claude_verdict_path", "claude_verdict_sha256"),
        (
            "successor verification",
            "successor_verification_path",
            "successor_verification_sha256",
        ),
        ("no-model acceptance", "no_model_acceptance_path", "no_model_acceptance_sha256"),
    ):
        referenced = Path(str(value.get(path_field) or ""))
        expected_sha = str(value.get(sha_field) or "")
        if (
            re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None
            or not referenced.is_file()
            or sha256_file(referenced) != expected_sha
        ):
            raise RecoveryError(f"{label} evidence SHA-256 drift")
        referenced_paths[label] = referenced
    if value["claude_verdict_sha256"] != infrastructure["claude_verdict_sha256"]:
        raise RecoveryError("infrastructure Claude verdict binding drift")
    verification = _load_json(
        referenced_paths["infrastructure verification"],
        "infrastructure verification evidence",
    )
    verification_before = verification.get("fingerprint_before")
    verification_after = verification.get("fingerprint_after")
    if (
        verification.get("result") != "pass"
        or verification.get("evidence_readback") is not True
        or verification.get("fingerprint_stable") is not True
        or not isinstance(verification_before, dict)
        or not isinstance(verification_after, dict)
        or verification_before.get("head") != infrastructure["reviewed_revision"]
        or verification_after.get("head") != infrastructure["reviewed_revision"]
        or verification_before.get("value") != infrastructure["reviewed_fingerprint"]
        or verification_after.get("value") != infrastructure["reviewed_fingerprint"]
    ):
        raise RecoveryError("infrastructure verification does not bind the reviewed candidate")
    claude = _load_json(referenced_paths["Claude verdict"], "Ubuntu Claude verdict")
    if (
        claude.get("schema_version")
        != "kgnote.o2-successor-recovery-infrastructure-review.v1"
        or claude.get("verdict") != "PASS"
        or claude.get("reviewer_role") != "UBUNTU_CLAUDE_REVIEWER"
        or claude.get("reviewed_revision") != infrastructure["reviewed_revision"]
        or claude.get("reviewed_fingerprint") != infrastructure["reviewed_fingerprint"]
        or claude.get("product_goal_review") is not False
    ):
        raise RecoveryError("Ubuntu Claude verdict does not bind the exact infrastructure candidate")
    successor_verification, successor_verification_sha256 = validate_verification_evidence(
        referenced_paths["successor verification"]
    )
    if successor_verification_sha256 != value["successor_verification_sha256"]:
        raise RecoveryError("deployed successor verification SHA-256 binding drift")
    acceptance = _load_json(
        referenced_paths["no-model acceptance"], "deployed no-model acceptance"
    )
    deployed_at = _aware_timestamp(value.get("deployed_at"), "deployment evidence deployed_at")
    verification_created_at = _aware_timestamp(
        successor_verification.get("created_at"), "successor verification created_at"
    )
    accepted_at = _aware_timestamp(acceptance.get("accepted_at"), "no-model acceptance accepted_at")
    if (
        acceptance.get("schema_version")
        != "kgnote.o2-successor-recovery-no-model-acceptance.v1"
        or acceptance.get("status") != "PASS"
        or acceptance.get("model_launches") != 0
        or acceptance.get("product_model_started") is not False
        or acceptance.get("runner_loaded") is not False
        or acceptance.get("candidate_commit") != SUCCESSOR_COMMIT
        or acceptance.get("candidate_fingerprint") != SUCCESSOR_FINGERPRINT
        or acceptance.get("infrastructure_merged_revision") != merged
        or acceptance.get("runtime_generation_id") != identity.get("generation_id")
        or acceptance.get("runtime_manifest_sha256") != identity.get("manifest_sha256")
        or acceptance.get("successor_verification_sha256")
        != successor_verification_sha256
        or acceptance.get("successor_verification_created_at")
        != successor_verification.get("created_at")
        or verification_created_at < deployed_at
        or accepted_at < verification_created_at
    ):
        raise RecoveryError("deployed no-model acceptance is incomplete or stale")
    return value, sha256_file(path)


def resolve_live_authority(
    spec: dict[str, Any],
    *,
    comments_fetcher: Callable[[dict[str, Any]], list[dict[str, Any]]] = github_control.fetch_issue_comments,
) -> dict[str, Any]:
    authority = github_control.resolve_authority(comments_fetcher(spec), spec)
    record = authority.get("record")
    if (
        authority.get("authority_lease") != "ACTIVE"
        or authority.get("status") not in {"APPROVED", "ACTIVE"}
        or not isinstance(record, dict)
        or record.get("action") != "APPROVE"
        or record.get("comment_id") != OWNER_COMMENT_ID
        or record.get("body_sha256") != OWNER_BODY_SHA256
        or record.get("author_association") != "OWNER"
        or record.get("goal_version") != GOAL_VERSION
        or record.get("goal_spec_sha256") != GOAL_SPEC_SHA256
    ):
        raise RecoveryError("live Owner authority drifted from the exact accepted APPROVE")
    return authority


def _validate_formal_preconditions(
    spec: dict[str, Any],
    state: dict[str, Any],
    ledger: list[dict[str, Any]],
    authority: dict[str, Any],
) -> None:
    if (
        spec.get("goal_id") != GOAL_ID
        or spec.get("goal_version") != GOAL_VERSION
        or goal_continuity.goal_spec_sha256(spec) != GOAL_SPEC_SHA256
    ):
        raise RecoveryError("formal Goal identity/spec digest drift")
    goal_continuity.validate_runner_state(state, spec)
    goal_continuity.validate_ledger_binding(ledger, state, spec)
    if state.get("event_cursor", {}).get("sequence") != FORMAL_LEDGER_CURSOR or len(ledger) != FORMAL_LEDGER_CURSOR:
        raise RecoveryError("formal ledger cursor drift")
    if state.get("authority_lease") != "ACTIVE" or state.get("lifecycle", {}).get("state") != "ACTIVE":
        raise RecoveryError("formal Goal authority/lifecycle is not ACTIVE")
    if state.get("authority_record") != authority.get("record"):
        raise RecoveryError("formal authority record differs from live Owner authority")
    projection = goal_continuity.reduce_ledger(ledger)
    if goal_runner_adapter._go_live_receipt(projection, authority, state, spec) is None:
        raise RecoveryError("exact go-live receipt no longer reads back")
    reservation = projection.get("dispatch_reservations", {}).get(ATTEMPT_ID)
    attempt = projection.get("model_attempts", {}).get(ATTEMPT_ID)
    if (
        not isinstance(reservation, dict)
        or reservation.get("reconciled") is not True
        or reservation.get("logical_work_id") != WORK_ITEM_ID
        or reservation.get("outcome") != "DETERMINISTIC_WORKER_FAILURE"
        or reservation.get("checkpoint_sha256") != CHECKPOINT_SHA256
        or not isinstance(attempt, dict)
        or attempt.get("started") is not True
        or attempt.get("finished") is not True
        or attempt.get("failure_class") != "DETERMINISTIC_WORKER_FAILURE"
    ):
        raise RecoveryError("formal attempt/reservation/checkpoint history mismatch")
    candidate = state.get("candidate_identity")
    if candidate != {
        "commit": ORIGINAL_COMMIT,
        "fingerprint": ORIGINAL_FINGERPRINT,
        "branch": PRODUCT_BRANCH,
        "pull_request": None,
    }:
        raise RecoveryError("formal original candidate identity drift")
    work = next((row for row in state["work_items"] if row["work_item_id"] == WORK_ITEM_ID), None)
    if (
        not isinstance(work, dict)
        or work.get("status") != "PLANNED"
        or work.get("attempts") != 1
        or work.get("active_attempt_id") is not None
        or work.get("failure_counts", {}).get("DETERMINISTIC_WORKER_FAILURE") != 1
    ):
        raise RecoveryError("formal failed Work Item history drift")
    accounting = state.get("resource_accounting", {}).get("codex", {})
    if accounting.get("total_launches") != 4:
        raise RecoveryError("formal Codex accounting is not exactly 4/5")
    if state.get("runtime_block") is not None:
        raise RecoveryError("formal runtime block must already be reconciled and released")


def _validate_recovered_state(state: dict[str, Any]) -> None:
    candidate = state.get("candidate_identity")
    if candidate != {
        "commit": SUCCESSOR_COMMIT,
        "fingerprint": SUCCESSOR_FINGERPRINT,
        "branch": PRODUCT_BRANCH,
        "pull_request": None,
    }:
        raise RecoveryError("recovered candidate identity is not exact")
    implement = next(row for row in state["work_items"] if row["work_item_id"] == WORK_ITEM_ID)
    verify = next(row for row in state["work_items"] if row["work_item_id"] == NEXT_WORK_ITEM_ID)
    if (
        implement.get("status") != "VERIFIED"
        or implement.get("attempts") != 1
        or implement.get("failure_counts", {}).get("DETERMINISTIC_WORKER_FAILURE") != 1
        or verify.get("status") != "PLANNED"
        or state.get("resource_accounting", {}).get("codex", {}).get("total_launches") != 4
    ):
        raise RecoveryError("recovered Work Item/accounting state is not exact")


def _recovery_payload(
    *,
    bundle_identity: dict[str, Any],
    evidence_hashes: dict[str, str],
    verification_sha256: str,
    deployment_evidence_sha256: str,
    infrastructure_merged_revision: str,
    state_patch: dict[str, Any],
) -> dict[str, Any]:
    return {
        "operation": "VERIFIED_SUCCESSOR_RECOVERED",
        "original_attempt_outcome": "DETERMINISTIC_WORKER_FAILURE",
        "original_candidate": {
            "commit": ORIGINAL_COMMIT,
            "fingerprint": ORIGINAL_FINGERPRINT,
        },
        "successor": bundle_identity,
        "bundle_sha256": BUNDLE_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "verification_evidence_sha256": verification_sha256,
        "deployment_evidence_sha256": deployment_evidence_sha256,
        "infrastructure_merged_revision": infrastructure_merged_revision,
        "pre_recovery_state_sha256": FORMAL_STATE_SHA256,
        "pre_recovery_ledger_sha256": FORMAL_LEDGER_SHA256,
        "pre_recovery_ledger_cursor": FORMAL_LEDGER_CURSOR,
        "authority_comment_id": OWNER_COMMENT_ID,
        "authority_body_sha256": OWNER_BODY_SHA256,
        "codex_total_launches": 4,
        "codex_ceiling": 5,
        "next_work_item_id": NEXT_WORK_ITEM_ID,
        "evidence_manifest": evidence_hashes,
        "state_patch": state_patch,
    }


def _ledger_prefix_sha256(ledger: list[dict[str, Any]], count: int) -> str:
    content = b"".join(
        goal_continuity.canonical_json_bytes(event) + b"\n" for event in ledger[:count]
    )
    return hashlib.sha256(content).hexdigest()


def runner_is_stopped(label: str = "com.kgnote.local-autonomy-runner") -> bool:
    completed = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode != 0


def recover_successor(
    *,
    spec_path: Path,
    state_path: Path,
    ledger_path: Path,
    evidence_root: Path,
    verification_path: Path,
    deployment_evidence_path: Path,
    apply: bool,
    occurred_at: datetime,
    comments_fetcher: Callable[[dict[str, Any]], list[dict[str, Any]]] = github_control.fetch_issue_comments,
    runner_stopped_checker: Callable[[], bool] = runner_is_stopped,
    ubuntu_fetcher: Callable[[], dict[str, Any]] = fetch_ubuntu_runtime_snapshot,
) -> dict[str, Any]:
    if occurred_at.tzinfo is None:
        raise RecoveryError("recovery time must be timezone-aware")
    if not runner_stopped_checker():
        raise RecoveryError("formal Runner must remain unloaded during successor recovery")
    deployment, deployment_evidence_sha256 = validate_recovery_deployment_evidence(
        deployment_evidence_path,
        ubuntu_fetcher=ubuntu_fetcher,
    )
    spec = goal_continuity.load_json(spec_path)
    authority = resolve_live_authority(spec, comments_fetcher=comments_fetcher)
    evidence_hashes = validate_preserved_evidence(evidence_root)
    bundle_identity = validate_bundle(
        evidence_root / "ubuntu/git/o2-v4-attempt1-successor-95d437a.bundle"
    )
    _verification, verification_sha256 = validate_verification_evidence(verification_path)
    if (
        Path(str(deployment.get("successor_verification_path") or "")).resolve()
        != verification_path.resolve()
        or deployment.get("successor_verification_sha256") != verification_sha256
    ):
        raise RecoveryError("CLI successor verification differs from deployed generation evidence")
    ledger = goal_continuity.read_ledger(ledger_path)
    existing = next((row for row in ledger if row["event_id"] == RECOVERY_EVENT_ID), None)
    if existing is not None:
        if (
            len(ledger) != FORMAL_LEDGER_CURSOR + 1
            or existing.get("sequence") != FORMAL_LEDGER_CURSOR + 1
            or ledger[-1].get("event_id") != RECOVERY_EVENT_ID
            or _ledger_prefix_sha256(ledger, FORMAL_LEDGER_CURSOR) != FORMAL_LEDGER_SHA256
            or existing.get("event_type") != "WORK_STATE_TRANSITION"
            or existing.get("attempt_id") != ATTEMPT_ID
            or existing.get("logical_work_id") != WORK_ITEM_ID
        ):
            raise RecoveryError("existing recovery event conflicts with exact recovery identity")
        stored_payload = existing.get("payload")
        stored_patch = stored_payload.get("state_patch") if isinstance(stored_payload, dict) else None
        expected_payload = _recovery_payload(
            bundle_identity=bundle_identity,
            evidence_hashes=evidence_hashes,
            verification_sha256=verification_sha256,
            deployment_evidence_sha256=deployment_evidence_sha256,
            infrastructure_merged_revision=deployment["infrastructure"]["merged_revision"],
            state_patch=stored_patch,
        )
        if goal_continuity.canonical_json_bytes(stored_payload) != (
            goal_continuity.canonical_json_bytes(expected_payload)
        ):
            raise RecoveryError("existing recovery event conflicts with exact recovery identity")
        try:
            state = goal_runner_adapter.synchronize_state_from_ledger(
                spec,
                goal_continuity.load_json(state_path),
                ledger,
                state_path=state_path if apply else None,
            )
        except (goal_continuity.GoalContractError, goal_runner_adapter.GoalRunnerError) as exc:
            raise RecoveryError("existing recovery event/state replay is invalid") from exc
        _validate_recovered_state(state)
        expected_payload = _recovery_payload(
            bundle_identity=bundle_identity,
            evidence_hashes=evidence_hashes,
            verification_sha256=verification_sha256,
            deployment_evidence_sha256=deployment_evidence_sha256,
            infrastructure_merged_revision=deployment["infrastructure"]["merged_revision"],
            state_patch=goal_runner_adapter._state_patch(state),
        )
        if goal_continuity.canonical_json_bytes(existing.get("payload")) != (
            goal_continuity.canonical_json_bytes(expected_payload)
        ):
            raise RecoveryError("existing recovery event conflicts with exact recovery identity")
        return {
            "status": "SUCCESSOR_ALREADY_RECOVERED",
            "appended": False,
            "event_id": RECOVERY_EVENT_ID,
            "ledger_cursor": state["event_cursor"]["sequence"],
            "candidate": deepcopy(state["candidate_identity"]),
        }
    if sha256_file(spec_path) != FORMAL_SPEC_FILE_SHA256:
        raise RecoveryError("formal spec file SHA-256 drift")
    if sha256_file(state_path) != FORMAL_STATE_SHA256:
        raise RecoveryError("formal state SHA-256 drift")
    if sha256_file(ledger_path) != FORMAL_LEDGER_SHA256:
        raise RecoveryError("formal ledger SHA-256 drift")
    state = goal_continuity.load_json(state_path)
    _validate_formal_preconditions(spec, state, ledger, authority)
    if not apply:
        return {
            "status": "RECOVERY_READY",
            "appended": False,
            "event_id": RECOVERY_EVENT_ID,
            "ledger_cursor": FORMAL_LEDGER_CURSOR,
            "candidate": bundle_identity,
            "verification_evidence_sha256": verification_sha256,
            "deployment_evidence_sha256": deployment_evidence_sha256,
        }
    if not runner_stopped_checker():
        raise RecoveryError("formal Runner restarted before recovery append")
    updated = deepcopy(state)
    work = next(row for row in updated["work_items"] if row["work_item_id"] == WORK_ITEM_ID)
    work["status"] = "VERIFIED"
    work["active_attempt_id"] = None
    updated["candidate_identity"] = {
        "commit": SUCCESSOR_COMMIT,
        "fingerprint": SUCCESSOR_FINGERPRINT,
        "branch": PRODUCT_BRANCH,
        "pull_request": None,
    }
    updated.pop("runtime_block", None)
    payload = _recovery_payload(
        bundle_identity=bundle_identity,
        evidence_hashes=evidence_hashes,
        verification_sha256=verification_sha256,
        deployment_evidence_sha256=deployment_evidence_sha256,
        infrastructure_merged_revision=deployment["infrastructure"]["merged_revision"],
        state_patch=goal_runner_adapter._state_patch(updated),
    )
    event, appended = goal_continuity.append_ledger_event(
        ledger_path,
        event_id=RECOVERY_EVENT_ID,
        event_type="WORK_STATE_TRANSITION",
        occurred_at=occurred_at.isoformat(timespec="seconds"),
        goal_id=GOAL_ID,
        goal_version=GOAL_VERSION,
        logical_work_id=WORK_ITEM_ID,
        attempt_id=ATTEMPT_ID,
        payload=payload,
    )
    if not appended:
        raise RecoveryError("recovery event appeared concurrently; rerun for exact read-back")
    updated["event_cursor"] = {
        "sequence": event["sequence"],
        "event_sha256": event["event_sha256"],
    }
    goal_continuity.validate_runner_state(updated, spec)
    _validate_recovered_state(updated)
    goal_continuity.atomic_write_json(state_path, updated)
    readback = goal_runner_adapter.synchronize_state_from_ledger(
        spec,
        goal_continuity.load_json(state_path),
        goal_continuity.read_ledger(ledger_path),
    )
    _validate_recovered_state(readback)
    return {
        "status": "SUCCESSOR_RECOVERED",
        "appended": True,
        "event_id": event["event_id"],
        "event_sha256": event["event_sha256"],
        "ledger_cursor": readback["event_cursor"]["sequence"],
        "candidate": deepcopy(readback["candidate_identity"]),
        "verification_evidence_sha256": verification_sha256,
        "deployment_evidence_sha256": deployment_evidence_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--deployment-evidence", type=Path, required=True)
    parser.add_argument("--writer-lock", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    args.writer_lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.writer_lock.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            result = recover_successor(
                spec_path=args.spec,
                state_path=args.state,
                ledger_path=args.ledger,
                evidence_root=args.evidence_root,
                verification_path=args.verification,
                deployment_evidence_path=args.deployment_evidence,
                apply=args.apply,
                occurred_at=datetime.now(ZONE),
            )
    except (RecoveryError, goal_continuity.GoalContractError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
