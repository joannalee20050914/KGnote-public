#!/usr/bin/env python3
"""Durable shared adapter from real worker evidence to Product Goal results.

The adapter is deliberately evidence-driven: process exit zero is never enough.
It preserves raw output, atomically saves the canonical envelope, and replays an
already-saved exact result instead of relaunching a completed worker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

try:
    from codex_jsonl_evidence import parse_codex_jsonl, provider_failure_from_output
    from product_goal_worker_identity import (
        PRODUCT_RUNTIME_CONTEXT_SCHEMA,
        ProductGoalIdentityError,
        validate_product_goal_runtime_context,
    )
except ModuleNotFoundError:  # Package import in repository unit tests.
    from scripts.codex_jsonl_evidence import parse_codex_jsonl, provider_failure_from_output
    from scripts.product_goal_worker_identity import (
        PRODUCT_RUNTIME_CONTEXT_SCHEMA,
        ProductGoalIdentityError,
        validate_product_goal_runtime_context,
    )


CONTEXT_SCHEMA = PRODUCT_RUNTIME_CONTEXT_SCHEMA
LEGACY_CONTEXT_SCHEMA = "kgnote.product-goal-worker-context.v1"
RESULT_SCHEMA = "kgnote.product-goal-worker-result.v1"
EVIDENCE_PREFIX = "KGNOTE_EXECUTION_EVIDENCE="
SHA1_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class WorkerResultError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n")


def validate_context(context: object) -> dict[str, Any]:
    if not isinstance(context, dict) or context.get("schema_version") not in {
        CONTEXT_SCHEMA, LEGACY_CONTEXT_SCHEMA,
    }:
        raise WorkerResultError("worker context is missing or unsupported")
    if context.get("schema_version") == CONTEXT_SCHEMA:
        try:
            validate_product_goal_runtime_context(context)
        except ProductGoalIdentityError as exc:
            raise WorkerResultError(str(exc)) from exc
    required = {
        "goal_id", "goal_version", "goal_spec_sha256", "work_item_id",
        "order_event_id", "attempt_id", "stage", "provider",
        "candidate_commit", "candidate_fingerprint", "obligation_ids",
    }
    if required - set(context):
        raise WorkerResultError("worker context is incomplete")
    if not SHA256_RE.fullmatch(str(context["goal_spec_sha256"])):
        raise WorkerResultError("worker context Goal digest is invalid")
    if context["stage"] not in {"codex", "publisher", "push", "claude"}:
        raise WorkerResultError("worker context stage is invalid")
    if context["provider"] not in {"codex", "claude", "NONE"}:
        raise WorkerResultError("worker context provider is invalid")
    if context["stage"] == "codex" and context["provider"] != "codex":
        raise WorkerResultError("Codex stage/provider mismatch")
    if context["stage"] == "claude" and context["provider"] != "claude":
        raise WorkerResultError("Claude stage/provider mismatch")
    if context["stage"] in {"publisher", "push"} and context["provider"] != "NONE":
        raise WorkerResultError("Publisher stage/provider mismatch")
    if not SHA1_RE.fullmatch(str(context["candidate_commit"])) or not SHA256_RE.fullmatch(str(context["candidate_fingerprint"])):
        raise WorkerResultError("worker context candidate identity is invalid")
    obligations = context["obligation_ids"]
    if not isinstance(obligations, list) or not obligations or any(
        not isinstance(item, str) or not item.startswith("OBL-") for item in obligations
    ):
        raise WorkerResultError("worker context obligations are invalid")
    return context


def _usage(raw: object, *, source: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        input_tokens = raw.get("input_tokens")
        output_tokens = raw.get("output_tokens")
        if all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in (input_tokens, output_tokens)):
            return {
                "status": "OBSERVED", "input_tokens": input_tokens,
                "output_tokens": output_tokens, "source": source,
            }
    return {
        "status": "UNKNOWN", "input_tokens": None, "output_tokens": None,
        "source": f"{source}_without_reliable_usage",
    }


def _failure_class(
    returncode: int | None, output: bytes, artifact: object,
) -> tuple[str, dict[str, Any]]:
    text = output.decode("utf-8", errors="replace")
    if isinstance(artifact, dict):
        reported = artifact.get("failure_class") or artifact.get("reason")
        if isinstance(reported, str):
            normalized = reported.upper()
            if normalized in {
                "PUBLICATION_FAILED", "GITHUB_WRITEBACK_FAILED",
                "DETERMINISTIC_WORKER_FAILURE", "EVIDENCE_INSUFFICIENT",
                "UNKNOWN_OUTCOME", "TRANSPORT_INTERRUPTED",
                "WORKER_ENVIRONMENT_ADMISSION_FAILED",
            }:
                return normalized, {
                    "source": "structured_worker_artifact",
                    "artifact_sha256": hashlib.sha256(_canonical(artifact)).hexdigest(),
                    "reported_field": "failure_class" if artifact.get("failure_class") else "reason",
                }
    provider_failure = provider_failure_from_output(text)
    if provider_failure is not None:
        return str(provider_failure["failure_class"]), provider_failure
    if returncode is None:
        return "UNKNOWN_OUTCOME", {"source": "missing_process_outcome"}
    return "DETERMINISTIC_WORKER_FAILURE", {
        "source": "process_exit_without_structured_provider_error",
        "exit_code": returncode,
    }


def _candidate(context: dict[str, Any], artifact: dict[str, Any], *, allow_successor: bool) -> dict[str, Any]:
    commit = artifact.get("candidate_commit") or artifact.get("commit") or artifact.get("reviewed_commit")
    fingerprint = artifact.get("candidate_fingerprint") or artifact.get("reviewed_fingerprint")
    if not isinstance(commit, str) or not SHA1_RE.fullmatch(commit):
        raise WorkerResultError("worker evidence lacks a valid candidate commit")
    if not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint):
        raise WorkerResultError("worker evidence lacks a valid candidate fingerprint")
    if allow_successor:
        parent = artifact.get("candidate_parent") or artifact.get("parent")
        if parent != context["candidate_commit"]:
            raise WorkerResultError("Codex successor evidence does not bind the expected parent")
    elif commit != context["candidate_commit"] or fingerprint != context["candidate_fingerprint"]:
        raise WorkerResultError("worker evidence binds a different exact candidate")
    candidate: dict[str, Any] = {"commit": commit, "fingerprint": fingerprint}
    branch = artifact.get("branch") or context.get("branch")
    if isinstance(branch, str) and branch:
        candidate["branch"] = branch
    pull_request = artifact.get("pull_request", context.get("pull_request"))
    if isinstance(pull_request, int) and not isinstance(pull_request, bool) and pull_request > 0:
        candidate["pull_request"] = pull_request
    return candidate


def _evaluations(context: dict[str, Any], artifact: dict[str, Any], *, verified: bool = False) -> list[dict[str, str]]:
    evidence_sha = hashlib.sha256(_canonical(artifact)).hexdigest()
    progress = "VERIFIED_RESOLVED" if verified else "FUNCTIONAL_PROGRESS_UNVERIFIED"
    return [
        {"obligation_id": item, "progress_class": progress, "evidence_sha256": evidence_sha}
        for item in context["obligation_ids"]
    ]


def adapt_worker_result(
    context: dict[str, Any], artifact: object, *, returncode: int | None,
    stdout: bytes = b"", stderr: bytes = b"",
) -> dict[str, Any]:
    """Translate one lane's persisted evidence; never infer success from exit 0."""
    context = validate_context(context)
    combined = stdout + b"\n" + stderr
    usage_raw = artifact.get("usage") if isinstance(artifact, dict) else None
    if isinstance(artifact, dict) and not isinstance(usage_raw, dict):
        execution_evidence = artifact.get("execution_evidence")
        if isinstance(execution_evidence, dict):
            usage_raw = execution_evidence.get("token_usage")
    if not isinstance(usage_raw, dict):
        usage_raw = parse_codex_jsonl(combined.decode("utf-8", errors="replace")).get("usage")
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        **{key: context[key] for key in (
            "goal_id", "goal_version", "goal_spec_sha256", "work_item_id",
            "order_event_id", "attempt_id", "stage", "provider",
        )},
        "result_state": "FAILED",
        "outcome": "WORK_FAILED",
        "failure_class": None,
        "candidate": None,
        "obligation_evaluations": [],
        "usage": _usage(usage_raw, source=f"{context['stage']}_worker_evidence"),
        "review_verdict": None,
        "review_findings": [],
        "publication": None,
        "execution": {
            "exit_code": returncode,
            "artifact_sha256": hashlib.sha256(_canonical(artifact)).hexdigest() if isinstance(artifact, dict) else None,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        },
    }
    if returncode != 0:
        failure, classification_evidence = _failure_class(returncode, combined, artifact)
        if context["stage"] in {"publisher", "push"} and failure == "DETERMINISTIC_WORKER_FAILURE":
            failure = "PUBLICATION_FAILED"
        result["failure_class"] = failure
        result["execution"]["classification_evidence"] = classification_evidence
        if failure in {"UNKNOWN_OUTCOME", "TRANSPORT_INTERRUPTED"}:
            result["result_state"] = "PENDING"
            result["outcome"] = "WORK_PENDING"
        return result
    if not isinstance(artifact, dict):
        result["failure_class"] = "EVIDENCE_INSUFFICIENT"
        return result

    try:
        if context["stage"] == "codex":
            if artifact.get("schema_version") != "kgnote.codex-product-goal-result.v1" or artifact.get("status") != "COMPLETED":
                raise WorkerResultError("Codex completion evidence is missing")
            verification = artifact.get("verification")
            if not isinstance(verification, dict) or verification.get("status") != "PASS":
                raise WorkerResultError("Codex completion lacks deterministic verification PASS")
            candidate = _candidate(context, artifact, allow_successor=True)
            result.update({
                "result_state": "COMPLETED", "outcome": "WORK_COMPLETED",
                "candidate": candidate,
                "obligation_evaluations": _evaluations(context, artifact),
            })
        elif context["stage"] in {"publisher", "push"}:
            if artifact.get("schema_version") == "kgnote.verification-evidence.v1":
                before = artifact.get("fingerprint_before")
                after = artifact.get("fingerprint_after")
                if (
                    artifact.get("result") != "pass"
                    or artifact.get("fingerprint_stable") is not True
                    or artifact.get("evidence_readback") is not True
                    or not isinstance(before, dict) or not isinstance(after, dict)
                    or before != after
                ):
                    raise WorkerResultError("deterministic verification evidence did not pass read-back")
                artifact = {
                    "schema_version":"kgnote.product-goal-publication-result.v1",
                    "status":"VERIFICATION_PASS",
                    "candidate_commit":after.get("head"),
                    "candidate_fingerprint":after.get("value"),
                    "branch":after.get("branch") or context.get("branch"),
                    "pull_request":context.get("pull_request"),
                    "verification_evidence_sha256":hashlib.sha256(_canonical(artifact)).hexdigest(),
                }
            if artifact.get("schema_version") != "kgnote.product-goal-publication-result.v1":
                raise WorkerResultError("Publisher evidence is missing")
            candidate = _candidate(context, artifact, allow_successor=False)
            status = artifact.get("status")
            if status == "VERIFICATION_PASS":
                result.update({
                    "result_state": "COMPLETED", "outcome": "WORK_COMPLETED",
                    "candidate": candidate,
                    "obligation_evaluations": _evaluations(context, artifact),
                })
            elif status in {"PUBLISHED", "READ_BACK_VERIFIED"} and SHA256_RE.fullmatch(str(artifact.get("receipt_sha256") or "")):
                result.update({
                    "result_state": "COMPLETED", "outcome": "WORK_COMPLETED",
                    "candidate": candidate,
                    "obligation_evaluations": _evaluations(context, artifact),
                    "publication": {"status": status, "receipt_sha256": artifact["receipt_sha256"]},
                })
            else:
                result["failure_class"] = "PUBLICATION_FAILED"
        else:
            review = artifact.get("review_result") if isinstance(artifact.get("review_result"), dict) else artifact
            verdict = review.get("verdict")
            if verdict not in {"PASS", "CHANGES_REQUIRED", "PRODUCT_DECISION_REQUIRED"}:
                result["failure_class"] = "EVIDENCE_INSUFFICIENT"
                return result
            candidate = _candidate(context, review, allow_successor=False)
            review_id = review.get("review_id")
            if not isinstance(review_id, str) or not review_id:
                review_id = f"{context['order_event_id']}:{context['attempt_id']}"
            identity_sha = review.get("candidate_identity_sha256")
            if not SHA256_RE.fullmatch(str(identity_sha or "")):
                identity_sha = hashlib.sha256(_canonical({
                    "goal_id": context["goal_id"],
                    "goal_version": context["goal_version"],
                    "work_item_id": context["work_item_id"],
                    "order_event_id": context["order_event_id"],
                    "attempt_id": context["attempt_id"],
                    "candidate_commit": candidate["commit"],
                    "candidate_fingerprint": candidate["fingerprint"],
                })).hexdigest()
            findings = review.get("findings", [])
            if not isinstance(findings, list):
                raise WorkerResultError("Claude findings are malformed")
            outcome = {
                "PASS": "REVIEW_PASS",
                "CHANGES_REQUIRED": "REVIEW_CHANGES_REQUIRED",
                "PRODUCT_DECISION_REQUIRED": "PRODUCT_DECISION_REQUIRED",
            }[verdict]
            result.update({
                "result_state": "COMPLETED", "outcome": outcome,
                "candidate": candidate,
                "obligation_evaluations": _evaluations(context, review, verified=verdict == "PASS"),
                "review_verdict": {
                    "review_id": review_id, "verdict": verdict,
                    "candidate_identity_sha256": identity_sha,
                },
                "review_findings": findings,
            })
    except WorkerResultError as exc:
        result["failure_class"] = "EVIDENCE_INSUFFICIENT"
        result["execution"]["validation_error"] = str(exc)
    return result


