#!/usr/bin/env python3
"""Fail-closed consumer for KGnote GitHub product-review results.

The transport adapter is intentionally outside this module. Callers fetch PR reviews
and top-level PR comments, normalize them to the record shape accepted here, and pass
the records to ``consume_records``. This keeps parsing and trust decisions deterministic
and independently testable without network access or credentials.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


SUPPORTED_PROTOCOL = "kgnote.product-review.v1"
SUPPORTED_SOURCES = {"pull_request_review", "issue_comment"}
FORMAL_STATE_BY_VERDICT = {
    "PASS": "COMMENTED",
    "CHANGES_REQUIRED": "COMMENTED",
    "PRODUCT_DECISION_REQUIRED": "COMMENTED",
}
JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class CandidateIdentity:
    repository: str
    pull_request: int
    program_id: str
    goal_id: str
    candidate_fingerprint: str
    candidate_commit: str
    review_round: int


class ConsumerInputError(ValueError):
    """Raised when caller-provided config or record data is malformed."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConsumerInputError(f"cannot read JSON from {path}: {exc}") from exc


def _result_marker(config: dict[str, Any]) -> str:
    marker = config.get("result_marker")
    if not isinstance(marker, str) or not marker:
        raise ConsumerInputError("config.result_marker must be a non-empty string")
    return marker


def _trusted_author(config: dict[str, Any]) -> str | None:
    author = config.get("trusted_reviewer_author_login")
    if author is not None and (not isinstance(author, str) or not author):
        raise ConsumerInputError(
            "config.trusted_reviewer_author_login must be null or a non-empty string"
        )
    return author


