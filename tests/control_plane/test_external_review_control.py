from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import external_review_control as CONTROL  # noqa: E402


class ExternalReviewControlTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = "joannalee20050914/KGnote-public"
        self.config = {
            "enabled": True,
            "canonical_repository": repository,
            "candidate_repository": repository,
            "trigger_repository": repository,
            "review_request_repository": repository,
            "archive_repository": "joannalee20050914/KGnote",
            "review_pr_number": 1,
            "max_product_review_rounds": 16,
            "trusted_reviewer_author_login": "trusted-reviewer[bot]",
            "trigger_events": ["pull_request.synchronize", "issue_comment.created"],
            "trigger_comment_template": "@kgnote-ai-review {candidate_commit}",
        }
        self.state = {
            **{field: repository for field in CONTROL.ACTIVE_REPOSITORY_FIELDS},
            "archive_repository": "joannalee20050914/KGnote",
            "pull_request": 1,
            "candidate_commit": "a" * 40,
            "candidate_fingerprint": "b" * 64,
            "review_round": 1,
            "internal_review": {"status": "PASS", "artifact": ".ai/REVIEW_RESULT.md"},
            "publication": {"status": "PUBLISHED", "remote_head": "a" * 40},
            "external_review": {
                "status": "PASS",
                "reviewed_commit": "a" * 40,
                "reviewed_fingerprint": "b" * 64,
                "artifact_url": (
                    f"https://github.com/{repository}/pull/1#pullrequestreview-1"
                ),
                "review_author": "trusted-reviewer[bot]",
                "review_source": "pull_request_review",
                "record_id": 1,
                "submitted_at": "2026-10-17T03:00:00Z",
                "repository": repository,
                "pull_request": 1,
                "review_round": 1,
                "findings": [],
                "blocking_findings": [],
                "consumer_accepted": True,
                "original_body_sha256": "c" * 64,
            },
        }
        self.state["publication"].update({
            "repository": repository,
            "pull_request": 1,
            "candidate_fingerprint": "b" * 64,
            "request_marker": "REQUEST_V2",
            "artifact_url": "https://github.example/pr/1",
            "trigger_comment": "@kgnote-ai-review " + "a" * 40,
            "trigger_artifact_url": "https://github.example/pr/1#issuecomment-1",
        })
        self.config["request_marker"] = "REQUEST_V2"
        self.authority = {
            "repository": repository,
            "pull_request": 1,
            "candidate_commit": "a" * 40,
            "candidate_fingerprint": "b" * 64,
            "review_round": 1,
        }

    def test_wrong_repository_publication_fails_closed(self) -> None:
        config = {**self.config, "candidate_repository": "joannalee20050914/KGnote"}
        self.assertIn("must match", " ".join(CONTROL.repository_authority_errors(config)))

    def test_trigger_payload_and_event_must_match_saved_task_contract(self) -> None:
        wrong_payload = {**self.config, "trigger_comment_template": "@kgnote-ai-review {candidate_commit} extra"}
        self.assertIn("trigger comment template", " ".join(CONTROL.repository_authority_errors(wrong_payload)))
        missing_event = {**self.config, "trigger_events": ["pull_request.synchronize"]}
        self.assertIn("issue-comment trigger", " ".join(CONTROL.repository_authority_errors(missing_event)))

    def test_missing_external_review_artifact_blocks_human_gate(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["artifact_url"] = None
        self.assertIn("artifact is missing", " ".join(CONTROL.human_gate_blockers(self.config, state)))

    def test_internal_pass_without_external_pass_blocks_human_gate(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"] = {"status": "PENDING", "artifact_url": None, "blocking_findings": []}
        self.assertNotEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(self.config, state))

    def test_external_changes_required_returns_to_repair(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["status"] = "CHANGES_REQUIRED"
        state["external_review"]["blocking_findings"] = ["KG-SEM-001"]
        self.assertEqual("REPAIRING_EXTERNAL_FINDINGS", CONTROL.next_machine_state(self.config, state))

    def test_repository_migration_split_brain_is_authority_conflict(self) -> None:
        config = {**self.config, "trigger_repository": "joannalee20050914/KGnote"}
        self.assertEqual("AUTHORITY_CONFLICT", CONTROL.next_machine_state(config, self.state))

    def test_premature_human_transition_requires_exact_external_pass(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["reviewed_commit"] = "c" * 40
        blockers = CONTROL.human_gate_blockers(self.config, state)
        self.assertTrue(any("exact candidate commit" in blocker for blocker in blockers))
        self.assertNotEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(self.config, state))

    def test_exact_external_pass_allows_real_human_checkpoint(self) -> None:
        self.assertEqual([], CONTROL.human_gate_blockers(
            self.config, self.state, canonical_authority=self.authority
        ))
        self.assertEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(
            self.config, self.state, canonical_authority=self.authority
        ))

    def test_canonical_publication_authority_is_resolved_independently(self) -> None:
        marker = (
            "<!-- REQUEST_V2 candidate_commit=" + "a" * 40
            + " candidate_fingerprint=" + "b" * 64
            + " review_round=1 -->"
        )
        snapshot = {
            "repository": self.config["canonical_repository"],
            "pull_request": self.config["review_pr_number"],
            "headRefOid": "a" * 40,
            "body": marker,
            "state": "OPEN",
        }
        self.assertEqual(
            self.authority,
            CONTROL.resolve_canonical_publication_authority(
                self.config, snapshot, "b" * 64
            ),
        )
        mutations = (
            ("repository", "other/repository", "b" * 64),
            ("pull_request", 2, "b" * 64),
            ("headRefOid", "e" * 40, "b" * 64),
            ("body", marker.replace("review_round=1", "review_round=0"), "b" * 64),
            ("body", marker.replace("review_round=1", "review_round=17"), "b" * 64),
            ("body", marker.replace("candidate_commit=" + "a" * 40,
                                     "candidate_commit=" + "e" * 40), "b" * 64),
            ("body", marker.replace("candidate_fingerprint=" + "b" * 64,
                                     "candidate_fingerprint=" + "f" * 64), "b" * 64),
            ("body", marker.replace("candidate_commit=" + "a" * 40,
                                     "candidate_commit=" + "z" * 40), "b" * 64),
            ("body", marker.replace("candidate_fingerprint=" + "b" * 64,
                                     "candidate_fingerprint=" + "z" * 64), "b" * 64),
            ("state", "CLOSED", "b" * 64),
        )
        for field, wrong, recomputed in mutations:
            with self.subTest(field=field, wrong=wrong):
                broken = {**snapshot, field: wrong}
                with self.assertRaises(CONTROL.CanonicalAuthorityError):
                    CONTROL.resolve_canonical_publication_authority(
                        self.config, broken, recomputed
                    )
        with self.assertRaises(CONTROL.CanonicalAuthorityError):
            CONTROL.resolve_canonical_publication_authority(
                self.config, snapshot, "f" * 64
            )

    def test_durable_accepted_record_identity_is_revalidated_through_completion(self) -> None:
        config = {
            **self.config,
            "trusted_reviewer_author_login": "trusted-reviewer[bot]",
            "delivery_issue_number": 8,
            "project_item_id": "project-item-8",
        }
        state = copy.deepcopy(self.state)
        state["review_round"] = 11
        state["external_review"].update({
            "record_id": 123,
            "review_author": "trusted-reviewer[bot]",
            "review_source": "pull_request_review",
            "submitted_at": "2026-10-17T03:00:00Z",
            "repository": config["canonical_repository"],
            "pull_request": config["review_pr_number"],
            "review_round": state["review_round"],
            "findings": [],
            "consumer_accepted": True,
            "original_body_sha256": "c" * 64,
            "artifact_url": (
                f"https://github.com/{config['canonical_repository']}/pull/1"
                "#pullrequestreview-123"
            ),
        })
        authority = {**self.authority, "review_round": 11}
        artifact_url = state["external_review"]["artifact_url"]
        receipt_body = CONTROL.issue_receipt_body(
            config, state, artifact_url, canonical_authority=authority
        )
        state["delivery_receipt"] = {
            "status": "VERIFIED",
            "repository": config["canonical_repository"],
            "pull_request": config["review_pr_number"],
            "candidate_commit": state["candidate_commit"],
            "candidate_fingerprint": state["candidate_fingerprint"],
            "review_round": state["review_round"],
            "project_status": "Review Queue",
            "review_artifact_url": artifact_url,
            "issue": config["delivery_issue_number"],
            "project_item_id": config["project_item_id"],
            "project_content_repository": config["canonical_repository"],
            "project_content_issue": config["delivery_issue_number"],
            "issue_comment_author": config["trusted_reviewer_author_login"],
            "issue_comment_id": 9001,
            "issue_comment_url": (
                f"https://github.com/{config['canonical_repository']}/issues/8"
                "#issuecomment-9001"
            ),
            "issue_receipt_body_sha256": hashlib.sha256(
                receipt_body.encode("utf-8")
            ).hexdigest(),
            "preserved_gates": [
                "PA-HUMAN-1", "NS-HUMAN-SMOKE", "release_verified=false"
            ],
        }
        self.assertEqual([], CONTROL.human_gate_blockers(
            config, state, canonical_authority=authority
        ))
        self.assertEqual([], CONTROL.delivery_receipt_blockers(
            config, state, canonical_authority=authority
        ))
        self.assertEqual(
            "HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(
                config, state, canonical_authority=authority
            )
        )

        self_consistent_rewrites = (
            ("repository", "other/repository"),
            ("pull_request", 2),
            ("review_round", 0),
            ("review_round", 12),
            ("review_round", 17),
            ("candidate_commit", "z" * 40),
            ("candidate_commit", "e" * 40),
            ("candidate_fingerprint", "z" * 64),
            ("candidate_fingerprint", "f" * 64),
        )
        for field, wrong in self_consistent_rewrites:
            with self.subTest(self_consistent_field=field, wrong=wrong):
                broken = copy.deepcopy(state)
                accepted_field = {
                    "candidate_commit": "reviewed_commit",
                    "candidate_fingerprint": "reviewed_fingerprint",
                }.get(field, field)
                broken[field] = wrong
                broken["external_review"][accepted_field] = wrong
                if field in {"repository", "pull_request"}:
                    broken["external_review"]["artifact_url"] = (
                        f"https://github.com/{broken.get('repository')}/pull/"
                        f"{broken.get('pull_request')}#pullrequestreview-123"
                    )
                serialized = json.loads(json.dumps(broken))
                self.assertTrue(CONTROL.human_gate_blockers(
                    config, serialized, canonical_authority=authority
                ))
                self.assertTrue(CONTROL.delivery_receipt_blockers(
                    config, serialized, canonical_authority=authority
                ))
                self.assertNotEqual(
                    "HUMAN_CHECKPOINT_REQUIRED",
                    CONTROL.next_machine_state(
                        config, serialized, canonical_authority=authority
                    ),
                )

        for source, url in (
            ("pull_request_review", "https://evil.example/review/123"),
            ("pull_request_review", f"https://github.com/{config['canonical_repository']}/pull/1#issuecomment-123"),
            ("issue_comment", f"https://github.com/{config['canonical_repository']}/pull/1#pullrequestreview-123"),
            ("issue_comment", f"https://github.com/{config['canonical_repository']}/pull/1#issuecomment-124"),
        ):
            with self.subTest(source=source, artifact_url=url):
                broken = copy.deepcopy(state)
                broken["external_review"]["review_source"] = source
                broken["external_review"]["artifact_url"] = url
                self.assertTrue(CONTROL.human_gate_blockers(
                    config, broken, canonical_authority=authority
                ))

        missing = object()
        malformed = {
            "record_id": (missing, None, "123", 0, -1, True),
            "artifact_url": (missing, None, 17, "", "not-a-url"),
            "review_author": (missing, None, 17, "", "untrusted"),
            "review_source": (missing, None, 17, "unknown"),
            "submitted_at": (missing, None, 17, "", "not-a-time", "2026-10-17T03:00:00"),
            "repository": (missing, None, "other/repo"),
            "pull_request": (missing, None, "1", 0, -1, 2, True),
            "review_round": (missing, None, "11", 0, -1, 10, True),
            "findings": (missing, None, {}, [{"id": ""}]),
            "consumer_accepted": (missing, None, False, "true"),
            "original_body_sha256": (missing, None, 17, "", "c" * 63),
        }
        for field, values in malformed.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    broken = copy.deepcopy(state)
                    if value is missing:
                        broken["external_review"].pop(field)
                    else:
                        broken["external_review"][field] = value
                    self.assertTrue(CONTROL.human_gate_blockers(
                        config, broken, canonical_authority=authority
                    ), field)
                    self.assertTrue(CONTROL.delivery_receipt_blockers(
                        config, broken, canonical_authority=authority
                    ), field)
                    self.assertNotEqual(
                        "HUMAN_CHECKPOINT_REQUIRED",
                        CONTROL.next_machine_state(
                            config, broken, canonical_authority=authority
                        ),
                        field,
                    )
                    with tempfile.TemporaryDirectory() as directory:
                        repo = Path(directory)
                        (repo / ".ai").mkdir()
                        (repo / CONTROL.CONFIG_PATH).write_text(
                            json.dumps(config), encoding="utf-8"
                        )
                        (repo / CONTROL.STATE_PATH).write_text(
                            json.dumps(broken), encoding="utf-8"
                        )
                        self.assertTrue(
                            CONTROL.repository_human_gate_blockers(
                                repo, canonical_authority=authority
                            ), field
                        )
                        restored = CONTROL.load_json(repo / CONTROL.STATE_PATH)
                        self.assertTrue(
                            CONTROL.delivery_receipt_blockers(
                                config, restored, canonical_authority=authority
                            ), field
                        )
                        self.assertNotEqual(
                            "HUMAN_CHECKPOINT_REQUIRED",
                            CONTROL.next_machine_state(
                                config, restored, canonical_authority=authority
                            ),
                            field,
                        )

    def test_exact_publication_readback_allows_publish_progression(self) -> None:
        self.assertEqual([], CONTROL.publication_progression_blockers(self.config, self.state))

    def test_publication_readback_fails_for_wrong_repo_stale_head_or_missing_marker(self) -> None:
        for field, value in (
            ("repository", "joannalee20050914/KGnote"),
            ("remote_head", "c" * 40),
            ("candidate_fingerprint", "d" * 64),
            ("request_marker", None),
            ("trigger_comment", "@kgnote-ai-review wrong"),
        ):
            with self.subTest(field=field):
                state = copy.deepcopy(self.state)
                state["publication"][field] = value
                blockers = CONTROL.publication_progression_blockers(self.config, state)
                self.assertTrue(any(field in blocker for blocker in blockers))

        state = copy.deepcopy(self.state)
        state["publication"]["trigger_artifact_url"] = None
        self.assertIn(
            "event-trigger artifact URL",
            " ".join(CONTROL.publication_progression_blockers(self.config, state)),
        )

    def test_pending_or_failed_publication_cannot_complete_milestone(self) -> None:
        state = copy.deepcopy(self.state)
        state["publication"]["status"] = "PENDING"
        self.assertIn("not published", " ".join(CONTROL.publication_progression_blockers(self.config, state)))

    def test_canonical_github_bytes_override_locally_rewritten_pass(self) -> None:
        config = {
            **self.config,
            "program_id": "program-external-review-test",
            "result_marker": "kgnote-ai-product-review:v1",
        }
        state = copy.deepcopy(self.state)
        state["goal_id"] = "goal-external-review-test"
        finding = {
            "id": "finding-live-blocker",
            "severity": "blocking",
            "category": "engineering",
            "observation": "Canonical GitHub bytes retain a blocking finding.",
            "expected_behavior": "Restart must preserve the machine blocker.",
            "authority_refs": ["docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md"],
            "candidate_evidence": ["tests/control_plane/test_external_review_control.py"],
        }
        result = {
            "protocol": "kgnote.product-review.v1",
            "repository": config["canonical_repository"],
            "pull_request": config["review_pr_number"],
            "program_id": config["program_id"],
            "goal_id": state["goal_id"],
            "candidate_fingerprint": self.authority["candidate_fingerprint"],
            "candidate_commit": self.authority["candidate_commit"],
            "review_round": self.authority["review_round"],
            "verdict": "CHANGES_REQUIRED",
            "findings": [finding],
            "native_ui_observed": False,
        }
        body = (
            "<!-- kgnote-ai-product-review:v1 reviewed_head_sha="
            + self.authority["candidate_commit"]
            + " -->\n```json\n"
            + json.dumps(result)
            + "\n```"
        )
        record = {
            "source": "pull_request_review",
            "author_login": config["trusted_reviewer_author_login"],
            "review_state": "COMMENTED",
            "record_id": 1,
            "body": body,
            "artifact_url": state["external_review"]["artifact_url"],
            "submitted_at": state["external_review"]["submitted_at"],
        }
        schema = json.loads(
            (ROOT / "schemas/product-review/v1/review-result.schema.json").read_text(
                encoding="utf-8"
            )
        )

        # The durable copy has been rewritten into a self-consistent PASS.
        state["external_review"].update({
            "status": "PASS",
            "findings": [],
            "blocking_findings": [],
            "original_body_sha256": hashlib.sha256(b"fabricated PASS").hexdigest(),
        })
        blockers = CONTROL.revalidated_external_review_blockers(
            config, state, record, schema, canonical_authority=self.authority
        )
        self.assertTrue(any("field status" in item for item in blockers), blockers)
        self.assertTrue(any("field findings" in item for item in blockers))
        self.assertTrue(any("original_body_sha256" in item for item in blockers))

        # A durable record that exactly matches the independently read bytes remains valid.
        state["external_review"].update({
            "status": "CHANGES_REQUIRED",
            "findings": [finding],
            "blocking_findings": [finding["id"]],
            "original_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        })
        self.assertEqual([], CONTROL.revalidated_external_review_blockers(
            config, state, record, schema, canonical_authority=self.authority
        ))

    def test_repository_revalidation_reads_exact_record_and_live_pr_routing(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/product-review/v1/review-result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for source, record_id in (("pull_request_review", 71), ("issue_comment", 72)):
            with self.subTest(source=source):
                with tempfile.TemporaryDirectory() as directory:
                    repo = Path(directory)
                    (repo / ".ai").mkdir()
                    (repo / "schemas/product-review/v1").mkdir(parents=True)
                    config = {
                        **self.config,
                        "schema_version": "kgnote.github-product-reviewer-config.v2",
                        "program_id": "program-external-review-test",
                        "result_marker": "kgnote-ai-product-review:v1",
                        "review_pr_expected_draft": True,
                        "review_pr_head_branch": "codex/candidate",
                        "review_pr_base_branch": "codex/base",
                        "dependency_pr_number": 22,
                        "dependency_pr_required_state": "OPEN",
                    }
                    state = copy.deepcopy(self.state)
                    state["goal_id"] = "goal-external-review-test"
                    result = {
                        "protocol": "kgnote.product-review.v1",
                        "repository": config["canonical_repository"],
                        "pull_request": config["review_pr_number"],
                        "program_id": config["program_id"],
                        "goal_id": state["goal_id"],
                        "candidate_fingerprint": self.authority["candidate_fingerprint"],
                        "candidate_commit": self.authority["candidate_commit"],
                        "review_round": self.authority["review_round"],
                        "verdict": "PASS",
                        "findings": [],
                        "native_ui_observed": False,
                    }
                    body = (
                        "<!-- kgnote-ai-product-review:v1 reviewed_head_sha="
                        + self.authority["candidate_commit"]
                        + " -->\n```json\n" + json.dumps(result) + "\n```"
                    )
                    anchor = "pullrequestreview" if source == "pull_request_review" else "issuecomment"
                    artifact_url = (
                        f"https://github.com/{config['canonical_repository']}/pull/1"
                        f"#{anchor}-{record_id}"
                    )
                    submitted_at = "2026-10-17T03:00:00Z"
                    state["external_review"].update({
                        "record_id": record_id,
                        "artifact_url": artifact_url,
                        "review_source": source,
                        "submitted_at": submitted_at,
                        "repository": config["canonical_repository"],
                        "pull_request": config["review_pr_number"],
                        "review_round": self.authority["review_round"],
                        "findings": [],
                        "blocking_findings": [],
                        "consumer_accepted": True,
                        "original_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    })
                    (repo / CONTROL.CONFIG_PATH).write_text(json.dumps(config), encoding="utf-8")
                    (repo / CONTROL.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")
                    (repo / "schemas/product-review/v1/review-result.schema.json").write_text(
                        json.dumps(schema), encoding="utf-8"
                    )
                    marker = (
                        "<!-- REQUEST_V2 candidate_commit=" + self.authority["candidate_commit"]
                        + " candidate_fingerprint=" + self.authority["candidate_fingerprint"]
                        + " review_round=1 -->"
                    )
                    config["request_marker"] = "REQUEST_V2"
                    (repo / CONTROL.CONFIG_PATH).write_text(json.dumps(config), encoding="utf-8")

                    def runner(command: list[str], *, cwd: Path) -> str:
                        if command[:3] == ["gh", "pr", "view"] and command[3] == "1":
                            return json.dumps({
                                "headRefOid": self.authority["candidate_commit"],
                                "body": marker,
                                "state": "OPEN",
                                "url": "https://github.com/example/pr/1",
                                "isDraft": True,
                                "headRefName": "codex/candidate",
                                "baseRefName": "codex/base",
                            })
                        if command[:3] == ["gh", "pr", "view"] and command[3] == "22":
                            return json.dumps({"number": 22, "state": "OPEN", "mergedAt": None})
                        if command[:2] == ["gh", "api"]:
                            payload = {
                                "id": record_id,
                                "html_url": artifact_url,
                                "user": {"login": config["trusted_reviewer_author_login"]},
                                "body": body,
                            }
                            if source == "pull_request_review":
                                payload.update({"state": "COMMENTED", "submitted_at": submitted_at})
                            else:
                                payload["created_at"] = submitted_at
                            return json.dumps(payload)
                        raise AssertionError(command)

                    with mock.patch("codex_control.repository_fingerprint", return_value={"value": self.authority["candidate_fingerprint"]}):
                        authority, blockers = CONTROL.resolve_repository_external_review(repo, runner)
                    self.assertEqual(self.authority, authority)
                    self.assertEqual([], blockers)

                    def stale_runner(command: list[str], *, cwd: Path) -> str:
                        raw = runner(command, cwd=cwd)
                        if command[:3] == ["gh", "pr", "view"] and command[3] == "1":
                            payload = json.loads(raw)
                            payload["isDraft"] = False
                            return json.dumps(payload)
                        return raw

                    with mock.patch("codex_control.repository_fingerprint", return_value={"value": self.authority["candidate_fingerprint"]}):
                        with self.assertRaises(CONTROL.CanonicalAuthorityError):
                            CONTROL.resolve_repository_external_review(repo, stale_runner)

                    def closed_dependency_runner(command: list[str], *, cwd: Path) -> str:
                        if command[:3] == ["gh", "pr", "view"] and command[3] == "22":
                            return json.dumps({"number": 22, "state": "CLOSED", "mergedAt": "2026-10-17T03:10:00Z"})
                        return runner(command, cwd=cwd)

                    with mock.patch("codex_control.repository_fingerprint", return_value={"value": self.authority["candidate_fingerprint"]}):
                        with self.assertRaises(CONTROL.CanonicalAuthorityError):
                            CONTROL.resolve_repository_external_review(repo, closed_dependency_runner)

                    def missing_record_runner(command: list[str], *, cwd: Path) -> str:
                        if command[:2] == ["gh", "api"]:
                            raise CONTROL.CanonicalAuthorityError("record not found")
                        return runner(command, cwd=cwd)

                    with mock.patch("codex_control.repository_fingerprint", return_value={"value": self.authority["candidate_fingerprint"]}):
                        with self.assertRaises(CONTROL.CanonicalAuthorityError):
                            CONTROL.resolve_repository_external_review(repo, missing_record_runner)


if __name__ == "__main__":
    unittest.main()
