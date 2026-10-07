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
    return errors


def human_gate_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    candidate_commit: str | None = None,
    candidate_fingerprint: str | None = None,
) -> list[str]:
    """Return reasons an AI-dependent workflow cannot enter a human checkpoint."""
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
    return blockers


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
    if not human_gate_blockers(config, state):
        return "HUMAN_CHECKPOINT_REQUIRED"
    return "WAITING_FOR_EXTERNAL_REVIEW"


def repository_human_gate_blockers(repo: Path) -> list[str]:
    try:
        config = load_json(repo / CONFIG_PATH)
        state = load_json(repo / STATE_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"external_review: cannot load canonical state: {exc}"]
    return human_gate_blockers(config, state)


__all__ = [
    "ACTIVE_REPOSITORY_FIELDS",
    "human_gate_blockers",
    "next_machine_state",
    "repository_authority_errors",
    "repository_human_gate_blockers",
]
