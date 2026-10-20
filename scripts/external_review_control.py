#!/usr/bin/env python3
"""Fail-closed authority and transition checks for external product review."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
from datetime import datetime
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


class CanonicalAuthorityError(RuntimeError):
    """The live canonical publication cannot be resolved exactly."""


def canonical_authority_blockers(
    config: Mapping[str, Any], authority: Mapping[str, Any] | None
) -> list[str]:
    """Validate an authority resolved independently from mutable receipt state."""
    if not isinstance(authority, Mapping):
        return ["external_review: independent canonical publication authority is missing"]
    blockers: list[str] = []
    expected = {
        "repository": config.get("canonical_repository"),
        "pull_request": config.get("review_pr_number"),
    }
    for field, value in expected.items():
        if authority.get(field) != value:
            blockers.append(f"external_review: canonical authority mismatch for {field}")
    commit = authority.get("candidate_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        blockers.append("external_review: canonical authority commit must be 40 lowercase hex characters")
    fingerprint = authority.get("candidate_fingerprint")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        blockers.append("external_review: canonical authority fingerprint must be 64 lowercase hex characters")
    review_round = authority.get("review_round")
    maximum = config.get("max_product_review_rounds")
    if (
        isinstance(review_round, bool)
        or not isinstance(review_round, int)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < 1
        or not 1 <= review_round <= maximum
    ):
        blockers.append("external_review: canonical authority round is outside the sealed authorization")
    return blockers


def resolve_canonical_publication_authority(
    config: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    recomputed_fingerprint: str,
) -> dict[str, Any]:
    """Resolve the exact candidate from the live canonical PR and local bytes."""
    errors = repository_authority_errors(config)
    if snapshot.get("repository") != config.get("canonical_repository"):
        errors.append("external_review: live publication repository is not canonical")
    if snapshot.get("pull_request") != config.get("review_pr_number"):
        errors.append("external_review: live publication pull request is not canonical")
    if snapshot.get("state") != "OPEN":
        errors.append("external_review: canonical review pull request is not open")
    if config.get("schema_version") == "kgnote.github-product-reviewer-config.v2":
        expected_shape = {
            "isDraft": config.get("review_pr_expected_draft"),
            "headRefName": config.get("review_pr_head_branch"),
            "baseRefName": config.get("review_pr_base_branch"),
        }
        for field, expected in expected_shape.items():
            if snapshot.get(field) != expected:
                errors.append(
                    f"external_review: canonical review pull request mismatch for {field}"
                )
    pattern = re.compile(
        rf"<!--\s*{re.escape(str(config.get('request_marker', '')))}\s+"
        r"candidate_commit=([0-9a-f]{40})\s+"
        r"candidate_fingerprint=([0-9a-f]{64})\s+"
        r"review_round=([1-9][0-9]*)\s*-->"
    )
    matches = pattern.findall(str(snapshot.get("body", "")))
    if len(matches) != 1:
        errors.append("external_review: canonical publication requires exactly one request marker")
        commit = fingerprint = ""
        review_round = 0
    else:
        commit, fingerprint, round_text = matches[0]
        review_round = int(round_text)
        if commit != snapshot.get("headRefOid"):
            errors.append("external_review: request marker commit does not match live PR head")
        if fingerprint != recomputed_fingerprint:
            errors.append("external_review: request marker fingerprint does not match recomputed candidate")
    authority = {
        "repository": snapshot.get("repository"),
        "pull_request": snapshot.get("pull_request"),
        "candidate_commit": commit,
        "candidate_fingerprint": fingerprint,
        "review_round": review_round,
    }
    errors.extend(canonical_authority_blockers(config, authority))
    if errors:
        raise CanonicalAuthorityError("; ".join(dict.fromkeys(errors)))
    return authority


def _run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.returncode:
        raise CanonicalAuthorityError(
            f"canonical authority command failed closed: {' '.join(command[:3])}: "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout.rstrip("\r\n")


def resolve_repository_canonical_authority(
    repo: Path, runner: Any | None = None
) -> dict[str, Any]:
    """Read the live PR and bind it to a fresh fingerprint of this checkout."""
    runner = runner or _run
    config = load_json(repo / CONFIG_PATH)
    repository = config.get("canonical_repository")
    pull_request = config.get("review_pr_number")
    raw = runner(
        [
            "gh", "pr", "view", str(pull_request), "--repo", str(repository),
            "--json", "headRefOid,body,state,url,isDraft,headRefName,baseRefName",
        ],
        cwd=repo,
    )
    try:
        snapshot = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CanonicalAuthorityError(f"canonical PR read-back is invalid JSON: {exc}") from exc
    if not isinstance(snapshot, dict):
        raise CanonicalAuthorityError("canonical PR read-back must be an object")
    snapshot.update({"repository": repository, "pull_request": pull_request})
    import codex_control  # Lazy import avoids a control-plane import cycle.

    fingerprint = codex_control.repository_fingerprint(repo)["value"]
    authority = resolve_canonical_publication_authority(config, snapshot, fingerprint)
    dependency = config.get("dependency_pr_number")
    if dependency is not None:
        dependency_raw = runner(
            [
                "gh", "pr", "view", str(dependency), "--repo", str(repository),
                "--json", "number,state,mergedAt",
            ],
            cwd=repo,
        )
        try:
            dependency_snapshot = json.loads(dependency_raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise CanonicalAuthorityError(
                f"dependency PR read-back is invalid JSON: {exc}"
            ) from exc
        if (
            not isinstance(dependency_snapshot, Mapping)
            or dependency_snapshot.get("number") != dependency
            or dependency_snapshot.get("state") != config.get("dependency_pr_required_state")
            or dependency_snapshot.get("mergedAt") is not None
        ):
            raise CanonicalAuthorityError(
                "external_review: dependency pull request routing is no longer valid"
            )
    return authority


def _canonical_record_from_github(
    source: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Normalize one exact GitHub record without trusting local durable state."""
    user = payload.get("user")
    if not isinstance(user, Mapping):
        raise CanonicalAuthorityError("external_review: GitHub record author is missing")
    if source == "pull_request_review":
        return {
            "source": source,
            "author_login": user.get("login", ""),
            "body": payload.get("body") or "",
            "review_state": payload.get("state") or "",
            "record_id": payload.get("id"),
            "artifact_url": payload.get("html_url"),
            "submitted_at": payload.get("submitted_at"),
        }
    if source == "issue_comment":
        return {
            "source": source,
            "author_login": user.get("login", ""),
            "body": payload.get("body") or "",
            "record_id": payload.get("id"),
            "artifact_url": payload.get("html_url"),
            "submitted_at": payload.get("created_at"),
        }
    raise CanonicalAuthorityError("external_review: durable review source is invalid")


