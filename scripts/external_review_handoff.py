#!/usr/bin/env python3
"""One bounded GitHub read/consume/update cycle for an external product review."""

from __future__ import annotations

import json
import os
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Callable

import external_review_control
import github_product_review_consumer as consumer
import codex_control as control


def _run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "GitHub command failed")
    return result.stdout


def _records(reviews: list[dict[str, Any]], comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(reviews, list) or not isinstance(comments, list):
        raise ValueError("GitHub reviews and comments responses must be arrays")
    for label, rows in (("reviews", reviews), ("comments", comments)):
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"GitHub {label}[{index}] must be an object")
            if not isinstance(row.get("user", {}), dict):
                raise ValueError(f"GitHub {label}[{index}].user must be an object")
    rows = [{"source": "pull_request_review", "author_login": row.get("user", {}).get("login", ""),
             "body": row.get("body") or "", "review_state": row.get("state") or "",
             "record_id": row.get("id"), "artifact_url": row.get("html_url"),
             "submitted_at": row.get("submitted_at")} for row in reviews]
    rows.extend({"source": "issue_comment", "author_login": row.get("user", {}).get("login", ""),
                 "body": row.get("body") or "", "record_id": row.get("id"),
                 "artifact_url": row.get("html_url"), "submitted_at": row.get("created_at")} for row in comments)
    return rows


def _matching_issue_receipt(rows: list[dict[str, Any]], body: str, trusted_author: str) -> dict[str, Any] | None:
    matches = [row for row in rows if row.get("body") == body
               and row.get("user", {}).get("login") == trusted_author
               and isinstance(row.get("html_url"), str) and row.get("html_url")]
    return matches[-1] if matches else None


def _write_state(repo: Path, state: dict[str, Any]) -> None:
    temporary = repo / ".ai/external-review-state.json.tmp"
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, repo / external_review_control.STATE_PATH)


def _project_decisions_and_state(
    repo: Path, pending: dict[str, Any], state: dict[str, Any]
) -> None:
    """Commit the canonical decision queue and external state as one recoverable unit."""
    decisions_path = repo / ".ai/DECISIONS.md"
    state_path = repo / external_review_control.STATE_PATH
    decisions_before = decisions_path.read_bytes()
    state_before = state_path.read_bytes()
    decisions_temporary = repo / ".ai/DECISIONS.md.tmp"
    state_temporary = repo / ".ai/external-review-state.json.tmp"
    decisions_rollback = repo / ".ai/DECISIONS.md.rollback"
    state_rollback = repo / ".ai/external-review-state.json.rollback"
    decisions_temporary.write_bytes(decisions_before)
    control.replace_embedded_json(
        decisions_temporary, control.DECISIONS_BEGIN, control.DECISIONS_END, pending
    )
    state_temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    decisions_replaced = False
    state_replaced = False
    try:
        os.replace(decisions_temporary, decisions_path)
        decisions_replaced = True
        os.replace(state_temporary, state_path)
        state_replaced = True
    except OSError:
        if decisions_replaced:
            decisions_rollback.write_bytes(decisions_before)
            os.replace(decisions_rollback, decisions_path)
        if state_replaced:
            state_rollback.write_bytes(state_before)
            os.replace(state_rollback, state_path)
        raise
    finally:
        for path in (
            decisions_temporary, state_temporary, decisions_rollback, state_rollback
        ):
            path.unlink(missing_ok=True)


