#!/usr/bin/env python3
"""Trusted O2 worker-lane entrypoint used inside the Linux worker sandbox.

The Runner selects the lane from the immutable Work Item.  This helper only
materializes the fixed inputs required by existing Codex, verifier, publisher,
and Claude entrypoints; it does not accept free-form shell commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

import codex_control
from claude_reviewer_adapter import (
    AdapterError,
    CLAUDE_SCHEMA_PROJECTION_VERSION,
    FORMAL_REVIEW_SCHEMA_SHA256,
    WorkOrder,
    build_claude_schema_projection,
    execute as execute_claude,
)
from product_goal_worker_result import CONTEXT_SCHEMA, WorkerResultError, validate_context


MODES = {"codex", "verify", "publish", "review"}
GUEST_NODE_BIN = "/home/kgnote/.local/lib/node-v24.12.0/bin"
GUEST_NODE = f"{GUEST_NODE_BIN}/node"
GUEST_NPM = f"{GUEST_NODE_BIN}/npm"
GUEST_GH = "/home/kgnote/.local/bin/gh"
GUEST_GH_VERSION = "2.103.2"
GUEST_CODEX_JS = "/home/kgnote/.local/lib/node-v24.12.0/lib/node_modules/@openai/codex/bin/codex.js"
GUEST_PYTHON_VERSION = "Python 3.12.3"
GUEST_NODE_VERSION = "v24.12.0"
GUEST_NPM_VERSION = "11.6.2"
GUEST_CODEX_VERSION = "codex-cli 0.146.0"


class LaneError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


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


def _run(
    command: list[str], *, cwd: Path,
    env: dict[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _prepare_verifier_environment(repo: Path) -> None:
    """Use deployed guest tools without depending on an untracked repo venv."""
    if not (repo / ".venv/bin/python").is_file():
        os.environ.setdefault("KGNOTE_TEST_PYTHON", "/usr/bin/python3")
    current_path = os.environ.get("PATH", "/usr/bin:/bin")
    if GUEST_NODE_BIN not in current_path.split(":"):
        os.environ["PATH"] = f"{GUEST_NODE_BIN}:{current_path}"


def _emit_child(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n", file=sys.stderr)


def _exact_candidate(repo: Path, context: dict[str, Any]) -> dict[str, Any]:
    fingerprint = codex_control.repository_fingerprint(repo)
    branch = subprocess.run(
        ["/usr/bin/git", "branch", "--show-current"], cwd=repo,
        text=True, capture_output=True, check=False,
    )
    if branch.returncode or branch.stdout.strip() != context.get("branch"):
        raise LaneError("worker checkout branch differs from the sealed context")
    return {
        "commit": fingerprint["head"], "fingerprint": fingerprint["value"],
        "branch": branch.stdout.strip(), "pull_request": context.get("pull_request"),
    }


def _probe(command: list[str], *, repo: Path) -> str:
    environment = dict(os.environ)
    environment["PATH"] = f"{GUEST_NODE_BIN}:/home/kgnote/.local/bin:/usr/bin:/bin"
    completed = subprocess.run(
        command, cwd=repo, env=environment, text=True, capture_output=True,
        timeout=30, check=False,
    )
    if completed.returncode:
        raise LaneError(f"development environment probe failed: {Path(command[0]).name}")
    return completed.stdout.strip() or completed.stderr.strip()


def admit_codex_development_environment(
    repo: Path, context: dict[str, Any], evidence_path: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Prove the exact checkout and toolchain before invoking Codex."""
    context = validate_context(context)
    if context.get("schema_version") != CONTEXT_SCHEMA:
        raise LaneError("Codex development admission requires Runner-verified context v2")
    candidate = _exact_candidate(repo, context)
    if (
        candidate["commit"] != context["candidate_commit"]
        or candidate["fingerprint"] != context["candidate_fingerprint"]
    ):
        raise LaneError("pre-model checkout differs from the sealed Runner context")
    python = repo / ".venv/bin/python"
    required = {
        "python": python,
        "node": Path(GUEST_NODE),
        "npm": Path(GUEST_NPM),
        "gh": Path(GUEST_GH),
        "git": Path("/usr/bin/git"),
        "codex_js": Path(GUEST_CODEX_JS),
    }
    missing = [name for name, path in required.items() if not path.is_file() or not os.access(path, os.X_OK if name != "codex_js" else os.R_OK)]
    if missing:
        raise LaneError("development environment is incomplete: " + ", ".join(sorted(missing)))
    versions = {
        "python": _probe([str(python), "--version"], repo=repo),
        "node": _probe([GUEST_NODE, "--version"], repo=repo),
        "npm": _probe([GUEST_NPM, "--version"], repo=repo),
        "gh": _probe([GUEST_GH, "--version"], repo=repo).splitlines()[0],
        "git": _probe(["/usr/bin/git", "--version"], repo=repo),
        "codex": _probe([GUEST_NODE, GUEST_CODEX_JS, "--version"], repo=repo),
    }
    if (
        versions["python"] != GUEST_PYTHON_VERSION
        or versions["node"] != GUEST_NODE_VERSION
        or versions["npm"] != GUEST_NPM_VERSION
        or versions["codex"] != GUEST_CODEX_VERSION
        or not versions["gh"].startswith(f"gh version {GUEST_GH_VERSION}")
    ):
        raise LaneError("development environment version differs from the pinned runtime")
    dependency_probe = _probe(
        [
            str(python), "-c",
            "import jsonschema,yaml; print(jsonschema.__version__ + ':' + yaml.__version__)",
        ],
        repo=repo,
    )
    context_path = evidence_path.parent.parent / "contexts" / f"{context['order_event_id']}.json"
    admission_path = evidence_path.parent.parent / "admissions" / f"{context['order_event_id']}.json"
    _atomic_json(context_path, context)
    receipt = {
        "schema_version": "kgnote.codex-development-environment-admission.v1",
        "status": "PASS",
        "order_event_id": context["order_event_id"],
        "attempt_id": context["attempt_id"],
        "candidate": candidate,
        "runner_context_sha256": hashlib.sha256(_canonical(context["runner_context"])).hexdigest(),
        "context_path": str(context_path),
        "context_sha256": hashlib.sha256(context_path.read_bytes()).hexdigest(),
        "versions": versions,
        "dependency_probe": dependency_probe,
    }
    _atomic_json(admission_path, receipt)
    child_env = dict(os.environ)
    child_env.update({
        "KGNOTE_PRODUCT_GOAL_CONTEXT": str(context_path),
        "KGNOTE_PRODUCT_GOAL_CONTEXT_SHA256": receipt["context_sha256"],
        "KGNOTE_TEST_PYTHON": str(python),
        "PATH": f"{python.parent}:/home/kgnote/.local/bin:{GUEST_NODE_BIN}:/usr/bin:/bin",
    })
    return receipt, child_env


