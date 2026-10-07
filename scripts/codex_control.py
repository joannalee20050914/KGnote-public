#!/usr/bin/env python3
"""Deterministic local control plane for KGnote.

This tool validates repository execution state. It does not approve product changes,
call external services, mutate product data, stage files, or create commits.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo


PLAN_BEGIN = "<!-- BEGIN CODEX PLAN JSON -->"
PLAN_END = "<!-- END CODEX PLAN JSON -->"
STATUS_BEGIN = "<!-- BEGIN CODEX STATUS JSON -->"
STATUS_END = "<!-- END CODEX STATUS JSON -->"
REVIEW_REQUEST_BEGIN = "<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->"
REVIEW_REQUEST_END = "<!-- END KGNOTE REVIEW REQUEST JSON -->"
REVIEW_RESULT_BEGIN = "<!-- BEGIN KGNOTE REVIEW RESULT JSON -->"
REVIEW_RESULT_END = "<!-- END KGNOTE REVIEW RESULT JSON -->"
DECISIONS_BEGIN = "<!-- BEGIN KGNOTE DECISIONS JSON -->"
DECISIONS_END = "<!-- END KGNOTE DECISIONS JSON -->"
HUMAN_DECISION_AUTHORITY_BEGIN = "<!-- BEGIN KGNOTE HUMAN DECISION AUTHORITY JSON -->"
HUMAN_DECISION_AUTHORITY_END = "<!-- END KGNOTE HUMAN DECISION AUTHORITY JSON -->"
HUMAN_DECISION_AUTHORITY_DIRECTORY = "docs/requirements/human-decisions"
REVIEW_PROTOCOL_VERSION = "kgnote.review-protocol.v1"
REVIEW_STATES = {
    "IMPLEMENTING",
    "READY_FOR_REVIEW",
    "UNDER_REVIEW",
    "CHANGES_REQUIRED",
    "PRODUCT_DECISION_REQUIRED",
    "PASS",
}
REVIEW_VERDICTS = {"PASS", "CHANGES_REQUIRED", "PRODUCT_DECISION_REQUIRED"}
FINDING_STATUSES = {"OPEN", "FIXED_PENDING_REVIEW", "VERIFIED", "SUPERSEDED_BY_HUMAN_DECISION"}
ORCHESTRATOR_STATES = {
    "IMPLEMENTING", "VALIDATING", "READY_FOR_AI_REVIEW", "REVIEWING", "REPAIRING",
    "AWAITING_EXTERNAL_PRODUCT_REVIEW",
    "HUMAN_CHECKPOINT_REQUIRED", "PRODUCT_DECISION_REQUIRED", "AUTHORITY_CONFLICT",
    "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED", "GOAL_COMPLETE", "STOPPED",
}
GENERATED_VIEWS = (
    "REQUIREMENTS_TRACE.md",
    "ACCEPTANCE_SCENARIOS.md",
    "SOURCE_INDEX.md",
    "TRACEABILITY_MATRIX.md",
)
FINGERPRINT_EXCLUDES = {
    "CODEX_STATUS.md",
    ".ai/REVIEW_REQUEST.md",
    ".ai/REVIEW_RESULT.md",
    ".ai/DECISIONS.md",
    ".ai/ORCHESTRATOR_STATE.json",
    ".ai/ORCHESTRATOR_STOP",
    ".ai/ORCHESTRATOR.lock",
    ".ai/external-review-state.json",
}
FINGERPRINT_EXCLUDE_PREFIXES = (".ai/REVIEW_HISTORY/", ".ai/ORCHESTRATION_HISTORY/")
PUBLICATION_RECEIPT_PATH = Path(".ai/PUBLICATION_RECEIPT.md")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check
    )


def git_text(repo: Path, *args: str) -> str:
    return run_git(repo, *args).stdout.decode("utf-8", "surrogateescape").strip()


def extract_embedded_json(path: Path, begin: str, end: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"{path.name}: expected exactly one structured JSON marker pair")
    body = text.split(begin, 1)[1].split(end, 1)[0]
    match = re.search(r"```json\s*(.*?)\s*```", body, re.DOTALL)
    if not match:
        raise ValueError(f"{path.name}: missing fenced JSON payload")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: structured payload must be an object")
    return value


def load_plan_status(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        extract_embedded_json(repo / "PLAN.md", PLAN_BEGIN, PLAN_END),
        extract_embedded_json(repo / "CODEX_STATUS.md", STATUS_BEGIN, STATUS_END),
    )


def replace_embedded_json(path: Path, begin: str, end: str, value: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"{path.name}: expected exactly one structured JSON marker pair")
    prefix, tail = text.split(begin, 1)
    _, suffix = tail.split(end, 1)
    body = f"\n```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n"
    path.write_text(prefix + begin + body + end + suffix, encoding="utf-8")


def render_status_handoff(status: dict[str, Any]) -> str:
    state = status.get("review", {}).get("state")
    review_id = status.get("review", {}).get("current_review_id")
    fingerprint = status.get("review", {}).get("candidate_fingerprint")
    goal = status.get("goal_id")
    milestone = status.get("active_milestone_id")
    unresolved = status.get("review", {}).get("unresolved_findings", [])
    decisions = status.get("review", {}).get("human_decision_blockers", [])
    lines = [
        f"Goal `{goal}` remains {status.get('goal_status')} at milestone `{milestone}`.",
        f"Review state is `{state}`.",
    ]
    if review_id:
        lines.append(f"Current review is `{review_id}` at candidate fingerprint `{fingerprint}`.")
    else:
        lines.append("There is no active submitted review request.")
    lines.append(
        f"Unresolved findings: {', '.join(unresolved) if unresolved else 'none'}. "
        f"Human decision blockers: {', '.join(decisions) if decisions else 'none'}."
    )
    lines.append(f"Exact next action: {status.get('next_action')}")
    lines.append("PA-HUMAN-1, NS-HUMAN-SMOKE, and release verification remain unchanged by local review automation.")
    return "## Human-readable handoff\n\n" + "\n".join(lines) + "\n"


def write_status(repo: Path, status: dict[str, Any]) -> None:
    path = repo / "CODEX_STATUS.md"
    replace_embedded_json(path, STATUS_BEGIN, STATUS_END, status)
    text = path.read_text(encoding="utf-8")
    heading = "## Human-readable handoff"
    if text.count(heading) != 1:
        raise ValueError("CODEX_STATUS.md: expected exactly one human-readable handoff heading")
    prefix = text.split(heading, 1)[0].rstrip()
    path.write_text(prefix + "\n\n" + render_status_handoff(status), encoding="utf-8")


def validate_status_handoff(repo: Path, status: dict[str, Any]) -> list[str]:
    path = repo / "CODEX_STATUS.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"status_handoff_drift: cannot read CODEX_STATUS.md: {exc}"]
    heading = "## Human-readable handoff"
    if text.count(heading) != 1:
        return ["status_handoff_drift: expected exactly one human-readable handoff heading"]
    actual = heading + text.split(heading, 1)[1]
    expected = render_status_handoff(status)
    if actual != expected:
        return ["status_handoff_drift: human-readable handoff differs from structured CODEX_STATUS state"]
    return []


def render_review_request_summary(request: dict[str, Any]) -> str:
    review_id = request.get("review_id")
    status = request.get("status")
    lines = [f"Review `{review_id}` is `{status}`."]
    if request.get("candidate_fingerprint"):
        lines.append(
            f"It is bound to `{request.get('candidate_revision')}` and fingerprint "
            f"`{request.get('candidate_fingerprint')}`."
        )
    else:
        lines.append("It has no active candidate binding and cannot be interpreted as a review request or PASS.")
    next_actions = {
        "IMPLEMENTING": "Codex must complete deterministic verification before issuing this request.",
        "READY_FOR_REVIEW": "ChatGPT Work must accept custody and inspect the exact repository candidate.",
        "UNDER_REVIEW": "The candidate is frozen while ChatGPT Work performs semantic review.",
        "CHANGES_REQUIRED": "Codex must preserve every finding, resume implementation, and request re-review.",
        "PRODUCT_DECISION_REQUIRED": "Affected implementation is blocked until a durable human decision exists.",
        "PASS": "This PASS applies only to the recorded candidate and does not promote explicit human gates.",
    }
    lines.append(next_actions.get(status, "Unknown review state; fail closed."))
    return "## Human-readable status\n\n" + "\n".join(lines) + "\n"


def write_review_request(repo: Path, request: dict[str, Any]) -> None:
    path = repo / ".ai/REVIEW_REQUEST.md"
    replace_embedded_json(path, REVIEW_REQUEST_BEGIN, REVIEW_REQUEST_END, request)
    text = path.read_text(encoding="utf-8")
    heading = "## Human-readable status"
    if text.count(heading) != 1:
        raise ValueError("REVIEW_REQUEST.md: expected exactly one human-readable status heading")
    prefix = text.split(heading, 1)[0].rstrip()
    path.write_text(prefix + "\n\n" + render_review_request_summary(request), encoding="utf-8")


def validate_review_request_summary(repo: Path, request: dict[str, Any]) -> list[str]:
    path = repo / ".ai/REVIEW_REQUEST.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"review_request_drift: cannot read REVIEW_REQUEST.md: {exc}"]
    heading = "## Human-readable status"
    if text.count(heading) != 1:
        return ["review_request_drift: expected exactly one human-readable status heading"]
    actual = heading + text.split(heading, 1)[1]
    if actual != render_review_request_summary(request):
        return ["review_request_drift: human-readable request status differs from canonical JSON"]
    return []


def load_review_artifacts(repo: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = repo / ".ai"
    return (
        extract_embedded_json(root / "REVIEW_REQUEST.md", REVIEW_REQUEST_BEGIN, REVIEW_REQUEST_END),
        extract_embedded_json(root / "REVIEW_RESULT.md", REVIEW_RESULT_BEGIN, REVIEW_RESULT_END),
        extract_embedded_json(root / "DECISIONS.md", DECISIONS_BEGIN, DECISIONS_END),
    )


def validate_orchestrator_state(
    repo: Path,
    plan: dict[str, Any],
    request: dict[str, Any],
) -> list[str]:
    """Validate the optional durable orchestration projection."""
    path = repo / ".ai/ORCHESTRATOR_STATE.json"
    if not path.exists():
        return []
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"orchestrator_state: cannot load durable state: {exc}"]
    required = (
        "schema_version", "run_id", "active_goal", "work_package", "state", "current_agent",
        "candidate_fingerprint", "review_id", "review_cycle", "max_review_cycles", "empty_reviewer_results", "blockers",
        "next_action", "human_action_required", "candidate_custody", "next_human_checkpoint",
    )
    errors = missing_fields(state, required, "orchestrator_state")
    if state.get("schema_version") != "kgnote.orchestrator-state.v1":
        errors.append("orchestrator_state: unsupported schema_version")
    if state.get("state") not in ORCHESTRATOR_STATES:
        errors.append("orchestrator_state: invalid state")
    if state.get("active_goal") != plan.get("goal_id"):
        errors.append("orchestrator_state: active_goal differs from PLAN")
    if state.get("work_package") != plan.get("active_milestone_id"):
        errors.append("orchestrator_state: work_package differs from PLAN")
    if not isinstance(state.get("review_cycle"), int) or state.get("review_cycle", -1) < 0:
        errors.append("orchestrator_state: review_cycle must be a non-negative integer")
    if not isinstance(state.get("max_review_cycles"), int) or state.get("max_review_cycles", 0) < 1:
        errors.append("orchestrator_state: max_review_cycles must be positive")
    if not isinstance(state.get("empty_reviewer_results"), int) or state.get("empty_reviewer_results", -1) < 0:
        errors.append("orchestrator_state: empty_reviewer_results must be a non-negative integer")
    if not isinstance(state.get("blockers"), list):
        errors.append("orchestrator_state: blockers must be an array")
    custody = state.get("candidate_custody")
    if not isinstance(custody, dict) or custody.get("status") not in {"NONE", "SEALED", "REVIEWER"}:
        errors.append("orchestrator_state: invalid candidate custody")
    elif custody.get("status") in {"SEALED", "REVIEWER"}:
        if custody.get("review_id") != request.get("review_id"):
            errors.append("orchestrator_state: custody review_id differs from current request")
        if custody.get("fingerprint") != request.get("candidate_fingerprint"):
            errors.append("orchestrator_state: custody fingerprint differs from current request")
    if state.get("state") == "READY_FOR_AI_REVIEW" and request.get("status") != "READY_FOR_REVIEW":
        errors.append("orchestrator_state: READY_FOR_AI_REVIEW requires a sealed READY_FOR_REVIEW request")
    if state.get("state") == "REVIEWING" and request.get("status") != "UNDER_REVIEW":
        errors.append("orchestrator_state: REVIEWING requires UNDER_REVIEW custody")
    if state.get("state") == "AWAITING_EXTERNAL_PRODUCT_REVIEW":
        if request.get("status") != "PASS":
            errors.append("orchestrator_state: external-review wait requires internal PASS")
        if state.get("review_id") != request.get("review_id"):
            errors.append("orchestrator_state: waiting review_id differs from current request")
        if state.get("candidate_fingerprint") != request.get("candidate_fingerprint"):
            errors.append("orchestrator_state: waiting fingerprint differs from current request")
        if not isinstance(custody, dict) or custody.get("status") != "NONE":
            errors.append("orchestrator_state: external-review wait requires released candidate custody")
    human_states = {
        "HUMAN_CHECKPOINT_REQUIRED", "PRODUCT_DECISION_REQUIRED", "AUTHORITY_CONFLICT",
        "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED",
    }
    if bool(state.get("human_action_required")) != (state.get("state") in human_states):
        errors.append("orchestrator_state: human_action_required does not match state")
    return errors


def validate_locked_entries(repo: Path, entries: Iterable[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for item in entries:
        relative = item.get("path")
        if not isinstance(relative, str):
            errors.append("authority lock entry has no path")
            continue
        path = repo / relative
        if not path.is_file():
            errors.append(f"authority_drift: missing {relative}")
            continue
        data = path.read_bytes()
        marker = item.get("required_marker")
        if marker and str(marker).encode() not in data:
            errors.append(f"authority_drift: required marker missing in {relative}")
        if item.get("validation", "sha256") == "sha256":
            expected = item.get("sha256")
            actual = sha256_bytes(data)
            if expected != actual:
                errors.append(
                    f"authority_drift: hash mismatch for {relative}: expected {expected}, got {actual}"
                )
    return errors


def validate_authority(repo: Path) -> tuple[list[str], dict[str, Any]]:
    path = repo / "docs/control-plane/authority-lock.json"
    if not path.is_file():
        return ["authority_drift: missing docs/control-plane/authority-lock.json"], {}
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"authority_drift: invalid authority lock: {exc}"], {}
    errors = []
    if lock.get("conflict_policy") != "fail_closed_authority_drift":
        errors.append("authority_drift: conflict policy is not fail-closed")
    errors.extend(validate_locked_entries(repo, lock.get("product_authority", [])))
    execution = lock.get("execution_authority", {})
    if execution.get("status") != "active":
        errors.append("authority_drift: execution authority is not active")
    errors.extend(validate_locked_entries(repo, execution.get("locked_paths", [])))
    return errors, lock


def validate_plan_status(
    plan: dict[str, Any],
    status: dict[str, Any],
    *,
    branch: str | None = None,
    head: str | None = None,
) -> list[str]:
    errors: list[str] = []
    milestones = plan.get("milestones")
    if not isinstance(milestones, list) or not milestones:
        return ["plan_invalid: milestones must be a non-empty list"]
    ids = [m.get("id") for m in milestones]
    if len(ids) != len(set(ids)):
        errors.append("plan_invalid: duplicate milestone ID")
    goal_active = plan.get("status") == "active"
    active = [m for m in milestones if m.get("status") == "active"]
    if goal_active and len(active) != 1:
        errors.append(f"plan_invalid: active goal requires exactly one active milestone, found {len(active)}")
    if not goal_active and active:
        errors.append("plan_invalid: inactive/complete goal cannot retain an active milestone")
    declared_active = plan.get("active_milestone_id")
    if goal_active and active and declared_active != active[0].get("id"):
        errors.append("plan_invalid: active_milestone_id does not identify the active milestone")
    if not goal_active and declared_active is not None:
        errors.append("plan_invalid: completed goal must set active_milestone_id to null")
    completed = {m.get("id") for m in milestones if m.get("status") == "complete"}
    if active:
        missing = set(active[0].get("dependencies", [])) - completed
        if missing:
            errors.append(f"plan_invalid: active milestone has incomplete dependencies {sorted(missing)}")
        gate = active[0].get("human_gate", "none")
        if gate not in {"none", "complete"}:
            errors.append(f"human_gate: active milestone requires {gate}")
        if active[0].get("consent_required"):
            errors.append("consent_gate: active milestone has unresolved consent requirements")
    if status.get("goal_id") != plan.get("goal_id"):
        errors.append("status_drift: goal_id differs from PLAN")
    if status.get("goal_status") != plan.get("status"):
        errors.append("status_drift: goal status differs from PLAN")
    if status.get("active_milestone_id") != declared_active:
        errors.append("status_drift: active milestone differs from PLAN")
    if status.get("product_direction_id") != plan.get("product_direction_id"):
        errors.append("authority_drift: PLAN and STATUS product direction differ")
    if branch is not None and status.get("git", {}).get("branch") != branch:
        errors.append("status_drift: recorded branch differs from current branch")
    if head is not None and status.get("git", {}).get("head") != head:
        errors.append("status_drift: recorded HEAD differs from current HEAD")
    if status.get("verification", {}).get("release_verified") is True:
        errors.append("verification_drift: CODEX_STATUS may not self-promote release_verified")
    review = status.get("review")
    if not isinstance(review, dict):
        errors.append("status_drift: CODEX_STATUS must expose structured review state")
    else:
        if review.get("state") not in REVIEW_STATES:
            errors.append("status_drift: CODEX_STATUS has invalid review state")
        if status.get("implementation_state") != review.get("state"):
            errors.append("status_drift: implementation_state differs from review state")
        for field in (
            "current_review_id", "candidate_revision", "candidate_fingerprint",
            "unresolved_findings", "human_decision_blockers",
        ):
            if field not in review:
                errors.append(f"status_drift: CODEX_STATUS review is missing {field}")
        if not isinstance(review.get("unresolved_findings"), list):
            errors.append("status_drift: unresolved_findings must be an array")
        if not isinstance(review.get("human_decision_blockers"), list):
            errors.append("status_drift: human_decision_blockers must be an array")
    if not isinstance(status.get("next_action"), str) or not status.get("next_action"):
        errors.append("status_drift: CODEX_STATUS must expose exact next_action")
    return errors


def missing_fields(value: dict[str, Any], names: Iterable[str], prefix: str) -> list[str]:
    return [f"{prefix}: missing required field {name}" for name in names if name not in value]


def validate_review_request(
    repo: Path, request: dict[str, Any], fingerprint: dict[str, Any] | None = None
) -> list[str]:
    errors = missing_fields(
        request,
        (
            "schema_version", "protocol_version", "review_id", "goal_id", "milestone_id", "status",
            "author_role", "base_revision", "candidate_revision", "candidate_fingerprint",
            "authoritative_specs", "changed_areas", "acceptance_criteria", "negative_requirements",
            "validation_performed", "validation_results", "known_deviations", "known_uncertainties",
            "reviewer_focus", "preserved_human_gates", "requested_at",
            "authorized_human_decision_identities", "candidate_manifest",
        ),
        "review_request",
    )
    if errors:
        return errors
    if request.get("schema_version") != "kgnote.review-request.v1":
        errors.append("review_request: unsupported schema_version")
    if request.get("protocol_version") != REVIEW_PROTOCOL_VERSION:
        errors.append("review_request: unsupported protocol_version")
    if request.get("author_role") != "CODEX_IMPLEMENTER":
        errors.append("review_request: author_role must be CODEX_IMPLEMENTER")
    if not re.fullmatch(r"review-[a-z0-9-]+-[0-9]{3}", str(request.get("review_id", ""))):
        errors.append("review_request: invalid review_id")
    status = request.get("status")
    if status not in REVIEW_STATES:
        errors.append(f"review_request: invalid status {status!r}")
    for name in (
        "authoritative_specs", "changed_areas", "acceptance_criteria", "negative_requirements",
        "validation_performed", "validation_results", "known_deviations", "known_uncertainties",
        "reviewer_focus", "preserved_human_gates",
    ):
        if not isinstance(request.get(name), list):
            errors.append(f"review_request: {name} must be an array")
    identities = request.get("authorized_human_decision_identities")
    if not isinstance(identities, list) or not identities or any(
        not isinstance(item, str) or not item.strip() for item in identities
    ):
        errors.append("review_request: authorized_human_decision_identities must be a non-empty array")
    for spec in request.get("authoritative_specs", []):
        if not isinstance(spec, str) or not spec:
            errors.append("review_request: authoritative_specs entries must be non-empty strings")
            continue
        relative = spec.split("#", 1)[0]
        path = repo / relative
        try:
            path.resolve().relative_to(repo.resolve())
        except ValueError:
            errors.append(f"review_request: authority path escapes repository: {relative}")
        if not path.is_file():
            errors.append(f"review_request: missing authority path {relative}")
    bound_states = REVIEW_STATES - {"IMPLEMENTING"}
    if status in bound_states:
        candidate = request.get("candidate_fingerprint")
        revision = request.get("candidate_revision")
        if not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{64}", candidate):
            errors.append("review_request: bound state requires candidate_fingerprint")
        head = git_text(repo, "rev-parse", "HEAD")
        expected_revision = f"{head}+worktree:{candidate}"
        if revision != expected_revision:
            errors.append("review_request: candidate_revision does not match HEAD and fingerprint")
        if not request.get("requested_at"):
            errors.append("review_request: bound state requires requested_at")
        manifest = request.get("candidate_manifest")
        if not isinstance(manifest, dict) or fingerprint_from_manifest(manifest) != candidate:
            errors.append("review_request: candidate_manifest does not reproduce candidate_fingerprint")
        if fingerprint and candidate != fingerprint.get("value"):
            errors.append(
                "stale_review: request fingerprint does not match current candidate; "
                f"expected {candidate}, got {fingerprint.get('value')}"
            )
    return errors


def authorized_human_decision_identities(
    repo: Path, request: dict[str, Any] | None = None
) -> tuple[set[str], list[str]]:
    """Return identities sealed with the reviewed candidate.

    The live PLAN is deliberately not sufficient: it is part of the candidate
    and can change while a human decision is pending. A bound request records
    the positive identity set at sealing time and validation also proves that
    the live PLAN still names the same set.
    """
    try:
        plan = extract_embedded_json(repo / "PLAN.md", PLAN_BEGIN, PLAN_END)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return set(), [f"human_decision_identity: cannot load PLAN authority: {type(exc).__name__}: {exc}"]
    explicit_direction = plan.get("explicit_direction")
    if not isinstance(explicit_direction, dict):
        return set(), ["human_decision_identity: PLAN lacks explicit_direction authority"]
    speaker = explicit_direction.get("speaker")
    if not isinstance(speaker, str) or not speaker.strip():
        return set(), ["human_decision_identity: PLAN explicit_direction speaker must be non-empty"]
    live_identities = {speaker.strip()}
    if request is None:
        return live_identities, []
    sealed = request.get("authorized_human_decision_identities")
    if not isinstance(sealed, list) or not sealed or any(
        not isinstance(item, str) or not item.strip() for item in sealed
    ):
        return set(), ["human_decision_identity: review request lacks a sealed positive identity registry"]
    sealed_identities = {item.strip() for item in sealed}
    if live_identities != sealed_identities:
        return set(), [
            "human_decision_identity: current PLAN identity anchor differs from the sealed reviewed candidate"
        ]
    return sealed_identities, []


def canonical_human_decision_authority_path(decision_id: Any) -> str:
    return f"{HUMAN_DECISION_AUTHORITY_DIRECTORY}/{decision_id}.md"


def render_human_decision_authority_record(authority: dict[str, Any]) -> str:
    return (
        "# KGnote human decision authority\n\n"
        f"{HUMAN_DECISION_AUTHORITY_BEGIN}\n"
        "```json\n"
        f"{json.dumps(authority, indent=2, ensure_ascii=False)}\n"
        "```\n"
        f"{HUMAN_DECISION_AUTHORITY_END}\n"
    )


def validate_human_decision_authority_record(
    repo: Path,
    entry: dict[str, Any],
    request: dict[str, Any] | None = None,
) -> list[str]:
    decision_id = entry.get("decision_id")
    authority_record = str(entry.get("authority_record") or "")
    relative = authority_record.split("#", 1)[0]
    expected_relative = canonical_human_decision_authority_path(decision_id)
    path = repo / relative
    errors: list[str] = []
    try:
        path.resolve().relative_to(repo.resolve())
    except ValueError:
        return [f"review_decisions[{decision_id}]: authority_record escapes repository"]
    if authority_record != expected_relative:
        return [
            f"review_decisions[{decision_id}]: authority_record must be the dedicated canonical record "
            f"{expected_relative}"
        ]
    if not path.is_file():
        return [f"review_decisions[{decision_id}]: authority_record does not exist: {relative}"]
    authorized_identities, identity_errors = authorized_human_decision_identities(repo, request)
    errors.extend(identity_errors)
    decided_by = entry.get("decided_by")
    if decided_by not in authorized_identities:
        errors.append(
            f"review_decisions[{decision_id}]: decided_by is not a positively authorized human identity"
        )
    try:
        authority = extract_embedded_json(
            path,
            HUMAN_DECISION_AUTHORITY_BEGIN,
            HUMAN_DECISION_AUTHORITY_END,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return errors + [
            f"review_decisions[{decision_id}]: authority_record lacks structured human decision proof: {exc}"
        ]
    required = (
        "schema_version",
        "decision_id",
        "review_id",
        "candidate_revision",
        "candidate_fingerprint",
        "selected_option",
        "decided_by",
        "decided_at",
        "decision_evidence",
        "linked_findings",
    )
    errors.extend(missing_fields(authority, required, f"human_decision_authority[{decision_id}]"))
    if set(authority) != set(required):
        errors.append(
            f"review_decisions[{decision_id}]: authority_record must contain exactly the canonical fields"
        )
    if authority.get("schema_version") != "kgnote.human-decision-authority.v1":
        errors.append(f"review_decisions[{decision_id}]: authority_record has unsupported schema_version")
    for name in (
        "decision_id",
        "review_id",
        "candidate_revision",
        "candidate_fingerprint",
        "selected_option",
        "decided_by",
        "decided_at",
    ):
        if authority.get(name) != entry.get(name):
            errors.append(
                f"review_decisions[{decision_id}]: authority_record {name} does not match decision entry"
            )
    if not isinstance(authority.get("decision_evidence"), str) or not authority.get("decision_evidence", "").strip():
        errors.append(f"review_decisions[{decision_id}]: authority_record decision_evidence must be non-empty")
    authority_findings = authority.get("linked_findings")
    if not isinstance(authority_findings, list) or sorted(authority_findings) != sorted(entry.get("linked_findings", [])):
        errors.append(f"review_decisions[{decision_id}]: authority_record linked_findings do not match decision entry")
    canonical_authority = {name: authority.get(name) for name in required}
    try:
        actual_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"review_decisions[{decision_id}]: authority_record cannot be read: {exc}")
    else:
        if actual_text != render_human_decision_authority_record(canonical_authority):
            errors.append(
                f"review_decisions[{decision_id}]: authority_record contains non-canonical or unrelated content"
            )
    return errors


def validate_decisions(
    decisions: dict[str, Any],
    repo: Path | None = None,
    request: dict[str, Any] | None = None,
) -> list[str]:
    errors = missing_fields(decisions, ("schema_version", "protocol_version", "decisions"), "review_decisions")
    if errors:
        return errors
    if decisions.get("schema_version") != "kgnote.review-decisions.v1":
        errors.append("review_decisions: unsupported schema_version")
    if decisions.get("protocol_version") != REVIEW_PROTOCOL_VERSION:
        errors.append("review_decisions: unsupported protocol_version")
    entries = decisions.get("decisions")
    if not isinstance(entries, list):
        return errors + ["review_decisions: decisions must be an array"]
    seen: set[str] = set()
    required = (
        "decision_id", "question", "why_existing_authority_is_insufficient", "affected_requirements",
        "available_options", "observable_consequences", "blocking_scope", "linked_findings", "status",
        "review_id", "candidate_revision", "candidate_fingerprint",
        "selected_option", "decided_by", "decided_at", "authority_record",
    )
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("review_decisions: each decision must be an object")
            continue
        decision_id = entry.get("decision_id")
        errors.extend(missing_fields(entry, required, f"review_decisions[{decision_id or '?'}]"))
        if not isinstance(decision_id, str) or not re.fullmatch(r"D-[0-9]{3,}", decision_id):
            errors.append("review_decisions: invalid decision_id")
        elif decision_id in seen:
            errors.append(f"review_decisions: duplicate decision_id {decision_id}")
        seen.add(str(decision_id))
        if entry.get("status") not in {"PENDING_HUMAN", "DECIDED"}:
            errors.append(f"review_decisions[{decision_id}]: invalid status")
        if len(entry.get("available_options", [])) < 2 or len(entry.get("observable_consequences", [])) < 2:
            errors.append(f"review_decisions[{decision_id}]: at least two options and consequences are required")
        candidate = entry.get("candidate_fingerprint")
        if not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{64}", candidate):
            errors.append(f"review_decisions[{decision_id}]: invalid candidate_fingerprint")
        if entry.get("candidate_revision") is None or not str(entry.get("candidate_revision")).endswith(
            f"+worktree:{candidate}"
        ):
            errors.append(f"review_decisions[{decision_id}]: candidate_revision does not match candidate_fingerprint")
        if not isinstance(entry.get("review_id"), str) or not re.fullmatch(
            r"review-[a-z0-9-]+-[0-9]{3}", entry.get("review_id", "")
        ):
            errors.append(f"review_decisions[{decision_id}]: invalid review_id")
        if entry.get("status") == "PENDING_HUMAN":
            if any(entry.get(name) is not None for name in ("selected_option", "decided_by", "decided_at", "authority_record")):
                errors.append(f"review_decisions[{decision_id}]: pending decision must not select an option")
        elif any(not entry.get(name) for name in ("selected_option", "decided_by", "decided_at", "authority_record")):
            errors.append(f"review_decisions[{decision_id}]: decided entry lacks human decision evidence")
        else:
            if entry.get("selected_option") not in entry.get("available_options", []):
                errors.append(f"review_decisions[{decision_id}]: selected_option is not an available option")
            if repo is not None:
                errors.extend(validate_human_decision_authority_record(repo, entry, request))
    return errors


def validate_review_result(
    request: dict[str, Any], result: dict[str, Any], decisions: dict[str, Any]
) -> list[str]:
    errors = missing_fields(
        result,
        (
            "schema_version", "protocol_version", "artifact_state", "review_id", "author_role",
            "reviewer_identity", "reviewed_revision", "reviewed_fingerprint", "verdict", "findings",
            "verified_requirements", "unverified_requirements", "human_decisions_required",
            "human_gates_preserved", "reviewed_at",
        ),
        "review_result",
    )
    if errors:
        return errors
    if result.get("schema_version") != "kgnote.review-result.v1":
        errors.append("review_result: unsupported schema_version")
    if result.get("protocol_version") != REVIEW_PROTOCOL_VERSION:
        errors.append("review_result: unsupported protocol_version")
    state = result.get("artifact_state")
    if state == "EMPTY":
        nullable = (
            "review_id", "author_role", "reviewer_identity", "reviewed_revision",
            "reviewed_fingerprint", "verdict", "reviewed_at",
        )
        if any(result.get(name) is not None for name in nullable) or result.get("findings"):
            errors.append("review_result: EMPTY template contains submitted reviewer content")
        return errors
    if state != "SUBMITTED":
        return errors + ["review_result: artifact_state must be EMPTY or SUBMITTED"]
    if result.get("author_role") != "CHATGPT_WORK_REVIEWER":
        errors.append("review_result: submitted result must be authored by CHATGPT_WORK_REVIEWER")
    if not result.get("reviewer_identity"):
        errors.append("review_result: reviewer_identity is required")
    if result.get("review_id") != request.get("review_id"):
        errors.append("stale_review: result review_id does not match request")
    if result.get("reviewed_revision") != request.get("candidate_revision"):
        errors.append("stale_review: result revision does not match request")
    if result.get("reviewed_fingerprint") != request.get("candidate_fingerprint"):
        errors.append("stale_review: result fingerprint does not match request")
    verdict = result.get("verdict")
    if verdict not in REVIEW_VERDICTS:
        errors.append(f"review_result: invalid verdict {verdict!r}")
    findings = result.get("findings")
    if not isinstance(findings, list):
        return errors + ["review_result: findings must be an array"]
    seen: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    finding_required = (
        "finding_id", "severity", "authority_source", "expected_behavior", "observed_behavior",
        "evidence", "affected_files_or_behavior", "required_resolution", "verification_method", "status",
    )
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("review_result: each finding must be an object")
            continue
        finding_id = finding.get("finding_id")
        errors.extend(missing_fields(finding, finding_required, f"review_result[{finding_id or '?'}]"))
        if not isinstance(finding_id, str) or not re.fullmatch(r"R-[0-9]{3,}", finding_id):
            errors.append("review_result: invalid finding_id")
        elif finding_id in seen:
            errors.append(f"review_result: duplicate finding_id {finding_id}")
        seen.add(str(finding_id))
        if finding.get("severity") not in {"BLOCKER", "MAJOR", "MINOR"}:
            errors.append(f"review_result[{finding_id}]: invalid severity")
        if finding.get("status") not in FINDING_STATUSES:
            errors.append(f"review_result[{finding_id}]: invalid status")
        if finding.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}:
            unresolved.append(finding)
        for name in finding_required[2:9]:
            if not finding.get(name):
                errors.append(f"review_result[{finding_id}]: {name} must be non-empty")
    if verdict == "PASS":
        if unresolved:
            errors.append("review_result: PASS cannot contain unresolved findings")
        if result.get("unverified_requirements"):
            errors.append("review_result: PASS cannot retain unverified_requirements")
        if result.get("human_decisions_required"):
            errors.append("review_result: PASS cannot retain human_decisions_required")
        missing_gates = set(request.get("preserved_human_gates", [])) - set(result.get("human_gates_preserved", []))
        if missing_gates:
            errors.append(f"review_result: PASS did not preserve human gates {sorted(missing_gates)}")
    if verdict == "CHANGES_REQUIRED" and not unresolved:
        errors.append("review_result: CHANGES_REQUIRED requires an unresolved finding")
    if verdict == "PRODUCT_DECISION_REQUIRED":
        required_ids = set(result.get("human_decisions_required", []))
        known = {
            item.get("decision_id"): item
            for item in decisions.get("decisions", [])
            if isinstance(item, dict)
        }
        known_ids = set(known)
        if not required_ids or not required_ids <= known_ids:
            errors.append("review_result: PRODUCT_DECISION_REQUIRED needs linked decision records")
        for decision_id in sorted(required_ids & known_ids):
            decision = known[decision_id]
            if decision.get("review_id") != request.get("review_id"):
                errors.append(f"review_result: decision {decision_id} is bound to a different review_id")
            if decision.get("candidate_revision") != request.get("candidate_revision"):
                errors.append(f"review_result: decision {decision_id} is bound to a different candidate_revision")
            if decision.get("candidate_fingerprint") != request.get("candidate_fingerprint"):
                errors.append(f"review_result: decision {decision_id} is bound to a different candidate_fingerprint")
    if not result.get("reviewed_at"):
        errors.append("review_result: submitted result requires reviewed_at")
    return errors


def read_history_events(repo: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = repo / ".ai/REVIEW_HISTORY/events.jsonl"
    errors: list[str] = []
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"review_history: cannot read events.jsonl: {exc}"]
    for number, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"review_history: blank event line {number}")
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"review_history: invalid JSON line {number}: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"review_history: event line {number} is not an object")
            continue
        expected_id = f"evt-{number:04d}"
        if event.get("event_id") != expected_id:
            errors.append(f"review_history: expected {expected_id} at line {number}")
        snapshot = event.get("snapshot_path")
        digest = event.get("snapshot_sha256")
        if (snapshot is None) != (digest is None):
            errors.append(f"review_history: {expected_id} snapshot path/digest must both be null or set")
        if snapshot is not None:
            if not isinstance(snapshot, str) or not snapshot.startswith(".ai/REVIEW_HISTORY/"):
                errors.append(f"review_history: {expected_id} snapshot path escapes history")
            else:
                path = repo / snapshot
                if not path.is_file():
                    errors.append(f"review_history: {expected_id} missing snapshot {snapshot}")
                elif sha256_file(path) != digest:
                    errors.append(f"review_history: {expected_id} snapshot digest mismatch")
        events.append(event)
    return events, errors


def expected_history_actor(event: dict[str, Any]) -> str | None:
    event_type = event.get("event_type")
    if event_type == "IMPLEMENTATION_RESUMED":
        return (
            "HUMAN_DECISION_AUTHORITY"
            if event.get("source_verdict") == "PRODUCT_DECISION_REQUIRED"
            else "CODEX_IMPLEMENTER"
        )
    return {
        "PROTOCOL_INITIALIZED": "CODEX_IMPLEMENTER",
        "READY_FOR_REVIEW": "CODEX_IMPLEMENTER",
        "INVALIDATED": "CODEX_IMPLEMENTER",
        "UNDER_REVIEW": "CHATGPT_WORK_REVIEWER",
        "CHANGES_REQUIRED": "CHATGPT_WORK_REVIEWER",
        "PRODUCT_DECISION_REQUIRED": "CHATGPT_WORK_REVIEWER",
        "PASS": "CHATGPT_WORK_REVIEWER",
        "STALE_CANDIDATE": "CHATGPT_WORK_REVIEWER",
        "FIXES_PROPOSED": "CODEX_IMPLEMENTER",
        "HUMAN_DECISION_RECORDED": "HUMAN_DECISION_AUTHORITY",
        "STALE_CANDIDATE_INVALIDATED": "ORCHESTRATOR",
        "PASS_CONSUMED_FOR_PROGRESSION": "ORCHESTRATOR",
        "HISTORY_ACTOR_CORRECTION": "CODEX_IMPLEMENTER",
    }.get(event_type)


def validate_history_event_actors(
    events: list[dict[str, Any]],
) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    by_id = {event.get("event_id"): event for event in events}
    positions = {event.get("event_id"): position for position, event in enumerate(events)}
    corrections: dict[str, str] = {}
    for event in events:
        if event.get("event_type") != "HISTORY_ACTOR_CORRECTION":
            continue
        event_id = event.get("event_id")
        target_id = event.get("corrects_event_id")
        target = by_id.get(target_id)
        if target is None or positions.get(target_id, len(events)) >= positions.get(event_id, -1):
            errors.append(f"review_history: {event_id} correction target must be an earlier event")
            continue
        if target.get("event_type") == "HISTORY_ACTOR_CORRECTION":
            errors.append(f"review_history: {event_id} cannot correct another correction event")
            continue
        if target_id in corrections:
            errors.append(f"review_history: event {target_id} has multiple actor corrections")
            continue
        expected = expected_history_actor(target)
        corrected = event.get("corrected_actor_role")
        if expected is None:
            errors.append(f"review_history: {event_id} targets unsupported event type {target.get('event_type')!r}")
        elif corrected != expected:
            errors.append(
                f"review_history: {event_id} corrected_actor_role must be {expected}, got {corrected}"
            )
        elif target.get("actor_role") == corrected:
            errors.append(f"review_history: {event_id} correction is unnecessary for {target_id}")
        else:
            corrections[str(target_id)] = str(corrected)
    effective_roles: dict[str, str] = {}
    for event in events:
        event_id = str(event.get("event_id"))
        expected = expected_history_actor(event)
        effective = corrections.get(event_id, event.get("actor_role"))
        if expected is None:
            errors.append(f"review_history: {event_id} has unsupported event type {event.get('event_type')!r}")
        elif effective != expected:
            errors.append(
                f"review_history: {event_id} {event.get('event_type')} requires actor {expected}, got {effective}"
            )
        effective_roles[event_id] = str(effective)
    return errors, effective_roles


def decision_authorizes_finding(
    repo: Path,
    decision: dict[str, Any],
    finding_id: str,
) -> bool:
    return (
        decision.get("status") == "DECIDED"
        and isinstance(decision.get("linked_findings"), list)
        and finding_id in decision["linked_findings"]
        and not validate_human_decision_authority_record(repo, decision)
    )


def validate_review_history(
    repo: Path,
    result: dict[str, Any],
    request: dict[str, Any] | None = None,
    decisions: dict[str, Any] | None = None,
) -> list[str]:
    events, errors = read_history_events(repo)
    index_path = repo / ".ai/REVIEW_HISTORY/index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return errors + [f"review_history: invalid index: {exc}"]
    if index.get("schema_version") != "kgnote.review-history-index.v1":
        errors.append("review_history: unsupported index schema_version")
    if index.get("protocol_version") != REVIEW_PROTOCOL_VERSION:
        errors.append("review_history: unsupported index protocol_version")
    if index.get("event_count") != len(events):
        errors.append("review_history: index event_count differs from append-only log")
    expected_last = events[-1].get("event_id") if events else None
    if index.get("last_event_id") != expected_last:
        errors.append("review_history: index last_event_id differs from append-only log")
    actor_errors, effective_roles = validate_history_event_actors(events)
    errors.extend(actor_errors)
    replayed: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("event_type") == "HISTORY_ACTOR_CORRECTION":
            continue
        event_id = str(event.get("event_id"))
        for finding in event.get("findings", []):
            if not isinstance(finding, dict) or not finding.get("finding_id"):
                errors.append(f"review_history: {event_id} contains an invalid finding entry")
                continue
            finding_id = str(finding["finding_id"])
            new_status = finding.get("status")
            previous = replayed.get(finding_id)
            if previous is None:
                if effective_roles.get(event_id) != "CHATGPT_WORK_REVIEWER":
                    errors.append(
                        f"review_history: {event_id} finding {finding_id} creation requires CHATGPT_WORK_REVIEWER"
                    )
            elif previous.get("status") != new_status:
                transition_actor = effective_roles.get(event_id, "")
                if new_status == "SUPERSEDED_BY_HUMAN_DECISION":
                    authorized = any(
                        decision_authorizes_finding(repo, decision, finding_id)
                        for decision in (decisions or {}).get("decisions", [])
                        if isinstance(decision, dict)
                    )
                    if authorized:
                        transition_actor = "HUMAN_DECISION_AUTHORITY"
                for error in validate_finding_transition(previous.get("status"), new_status, transition_actor):
                    errors.append(f"review_history: {event_id} {finding_id}: {error}")
            replayed[finding_id] = {
                "status": new_status,
                "review_id": event.get("review_id"),
                "last_event_id": event_id,
            }
    indexed_findings = index.get("findings", {})
    for finding_id, replayed_state in replayed.items():
        if indexed_findings.get(finding_id) != replayed_state:
            errors.append(f"review_history: index finding {finding_id} differs from append-only replay")
    for finding_id in set(indexed_findings) - set(replayed):
        errors.append(f"review_history: index finding {finding_id} has no append-only event")
    current = {
        item.get("finding_id"): item for item in result.get("findings", []) if isinstance(item, dict)
    }
    if result.get("artifact_state") == "SUBMITTED":
        for finding_id, known in index.get("findings", {}).items():
            if known.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"} and finding_id not in current:
                errors.append(f"review_history: unresolved finding {finding_id} disappeared from current result")
                continue
            if finding_id not in current:
                continue
            old_status = known.get("status")
            new_status = current[finding_id].get("status")
            if old_status == new_status:
                continue
            actor_role = (
                "CODEX_IMPLEMENTER"
                if request is not None and request.get("status") == "IMPLEMENTING"
                else "CHATGPT_WORK_REVIEWER"
            )
            if new_status == "SUPERSEDED_BY_HUMAN_DECISION":
                linked_decisions = [
                    item.get("decision_id")
                    for item in (decisions or {}).get("decisions", [])
                    if isinstance(item, dict)
                    and decision_authorizes_finding(repo, item, finding_id)
                ]
                if linked_decisions:
                    actor_role = "HUMAN_DECISION_AUTHORITY"
                else:
                    errors.append(
                        f"review_history: finding {finding_id} cannot be superseded without a linked "
                        "DECIDED human decision and external authority_record"
                    )
            errors.extend(validate_finding_transition(old_status, new_status, actor_role))
    return errors


def history_unresolved_finding_ids(repo: Path) -> list[str]:
    index = json.loads((repo / ".ai/REVIEW_HISTORY/index.json").read_text(encoding="utf-8"))
    return sorted(
        finding_id
        for finding_id, item in index.get("findings", {}).items()
        if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
    )


def validate_review_artifacts(
    repo: Path,
    *,
    fingerprint: dict[str, Any] | None = None,
    check_status: bool = True,
) -> tuple[list[str], dict[str, Any]]:
    try:
        request, result, decisions = load_review_artifacts(repo)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"review_artifacts: cannot load current artifacts: {type(exc).__name__}: {exc}"], {}
    fingerprint = fingerprint or repository_fingerprint(repo)
    errors = validate_review_request(repo, request, fingerprint)
    errors.extend(validate_review_request_summary(repo, request))
    errors.extend(validate_decisions(decisions, repo, request))
    errors.extend(validate_review_result(request, result, decisions))
    errors.extend(validate_review_history(repo, result, request, decisions))
    if check_status:
        try:
            _, status = load_plan_status(repo)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"review_artifacts: cannot compare CODEX_STATUS: {exc}")
        else:
            status_review = status.get("review", {})
            if status_review.get("state") != request.get("status"):
                errors.append("review_state_drift: CODEX_STATUS review state differs from request")
            if status_review.get("current_review_id") != (
                request.get("review_id") if request.get("status") != "IMPLEMENTING" else None
            ):
                errors.append("review_state_drift: CODEX_STATUS current_review_id differs from request")
            if status_review.get("candidate_fingerprint") != request.get("candidate_fingerprint"):
                errors.append("review_state_drift: CODEX_STATUS candidate fingerprint differs from request")
            try:
                history_unresolved = set(history_unresolved_finding_ids(repo))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"review_state_drift: cannot read finding history: {exc}")
            else:
                current_unresolved = {
                    item.get("finding_id") for item in result.get("findings", [])
                    if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
                }
                expected_unresolved = sorted(history_unresolved | current_unresolved)
                recorded_unresolved = sorted(status_review.get("unresolved_findings", []))
                if recorded_unresolved != expected_unresolved:
                    errors.append(
                        "review_state_drift: CODEX_STATUS unresolved_findings does not match current/history ledger"
                    )
    return errors, {"request": request, "result": result, "decisions": decisions, "fingerprint": fingerprint}


def validate_pending_review_result(repo: Path) -> tuple[list[str], dict[str, Any]]:
    """Reviewer-safe validation before orchestrator submission.

    A newly written result is reviewer-owned while CODEX_STATUS is still the
    orchestrator-owned UNDER_REVIEW projection.  Validate all candidate,
    schema, decision, finding, and immutable-history rules without demanding
    the post-submit STATUS projection prematurely.
    """
    return validate_review_artifacts(repo, check_status=False)


def validate_review_transition(old: str, new: str, actor_role: str) -> list[str]:
    allowed = {
        ("IMPLEMENTING", "READY_FOR_REVIEW"): "CODEX_IMPLEMENTER",
        ("READY_FOR_REVIEW", "UNDER_REVIEW"): "CHATGPT_WORK_REVIEWER",
        ("READY_FOR_REVIEW", "IMPLEMENTING"): "CODEX_IMPLEMENTER",
        ("UNDER_REVIEW", "CHANGES_REQUIRED"): "CHATGPT_WORK_REVIEWER",
        ("UNDER_REVIEW", "PRODUCT_DECISION_REQUIRED"): "CHATGPT_WORK_REVIEWER",
        ("UNDER_REVIEW", "PASS"): "CHATGPT_WORK_REVIEWER",
        ("CHANGES_REQUIRED", "IMPLEMENTING"): "CODEX_IMPLEMENTER",
        ("PRODUCT_DECISION_REQUIRED", "IMPLEMENTING"): "HUMAN_DECISION_AUTHORITY",
    }
    expected = allowed.get((old, new))
    if expected is None:
        return [f"review_transition: forbidden transition {old} -> {new}"]
    if actor_role != expected:
        return [f"review_transition: {old} -> {new} requires {expected}, got {actor_role}"]
    return []


def validate_finding_transition(old: str, new: str, actor_role: str) -> list[str]:
    allowed = {
        ("OPEN", "FIXED_PENDING_REVIEW"): "CODEX_IMPLEMENTER",
        ("FIXED_PENDING_REVIEW", "VERIFIED"): "CHATGPT_WORK_REVIEWER",
        ("FIXED_PENDING_REVIEW", "OPEN"): "CHATGPT_WORK_REVIEWER",
        ("OPEN", "SUPERSEDED_BY_HUMAN_DECISION"): "HUMAN_DECISION_AUTHORITY",
        ("FIXED_PENDING_REVIEW", "SUPERSEDED_BY_HUMAN_DECISION"): "HUMAN_DECISION_AUTHORITY",
    }
    expected = allowed.get((old, new))
    if expected is None:
        return [f"finding_transition: forbidden transition {old} -> {new}"]
    if actor_role != expected:
        return [f"finding_transition: {old} -> {new} requires {expected}, got {actor_role}"]
    return []


def review_progression_blockers(
    request: dict[str, Any],
    result: dict[str, Any],
    decisions: dict[str, Any],
    plan: dict[str, Any],
    fingerprint: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if request.get("status") in {"READY_FOR_REVIEW", "UNDER_REVIEW"} and result.get("artifact_state") != "SUBMITTED":
        blockers.append("review_block: missing review result cannot be interpreted as PASS")
    if request.get("candidate_fingerprint") and request.get("candidate_fingerprint") != fingerprint.get("value"):
        blockers.append("review_block: candidate fingerprint changed; review is stale")
    verdict = result.get("verdict") if result.get("artifact_state") == "SUBMITTED" else None
    if verdict == "CHANGES_REQUIRED":
        blockers.append("review_block: CHANGES_REQUIRED blocks progression")
    if verdict == "PRODUCT_DECISION_REQUIRED":
        pending = [item.get("decision_id") for item in decisions.get("decisions", []) if item.get("status") == "PENDING_HUMAN"]
        blockers.append(f"review_block: PRODUCT_DECISION_REQUIRED blocks affected scope; pending {pending}")
    unresolved = [
        item.get("finding_id") for item in result.get("findings", [])
        if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
    ]
    if unresolved:
        blockers.append(f"review_block: unresolved findings {unresolved}")
    # Preserved product/human gates remain pending, but they do not turn a
    # fingerprint-bound reviewer PASS into a manual continuation prompt.  The
    # orchestrator evaluates the next work package's own human checkpoint and
    # stops there.  This keeps PA-HUMAN-1 and NS-HUMAN-SMOKE unpromoted without
    # blocking unrelated, already-authorized machine progression.
    return blockers


def append_history_event(repo: Path, event: dict[str, Any]) -> None:
    events, errors = read_history_events(repo)
    if errors:
        raise ValueError("; ".join(errors))
    event = dict(event)
    event["event_id"] = f"evt-{len(events) + 1:04d}"
    path = repo / ".ai/REVIEW_HISTORY/events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n")
    index_path = repo / ".ai/REVIEW_HISTORY/index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["event_count"] = len(events) + 1
    index["last_event_id"] = event["event_id"]
    review_id = event.get("review_id")
    if review_id:
        review = index.setdefault("reviews", {}).setdefault(review_id, {"snapshots": []})
        if event.get("snapshot_path"):
            review["snapshots"].append(
                {"path": event["snapshot_path"], "sha256": event["snapshot_sha256"], "event_id": event["event_id"]}
            )
        review["last_event_type"] = event.get("event_type")
        review["candidate_fingerprint"] = event.get("candidate_fingerprint")
    for finding in event.get("findings", []):
        index.setdefault("findings", {})[finding["finding_id"]] = {
            "status": finding["status"],
            "review_id": review_id,
            "last_event_id": event["event_id"],
        }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_history_actor_correction(repo: Path, event_id: str, reason: str) -> dict[str, Any]:
    events, errors = read_history_events(repo)
    if errors:
        raise ValueError("; ".join(errors))
    target = next((event for event in events if event.get("event_id") == event_id), None)
    if target is None:
        raise ValueError(f"review_history_correction: unknown event {event_id}")
    if target.get("event_type") == "HISTORY_ACTOR_CORRECTION":
        raise ValueError("review_history_correction: correction events cannot be corrected")
    if any(event.get("corrects_event_id") == event_id for event in events):
        raise ValueError(f"review_history_correction: event {event_id} already has a correction")
    corrected_actor = expected_history_actor(target)
    if corrected_actor is None:
        raise ValueError(f"review_history_correction: unsupported event type {target.get('event_type')!r}")
    if target.get("actor_role") == corrected_actor:
        raise ValueError(f"review_history_correction: event {event_id} already has the required actor")
    if not reason.strip():
        raise ValueError("review_history_correction: reason is required")
    correction = {
        "event_type": "HISTORY_ACTOR_CORRECTION",
        "review_id": target.get("review_id"),
        "actor_role": "CODEX_IMPLEMENTER",
        "candidate_fingerprint": target.get("candidate_fingerprint"),
        "snapshot_path": None,
        "snapshot_sha256": None,
        "corrects_event_id": event_id,
        "prior_actor_role": target.get("actor_role"),
        "corrected_actor_role": corrected_actor,
        "reason": reason.strip(),
        "created_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
    }
    append_history_event(repo, correction)
    return correction


def archive_review_artifact(
    repo: Path,
    relative: str,
    review_id: str,
    kind: str,
    event_type: str,
    candidate_fingerprint: str | None,
    findings: list[dict[str, Any]] | None = None,
) -> str:
    source = repo / relative
    data = source.read_bytes()
    digest = sha256_bytes(data)
    cycle = repo / ".ai/REVIEW_HISTORY" / review_id
    cycle.mkdir(parents=True, exist_ok=True)
    target = cycle / f"{kind}-{digest}.md"
    if target.exists() and target.read_bytes() != data:
        raise ValueError(f"review_history: immutable snapshot collision at {target}")
    if not target.exists():
        target.write_bytes(data)
    snapshot = str(target.relative_to(repo))
    actor_role = {
        "request": "CODEX_IMPLEMENTER",
        "resolution": (
            "HUMAN_DECISION_AUTHORITY"
            if event_type == "HUMAN_DECISION_RECORDED"
            else "CODEX_IMPLEMENTER"
        ),
    }.get(kind, "CHATGPT_WORK_REVIEWER")
    append_history_event(
        repo,
        {
            "event_type": event_type,
            "review_id": review_id,
            "actor_role": actor_role,
            "candidate_fingerprint": candidate_fingerprint,
            "snapshot_path": snapshot,
            "snapshot_sha256": digest,
            "findings": findings or [],
            "created_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        },
    )
    return snapshot


def load_verification_evidence(repo: Path, relative: str, fingerprint: dict[str, Any]) -> dict[str, Any]:
    path = (repo / relative).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise ValueError("review_request: verification evidence escapes repository") from exc
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("result") != "pass" or evidence.get("claims", {}).get("candidate_verified") is not True:
        raise ValueError("review_request: verification evidence is not a passing candidate verification")
    if evidence.get("claims", {}).get("release_verified") is not False:
        raise ValueError("review_request: local evidence improperly promotes release_verified")
    if evidence.get("fingerprint_stable") is not True:
        raise ValueError("review_request: verification evidence is not fingerprint-stable")
    for name in ("fingerprint_before", "fingerprint_after"):
        if evidence.get(name, {}).get("value") != fingerprint.get("value"):
            raise ValueError(f"review_request: {name} does not match current candidate")
    return evidence


def repository_relative_command(repo: Path, command: list[Any]) -> str:
    """Render verification commands without persisting host-specific repo paths."""
    repo_prefix = str(repo.resolve())
    return " ".join(str(part).replace(repo_prefix, ".") for part in command)


def empty_review_result() -> dict[str, Any]:
    return {
        "schema_version": "kgnote.review-result.v1",
        "protocol_version": REVIEW_PROTOCOL_VERSION,
        "artifact_state": "EMPTY",
        "review_id": None,
        "author_role": None,
        "reviewer_identity": None,
        "reviewed_revision": None,
        "reviewed_fingerprint": None,
        "verdict": None,
        "findings": [],
        "verified_requirements": [],
        "unverified_requirements": [],
        "human_decisions_required": [],
        "human_gates_preserved": [],
        "reviewed_at": None,
    }


def next_review_id(review_id: str) -> str:
    match = re.fullmatch(r"(review-[a-z0-9-]+-)([0-9]{3})", review_id)
    if not match:
        raise ValueError("review_request: cannot increment invalid review_id")
    return f"{match.group(1)}{int(match.group(2)) + 1:03d}"


def prepare_review_request(
    repo: Path,
    evidence_path: str,
    changed_areas: list[str],
    reviewer_focus: list[str],
    known_deviations: list[str],
    known_uncertainties: list[str],
) -> dict[str, Any]:
    preflight_result = preflight(repo)
    if preflight_result.get("status") != "pass":
        raise ValueError(f"review_request: preflight failed: {preflight_result.get('errors')}")
    plan, status = load_plan_status(repo)
    request, result, _ = load_review_artifacts(repo)
    if request.get("status") != "IMPLEMENTING":
        raise ValueError("review_request: current state must be IMPLEMENTING")
    previous_result = result.get("artifact_state") == "SUBMITTED"
    carried_findings: list[str] = []
    if previous_result:
        if result.get("verdict") == "CHANGES_REQUIRED":
            still_open = [
                item.get("finding_id") for item in result.get("findings", [])
                if item.get("status") == "OPEN"
            ]
            if still_open:
                raise ValueError(f"review_request: unresolved OPEN findings remain {still_open}")
        elif result.get("verdict") == "PRODUCT_DECISION_REQUIRED":
            unresolved_decisions = [
                item.get("decision_id") for item in load_review_artifacts(repo)[2].get("decisions", [])
                if item.get("decision_id") in result.get("human_decisions_required", [])
                and item.get("status") != "DECIDED"
            ]
            if unresolved_decisions:
                raise ValueError(f"review_request: human decisions remain unresolved {unresolved_decisions}")
        else:
            raise ValueError("review_request: PASS is terminal; candidate changes require explicit invalidation")
        archive_review_artifact(
            repo,
            ".ai/REVIEW_RESULT.md",
            request["review_id"],
            "resolution",
            "FIXES_PROPOSED" if result.get("verdict") == "CHANGES_REQUIRED" else "HUMAN_DECISION_RECORDED",
            request.get("candidate_fingerprint"),
            result.get("findings", []),
        )
        carried_findings = sorted(
            item["finding_id"] for item in result.get("findings", [])
            if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
        )
        request["review_id"] = next_review_id(request["review_id"])
        result = empty_review_result()
        replace_embedded_json(repo / ".ai/REVIEW_RESULT.md", REVIEW_RESULT_BEGIN, REVIEW_RESULT_END, result)
    elif result.get("artifact_state") != "EMPTY":
        raise ValueError("review_request: current result must be EMPTY before a new request")
    fingerprint = repository_fingerprint(repo)
    manifest = repository_manifest(repo)
    evidence = load_verification_evidence(repo, evidence_path, fingerprint)
    now = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    request["milestone_id"] = plan.get("active_milestone_id")
    request["status"] = "READY_FOR_REVIEW"
    request["candidate_fingerprint"] = fingerprint["value"]
    request["candidate_revision"] = f"{fingerprint['head']}+worktree:{fingerprint['value']}"
    request["candidate_manifest"] = manifest
    identities, identity_errors = authorized_human_decision_identities(repo)
    if identity_errors:
        raise ValueError("; ".join(identity_errors))
    request["authorized_human_decision_identities"] = sorted(identities)
    request["changed_areas"] = changed_areas
    active_milestone = next(
        (
            item for item in plan.get("milestones", [])
            if item.get("id") == plan.get("active_milestone_id")
        ),
        None,
    )
    request["acceptance_criteria"] = list(
        active_milestone.get("acceptance", []) if active_milestone else []
    )
    request["validation_performed"] = [
        repository_relative_command(repo, gate.get("command", []))
        for gate in evidence.get("gates", [])
    ]
    request["validation_results"] = [
        {
            "name": gate.get("name", "unknown"),
            "status": "PASS" if gate.get("passed") else "FAIL",
            "evidence": f"{evidence_path}#{gate.get('name', 'unknown')}",
        }
        for gate in evidence.get("gates", [])
    ]
    request["known_deviations"] = known_deviations
    request["known_uncertainties"] = known_uncertainties
    request["reviewer_focus"] = list(reviewer_focus)
    if carried_findings:
        request["reviewer_focus"].append(
            f"Re-verify carried unresolved findings from immutable history: {', '.join(carried_findings)}."
        )
    request["requested_at"] = now
    errors = validate_review_request(repo, request, fingerprint)
    if errors:
        raise ValueError("; ".join(errors))
    write_review_request(repo, request)
    snapshot = archive_review_artifact(
        repo,
        ".ai/REVIEW_REQUEST.md",
        request["review_id"],
        "request",
        "READY_FOR_REVIEW",
        fingerprint["value"],
    )
    status["updated_at"] = now
    status["implementation_state"] = "READY_FOR_REVIEW"
    status["review"] = {
        "state": "READY_FOR_REVIEW",
        "current_review_id": request["review_id"],
        "candidate_revision": request["candidate_revision"],
        "candidate_fingerprint": request["candidate_fingerprint"],
        "unresolved_findings": carried_findings,
        "human_decision_blockers": [],
    }
    status["verification"]["candidate_verified"] = True
    status["verification"]["release_verified"] = False
    status["verification"]["control_plane_ready"] = True
    status["verification"]["last_candidate_evidence"] = evidence_path
    status["verification"]["last_verified_fingerprint"] = fingerprint["value"]
    status["verification"]["last_result"] = (
        "Deterministic verification passed for the exact candidate; semantic review is pending."
    )
    status["next_action"] = (
        "STOP semantic progression. ChatGPT Work must follow .ai/REVIEWER_BOOTSTRAP.md and review "
        f"{request['review_id']} at the recorded fingerprint."
    )
    write_status(repo, status)
    return {"review_id": request["review_id"], "candidate_fingerprint": fingerprint["value"], "snapshot": snapshot}


def accept_review_custody(repo: Path, reviewer_identity: str) -> None:
    request, result, _ = load_review_artifacts(repo)
    fingerprint = repository_fingerprint(repo)
    errors, _ = validate_review_artifacts(repo, fingerprint=fingerprint)
    errors.extend(validate_review_transition(request.get("status"), "UNDER_REVIEW", "CHATGPT_WORK_REVIEWER"))
    if result.get("artifact_state") != "EMPTY":
        errors.append("review_custody: result must be EMPTY")
    if not reviewer_identity:
        errors.append("review_custody: reviewer identity is required")
    if errors:
        raise ValueError("; ".join(errors))
    request["status"] = "UNDER_REVIEW"
    write_review_request(repo, request)
    _, status = load_plan_status(repo)
    status["updated_at"] = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    status["implementation_state"] = "UNDER_REVIEW"
    status["review"]["state"] = "UNDER_REVIEW"
    status["next_action"] = f"Reviewer {reviewer_identity} owns the frozen review; Codex must not change the candidate."
    write_status(repo, status)
    append_history_event(
        repo,
        {
            "event_type": "UNDER_REVIEW",
            "review_id": request["review_id"],
            "actor_role": "CHATGPT_WORK_REVIEWER",
            "candidate_fingerprint": request["candidate_fingerprint"],
            "snapshot_path": None,
            "snapshot_sha256": None,
            "reviewer_identity": reviewer_identity,
            "created_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        },
    )


def invalidate_ready_request(repo: Path, reason: str) -> dict[str, Any]:
    request, result, _ = load_review_artifacts(repo)
    plan, status = load_plan_status(repo)
    if not reason.strip():
        raise ValueError("review_invalidate: a concrete reason is required")
    errors = validate_review_transition(request.get("status"), "IMPLEMENTING", "CODEX_IMPLEMENTER")
    if result.get("artifact_state") != "EMPTY":
        errors.append("review_invalidate: cannot invalidate after reviewer result content exists")
    if errors:
        raise ValueError("; ".join(errors))
    old_review_id = request["review_id"]
    old_fingerprint = request.get("candidate_fingerprint")
    request["review_id"] = next_review_id(old_review_id)
    request["status"] = "IMPLEMENTING"
    request["candidate_revision"] = None
    request["candidate_fingerprint"] = None
    request["requested_at"] = None
    active = next(
        (item for item in plan.get("milestones", []) if item.get("id") == plan.get("active_milestone_id")),
        None,
    )
    if active is not None:
        request["milestone_id"] = active["id"]
        request["acceptance_criteria"] = list(active.get("acceptance", []))
    write_review_request(repo, request)
    now = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    status["updated_at"] = now
    status["implementation_state"] = "IMPLEMENTING"
    status["review"] = {
        "state": "IMPLEMENTING",
        "current_review_id": None,
        "candidate_revision": None,
        "candidate_fingerprint": None,
        "unresolved_findings": history_unresolved_finding_ids(repo),
        "human_decision_blockers": [],
    }
    status["verification"]["candidate_verified"] = False
    status["verification"]["control_plane_ready"] = False
    status["verification"]["release_verified"] = False
    status["verification"]["last_result"] = (
        f"Review {old_review_id} was invalidated before reviewer custody: {reason.strip()}"
    )
    status["next_action"] = (
        "Repair the invalidated candidate within current authority, rerun deterministic verification, "
        f"and issue {request['review_id']}."
    )
    write_status(repo, status)
    append_history_event(
        repo,
        {
            "event_type": "INVALIDATED",
            "review_id": old_review_id,
            "actor_role": "CODEX_IMPLEMENTER",
            "candidate_fingerprint": old_fingerprint,
            "snapshot_path": None,
            "snapshot_sha256": None,
            "reason": reason.strip(),
            "created_at": now,
        },
    )
    return {"invalidated_review_id": old_review_id, "next_review_id": request["review_id"]}


def invalidate_stale_review(repo: Path, reason: str) -> dict[str, Any]:
    """Invalidate a sealed/in-custody candidate whose bytes changed.

    This is recovery, never approval: the old request/result remain in the
    append-only history and a fresh review ID is allocated before returning to
    implementation.  It exists separately from pre-custody invalidation so a
    crash or accidental mutation during reviewer custody cannot strand the
    autonomous loop or tempt it to reuse a stale verdict.
    """
    request, result, _ = load_review_artifacts(repo)
    plan, status = load_plan_status(repo)
    if request.get("status") not in {"READY_FOR_REVIEW", "UNDER_REVIEW", "PASS"}:
        raise ValueError("stale_review_invalidate: candidate is not sealed or in reviewer custody")
    if not reason.strip():
        raise ValueError("stale_review_invalidate: a concrete reason is required")
    old_review_id = request["review_id"]
    old_fingerprint = request.get("candidate_fingerprint")
    if result.get("artifact_state") == "SUBMITTED":
        archive_review_artifact(
            repo,
            ".ai/REVIEW_RESULT.md",
            old_review_id,
            "stale-result",
            "STALE_CANDIDATE",
            old_fingerprint,
            result.get("findings", []),
        )
    request["review_id"] = next_review_id(old_review_id)
    request["status"] = "IMPLEMENTING"
    request["candidate_revision"] = None
    request["candidate_fingerprint"] = None
    request["requested_at"] = None
    active = next(
        (item for item in plan.get("milestones", []) if item.get("id") == plan.get("active_milestone_id")),
        None,
    )
    if active is not None:
        request["milestone_id"] = active["id"]
        request["acceptance_criteria"] = list(active.get("acceptance", []))
    write_review_request(repo, request)
    replace_embedded_json(
        repo / ".ai/REVIEW_RESULT.md", REVIEW_RESULT_BEGIN, REVIEW_RESULT_END, empty_review_result()
    )
    now = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    fingerprint = repository_fingerprint(repo)
    status["updated_at"] = now
    status["implementation_state"] = "IMPLEMENTING"
    status["working_state"]["fingerprint"] = fingerprint["value"]
    status["review"] = {
        "state": "IMPLEMENTING",
        "current_review_id": None,
        "candidate_revision": None,
        "candidate_fingerprint": None,
        "unresolved_findings": history_unresolved_finding_ids(repo),
        "human_decision_blockers": [],
    }
    status["verification"]["candidate_verified"] = False
    status["verification"]["control_plane_ready"] = False
    status["verification"]["release_verified"] = False
    status["verification"]["last_result"] = (
        f"Review {old_review_id} became stale and was invalidated: {reason.strip()}"
    )
    status["next_action"] = (
        "Inspect the candidate drift, repair within current authority, validate a new fingerprint, "
        f"and issue {request['review_id']} without waiting for human continuation."
    )
    write_status(repo, status)
    append_history_event(
        repo,
        {
            "event_type": "STALE_CANDIDATE_INVALIDATED",
            "review_id": old_review_id,
            "actor_role": "ORCHESTRATOR",
            "candidate_fingerprint": old_fingerprint,
            "replacement_fingerprint": fingerprint["value"],
            "snapshot_path": None,
            "snapshot_sha256": None,
            "reason": reason.strip(),
            "created_at": now,
        },
    )
    return {
        "invalidated_review_id": old_review_id,
        "next_review_id": request["review_id"],
        "replacement_fingerprint": fingerprint["value"],
    }


def sync_implementing_fingerprint(
    repo: Path,
    reason: str,
    next_action: str | None = None,
) -> dict[str, Any]:
    """Synchronize factual STATUS after authorized implementation changed bytes."""
    request, _, _ = load_review_artifacts(repo)
    if request.get("status") != "IMPLEMENTING":
        raise ValueError("fingerprint_sync: only IMPLEMENTING may adopt changed candidate bytes")
    fingerprint = repository_fingerprint(repo)
    _, status = load_plan_status(repo)
    status["updated_at"] = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    status["working_state"]["fingerprint"] = fingerprint["value"]
    status["verification"]["candidate_verified"] = False
    status["verification"]["control_plane_ready"] = False
    status["verification"]["release_verified"] = False
    status["verification"]["last_result"] = reason.strip() or "Authorized implementation changed candidate bytes."
    status["next_action"] = next_action or (
        "Run deterministic validation; on success create the next fingerprint-bound review request."
    )
    write_status(repo, status)
    return fingerprint


def resume_implementation(repo: Path) -> dict[str, Any] | None:
    request, result, decisions = load_review_artifacts(repo)
    decision_errors = validate_decisions(decisions, repo, request)
    if decision_errors:
        raise ValueError("; ".join(decision_errors))
    verdict = result.get("verdict")
    if request.get("status") not in {"CHANGES_REQUIRED", "PRODUCT_DECISION_REQUIRED"}:
        raise ValueError("review_resume: current state is not resumable")
    actor = "CODEX_IMPLEMENTER"
    if request.get("status") == "PRODUCT_DECISION_REQUIRED":
        required = set(result.get("human_decisions_required", []))
        decided = {
            item.get("decision_id") for item in decisions.get("decisions", [])
            if item.get("status") == "DECIDED"
        }
        if not required or not required <= decided:
            raise ValueError("review_resume: required human decision is not durably decided")
        decision_errors = validate_human_decision_delta(repo, request, decisions, required)
        if decision_errors:
            raise ValueError("; ".join(decision_errors))
        actor = "HUMAN_DECISION_AUTHORITY"
    errors = validate_review_transition(request["status"], "IMPLEMENTING", actor)
    if errors:
        raise ValueError("; ".join(errors))
    request["status"] = "IMPLEMENTING"
    write_review_request(repo, request)
    _, status = load_plan_status(repo)
    status["updated_at"] = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    status["implementation_state"] = "IMPLEMENTING"
    status["review"]["state"] = "IMPLEMENTING"
    status["review"]["current_review_id"] = None
    status["next_action"] = (
        "Implement only the authority-bounded resolutions, preserve finding IDs, rerun deterministic verification, "
        "and issue a new fingerprint-bound review request."
    )
    write_status(repo, status)
    append_history_event(
        repo,
        {
            "event_type": "IMPLEMENTATION_RESUMED",
            "review_id": request["review_id"],
            "actor_role": actor,
            "candidate_fingerprint": request.get("candidate_fingerprint"),
            "snapshot_path": None,
            "snapshot_sha256": None,
            "source_verdict": verdict,
            "created_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        },
    )
    if actor == "HUMAN_DECISION_AUTHORITY":
        return sync_implementing_fingerprint(
            repo,
            "Validated human decision authority changed candidate bytes; the IMPLEMENTING state adopted the new fingerprint.",
            "Invoke a fresh implementer for only the human-authorized resolution, then run deterministic validation.",
        )
    return None


def mark_finding_fixed(repo: Path, finding_id: str, evidence: list[str]) -> None:
    request, result, _ = load_review_artifacts(repo)
    if request.get("status") != "IMPLEMENTING" or result.get("verdict") != "CHANGES_REQUIRED":
        raise ValueError("finding_resolution: findings may be marked fixed only while implementing CHANGES_REQUIRED")
    finding = next((item for item in result.get("findings", []) if item.get("finding_id") == finding_id), None)
    if finding is None:
        raise ValueError(f"finding_resolution: unknown finding {finding_id}")
    errors = validate_finding_transition(finding.get("status"), "FIXED_PENDING_REVIEW", "CODEX_IMPLEMENTER")
    if errors:
        raise ValueError("; ".join(errors))
    if not evidence:
        raise ValueError("finding_resolution: resolution evidence is required")
    finding["status"] = "FIXED_PENDING_REVIEW"
    finding["resolution_evidence"] = evidence
    replace_embedded_json(repo / ".ai/REVIEW_RESULT.md", REVIEW_RESULT_BEGIN, REVIEW_RESULT_END, result)
    _, status = load_plan_status(repo)
    status["review"]["unresolved_findings"] = [
        item["finding_id"] for item in result.get("findings", [])
        if item.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
    ]
    write_status(repo, status)


def archive_submitted_result(repo: Path) -> dict[str, Any]:
    request, result, decisions = load_review_artifacts(repo)
    fingerprint = repository_fingerprint(repo)
    errors = validate_review_request(repo, request, fingerprint)
    errors.extend(validate_decisions(decisions, repo, request))
    errors.extend(validate_review_result(request, result, decisions))
    errors.extend(validate_review_history(repo, result, request, decisions))
    errors.extend(validate_review_transition(request.get("status"), result.get("verdict"), "CHATGPT_WORK_REVIEWER"))
    if errors:
        raise ValueError("; ".join(errors))
    snapshot = archive_review_artifact(
        repo,
        ".ai/REVIEW_RESULT.md",
        request["review_id"],
        "result",
        result["verdict"],
        request["candidate_fingerprint"],
        result.get("findings", []),
    )
    request["status"] = result["verdict"]
    write_review_request(repo, request)
    _, status = load_plan_status(repo)
    unresolved = [
        finding["finding_id"] for finding in result.get("findings", [])
        if finding.get("status") in {"OPEN", "FIXED_PENDING_REVIEW"}
    ]
    status["updated_at"] = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    status["implementation_state"] = result["verdict"]
    status["review"]["state"] = result["verdict"]
    status["review"]["unresolved_findings"] = unresolved
    status["review"]["human_decision_blockers"] = result.get("human_decisions_required", [])
    status["next_action"] = {
        "PASS": "Review PASS is bound to this candidate. Preserve human gates and consult PLAN before progression.",
        "CHANGES_REQUIRED": "Codex must read every unresolved finding, fix within authority, and re-request review.",
        "PRODUCT_DECISION_REQUIRED": "STOP affected implementation until the human decision is durably recorded.",
    }[result["verdict"]]
    write_status(repo, status)
    return {"review_id": request["review_id"], "verdict": result["verdict"], "snapshot": snapshot}


def path_is_owned(path: str, owned: str) -> bool:
    normalized = owned.rstrip("/")
    if owned.endswith("/"):
        return path == normalized or path.startswith(normalized + "/")
    return path == owned


def allowed_dirty_paths(plan: dict[str, Any]) -> list[str]:
    allowed: list[str] = []
    for milestone in plan.get("milestones", []):
        if milestone.get("status") in {"complete", "active"}:
            allowed.extend(x for x in milestone.get("owned_paths", []) if isinstance(x, str))
    return sorted(set(allowed))


def unexpected_dirty_paths(changed: Iterable[str], plan: dict[str, Any]) -> list[str]:
    allowed = allowed_dirty_paths(plan)
    return sorted(path for path in changed if not any(path_is_owned(path, item) for item in allowed))


def changed_paths(repo: Path) -> list[str]:
    tracked = run_git(repo, "diff", "--name-only", "-z", "HEAD").stdout.split(b"\0")
    untracked = run_git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
    return sorted(
        {
            item.decode("utf-8", "surrogateescape")
            for item in tracked + untracked
            if item
        }
    )


def python_test_selectors(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    selectors: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            selectors.add(node.name)
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test"):
                    selectors.add(f"{node.name}.{child.name}")
    return selectors


def javascript_test_selectors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"\b(?:test|it)\s*\(\s*([\"'])(.*?)\1", re.DOTALL)
    return {match.group(2) for match in pattern.finditer(text)}


def validate_test_ref(repo: Path, ref: dict[str, Any]) -> str | None:
    relative = ref.get("path")
    selector = ref.get("selector")
    if not isinstance(relative, str) or not isinstance(selector, str):
        return "selector_integrity: test ref requires string path and selector"
    path = repo / relative
    if not path.is_file():
        return f"selector_integrity: missing test file {relative}"
    try:
        if path.suffix == ".py":
            available = python_test_selectors(path)
        elif path.suffix in {".js", ".mjs", ".cjs"}:
            available = javascript_test_selectors(path)
        else:
            return f"selector_integrity: unsupported test file type {relative}"
    except (OSError, SyntaxError, UnicodeError) as exc:
        return f"selector_integrity: cannot inspect {relative}: {exc}"
    if selector not in available:
        return f"selector_integrity: {relative} has no exact selector {selector!r}"
    return None


def validate_selectors(repo: Path, scenarios_path: Path | None = None) -> list[str]:
    scenarios_path = scenarios_path or repo / "docs/requirements/scenarios.json"
    try:
        cases = json.loads(scenarios_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"selector_integrity: invalid scenarios file: {exc}"]
    errors: list[str] = []
    for case in cases.get("scenarios", []):
        for ref in (case.get("test_binding") or {}).get("test_refs", []):
            error = validate_test_ref(repo, ref)
            if error:
                errors.append(f"{case.get('id', 'UNKNOWN')}: {error}")
    return errors


def compare_generated_files(actual_root: Path, rendered_root: Path) -> list[str]:
    errors: list[str] = []
    for name in GENERATED_VIEWS:
        actual = actual_root / name
        rendered = rendered_root / name
        if not actual.is_file() or not rendered.is_file():
            errors.append(f"generated_view_drift: missing {name}")
        elif actual.read_bytes() != rendered.read_bytes():
            errors.append(f"generated_view_drift: {name} differs from deterministic render")
    return errors


def validate_generated_views(repo: Path) -> list[str]:
    req_root = repo / "docs/requirements"
    module_path = req_root / "requirements_guard.py"
    try:
        spec = importlib.util.spec_from_file_location("kgnote_requirements_guard", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot create module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ledger = module.load(req_root / "requirements.json")
        sources = module.load(req_root / "sources.json")
        cases = module.load(req_root / "scenarios.json")
        captured: dict[str, bytes] = {}

        def capture_write_text(path: Path, data: str, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> int:
            del encoding, errors, newline
            captured[path.name] = data.encode("utf-8")
            return len(data)

        # Preflight must remain usable in a read-only sandbox. Capture the
        # deterministic renderer's writes in memory instead of weakening the
        # generated-view comparison or requiring a writable temp directory.
        with patch.object(Path, "write_text", capture_write_text):
            module.render(Path("__memory__"), ledger, sources, cases)
        errors: list[str] = []
        for name in GENERATED_VIEWS:
            actual = req_root / name
            if not actual.is_file() or name not in captured:
                errors.append(f"generated_view_drift: missing {name}")
            elif actual.read_bytes() != captured[name]:
                errors.append(f"generated_view_drift: {name} differs from deterministic render")
        return errors
    except Exception as exc:  # deterministic preflight must report, not crash
        return [f"generated_view_drift: render failed: {type(exc).__name__}: {exc}"]


def tool_version(command: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as exc:
        return False, str(exc)
    return result.returncode == 0, result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""


def validate_tooling(repo: Path) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    if sys.version_info < (3, 10):
        errors.append("tooling: Python 3.10+ required")
    test_python = Path(os.environ.get("KGNOTE_TEST_PYTHON", repo / ".venv/bin/python"))
    if not test_python.is_absolute():
        test_python = repo / test_python
    if not os.access(test_python, os.X_OK):
        errors.append(f"tooling: missing executable test Python {test_python}")
    else:
        ok, version = tool_version([str(test_python), "--version"], repo)
        versions["test_python"] = version
        if not ok:
            errors.append("tooling: test Python version command failed")
    ok, node_version = tool_version(["node", "--version"], repo)
    versions["node"] = node_version
    if not ok:
        errors.append("tooling: node is unavailable")
    else:
        match = re.search(r"(\d+)", node_version)
        if not match or int(match.group(1)) < 20:
            errors.append(f"tooling: Node >=20 required, got {node_version}")
    ok, npm_version = tool_version(["npm", "--version"], repo)
    versions["npm"] = npm_version
    if not ok:
        errors.append("tooling: npm is unavailable")
    return errors, versions


def fingerprint_excluded(relative: str) -> bool:
    return relative in FINGERPRINT_EXCLUDES or any(
        relative.startswith(prefix) for prefix in FINGERPRINT_EXCLUDE_PREFIXES
    )


def repository_manifest(repo: Path) -> dict[str, Any]:
    tracked = run_git(repo, "ls-files", "-z").stdout.split(b"\0")
    untracked = run_git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
    paths = sorted(
        {
            item.decode("utf-8", "surrogateescape")
            for item in tracked + untracked
            if item and not fingerprint_excluded(item.decode("utf-8", "surrogateescape"))
        }
    )
    rows: list[dict[str, Any]] = []
    for relative in paths:
        path = repo / relative
        if not path.exists() and not path.is_symlink():
            rows.append({"path": relative, "state": "missing"})
            continue
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            data = os.readlink(path).encode("utf-8", "surrogateescape")
            kind = "symlink"
        elif stat.S_ISREG(mode):
            data = path.read_bytes()
            kind = "file"
        else:
            data = b""
            kind = "other"
        rows.append(
            {
                "path": relative,
                "kind": kind,
                "mode": oct(stat.S_IMODE(mode)),
                "sha256": sha256_bytes(data),
            }
        )
    payload = {
        "algorithm": "sha256-canonical-json-v3-branch-independent-review-bus-exclusions",
        "branch": git_text(repo, "branch", "--show-current"),
        "head": git_text(repo, "rev-parse", "HEAD"),
        "excluded_paths": sorted(FINGERPRINT_EXCLUDES),
        "excluded_prefixes": sorted(FINGERPRINT_EXCLUDE_PREFIXES),
        "entries": rows,
    }
    return payload


def fingerprint_from_manifest(manifest: dict[str, Any]) -> str | None:
    required = {"algorithm", "branch", "head", "excluded_paths", "excluded_prefixes", "entries"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        return None
    if not isinstance(manifest.get("entries"), list):
        return None
    digest_manifest = dict(manifest)
    if manifest.get("algorithm") == "sha256-canonical-json-v3-branch-independent-review-bus-exclusions":
        digest_manifest.pop("branch", None)
    canonical = json.dumps(
        digest_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256_bytes(canonical)


def repository_fingerprint(repo: Path) -> dict[str, Any]:
    payload = repository_manifest(repo)
    return {
        "algorithm": payload["algorithm"],
        "value": fingerprint_from_manifest(payload),
        "entry_count": len(payload["entries"]),
        "excluded_paths": payload["excluded_paths"],
        "excluded_prefixes": payload["excluded_prefixes"],
        "branch": payload["branch"],
        "head": payload["head"],
    }


def validate_human_decision_delta(
    repo: Path,
    request: dict[str, Any],
    decisions: dict[str, Any],
    required_ids: set[str],
) -> list[str]:
    """Allow only new canonical human-authority artifacts to differ from the seal."""
    sealed = request.get("candidate_manifest")
    if not isinstance(sealed, dict) or fingerprint_from_manifest(sealed) != request.get("candidate_fingerprint"):
        return ["human_decision_delta: sealed candidate manifest is missing or invalid"]
    current = repository_manifest(repo)
    errors: list[str] = []
    for field in ("algorithm", "branch", "head", "excluded_paths", "excluded_prefixes"):
        if current.get(field) != sealed.get(field):
            errors.append(f"human_decision_delta: repository {field} changed after candidate seal")
    entries = {
        item.get("decision_id"): item
        for item in decisions.get("decisions", [])
        if isinstance(item, dict)
    }
    for decision_id in sorted(required_ids):
        entry = entries.get(decision_id)
        if entry is None:
            errors.append(f"human_decision_delta: missing required decision {decision_id}")
            continue
        errors.extend(validate_human_decision_authority_record(repo, entry, request))
    allowed_paths = {
        str(entries[decision_id].get("authority_record", "")).split("#", 1)[0]
        for decision_id in required_ids
        if decision_id in entries
    }
    sealed_entries = {item.get("path"): item for item in sealed.get("entries", []) if isinstance(item, dict)}
    current_entries = {item.get("path"): item for item in current.get("entries", []) if isinstance(item, dict)}
    preexisting_authority = sorted(path for path in allowed_paths if path in sealed_entries)
    if preexisting_authority:
        errors.append(
            "human_decision_delta: authority records must be new dedicated artifacts absent from the sealed candidate: "
            + ", ".join(preexisting_authority)
        )
    changed_paths = {
        path for path in set(sealed_entries) | set(current_entries)
        if sealed_entries.get(path) != current_entries.get(path)
    }
    unrelated = sorted(changed_paths - allowed_paths)
    if unrelated:
        errors.append(
            "human_decision_delta: unrelated candidate drift is not authorized: " + ", ".join(unrelated)
        )
    missing_authority = sorted(path for path in allowed_paths if path not in current_entries)
    if missing_authority:
        errors.append(
            "human_decision_delta: authorized authority records are absent: " + ", ".join(missing_authority)
        )
    unchanged_authority = sorted(path for path in allowed_paths if path not in changed_paths)
    if unchanged_authority:
        errors.append(
            "human_decision_delta: authority records were not added after the candidate seal: "
            + ", ".join(unchanged_authority)
        )
    return errors


def validate_recorded_fingerprint(status: dict[str, Any], fingerprint: dict[str, Any]) -> list[str]:
    recorded = status.get("working_state", {}).get("fingerprint")
    if recorded in {None, "pending_cp3"}:
        return []
    if recorded != fingerprint.get("value"):
        return [
            "status_drift: recorded working-state fingerprint does not match repository; "
            f"expected {recorded}, got {fingerprint.get('value')}"
        ]
    return []


def is_clean_publication_adapter_checkout(
    repo: Path, dirty_paths: list[str] | None = None
) -> bool:
    """Recognize a clean exact-candidate checkout without local execution state.

    Mutable review/status receipts cannot embed their containing commit's final
    SHA and are deliberately excluded from the candidate fingerprint.  A clean
    checkout therefore recovers external identity through the tracked
    PUBLICATION_RECEIPT contract and live PR marker, while a worktree with local
    receipt mutations remains subject to the ordinary strict drift checks.
    """
    dirty = changed_paths(repo) if dirty_paths is None else dirty_paths
    return (repo / PUBLICATION_RECEIPT_PATH).is_file() and not dirty


def validate_publication_adapter_identity(
    repo: Path,
    fingerprint: dict[str, Any],
    head: str,
    runner: Callable[[list[str]], str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Resolve the live canonical PR tuple required by PUBLICATION_RECEIPT."""
    errors: list[str] = []
    try:
        config = json.loads((repo / ".ai/github-product-reviewer.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"publication_adapter: cannot load reviewer config: {exc}"], {}
    repositories = {
        config.get(name)
        for name in (
            "canonical_repository", "candidate_repository", "trigger_repository",
            "review_request_repository",
        )
    }
    if len(repositories) != 1 or None in repositories:
        errors.append("publication_adapter: active repository identities do not match")
    repository = config.get("canonical_repository")
    pull_request = config.get("review_pr_number")
    marker = config.get("request_marker")
    if not isinstance(repository, str) or not isinstance(pull_request, int) or not isinstance(marker, str):
        errors.append("publication_adapter: canonical PR configuration is invalid")
        return errors, {}
    command = [
        "gh", "pr", "view", str(pull_request), "--repo", repository,
        "--json", "headRefOid,body,state,url",
    ]
    try:
        if runner is None:
            completed = subprocess.run(command, cwd=repo, text=True, capture_output=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr.strip() or "gh pr view failed")
            raw = completed.stdout
        else:
            raw = runner(command)
        snapshot = json.loads(raw)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return errors + [f"publication_adapter: cannot resolve live canonical PR: {exc}"], {}
    pattern = re.compile(
        rf"<!--\s*{re.escape(marker)}\s+candidate_commit=([0-9a-f]{{40}})\s+"
        rf"candidate_fingerprint=([0-9a-f]{{64}})\s+review_round=([1-9][0-9]*)\s*-->"
    )
    matches = pattern.findall(str(snapshot.get("body", "")))
    if len(matches) != 1:
        errors.append("publication_adapter: live PR must contain exactly one request marker")
        return errors, snapshot
    marker_head, marker_fingerprint, marker_round = matches[0]
    if snapshot.get("state") != "OPEN":
        errors.append("publication_adapter: canonical PR is not open")
    if snapshot.get("headRefOid") != head or marker_head != head:
        errors.append("publication_adapter: live PR head/marker does not match checkout HEAD")
    if marker_fingerprint != fingerprint.get("value"):
        errors.append("publication_adapter: live marker fingerprint does not match checkout")
    snapshot.update({
        "repository": repository,
        "pull_request": pull_request,
        "marker_head": marker_head,
        "marker_fingerprint": marker_fingerprint,
        "review_round": int(marker_round),
    })
    return errors, snapshot


def preflight(repo: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ("AGENTS.md", "PLAN.md", "CODEX_STATUS.md", "DEVELOPMENT_PLAIN.md")
    for relative in required:
        if not (repo / relative).is_file():
            errors.append(f"repository: missing {relative}")
    try:
        root = Path(git_text(repo, "rev-parse", "--show-toplevel")).resolve()
        if root != repo.resolve():
            errors.append(f"repository: expected root {repo.resolve()}, git reports {root}")
    except subprocess.CalledProcessError as exc:
        errors.append(f"repository: not a Git worktree: {exc.stderr.decode(errors='replace')}")
        return {"status": "fail", "errors": errors, "warnings": warnings}

    branch = git_text(repo, "branch", "--show-current")
    head = git_text(repo, "rev-parse", "HEAD")
    authority_errors, lock = validate_authority(repo)
    errors.extend(authority_errors)
    publication_adapter_checkout = False
    try:
        plan, status = load_plan_status(repo)
        dirty = changed_paths(repo)
        publication_adapter_checkout = is_clean_publication_adapter_checkout(repo, dirty)
        plan_status_errors = validate_plan_status(plan, status, branch=branch, head=head)
        if publication_adapter_checkout:
            errors.extend(
                item for item in plan_status_errors
                if not item.startswith("status_drift:")
            )
        else:
            errors.extend(plan_status_errors)
            errors.extend(validate_status_handoff(repo, status))
        if lock and plan.get("product_direction_id") != lock.get("product_direction_id"):
            errors.append("authority_drift: PLAN direction differs from authority lock")
        unexpected = unexpected_dirty_paths(dirty, plan)
        if unexpected:
            errors.append(f"dirty_state: unexpected paths {unexpected}")
        recorded_unexpected = status.get("working_state", {}).get("unexpected_dirty_paths", [])
        if recorded_unexpected != unexpected:
            errors.append("status_drift: unexpected_dirty_paths does not match repository")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        plan, status, dirty, unexpected = {}, {}, [], []
        errors.append(f"plan_or_status_invalid: {type(exc).__name__}: {exc}")

    errors.extend(validate_generated_views(repo))
    errors.extend(validate_selectors(repo))
    tooling_errors, versions = validate_tooling(repo)
    errors.extend(tooling_errors)

    checkpoint = status.get("git", {}).get("checkpoint_manifest") if status else None
    checkpoint_digest = status.get("git", {}).get("checkpoint_manifest_sha256") if status else None
    if checkpoint:
        checkpoint_path = repo / checkpoint
        if not checkpoint_path.is_file():
            errors.append(f"checkpoint: missing {checkpoint}")
        elif sha256_file(checkpoint_path) != checkpoint_digest:
            errors.append("checkpoint: approved manifest digest mismatch")

    worktrees = [line[9:] for line in git_text(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")]
    fingerprint = repository_fingerprint(repo)
    if publication_adapter_checkout:
        adapter_errors, _ = validate_publication_adapter_identity(
            repo, fingerprint, head
        )
        errors.extend(adapter_errors)
        if not adapter_errors:
            warnings.append(
                "Clean publication-adapter checkout: live canonical PR head and marker fingerprint resolved exactly; "
                "mutable STATUS/review receipts are historical."
            )
    if not publication_adapter_checkout:
        errors.extend(validate_recorded_fingerprint(status, fingerprint))
    review_errors: list[str] = []
    review_blockers: list[str] = []
    review_state: str | None = None
    if (repo / ".ai/REVIEW_PROTOCOL.md").is_file():
        if publication_adapter_checkout:
            review_state = "EXTERNAL_ADAPTER_CHECKOUT"
        else:
            review_errors, review_artifacts = validate_review_artifacts(repo, fingerprint=fingerprint)
            errors.extend(review_errors)
            request = review_artifacts.get("request", {})
            result = review_artifacts.get("result", {})
            decisions = review_artifacts.get("decisions", {})
            orchestration_errors = validate_orchestrator_state(repo, plan, request)
            review_errors.extend(orchestration_errors)
            errors.extend(orchestration_errors)
            review_state = request.get("status")
            review_blockers = review_progression_blockers(
                request, result, decisions, plan, fingerprint
            )
    return {
        "schema_version": "kgnote.preflight-result.v1",
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "repository": {"root": str(repo.resolve()), "branch": branch, "head": head, "worktrees": worktrees},
        "goal_id": plan.get("goal_id") if plan else None,
        "active_milestone_id": plan.get("active_milestone_id") if plan else None,
        "dirty_paths": dirty,
        "unexpected_dirty_paths": unexpected,
        "tool_versions": versions,
        "fingerprint": fingerprint,
        "review": {
            "state": review_state,
            "artifact_errors": review_errors,
            "progression_allowed": not review_errors and not review_blockers,
            "progression_blockers": review_blockers,
        },
        "checks": {
            "authority_lock": not authority_errors,
            "plan_status": not any("plan_" in e or "status_" in e for e in errors),
            "status_handoff": not any(e.startswith("status_handoff_drift") for e in errors),
            "generated_views": not any(e.startswith("generated_view_drift") for e in errors),
            "selector_integrity": not any("selector_integrity" in e for e in errors),
            "dirty_ownership": not unexpected,
            "checkpoint_manifest": not any(e.startswith("checkpoint:") for e in errors),
            "tooling": not tooling_errors,
            "review_artifacts": not review_errors,
        },
    }


def untracked_whitespace_errors(repo: Path) -> list[str]:
    paths = [
        item.decode("utf-8", "surrogateescape")
        for item in run_git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
        if item
    ]
    errors: list[str] = []
    for relative in paths:
        data = (repo / relative).read_bytes()
        if b"\0" in data[:8192]:
            continue
        for number, line in enumerate(data.splitlines(), 1):
            if line.endswith((b" ", b"\t")):
                errors.append(f"{relative}:{number}: trailing whitespace in untracked file")
        if data.endswith(b"\n\n"):
            errors.append(f"{relative}: blank line at EOF in untracked file")
    return errors


def execute_gate(name: str, command: list[str], repo: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout
    return {
        "name": name,
        "command": command,
        "exit_code": result.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output_sha256": sha256_bytes(output.encode("utf-8", "replace")),
        "output_tail": output[-4000:],
        "passed": result.returncode == 0,
    }


def verification_claims(success: bool) -> dict[str, Any]:
    return {
        "candidate_verified": bool(success),
        "release_verified": False,
        "release_reason": "External/physical/human acceptance cannot be promoted by the local verifier.",
    }


def can_auto_advance(plan: dict[str, Any]) -> bool:
    active = [m for m in plan.get("milestones", []) if m.get("status") == "active"]
    if len(active) != 1 or active[0].get("human_gate", "none") not in {"none", "complete"}:
        return False
    completed = {m.get("id") for m in plan.get("milestones", []) if m.get("status") == "complete"}
    return set(active[0].get("dependencies", [])) <= completed


def milestone_after_verification(active_id: str, success: bool) -> str:
    return "candidate_verified" if success else "active"


def verify(repo: Path) -> tuple[dict[str, Any], int]:
    before = preflight(repo)
    timestamp = datetime.now(ZoneInfo("Asia/Taipei"))
    evidence_dir = repo / "output/control-plane"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"verification-{timestamp.strftime('%Y%m%dT%H%M%S%z')}.json"
    gates: list[dict[str, Any]] = []
    if before["status"] == "pass":
        test_python = Path(os.environ.get("KGNOTE_TEST_PYTHON", repo / ".venv/bin/python"))
        if not test_python.is_absolute():
            test_python = repo / test_python
        base_env = os.environ.copy()
        guard_env = base_env | {"PYTHONPATH": str(repo / "docs/requirements")}
        product_env = base_env | {"PYTHONPATH": str(repo / "src")}
        gates = [
            execute_gate(
                "requirements_guard",
                [str(test_python), "docs/requirements/requirements_guard.py", "check", "--repo", str(repo)],
                repo,
                base_env,
            ),
            execute_gate(
                "requirements_guard_tests",
                [str(test_python), "-m", "unittest", "discover", "-s", "docs/requirements", "-p", "test_requirements_guard.py", "-v"],
                repo,
                guard_env,
            ),
            execute_gate(
                "control_plane_negative_tests",
                [str(test_python), "-m", "unittest", "discover", "-s", "tests/control_plane", "-p", "test_*.py", "-v"],
                repo,
                product_env,
            ),
            execute_gate(
                "python_product_tests",
                [str(test_python), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
                repo,
                product_env,
            ),
            execute_gate("node_tests", ["npm", "test"], repo, base_env),
            execute_gate("strict_git_diff_check", ["git", "diff", "--check"], repo, base_env),
        ]
        whitespace = untracked_whitespace_errors(repo)
        gates.append(
            {
                "name": "untracked_whitespace",
                "command": ["internal", "untracked_whitespace_errors"],
                "exit_code": 0 if not whitespace else 2,
                "duration_seconds": 0.0,
                "output_sha256": sha256_bytes("\n".join(whitespace).encode()),
                "output_tail": "\n".join(whitespace),
                "passed": not whitespace,
            }
        )
    after_fingerprint = repository_fingerprint(repo)
    stable = before.get("fingerprint", {}).get("value") == after_fingerprint.get("value")
    success = before["status"] == "pass" and all(gate["passed"] for gate in gates) and stable
    claims = verification_claims(success)
    evidence: dict[str, Any] = {
        "schema_version": "kgnote.verification-evidence.v1",
        "verification_id": evidence_path.stem,
        "created_at": timestamp.isoformat(timespec="seconds"),
        "goal_id": before.get("goal_id"),
        "milestone_id": before.get("active_milestone_id"),
        "repository": before.get("repository"),
        "fingerprint_before": before.get("fingerprint"),
        "fingerprint_after": after_fingerprint,
        "fingerprint_stable": stable,
        "preflight": before,
        "gates": gates,
        "claims": claims,
        "result": "pass" if success else "fail",
        "baseline_waivers_applied": [],
        "remote_ci": "not_configured_enhancement",
        "evidence_readback": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readback = json.loads(evidence_path.read_text(encoding="utf-8"))
    if readback.get("verification_id") != evidence["verification_id"] or readback.get("fingerprint_before") != evidence["fingerprint_before"]:
        success = False
        evidence["result"] = "fail"
        evidence["claims"] = verification_claims(False)
        evidence["readback_error"] = "evidence read-back mismatch"
    else:
        evidence["evidence_readback"] = True
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    evidence["evidence_path"] = str(evidence_path.relative_to(repo))
    return evidence, 0 if success else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("fingerprint")
    sub.add_parser("selectors")
    sub.add_parser("generated")
    sub.add_parser("verify")
    sub.add_parser("review-validate")
    sub.add_parser("review-validate-pending")
    sub.add_parser("review-guard")
    request_parser = sub.add_parser("review-request")
    request_parser.add_argument("--evidence", required=True)
    request_parser.add_argument("--changed-area", action="append", required=True)
    request_parser.add_argument("--reviewer-focus", action="append", default=[])
    request_parser.add_argument("--known-deviation", action="append", default=[])
    request_parser.add_argument("--known-uncertainty", action="append", default=[])
    custody_parser = sub.add_parser("review-custody")
    custody_parser.add_argument("--reviewer-identity", required=True)
    invalidate_parser = sub.add_parser("review-invalidate")
    invalidate_parser.add_argument("--reason", required=True)
    sub.add_parser("review-submit")
    sub.add_parser("review-resume")
    fixed_parser = sub.add_parser("review-finding-fixed")
    fixed_parser.add_argument("--finding-id", required=True)
    fixed_parser.add_argument("--evidence", action="append", required=True)
    correction_parser = sub.add_parser("review-history-correct-actor")
    correction_parser.add_argument("--event-id", required=True)
    correction_parser.add_argument("--reason", required=True)
    sub.add_parser("review-status")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.command == "preflight":
        result = preflight(repo)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "pass" else 2
    if args.command == "fingerprint":
        print(json.dumps(repository_fingerprint(repo), indent=2, ensure_ascii=False))
        return 0
    if args.command == "selectors":
        errors = validate_selectors(repo)
        print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2, ensure_ascii=False))
        return 0 if not errors else 2
    if args.command == "generated":
        errors = validate_generated_views(repo)
        print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2, ensure_ascii=False))
        return 0 if not errors else 2
    if args.command == "review-validate":
        errors, artifacts = validate_review_artifacts(repo)
        print(
            json.dumps(
                {
                    "status": "pass" if not errors else "fail",
                    "errors": errors,
                    "review_id": artifacts.get("request", {}).get("review_id"),
                    "review_state": artifacts.get("request", {}).get("status"),
                    "candidate_fingerprint": artifacts.get("request", {}).get("candidate_fingerprint"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if not errors else 2
    if args.command == "review-validate-pending":
        errors, artifacts = validate_pending_review_result(repo)
        print(
            json.dumps(
                {
                    "status": "pass" if not errors else "fail",
                    "errors": errors,
                    "review_id": artifacts.get("request", {}).get("review_id"),
                    "review_state": artifacts.get("request", {}).get("status"),
                    "candidate_fingerprint": artifacts.get("request", {}).get("candidate_fingerprint"),
                    "result_state": artifacts.get("result", {}).get("artifact_state"),
                    "verdict": artifacts.get("result", {}).get("verdict"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if not errors else 2
    if args.command == "review-guard":
        errors, artifacts = validate_review_artifacts(repo)
        try:
            plan, _ = load_plan_status(repo)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"review_guard: cannot load PLAN: {exc}")
            plan = {}
        blockers = review_progression_blockers(
            artifacts.get("request", {}),
            artifacts.get("result", {}),
            artifacts.get("decisions", {}),
            plan,
            artifacts.get("fingerprint", repository_fingerprint(repo)),
        )
        print(json.dumps({"status": "pass" if not errors and not blockers else "blocked", "errors": errors, "blockers": blockers}, indent=2, ensure_ascii=False))
        return 0 if not errors and not blockers else 2
    if args.command == "review-request":
        try:
            result = prepare_review_request(
                repo,
                args.evidence,
                args.changed_area,
                args.reviewer_focus,
                args.known_deviation,
                args.known_uncertainty,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "ready_for_review", **result}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-custody":
        try:
            accept_review_custody(repo, args.reviewer_identity)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "under_review"}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-invalidate":
        try:
            result = invalidate_ready_request(repo, args.reason)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "implementing", **result}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-submit":
        try:
            result = archive_submitted_result(repo)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "submitted", **result}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-resume":
        try:
            resume_implementation(repo)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "implementing"}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-finding-fixed":
        try:
            mark_finding_fixed(repo, args.finding_id, args.evidence)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "fixed_pending_review", "finding_id": args.finding_id}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-history-correct-actor":
        try:
            correction = append_history_actor_correction(repo, args.event_id, args.reason)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "corrected", "event": correction}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "review-status":
        errors, artifacts = validate_review_artifacts(repo)
        plan, status = load_plan_status(repo)
        blockers = review_progression_blockers(
            artifacts.get("request", {}), artifacts.get("result", {}), artifacts.get("decisions", {}),
            plan, artifacts.get("fingerprint", repository_fingerprint(repo)),
        )
        request = artifacts.get("request", {})
        snapshot = {
            "schema_version": "kgnote.review-resume-state.v1",
            "status": "valid" if not errors else "invalid",
            "active_goal": plan.get("goal_id"),
            "active_milestone": plan.get("active_milestone_id"),
            "implementation_state": status.get("implementation_state"),
            "review_state": request.get("status"),
            "current_review_id": status.get("review", {}).get("current_review_id"),
            "candidate_revision": request.get("candidate_revision"),
            "candidate_fingerprint": request.get("candidate_fingerprint"),
            "unresolved_findings": status.get("review", {}).get("unresolved_findings", []),
            "human_decision_blockers": status.get("review", {}).get("human_decision_blockers", []),
            "preserved_human_gates": plan.get("preserved_human_gates", []),
            "authoritative_specs": request.get("authoritative_specs", []),
            "validation_results": request.get("validation_results", []),
            "progression_blockers": blockers,
            "exact_next_action": status.get("next_action"),
            "errors": errors,
        }
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0 if not errors else 2
    if args.command == "verify":
        evidence, code = verify(repo)
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
