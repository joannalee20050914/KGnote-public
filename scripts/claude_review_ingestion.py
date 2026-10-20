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
    if event["review_scope"] != "KGNOTE_PRODUCT_CONTRACT":
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
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--github-writeback", action="store_true")
    parser.add_argument("--cwd", type=Path)
    args = parser.parse_args()
    try:
        values = {
            "event": _read_json(args.event), "config": _read_json(args.config),
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