def run_codex(
    repo: Path, context: dict[str, Any], evidence_path: Path, command: list[str],
    *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    verifier: Callable[[Path], tuple[dict[str, Any], int]] = codex_control.verify,
    admitter: Callable[[Path, dict[str, Any], Path], tuple[dict[str, Any], dict[str, str]]] = admit_codex_development_environment,
) -> int:
    if not command or command[0] != "/home/kgnote/.local/bin/kgnote-successor-codex":
        raise LaneError("Codex lane command is not the fixed successor entrypoint")
    try:
        admission, child_env = admitter(repo, context, evidence_path)
    except (OSError, WorkerResultError, LaneError) as exc:
        _atomic_json(evidence_path, {
            "schema_version": "kgnote.codex-product-goal-result.v1",
            "status": "BLOCKED",
            "failure_class": "WORKER_ENVIRONMENT_ADMISSION_FAILED",
            "classification_evidence": {
                "source": "trusted_pre_model_environment_admission",
                "error_type": type(exc).__name__,
                "error_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
            },
        })
        raise
    completed = _run(command, cwd=repo, env=child_env, runner=runner)
    _emit_child(completed)
    if completed.returncode:
        return completed.returncode
    candidate = _exact_candidate(repo, context)
    if candidate["commit"] == context["candidate_commit"]:
        raise LaneError("Codex returned without creating a successor commit")
    _prepare_verifier_environment(repo)
    verification, verify_code = verifier(repo)
    artifact = {
        "schema_version": "kgnote.codex-product-goal-result.v1",
        "status": "COMPLETED" if verify_code == 0 else "FAILED_CLOSED",
        "candidate_parent": context["candidate_commit"],
        "candidate_commit": candidate["commit"],
        "candidate_fingerprint": candidate["fingerprint"],
        "branch": candidate["branch"], "pull_request": candidate["pull_request"],
        "verification": {
            "status": "PASS" if verify_code == 0 else "FAIL",
            "verification_id": verification.get("verification_id"),
            "evidence_path": verification.get("evidence_path"),
            "evidence_sha256": hashlib.sha256(_canonical(verification)).hexdigest(),
        },
        "environment_admission": {
            "status": admission["status"],
            "context_sha256": admission["context_sha256"],
            "runner_context_sha256": admission["runner_context_sha256"],
            "versions": admission["versions"],
        },
    }
    _atomic_json(evidence_path, artifact)
    return verify_code


