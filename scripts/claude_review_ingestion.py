#!/usr/bin/env python3
"""Strict Claude/agent-loop result adapter for the existing KGnote Consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Any

from github_product_review_consumer import CandidateIdentity, ConsumerInputError, consume_records


class IngestionError(RuntimeError):
    pass


TERMINAL_FAILURES = {"TIMEOUT", "QUOTA_EXHAUSTED", "PROVIDER_FAILURE", "CRASHED"}
LEGACY_PRODUCT_CONTRACT_SCOPE = "KGNOTE_PRODUCT_CONTRACT"


def _github(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise IngestionError(result.stderr.strip() or "GitHub command failed")
    return result.stdout


def publish_validated_review(
    *, event: dict[str, Any], config: dict[str, Any], schema: dict[str, Any],
    checkpoint_path: Path, cwd: Path,
    runner: Any = None,
) -> dict[str, Any]:
    """Publish once and consume only the record fetched back from GitHub.

    This boundary deliberately requires a separate, explicit writer authority.
    Reviewer admission alone never implies permission to write GitHub evidence.
    """
    runner = runner or _github
    allowed = config.get("github_writeback_authorized_reviewer_identities", [])
    if (config.get("github_writeback_enabled") is not True
            or event.get("reviewer_identity") not in allowed):
        raise IngestionError("GitHub writeback is not authorized for reviewer identity")
    validated = ingest(
        event=event, config=config, schema=schema, checkpoint_path=checkpoint_path
    )
    if validated.get("status") == "ALREADY_CONSUMED":
        return validated
    repository, pull_request = event["repository"], event["pull_request"]
    try:
        head = json.loads(runner(
            ["gh", "pr", "view", str(pull_request), "--repo", repository,
             "--json", "headRefOid"], cwd=cwd
        )).get("headRefOid")
    except (json.JSONDecodeError, AttributeError) as exc:
        raise IngestionError("GitHub PR identity read-back failed") from exc
    if head != event["candidate_commit"]:
        raise IngestionError("GitHub PR HEAD does not match reviewed candidate")
    result = dict(event["review"])
    for field, value in {
        "protocol": "kgnote.product-review.v1", "repository": repository,
        "pull_request": pull_request, "program_id": event["program_id"],
        "goal_id": event["goal_id"], "candidate_fingerprint": event["candidate_fingerprint"],
        "candidate_commit": event["candidate_commit"], "review_round": event["review_round"],
    }.items():
        result[field] = value
    body = (
        f"<!-- {config['result_marker']} reviewed_head_sha={event['candidate_commit']} -->\n"
        f"Reviewer transport: `{event['reviewer_identity']}` (Runner relay; not ChatGPT Work).\n\n"
        f"```json\n{json.dumps(result, ensure_ascii=False)}\n```"
    )
    endpoint = f"repos/{repository}/issues/{pull_request}/comments"

    def fetched_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            rows = json.loads(runner(["gh", "api", endpoint, "--paginate"], cwd=cwd))
        except json.JSONDecodeError as exc:
            raise IngestionError("GitHub comment read-back failed") from exc
        if not isinstance(rows, list):
            raise IngestionError("GitHub comment read-back was not an array")
        exact = [row for row in rows if row.get("body") == body]
        records = [{
            "source": "issue_comment", "author_login": row.get("user", {}).get("login", ""),
            "record_id": row.get("id"), "body": row.get("body", ""),
            "artifact_url": row.get("html_url"), "submitted_at": row.get("created_at"),
        } for row in rows]
        return exact, records

    exact, records = fetched_records()
    if len(exact) > 1:
        raise IngestionError("multiple exact GitHub review artifacts exist")
    if not exact:
        runner(["gh", "api", endpoint, "-f", f"body={body}"], cwd=cwd)
        exact, records = fetched_records()
    if len(exact) != 1:
        raise IngestionError("GitHub writeback exact read-back failed")
    row = exact[0]
    required = {
        "record_id": row.get("id"), "artifact_url": row.get("html_url"),
        "submitted_at": row.get("created_at"), "author_login": row.get("user", {}).get("login"),
    }
    if (isinstance(required["record_id"], bool) or not isinstance(required["record_id"], int)
            or required["record_id"] <= 0 or not all(required[name] for name in
            ("artifact_url", "submitted_at", "author_login"))):
        raise IngestionError("GitHub canonical record metadata is invalid")
    identity = CandidateIdentity(
        repository, pull_request, event["program_id"], event["goal_id"],
        event["candidate_fingerprint"], event["candidate_commit"], event["review_round"],
    )
    decision = consume_records(config=config, schema=schema, identity=identity, records=records)
    if not decision.get("accepted") or decision.get("record_id") != required["record_id"]:
        raise IngestionError("canonical Consumer rejected GitHub read-back")
    canonical = {
        **validated, "status": decision["status"], "product_review_accepted": True,
        "canonical_record": {
            "record_id": required["record_id"], "artifact_url": required["artifact_url"],
            "author": required["author_login"], "submitted_at": required["submitted_at"],
            "reviewer_identity": event["reviewer_identity"],
            "publisher_identity": required["author_login"],
            "source": "issue_comment", "original_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "repository": repository, "pull_request": pull_request,
            "candidate_commit": event["candidate_commit"],
            "candidate_fingerprint": event["candidate_fingerprint"],
        },
    }
    _atomic(checkpoint_path, canonical)
    return canonical


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _configured_product_contract_scope(config: dict[str, Any]) -> str:
    """Return the one exact descriptive scope authorized as product review.

    Older goal-scoped configs used the literal legacy scope.  New configs bind
    the complete descriptive scope so ingestion does not require the order to
    masquerade as a different work type and does not broaden admission to every
    non-empty scope.
    """
    scope = config.get("product_contract_review_scope", LEGACY_PRODUCT_CONTRACT_SCOPE)
    if not isinstance(scope, str) or not scope.strip():
        raise IngestionError("config.product_contract_review_scope must be a non-empty string")
    return scope


def event_from_adapter_checkpoint(
    *, reviewer_checkpoint: dict[str, Any], work_order: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Convert one exact Adapter checkpoint into the canonical ingestion event."""
    required_order = {
        "goal_id", "repository", "issue", "pull_request", "candidate_commit",
        "candidate_fingerprint", "review_round_used", "review_round_limit",
        "program_id", "review_scope",
    }
    missing = sorted(required_order - work_order.keys())
    if missing:
        raise IngestionError(f"work order is missing ingestion fields: {missing}")
    for field in ("issue", "pull_request", "review_round_used", "review_round_limit"):
        if isinstance(work_order[field], bool) or not isinstance(work_order[field], int):
            raise IngestionError(f"work order field {field} must be an integer")
    for field in (
        "goal_id", "repository", "candidate_commit", "candidate_fingerprint",
        "program_id", "review_scope",
    ):
        if not isinstance(work_order[field], str) or not work_order[field].strip():
            raise IngestionError(f"work order field {field} must be a non-empty string")
    if reviewer_checkpoint.get("schema_version") != "kgnote.claude-reviewer-adapter-checkpoint.v1":
        raise IngestionError("reviewer checkpoint schema is not supported")
    round_number = work_order["review_round_used"] + 1
    identity_key = hashlib.sha256(
        (
            f"{work_order['repository']}\0{work_order['pull_request']}\0"
            f"{work_order['candidate_commit']}\0{work_order['candidate_fingerprint']}\0"
            f"{round_number}"
        ).encode()
    ).hexdigest()
    expected_checkpoint = {
        "identity_key": identity_key,
        "goal_id": work_order["goal_id"],
        "repository": work_order["repository"],
        "issue": work_order["issue"],
        "pull_request": work_order["pull_request"],
        "candidate_commit": work_order["candidate_commit"],
        "candidate_fingerprint": work_order["candidate_fingerprint"],
        "review_round": round_number,
        "review_round_limit": work_order["review_round_limit"],
        "program_id": work_order["program_id"],
        "review_scope": work_order["review_scope"],
    }
    mismatches = [
        field for field, expected in expected_checkpoint.items()
        if reviewer_checkpoint.get(field) != expected
    ]
    if mismatches:
        raise IngestionError(
            "reviewer checkpoint/work-order mismatch: " + ", ".join(sorted(mismatches))
        )
    trusted = config.get("trusted_reviewer_identities")
    if (
        not isinstance(trusted, list) or len(trusted) != 1
        or not isinstance(trusted[0], str) or not trusted[0]
    ):
        raise IngestionError("adapter bridge requires exactly one trusted reviewer identity")
    status = reviewer_checkpoint.get("status")
    if status in {"COMPLETED", "ALREADY_COMPLETED"}:
        review = reviewer_checkpoint.get("review_result")
        if not isinstance(review, dict):
            raise IngestionError("completed reviewer checkpoint has no structured review result")
        evidence = reviewer_checkpoint.get("execution_evidence")
        if not isinstance(evidence, dict) or evidence.get("effective_status") != "EFFECTIVE_CONFIRMED":
            raise IngestionError("completed reviewer checkpoint lacks confirmed model identity")
        event_status = "REVIEW_SUBMITTED"
    elif status == "FAILED_CLOSED":
        review = None
        event_status = {
            "timeout": "TIMEOUT",
            "quota_exhausted": "QUOTA_EXHAUSTED",
            "provider_authentication_failure": "PROVIDER_FAILURE",
            "schema_provider_interface_admission_failure": "PROVIDER_FAILURE",
        }.get(str(reviewer_checkpoint.get("reason")), "CRASHED")
    else:
        raise IngestionError("reviewer checkpoint is not terminal")
    event: dict[str, Any] = {
        "event_id": f"claude-reviewer-{identity_key}",
        "status": event_status,
        "repository": work_order["repository"],
        "issue": work_order["issue"],
        "pull_request": work_order["pull_request"],
        "program_id": work_order["program_id"],
        "goal_id": work_order["goal_id"],
        "candidate_commit": work_order["candidate_commit"],
        "candidate_fingerprint": work_order["candidate_fingerprint"],
        "review_round": round_number,
        "cumulative_round_limit": work_order["review_round_limit"],
        "reviewer_identity": trusted[0],
        "review_scope": work_order["review_scope"],
    }
    if review is not None:
        event["review"] = review
    return event


