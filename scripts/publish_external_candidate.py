#!/usr/bin/env python3
"""Publish and read back one exact candidate on the canonical review PR."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

import codex_control
import external_review_control


class PublicationError(RuntimeError):
    pass


def validated_review_round(config: dict[str, Any], value: Any) -> int:
    maximum = config.get("max_product_review_rounds")
    if not isinstance(maximum, int) or maximum < 1:
        raise PublicationError("review round policy is missing or invalid")
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise PublicationError("review round is outside the configured authority envelope")
    return value


def resolve_pr_candidate(config: dict[str, Any], snapshot: dict[str, Any], recomputed_fingerprint: str) -> dict[str, Any]:
    pattern = re.compile(
        rf"<!--\s*{re.escape(config['request_marker'])}\s+candidate_commit=([0-9a-f]{{40}})\s+"
        rf"candidate_fingerprint=([0-9a-f]{{64}})\s+review_round=([1-9][0-9]*)\s*-->"
    )
    matches = pattern.findall(str(snapshot.get("body", "")))
    if len(matches) != 1:
        raise PublicationError("candidate resolver requires exactly one request marker")
    commit, fingerprint, review_round = matches[0]
    if commit != snapshot.get("headRefOid") or fingerprint != recomputed_fingerprint:
        raise PublicationError("candidate resolver identity mismatch")
    round_number = validated_review_round(config, int(review_round))
    return {"candidate_commit": commit, "candidate_fingerprint": fingerprint, "review_round": round_number}


def request_marker(config: dict[str, Any], state: dict[str, Any]) -> str:
    round_number = validated_review_round(config, state.get("review_round"))
    return (
        f"<!-- {config['request_marker']} candidate_commit={state['candidate_commit']} "
        f"candidate_fingerprint={state['candidate_fingerprint']} "
        f"review_round={round_number} -->"
    )


def review_trigger_comment(config: dict[str, Any], state: dict[str, Any]) -> str:
    template = config.get("trigger_comment_template")
    if template != "@kgnote-ai-review {candidate_commit}":
        raise PublicationError("exact review trigger comment template is missing")
    commit = state.get("candidate_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PublicationError("candidate commit is invalid for the review trigger")
    return template.format(candidate_commit=commit)


def without_request_markers(config: dict[str, Any], body: str) -> str:
    pattern = re.compile(
        rf"\n?<!--\s*{re.escape(config['request_marker'])}\s+candidate_commit=[0-9a-f]{{40}}\s+"
        rf"candidate_fingerprint=[0-9a-f]{{64}}\s+review_round=[1-9][0-9]*\s*-->\n?"
    )
    return pattern.sub("\n", body).rstrip()


def remote_snapshot_errors(
    config: dict[str, Any], state: dict[str, Any], snapshot: dict[str, Any]
) -> list[str]:
    errors = external_review_control.repository_authority_errors(config)
    expected = {
        "repository": config.get("canonical_repository"),
        "pull_request": config.get("review_pr_number"),
        "remote_head": state.get("candidate_commit"),
        "candidate_fingerprint": state.get("candidate_fingerprint"),
        "request_marker": config.get("request_marker"),
    }
    for field, value in expected.items():
        if snapshot.get(field) != value:
            errors.append(f"publication_readback: mismatch for {field}")
    if request_marker(config, state) not in str(snapshot.get("body", "")):
        errors.append("publication_readback: exact request marker is absent")
    if snapshot.get("state") != "OPEN":
        errors.append("publication_readback: canonical PR is not open")
    return errors


def _run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.returncode:
        raise PublicationError(f"command failed closed: {' '.join(command[:3])}: {completed.stderr.strip()}")
    # Preserve leading porcelain-status columns.  Removing leading whitespace
    # turns a tracked path such as `.ai/...` into `ai/...` on the first row and
    # can falsely classify orchestrator-owned mutable state as candidate bytes.
    return completed.stdout.rstrip("\r\n")


def publish(repo: Path, runner: Callable[..., str] | None = None) -> dict[str, Any]:
    runner = runner or _run
    config = external_review_control.load_json(repo / external_review_control.CONFIG_PATH)
    state = external_review_control.load_json(repo / external_review_control.STATE_PATH)
    authority = external_review_control.repository_authority_errors(config)
    if authority:
        raise PublicationError("; ".join(authority))
    head = runner(["git", "rev-parse", "HEAD"], cwd=repo)
    fingerprint = codex_control.repository_fingerprint(repo)["value"]
    status_rows = runner(["git", "status", "--porcelain"], cwd=repo).splitlines()
    mutable_exact = {
        ".ai/ORCHESTRATOR.lock", ".ai/ORCHESTRATOR_STATE.json", ".ai/REVIEW_REQUEST.md",
        ".ai/REVIEW_RESULT.md", ".ai/external-review-state.json", "CODEX_STATUS.md",
    }
    mutable_prefixes = (".ai/ORCHESTRATION_HISTORY/", ".ai/REVIEW_HISTORY/")
    unpublished = []
    for row in status_rows:
        path = row[3:].split(" -> ")[-1]
        if path not in mutable_exact and not path.startswith(mutable_prefixes):
            unpublished.append(path)
    if unpublished:
        raise PublicationError(
            "candidate contains unpublished files: " + ", ".join(sorted(unpublished))
        )
    if state.get("candidate_commit") != head or state.get("candidate_fingerprint") != fingerprint:
        raise PublicationError("local candidate identity is stale")
    origin = runner(["git", "remote", "get-url", "origin"], cwd=repo)
    if config["canonical_repository"] not in origin:
        raise PublicationError("origin is not the canonical repository")
    branch = runner(["git", "branch", "--show-current"], cwd=repo)
    pr_json = runner(
        ["gh", "pr", "view", str(config["review_pr_number"]), "--repo", config["canonical_repository"], "--json", "body"],
        cwd=repo,
    )
    body = json.loads(pr_json).get("body", "")
    marker = request_marker(config, state)
    if marker not in body:
        body_file = repo / ".git" / "kgnote-review-request-body.md"
        body_file.write_text(without_request_markers(config, body) + "\n\n" + marker + "\n", encoding="utf-8")
        try:
            runner(["gh", "pr", "edit", str(config["review_pr_number"]), "--repo", config["canonical_repository"], "--body-file", str(body_file)], cwd=repo)
        finally:
            body_file.unlink(missing_ok=True)
    runner(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo)
    observed = json.loads(runner(
        ["gh", "pr", "view", str(config["review_pr_number"]), "--repo", config["canonical_repository"], "--json", "headRefOid,body,state,url"],
        cwd=repo,
    ))
    resolve_pr_candidate(config, observed, fingerprint)
    snapshot = {
        "repository": config["canonical_repository"], "pull_request": config["review_pr_number"],
        "remote_head": observed.get("headRefOid"), "candidate_fingerprint": fingerprint,
        "request_marker": config["request_marker"], "body": observed.get("body"),
        "state": observed.get("state"), "artifact_url": observed.get("url"),
    }
    errors = remote_snapshot_errors(config, state, snapshot)
    if errors:
        raise PublicationError("; ".join(errors))
    trigger_body = review_trigger_comment(config, state)
    comments_path = (
        f"repos/{config['canonical_repository']}/issues/{config['review_pr_number']}/comments"
    )
    comments = json.loads(runner(["gh", "api", comments_path, "--paginate"], cwd=repo))
    exact_comments = [
        row for row in comments
        if isinstance(row, dict) and row.get("body") == trigger_body
    ]
    if exact_comments:
        trigger_artifact_url = exact_comments[-1].get("html_url")
    else:
        created = json.loads(
            runner(["gh", "api", comments_path, "-f", f"body={trigger_body}"], cwd=repo)
        )
        trigger_artifact_url = created.get("html_url")
    if not isinstance(trigger_artifact_url, str) or not trigger_artifact_url:
        raise PublicationError("exact review trigger comment read-back failed")
    state["phase"] = "AWAITING_EXTERNAL_PRODUCT_REVIEW"
    state["publication"] = {"status": "PUBLISHED", **{k: snapshot[k] for k in (
        "repository", "pull_request", "remote_head", "candidate_fingerprint",
        "request_marker", "artifact_url")}, "trigger_comment": trigger_body,
        "trigger_artifact_url": trigger_artifact_url}
    temporary = repo / ".ai/external-review-state.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, repo / external_review_control.STATE_PATH)
    return state["publication"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.repo.resolve()), indent=2))
    except PublicationError as exc:
        print(json.dumps({"status": "FAILED_CLOSED", "reason": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