def run_verify(
    repo: Path, context: dict[str, Any], evidence_path: Path, *,
    verifier: Callable[[Path], tuple[dict[str, Any], int]] = codex_control.verify,
) -> int:
    candidate = _exact_candidate(repo, context)
    if (
        candidate["commit"] != context["candidate_commit"]
        or candidate["fingerprint"] != context["candidate_fingerprint"]
    ):
        raise LaneError("verification checkout differs from the sealed candidate")
    _prepare_verifier_environment(repo)
    evidence, code = verifier(repo)
    _atomic_json(evidence_path, evidence)
    return code


def run_publish(
    repo: Path, context: dict[str, Any], evidence_path: Path, *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    github_reader: Callable[[str, int], dict[str, Any]] | None = None,
    branch_reader: Callable[[str, str], dict[str, Any]] | None = None,
) -> int:
    candidate = _exact_candidate(repo, context)
    if (
        candidate["commit"] != context["candidate_commit"]
        or candidate["fingerprint"] != context["candidate_fingerprint"]
    ):
        raise LaneError("publication checkout differs from the sealed candidate")
    pull_request = context.get("pull_request")
    if pull_request is not None and (
        not isinstance(pull_request, int) or isinstance(pull_request, bool) or pull_request < 1
    ):
        raise LaneError("publication pull request identity is invalid")
    push = _run(
        [
            "/usr/bin/git", "push",
            f"git@github.com:{context['repository']}.git",
            f"HEAD:refs/heads/{context['branch']}",
        ],
        cwd=repo, runner=runner,
    )
    _emit_child(push)
    if push.returncode:
        return push.returncode
    if pull_request is None:
        if branch_reader is None:
            branch_reader = _github_branch_snapshot
        observed = branch_reader(str(context["repository"]), candidate["branch"])
        if observed.get("headRefOid") != candidate["commit"]:
            raise LaneError("GitHub branch read-back differs from the exact candidate")
        status = "PUBLISHED"
    else:
        if github_reader is None:
            github_reader = _github_pr_snapshot
        observed = github_reader(str(context["repository"]), pull_request)
        if (
            observed.get("headRefOid") != candidate["commit"]
            or observed.get("headRefName") != candidate["branch"]
            or observed.get("state") != "OPEN"
        ):
            raise LaneError("GitHub publication read-back differs from the exact candidate")
        status = "READ_BACK_VERIFIED"
    receipt = {
        "repository": context["repository"], "pull_request": pull_request,
        "candidate": candidate, "github": observed,
    }
    _atomic_json(evidence_path, {
        "schema_version": "kgnote.product-goal-publication-result.v1",
        "status": status,
        "candidate_commit": candidate["commit"],
        "candidate_fingerprint": candidate["fingerprint"],
        "branch": candidate["branch"], "pull_request": pull_request,
        "receipt_sha256": hashlib.sha256(_canonical(receipt)).hexdigest(),
        "artifact_url": observed.get("url"),
    })
    return 0


