#!/usr/bin/env python3
"""Shared fail-closed identity checks for Product Goal Linux workers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PRODUCT_IDENTITY_SCHEMA = "kgnote.authorized-product-goal-work-identity.v1"
PRODUCT_GOAL_ID = "GOAL-KGNOTE-O2-READING-EXPERIENCE"
PRODUCT_GOAL_VERSION = "2026-10-23.2-s0-s2-proposal"
PRODUCT_GOAL_SPEC_SHA256 = "82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604"
PRODUCT_REPOSITORY = "joannalee20050914/KGnote-public"
PRODUCT_ISSUE = 9
PRODUCT_WORKTREE_SLUG = "goal-o2-reading-experience"
PRODUCT_BRANCH = "codex/o2-reading-experience"
PRODUCT_BRANCH_RE = re.compile(r"codex/[a-z0-9][a-z0-9-]{2,80}")
EVENT_RE = re.compile(
    r"o2-wi-o2-(?:a|b)-(?:implement|verify|publish|review|repair)-"
    r"(?:codex|publisher|push|claude)-[0-9a-f]{16}"
)
WORK_ITEM_RE = re.compile(r"WI-O2-(?:A|B)-(IMPLEMENT|VERIFY|PUBLISH|REVIEW|REPAIR)")
LANES = {
    "IMPLEMENT": ("codex", "codex"),
    "REPAIR": ("codex", "codex"),
    "VERIFY": ("publisher", "NONE"),
    "PUBLISH": ("push", "NONE"),
    "REVIEW": ("claude", "claude"),
}


class ProductGoalIdentityError(ValueError):
    pass


def validate_product_goal_identity(
    identity: object,
    *,
    event_id: str,
    stage: str,
    working_directory: Path,
    worktree_root: Path,
) -> dict[str, Any]:
    """Validate one exact O2 identity without broad WI-* admission."""
    if not isinstance(identity, dict) or identity.get("schema_version") != PRODUCT_IDENTITY_SCHEMA:
        raise ProductGoalIdentityError("Product Goal bootstrap identity is missing or unsupported")
    required = {
        "identity_kind", "authority_kind", "repository", "issue", "goal_id",
        "goal_version", "goal_spec_sha256", "work_item_id", "provider", "stage",
        "order_event_id", "branch", "worktree_slug", "authority_record",
        "authority_sha256", "authority_status", "authority_action",
        "go_live_authorized",
    }
    if required - set(identity):
        raise ProductGoalIdentityError("Product Goal bootstrap identity is incomplete")
    if identity["identity_kind"] != "KGNOTE_PRODUCT_GOAL" or identity["authority_kind"] != "GITHUB_OWNER_APPROVAL":
        raise ProductGoalIdentityError("Product Goal identity or authority kind is invalid")
    exact = {
        "repository": PRODUCT_REPOSITORY,
        "issue": PRODUCT_ISSUE,
        "goal_id": PRODUCT_GOAL_ID,
        "goal_version": PRODUCT_GOAL_VERSION,
        "goal_spec_sha256": PRODUCT_GOAL_SPEC_SHA256,
        "worktree_slug": PRODUCT_WORKTREE_SLUG,
        "authority_record": f"https://github.com/{PRODUCT_REPOSITORY}/issues/{PRODUCT_ISSUE}",
        "authority_status": "APPROVED",
        "authority_action": "APPROVE",
        "go_live_authorized": True,
    }
    if any(identity.get(key) != value for key, value in exact.items()):
        raise ProductGoalIdentityError("Product Goal identity differs from the authorized O2 Goal")
    work_match = WORK_ITEM_RE.fullmatch(str(identity["work_item_id"]))
    if work_match is None:
        raise ProductGoalIdentityError("Product Goal Work Item is not authorized")
    expected_stage, expected_provider = LANES[work_match.group(1)]
    if stage != expected_stage or identity["stage"] != stage or identity["provider"] != expected_provider:
        raise ProductGoalIdentityError("Product Goal provider or stage does not match the Work Item")
    if identity["order_event_id"] != event_id or EVENT_RE.fullmatch(event_id) is None:
        raise ProductGoalIdentityError("Product Goal order event identity is stale or malformed")
    if (
        PRODUCT_BRANCH_RE.fullmatch(str(identity["branch"])) is None
        or identity["branch"] != PRODUCT_BRANCH
    ):
        raise ProductGoalIdentityError("Product Goal branch is invalid")
    if not isinstance(identity["authority_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", identity["authority_sha256"]) is None:
        raise ProductGoalIdentityError("Product Goal authority digest is invalid")
    expected_directory = worktree_root / "work-items" / PRODUCT_WORKTREE_SLUG
    if not working_directory.is_absolute() or working_directory != expected_directory:
        raise ProductGoalIdentityError("Product Goal working directory is outside the exact authorized path")
    return identity