def execute_and_adapt(
    context: dict[str, Any], command: list[str], *, evidence_path: Path,
    result_path: Path, stdout_path: Path, stderr_path: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run once, persist raw evidence first, then atomically seal/replay result."""
    context = validate_context(context)
    if result_path.is_file():
        try:
            previous = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkerResultError("existing worker result is unreadable") from exc
        exact = {key: context[key] for key in (
            "goal_id", "goal_version", "goal_spec_sha256", "work_item_id",
            "order_event_id", "attempt_id", "stage", "provider",
        )}
        if previous.get("schema_version") != RESULT_SCHEMA or any(previous.get(key) != value for key, value in exact.items()):
            raise WorkerResultError("existing worker result belongs to a different attempt")
        return previous
    if not command or not command[0].startswith(("/bin/", "/usr/bin/", "/home/kgnote/.local/")):
        raise WorkerResultError("worker command must use an approved absolute executable")
    completed = runner(command, text=True, capture_output=True, check=False)
    stdout = completed.stdout.encode("utf-8", errors="replace")
    stderr = completed.stderr.encode("utf-8", errors="replace")
    _atomic_bytes(stdout_path, stdout)
    _atomic_bytes(stderr_path, stderr)
    artifact: object = None
    if evidence_path.is_file():
        try:
            artifact = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            artifact = None
    elif completed.stdout.strip():
        try:
            artifact = json.loads(completed.stdout)
        except json.JSONDecodeError:
            artifact = None
    result = adapt_worker_result(
        context, artifact, returncode=completed.returncode,
        stdout=stdout, stderr=stderr,
    )
    _atomic_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    context_group = parser.add_mutually_exclusive_group(required=True)
    context_group.add_argument("--context", type=Path)
    context_group.add_argument("--context-json")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--stdout", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--command-json", required=True)
    args = parser.parse_args()
    try:
        context = json.loads(
            args.context.read_text(encoding="utf-8")
            if args.context is not None else args.context_json
        )
        command = json.loads(args.command_json)
        if not isinstance(command, list) or any(not isinstance(item, str) for item in command):
            raise WorkerResultError("worker command JSON must be a string array")
        result = execute_and_adapt(
            context, command, evidence_path=args.evidence, result_path=args.result,
            stdout_path=args.stdout, stderr_path=args.stderr,
        )
    except (OSError, json.JSONDecodeError, WorkerResultError) as exc:
        parser.error(str(exc))
    evidence = {
        "schema_version": "kgnote.model-execution-evidence.v1",
        "product_goal_result": result,
        "result_sha256": hashlib.sha256(_canonical(result)).hexdigest(),
    }
    print(EVIDENCE_PREFIX + json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
