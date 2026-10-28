#!/usr/bin/env python3
"""Append exact corrections for the two preserved O2 misclassifications.

This is a one-purpose deployment reconciliation.  It verifies the paused
formal state, hash-chained ledger, original checkpoints, and immutable Ubuntu
raw logs before appending correction events.  Existing events and launch or
attempt counters are never rewritten or reset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import goal_continuity
from github_product_review_consumer import CandidateIdentity, ConsumerInputError, consume_records


BASELINE_STATE_SHA256 = "b2f2e37c3e15ba9733f07ea31f4b27276da7f69aa1434f07a7ee658d72cf446d"
BASELINE_LEDGER_SHA256 = "19515c795f59e10cdcfacdb3dad47f06c9c526548c2ba7aa13a04de1b0c21415"
REMOTE_RAW_ROOT = Path("/home/kgnote/.local/share/kgnote/runtime-state/product-goal/raw")
WORK_ITEM_ID = "WI-O2-A-IMPLEMENT"
REVIEW_REPOSITORY = "joannalee20050914/KGnote-public"
REVIEW_PULL_REQUEST = 36
REVIEW_GOAL_ID = "CODEX-APP-GOAL-O2-RUNTIME-CONTEXT-RECOVERY-20261028"
REVIEW_PROGRAM_ID = "program-kgnote-o2-runtime-context-recovery-20261028"
REVIEWER_IDENTITY = "claude-code:ubuntu-review-only"
TRUSTED_GITHUB_AUTHOR = "joannalee20050914"
REVIEW_RESULT_MARKER = "kgnote-ai-product-review:v1"
REVIEW_SCHEMA = Path("schemas/product-review/v1/review-result.schema.json")
REVIEW_SCOPE = (
    "Bounded O2 runtime-context recovery: sealed Runner-verified authority/work/candidate/ledger "
    "context; pre-model exact Ubuntu checkout and pinned Python/Node/npm/gh/Codex/dependencies; "
    "structured Codex JSONL-only provider-failure classification; append-only exact-evidence "
    "reconciliation of two historical attempts; preserve PAUSE/BLOCKED/go_live_authorized=false, "
    "attempts/model launches=2, no RESUME or third dispatch, and all human/release gates."
)

ATTEMPTS = (
    {
        "attempt_id": "attempt-2026-10-23.2-s0-s2-proposal-WI-O2-A-IMPLEMENT-1",
        "event_id": "o2-wi-o2-a-implement-codex-c7ebf68b7d1eb5a7",
        "checkpoint_sha256": "b187de690f7ef21e7b9a4ef3abf0611a8c6d6d356f12767c70d91fe5a2275e69",
        "stdout_sha256": "f13ed7ff260f6831a8213c8e78c24487fe36e258896bb803e24d6de8f9c585c8",
        "stderr_sha256": "2553a8bf52c98f2355a18f98559cb6b57c44e6b3465363a2718ae259972c819a",
        "cause_codes": ["STALE_REPOSITORY_AUTHORITY_CONTEXT"],
    },
    {
        "attempt_id": "attempt-2026-10-23.2-s0-s2-proposal-WI-O2-A-IMPLEMENT-2",
        "event_id": "o2-wi-o2-a-implement-codex-34ce7891c1d73523",
        "checkpoint_sha256": "bac13415d172a25379373630fd1e7e2a95e6b8b7116d986ef602550d63c2c95b",
        "stdout_sha256": "e8907c1ceb6356f39201670b5a4f36e5554811307dfa6a056a67ec9100a4480e",
        "stderr_sha256": "07bbe6238bc68a1ae1b3a73507b7fde8dde01b407cf7f90129822f0ef51968bb",
        "cause_codes": [
            "STALE_REPOSITORY_AUTHORITY_CONTEXT",
            "WORKER_DEVELOPMENT_ENVIRONMENT_INCOMPLETE",
        ],
    },
)


class ClassificationReconciliationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_patch(state: dict[str, Any]) -> dict[str, Any]:
    mutable = (
        "milestone_id", "lifecycle", "authority_lease", "authority_record",
        "work_items", "obligations", "go_live_authorized", "dependency_receipts",
        "candidate_identity", "resource_accounting",
    )
    return {key: deepcopy(state[key]) for key in mutable if key in state} | {
        "runtime_block": deepcopy(state.get("runtime_block")),
    }


def _github_record(repository: str, record_id: int) -> dict[str, Any]:
    completed = subprocess.run(
        ["gh", "api", f"repos/{repository}/issues/comments/{record_id}"],
        text=True, capture_output=True, timeout=30, check=False,
    )
    if completed.returncode:
        raise ClassificationReconciliationError("canonical GitHub review read-back failed")
    try:
        record = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ClassificationReconciliationError("canonical GitHub review is not valid JSON") from exc
    if not isinstance(record, dict):
        raise ClassificationReconciliationError("canonical GitHub review is not an object")
    return record


def _git_text(checkout: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", str(checkout), *arguments],
        text=True, capture_output=True, timeout=30, check=False,
    )
    if completed.returncode:
        raise ClassificationReconciliationError("deployed checkout identity read-back failed")
    return completed.stdout.strip()


def _validated_deployment_identity(
    checkout: Path, *, reviewed_commit: str, reviewed_tree: str,
) -> dict[str, str]:
    deployed_commit = _git_text(checkout, "rev-parse", "HEAD")
    deployed_tree = _git_text(checkout, "rev-parse", "HEAD^{tree}")
    candidate_tree = _git_text(checkout, "rev-parse", f"{reviewed_commit}^{{tree}}")
    if (
        len(deployed_commit) != 40
        or any(character not in "0123456789abcdef" for character in deployed_commit)
        or candidate_tree != reviewed_tree
        or deployed_tree != reviewed_tree
    ):
        raise ClassificationReconciliationError(
            "deployed Runner tree differs from the exact reviewed candidate tree"
        )
    return {
        "deployed_commit": deployed_commit,
        "deployed_tree": deployed_tree,
        "reviewed_commit": reviewed_commit,
        "reviewed_tree": reviewed_tree,
    }


def _validated_review_pass(
    *, consumer_checkpoint: Path, work_order_path: Path, deployed_checkout: Path,
    github_record_reader: Callable[[str, int], dict[str, Any]] = _github_record,
    deployment_identity_reader: Callable[..., dict[str, str]] = _validated_deployment_identity,
) -> dict[str, Any]:
    if not consumer_checkpoint.is_file() or not work_order_path.is_file():
        raise ClassificationReconciliationError("exact canonical review evidence is absent")
    checkpoint = goal_continuity.load_json(consumer_checkpoint)
    work_order = goal_continuity.load_json(work_order_path)
    candidate_commit = work_order.get("candidate_commit")
    candidate_fingerprint = work_order.get("candidate_fingerprint")
    candidate_tree = work_order.get("candidate_tree")
    review_id = work_order.get("review_id")
    round_used = work_order.get("review_round_used")
    round_limit = work_order.get("review_round_limit")
    if (
        work_order.get("goal_id") != REVIEW_GOAL_ID
        or work_order.get("repository") != REVIEW_REPOSITORY
        or work_order.get("pull_request") != REVIEW_PULL_REQUEST
        or work_order.get("program_id") != REVIEW_PROGRAM_ID
        or not isinstance(review_id, str)
        or not review_id.startswith("review-o2-runtime-context-recovery-20261028-")
        or not isinstance(candidate_commit, str)
        or len(candidate_commit) != 40
        or any(character not in "0123456789abcdef" for character in candidate_commit)
        or not isinstance(candidate_fingerprint, str)
        or len(candidate_fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in candidate_fingerprint)
        or not isinstance(candidate_tree, str)
        or len(candidate_tree) != 40
        or any(character not in "0123456789abcdef" for character in candidate_tree)
        or isinstance(round_used, bool)
        or not isinstance(round_used, int)
        or isinstance(round_limit, bool)
        or not isinstance(round_limit, int)
        or not 0 <= round_used < round_limit
        or work_order.get("review_scope") != REVIEW_SCOPE
    ):
        raise ClassificationReconciliationError("review work order identity is not exact")
    review_round = round_used + 1
    identity_key = hashlib.sha256(
        (
            f"{REVIEW_REPOSITORY}\0{REVIEW_PULL_REQUEST}\0{candidate_commit}\0"
            f"{candidate_fingerprint}\0{review_round}"
        ).encode()
    ).hexdigest()
    canonical = checkpoint.get("canonical_record")
    if (
        checkpoint.get("schema_version") != "kgnote.claude-review-ingestion.v1"
        or checkpoint.get("status") != "PASS"
        or checkpoint.get("validated_verdict") != "PASS"
        or checkpoint.get("product_review_accepted") is not True
        or checkpoint.get("event_id") != f"claude-reviewer-{identity_key}"
        or checkpoint.get("candidate_commit") != candidate_commit
        or checkpoint.get("candidate_fingerprint") != candidate_fingerprint
        or checkpoint.get("review_round") != review_round
        or checkpoint.get("reviewer_identity") != REVIEWER_IDENTITY
        or checkpoint.get("review_scope") != work_order["review_scope"]
        or not isinstance(canonical, dict)
        or canonical.get("repository") != REVIEW_REPOSITORY
        or canonical.get("pull_request") != REVIEW_PULL_REQUEST
        or canonical.get("candidate_commit") != candidate_commit
        or canonical.get("candidate_fingerprint") != candidate_fingerprint
        or canonical.get("reviewer_identity") != REVIEWER_IDENTITY
        or canonical.get("publisher_identity") != TRUSTED_GITHUB_AUTHOR
        or canonical.get("source") != "issue_comment"
        or isinstance(canonical.get("record_id"), bool)
        or not isinstance(canonical.get("record_id"), int)
        or canonical["record_id"] <= 0
    ):
        raise ClassificationReconciliationError("canonical review checkpoint is not an exact PASS")
    record = github_record_reader(REVIEW_REPOSITORY, canonical["record_id"])
    body = record.get("body")
    if (
        not isinstance(body, str)
        or (record.get("user") or {}).get("login") != TRUSTED_GITHUB_AUTHOR
        or record.get("html_url") != canonical.get("artifact_url")
        or record.get("created_at") != canonical.get("submitted_at")
        or hashlib.sha256(body.encode()).hexdigest() != canonical.get("original_body_sha256")
    ):
        raise ClassificationReconciliationError("canonical GitHub review metadata differs")
    schema = goal_continuity.load_json(deployed_checkout / REVIEW_SCHEMA)
    identity = CandidateIdentity(
        REVIEW_REPOSITORY, REVIEW_PULL_REQUEST, REVIEW_PROGRAM_ID, REVIEW_GOAL_ID,
        candidate_fingerprint, candidate_commit, review_round,
    )
    try:
        decision = consume_records(
            config={
                "enabled": True,
                "result_marker": REVIEW_RESULT_MARKER,
                "trusted_reviewer_author_login": TRUSTED_GITHUB_AUTHOR,
                "last_reviewed_candidate_fingerprint": None,
            },
            schema=schema,
            identity=identity,
            records=[{
                "source": "issue_comment",
                "author_login": TRUSTED_GITHUB_AUTHOR,
                "record_id": canonical["record_id"],
                "body": body,
            }],
        )
    except ConsumerInputError as exc:
        raise ClassificationReconciliationError("canonical Consumer review is invalid") from exc
    if (
        decision.get("accepted") is not True
        or decision.get("verdict") != "PASS"
        or decision.get("record_id") != canonical["record_id"]
        or decision.get("human_decisions") != []
    ):
        raise ClassificationReconciliationError("canonical GitHub review is not an exact PASS")
    deployment = deployment_identity_reader(
        deployed_checkout,
        reviewed_commit=candidate_commit,
        reviewed_tree=candidate_tree,
    )
    if (
        not isinstance(deployment, dict)
        or deployment.get("reviewed_commit") != candidate_commit
        or deployment.get("reviewed_tree") != candidate_tree
        or deployment.get("deployed_tree") != candidate_tree
        or not isinstance(deployment.get("deployed_commit"), str)
        or len(deployment["deployed_commit"]) != 40
        or any(character not in "0123456789abcdef" for character in deployment["deployed_commit"])
    ):
        raise ClassificationReconciliationError(
            "deployed Runner tree differs from the exact reviewed candidate tree"
        )
    return {
        "review_id": review_id,
        "reviewed_revision": f"{candidate_commit}+worktree:{candidate_fingerprint}",
        "reviewed_fingerprint": candidate_fingerprint,
        "reviewed_commit": candidate_commit,
        "reviewed_tree": candidate_tree,
        "review_round": review_round,
        "consumer_checkpoint_sha256": _sha256(consumer_checkpoint),
        "review_work_order_sha256": _sha256(work_order_path),
        "canonical_record": canonical,
        "deployment": deployment,
    }


def _remote_hashes(host: str, paths: list[Path]) -> dict[str, str]:
    completed = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes",
            host, "/usr/bin/sha256sum", *(str(path) for path in paths),
        ],
        text=True, capture_output=True, timeout=30, check=False,
    )
    if completed.returncode:
        raise ClassificationReconciliationError("Ubuntu raw-log hash read-back failed")
    values: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2:
            values[fields[1].strip()] = fields[0]
    return values


def _validate_paused_state(spec: dict[str, Any], state: dict[str, Any]) -> None:
    goal_continuity.validate_runner_state(state, spec)
    if (
        state["lifecycle"]["state"] != "BLOCKED"
        or state["authority_lease"] != "PAUSED"
        or state["go_live_authorized"] is not False
        or state.get("authority_record", {}).get("action") != "PAUSE"
        or str(state.get("authority_record", {}).get("comment_id")) != "6458880366"
    ):
        raise ClassificationReconciliationError("formal O2 PAUSE is not exact")
    work = next((row for row in state["work_items"] if row["work_item_id"] == WORK_ITEM_ID), None)
    if not isinstance(work, dict) or work.get("attempts") != 2 or work.get("active_attempt_id") is not None:
        raise ClassificationReconciliationError("Work Item A attempt accounting differs from two settled attempts")
    accounting = state.get("resource_accounting", {}).get("codex", {})
    if accounting.get("total_launches") != 2:
        raise ClassificationReconciliationError("Codex launch accounting differs from two preserved launches")


def _validate_evidence(
    checkpoint_root: Path, remote: dict[str, str], ledger: list[dict[str, Any]],
) -> None:
    events = {row["event_id"]: row for row in ledger}
    for item in ATTEMPTS:
        checkpoint = checkpoint_root / f"{item['event_id']}.json"
        if not checkpoint.is_file() or _sha256(checkpoint) != item["checkpoint_sha256"]:
            raise ClassificationReconciliationError("original Ubuntu checkpoint digest differs")
        value = json.loads(checkpoint.read_text(encoding="utf-8"))
        result = value.get("execution_evidence", {}).get("product_goal_result", {})
        execution = result.get("execution", {})
        if (
            value.get("event_id") != item["event_id"]
            or result.get("attempt_id") != item["attempt_id"]
            or result.get("failure_class") != "RATE_LIMITED"
            or execution.get("stdout_sha256") != item["stdout_sha256"]
            or execution.get("stderr_sha256") != item["stderr_sha256"]
        ):
            raise ClassificationReconciliationError("original checkpoint result identity differs")
        finished = events.get(f"{item['attempt_id']}-finished")
        if not isinstance(finished, dict) or finished.get("payload", {}).get("failure_class") != "RATE_LIMITED":
            raise ClassificationReconciliationError("original RATE_LIMITED ledger event is absent")
        for suffix in ("stdout", "stderr"):
            path = REMOTE_RAW_ROOT / f"{item['event_id']}.{suffix}.log"
            if remote.get(str(path)) != item[f"{suffix}_sha256"]:
                raise ClassificationReconciliationError("immutable Ubuntu raw-log digest differs")


def reconcile(
    *, spec_path: Path, state_path: Path, ledger_path: Path,
    checkpoint_root: Path, remote_host: str, deployed_checkout: Path,
    review_consumer_checkpoint: Path, review_work_order: Path,
    receipt_path: Path, occurred_at: str,
    remote_hash_reader: Callable[[str, list[Path]], dict[str, str]] = _remote_hashes,
    github_record_reader: Callable[[str, int], dict[str, Any]] = _github_record,
    deployment_identity_reader: Callable[..., dict[str, str]] = _validated_deployment_identity,
) -> dict[str, Any]:
    try:
        observed = datetime.fromisoformat(occurred_at)
    except ValueError as exc:
        raise ClassificationReconciliationError("occurred_at is invalid") from exc
    if observed.tzinfo is None:
        raise ClassificationReconciliationError("occurred_at must be timezone-aware")
    review_result = _validated_review_pass(
        consumer_checkpoint=review_consumer_checkpoint,
        work_order_path=review_work_order,
        deployed_checkout=deployed_checkout,
        github_record_reader=github_record_reader,
        deployment_identity_reader=deployment_identity_reader,
    )
    spec = goal_continuity.load_json(spec_path)
    state = goal_continuity.load_json(state_path)
    ledger = goal_continuity.read_ledger(ledger_path)
    _validate_paused_state(spec, state)
    goal_continuity.validate_ledger_binding(ledger, state, spec)
    correction_ids = {
        f"{item['attempt_id']}-classification-corrected-20261028" for item in ATTEMPTS
    }
    existing_ids = {row["event_id"] for row in ledger}
    if not (existing_ids & correction_ids):
        if _sha256(state_path) != BASELINE_STATE_SHA256 or _sha256(ledger_path) != BASELINE_LEDGER_SHA256:
            raise ClassificationReconciliationError("formal baseline changed before classification correction")
    remote_paths = [
        REMOTE_RAW_ROOT / f"{item['event_id']}.{suffix}.log"
        for item in ATTEMPTS for suffix in ("stdout", "stderr")
    ]
    _validate_evidence(checkpoint_root, remote_hash_reader(remote_host, remote_paths), ledger)

    original_attempts = next(
        row["attempts"] for row in state["work_items"] if row["work_item_id"] == WORK_ITEM_ID
    )
    original_launches = state["resource_accounting"]["codex"]["total_launches"]
    appended_events: list[dict[str, Any]] = []
    for index, item in enumerate(ATTEMPTS):
        event_id = f"{item['attempt_id']}-classification-corrected-20261028"
        ledger = goal_continuity.read_ledger(ledger_path)
        existing = next((row for row in ledger if row["event_id"] == event_id), None)
        if existing is not None:
            appended_events.append(existing)
            if state["event_cursor"]["sequence"] < existing["sequence"]:
                patch = existing["payload"].get("state_patch")
                if isinstance(patch, dict):
                    for key, value in patch.items():
                        if key == "runtime_block" and value is None:
                            state.pop(key, None)
                        else:
                            state[key] = deepcopy(value)
                state["event_cursor"] = {
                    "sequence": existing["sequence"],
                    "event_sha256": existing["event_sha256"],
                }
                goal_continuity.atomic_write_json(state_path, state)
            continue
        updated = deepcopy(state)
        if index == len(ATTEMPTS) - 1:
            updated.pop("runtime_block", None)
            updated["resource_accounting"]["codex"].pop("quota_retry_at", None)
        payload: dict[str, Any] = {
            "operation": "ATTEMPT_FAILURE_CLASSIFICATION_CORRECTED",
            "supersedes_event_id": f"{item['attempt_id']}-finished",
            "original_failure_class": "RATE_LIMITED",
            "corrected_failure_class": "CONTROL_PLANE_PREFLIGHT_FAILURE",
            "cause_codes": item["cause_codes"],
            "provider_error_evidence": {
                "status": "ABSENT_IN_PRESERVED_RAW_RESPONSE",
                "http_status": None,
                "provider_recovery_time": None,
            },
            "evidence": {
                "checkpoint_sha256": item["checkpoint_sha256"],
                "stdout_sha256": item["stdout_sha256"],
                "stderr_sha256": item["stderr_sha256"],
            },
            "review_id": review_result["review_id"],
            "review_round": review_result["review_round"],
            "reviewed_deployment_commit": review_result["deployment"]["deployed_commit"],
            "reviewed_candidate_commit": review_result["reviewed_commit"],
            "reviewed_candidate_tree": review_result["reviewed_tree"],
            "reviewed_candidate_revision": review_result["reviewed_revision"],
            "reviewed_candidate_fingerprint": review_result["reviewed_fingerprint"],
            "review_consumer_checkpoint_sha256": review_result["consumer_checkpoint_sha256"],
            "review_work_order_sha256": review_result["review_work_order_sha256"],
            "canonical_review_record": deepcopy(review_result["canonical_record"]),
        }
        if index == len(ATTEMPTS) - 1:
            payload["state_patch"] = _state_patch(updated)
        event, appended = goal_continuity.append_ledger_event(
            ledger_path, event_id=event_id, event_type="WORK_STATE_TRANSITION",
            occurred_at=occurred_at, goal_id=spec["goal_id"],
            goal_version=spec["goal_version"], logical_work_id=WORK_ITEM_ID,
            attempt_id=item["attempt_id"], payload=payload,
        )
        if not appended:
            raise ClassificationReconciliationError("classification correction replay conflicted")
        updated["event_cursor"] = {
            "sequence": event["sequence"], "event_sha256": event["event_sha256"],
        }
        goal_continuity.validate_runner_state(updated, spec)
        goal_continuity.atomic_write_json(state_path, updated)
        state = updated
        appended_events.append(event)

    state = goal_continuity.load_json(state_path)
    ledger = goal_continuity.read_ledger(ledger_path)
    _validate_paused_state(spec, state)
    goal_continuity.validate_ledger_binding(ledger, state, spec)
    projection = goal_continuity.reduce_ledger(ledger)
    if (
        set(projection["classification_corrections"]) != {item["attempt_id"] for item in ATTEMPTS}
        or next(row["attempts"] for row in state["work_items"] if row["work_item_id"] == WORK_ITEM_ID) != original_attempts
        or state["resource_accounting"]["codex"]["total_launches"] != original_launches
        or isinstance(state.get("runtime_block"), dict)
        or "quota_retry_at" in state["resource_accounting"]["codex"]
    ):
        raise ClassificationReconciliationError("post-correction read-back differs")
    receipt = {
        "schema_version": "kgnote.o2-classification-reconciliation-receipt.v1",
        "status": "PASS",
        "review_id": review_result["review_id"],
        "review_round": review_result["review_round"],
        "reviewed_deployment_commit": review_result["deployment"]["deployed_commit"],
        "reviewed_deployment_tree": review_result["deployment"]["deployed_tree"],
        "reviewed_candidate_commit": review_result["reviewed_commit"],
        "reviewed_candidate_tree": review_result["reviewed_tree"],
        "reviewed_candidate_revision": review_result["reviewed_revision"],
        "reviewed_candidate_fingerprint": review_result["reviewed_fingerprint"],
        "review_consumer_checkpoint_sha256": review_result["consumer_checkpoint_sha256"],
        "review_work_order_sha256": review_result["review_work_order_sha256"],
        "canonical_review_record": review_result["canonical_record"],
        "appended_event_ids": [row["event_id"] for row in appended_events],
        "event_cursor": state["event_cursor"],
        "state_sha256": _sha256(state_path),
        "ledger_sha256": _sha256(ledger_path),
        "lifecycle": state["lifecycle"]["state"],
        "authority_lease": state["authority_lease"],
        "go_live_authorized": state["go_live_authorized"],
        "work_item_attempts": original_attempts,
        "model_launches": original_launches,
        "third_attempt_created": False,
    }
    goal_continuity.atomic_write_json(receipt_path, receipt)
    if goal_continuity.load_json(receipt_path) != receipt:
        raise ClassificationReconciliationError("reconciliation receipt read-back differs")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--remote-host", default="kgnote-ubuntu")
    parser.add_argument("--deployed-checkout", type=Path, required=True)
    parser.add_argument("--review-consumer-checkpoint", type=Path, required=True)
    parser.add_argument("--review-work-order", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--occurred-at", required=True)
    args = parser.parse_args()
    try:
        receipt = reconcile(
            spec_path=args.spec, state_path=args.state, ledger_path=args.ledger,
            checkpoint_root=args.checkpoint_root, remote_host=args.remote_host,
            deployed_checkout=args.deployed_checkout,
            review_consumer_checkpoint=args.review_consumer_checkpoint,
            review_work_order=args.review_work_order, receipt_path=args.receipt,
            occurred_at=args.occurred_at,
        )
    except (OSError, json.JSONDecodeError, goal_continuity.GoalContractError, ClassificationReconciliationError) as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
