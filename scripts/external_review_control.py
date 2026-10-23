#!/usr/bin/env python3
"""Fail-closed authority and transition checks for external product review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


CONFIG_PATH = Path(".ai/github-product-reviewer.json")
STATE_PATH = Path(".ai/external-review-state.json")
ACTIVE_REPOSITORY_FIELDS = (
    "canonical_repository",
    "candidate_repository",
    "trigger_repository",
    "review_request_repository",
)
UBUNTU_REVIEW_TRIGGER_TEMPLATE = (
    "<!-- kgnote-ubuntu-claude-review-request candidate_commit={candidate_commit} -->"
)
LEGACY_WORK_TRIGGER_TEMPLATE = "@kgnote-ai-review {candidate_commit}"
FINAL_HUMAN_GATE_ID = "D2-T14-FINAL-HUMAN-ACCEPTANCE"
FINAL_HUMAN_GATE_AUTHORITY_REFS = {
    "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
    "https://github.com/joannalee20050914/KGnote-public/issues/21",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def repository_authority_errors(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    identities = {field: config.get(field) for field in ACTIVE_REPOSITORY_FIELDS}
    if any(not isinstance(value, str) or not value for value in identities.values()):
        errors.append("external_review: every active repository identity must be non-empty")
    elif len(set(identities.values())) != 1:
        errors.append(
            "external_review: canonical, candidate, trigger, and request repositories must match"
        )
    archive = config.get("archive_repository")
    if not isinstance(archive, str) or not archive:
        errors.append("external_review: archive_repository must be non-empty")
    elif archive in identities.values():
        errors.append("external_review: archive repository cannot be an active review surface")
    if config.get("enabled") is not True:
        errors.append("external_review: transport must be enabled")
    trigger_events = config.get("trigger_events")
    if not isinstance(trigger_events, list) or "issue_comment.created" not in trigger_events:
        errors.append("external_review: exact issue-comment trigger event must be configured")
    transport = config.get("transport")
    accepted_triggers = (
        {UBUNTU_REVIEW_TRIGGER_TEMPLATE, LEGACY_WORK_TRIGGER_TEMPLATE}
        if transport == "ubuntu_claude_runner_github_relay"
        else {LEGACY_WORK_TRIGGER_TEMPLATE}
    )
    if config.get("trigger_comment_template") not in accepted_triggers:
        errors.append("external_review: exact transport-specific trigger comment template is missing")
    if config.get("schema_version") == "kgnote.github-product-reviewer-config.v2":
        if config.get("review_pr_expected_draft") is not True:
            errors.append("external_review: candidate PR must remain Draft")
        for field in ("review_pr_head_branch", "review_pr_base_branch", "dependency_pr_required_state"):
            if not isinstance(config.get(field), str) or not config.get(field):
                errors.append(f"external_review: missing {field}")
        if not isinstance(config.get("dependency_pr_number"), int):
            errors.append("external_review: missing dependency_pr_number")
    return errors


def external_review_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    candidate_commit: str | None = None,
    candidate_fingerprint: str | None = None,
) -> list[str]:
    """Return exact-candidate review/publication reasons progression is blocked."""
    blockers = repository_authority_errors(config)
    for field in ACTIVE_REPOSITORY_FIELDS:
        if state.get(field) != config.get(field):
            blockers.append(f"external_review: state/config mismatch for {field}")
    if state.get("pull_request") != config.get("review_pr_number"):
        blockers.append("external_review: state/config pull request mismatch")

    review = state.get("external_review")
    if not isinstance(review, Mapping):
        blockers.append("external_review: verifiable external review artifact is missing")
        return blockers
    if review.get("status") != "PASS":
        blockers.append("external_review: external PASS is required before human acceptance")
    if not review.get("artifact_url"):
        blockers.append("external_review: verifiable external review artifact is missing")
    if review.get("blocking_findings"):
        blockers.append("external_review: blocking findings remain")

    expected_commit = candidate_commit or state.get("candidate_commit")
    expected_fingerprint = candidate_fingerprint or state.get("candidate_fingerprint")
    if not expected_commit or review.get("reviewed_commit") != expected_commit:
        blockers.append("external_review: external artifact is not bound to the exact candidate commit")
    if not expected_fingerprint or review.get("reviewed_fingerprint") != expected_fingerprint:
        blockers.append("external_review: external artifact is not bound to the exact candidate fingerprint")

    internal = state.get("internal_review")
    publication = state.get("publication")
    if not isinstance(internal, Mapping) or internal.get("status") != "PASS":
        blockers.append("external_review: internal verification/review has not passed")
    if not isinstance(publication, Mapping) or publication.get("status") != "PUBLISHED":
        blockers.append("external_review: exact candidate has not been published")
    if isinstance(publication, Mapping) and publication.get("remote_head") != expected_commit:
        blockers.append("external_review: published remote head does not match candidate commit")
    receipt = state.get("delivery_receipt")
    if config.get("delivery_issue_number") is not None and (not isinstance(receipt, Mapping) or receipt.get("status") != "VERIFIED"):
        blockers.append("external_review: Issue/Project delivery receipt is missing")
    elif isinstance(receipt, Mapping):
        expected_receipt = {"repository": config.get("canonical_repository"), "pull_request": config.get("review_pr_number"),
            "candidate_commit": expected_commit, "candidate_fingerprint": expected_fingerprint,
            "review_round": state.get("review_round"), "project_status": "Review Queue"}
        for field, value in expected_receipt.items():
            if receipt.get(field) != value:
                blockers.append(f"external_review: delivery receipt mismatch for {field}")
        if not receipt.get("issue_comment_url") or not receipt.get("review_artifact_url"):
            blockers.append("external_review: delivery receipt read-back URLs are missing")
    return blockers


def final_human_acceptance_errors(
    checkpoint: object,
    *,
    candidate_commit: str | None = None,
    candidate_fingerprint: str | None = None,
) -> list[str]:
    """Validate the one current blocking product-experience gate.

    Every prerequisite is positive evidence.  Missing fields, legacy gate IDs,
    and an existing human verdict all keep the workflow out of the final wait.
    """
    if not isinstance(checkpoint, Mapping):
        return ["final_acceptance: final human checkpoint is not explicitly scheduled"]
    errors: list[str] = []
    expected_scalars = {
        "gate_id": FINAL_HUMAN_GATE_ID,
        "status": "READY",
        "candidate_scope": "COMPLETE_PRODUCT_DELIVERY",
        "formal_human_acceptance_status": "NOT_EVALUATED",
    }
    for field, expected in expected_scalars.items():
        if checkpoint.get(field) != expected:
            errors.append(f"final_acceptance: {field} must equal {expected}")
    required_evidence = (
        "approved_required_scope_complete",
        "required_features_complete",
        "dependencies_complete",
        "cross_module_integration_complete",
        "required_scenarios_complete",
        "delivery_evidence_complete",
        "no_known_delivery_blockers",
        "rc_evidence_complete",
        "independent_review_complete",
        "integrated_verification_complete",
    )
    for field in required_evidence:
        if checkpoint.get(field) is not True:
            errors.append(f"final_acceptance: {field} is not proven")
    entrypoint = checkpoint.get("trial_entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        errors.append("final_acceptance: complete trial entrypoint is missing")
    authority_refs = checkpoint.get("authority_refs")
    if not isinstance(authority_refs, list) or not FINAL_HUMAN_GATE_AUTHORITY_REFS.issubset(
        {str(value) for value in authority_refs}
    ):
        errors.append("final_acceptance: final gate authority is incomplete")
    if candidate_commit and checkpoint.get("candidate_commit") != candidate_commit:
        errors.append("final_acceptance: candidate commit does not match the reviewed candidate")
    if candidate_fingerprint and checkpoint.get("candidate_fingerprint") != candidate_fingerprint:
        errors.append("final_acceptance: candidate fingerprint does not match the reviewed candidate")
    return errors


def human_gate_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    candidate_commit: str | None = None,
    candidate_fingerprint: str | None = None,
) -> list[str]:
    """Compatibility entrypoint for the exact final human acceptance gate."""
    expected_commit = candidate_commit or state.get("candidate_commit")
    expected_fingerprint = candidate_fingerprint or state.get("candidate_fingerprint")
    return external_review_blockers(
        config,
        state,
        candidate_commit=candidate_commit,
        candidate_fingerprint=candidate_fingerprint,
    ) + final_human_acceptance_errors(
        state.get("human_checkpoint"),
        candidate_commit=expected_commit if isinstance(expected_commit, str) else None,
        candidate_fingerprint=(
            expected_fingerprint if isinstance(expected_fingerprint, str) else None
        ),
    )


def next_machine_state(config: Mapping[str, Any], state: Mapping[str, Any]) -> str:
    """Derive the autonomous next state without promoting a human gate."""
    authority = repository_authority_errors(config)
    if authority:
        return "AUTHORITY_CONFLICT"
    review = state.get("external_review")
    if not isinstance(review, Mapping) or not review.get("artifact_url"):
        return "WAITING_FOR_EXTERNAL_REVIEW"
    if review.get("status") == "CHANGES_REQUIRED" or review.get("blocking_findings"):
        return "REPAIRING_EXTERNAL_FINDINGS"
    if external_review_blockers(config, state):
        return "WAITING_FOR_EXTERNAL_REVIEW"
    if final_human_acceptance_errors(
        state.get("human_checkpoint"),
        candidate_commit=(state.get("candidate_commit") if isinstance(state.get("candidate_commit"), str) else None),
        candidate_fingerprint=(state.get("candidate_fingerprint") if isinstance(state.get("candidate_fingerprint"), str) else None),
    ):
        return "COMPONENT_REVIEW_COMPLETE"
    return "FINAL_HUMAN_ACCEPTANCE_REQUIRED"


def publication_progression_blockers(
    config: Mapping[str, Any], state: Mapping[str, Any]
) -> list[str]:
    """Require authoritative exact-candidate remote read-back before progression."""
    blockers = repository_authority_errors(config)
    publication = state.get("publication")
    if not isinstance(publication, Mapping):
        return blockers + ["external_review: publication evidence is missing"]
    expected = {
        "repository": config.get("canonical_repository"),
        "pull_request": config.get("review_pr_number"),
        "remote_head": state.get("candidate_commit"),
        "candidate_fingerprint": state.get("candidate_fingerprint"),
        "request_marker": config.get("request_marker"),
        "trigger_comment": str(config.get("trigger_comment_template", "")).format(
            candidate_commit=state.get("candidate_commit")
        ),
    }
    if config.get("dependency_pr_number") is not None:
        expected.update({"is_draft": config.get("review_pr_expected_draft"),
            "head_branch": config.get("review_pr_head_branch"), "base_branch": config.get("review_pr_base_branch"),
            "dependency_pr": config.get("dependency_pr_number"), "dependency_state": config.get("dependency_pr_required_state"),
            "dependency_merged": False})
    if publication.get("status") != "PUBLISHED":
        blockers.append("external_review: exact candidate is not published")
    for field, value in expected.items():
        if value is None or value == "" or publication.get(field) != value:
            blockers.append(f"external_review: publication read-back mismatch for {field}")
    artifact = publication.get("artifact_url")
    if not isinstance(artifact, str) or not artifact:
        blockers.append("external_review: publication artifact URL is missing")
    trigger_artifact = publication.get("trigger_artifact_url")
    if not isinstance(trigger_artifact, str) or not trigger_artifact:
        blockers.append("external_review: exact event-trigger artifact URL is missing")
    return blockers


def repository_publication_progression_blockers(repo: Path) -> list[str]:
    try:
        config = load_json(repo / CONFIG_PATH)
        state = load_json(repo / STATE_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"external_review: cannot load publication state: {exc}"]
    return publication_progression_blockers(config, state)


def repository_human_gate_blockers(repo: Path) -> list[str]:
    try:
        config = load_json(repo / CONFIG_PATH)
        state = load_json(repo / STATE_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"external_review: cannot load canonical state: {exc}"]
    return human_gate_blockers(config, state)


__all__ = [
    "ACTIVE_REPOSITORY_FIELDS",
    "FINAL_HUMAN_GATE_ID",
    "external_review_blockers",
    "final_human_acceptance_errors",
    "human_gate_blockers",
    "next_machine_state",
    "publication_progression_blockers",
    "repository_authority_errors",
    "repository_human_gate_blockers",
    "repository_publication_progression_blockers",
]