def _record_rejection(
    repo: Path,
    state: dict[str, Any],
    *,
    status: str,
    reason: str,
    rejected: list[dict[str, Any]] | None = None,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a retryable machine-owned rejection without accepting a verdict."""
    state["phase"] = "EXTERNAL_PRODUCT_REVIEW_REJECTED"
    state["external_review"] = {
        "status": status,
        "reviewed_commit": state.get("candidate_commit"),
        "reviewed_fingerprint": state.get("candidate_fingerprint"),
        "review_round": state.get("review_round"),
        "consumer_accepted": False,
        "consumer_reason": reason,
        "rejected": rejected or [],
    }
    state.pop("pending_external_decisions", None)
    if record is not None:
        state["external_review"].update({
            "record_id": record.get("record_id"),
            "artifact_url": record.get("artifact_url"),
            "review_author": record.get("author_login"),
            "review_source": record.get("source"),
            "submitted_at": record.get("submitted_at"),
            "original_body_sha256": hashlib.sha256(
                str(record.get("body", "")).encode("utf-8")
            ).hexdigest(),
        })
    _write_state(repo, state)
    return {
        "status": status,
        "accepted": False,
        "reason": reason,
        "rejected": rejected or [],
    }


def process(repo: Path, runner: Callable[..., str] | None = None) -> dict[str, Any]:
    runner = runner or _run
    config = external_review_control.load_json(repo / external_review_control.CONFIG_PATH)
    state = external_review_control.load_json(repo / external_review_control.STATE_PATH)
    blockers = external_review_control.publication_progression_blockers(config, state)
    if blockers:
        return {"status": "AUTOMATION_BLOCKED", "accepted": False, "errors": blockers}
    try:
        canonical_authority = external_review_control.resolve_repository_canonical_authority(
            repo, runner
        )
    except (OSError, ValueError, external_review_control.CanonicalAuthorityError) as exc:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason=f"canonical publication authority failed closed: {exc}",
        )
    repository, pr = config["canonical_repository"], config["review_pr_number"]
    try:
        reviews = json.loads(runner(["gh", "api", f"repos/{repository}/pulls/{pr}/reviews", "--paginate"], cwd=repo))
        comments = json.loads(runner(["gh", "api", f"repos/{repository}/issues/{pr}/comments", "--paginate"], cwd=repo))
        records = _records(reviews, comments)
    except (json.JSONDecodeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason=f"external review adapter failed closed: {exc}",
        )
    identity = consumer.CandidateIdentity(repository, pr, config["program_id"], state["goal_id"],
        state["candidate_fingerprint"], state["candidate_commit"], state["review_round"])
    schema = external_review_control.load_json(repo / "schemas/product-review/v1/review-result.schema.json")
    try:
        decision = consumer.consume_records(
            config=config, schema=schema, identity=identity, records=records
        )
    except consumer.ConsumerInputError as exc:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason=f"external review consumer failed closed: {exc}",
        )
    if not decision.get("accepted"):
        malformed = [
            item for item in decision.get("rejected", [])
            if item.get("reason") in {
                "schema_invalid", "invalid_json",
                "expected_exactly_one_fenced_json_object", "semantic_invalid",
            }
        ]
        if malformed:
            return _record_rejection(
                repo, state, status="REVIEW_REJECTED",
                reason="external result is malformed or lacks required canonical decision proposals",
                rejected=malformed,
            )
        return decision
    matches = [
        row for row in records
        if row.get("record_id") == decision.get("record_id")
        and row["source"] == decision.get("review_source")
    ]
    if len(matches) != 1:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason="accepted external result does not resolve to exactly one fetched record",
        )
    matching = matches[0]
    invalid_metadata = [
        field for field in ("artifact_url", "submitted_at")
        if not isinstance(matching.get(field), str) or not matching[field].strip()
    ]
    record_id = matching.get("record_id")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        invalid_metadata.insert(0, "record_id")
    if invalid_metadata:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason=("accepted external record has missing or invalid required metadata: "
                    + ", ".join(invalid_metadata)),
            record=matching,
        )
    accepted_review = {
        "status": decision["verdict"], "reviewed_commit": decision["candidate_commit"],
        "reviewed_fingerprint": decision["candidate_fingerprint"], "artifact_url": matching.get("artifact_url"),
        "review_author": decision["review_author"], "review_source": decision["review_source"],
        "record_id": decision["record_id"], "native_ui_observed": decision["native_ui_observed"],
        "repository": repository, "pull_request": pr, "review_round": decision["review_round"],
        "submitted_at": matching.get("submitted_at"),
        "original_body_sha256": hashlib.sha256(matching["body"].encode("utf-8")).hexdigest(),
        "findings": decision["findings"],
        "blocking_findings": [item["id"] for item in decision["findings"] if item.get("severity") == "blocking"],
        "consumer_accepted": True,
    }
    accepted_errors = external_review_control.accepted_external_review_blockers(
        config, state, accepted_review, canonical_authority=canonical_authority
    )
    if accepted_errors:
        return _record_rejection(
            repo, state, status="ADAPTER_REJECTED",
            reason=("accepted external record failed durable identity validation: "
                    + "; ".join(accepted_errors)),
            record=matching,
        )
    state["phase"] = "EXTERNAL_PRODUCT_REVIEW_ACCEPTED"
    state["external_review"] = accepted_review
    if decision["verdict"] == "PRODUCT_DECISION_REQUIRED":
        request, _result, decisions = control.load_review_artifacts(repo)
        if (request.get("status") != "PASS"
                or request.get("candidate_fingerprint") != state["candidate_fingerprint"]
                or not str(request.get("candidate_revision", "")).startswith(state["candidate_commit"] + "+worktree:")):
            return _record_rejection(
                repo, state, status="ADAPTER_REJECTED",
                reason="external product decision is not bound to the sealed internal PASS candidate",
                record=matching,
            )
        proposals = decision.get("human_decisions")
        if not isinstance(proposals, list) or not proposals:
            return _record_rejection(
                repo, state, status="REVIEW_REJECTED",
                reason="external PRODUCT_DECISION_REQUIRED lacks canonical decision proposals",
                record=matching,
            )
        finding_ids = {
            item.get("id") for item in decision.get("findings", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        invalid_links = {
            item.get("decision_id"): sorted(
                set(item.get("linked_findings", [])) - finding_ids
            )
            for item in proposals if isinstance(item, dict)
        }
        invalid_links = {
            decision_id: links for decision_id, links in invalid_links.items() if links
        }
        if invalid_links:
            return _record_rejection(
                repo, state, status="REVIEW_REJECTED",
                reason=f"external product decision links unknown findings: {invalid_links}",
                record=matching,
            )
        projected = []
        for item in proposals:
            projected.append({
                **item,
                "status": "PENDING_HUMAN",
                "review_id": request["review_id"],
                "candidate_revision": request["candidate_revision"],
                "candidate_fingerprint": request["candidate_fingerprint"],
                "selected_option": None,
                "decided_by": None,
                "decided_at": None,
                "authority_record": None,
            })
        pending = {**decisions, "decisions": projected}
        decision_errors = control.validate_decisions(pending, repo, request)
        if decision_errors:
            return _record_rejection(
                repo, state, status="REVIEW_REJECTED",
                reason="external product decision is not protocol-valid: " + "; ".join(decision_errors),
                record=matching,
            )
        state["pending_external_decisions"] = [item["decision_id"] for item in projected]
        try:
            _project_decisions_and_state(repo, pending, state)
        except (OSError, ValueError) as exc:
            return _record_rejection(
                repo, state, status="ADAPTER_REJECTED",
                reason=f"canonical decision projection failed closed: {exc}",
                record=matching,
            )
        return decision
    if decision["verdict"] == "PASS":
        issue_path = f"repos/{repository}/issues/{config['delivery_issue_number']}/comments"
        issue_comments = json.loads(runner(["gh", "api", issue_path, "--paginate"], cwd=repo))
        body = external_review_control.issue_receipt_body(
            config, state, matching["artifact_url"],
            canonical_authority=canonical_authority,
        )
        issue_receipt = _matching_issue_receipt(issue_comments, body, config["trusted_reviewer_author_login"])
        if issue_receipt is None:
            runner(["gh", "api", issue_path, "-f", f"body={body}"], cwd=repo)
            issue_comments = json.loads(runner(["gh", "api", issue_path, "--paginate"], cwd=repo))
            issue_receipt = _matching_issue_receipt(issue_comments, body, config["trusted_reviewer_author_login"])
        if issue_receipt is None:
            raise RuntimeError("Issue receipt exact read-back failed")
        runner(["gh", "project", "item-edit", "--id", config["project_item_id"], "--project-id", config["project_id"],
                "--field-id", config["project_status_field_id"], "--single-select-option-id", config["project_review_option_id"]], cwd=repo)
        items = json.loads(runner(["gh", "project", "item-list", str(config["project_number"]), "--owner", config["project_owner"], "--format", "json", "--limit", "100"], cwd=repo))
        item = next((row for row in items.get("items", []) if row.get("id") == config["project_item_id"]), None)
        content = item.get("content", {}) if item else {}
        if (not item or item.get("status") != "Review Queue"
                or content.get("number") != config["delivery_issue_number"]
                or content.get("repository") != repository):
            raise RuntimeError("Project read-back did not confirm the canonical Issue linkage and Review Queue")
        state["delivery_receipt"] = {"status": "VERIFIED", "repository": repository, "pull_request": pr,
            "candidate_commit": state["candidate_commit"], "candidate_fingerprint": state["candidate_fingerprint"],
            "review_round": state["review_round"], "review_artifact_url": matching.get("artifact_url"),
            "issue": config["delivery_issue_number"], "issue_comment_id": issue_receipt.get("id"),
            "issue_comment_url": issue_receipt.get("html_url"),
            "issue_comment_author": issue_receipt.get("user", {}).get("login"),
            "project_item_id": config["project_item_id"], "project_status": item.get("status"),
            "project_content_repository": content.get("repository"), "project_content_issue": content.get("number"),
            "issue_receipt_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "preserved_gates": ["PA-HUMAN-1", "NS-HUMAN-SMOKE", "release_verified=false"]}
    _write_state(repo, state)
    return decision
