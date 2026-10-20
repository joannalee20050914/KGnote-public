#!/usr/bin/env python3
"""Guest entrypoint for one resumable epoch-new KGnote Codex worker."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


NODE = "/home/kgnote/.local/lib/node-v24.12.0/bin/node"
CODEX_JS = "/home/kgnote/.local/lib/node-v24.12.0/lib/node_modules/@openai/codex/bin/codex.js"
REQUESTED_MODEL = "gpt-5.6-terra"
REQUESTED_EFFORT = "medium"
PROVIDER = "OpenAI"
AUTHENTICATION = "ChatGPT OAuth"
EVIDENCE_PREFIX = "KGNOTE_EXECUTION_EVIDENCE="


def quota_failure_reason(output: str) -> str | None:
    """Use the same fail-closed quota vocabulary as the Claude adapter."""
    lowered = output.lower()
    if "quota" in lowered or "rate limit" in lowered or "usage limit" in lowered:
        return "quota_exhausted"
    return None


def atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def codex_command(prompt: str, worktree: Path) -> list[str]:
    # Both overrides are invocation-local and therefore outrank user/project
    # config without changing either file.  Keep them before `exec` because
    # they are global Codex CLI options in 0.146.0.
    return [
        NODE, CODEX_JS,
        "--strict-config",
        "--model", REQUESTED_MODEL,
        "--config", f'model_reasoning_effort="{REQUESTED_EFFORT}"',
        "-a", "never", "-s", "danger-full-access", "-C", str(worktree),
        "exec", "--ephemeral", prompt,
    ]


def cli_version() -> str:
    return subprocess.check_output([NODE, CODEX_JS, "--version"], text=True).strip()


def execution_evidence(goal_id: str, pull_request: int, cycle: int) -> dict[str, object]:
    return {
        "schema_version": "kgnote.model-execution-evidence.v1",
        "role": "CODEX_IMPLEMENTER",
        "goal_id": goal_id,
        "pull_request": pull_request,
        "cycle": cycle,
        "provider": PROVIDER,
        "authentication": AUTHENTICATION,
        "requested_model": REQUESTED_MODEL,
        "requested_effort": REQUESTED_EFFORT,
        "cli_version": cli_version(),
        "configuration_status": "CONFIGURED",
        "effective_model": None,
        "effective_effort": None,
        "effective_status": "EFFECTIVE_UNKNOWN",
        "effective_reason": "Codex CLI 0.146.0 exec output does not provide a reliable actual-model field in this production path.",
        "token_usage": None,
    }


def run(
    repository: str,
    branch: str,
    expected_head: str,
    prompt: str,
    worktree: Path,
    *,
    goal_id: str = "UNKNOWN",
    pull_request: int = 0,
    cycle: int = 0,
) -> int:
    checkpoint = worktree / ".git/kgnote-successor-worker-checkpoint.json"
    if not (worktree / ".git").is_dir():
        if any(worktree.iterdir()): raise RuntimeError("successor worktree is non-empty and uninitialized")
        subprocess.run(["/usr/bin/git", "clone", "--branch", branch, "--single-branch", f"https://github.com/{repository}.git", str(worktree)], check=True)
    actual_branch = subprocess.check_output(["/usr/bin/git", "-C", str(worktree), "branch", "--show-current"], text=True).strip()
    inherited_head = subprocess.check_output(["/usr/bin/git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if actual_branch != branch: raise RuntimeError("successor branch identity mismatch")
    if not checkpoint.exists() and inherited_head != expected_head: raise RuntimeError("successor inherited HEAD mismatch")
    evidence = execution_evidence(goal_id, pull_request, cycle)
    child: subprocess.Popen[str] | None = None

    def stop(signum: int, _frame: object) -> None:
        atomic_json(checkpoint, {"schema_version":"kgnote.successor-worker-checkpoint.v1","status":"TERMINATION_REQUESTED","signal":signum,"head":subprocess.check_output(["/usr/bin/git","-C",str(worktree),"rev-parse","HEAD"],text=True).strip(),"execution_evidence":evidence,"recorded_at":datetime.now(timezone.utc).isoformat()})
        if child is not None: child.terminate()

    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    atomic_json(checkpoint, {"schema_version":"kgnote.successor-worker-checkpoint.v1","status":"RUNNING","head":inherited_head,"execution_evidence":evidence,"recorded_at":datetime.now(timezone.utc).isoformat()})
    print(EVIDENCE_PREFIX + json.dumps(evidence, sort_keys=True), flush=True)
    child = subprocess.Popen(
        codex_command(prompt, worktree),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    stdout, stderr = child.communicate()
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n", flush=True)
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr, flush=True)
    exit_code = child.returncode
    reason = None if exit_code == 0 else quota_failure_reason(stdout + stderr)
    if exit_code != 0 and reason is None:
        reason = "codex_process_returned_non_zero"
    head = subprocess.check_output(["/usr/bin/git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    atomic_json(checkpoint, {"schema_version":"kgnote.successor-worker-checkpoint.v1","status":"COMPLETED" if exit_code == 0 else "FAILED_CLOSED","reason":reason,"exit_code":exit_code,"head":head,"execution_evidence":evidence,"recorded_at":datetime.now(timezone.utc).isoformat()})
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal-id", required=True)
    parser.add_argument("--pull-request", required=True, type=int)
    parser.add_argument("--cycle", required=True, type=int)
    parser.add_argument("repository"); parser.add_argument("branch"); parser.add_argument("expected_head"); parser.add_argument("prompt")
    args = parser.parse_args()
    try: return run(args.repository, args.branch, args.expected_head, args.prompt, Path.cwd(), goal_id=args.goal_id, pull_request=args.pull_request, cycle=args.cycle)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"successor worker rejected: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
