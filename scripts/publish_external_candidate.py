#!/usr/bin/env python3
"""Publish and read back one exact candidate on the canonical review PR."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import codex_control
import external_review_control


class PublicationError(RuntimeError):
    pass


def request_marker(config: dict[str, Any], state: dict[str, Any]) -> str:
    return (
        f"<!-- {config['request_marker']} candidate_commit={state['candidate_commit']} "
        f"candidate_fingerprint={state['candidate_fingerprint']} "
        f"review_round={state['review_round']} -->"
    )


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
    return completed.stdout.strip()


def publish(repo: Path, runner: Callable[..., str] = _run) -> dict[str, Any]:
    config = external_review_control.load_json(repo / external_review_control.CONFIG_PATH)
    state = external_review_control.load_json(repo / external_review_control.STATE_PATH)
    authority = external_review_control.repository_authority_errors(config)
    if authority:
        raise PublicationError("; ".join(authority))
    head = runner(["git", "rev-parse", "HEAD"], cwd=repo)
    fingerprint = codex_control.repository_fingerprint(repo)["value"]
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
        body_file.write_text(body.rstrip() + "\n\n" + marker + "\n", encoding="utf-8")
        try:
            runner(["gh", "pr", "edit", str(config["review_pr_number"]), "--repo", config["canonical_repository"], "--body-file", str(body_file)], cwd=repo)
        finally:
            body_file.unlink(missing_ok=True)
    runner(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo)
    observed = json.loads(runner(
        ["gh", "pr", "view", str(config["review_pr_number"]), "--repo", config["canonical_repository"], "--json", "headRefOid,body,state,url"],
        cwd=repo,
    ))
    snapshot = {
        "repository": config["canonical_repository"], "pull_request": config["review_pr_number"],
        "remote_head": observed.get("headRefOid"), "candidate_fingerprint": fingerprint,
        "request_marker": config["request_marker"], "body": observed.get("body"),
        "state": observed.get("state"), "artifact_url": observed.get("url"),
    }
    errors = remote_snapshot_errors(config, state, snapshot)
    if errors:
        raise PublicationError("; ".join(errors))
    state["phase"] = "AWAITING_EXTERNAL_PRODUCT_REVIEW"
    state["publication"] = {"status": "PUBLISHED", **{k: snapshot[k] for k in (
        "repository", "pull_request", "remote_head", "candidate_fingerprint",
        "request_marker", "artifact_url")}}
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