def _github_pr_snapshot(repository: str, pull_request: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/pulls/{pull_request}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "KGnote-product-goal-publisher/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise LaneError("GitHub publication read-back failed") from exc
    if not isinstance(raw, dict):
        raise LaneError("GitHub publication read-back is not an object")
    head = raw.get("head") if isinstance(raw.get("head"), dict) else {}
    return {
        "headRefOid": head.get("sha"), "headRefName": head.get("ref"),
        "state": str(raw.get("state", "")).upper(),
        "isDraft": raw.get("draft"), "url": raw.get("html_url"),
    }


def _github_branch_snapshot(repository: str, branch: str) -> dict[str, Any]:
    quoted_branch = urllib.parse.quote(branch, safe="")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/branches/{quoted_branch}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "KGnote-product-goal-publisher/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise LaneError("GitHub branch read-back failed") from exc
    if not isinstance(raw, dict):
        raise LaneError("GitHub branch read-back is not an object")
    commit = raw.get("commit") if isinstance(raw.get("commit"), dict) else {}
    return {"headRefOid": commit.get("sha"), "headRefName": raw.get("name")}


def run_review(
    repo: Path, context: dict[str, Any], evidence_path: Path, *,
    executor: Callable[[WorkOrder], dict[str, Any]] = execute_claude,
    runtime_paths: dict[str, str] | None = None,
) -> int:
    candidate = _exact_candidate(repo, context)
    if (
        candidate["commit"] != context["candidate_commit"]
        or candidate["fingerprint"] != context["candidate_fingerprint"]
    ):
        raise LaneError("review checkout differs from the sealed candidate")
    pull_request = context.get("pull_request")
    if not isinstance(pull_request, int) or isinstance(pull_request, bool) or pull_request < 1:
        raise LaneError("review requires an existing exact pull request")
    used = context.get("total_launches_before")
    limit = context.get("max_total_launches")
    if not isinstance(used, int) or not isinstance(limit, int) or not 0 <= used < limit:
        raise LaneError("review launch accounting is missing or exhausted")
    try:
        _, projection = build_claude_schema_projection()
    except AdapterError as exc:
        raise LaneError(f"formal Claude schema projection failed: {exc}") from exc
    if (
        projection.get("formal_schema_sha256") != FORMAL_REVIEW_SCHEMA_SHA256
        or projection.get("projection_version") != CLAUDE_SCHEMA_PROJECTION_VERSION
        or not isinstance(projection.get("claude_facing_schema_sha256"), str)
    ):
        raise LaneError("formal Claude schema projection metadata is inconsistent")
    checkpoint = evidence_path.with_name(evidence_path.stem + "-claude-checkpoint.json")
    paths = {
        "agent_loop": "/home/kgnote/.local/share/kgnote/coding-review-agent-loop/.venv/bin/agent-loop",
        "agent_loop_checkout": "/home/kgnote/.local/share/kgnote/coding-review-agent-loop",
        "claude_cmd": "/home/kgnote/.local/bin/claude",
        "codex_cmd": "/home/kgnote/.local/bin/codex",
    }
    if runtime_paths is not None:
        if set(runtime_paths) != set(paths):
            raise LaneError("review runtime path override is incomplete")
        paths = dict(runtime_paths)
    order = WorkOrder.from_dict({
        "goal_id": context["goal_id"], "repository": context["repository"],
        "issue": context["issue"], "pull_request": pull_request,
        "candidate_commit": candidate["commit"],
        "candidate_fingerprint": candidate["fingerprint"],
        "review_round_used": used, "review_round_limit": limit,
        "timeout_seconds": 1800, "checkpoint_path": str(checkpoint),
        **paths,
        "allow_live_write": False, "review_only_live": True,
        "safety_baseline_verified": True,
        "requested_model": "sonnet", "requested_effort": "medium",
        "requested_provider": "Anthropic",
        "program_id": context["goal_version"],
        "review_scope": (
            f"Work Item {context['work_item_id']} and obligations "
            + ", ".join(context["obligation_ids"])
        ),
        "review_authority_paths": [
            "AGENTS.md", "PLAN.md", "CODEX_STATUS.md",
            "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
        ],
        "formal_consumer_schema_sha256": projection["formal_schema_sha256"],
        "claude_facing_schema_sha256": projection["claude_facing_schema_sha256"],
        "schema_projection_version": projection["projection_version"],
    })
    if (
        order.formal_consumer_schema_sha256 != projection["formal_schema_sha256"]
        or order.claude_facing_schema_sha256 != projection["claude_facing_schema_sha256"]
        or order.schema_projection_version != projection["projection_version"]
    ):
        raise LaneError("Reviewer WorkOrder schema admission differs from the formal projection")
    result = executor(order)
    _atomic_json(evidence_path, result)
    return 0 if result.get("status") in {"COMPLETED", "ALREADY_COMPLETED"} else 2


def execute_lane(
    mode: str, repo: Path, context: dict[str, Any], evidence_path: Path,
    command: list[str] | None = None,
) -> int:
    context = validate_context(context)
    expected = {
        "codex": ("codex", {"DISPATCH_IMPLEMENTATION", "DISPATCH_REPAIR"}),
        "verify": ("publisher", {"RUN_DETERMINISTIC_VERIFICATION", "RETRY_COMPLETION_GATE"}),
        "publish": ("push", {"RETRY_PUBLICATION"}),
        "review": ("claude", {"DISPATCH_REVIEW"}),
    }
    stage, actions = expected[mode]
    if context["stage"] != stage or context.get("action") not in actions:
        raise LaneError("lane mode differs from the sealed stage/action")
    if mode == "codex":
        return run_codex(repo, context, evidence_path, command or [])
    if command:
        raise LaneError("only the Codex lane accepts a nested fixed command")
    if mode == "verify":
        return run_verify(repo, context, evidence_path)
    if mode == "publish":
        return run_publish(repo, context, evidence_path)
    return run_review(repo, context, evidence_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--context-json", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--command-json")
    args = parser.parse_args()
    try:
        context = json.loads(args.context_json)
        command = json.loads(args.command_json) if args.command_json else None
        if command is not None and (
            not isinstance(command, list) or any(not isinstance(item, str) for item in command)
        ):
            raise LaneError("nested command must be a JSON string array")
        return execute_lane(args.mode, Path.cwd(), context, args.evidence, command)
    except (OSError, json.JSONDecodeError, WorkerResultError, LaneError, AdapterError) as exc:
        print(f"product goal lane rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
