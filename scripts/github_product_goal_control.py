#!/usr/bin/env python3
"""Validate GitHub Owner-authored Product Goal lifecycle authority records."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import goal_continuity


MARKER = "<!-- kgnote-product-goal-authority:v1 -->"
ALLOWED_ACTIONS = {"APPROVE", "PAUSE", "RESUME", "REVOKE", "ACCEPT", "CLOSE"}


class GitHubAuthorityError(goal_continuity.GoalContractError):
    pass


def parse_marker_payload(body: str) -> dict[str, Any]:
    if body.count(MARKER) != 1:
        raise GitHubAuthorityError("authority marker must occur exactly once")
    tail = body.split(MARKER, 1)[1]
    match = re.search(r"```json\s*(.*?)\s*```", tail, re.DOTALL)
    if not match:
        raise GitHubAuthorityError("authority marker requires one fenced JSON payload")
    if len(re.findall(r"```json\s*", tail)) != 1:
        raise GitHubAuthorityError("authority marker must contain exactly one JSON fence")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise GitHubAuthorityError("authority payload must be a JSON object")
    expected = {
        "schema_version", "action", "goal_id", "goal_version",
        "goal_spec_sha256", "permissions",
    }
    if set(value) != expected:
        raise GitHubAuthorityError(
            f"authority payload keys must be exact; got {sorted(value)}"
        )
    return value


def authority_record_from_comment(
    comment: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    goal_continuity.validate_goal_spec(spec)
    body = comment.get("body")
    if not isinstance(body, str):
        raise GitHubAuthorityError("GitHub comment body is missing")
    payload = parse_marker_payload(body)
    author = comment.get("user") if isinstance(comment.get("user"), dict) else {}
    login = author.get("login")
    if comment.get("author_association") != "OWNER" or login not in spec["owner_logins"]:
        raise GitHubAuthorityError("authority comment is not authored by an allowed repository Owner")
    if payload["schema_version"] != "kgnote.product-goal-authority-command.v1":
        raise GitHubAuthorityError("unsupported authority command schema")
    if payload["action"] not in ALLOWED_ACTIONS:
        raise GitHubAuthorityError(f"unsupported authority action: {payload['action']}")
    expected_identity = (
        spec["goal_id"], spec["goal_version"], goal_continuity.goal_spec_sha256(spec)
    )
    actual_identity = (
        payload["goal_id"], payload["goal_version"], payload["goal_spec_sha256"]
    )
    if actual_identity != expected_identity:
        raise GitHubAuthorityError("authority command does not bind the exact Goal version/spec digest")
    if payload["permissions"] != spec["allowed_operations"]:
        raise GitHubAuthorityError("authority permissions must exactly match Goal allowed_operations order")
    comment_id = comment.get("id")
    issue_url = comment.get("issue_url", "")
    issue_match = re.search(r"/issues/(\d+)$", issue_url)
    if not isinstance(comment_id, int) or not issue_match:
        raise GitHubAuthorityError("GitHub comment identity is incomplete")
    if int(issue_match.group(1)) != spec["github_issue"]:
        raise GitHubAuthorityError("authority comment belongs to the wrong GitHub Issue")
    html_url = comment.get("html_url")
    created_at = comment.get("created_at")
    if not isinstance(html_url, str) or not isinstance(created_at, str):
        raise GitHubAuthorityError("GitHub comment URL/timestamp is incomplete")
    record = {
        "schema_version": "kgnote.product-goal-authority.v1",
        "identity_kind": goal_continuity.PRODUCT_IDENTITY,
        "authority_kind": goal_continuity.PRODUCT_AUTHORITY,
        "repository": spec["repository"],
        "issue": spec["github_issue"],
        "comment_id": comment_id,
        "comment_url": html_url,
        "author_login": login,
        "author_association": "OWNER",
        "created_at": created_at,
        "action": payload["action"],
        "goal_id": payload["goal_id"],
        "goal_version": payload["goal_version"],
        "goal_spec_sha256": payload["goal_spec_sha256"],
        "permissions": deepcopy(payload["permissions"]),
        "expires_at": None,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }
    goal_continuity.validate_document(record, "github-authority-record.schema.json")
    return record


def resolve_authority(
    comments: list[dict[str, Any]], spec: dict[str, Any]
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for comment in comments:
        body = comment.get("body")
        if not isinstance(body, str) or MARKER not in body:
            continue
        try:
            records.append(authority_record_from_comment(comment, spec))
        except (GitHubAuthorityError, json.JSONDecodeError) as exc:
            rejected.append({"comment_id": comment.get("id"), "reason": str(exc)})
    records.sort(key=lambda row: (row["created_at"], row["comment_id"]))
    if not records:
        return {
            "status": "APPROVAL_REQUIRED",
            "authority_lease": "PAUSED",
            "record": None,
            "valid_records": [],
            "rejected_records": rejected,
        }
    lease = "PAUSED"
    status = "APPROVAL_REQUIRED"
    current: dict[str, Any] | None = None
    for record in records:
        action = record["action"]
        if lease == "REVOKED":
            # Revocation is terminal for an exact Goal version. A later comment
            # cannot resurrect that sealed authority; Owner must issue a new
            # Goal version/spec digest and approve it explicitly.
            continue
        if action == "APPROVE":
            lease, status, current = "ACTIVE", "APPROVED", record
        elif action == "PAUSE" and current is not None:
            lease, status, current = "PAUSED", "BLOCKED", record
        elif action == "RESUME" and current is not None and lease != "REVOKED":
            lease, status, current = "ACTIVE", "ACTIVE", record
        elif action == "REVOKE":
            lease, status, current = "REVOKED", "BLOCKED", record
        elif action == "ACCEPT" and current is not None and lease == "ACTIVE":
            status, current = "ACCEPTANCE_REQUIRED", record
        elif action == "CLOSE" and current is not None and lease == "ACTIVE":
            status, current = "CLOSED", record
    return {
        "status": status,
        "authority_lease": lease,
        "record": current,
        "valid_records": records,
        "rejected_records": rejected,
    }


def fetch_issue_comments(
    spec: dict[str, Any],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[dict[str, Any]]:
    endpoint = f"repos/{spec['repository']}/issues/{spec['github_issue']}/comments"
    result = command_runner(
        ["gh", "api", endpoint, "--paginate"], capture_output=True, text=True
    )
    if result.returncode:
        raise GitHubAuthorityError((result.stderr or "GitHub authority read failed").strip())
    value = json.loads(result.stdout)
    if not isinstance(value, list):
        raise GitHubAuthorityError("GitHub authority read did not return a list")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--comments", type=Path)
    args = parser.parse_args()
    spec = goal_continuity.load_json(args.spec)
    comments = json.loads(args.comments.read_text()) if args.comments else fetch_issue_comments(spec)
    print(json.dumps(resolve_authority(comments, spec), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
