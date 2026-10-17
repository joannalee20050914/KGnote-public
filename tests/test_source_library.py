from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kgnote.learning.source_library import (
    BATCH_VERSION,
    IMPORT_VERSION,
    MAX_SOURCE_BYTES,
    extraction_input_for_source,
    import_source,
    import_sources,
    list_sources,
    read_source,
)


def request(
    *,
    title: str = "DNS 入門",
    content: str = "# DNS\n\nA resolver maps a name to an address.\n",
    source_kind: str = "document",
    file_name: str = "dns.md",
    source_id: str | None = None,
    expected_revision_id: str | None = None,
) -> dict:
    return {
        "schema_version": IMPORT_VERSION,
        "source_id": source_id,
        "expected_revision_id": expected_revision_id,
        "title": title,
        "content": content,
        "source_kind": source_kind,
        "locator": {"kind": "file_name", "value": file_name},
    }


def tree_bytes(root: Path) -> tuple[tuple[str, bytes], ...]:
    if not root.exists():
        return ()
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


class SourceLibraryTests(unittest.TestCase):
    def test_ordinary_markdown_preserves_exact_bytes_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            content = "# DNS\n\n臺灣的 resolver 會保留原文。\n"
            status, payload = import_source(root, request(content=content))
            self.assertEqual(status, "created")
            source = payload["source"]
            self.assertRegex(source["source_id"], r"^src_[0-9a-f]{24}$")
            self.assertEqual(source["source_kind"], "document")
            self.assertEqual(source["revision_count"], 1)

            read_back = read_source(root, source["source_id"])
            self.assertEqual(read_back["content"].encode("utf-8"), content.encode("utf-8"))
            self.assertEqual(read_back["revision"]["provenance"]["locator"], {"kind": "file_name", "value": "dns.md"})
            self.assertEqual(read_back["revision"]["provenance"]["adapter_version"], IMPORT_VERSION)
            self.assertEqual(read_back["headings"], [{"line": 1, "title": "DNS", "level": 1}])
            self.assertEqual(list_sources(root)[0]["current_revision_id"], source["current_revision_id"])
            extraction_input = extraction_input_for_source(root, source["source_id"])
            self.assertEqual(extraction_input["source"]["content"].encode("utf-8"), content.encode("utf-8"))
            self.assertEqual(extraction_input["source"]["content_sha256"], read_back["revision"]["content_sha256"])

    def test_conversation_preserves_explicit_speakers_and_rejects_ambiguous_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            content = "# 對話\n\nLearner: correlation 是 causation 嗎？\n\nTutor: 不是，仍要檢查其他證據。\n"
            status, payload = import_source(root, request(
                title="概念對話", content=content, source_kind="chatgpt_conversation", file_name="chat.md",
            ))
            self.assertEqual(status, "created")
            read_back = read_source(root, payload["source"]["source_id"])
            self.assertEqual(
                [(item["speaker"], item["role"], item["locator"]["value"]) for item in read_back["revision"]["speaker_spans"]],
                [("Learner", "user", "L3-L4"), ("Tutor", "assistant", "L5-L5")],
            )

            status, rejected = import_source(root, request(
                title="不明對話", content="Alex: 私人名稱不應被猜成 user。\n", source_kind="chatgpt_conversation", file_name="unknown.md",
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(rejected["problem"]["code"], "ambiguous_conversation_speaker")

            status, rejected = import_source(root, request(
                title="中途不明對話",
                content="Learner: 已知發言者。\n\nAlex: 不可沿用上一位發言者。\n",
                source_kind="chatgpt_conversation",
                file_name="unknown-after-known.md",
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(rejected["problem"]["code"], "ambiguous_conversation_speaker")

    def test_heading_conversation_records_system_user_and_assistant_spans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            content = "# Session\n\n## System\nBe precise.\n\n## User\nQuestion.\n\n## Assistant\nAnswer.\n"
            status, payload = import_source(root, request(
                content=content, source_kind="chatgpt_conversation", file_name="session.md",
            ))
            self.assertEqual(status, "created")
            roles = [item["role"] for item in read_source(root, payload["source"]["source_id"])["revision"]["speaker_spans"]]
            self.assertEqual(roles, ["system", "user", "assistant"])

    def test_mixed_conversation_formats_reject_unknown_labels_and_keep_known_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            for file_name, content in (
                ("heading-first.md", "## User\nKnown.\n\nAlex: ambiguous.\n"),
                ("prefix-first.md", "User: Known.\n\n## Assistant\nAnswer.\n\nAlex: ambiguous.\n"),
            ):
                before = tree_bytes(root)
                status, rejected = import_source(root, request(
                    title="Mixed", content=content,
                    source_kind="chatgpt_conversation", file_name=file_name,
                ))
                self.assertEqual(status, "rejected")
                self.assertEqual(rejected["problem"]["code"], "ambiguous_conversation_speaker")
                self.assertEqual(tree_bytes(root), before)

            status, accepted = import_source(root, request(
                title="Known mixed",
                content="## User\nQuestion.\n\nAssistant: Answer.\n\n## Tool\nResult.\n",
                source_kind="chatgpt_conversation", file_name="known-mixed.md",
            ))
            self.assertEqual(status, "created")
            spans = read_source(root, accepted["source"]["source_id"])["revision"]["speaker_spans"]
            self.assertEqual([span["role"] for span in spans], ["user", "assistant", "tool"])
            self.assertEqual([span["locator"]["value"] for span in spans], ["L1-L3", "L4-L5", "L6-L7"])

    def test_conversation_ignores_speaker_like_markers_inside_markdown_fences(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            content = (
                "## User\nQuestion.\n\n## Assistant\nHere is an example:\n"
                "```text\nUser: demonstration only\n## Tool\n```\n"
                "Assistant explanation continues.\n\nUser: Actual follow-up.\n"
                "~~~md\nAssistant: another example\n~~~\n"
            )
            status, accepted = import_source(root, request(
                title="Fenced examples", content=content,
                source_kind="chatgpt_conversation", file_name="fenced.md",
            ))
            self.assertEqual(status, "created")
            spans = read_source(root, accepted["source"]["source_id"])["revision"]["speaker_spans"]
            self.assertEqual(
                [(span["role"], span["locator"]["value"]) for span in spans],
                [("user", "L1-L3"), ("assistant", "L4-L11"), ("user", "L12-L15")],
            )

            status, rejected = import_source(root, request(
                title="Unclosed fence",
                content="User: question\n```text\nAssistant: example only\n",
                source_kind="chatgpt_conversation", file_name="unclosed.md",
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(rejected["problem"]["code"], "ambiguous_conversation_speaker")

    def test_conversation_ignores_speaker_markers_in_html_comments_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            content = (
                "## User\nQuestion.\n\n## Assistant\n<!--\nUser: demonstration only\n-->\n"
                "Assistant explanation continues.\n> User: quoted example only\n"
                "<!-- Assistant: inline example only -->\n\nUser: Actual follow-up.\n"
            )
            status, accepted = import_source(root, request(
                title="Protected examples", content=content,
                source_kind="chatgpt_conversation", file_name="protected.md",
            ))
            self.assertEqual(status, "created")
            read_back = read_source(root, accepted["source"]["source_id"])
            self.assertEqual(read_back["content"].encode("utf-8"), content.encode("utf-8"))
            self.assertEqual(
                [(span["role"], span["locator"]["value"]) for span in read_back["revision"]["speaker_spans"]],
                [("user", "L1-L3"), ("assistant", "L4-L11"), ("user", "L12-L12")],
            )

            status, rejected = import_source(root, request(
                title="Unclosed comment",
                content="User: question\n<!--\nAssistant: example only\n",
                source_kind="chatgpt_conversation", file_name="unclosed-comment.md",
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(rejected["problem"]["code"], "ambiguous_conversation_speaker")

    def test_bom_is_semantic_neutral_for_blank_and_first_conversation_speaker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            for file_name, content in (("bom-only.md", "\ufeff"), ("bom-blank.md", "\ufeff  \n\t")):
                before = tree_bytes(root)
                status, rejected = import_source(root, request(content=content, file_name=file_name))
                self.assertEqual(status, "rejected")
                self.assertEqual(rejected["problem"]["code"], "empty_source")
                self.assertEqual(tree_bytes(root), before)

            for file_name, content, expected in (
                ("bom-prefix.md", "\ufeffUser: Question.\n\nAssistant: Answer.\n", [("user", "L1-L2"), ("assistant", "L3-L3")]),
                ("bom-heading.md", "\ufeff## User\nQuestion.\n\n## Assistant\nAnswer.\n", [("user", "L1-L3"), ("assistant", "L4-L5")]),
            ):
                status, accepted = import_source(root, request(
                    title="BOM conversation", content=content,
                    source_kind="chatgpt_conversation", file_name=file_name,
                ))
                self.assertEqual(status, "created")
                read_back = read_source(root, accepted["source"]["source_id"])
                self.assertEqual(read_back["content"].encode("utf-8"), content.encode("utf-8"))
                self.assertEqual(
                    [(span["role"], span["locator"]["value"]) for span in read_back["revision"]["speaker_spans"]],
                    expected,
                )
                extraction = extraction_input_for_source(root, accepted["source"]["source_id"])
                self.assertFalse(extraction["source"]["content"].startswith("\ufeff"))

    def test_duplicate_is_unchanged_and_update_keeps_both_immutable_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            first_request = request(content="# DNS\n\nVersion one.\n")
            status, first = import_source(root, first_request)
            self.assertEqual(status, "created")
            before = tree_bytes(root)
            status, duplicate = import_source(root, first_request)
            self.assertEqual(status, "unchanged")
            self.assertEqual(duplicate["source"]["revision_count"], 1)
            self.assertEqual(tree_bytes(root), before)

            source_id = first["source"]["source_id"]
            revision_one = first["source"]["current_revision_id"]
            second_request = request(
                content="# DNS\n\nVersion two.\n",
                source_id=source_id,
                expected_revision_id=revision_one,
            )
            status, second = import_source(root, second_request)
            self.assertEqual(status, "updated")
            revision_two = second["source"]["current_revision_id"]
            self.assertNotEqual(revision_one, revision_two)
            self.assertEqual(second["source"]["revision_count"], 2)
            self.assertEqual(read_source(root, source_id, revision_one)["content"], "# DNS\n\nVersion one.\n")
            self.assertEqual(read_source(root, source_id, revision_two)["content"], "# DNS\n\nVersion two.\n")
            self.assertEqual(read_source(root, source_id, revision_two)["revision"]["previous_revision_id"], revision_one)

            status, stale = import_source(root, request(
                content="# DNS\n\nVersion three.\n",
                source_id=source_id,
                expected_revision_id=revision_one,
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(stale["problem"]["code"], "stale_source_revision")
            self.assertEqual(read_source(root, source_id)["revision"]["revision_id"], revision_two)

    def test_a_b_a_history_uses_unique_revision_tokens_and_rejects_first_token_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            _, first = import_source(root, request(content="# DNS\n\nA\n"))
            source_id = first["source"]["source_id"]
            revision_a1 = first["source"]["current_revision_id"]
            _, second = import_source(root, request(
                content="# DNS\n\nB\n", source_id=source_id, expected_revision_id=revision_a1,
            ))
            revision_b = second["source"]["current_revision_id"]
            _, third = import_source(root, request(
                content="# DNS\n\nA\n", source_id=source_id, expected_revision_id=revision_b,
            ))
            revision_a2 = third["source"]["current_revision_id"]

            self.assertEqual(len({revision_a1, revision_b, revision_a2}), 3)
            self.assertEqual(read_source(root, source_id, revision_a2)["content"], "# DNS\n\nA\n")
            self.assertEqual(read_source(root, source_id, revision_a2)["revision"]["previous_revision_id"], revision_b)
            status, stale = import_source(root, request(
                content="# DNS\n\nC\n", source_id=source_id, expected_revision_id=revision_a1,
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(stale["problem"]["code"], "stale_source_revision")
            self.assertEqual(read_source(root, source_id)["revision"]["revision_id"], revision_a2)

    def test_batch_is_all_or_nothing_for_validation_and_commit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            initial_status, _ = import_source(root, request())
            self.assertEqual(initial_status, "created")
            before = tree_bytes(root)

            status, payload = import_sources(root, {
                "schema_version": BATCH_VERSION,
                "sources": [
                    request(title="A", content="# A\n", file_name="a.md"),
                    request(title="Broken", content="   ", file_name="broken.md"),
                ],
            })
            self.assertEqual(status, "rejected")
            self.assertEqual(payload["problem"]["code"], "empty_source")
            self.assertEqual(tree_bytes(root), before)

            def fail_commit(_root: Path, _staged: Path) -> None:
                raise OSError("injected")

            status, payload = import_sources(root, {
                "schema_version": BATCH_VERSION,
                "sources": [request(title="A", content="# A\n", file_name="a.md")],
            }, commit=fail_commit)
            self.assertEqual(status, "failed")
            self.assertEqual(payload["problem"]["code"], "source_transaction_failed")
            self.assertEqual(tree_bytes(root), before)

    def test_malformed_size_path_and_symlink_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "library"
            cases = [
                ({}, "invalid_source_request"),
                (request(content=" "), "empty_source"),
                (request(content="x" * (MAX_SOURCE_BYTES + 1)), "source_too_large"),
                (request(file_name="../private.md"), "invalid_source_locator"),
                (request(source_kind="unknown"), "invalid_source_kind"),
                (request(content="No speaker here.\n", source_kind="chatgpt_conversation"), "conversation_speaker_missing"),
            ]
            for value, expected in cases:
                with self.subTest(expected=expected):
                    status, payload = import_source(root, value)
                    self.assertEqual(status, "rejected")
                    self.assertEqual(payload["problem"]["code"], expected)
            self.assertFalse(root.exists())

            target = parent / "actual"
            target.mkdir()
            root.symlink_to(target, target_is_directory=True)
            status, payload = import_source(root, request())
            self.assertEqual(status, "rejected")
            self.assertEqual(payload["problem"]["code"], "library_root_symlink")

    def test_metadata_and_raw_tampering_make_read_back_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            _, payload = import_source(root, request())
            source = payload["source"]
            revision = source["revisions"][0]
            raw = root / "sources" / source["source_id"] / revision["raw_path"]
            raw.write_text("tampered", encoding="utf-8")
            self.assertIsNone(read_source(root, source["source_id"]))

    def test_legacy_duplicate_revision_ids_fail_closed_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "library"
            _, payload = import_source(root, request(content="# DNS\n\nA\n"))
            source = payload["source"]
            metadata_path = root / "sources" / source["source_id"] / "source.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            duplicate = dict(metadata["revisions"][0])
            duplicate["previous_revision_id"] = duplicate["revision_id"]
            metadata["revisions"].append(duplicate)
            metadata["revision_count"] = 2
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            before = tree_bytes(root)

            self.assertIsNone(read_source(root, source["source_id"]))
            status, rejected = import_source(root, request(
                content="# DNS\n\nB\n", source_id=source["source_id"],
                expected_revision_id=source["current_revision_id"],
            ))
            self.assertEqual(status, "rejected")
            self.assertEqual(rejected["problem"]["code"], "source_revision_identity_ambiguous")
            self.assertEqual(tree_bytes(root), before)


if __name__ == "__main__":
    unittest.main()