def _validate_record_shape(record: Any, index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ConsumerInputError(f"records[{index}] must be an object")
    for field in ("source", "author_login", "body"):
        if not isinstance(record.get(field), str):
            raise ConsumerInputError(f"records[{index}].{field} must be a string")
    if record["source"] not in SUPPORTED_SOURCES:
        raise ConsumerInputError(
            f"records[{index}].source must be one of {sorted(SUPPORTED_SOURCES)}"
        )
    if record["source"] == "pull_request_review" and not isinstance(
        record.get("review_state"), str
    ):
        raise ConsumerInputError(
            f"records[{index}].review_state is required for pull_request_review"
        )
    return record


def _parse_one_result(
    body: str, marker: str, candidate_commit: str
) -> tuple[dict[str, Any] | None, str | None]:
    marker_re = re.compile(
        rf"<!--\s*{re.escape(marker)}\s+reviewed_head_sha=([0-9a-f]{{40}})\s*-->"
    )
    markers = marker_re.findall(body)
    if not markers:
        return None, "missing_result_marker"
    if len(markers) != 1:
        return None, "expected_exactly_one_result_marker"
    if markers[0] != candidate_commit:
        return None, "result_marker_commit_mismatch"
    matches = JSON_FENCE_RE.findall(body)
    if len(matches) != 1:
        return None, "expected_exactly_one_fenced_json_object"
    try:
        result = json.loads(matches[0])
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(result, dict):
        return None, "result_must_be_object"
    return result, None


def _identity_mismatches(
    result: dict[str, Any], identity: CandidateIdentity
) -> list[str]:
    expected = {
        "protocol": SUPPORTED_PROTOCOL,
        "repository": identity.repository,
        "pull_request": identity.pull_request,
        "program_id": identity.program_id,
        "goal_id": identity.goal_id,
        "candidate_fingerprint": identity.candidate_fingerprint,
        "candidate_commit": identity.candidate_commit,
        "review_round": identity.review_round,
    }
    return [field for field, value in expected.items() if result.get(field) != value]


def consume_records(
    *,
    config: dict[str, Any],
    schema: dict[str, Any],
    identity: CandidateIdentity,
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Return one fail-closed decision for the exact current candidate.

    No record is trusted unless the repository transport is enabled and the observed
    author allowlist has been configured. Rejected records are summarized without
    echoing their untrusted bodies.
    """

    if config.get("enabled") is not True:
        return {
            "status": "DISABLED",
            "accepted": False,
            "reason": "github_work reviewer transport is disabled",
        }

    trusted_author = _trusted_author(config)
    if trusted_author is None:
        return {
            "status": "AUTOMATION_BLOCKED",
            "accepted": False,
            "reason": "trusted reviewer author login has not been observed and configured",
        }

    if config.get("last_reviewed_candidate_fingerprint") == identity.candidate_fingerprint:
        return {
            "status": "ALREADY_CONSUMED",
            "accepted": False,
            "reason": "candidate fingerprint matches the last completed review fingerprint",
        }

    marker = _result_marker(config)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ConsumerInputError(f"invalid result schema: {exc}") from exc
    validator = Draft202012Validator(schema)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for index, raw_record in enumerate(records):
        record = _validate_record_shape(raw_record, index)
        rejection: dict[str, Any] = {"index": index}

        if record["author_login"] != trusted_author:
            rejection["reason"] = "untrusted_author"
            rejected.append(rejection)
            continue

        result, parse_error = _parse_one_result(
            record["body"], marker, identity.candidate_commit
        )
        if parse_error:
            rejection["reason"] = parse_error
            rejected.append(rejection)
            continue
        assert result is not None

        schema_errors = sorted(
            validator.iter_errors(result), key=lambda error: list(error.absolute_path)
        )
        if schema_errors:
            rejection["reason"] = "schema_invalid"
            rejection["schema_error_count"] = len(schema_errors)
            rejected.append(rejection)
            continue

        mismatches = _identity_mismatches(result, identity)
        if mismatches:
            rejection["reason"] = "candidate_identity_mismatch"
            rejection["fields"] = mismatches
            rejected.append(rejection)
            continue

        if record["source"] == "pull_request_review":
            expected_state = FORMAL_STATE_BY_VERDICT[result["verdict"]]
            if record["review_state"].upper() != expected_state:
                rejection["reason"] = "formal_review_state_mismatch"
                rejected.append(rejection)
                continue

        accepted.append(
            {
                "index": index,
                "source": record["source"],
                "author_login": record["author_login"],
                "record_id": record.get("record_id"),
                "result": result,
            }
        )

    if not accepted:
        return {
            "status": "WAITING_FOR_PRODUCT_REVIEW",
            "accepted": False,
            "candidate_fingerprint": identity.candidate_fingerprint,
            "rejected": rejected,
        }
    if len(accepted) > 1:
        return {
            "status": "AUTOMATION_BLOCKED",
            "accepted": False,
            "reason": "multiple trusted results match the exact candidate",
            "matching_record_count": len(accepted),
            "rejected": rejected,
        }

    match = accepted[0]
    result = match["result"]
    return {
        "status": result["verdict"],
        "accepted": True,
        "program_id": result["program_id"],
        "goal_id": result["goal_id"],
        "candidate_fingerprint": result["candidate_fingerprint"],
        "candidate_commit": result["candidate_commit"],
        "review_round": result["review_round"],
        "review_author": match["author_login"],
        "review_source": match["source"],
        "record_id": match["record_id"],
        "verdict": result["verdict"],
        "finding_count": len(result["findings"]),
        "findings": result["findings"],
        "native_ui_observed": result["native_ui_observed"],
        "rejected": rejected,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consume normalized GitHub PR review/comment records fail-closed."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pull-request", type=int, required=True)
    parser.add_argument("--goal-id", required=True)
    parser.add_argument("--candidate-fingerprint", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--review-round", type=int, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        config = _load_json(args.config)
        schema = _load_json(args.schema)
        records = _load_json(args.records)
        if not isinstance(config, dict) or not isinstance(schema, dict):
            raise ConsumerInputError("config and schema roots must be objects")
        if not isinstance(records, list):
            raise ConsumerInputError("records root must be an array")
        decision = consume_records(
            config=config,
            schema=schema,
            identity=CandidateIdentity(
                repository=args.repository,
                pull_request=args.pull_request,
                program_id=args.program_id,
                goal_id=args.goal_id,
                candidate_fingerprint=args.candidate_fingerprint,
                candidate_commit=args.candidate_commit,
                review_round=args.review_round,
            ),
            records=records,
        )
    except ConsumerInputError as exc:
        print(json.dumps({"status": "INPUT_ERROR", "accepted": False, "reason": str(exc)}))
        return 2

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