def ingest(*, event: dict[str, Any], config: dict[str, Any], schema: dict[str, Any], checkpoint_path: Path) -> dict[str, Any]:
    required = {
        "event_id", "status", "repository", "issue", "pull_request", "program_id",
        "goal_id", "candidate_commit", "candidate_fingerprint", "review_round",
        "cumulative_round_limit", "reviewer_identity", "review_scope",
    }
    missing = sorted(required - event.keys())
    if missing:
        raise IngestionError(f"missing event fields: {missing}")
    if event["status"] in TERMINAL_FAILURES:
        checkpoint = {
            "schema_version": "kgnote.claude-review-ingestion.v1",
            "status": "FAILED_CLOSED",
            "reason": event["status"],
            "event_id": event["event_id"],
            "candidate_commit": event["candidate_commit"],
            "candidate_fingerprint": event["candidate_fingerprint"],
            "review_round": event["review_round"],
            "cumulative_round_limit": event["cumulative_round_limit"],
            "product_review_accepted": False,
        }
        _atomic(checkpoint_path, checkpoint)
        return checkpoint
    if event["status"] != "REVIEW_SUBMITTED" or not isinstance(event.get("review"), dict):
        raise IngestionError("non-failure event must contain one REVIEW_SUBMITTED review")
    trusted_identities = config.get("trusted_reviewer_identities")
    if not isinstance(trusted_identities, list) or event["reviewer_identity"] not in trusted_identities:
        raise IngestionError("reviewer identity is not allow-listed")
    if not 1 <= event["review_round"] <= event["cumulative_round_limit"]:
        raise IngestionError("review round is outside the cumulative budget")
    previous: dict[str, Any] = {}
    if checkpoint_path.exists():
        try:
            previous = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngestionError("existing checkpoint is unreadable") from exc
    digest = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if previous.get("event_digest") == digest:
        if previous.get("product_review_accepted") is True and isinstance(previous.get("canonical_record"), dict):
            return {**previous, "status": "ALREADY_CONSUMED"}
        return previous
    if previous.get("event_id") == event["event_id"]:
        raise IngestionError("event ID was reused with different bytes")
    if isinstance(previous.get("review_round"), int) and event["review_round"] < previous["review_round"]:
        raise IngestionError("review round regressed across resume")
    authorized_scope = _configured_product_contract_scope(config)
    if event["review_scope"] != authorized_scope:
        checkpoint = {
            "schema_version": "kgnote.claude-review-ingestion.v1",
            "status": "CODE_REVIEW_ONLY",
            "event_id": event["event_id"],
            "event_digest": digest,
            "candidate_commit": event["candidate_commit"],
            "candidate_fingerprint": event["candidate_fingerprint"],
            "review_round": event["review_round"],
            "cumulative_round_limit": event["cumulative_round_limit"],
            "reviewer_identity": event["reviewer_identity"],
            "review_scope": event["review_scope"],
            "product_review_accepted": False,
        }
        _atomic(checkpoint_path, checkpoint)
        return checkpoint
    result = dict(event["review"])
    identity_fields = {
        "protocol": "kgnote.product-review.v1",
        "repository": event["repository"],
        "pull_request": event["pull_request"],
        "program_id": event["program_id"],
        "goal_id": event["goal_id"],
        "candidate_fingerprint": event["candidate_fingerprint"],
        "candidate_commit": event["candidate_commit"],
        "review_round": event["review_round"],
    }
    for field, expected in identity_fields.items():
        if field in result and result[field] != expected:
            raise IngestionError(f"review identity mismatch: {field}")
        result[field] = expected
    marker = config["result_marker"]
    # This is only a deterministic contract check.  A locally synthesized record
    # is not a GitHub artifact and its round number is not a GitHub record ID.
    record = {
        "source": "issue_comment",
        "author_login": config["trusted_reviewer_author_login"],
        "record_id": 1,
        "body": (
            f"<!-- {marker} reviewed_head_sha={event['candidate_commit']} -->\n"
            f"```json\n{json.dumps(result, ensure_ascii=False)}\n```"
        ),
    }
    identity = CandidateIdentity(
        event["repository"], event["pull_request"], event["program_id"], event["goal_id"],
        event["candidate_fingerprint"], event["candidate_commit"], event["review_round"],
    )
    try:
        decision = consume_records(config=config, schema=schema, identity=identity, records=[record])
    except ConsumerInputError as exc:
        raise IngestionError(f"KGnote Consumer rejected input: {exc}") from exc
    if not decision.get("accepted"):
        raise IngestionError(f"KGnote Consumer rejected review: {decision.get('reason') or decision.get('rejected')}")
    checkpoint = {
        "schema_version": "kgnote.claude-review-ingestion.v1",
        "status": "VALIDATED_PENDING_GITHUB_WRITEBACK",
        "event_id": event["event_id"],
        "event_digest": digest,
        "candidate_commit": event["candidate_commit"],
        "candidate_fingerprint": event["candidate_fingerprint"],
        "review_round": event["review_round"],
        "cumulative_round_limit": event["cumulative_round_limit"],
        "reviewer_identity": event["reviewer_identity"],
        "review_scope": event["review_scope"],
        "finding_count": decision.get("finding_count", len(decision.get("findings", []))),
        "findings": decision.get("findings", []),
        "validated_verdict": decision["status"],
        "product_review_accepted": False,
        "canonical_record": None,
    }
    _atomic(checkpoint_path, checkpoint)
    return checkpoint


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IngestionError(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event", type=Path)
    source.add_argument("--reviewer-checkpoint", type=Path)
    parser.add_argument("--work-order", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--github-writeback", action="store_true")
    parser.add_argument("--cwd", type=Path)
    args = parser.parse_args()
    try:
        config = _read_json(args.config)
        if args.event is not None:
            if args.work_order is not None:
                raise IngestionError("--work-order is valid only with --reviewer-checkpoint")
            event = _read_json(args.event)
        else:
            if args.work_order is None:
                raise IngestionError("--reviewer-checkpoint requires --work-order")
            event = event_from_adapter_checkpoint(
                reviewer_checkpoint=_read_json(args.reviewer_checkpoint),
                work_order=_read_json(args.work_order),
                config=config,
            )
        values = {
            "event": event, "config": config,
            "schema": _read_json(args.schema), "checkpoint_path": args.checkpoint,
        }
        result = (publish_validated_review(
            **values, cwd=(args.cwd or Path.cwd())
        ) if args.github_writeback else ingest(**values))
    except (OSError, json.JSONDecodeError, IngestionError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
