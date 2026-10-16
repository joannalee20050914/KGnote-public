#!/usr/bin/env python3
"""One bounded GitHub read/consume/update cycle for an external product review."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import external_review_control
import github_product_review_consumer as consumer


def _run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "GitHub command failed")
    return result.stdout


def _records(reviews: list[dict[str, Any]], comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"source": "pull_request_review", "author_login": row.get("user", {}).get("login", ""),
             "body": row.get("body") or "", "review_state": row.get("state") or "",
             "record_id": row.get("id"), "artifact_url": row.get("html_url")} for row in reviews]
    rows.extend({"source": "issue_comment", "author_login": row.get("user", {}).get("login", ""),
                 "body": row.get("body") or "", "record_id": row.get("id"),
                 "artifact_url": row.get("html_url")} for row in comments)
    return rows


def process(repo: Path, runner: Callable[..., str] | None = None) -> dict[str, Any]:
    runner = runner or _run
    config = external_review_control.load_json(repo / external_review_control.CONFIG_PATH)
    state = external_review_control.load_json(repo / external_review_control.STATE_PATH)
    blockers = external_review_control.publication_progression_blockers(config, state)
    if blockers:
        return {"status": "AUTOMATION_BLOCKED", "accepted": False, "errors": blockers}
    repository, pr = config["canonical_repository"], config["review_pr_number"]
    reviews = json.loads(runner(["gh", "api", f"repos/{repository}/pulls/{pr}/reviews", "--paginate"], cwd=repo))
    comments = json.loads(runner(["gh", "api", f"repos/{repository}/issues/{pr}/comments", "--paginate"], cwd=repo))
    records = _records(reviews, comments)
    identity = consumer.CandidateIdentity(repository, pr, config["program_id"], state["goal_id"],
        state["candidate_fingerprint"], state["candidate_commit"], state["review_round"])
    schema = external_review_control.load_json(repo / "schemas/product-review/v1/review-result.schema.json")
    decision = consumer.consume_records(config=config, schema=schema, identity=identity, records=records)
    if not decision.get("accepted"):
        return decision
    matching = next(row for row in records if row.get("record_id") == decision.get("record_id") and row["source"] == decision["review_source"])
    state["phase"] = "EXTERNAL_PRODUCT_REVIEW_ACCEPTED"
    state["external_review"] = {
        "status": decision["verdict"], "reviewed_commit": decision["candidate_commit"],
        "reviewed_fingerprint": decision["candidate_fingerprint"], "artifact_url": matching.get("artifact_url"),
        "review_author": decision["review_author"], "review_source": decision["review_source"],
        "record_id": decision["record_id"], "native_ui_observed": decision["native_ui_observed"],
        "blocking_findings": [item["id"] for item in decision["findings"]], "consumer_accepted": True,
    }
    if decision["verdict"] == "PASS":
        marker = (f"<!-- KGNOTE_ISSUE8_REVIEW_RECEIPT commit={state['candidate_commit']} "
                  f"fingerprint={state['candidate_fingerprint']} round={state['review_round']} -->")
        issue_path = f"repos/{repository}/issues/{config['delivery_issue_number']}/comments"
        issue_comments = json.loads(runner(["gh", "api", issue_path, "--paginate"], cwd=repo))
        matches = [row for row in issue_comments if marker in (row.get("body") or "")]
        if matches:
            issue_receipt = matches[-1]
        else:
            body = (marker + "\n\n外部獨立審查已由 Consumer（審查結果接收器）核對精確 PR、HEAD、Fingerprint 與 Round。\n\n"
                    f"- PR：#{pr}\n- HEAD：`{state['candidate_commit']}`\n- Fingerprint：`{state['candidate_fingerprint']}`\n"
                    f"- Round：{state['review_round']}\n- Review：{matching.get('artifact_url')}\n"
                    "- 限制：PR #23 尚未合併；跨工作階段自動喚醒與 Work 無人值守寫回仍未獨立證明。\n"
                    "- 回復：關閉未合併的 Draft PR 並將 Project 狀態移回 In Progress。\n"
                    "- PA-HUMAN-1、NS-HUMAN-SMOKE、release_verified=false 均未提升。")
            issue_receipt = json.loads(runner(["gh", "api", issue_path, "-f", f"body={body}"], cwd=repo))
        runner(["gh", "project", "item-edit", "--id", config["project_item_id"], "--project-id", config["project_id"],
                "--field-id", config["project_status_field_id"], "--single-select-option-id", config["project_review_option_id"]], cwd=repo)
        items = json.loads(runner(["gh", "project", "item-list", str(config["project_number"]), "--owner", config["project_owner"], "--format", "json", "--limit", "100"], cwd=repo))
        item = next((row for row in items.get("items", []) if row.get("id") == config["project_item_id"]), None)
        if not item or item.get("status") != "Review Queue":
            raise RuntimeError("Project read-back did not confirm Review Queue")
        state["delivery_receipt"] = {"status": "VERIFIED", "repository": repository, "pull_request": pr,
            "candidate_commit": state["candidate_commit"], "candidate_fingerprint": state["candidate_fingerprint"],
            "review_round": state["review_round"], "review_artifact_url": matching.get("artifact_url"),
            "issue": config["delivery_issue_number"], "issue_comment_url": issue_receipt.get("html_url"),
            "project_item_id": config["project_item_id"], "project_status": item.get("status"),
            "preserved_gates": ["PA-HUMAN-1", "NS-HUMAN-SMOKE", "release_verified=false"]}
    temporary = repo / ".ai/external-review-state.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, repo / external_review_control.STATE_PATH)
    return decision

