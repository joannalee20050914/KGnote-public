from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import external_review_control as external_control  # noqa: E402
import publish_external_candidate as publisher  # noqa: E402
from github_product_review_consumer import (  # noqa: E402
    CandidateIdentity,
    consume_records,
)


COMMIT = "c" * 40
FINGERPRINT = "d" * 64
GOAL_ID = "goal-isolated-exact-review-integration"
ROUND = 15


class ExactReviewIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live_config = json.loads(
            (ROOT / ".ai/github-product-reviewer.json").read_text(encoding="utf-8")
        )
        cls.schema = json.loads(
            (ROOT / "schemas/product-review/v1/review-result.schema.json").read_text(
                encoding="utf-8"
            )
        )

    def identity(self) -> CandidateIdentity:
        return CandidateIdentity(
            repository=self.live_config["canonical_repository"],
            pull_request=self.live_config["review_pr_number"],
            program_id=self.live_config["program_id"],
            goal_id=GOAL_ID,
            candidate_fingerprint=FINGERPRINT,
            candidate_commit=COMMIT,
            review_round=ROUND,
        )

    def result(self, *, verdict: str = "PASS", findings: list[dict] | None = None) -> dict:
        identity = self.identity()
        return {
            "protocol": "kgnote.product-review.v1",
            "repository": identity.repository,
            "pull_request": identity.pull_request,
            "program_id": identity.program_id,
            "goal_id": identity.goal_id,
            "candidate_fingerprint": identity.candidate_fingerprint,
            "candidate_commit": identity.candidate_commit,
            "review_round": identity.review_round,
            "verdict": verdict,
            "findings": [] if findings is None else findings,
            "native_ui_observed": False,
        }

    def record(
        self,
        result: dict,
        *,
        marker_commit: str = COMMIT,
        record_id: int = 9001,
    ) -> dict:
        return {
            "source": "pull_request_review",
            "author_login": self.live_config["trusted_reviewer_author_login"],
            "review_state": "COMMENTED",
            "record_id": record_id,
            "body": (
                "<!-- "
                + self.live_config["result_marker"]
                + f" reviewed_head_sha={marker_commit} -->\n"
                + "```json\n"
                + json.dumps(result)
                + "\n```"
            ),
        }

    def base_state(self) -> dict:
        repository = self.live_config["canonical_repository"]
        return {
            **{
                field: repository
                for field in external_control.ACTIVE_REPOSITORY_FIELDS
            },
            "archive_repository": self.live_config["archive_repository"],
            "pull_request": self.live_config["review_pr_number"],
            "candidate_commit": COMMIT,
            "candidate_fingerprint": FINGERPRINT,
            "review_round": ROUND,
            "internal_review": {
                "status": "PASS",
                "artifact": "synthetic-isolated-test-only",
            },
            "publication": {"status": "PENDING"},
            "external_review": {
                "status": "PENDING",
                "reviewed_commit": None,
                "reviewed_fingerprint": None,
                "artifact_url": None,
                "blocking_findings": [],
            },
            "release_verified": False,
        }

    def publish_isolated_candidate(self, repo: Path) -> dict:
        (repo / ".ai").mkdir()
        (repo / ".git").mkdir()
        (repo / ".ai/github-product-reviewer.json").write_text(
            json.dumps(self.live_config), encoding="utf-8"
        )
        (repo / ".ai/external-review-state.json").write_text(
            json.dumps(self.base_state()), encoding="utf-8"
        )
        marker = publisher.request_marker(self.live_config, self.base_state())
        trigger = publisher.review_trigger_comment(self.live_config, self.base_state())
        calls: list[list[str]] = []

        def runner(command: list[str], *, cwd: Path) -> str:
            calls.append(command)
            if command[:3] == ["git", "rev-parse", "HEAD"]:
                return COMMIT
            if command[:3] == ["git", "status", "--porcelain"]:
                return ""
            if command[:4] == ["git", "remote", "get-url", "origin"]:
                return f"https://github.com/{self.live_config['canonical_repository']}.git"
            if command[:3] == ["git", "branch", "--show-current"]:
                return "codex/isolated-exact-review"
            if command[:3] == ["gh", "pr", "view"] and command[-1] == "body":
                return json.dumps({"body": "isolated candidate\n" + marker})
            if command[:3] == ["git", "push", "origin"]:
                return ""
            if command[:3] == ["gh", "pr", "view"]:
                if command[3] == str(self.live_config["dependency_pr_number"]):
                    return json.dumps({"number": self.live_config["dependency_pr_number"], "state": "OPEN", "mergedAt": None})
                return json.dumps(
                    {
                        "headRefOid": COMMIT,
                        "body": "isolated candidate\n" + marker,
                        "state": "OPEN",
                        "url": "https://example.invalid/isolated/pr/1",
                        "isDraft": True,
                        "headRefName": self.live_config["review_pr_head_branch"],
                        "baseRefName": self.live_config["review_pr_base_branch"],
                    }
                )
            if command[:2] == ["gh", "api"] and command[-1] == "--paginate":
                return "[]"
            if command[:2] == ["gh", "api"] and command[-1] == f"body={trigger}":
                return json.dumps(
                    {"html_url": "https://example.invalid/isolated/pr/1#trigger"}
                )
            raise AssertionError(command)

        with mock.patch.object(
            publisher.codex_control,
            "repository_fingerprint",
            return_value={"value": FINGERPRINT},
        ):
            publication = publisher.publish(repo, runner)
        self.assertTrue(any(command[:2] == ["git", "push"] for command in calls))
        self.assertEqual([], external_control.repository_publication_progression_blockers(repo))
        return publication

    def test_exact_publication_result_consumption_and_gate_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            publication = self.publish_isolated_candidate(repo)
            decision = consume_records(
                config=self.live_config,
                schema=self.schema,
                identity=self.identity(),
                records=[self.record(self.result())],
            )
            self.assertTrue(decision["accepted"])
            self.assertEqual("PASS", decision["status"])

            state = json.loads(
                (repo / ".ai/external-review-state.json").read_text(encoding="utf-8")
            )
            state["external_review"] = {
                "status": decision["status"],
                "reviewed_commit": decision["candidate_commit"],
                "reviewed_fingerprint": decision["candidate_fingerprint"],
                "artifact_url": "https://example.invalid/isolated/review/9001",
                "blocking_findings": decision["findings"],
            }
            state["delivery_receipt"] = {
                "status": "VERIFIED", "repository": self.live_config["canonical_repository"],
                "pull_request": self.live_config["review_pr_number"], "candidate_commit": COMMIT,
                "candidate_fingerprint": FINGERPRINT, "review_round": state["review_round"],
                "review_artifact_url": "https://example.invalid/isolated/review/9001",
                "issue_comment_url": "https://example.invalid/issues/8#comment",
                "project_status": "Review Queue",
            }
            self.assertEqual(COMMIT, publication["remote_head"])
            self.assertEqual(FINGERPRINT, publication["candidate_fingerprint"])
            self.assertEqual([], external_control.human_gate_blockers(self.live_config, state))
            self.assertEqual(
                "HUMAN_CHECKPOINT_REQUIRED",
                external_control.next_machine_state(self.live_config, state),
            )
            self.assertFalse(state["release_verified"])

    def test_identity_internal_only_and_blocking_finding_fail_closed(self) -> None:
        identity = self.identity()
        for field, value in (
            ("repository", "joannalee20050914/KGnote"),
            ("pull_request", 99),
            ("candidate_commit", "e" * 40),
            ("candidate_fingerprint", "f" * 64),
            ("review_round", ROUND - 1),
        ):
            with self.subTest(field=field):
                result = self.result()
                result[field] = value
                decision = consume_records(
                    config=self.live_config,
                    schema=self.schema,
                    identity=identity,
                    records=[self.record(result)],
                )
                self.assertFalse(decision["accepted"])
                self.assertEqual("WAITING_FOR_PRODUCT_REVIEW", decision["status"])
                self.assertIn(field, decision["rejected"][0]["fields"])

        marker_mismatch = consume_records(
            config=self.live_config,
            schema=self.schema,
            identity=identity,
            records=[self.record(self.result(), marker_commit="e" * 40)],
        )
        self.assertFalse(marker_mismatch["accepted"])
        self.assertEqual(
            "result_marker_commit_mismatch",
            marker_mismatch["rejected"][0]["reason"],
        )

        internal_only = consume_records(
            config=self.live_config,
            schema=self.schema,
            identity=identity,
            records=[],
        )
        self.assertFalse(internal_only["accepted"])
        self.assertEqual("WAITING_FOR_PRODUCT_REVIEW", internal_only["status"])

        finding = {
            "id": "finding-synthetic-blocker",
            "severity": "blocking",
            "category": "engineering",
            "observation": "Synthetic isolated fixture exercises blocking routing.",
            "expected_behavior": "Blocking findings prevent human-gate progression.",
            "authority_refs": ["docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md"],
            "candidate_evidence": ["tests/control_plane/test_exact_review_integration.py"],
        }
        changes = consume_records(
            config=self.live_config,
            schema=self.schema,
            identity=identity,
            records=[
                self.record(
                    self.result(verdict="CHANGES_REQUIRED", findings=[finding]),
                    record_id=9002,
                )
            ],
        )
        self.assertTrue(changes["accepted"])
        self.assertEqual("CHANGES_REQUIRED", changes["status"])
        state = self.base_state()
        state["external_review"] = {
            "status": changes["status"],
            "reviewed_commit": changes["candidate_commit"],
            "reviewed_fingerprint": changes["candidate_fingerprint"],
            "artifact_url": "https://example.invalid/isolated/review/9002",
            "blocking_findings": changes["findings"],
        }
        self.assertEqual(
            "REPAIRING_EXTERNAL_FINDINGS",
            external_control.next_machine_state(self.live_config, state),
        )
        self.assertIn(
            "blocking findings remain",
            " ".join(external_control.human_gate_blockers(self.live_config, state)),
        )


if __name__ == "__main__":
    unittest.main()