def revalidated_external_review_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    canonical_authority: Mapping[str, Any],
) -> list[str]:
    """Re-run the Consumer on canonical bytes and compare the complete durable record."""
    import github_product_review_consumer as consumer

    review = state.get("external_review")
    if not isinstance(review, Mapping):
        return ["external_review: complete accepted external record is missing"]
    authority_errors = canonical_authority_blockers(config, canonical_authority)
    if authority_errors:
        return authority_errors
    identity = consumer.CandidateIdentity(
        str(canonical_authority["repository"]),
        int(canonical_authority["pull_request"]),
        str(config.get("program_id", "")),
        str(state.get("goal_id", "")),
        str(canonical_authority["candidate_fingerprint"]),
        str(canonical_authority["candidate_commit"]),
        int(canonical_authority["review_round"]),
    )
    try:
        decision = consumer.consume_records(
            config=dict(config), schema=dict(schema), identity=identity,
            records=[dict(record)],
        )
    except consumer.ConsumerInputError as exc:
        return [f"external_review: canonical GitHub record is invalid: {exc}"]
    if not decision.get("accepted"):
        return ["external_review: canonical GitHub record is not an accepted exact-candidate result"]
    findings = decision.get("findings", [])
    expected = {
        "status": decision.get("verdict"),
        "reviewed_commit": decision.get("candidate_commit"),
        "reviewed_fingerprint": decision.get("candidate_fingerprint"),
        "artifact_url": record.get("artifact_url"),
        "review_author": decision.get("review_author"),
        "review_source": decision.get("review_source"),
        "record_id": decision.get("record_id"),
        "submitted_at": record.get("submitted_at"),
        "repository": canonical_authority.get("repository"),
        "pull_request": canonical_authority.get("pull_request"),
        "review_round": decision.get("review_round"),
        "findings": findings,
        "blocking_findings": [
            item["id"] for item in findings
            if isinstance(item, Mapping) and item.get("severity") == "blocking"
        ],
        "consumer_accepted": True,
        "original_body_sha256": hashlib.sha256(
            str(record.get("body", "")).encode("utf-8")
        ).hexdigest(),
    }
    blockers: list[str] = []
    for field, expected_value in expected.items():
        if review.get(field) != expected_value:
            blockers.append(
                f"external_review: durable record differs from canonical GitHub field {field}"
            )
    return blockers


