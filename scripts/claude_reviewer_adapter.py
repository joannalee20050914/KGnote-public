#!/usr/bin/env python3
"""Bounded adapter between the KGnote Runner and coding-review-agent-loop.

The adapter deliberately does not own scheduling, GitHub Projects, merge, or
product acceptance.  It validates one Runner-issued work order, invokes one
agent-loop process, and writes an atomic checkpoint that the Runner can read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from claude_billing_preflight import BillingPreflightError, verify_subscription_oauth


PINNED_AGENT_LOOP_COMMIT = "aa24f193558db704c870658718650732860addd9"
PROTECTED_PR = 23
FORBIDDEN_FLAGS = {"--auto-merge", "--dangerous-agent-permissions"}
REQUESTED_MODEL = "sonnet"
REQUESTED_EFFORT = "medium"
REQUESTED_PROVIDER = "Anthropic"
FORMAL_REVIEW_SCHEMA_RELATIVE_PATH = Path("schemas/product-review/v1/review-result.schema.json")
FORMAL_REVIEW_SCHEMA_SHA256 = "f0b977274a82b291bea0d0aa0b447d2425155cad413da035457ba516abe898b5"


class AdapterError(RuntimeError):
    """A fail-closed work-order or execution failure."""


@dataclass(frozen=True)
class WorkOrder:
    goal_id: str
    repository: str
    issue: int
    pull_request: int
    candidate_commit: str
    candidate_fingerprint: str
    review_round_used: int
    review_round_limit: int
    timeout_seconds: int
    checkpoint_path: Path
    agent_loop: Path
    agent_loop_checkout: Path
    claude_cmd: Path
    codex_cmd: Path
    allow_live_write: bool
    review_only_live: bool
    safety_baseline_verified: bool
    requested_model: str
    requested_effort: str
    requested_provider: str
    program_id: str
    review_scope: str
    review_authority_paths: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkOrder":
        try:
            order = cls(
                goal_id=str(value["goal_id"]),
                repository=str(value["repository"]),
                issue=int(value["issue"]),
                pull_request=int(value["pull_request"]),
                candidate_commit=str(value["candidate_commit"]),
                candidate_fingerprint=str(value["candidate_fingerprint"]),
                review_round_used=int(value["review_round_used"]),
                review_round_limit=int(value["review_round_limit"]),
                timeout_seconds=int(value["timeout_seconds"]),
                checkpoint_path=Path(value["checkpoint_path"]),
                agent_loop=Path(value["agent_loop"]),
                agent_loop_checkout=Path(value["agent_loop_checkout"]),
                claude_cmd=Path(value["claude_cmd"]),
                codex_cmd=Path(value["codex_cmd"]),
                allow_live_write=value["allow_live_write"] is True,
                review_only_live=value.get("review_only_live", False) is True,
                safety_baseline_verified=value["safety_baseline_verified"] is True,
                requested_model=str(value["requested_model"]),
                requested_effort=str(value["requested_effort"]),
                requested_provider=str(value["requested_provider"]),
                program_id=str(
                    value.get("program_id", "kgnote-source-library-successor-20261019")
                ),
                review_scope=str(
                    value.get(
                        "review_scope",
                        "KGNOTE_PRODUCT_CONTRACT and inherited finding-r-004 only",
                    )
                ),
                review_authority_paths=tuple(
                    str(path) for path in value.get(
                        "review_authority_paths",
                        ["AGENTS.md", "PLAN.md", "CODEX_STATUS.md", ".ai/REVIEW_REQUEST.md"],
                    )
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AdapterError(f"invalid work order: {exc}") from exc
        order.validate()
        return order

    def validate(self) -> None:
        if not self.goal_id:
            raise AdapterError("goal_id must be non-empty")
        if self.repository.count("/") != 1:
            raise AdapterError("repository must be OWNER/REPO")
        if self.issue < 1 or self.pull_request < 1:
            raise AdapterError("issue and pull_request must be positive")
        if len(self.candidate_commit) != 40 or any(c not in "0123456789abcdef" for c in self.candidate_commit):
            raise AdapterError("candidate_commit must be a lowercase 40-character SHA")
        if len(self.candidate_fingerprint) != 64 or any(c not in "0123456789abcdef" for c in self.candidate_fingerprint):
            raise AdapterError("candidate_fingerprint must be lowercase SHA-256")
        if not 0 <= self.review_round_used < self.review_round_limit:
            raise AdapterError("review budget is exhausted or inconsistent")
        if self.timeout_seconds < 1:
            raise AdapterError("timeout_seconds must be positive")
        if self.pull_request == PROTECTED_PR:
            raise AdapterError("PR #23 is forbidden for migration validation")
        if self.allow_live_write:
            raise AdapterError(
                "agent-loop live coder writes are disabled; use sandboxed Codex edits plus trusted_candidate_publisher"
            )
        if self.review_only_live and not self.safety_baseline_verified:
            raise AdapterError("review-only live mode requires a verified safety baseline")
        if (self.requested_model, self.requested_effort, self.requested_provider) != (
            REQUESTED_MODEL, REQUESTED_EFFORT, REQUESTED_PROVIDER
        ):
            raise AdapterError("formal reviewer model configuration must be Sonnet / medium / Anthropic")
        if not self.program_id or not self.review_scope.strip():
            raise AdapterError("program_id and review_scope must be non-empty")
        if not self.review_authority_paths:
            raise AdapterError("review_authority_paths must be non-empty")
        for value in self.review_authority_paths:
            path = Path(value)
            if path.is_absolute() or ".." in path.parts or not value.strip():
                raise AdapterError("review authority paths must be non-empty repository-relative paths")
        for path, label in ((self.agent_loop, "agent-loop"), (self.claude_cmd, "claude"), (self.codex_cmd, "codex")):
            if not path.is_file() or not os.access(path, os.X_OK):
                raise AdapterError(f"{label} executable is unavailable: {path}")


def verify_pin(order: WorkOrder, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
    result = runner(
        ["git", "-C", str(order.agent_loop_checkout), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode or result.stdout.strip() != PINNED_AGENT_LOOP_COMMIT:
        raise AdapterError("agent-loop checkout does not match the pinned commit")


def load_formal_consumer_schema(adapter_file: Path | None = None) -> dict[str, Any]:
    """Load the exact reviewed Consumer schema from the trusted install layout."""
    adapter_path = (adapter_file or Path(__file__)).resolve()
    runtime_root = adapter_path.parent.parent if adapter_path.parent.name == "scripts" else adapter_path.parent
    schema_path = runtime_root / FORMAL_REVIEW_SCHEMA_RELATIVE_PATH
    try:
        schema_bytes = schema_path.read_bytes()
    except OSError as exc:
        raise AdapterError(f"formal review schema unavailable: {schema_path}") from exc
    actual_sha256 = hashlib.sha256(schema_bytes).hexdigest()
    if actual_sha256 != FORMAL_REVIEW_SCHEMA_SHA256:
        raise AdapterError(
            "formal review schema digest mismatch: "
            f"expected {FORMAL_REVIEW_SCHEMA_SHA256}, got {actual_sha256}"
        )
    try:
        schema = json.loads(schema_bytes)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"formal review schema is invalid JSON: {schema_path}") from exc
    if not isinstance(schema, dict):
        raise AdapterError(f"formal review schema must be an object: {schema_path}")
    return schema


def build_command(order: WorkOrder) -> list[str]:
    if order.review_only_live:
        schema_value = load_formal_consumer_schema()
        # Claude's CLI does not need the dialect annotation.  All validation
        # keywords, including allOf/if/then/else, $defs and required, remain exact.
        schema_value.pop("$schema", None)
        schema = json.dumps(schema_value, separators=(",", ":"))
        authority_paths = ", ".join(order.review_authority_paths)
        prompt = (
            "You are the independent KGnote product-contract reviewer. Review the exact read-only checkout in the current directory. "
            "Do not modify files, run commands, browse, publish, merge, or infer native UI behavior. Read AGENTS.md, PLAN.md, "
            "CODEX_STATUS.md, the sealed .ai/REVIEW_REQUEST.md, the product contracts, changed implementation, and relevant tests. "
            f"The exact authority/read set starts with: {authority_paths}. Return only the schema object. "
            f"Exact identity: repository={order.repository}; pull_request={order.pull_request}; program_id={order.program_id}; "
            f"goal_id={order.goal_id}; candidate_commit={order.candidate_commit}; "
            f"candidate_fingerprint={order.candidate_fingerprint}; review_round={order.review_round_used + 1}. "
            f"Scope is exactly: {order.review_scope}. "
            "Judge every sealed acceptance criterion and negative requirement. PASS only when the exact candidate satisfies that scope, "
            "has no blocking or major finding, and preserves every stated human gate. "
            "Set native_ui_observed=false."
        )
        return [str(order.claude_cmd), "-p", "--model", order.requested_model,
                "--effort", order.requested_effort,
                "--output-format", "json", "--json-schema", schema,
                "--permission-mode", "dontAsk", "--permission-prompts", "none",
                "--disallowedTools", "Bash,Edit,Write,WebFetch,WebSearch", "--allowedTools", "Read,Grep,Glob",
                "--no-session-persistence", prompt]
    remaining = order.review_round_limit - order.review_round_used
    command = [
        str(order.agent_loop), "pr", str(order.pull_request),
        "--repo", order.repository,
        "--expected-closing-issue", str(order.issue),
        "--coder", "codex",
        "--reviewer", "claude",
        "--repair-backend", "codex",
        "--repair-model", "gpt-5.6-codex",
        "--max-rounds", str(remaining),
        "--claude-cmd", str(order.claude_cmd),
        "--codex-cmd", str(order.codex_cmd),
        "--agent-permissions", "sandboxed",
        "--containment-mode", "auto",
        "--semantic-followup-backend", "claude",
    ]
    command.append("--dry-run")
    if FORBIDDEN_FLAGS.intersection(command):
        raise AdapterError("forbidden agent-loop flag selected")
    return command


def read_cli_version(
    claude_cmd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    result = runner(
        [str(claude_cmd), "--version"], text=True, capture_output=True,
        timeout=10, check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise AdapterError("Claude CLI version is unavailable")
    return result.stdout.strip()


def model_execution_evidence(
    order: WorkOrder,
    *,
    cli_version: str,
    auth: dict[str, object],
    envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_usage = envelope.get("modelUsage") if isinstance(envelope, dict) else None
    actual_models: list[str] = []
    providers: list[str] = []
    if isinstance(model_usage, dict):
        for reported_name, details in model_usage.items():
            if isinstance(details, dict):
                actual = details.get("canonicalModel") or reported_name
                if isinstance(actual, str) and actual:
                    actual_models.append(actual)
                provider = details.get("provider")
                if isinstance(provider, str) and provider:
                    providers.append(provider)
    actual_models = sorted(set(actual_models))
    providers = sorted(set(providers))
    if len(actual_models) == 1 and actual_models[0].startswith("claude-sonnet-"):
        effective_status = "EFFECTIVE_CONFIRMED"
        effective_reason = "Claude modelUsage canonicalModel resolved the requested sonnet alias to the Sonnet family."
    elif actual_models:
        effective_status = "MODEL_MISMATCH"
        effective_reason = f"Requested sonnet but modelUsage reported {actual_models}."
    else:
        effective_status = "EFFECTIVE_UNKNOWN"
        effective_reason = "Claude result did not contain a reliable modelUsage canonicalModel."
    return {
        "schema_version": "kgnote.model-execution-evidence.v1",
        "role": "CLAUDE_PRODUCT_REVIEWER",
        "goal_id": order.goal_id,
        "pull_request": order.pull_request,
        "review_round": order.review_round_used + 1,
        "provider": order.requested_provider,
        "authentication": auth,
        "requested_model": order.requested_model,
        "requested_effort": order.requested_effort,
        "cli_version": cli_version,
        "configuration_status": "CONFIGURED",
        "actual_models": actual_models,
        "actual_providers": providers,
        "effective_status": effective_status,
        "effective_reason": effective_reason,
        "token_usage": envelope.get("usage") if isinstance(envelope, dict) else None,
        "model_usage": model_usage,
        "total_cost_usd": envelope.get("total_cost_usd") if isinstance(envelope, dict) else None,
        "total_cost_usd_interpretation": "usage_reference_only_under_verified_Claude_Pro_OAuth",
    }


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _run_process_group(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    """Run one agent-loop tree and deterministically terminate it on timeout."""
    process = subprocess.Popen(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout_seconds, output=stdout, stderr=stderr) from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def execute(
    order: WorkOrder,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    auth_checker: Callable[[Path], dict[str, object]] = verify_subscription_oauth,
) -> dict[str, Any]:
    review_round = order.review_round_used + 1
    identity_key = hashlib.sha256(
        f"{order.repository}\0{order.pull_request}\0{order.candidate_commit}\0{order.candidate_fingerprint}\0{review_round}".encode()
    ).hexdigest()
    if order.checkpoint_path.exists():
        try:
            previous = json.loads(order.checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AdapterError("existing reviewer checkpoint is unreadable") from exc
        if previous.get("identity_key") == identity_key and previous.get("status") == "COMPLETED":
            return {**previous, "status": "ALREADY_COMPLETED"}
        if previous.get("identity_key") and previous.get("identity_key") != identity_key:
            raise AdapterError("review checkpoint belongs to a different exact candidate or round")
    try:
        auth = auth_checker(order.claude_cmd)
    except BillingPreflightError as exc:
        raise AdapterError(str(exc)) from exc
    verify_pin(order, runner)
    version = read_cli_version(order.claude_cmd, runner)
    command = build_command(order)
    configured_evidence = model_execution_evidence(order, cli_version=version, auth=auth)
    started = datetime.now(ZoneInfo("Asia/Taipei")).isoformat()
    _atomic_json(order.checkpoint_path, {
        "schema_version":"kgnote.claude-reviewer-adapter-checkpoint.v1", "status":"RUNNING",
        "identity_key":identity_key, "repository":order.repository, "pull_request":order.pull_request,
        "candidate_commit":order.candidate_commit, "candidate_fingerprint":order.candidate_fingerprint,
        "review_round":review_round, "started_at":started, "product_review_accepted":False,
        "execution_evidence": configured_evidence,
    })
    envelope: dict[str, Any] | None = None
    try:
        result = (
            _run_process_group(command, order.timeout_seconds)
            if runner is subprocess.run
            else runner(command, text=True, capture_output=True, timeout=order.timeout_seconds, check=False)
        )
        status = "COMPLETED" if result.returncode == 0 else "FAILED_CLOSED"
        exit_code: int | None = result.returncode
        output = (result.stdout + result.stderr).encode("utf-8", errors="replace")
        lowered = output.lower()
        try:
            parsed_stdout = json.loads(result.stdout)
            if isinstance(parsed_stdout, dict):
                envelope = parsed_stdout
        except json.JSONDecodeError:
            envelope = None
        if result.returncode == 0:
            reason = None
        elif (
            (isinstance(envelope, dict) and (
                envelope.get("api_error_status") == 429
                or envelope.get("api_error") == "usage_limit_reached"
            ))
            or b"quota" in lowered
            or b"rate limit" in lowered
            or b"usage_limit_reached" in lowered
            or b"session limit" in lowered
        ):
            reason = "quota_exhausted"
        elif b"401" in lowered or b"oauth" in lowered:
            reason = "provider_authentication_failure"
        else:
            reason = "review process returned non-zero"
    except subprocess.TimeoutExpired as exc:
        status, exit_code, reason = "FAILED_CLOSED", None, "timeout"
        output = ((exc.stdout or "") + (exc.stderr or "")).encode("utf-8", errors="replace")
    checkpoint = {
        "schema_version": "kgnote.claude-reviewer-adapter-checkpoint.v1",
        "status": status,
        "reason": reason,
        "repository": order.repository,
        "issue": order.issue,
        "pull_request": order.pull_request,
        "candidate_commit": order.candidate_commit,
        "candidate_fingerprint": order.candidate_fingerprint,
        "identity_key": identity_key,
        "review_round": review_round,
        "review_round_used_before": order.review_round_used,
        "review_round_limit": order.review_round_limit,
        "agent_loop_commit": PINNED_AGENT_LOOP_COMMIT,
        "command": command,
        "exit_code": exit_code,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "stdout_tail": (result.stdout if 'result' in locals() else "")[-8000:],
        "stderr_tail": (result.stderr if 'result' in locals() else "")[-8000:],
        "started_at": started,
        "finished_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
        "product_review_accepted": False,
        "note": "Exit 0 is transport success only; KGnote Product Contract consumption is a separate exact-candidate gate.",
        "execution_evidence": (
            model_execution_evidence(order, cli_version=version, auth=auth, envelope=envelope)
            if envelope is not None else configured_evidence
        ),
    }
    if order.review_only_live and status == "COMPLETED":
        try:
            if envelope is None:
                envelope = json.loads(result.stdout)
            structured = envelope.get("structured_output")
            if not isinstance(structured, dict):
                raise ValueError("structured_output missing")
            checkpoint["review_envelope"] = envelope
            checkpoint["review_result"] = structured
            evidence = model_execution_evidence(order, cli_version=version, auth=auth, envelope=envelope)
            checkpoint["execution_evidence"] = evidence
            if evidence["effective_status"] == "MODEL_MISMATCH":
                checkpoint.update({
                    "status": "FAILED_CLOSED",
                    "reason": "configured Claude model did not match modelUsage/canonicalModel",
                    "product_review_accepted": False,
                })
        except (json.JSONDecodeError, ValueError) as exc:
            checkpoint.update({"status":"FAILED_CLOSED", "reason":f"invalid structured Claude output: {exc}", "product_review_accepted":False})
    _atomic_json(order.checkpoint_path, checkpoint)
    return checkpoint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work_order", type=Path)
    args = parser.parse_args()
    try:
        order = WorkOrder.from_dict(json.loads(args.work_order.read_text(encoding="utf-8")))
        checkpoint = execute(order)
    except (AdapterError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAILED_CLOSED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(checkpoint, ensure_ascii=False))
    return 0 if checkpoint["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
