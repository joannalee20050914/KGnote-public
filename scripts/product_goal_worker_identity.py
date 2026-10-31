#!/usr/bin/env python3
"""Shared fail-closed identity checks for Product Goal Linux workers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PRODUCT_IDENTITY_SCHEMA = "kgnote.authorized-product-goal-work-identity.v1"
PRODUCT_RUNTIME_CONTEXT_SCHEMA = "kgnote.product-goal-worker-context.v2"
COLLABORATION_IDENTITY_SCHEMA = "kgnote.authorized-product-goal-work-identity.v2"
COLLABORATION_RUNTIME_CONTEXT_SCHEMA = "kgnote.product-goal-worker-context.v3"
PRODUCT_GOAL_ID = "GOAL-KGNOTE-O2-READING-EXPERIENCE"
PRODUCT_GOAL_VERSION = "2026-10-29.4-bounded-trial-day0-proposal"
PRODUCT_GOAL_SPEC_SHA256 = "7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f"
PRODUCT_REPOSITORY = "joannalee20050914/KGnote-public"
PRODUCT_ISSUE = 9
PRODUCT_WORKTREE_SLUG = "goal-o2-reading-experience"
PRODUCT_BRANCH = "codex/o2-reading-experience"
PRODUCT_SEED_COMMIT = "483f9e64066821d5d647d411e6da8ddb50ad88e5"
PRODUCT_REPOSITORY_URL = f"https://github.com/{PRODUCT_REPOSITORY}.git"
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


def _validate_collaboration_identity(
    identity: dict[str, Any], *, event_id: str, stage: str,
    working_directory: Path, worktree_root: Path,
) -> dict[str, Any]:
    required = {
        "identity_kind", "authority_kind", "repository", "issue", "goal_id",
        "goal_version", "goal_spec_sha256", "work_item_id", "provider", "stage",
        "order_event_id", "branch", "worktree_slug", "authority_record",
        "authority_sha256", "authority_status", "authority_action",
        "go_live_authorized", "candidate_commit", "candidate_fingerprint",
    }
    if required - set(identity):
        raise ProductGoalIdentityError("collaboration Product Goal identity is incomplete")
    if identity["identity_kind"] != "KGNOTE_PRODUCT_GOAL" or identity["authority_kind"] != "GITHUB_OWNER_APPROVAL":
        raise ProductGoalIdentityError("Product Goal identity or authority kind is invalid")
    repository = str(identity["repository"])
    issue = identity["issue"]
    if re.fullmatch(r"[^/\s]+/[^/\s]+", repository) is None or not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise ProductGoalIdentityError("collaboration repository or Issue identity is invalid")
    if re.fullmatch(r"GOAL-KGNOTE-[A-Z0-9-]+", str(identity["goal_id"])) is None:
        raise ProductGoalIdentityError("collaboration Goal identity is invalid")
    if not isinstance(identity["goal_version"], str) or not identity["goal_version"]:
        raise ProductGoalIdentityError("collaboration Goal version is invalid")
    if re.fullmatch(r"[0-9a-f]{64}", str(identity["goal_spec_sha256"])) is None:
        raise ProductGoalIdentityError("collaboration Goal digest is invalid")
    if re.fullmatch(r"WI-[A-Z0-9-]+", str(identity["work_item_id"])) is None:
        raise ProductGoalIdentityError("collaboration Work Item identity is invalid")
    lanes = {"codex": "codex", "claude": "claude", "publisher": "NONE", "push": "NONE"}
    if stage not in lanes or identity["stage"] != stage or identity["provider"] != lanes[stage]:
        raise ProductGoalIdentityError("Product Goal provider or stage does not match the Work Item")
    if identity["order_event_id"] != event_id or re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", event_id) is None:
        raise ProductGoalIdentityError("collaboration order event identity is stale or malformed")
    branch = str(identity["branch"])
    slug = str(identity["worktree_slug"])
    if PRODUCT_BRANCH_RE.fullmatch(branch) is None or re.fullmatch(r"goal-[a-z0-9-]{8,48}", slug) is None:
        raise ProductGoalIdentityError("collaboration branch or worktree slug is invalid")
    if identity["authority_record"] != f"https://github.com/{repository}/issues/{issue}":
        raise ProductGoalIdentityError("collaboration authority record is invalid")
    if (
        identity["authority_status"] != "APPROVED"
        or identity["authority_action"] not in {"APPROVE", "RESUME"}
        or identity["go_live_authorized"] is not True
    ):
        raise ProductGoalIdentityError("collaboration authority is not active")
    for key, pattern in {
        "authority_sha256": r"[0-9a-f]{64}",
        "candidate_commit": r"[0-9a-f]{40}",
        "candidate_fingerprint": r"[0-9a-f]{64}",
    }.items():
        if re.fullmatch(pattern, str(identity[key])) is None:
            raise ProductGoalIdentityError(f"collaboration {key} is invalid")
    if working_directory != worktree_root / "work-items" / slug:
        raise ProductGoalIdentityError("collaboration working directory is not Goal-bound")
    return identity


def validate_product_goal_identity(
    identity: object,
    *,
    event_id: str,
    stage: str,
    working_directory: Path,
    worktree_root: Path,
) -> dict[str, Any]:
    """Validate one exact O2 identity without broad WI-* admission."""
    if isinstance(identity, dict) and identity.get("schema_version") == COLLABORATION_IDENTITY_SCHEMA:
        return _validate_collaboration_identity(
            identity, event_id=event_id, stage=stage,
            working_directory=working_directory, worktree_root=worktree_root,
        )
    if not isinstance(identity, dict) or identity.get("schema_version") != PRODUCT_IDENTITY_SCHEMA:
        raise ProductGoalIdentityError("Product Goal bootstrap identity is missing or unsupported")
    required = {
        "identity_kind", "authority_kind", "repository", "issue", "goal_id",
        "goal_version", "goal_spec_sha256", "work_item_id", "provider", "stage",
        "order_event_id", "branch", "worktree_slug", "authority_record",
        "authority_sha256", "authority_status", "authority_action",
        "go_live_authorized", "candidate_commit", "candidate_fingerprint",
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
        "go_live_authorized": True,
    }
    if any(identity.get(key) != value for key, value in exact.items()):
        raise ProductGoalIdentityError("Product Goal identity differs from the authorized O2 Goal")
    if identity.get("authority_action") not in {"APPROVE", "RESUME"}:
        raise ProductGoalIdentityError("Product Goal authority action is not an active Owner command")
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
    if (
        not isinstance(identity["candidate_commit"], str)
        or re.fullmatch(r"[0-9a-f]{40}", identity["candidate_commit"]) is None
    ):
        raise ProductGoalIdentityError("Product Goal candidate commit is invalid")
    if (
        not isinstance(identity["candidate_fingerprint"], str)
        or re.fullmatch(r"[0-9a-f]{64}", identity["candidate_fingerprint"]) is None
    ):
        raise ProductGoalIdentityError("Product Goal candidate fingerprint is invalid")
    if not isinstance(identity["authority_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", identity["authority_sha256"]) is None:
        raise ProductGoalIdentityError("Product Goal authority digest is invalid")
    expected_directory = worktree_root / "work-items" / PRODUCT_WORKTREE_SLUG
    if not working_directory.is_absolute() or working_directory != expected_directory:
        raise ProductGoalIdentityError("Product Goal working directory is outside the exact authorized path")
    return identity


def validate_product_goal_runtime_context(
    context: object, *, identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the sealed Runner projection consumed by an Ubuntu worker."""
    if isinstance(context, dict) and context.get("schema_version") == COLLABORATION_RUNTIME_CONTEXT_SCHEMA:
        return _validate_collaboration_runtime_context(context, identity=identity)
    if not isinstance(context, dict) or context.get("schema_version") != PRODUCT_RUNTIME_CONTEXT_SCHEMA:
        raise ProductGoalIdentityError("Product Goal runtime context is missing or unsupported")
    required = {
        "goal_id", "goal_version", "goal_spec_sha256", "repository", "issue",
        "work_item_id", "order_event_id", "attempt_id", "stage", "provider",
        "candidate_commit", "candidate_fingerprint", "branch", "obligation_ids",
        "runner_context",
    }
    if required - set(context):
        raise ProductGoalIdentityError("Product Goal runtime context is incomplete")
    exact = {
        "goal_id": PRODUCT_GOAL_ID,
        "goal_version": PRODUCT_GOAL_VERSION,
        "goal_spec_sha256": PRODUCT_GOAL_SPEC_SHA256,
        "repository": PRODUCT_REPOSITORY,
        "issue": PRODUCT_ISSUE,
        "branch": PRODUCT_BRANCH,
    }
    if any(context.get(key) != value for key, value in exact.items()):
        raise ProductGoalIdentityError("Product Goal runtime context differs from exact O2 identity")
    runner = context.get("runner_context")
    if not isinstance(runner, dict):
        raise ProductGoalIdentityError("Runner-verified context is absent")
    if (
        runner.get("schema_version") != "kgnote.runner-verified-work-context.v1"
        or runner.get("source") != "MAC_RUNNER_DURABLE_STATE"
        or runner.get("repository_plan_status_authoritative") is not False
        or runner.get("authority_lease") != "ACTIVE"
        or runner.get("go_live_authorized") is not True
    ):
        raise ProductGoalIdentityError("Runner-verified authority projection is not active")
    lifecycle = runner.get("lifecycle")
    cursor = runner.get("event_cursor")
    authority = runner.get("authority_record")
    work = runner.get("work_item")
    candidate = runner.get("candidate_identity")
    if not isinstance(lifecycle, dict) or lifecycle.get("state") != "ACTIVE":
        raise ProductGoalIdentityError("Runner lifecycle is not ACTIVE")
    if (
        not isinstance(cursor, dict)
        or not isinstance(cursor.get("sequence"), int)
        or cursor["sequence"] < 1
        or re.fullmatch(r"[0-9a-f]{64}", str(cursor.get("event_sha256") or "")) is None
    ):
        raise ProductGoalIdentityError("Runner event cursor is invalid")
    if re.fullmatch(r"[0-9a-f]{64}", str(runner.get("state_projection_sha256") or "")) is None:
        raise ProductGoalIdentityError("Runner state projection digest is invalid")
    if not isinstance(authority, dict) or any(
        authority.get(key) != value for key, value in {
            "authority_kind": "GITHUB_OWNER_APPROVAL",
            "author_association": "OWNER",
            "goal_id": PRODUCT_GOAL_ID,
            "goal_version": PRODUCT_GOAL_VERSION,
            "goal_spec_sha256": PRODUCT_GOAL_SPEC_SHA256,
            "repository": PRODUCT_REPOSITORY,
            "issue": PRODUCT_ISSUE,
        }.items()
    ):
        raise ProductGoalIdentityError("Runner Owner authority record is invalid")
    if authority.get("action") not in {"APPROVE", "RESUME"}:
        raise ProductGoalIdentityError("Runner Owner authority does not authorize active work")
    authority_digest = hashlib.sha256(
        json.dumps(authority, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if runner.get("authority_record_sha256") != authority_digest:
        raise ProductGoalIdentityError("Runner Owner authority record digest differs")
    if not isinstance(work, dict) or any(
        work.get(key) != value for key, value in {
            "work_item_id": context["work_item_id"],
            "dispatch_attempt_id": context["attempt_id"],
        }.items()
    ):
        raise ProductGoalIdentityError("Runner Work Item projection differs from the order")
    if (
        work.get("status") not in {"PLANNED", "READY", "REPAIR_REQUIRED", "VERIFY_REQUIRED", "PUBLISH_REQUIRED"}
        or work.get("active_attempt_id") is not None
        or not isinstance(work.get("attempts_before"), int)
        or work["attempts_before"] < 0
        or work.get("obligation_ids") != context.get("obligation_ids")
    ):
        raise ProductGoalIdentityError("Runner Work Item projection is not dispatchable")
    if not isinstance(candidate, dict) or any(
        candidate.get(key) != context.get(target) for key, target in {
            "commit": "candidate_commit", "fingerprint": "candidate_fingerprint", "branch": "branch",
        }.items()
    ):
        raise ProductGoalIdentityError("Runner candidate projection differs from the order")
    if identity is not None:
        pairs = {
            "goal_id": "goal_id", "goal_version": "goal_version",
            "goal_spec_sha256": "goal_spec_sha256", "repository": "repository",
            "issue": "issue", "work_item_id": "work_item_id", "order_event_id": "order_event_id",
            "stage": "stage", "provider": "provider", "candidate_commit": "candidate_commit",
            "candidate_fingerprint": "candidate_fingerprint", "branch": "branch",
        }
        if any(identity.get(left) != context.get(right) for left, right in pairs.items()):
            raise ProductGoalIdentityError("bootstrap identity differs from Runner runtime context")
        if (
            identity.get("authority_sha256") != authority.get("body_sha256")
            or identity.get("authority_action") != authority.get("action")
        ):
            raise ProductGoalIdentityError("bootstrap authority differs from Runner runtime context")
    return context


def _validate_collaboration_runtime_context(
    context: dict[str, Any], *, identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required = {
        "goal_id", "goal_version", "goal_spec_sha256", "repository", "issue",
        "work_item_id", "order_event_id", "attempt_id", "stage", "provider",
        "action", "candidate_commit", "candidate_fingerprint", "branch",
        "obligation_ids", "runner_context", "checkpoint", "review", "usage",
        "next_action", "dispatch_envelope", "dispatch_envelope_sha256",
    }
    if required - set(context):
        raise ProductGoalIdentityError("collaboration runtime context is incomplete")
    if (
        re.fullmatch(r"GOAL-KGNOTE-[A-Z0-9-]+", str(context["goal_id"])) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(context["goal_spec_sha256"])) is None
        or re.fullmatch(r"WI-[A-Z0-9-]+", str(context["work_item_id"])) is None
        or re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", str(context["order_event_id"])) is None
        or PRODUCT_BRANCH_RE.fullmatch(str(context["branch"])) is None
    ):
        raise ProductGoalIdentityError("collaboration runtime identity fields are invalid")
    runner = context.get("runner_context")
    if not isinstance(runner, dict) or any(
        runner.get(key) != expected for key, expected in {
            "schema_version": "kgnote.runner-verified-work-context.v1",
            "source": "MAC_RUNNER_DURABLE_STATE",
            "repository_plan_status_authoritative": False,
            "authority_lease": "ACTIVE",
            "go_live_authorized": True,
        }.items()
    ):
        raise ProductGoalIdentityError("Runner-verified collaboration authority is not active")
    lifecycle = runner.get("lifecycle")
    cursor = runner.get("event_cursor")
    authority = runner.get("authority_record")
    work = runner.get("work_item")
    candidate = runner.get("candidate_identity")
    if not isinstance(lifecycle, dict) or lifecycle.get("state") != "ACTIVE":
        raise ProductGoalIdentityError("Runner collaboration lifecycle is not ACTIVE")
    if (
        not isinstance(cursor, dict)
        or not isinstance(cursor.get("sequence"), int)
        or cursor["sequence"] < 1
        or re.fullmatch(r"[0-9a-f]{64}", str(cursor.get("event_sha256") or "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(runner.get("state_projection_sha256") or "")) is None
    ):
        raise ProductGoalIdentityError("Runner collaboration state cursor is invalid")
    exact_authority = {
        "authority_kind": "GITHUB_OWNER_APPROVAL",
        "author_association": "OWNER",
        "goal_id": context["goal_id"],
        "goal_version": context["goal_version"],
        "goal_spec_sha256": context["goal_spec_sha256"],
        "repository": context["repository"],
        "issue": context["issue"],
    }
    if not isinstance(authority, dict) or any(authority.get(key) != value for key, value in exact_authority.items()):
        raise ProductGoalIdentityError("Runner collaboration Owner authority is invalid")
    if authority.get("action") not in {"APPROVE", "RESUME"}:
        raise ProductGoalIdentityError("Runner collaboration authority is not active")
    authority_digest = hashlib.sha256(
        json.dumps(authority, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if runner.get("authority_record_sha256") != authority_digest:
        raise ProductGoalIdentityError("Runner collaboration authority digest differs")
    if (
        not isinstance(work, dict)
        or work.get("work_item_id") != context["work_item_id"]
        or work.get("dispatch_attempt_id") != context["attempt_id"]
        or work.get("active_attempt_id") is not None
        or work.get("status") not in {"PLANNED", "READY", "REPAIR_REQUIRED", "VERIFY_REQUIRED", "PUBLISH_REQUIRED"}
        or work.get("obligation_ids") != context["obligation_ids"]
    ):
        raise ProductGoalIdentityError("Runner collaboration Work Item differs from the order")
    if not isinstance(candidate, dict) or any(
        candidate.get(left) != context.get(right)
        for left, right in {"commit": "candidate_commit", "fingerprint": "candidate_fingerprint", "branch": "branch"}.items()
    ):
        raise ProductGoalIdentityError("Runner collaboration candidate differs from the order")
    checkpoint = context.get("checkpoint")
    usage = context.get("usage")
    next_action = context.get("next_action")
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("order_event_id") != context["order_event_id"]
        or not isinstance(checkpoint.get("path"), str)
        or not isinstance(usage, dict)
        or usage.get("provider") != context["provider"]
        or not isinstance(next_action, dict)
        or next_action.get("action") != context["action"]
        or next_action.get("work_item_id") != context["work_item_id"]
    ):
        raise ProductGoalIdentityError("collaboration checkpoint, usage, or next action binding differs")
    review = context.get("review")
    if review is not None and (
        not isinstance(review, dict)
        or not isinstance(review.get("review_id"), str)
        or re.fullmatch(r"[0-9a-f]{64}", str(review.get("candidate_identity_sha256") or "")) is None
    ):
        raise ProductGoalIdentityError("collaboration review binding is invalid")
    envelope = context.get("dispatch_envelope")
    if not isinstance(envelope, dict) or envelope.get("schema_version") != "kgnote.product-goal-dispatch-envelope.v1":
        raise ProductGoalIdentityError("collaboration dispatch envelope is absent")
    expected_envelope = {
        "schema_version": "kgnote.product-goal-dispatch-envelope.v1",
        "goal": {
            "goal_id": context["goal_id"], "goal_version": context["goal_version"],
            "goal_spec_sha256": context["goal_spec_sha256"],
        },
        "work_item_id": context["work_item_id"], "attempt_id": context["attempt_id"],
        "authority": {
            "record_sha256": runner["authority_record_sha256"],
            "body_sha256": authority["body_sha256"],
            "lease": runner["authority_lease"],
        },
        "candidate": candidate,
        "checkpoint": checkpoint,
        "review": review,
        "usage": usage,
        "next_action": next_action,
    }
    if json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False) != json.dumps(
        expected_envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ):
        raise ProductGoalIdentityError("collaboration dispatch envelope differs from sealed context")
    envelope_digest = hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if context.get("dispatch_envelope_sha256") != envelope_digest:
        raise ProductGoalIdentityError("collaboration dispatch envelope digest differs")
    if identity is not None:
        if identity.get("schema_version") != COLLABORATION_IDENTITY_SCHEMA:
            raise ProductGoalIdentityError("collaboration context requires v2 bootstrap identity")
        pairs = {
            "goal_id": "goal_id", "goal_version": "goal_version",
            "goal_spec_sha256": "goal_spec_sha256", "repository": "repository",
            "issue": "issue", "work_item_id": "work_item_id",
            "order_event_id": "order_event_id", "stage": "stage",
            "provider": "provider", "candidate_commit": "candidate_commit",
            "candidate_fingerprint": "candidate_fingerprint", "branch": "branch",
        }
        if any(identity.get(left) != context.get(right) for left, right in pairs.items()):
            raise ProductGoalIdentityError("collaboration bootstrap identity differs from runtime context")
        if identity.get("authority_sha256") != authority.get("body_sha256"):
            raise ProductGoalIdentityError("collaboration bootstrap authority differs")
    return context