def resolve_repository_external_review(
    repo: Path, runner: Any | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Read and validate canonical PR/dependency state plus the exact review record."""
    runner = runner or _run
    config = load_json(repo / CONFIG_PATH)
    state = load_json(repo / STATE_PATH)
    authority = resolve_repository_canonical_authority(repo, runner)
    review = state.get("external_review")
    if not isinstance(review, Mapping):
        return authority, ["external_review: complete accepted external record is missing"]
    source = review.get("review_source")
    record_id = review.get("record_id")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        return authority, ["external_review: accepted record_id must be a positive integer"]
    repository = config.get("canonical_repository")
    if source == "pull_request_review":
        endpoint = f"repos/{repository}/pulls/{config.get('review_pr_number')}/reviews/{record_id}"
    elif source == "issue_comment":
        endpoint = f"repos/{repository}/issues/comments/{record_id}"
    else:
        return authority, ["external_review: durable review source is invalid"]
    raw = runner(["gh", "api", endpoint], cwd=repo)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CanonicalAuthorityError(
            f"canonical GitHub record read-back is invalid JSON: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise CanonicalAuthorityError("canonical GitHub record read-back must be an object")
    record = _canonical_record_from_github(str(source), payload)
    schema = load_json(repo / "schemas/product-review/v1/review-result.schema.json")
    blockers = revalidated_external_review_blockers(
        config, state, record, schema, canonical_authority=authority
    )
    return authority, blockers


def issue_receipt_body(
    config: Mapping[str, Any], state: Mapping[str, Any], artifact_url: str, *,
    canonical_authority: Mapping[str, Any] | None = None,
) -> str:
    identity = canonical_authority if isinstance(canonical_authority, Mapping) else state
    marker = (f"<!-- KGNOTE_ISSUE8_REVIEW_RECEIPT commit={identity['candidate_commit']} "
              f"fingerprint={identity['candidate_fingerprint']} round={identity['review_round']} -->")
    return (marker + "\n\n外部獨立審查已由 Consumer（審查結果接收器）核對精確 repository、PR、HEAD、Fingerprint 與 Round。\n\n"
            f"- Repository：`{config['canonical_repository']}`\n- PR：#{config['review_pr_number']}\n"
            f"- HEAD：`{identity['candidate_commit']}`\n- Fingerprint：`{identity['candidate_fingerprint']}`\n"
            f"- Round：{identity['review_round']}\n- Review：{artifact_url}\n- Consumer：accepted\n"
            "- 限制：PR #23 尚未合併；跨工作階段自動喚醒與 Work 無人值守寫回仍未獨立證明。\n"
            "- 回復：關閉未合併的 Draft PR 並將 Project 狀態移回 In Progress。\n"
            "- PA-HUMAN-1、NS-HUMAN-SMOKE、release_verified=false 均未提升。")


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
    if config.get("trigger_comment_template") != "@kgnote-ai-review {candidate_commit}":
        errors.append("external_review: exact review trigger comment template is missing")
    if config.get("schema_version") == "kgnote.github-product-reviewer-config.v2":
        if config.get("review_pr_expected_draft") is not True:
            errors.append("external_review: candidate PR must remain Draft")
        for field in ("review_pr_head_branch", "review_pr_base_branch", "dependency_pr_required_state"):
            if not isinstance(config.get(field), str) or not config.get(field):
                errors.append(f"external_review: missing {field}")
        if not isinstance(config.get("dependency_pr_number"), int):
            errors.append("external_review: missing dependency_pr_number")
    return errors


def accepted_external_review_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    review: Mapping[str, Any] | None = None,
    *,
    canonical_authority: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate the complete durable identity of an accepted external record."""
    value = review if review is not None else state.get("external_review")
    if not isinstance(value, Mapping):
        return ["external_review: complete accepted external record is missing"]

    blockers = canonical_authority_blockers(config, canonical_authority)
    record_id = value.get("record_id")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        blockers.append("external_review: accepted record_id must be a positive integer")

    artifact_url = value.get("artifact_url")
    repository = re.escape(str(config.get("canonical_repository", "")))
    pull_request = config.get("review_pr_number")
    source = value.get("review_source")
    anchor = "pullrequestreview" if source == "pull_request_review" else "issuecomment"
    expected_url = rf"https://github\.com/{repository}/pull/{pull_request}#{anchor}-([0-9]+)"
    url_match = re.fullmatch(
        expected_url, artifact_url if isinstance(artifact_url, str) else ""
    )
    if not url_match or not isinstance(record_id, int) or int(url_match.group(1)) != record_id:
        blockers.append("external_review: accepted artifact_url is not the canonical source-specific record URL")

    trusted_author = config.get("trusted_reviewer_author_login")
    if (
        not isinstance(trusted_author, str)
        or not trusted_author
        or value.get("review_author") != trusted_author
    ):
        blockers.append("external_review: accepted review_author is not the trusted reviewer")
    if value.get("review_source") not in {"pull_request_review", "issue_comment"}:
        blockers.append("external_review: accepted review_source is invalid")

    submitted_at = value.get("submitted_at")
    submitted_time = None
    if isinstance(submitted_at, str) and submitted_at:
        try:
            submitted_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except ValueError:
            submitted_time = None
    if submitted_time is None or submitted_time.tzinfo is None:
        blockers.append("external_review: accepted submitted_at must be a timezone-aware timestamp")

    authority = canonical_authority if isinstance(canonical_authority, Mapping) else {}
    expected_identity = {
        "repository": authority.get("repository"),
        "pull_request": authority.get("pull_request"),
        "review_round": authority.get("review_round"),
        "reviewed_commit": authority.get("candidate_commit"),
        "reviewed_fingerprint": authority.get("candidate_fingerprint"),
    }
    for field, expected in expected_identity.items():
        actual = value.get(field)
        if (
            expected is None
            or isinstance(actual, bool)
            or actual != expected
        ):
            blockers.append(f"external_review: accepted record identity mismatch for {field}")

    if value.get("status") not in {
        "PASS", "CHANGES_REQUIRED", "PRODUCT_DECISION_REQUIRED"
    }:
        blockers.append("external_review: accepted verdict is invalid")
    findings = value.get("findings")
    findings_valid = isinstance(findings, list) and all(
        isinstance(item, Mapping)
        and isinstance(item.get("id"), str)
        and bool(item["id"])
        for item in findings or []
    )
    if not findings_valid:
        blockers.append("external_review: accepted findings are malformed")
    blocking_findings = value.get("blocking_findings")
    expected_blocking = [
        item["id"] for item in findings or []
        if isinstance(item, Mapping) and item.get("severity") == "blocking"
        and isinstance(item.get("id"), str) and item.get("id")
    ] if isinstance(findings, list) else []
    if not isinstance(blocking_findings, list) or blocking_findings != expected_blocking:
        blockers.append("external_review: accepted blocking findings projection is invalid")
    if value.get("consumer_accepted") is not True:
        blockers.append("external_review: accepted record lacks Consumer acceptance")
    digest = value.get("original_body_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        blockers.append("external_review: accepted original-body digest is invalid")
    return blockers


def human_gate_blockers(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    candidate_commit: str | None = None,
    candidate_fingerprint: str | None = None,
    canonical_authority: Mapping[str, Any] | None = None,
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
    blockers.extend(accepted_external_review_blockers(
        config, state, review, canonical_authority=canonical_authority
    ))
    if review.get("status") != "PASS":
        blockers.append("external_review: external PASS is required before human acceptance")
    if not review.get("artifact_url"):
        blockers.append("external_review: verifiable external review artifact is missing")
    if review.get("blocking_findings"):
        blockers.append("external_review: blocking findings remain")

    authority = canonical_authority if isinstance(canonical_authority, Mapping) else {}
    expected_commit = candidate_commit or authority.get("candidate_commit")
    expected_fingerprint = candidate_fingerprint or authority.get("candidate_fingerprint")
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
    blockers.extend(delivery_receipt_blockers(
        config, state, canonical_authority=canonical_authority
    ))
    return blockers


def delivery_receipt_blockers(
    config: Mapping[str, Any], state: Mapping[str, Any], *,
    canonical_authority: Mapping[str, Any] | None = None,
) -> list[str]:
    blockers = accepted_external_review_blockers(
        config, state, canonical_authority=canonical_authority
    )
    receipt = state.get("delivery_receipt")
    if config.get("delivery_issue_number") is not None and (not isinstance(receipt, Mapping) or receipt.get("status") != "VERIFIED"):
        return ["external_review: Issue/Project delivery receipt is missing"]
    if isinstance(receipt, Mapping):
        review = state.get("external_review")
        artifact_url = review.get("artifact_url") if isinstance(review, Mapping) else None
        authority = canonical_authority if isinstance(canonical_authority, Mapping) else {}
        expected_receipt = {"repository": authority.get("repository"), "pull_request": authority.get("pull_request"),
            "candidate_commit": authority.get("candidate_commit"), "candidate_fingerprint": authority.get("candidate_fingerprint"),
            "review_round": authority.get("review_round"), "project_status": "Review Queue",
            "review_artifact_url": artifact_url,
            "issue": config.get("delivery_issue_number"),
            "project_item_id": config.get("project_item_id"),
            "project_content_repository": config.get("canonical_repository"),
            "project_content_issue": config.get("delivery_issue_number"),
            "issue_comment_author": config.get("trusted_reviewer_author_login"),
            "preserved_gates": ["PA-HUMAN-1", "NS-HUMAN-SMOKE", "release_verified=false"]}
        for field, value in expected_receipt.items():
            if receipt.get(field) != value:
                blockers.append(f"external_review: delivery receipt mismatch for {field}")
        comment_id = receipt.get("issue_comment_id")
        comment_url = receipt.get("issue_comment_url")
        repository = re.escape(str(config.get("canonical_repository", "")))
        issue = config.get("delivery_issue_number")
        expected_url = rf"https://github\.com/{repository}/issues/{issue}#issuecomment-([0-9]+)"
        match = re.fullmatch(expected_url, comment_url or "")
        if not isinstance(comment_id, int) or not match or int(match.group(1)) != comment_id:
            blockers.append("external_review: delivery receipt Issue comment identity is invalid")
        if not artifact_url:
            blockers.append("external_review: accepted external review artifact is missing")
        if not receipt.get("issue_comment_url") or not receipt.get("review_artifact_url") or not receipt.get("issue_receipt_body_sha256"):
            blockers.append("external_review: delivery receipt read-back URLs are missing")
        elif artifact_url:
            expected_body = issue_receipt_body(
                config, state, artifact_url, canonical_authority=canonical_authority
            )
            expected_digest = hashlib.sha256(expected_body.encode("utf-8")).hexdigest()
            if receipt.get("issue_receipt_body_sha256") != expected_digest:
                blockers.append("external_review: delivery receipt body digest does not match canonical content")
    return blockers


def next_machine_state(
    config: Mapping[str, Any], state: Mapping[str, Any], *,
    canonical_authority: Mapping[str, Any] | None = None,
) -> str:
    """Derive the autonomous next state without promoting a human gate."""
    authority = repository_authority_errors(config)
    if authority:
        return "AUTHORITY_CONFLICT"
    review = state.get("external_review")
    if not isinstance(review, Mapping) or not review.get("artifact_url"):
        return "WAITING_FOR_EXTERNAL_REVIEW"
    if review.get("status") == "CHANGES_REQUIRED" or review.get("blocking_findings"):
        return "REPAIRING_EXTERNAL_FINDINGS"
    if not human_gate_blockers(config, state, canonical_authority=canonical_authority):
        return "HUMAN_CHECKPOINT_REQUIRED"
    return "WAITING_FOR_EXTERNAL_REVIEW"


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


def repository_human_gate_blockers(
    repo: Path, *, canonical_authority: Mapping[str, Any] | None = None,
    runner: Any | None = None,
) -> list[str]:
    try:
        config = load_json(repo / CONFIG_PATH)
        state = load_json(repo / STATE_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"external_review: cannot load canonical state: {exc}"]
    if canonical_authority is None:
        try:
            canonical_authority, evidence_blockers = resolve_repository_external_review(
                repo, runner
            )
        except (OSError, ValueError, CanonicalAuthorityError) as exc:
            return [f"external_review: cannot revalidate canonical external evidence: {exc}"]
        if evidence_blockers:
            return evidence_blockers
    return human_gate_blockers(
        config, state, canonical_authority=canonical_authority
    )


__all__ = [
    "ACTIVE_REPOSITORY_FIELDS",
    "CanonicalAuthorityError",
    "accepted_external_review_blockers",
    "canonical_authority_blockers",
    "delivery_receipt_blockers",
    "human_gate_blockers",
    "issue_receipt_body",
    "next_machine_state",
    "publication_progression_blockers",
    "repository_authority_errors",
    "repository_human_gate_blockers",
    "repository_publication_progression_blockers",
    "revalidated_external_review_blockers",
    "resolve_canonical_publication_authority",
    "resolve_repository_external_review",
    "resolve_repository_canonical_authority",
]
