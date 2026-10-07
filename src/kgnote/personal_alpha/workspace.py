"""Transactional materialization for a plugin-free Obsidian learning workspace."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

from .learner_projection import LearnerProjection, project_learner_workspace
from .preview import PersonalAlphaPreview


PERSONAL_ALPHA_WORKSPACE_VERSION = "kgnote.personal-alpha-workspace.v1"
_MANIFEST_PATH = PurePosixPath(".kgnote/manifest.json")
_USER_NOTES_PATH = PurePosixPath("My Notes.md")
_CONTINUE_PATH = PurePosixPath("Continue Here.md")
_WIKILINK = re.compile(
    r"(?<!!)\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|[^\]]+)?\]\]"
)
_CONTINUATION_LINK = re.compile(
    r"^- Resume link:\s*\[\[([^\]|#]+)#([^\]|]+)(?:\|[^\]]+)?\]\]\s*$",
    re.MULTILINE,
)
_CONTINUATION_FIELD = re.compile(
    r"^- (Current note|Current section|Next|Question to revisit):\s*(.*?)\s*$",
    re.MULTILINE,
)
_LINE_RANGE = re.compile(r"^L(\d+)-L(\d+)$")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_BLOCK_ID = re.compile(r"^[A-Za-z0-9-]+$")


class PersonalAlphaMaterializationError(RuntimeError):
    """A scoped materialization failure with an actionable recovery step."""

    def __init__(self, code: str, message: str, action: str):
        self.code = code
        self.action = action
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        return {
            "status": "error",
            "problem_code": self.code,
            "message": str(self),
            "action": self.action,
        }


@dataclass(frozen=True)
class PersonalAlphaMaterializationResult:
    status: str
    workspace_path: str
    entry_note: str
    source_sha256: str
    created_files: int
    updated_files: int
    unchanged_files: int
    read_back: bool
    recovered_interrupted_transaction: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "workspace_path": self.workspace_path,
            "entry_note": self.entry_note,
            "source_sha256": self.source_sha256,
            "created_files": self.created_files,
            "updated_files": self.updated_files,
            "unchanged_files": self.unchanged_files,
            "read_back": self.read_back,
            "recovered_interrupted_transaction": self.recovered_interrupted_transaction,
        }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _frontmatter(fields: Iterable[tuple[str, Any]]) -> str:
    rows = ["---"]
    for key, value in fields:
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, list):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = json.dumps(str(value), ensure_ascii=False)
        rows.append(f"{key}: {rendered}")
    rows.extend(["---", ""])
    return "\n".join(rows)


def _without_suffix(path: str) -> str:
    return path[:-3] if path.casefold().endswith(".md") else path


def _relative_link(from_path: str, to_path: str) -> str:
    source_parent = PurePosixPath(from_path).parent
    target = PurePosixPath(_without_suffix(to_path))
    relative = os.path.relpath(str(target), str(source_parent) or ".")
    return PurePosixPath(relative).as_posix()


def _source_link(from_path: str, source_relative: str, label: str, heading: str | None = None) -> str:
    target = _relative_link(from_path, source_relative)
    anchor = f"#{heading}" if heading else ""
    return f"[[{target}{anchor}|{label}]]"


def _locator_start(value: str) -> int | None:
    match = _LINE_RANGE.fullmatch(value)
    return int(match.group(1)) if match else None


def _source_heading_for_locator(
    projection: Mapping[str, Any], locator: Mapping[str, Any]
) -> str | None:
    """Return a unique enclosing source heading; a line range is never itself a link anchor."""

    line = _locator_start(str(locator.get("value", "")))
    if line is None:
        return None
    structure = list(projection["structure"])
    title_counts: dict[str, int] = {}
    candidates: list[tuple[int, int, str]] = []
    for item in structure:
        title = str(item["title"])
        title_counts[title] = title_counts.get(title, 0) + 1
        heading_line = _locator_start(str(item["source_locator"]["value"]))
        if heading_line is not None and heading_line <= line:
            candidates.append((heading_line, int(item["level"]), title))
    if not candidates:
        return None
    _, _, title = max(candidates, key=lambda item: (item[0], item[1]))
    return title if title_counts[title] == 1 else None


def _source_locator_lines(
    *,
    from_path: str,
    source_relative: str,
    projection: Mapping[str, Any],
    group: Mapping[str, Any],
) -> list[str]:
    locator = str(group["locator"]["value"])
    heading = _source_heading_for_locator(projection, group["locator"])
    if heading:
        return [
            f"Exact source bytes: `{locator}`. "
            + _source_link(from_path, source_relative, f'Open containing section “{heading}”', heading),
            "The link opens the containing heading; the line range identifies the exact excerpt within it.",
        ]
    return [
        f"Exact source bytes: `{locator}`. "
        + _source_link(from_path, source_relative, "Open the source document"),
        "This source has no unique generated heading/block target here. The link opens the document only; "
        "use the line range to find the excerpt. KGnote does not claim exact-line jumping.",
    ]


def _quoted_source_excerpt(value: str) -> str:
    """Keep source markup visible without activating source-owned wikilinks."""

    return value.replace("\\", "\\\\").replace("[[", "\\[\\[").replace("]]", "\\]\\]")


def _evidence_by_id(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["id"]): item for item in payload["evidence"]}


def _concept_note_paths(projection: Mapping[str, Any]) -> dict[str, str]:
    return {str(concept["id"]): str(concept["path"]) for concept in projection["concepts"]}


def _render_entry(payload: Mapping[str, Any], source_relative: str) -> bytes:
    source = payload["source"]
    summary = payload["topic_summary"]
    relations = payload["relations"]
    unresolved = sum(1 for item in relations if item["relation"] is None)
    body = _frontmatter(
        (
            ("kgnote_schema", PERSONAL_ALPHA_WORKSPACE_VERSION),
            ("kgnote_source_id", source["id"]),
            ("kgnote_source_sha256", source["content_sha256"]),
            ("kgnote_generated", True),
            ("tags", ["kgnote/personal-alpha"]),
        )
    )
    lines = [
        body + f"# {source['title']}",
        "",
        "> [!info] Start here",
        "> This page is a generated learning entry. The original Markdown is preserved byte-for-byte.",
        "",
        "## What this material is about",
        "",
        str(summary["text"]),
        "",
        f"Evidence: `{summary['source_locator']['value']}` in "
        + _source_link("Start Here.md", source_relative, "the immutable source"),
        "",
        "## Learning path",
        "",
        "1. [[Structure|See the material's structure]]",
        "2. [[Concepts/Index|Review important concept candidates]]",
        "3. [[Relationships|Read supported and unresolved relationships]]",
        "4. [[Evidence|Inspect exact supporting excerpts]]",
        "5. [[My Notes|Continue with your own notes]]",
        "",
        "## At a glance",
        "",
        f"- {len(payload['structure'])} source sections",
        f"- {len(payload['concepts'])} important concept candidates",
        f"- {len(relations) - unresolved} explicit relationship candidates",
        f"- {unresolved} unresolved associations",
        f"- {len(payload['evidence'])} source-grounded evidence records",
        "",
        "## What still needs review",
        "",
    ]
    lines.extend(f"- {item['message']}" for item in payload["uncertainties"])
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            f"- Source ID: `{source['id']}`",
            f"- Source SHA-256: `{source['content_sha256']}`",
            f"- Extractor: `{payload['extractor_version']}`",
            "- All concepts and relationships are unreviewed candidates unless stated otherwise.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _render_structure(payload: Mapping[str, Any], source_relative: str) -> bytes:
    nodes = payload["structure"]
    node_by_id = {str(item["id"]): item for item in nodes}
    lines = [
        _frontmatter((("kgnote_generated", True), ("kgnote_view", "source_structure")))
        + "# Material structure",
        "",
        "This hierarchy comes only from Markdown headings. It is navigation, not a canonical knowledge graph.",
        "",
    ]
    if not nodes:
        lines.append(
            "- " + _source_link("Structure.md", source_relative, "Read the whole immutable source")
        )
    for node in nodes:
        depth = 0
        parent = node["parent_id"]
        while parent:
            depth += 1
            parent = node_by_id.get(str(parent), {}).get("parent_id")
        label = _source_link(
            "Structure.md", source_relative, str(node["title"]), str(node["title"])
        )
        lines.append(f"{'  ' * depth}- {label} — `{node['source_locator']['value']}`")
    lines.extend(["", "[[Start Here|Back to the learning entry]]", ""])
    return "\n".join(lines).encode("utf-8")


def _render_concept_index(payload: Mapping[str, Any], concept_paths: Mapping[str, str]) -> bytes:
    lines = [
        _frontmatter((("kgnote_generated", True), ("kgnote_view", "concept_index")))
        + "# Important concept candidates",
        "",
        "These are deterministic, source-marked candidates. They are not claims about what you understand.",
        "",
    ]
    for concept in payload["concepts"]:
        path = concept_paths[str(concept["id"])]
        target = _relative_link("Concepts/Index.md", path)
        lines.append(
            f"- [[{target}|{concept['canonical_name_candidate']}]] — "
            f"{concept['mention_count']} marked mention(s); status: unreviewed"
        )
    if not payload["concepts"]:
        lines.append("- No explicit concept signal met the deterministic preview rules.")
    lines.extend(["", "[[../Start Here|Back to the learning entry]]", ""])
    return "\n".join(lines).encode("utf-8")


def _render_concept(
    payload: Mapping[str, Any], concept: Mapping[str, Any], path: str, source_relative: str,
) -> bytes:
    evidence_by_id = _evidence_by_id(payload)
    name = str(concept["canonical_name_candidate"])
    body = _frontmatter(
        (
            ("kgnote_schema", PERSONAL_ALPHA_WORKSPACE_VERSION),
            ("kgnote_concept_candidate_id", concept["id"]),
            ("aliases", concept["aliases"]),
            ("kgnote_review_status", concept["review_status"]),
            ("kgnote_generated", True),
        )
    )
    lines = [
        body + f"# {name}",
        "",
        "> [!warning] Unreviewed concept candidate",
        "> Included because the selected source explicitly marks this term; identity is source-scoped until reviewed.",
        "",
        "## Why it is included",
        "",
        f"Signals: {', '.join(concept['signals'])}. Marked mentions: {concept['mention_count']}.",
        "",
        "## Supporting evidence",
        "",
    ]
    for evidence_id in concept["evidence_ids"]:
        evidence = evidence_by_id[str(evidence_id)]
        evidence_link = _relative_link(path, "Evidence.md")
        source_link = _source_link(path, source_relative, evidence["locator"]["value"])
        lines.extend(
            [
                f"- [[{evidence_link}#{evidence_id}|Evidence {evidence['locator']['value']}]] · {source_link}",
                f"  > {_quoted_source_excerpt(str(evidence['excerpt']))}",
            ]
        )
    lines.extend(["", "[[Index|Back to concepts]]", "[[../Start Here|Back to the learning entry]]", ""])
    return "\n".join(lines).encode("utf-8")


def _relation_phrase(relation: str | None) -> str:
    return {
        "is_a": "is a kind of",
        "part_of": "is part of",
        "requires": "requires",
        "maps_to": "maps to",
        "causes": "causes",
        "contrasts_with": "contrasts with",
        None: "is mentioned near (relation unresolved)",
    }[relation]


def _render_relationships(
    payload: Mapping[str, Any], concept_paths: Mapping[str, str], source_relative: str
) -> bytes:
    evidence_by_id = _evidence_by_id(payload)
    lines = [
        _frontmatter((("kgnote_generated", True), ("kgnote_view", "relationships")))
        + "# Relationships",
        "",
        "Precise relation candidates require an explicit source phrase. Co-mentions remain unresolved.",
        "",
    ]
    for relation in payload["relations"]:
        subject_path = _relative_link("Relationships.md", concept_paths[str(relation["subject_concept_id"])])
        object_path = _relative_link("Relationships.md", concept_paths[str(relation["object_concept_id"])])
        evidence_id = str(relation["evidence_ids"][0])
        evidence = evidence_by_id[evidence_id]
        source_link = _source_link(
            "Relationships.md", source_relative, evidence["locator"]["value"]
        )
        lines.extend(
            [
                f"## {relation['subject_label']} → {relation['object_label']}",
                "",
                f"[[{subject_path}|{relation['subject_label']}]] **{_relation_phrase(relation['relation'])}** "
                f"[[{object_path}|{relation['object_label']}]].",
                "",
                f"- Status: `{relation['review_status']}`; confidence: `{relation['confidence']}`",
                f"- Why included: {relation['rationale']}",
                f"- Support: [[Evidence#{evidence_id}|{evidence['locator']['value']}]] · {source_link}",
                "",
                f"> {_quoted_source_excerpt(str(evidence['excerpt']))}",
                "",
            ]
        )
    if not payload["relations"]:
        lines.extend(["No relationship was invented for this source.", ""])
    lines.extend(["[[Start Here|Back to the learning entry]]", ""])
    return "\n".join(lines).encode("utf-8")


def _render_evidence(payload: Mapping[str, Any], source_relative: str) -> bytes:
    lines = [
        _frontmatter((("kgnote_generated", True), ("kgnote_view", "evidence")))
        + "# Evidence",
        "",
        "Each excerpt is copied from the immutable source and keeps its exact line locator.",
        "",
    ]
    for evidence in payload["evidence"]:
        source_link = _source_link(
            "Evidence.md", source_relative, "Open immutable source"
        )
        lines.extend(
            [
                f"## {evidence['id']}",
                "",
                f"- Locator: `{evidence['locator']['value']}` · {source_link}",
                f"- Kind: `{evidence['evidence_kind']}` · Review: `{evidence['review_status']}`",
                f"- Proposition: {evidence['proposition']}",
                "",
                f"> {_quoted_source_excerpt(str(evidence['excerpt']))}",
                "",
            ]
        )
    lines.extend(["[[Start Here|Back to the learning entry]]", ""])
    return "\n".join(lines).encode("utf-8")


def _render_learner_entry(
    payload: Mapping[str, Any], projection: Mapping[str, Any], source_relative: str
) -> bytes:
    source = projection["source"]
    body = _frontmatter(
        (
            ("kgnote_schema", PERSONAL_ALPHA_WORKSPACE_VERSION),
            ("kgnote_source_id", source["id"]),
            ("kgnote_source_sha256", source["content_sha256"]),
            ("kgnote_projection", projection["schema_version"]),
            ("kgnote_generated", True),
            ("tags", ["kgnote/personal-alpha"]),
        )
    )
    lines = [
        body + f"# {source['title']}",
        "",
        str(projection["summary"]),
        "",
        "> [!question] Learning goal",
        f"> {projection['learning_goal']}",
        "",
        "## Learning path",
        "",
    ]
    lines.extend(
        f"{index}. {step}" for index, step in enumerate(projection["learning_path"], 1)
    )
    lines.extend(
        [
            "",
            "→ " + _source_link("Start Here.md", source_relative, "Start reading the original material"),
            "",
            "## Key concepts",
            "",
        ]
    )
    for concept in projection["concepts"]:
        target = _relative_link("Start Here.md", str(concept["path"]))
        role = str(concept["explanation"]).replace("In this material, ", "", 1)
        lines.append(f"- [[{target}|{concept['label']}]] — {role}")
    if not projection["concepts"]:
        lines.append("- The source does not mark a reusable concept explicitly.")
    lines.extend(["", "## Key relationships", ""])
    for relation in projection["relationships"]:
        subject = _relative_link("Start Here.md", str(relation["subject_path"]))
        object_ = _relative_link("Start Here.md", str(relation["object_path"]))
        if relation["resolved"]:
            lines.append(
                f"- [[{subject}|{relation['subject_label']}]] **{relation['phrase']}** "
                f"[[{object_}|{relation['object_label']}]]."
            )
        else:
            lines.append(
                f"- [[{subject}|{relation['subject_label']}]] and "
                f"[[{object_}|{relation['object_label']}]] are mentioned together, but this source "
                "does not establish a more precise relationship."
            )
    if not projection["relationships"]:
        lines.append("- This source does not establish a relationship between marked concepts.")
    lines.extend(
        [
            "",
            "## Continue",
            "",
            "[[Continue Here|Continue from where you left off]]",
            "",
            "## My notes",
            "",
            "[[My Notes]]",
            "",
            "> [!info]- KGnote details",
            "> Generated learning workspace.",
            "> Detailed provenance and review information is available here only when needed.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _render_learner_concept_index(
    projection: Mapping[str, Any], concept_paths: Mapping[str, str]
) -> bytes:
    lines = [
        _frontmatter((("kgnote_generated", True), ("kgnote_view", "concept_index")))
        + "# Key concepts",
        "",
        "These concepts are grounded in the selected material.",
        "",
    ]
    for concept in projection["concepts"]:
        path = concept_paths[str(concept["id"])]
        target = _relative_link("Concepts/Index.md", path)
        role = str(concept["explanation"]).replace("In this material, ", "", 1)
        lines.append(f"- [[{target}|{concept['label']}]] — {role}")
    if not projection["concepts"]:
        lines.append("- This source does not mark a reusable concept explicitly.")
    lines.extend(["", "[[../Start Here|Back to Start Here]]", ""])
    return "\n".join(lines).encode("utf-8")


def _append_source_evidence_callout(
    lines: list[str],
    *,
    from_path: str,
    source_relative: str,
    projection: Mapping[str, Any],
    group: Mapping[str, Any],
) -> None:
    locator_lines = _source_locator_lines(
        from_path=from_path,
        source_relative=source_relative,
        projection=projection,
        group=group,
    )
    lines.extend(
        [
            "> [!quote]- Source evidence",
            f"> {_quoted_source_excerpt(str(group['excerpt']))}",
            ">",
            *(f"> {line}" for line in locator_lines),
            "",
        ]
    )


def _render_learner_concept(
    projection: Mapping[str, Any],
    concept: Mapping[str, Any],
    path: str,
    source_relative: str,
) -> bytes:
    body = _frontmatter(
        (
            ("kgnote_schema", PERSONAL_ALPHA_WORKSPACE_VERSION),
            ("kgnote_concept_candidate_id", concept["id"]),
            ("aliases", concept["aliases"]),
            ("kgnote_review_status", concept["review_status"]),
            ("kgnote_projection", projection["schema_version"]),
            ("kgnote_generated", True),
        )
    )
    lines = [body + f"# {concept['label']}", "", str(concept["explanation"]), ""]
    if concept["limitation"]:
        lines.extend([str(concept["limitation"]), ""])
    lines.extend(["## In this material", "", str(concept["role"]), "", "## Related concepts", ""])
    for related in concept["related"]:
        target = _relative_link(path, str(related["path"]))
        link = (
            f"[[{target}]]"
            if PurePosixPath(target).name == str(related["label"])
            else f"[[{target}|{related['label']}]]"
        )
        lines.append(f"- {link} — {related['description']}")
    if not concept["related"]:
        lines.append("- This source does not establish a relation to another marked concept.")
    lines.append("")
    for group in concept["evidence_groups"]:
        _append_source_evidence_callout(
            lines,
            from_path=path,
            source_relative=source_relative,
            projection=projection,
            group=group,
        )
    lines.extend(
        [
            "> [!info]- KGnote details",
            f"> Review status: {concept['review_status']}",
            "> Extraction reason and internal provenance are kept here rather than in the learning text.",
            "",
            "[[Index|Back to concepts]] · [[../Start Here|Back to Start Here]]",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _render_learner_relationships(
    projection: Mapping[str, Any],
    concept_paths: Mapping[str, str],
    source_relative: str,
) -> bytes:
    lines = [
        _frontmatter(
            (
                ("kgnote_generated", True),
                ("kgnote_view", "relationships"),
                ("kgnote_projection", projection["schema_version"]),
            )
        )
        + "# Key relationships",
        "",
        "These are source-linked relationship candidates. Unreviewed candidates remain visibly provisional.",
        "",
    ]
    for relation in projection["relationships"]:
        subject = _relative_link(
            "Relationships.md", concept_paths[str(relation["subject_id"])]
        )
        object_ = _relative_link("Relationships.md", concept_paths[str(relation["object_id"])])
        arrow = "→" if relation["resolved"] else "↔"
        lines.extend(
            [
                f"## {relation['subject_label']} {arrow} {relation['object_label']}",
                "",
            ]
        )
        if relation["resolved"]:
            lines.append(
                f"[[{subject}|{relation['subject_label']}]] **{relation['phrase']}** "
                f"[[{object_}|{relation['object_label']}]]."
            )
        else:
            lines.extend(
                [
                    f"[[{subject}|{relation['subject_label']}]] and "
                    f"[[{object_}|{relation['object_label']}]] are mentioned together.",
                    "",
                    (
                        f"The source contains the candidate phrase **{relation['phrase']}**, but it is "
                        "still unreviewed, so KGnote does not present it as settled learner truth."
                        if relation["relation"] is not None
                        else "The source does **not** establish a more precise relationship, so KGnote leaves this unresolved."
                    ),
                ]
            )
        lines.append("")
        for group in relation["evidence_groups"]:
            _append_source_evidence_callout(
                lines,
                from_path="Relationships.md",
                source_relative=source_relative,
                projection=projection,
                group=group,
            )
    if not projection["relationships"]:
        lines.extend(
            [
                "This source does not establish a relationship between marked concepts.",
                "",
            ]
        )
    lines.extend(["[[Start Here|Back to Start Here]]", ""])
    return "\n".join(lines).encode("utf-8")


def _render_learner_evidence(
    projection: Mapping[str, Any], source_relative: str
) -> bytes:
    lines = [
        _frontmatter(
            (
                ("kgnote_generated", True),
                ("kgnote_view", "source_evidence"),
                ("kgnote_projection", projection["schema_version"]),
            )
        )
        + "# Source evidence",
        "",
        "Reference excerpts from the original material. Open this page when you want to verify a learning note.",
        "",
    ]
    for group in projection["evidence_groups"]:
        locator_lines = _source_locator_lines(
            from_path="Evidence.md",
            source_relative=source_relative,
            projection=projection,
            group=group,
        )
        lines.extend(
            [
                f"## Source at {group['locator']['value']}",
                "",
                f"> {_quoted_source_excerpt(str(group['excerpt']))}",
                "",
                *locator_lines,
                "",
                "> [!info]- KGnote details",
                f"> Evidence records: {', '.join(group['evidence_ids'])}",
                f"> Review status: {', '.join(group['review_statuses'])}",
                "",
            ]
        )
    lines.extend(["[[Start Here|Back to Start Here]]", ""])
    return "\n".join(lines).encode("utf-8")


def _artifact_bytes(
    preview: PersonalAlphaPreview,
) -> tuple[dict[str, bytes], bytes, LearnerProjection]:
    payload = preview.payload
    source_path = Path(str(payload["source"]["selected_path"]))
    try:
        source_bytes = source_path.read_bytes()
    except OSError as error:
        raise PersonalAlphaMaterializationError(
            "source_read_failed",
            "The selected source could not be read during materialization.",
            "Restore access to the same source file, then rerun preview and apply.",
        ) from error
    if _sha256(source_bytes) != payload["source"]["content_sha256"]:
        raise PersonalAlphaMaterializationError(
            "source_changed_after_preview",
            "The selected source changed after the preview was built.",
            "Rerun the preview so the planned workspace is bound to the current source bytes.",
        )
    root = PurePosixPath(str(payload["planned_artifacts"]["workspace_root"]))
    planned = payload["planned_artifacts"]
    source_relative = PurePosixPath(str(planned["immutable_source"])).relative_to(root).as_posix()
    projected = project_learner_workspace(payload)
    projection = projected.model
    concept_paths = _concept_note_paths(projection)
    artifacts: dict[str, bytes] = {
        "Start Here.md": _render_learner_entry(payload, projection, source_relative),
        "Structure.md": _render_structure(payload, source_relative),
        "Concepts/Index.md": _render_learner_concept_index(projection, concept_paths),
        "Relationships.md": _render_learner_relationships(
            projection, concept_paths, source_relative
        ),
        "Evidence.md": _render_learner_evidence(projection, source_relative),
        source_relative: source_bytes,
    }
    for concept in projection["concepts"]:
        path = concept_paths[str(concept["id"])]
        artifacts[path] = _render_learner_concept(
            projection, concept, path, source_relative
        )
    return artifacts, source_bytes, projected


def _manifest_bytes(
    preview: PersonalAlphaPreview,
    artifacts: Mapping[str, bytes],
    learner_projection: LearnerProjection,
) -> bytes:
    payload = preview.payload
    projection = learner_projection.model
    manifest = {
        "schema_version": PERSONAL_ALPHA_WORKSPACE_VERSION,
        "source": {
            "id": payload["source"]["id"],
            "content_sha256": payload["source"]["content_sha256"],
            "immutable_source": str(
                PurePosixPath(str(payload["planned_artifacts"]["immutable_source"])).relative_to(
                    PurePosixPath(str(payload["planned_artifacts"]["workspace_root"]))
                )
            ),
        },
        "extractor_version": payload["extractor_version"],
        "learner_projection_version": projection["schema_version"],
        "workspace_version": PERSONAL_ALPHA_WORKSPACE_VERSION,
        "entry_note": "Start Here.md",
        "managed_files": [
            {"path": path, "sha256": _sha256(content)}
            for path, content in sorted(artifacts.items())
        ],
        "user_owned_paths": [str(_USER_NOTES_PATH), str(_CONTINUE_PATH)],
        "projected_concept_paths": {
            str(item["id"]): str(item["path"]) for item in projection["concepts"]
        },
        "record_ids": {
            "concepts": [item["id"] for item in payload["concepts"]],
            "relations": [item["id"] for item in payload["relations"]],
            "evidence": [item["id"] for item in payload["evidence"]],
        },
        "uncertainty_codes": [item["code"] for item in payload["uncertainties"]],
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise PersonalAlphaMaterializationError(
            "manifest_path_invalid",
            "A generated manifest contains an unsafe managed path.",
            "Do not repair the manifest by hand; preserve the workspace and report the conflict.",
        )
    return path


def _load_manifest(workspace: Path) -> dict[str, Any]:
    path = workspace / Path(*_MANIFEST_PATH.parts)
    if path.is_symlink() or not path.is_file():
        raise PersonalAlphaMaterializationError(
            "workspace_manifest_missing",
            "The existing target is not a complete KGnote Personal Alpha workspace.",
            "Choose a different destination or move the conflicting folder aside yourself.",
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PersonalAlphaMaterializationError(
            "workspace_manifest_invalid",
            "The existing workspace manifest cannot be read safely.",
            "Preserve the folder and choose a different destination; do not delete it automatically.",
        ) from error
    if manifest.get("schema_version") != PERSONAL_ALPHA_WORKSPACE_VERSION:
        raise PersonalAlphaMaterializationError(
            "workspace_version_unsupported",
            "The existing target uses an unsupported workspace version.",
            "Preserve it and use a different destination until an explicit migration exists.",
        )
    return manifest


def _reject_symlinks(root: Path) -> None:
    for current, directories, files in os.walk(root):
        current_path = Path(current)
        for name in directories + files:
            if (current_path / name).is_symlink():
                raise PersonalAlphaMaterializationError(
                    "workspace_symlink_unsafe",
                    "The existing workspace contains a symlink, so transactional copying was refused.",
                    "Replace the symlink with a regular file or choose a separate destination.",
                )


def _validate_managed_files(workspace: Path, manifest: Mapping[str, Any]) -> None:
    rows = manifest.get("managed_files")
    if not isinstance(rows, list):
        raise PersonalAlphaMaterializationError(
            "workspace_manifest_invalid",
            "The existing workspace manifest has no managed-file inventory.",
            "Preserve the folder and choose a different destination.",
        )
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise PersonalAlphaMaterializationError(
                "workspace_manifest_invalid",
                "The managed-file inventory is malformed.",
                "Preserve the folder and choose a different destination.",
            )
        relative = _safe_relative(str(row["path"]))
        path = workspace / Path(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise PersonalAlphaMaterializationError(
                "managed_file_conflict",
                f"A KGnote-managed file is missing or unsafe: {relative.as_posix()}.",
                "Preserve your workspace; restore the generated file or choose a new destination.",
            )
        if _sha256(path.read_bytes()) != row.get("sha256"):
            raise PersonalAlphaMaterializationError(
                "managed_file_conflict",
                f"A KGnote-managed file has local edits: {relative.as_posix()}.",
                "Move your edits to My Notes.md or another user-owned file before rerunning.",
            )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _remove_scoped(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _transaction_journal(source_id: str, workspace_relative: PurePosixPath, state: str) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": "kgnote.personal-alpha-transaction.v1",
                "source_id": source_id,
                "target": workspace_relative.as_posix(),
                "state": state,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _recover_transaction(
    transaction: Path,
    target: Path,
    *,
    source_id: str,
    workspace_relative: PurePosixPath,
) -> bool:
    if not transaction.exists():
        return False
    if transaction.is_symlink() or not transaction.is_dir():
        raise PersonalAlphaMaterializationError(
            "transaction_path_conflict",
            "The reserved KGnote transaction path is not a safe directory.",
            "Preserve it for inspection and choose a different destination.",
        )
    journal_path = transaction / "journal.json"
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PersonalAlphaMaterializationError(
            "transaction_journal_invalid",
            "An interrupted transaction exists without a valid recovery journal.",
            "Preserve the reserved transaction folder for inspection; do not delete it automatically.",
        ) from error
    if (
        journal.get("schema_version") != "kgnote.personal-alpha-transaction.v1"
        or journal.get("source_id") != source_id
        or journal.get("target") != workspace_relative.as_posix()
        or journal.get("state") not in {"staging", "prepared"}
    ):
        raise PersonalAlphaMaterializationError(
            "transaction_journal_conflict",
            "The interrupted transaction journal does not match this source and workspace.",
            "Preserve it for inspection and choose a different destination.",
        )
    staged = transaction / "staged"
    backup = transaction / "backup"
    recovered = True
    if backup.exists():
        if target.exists():
            try:
                read_back_learning_workspace(target)
            except PersonalAlphaMaterializationError:
                failed = transaction / "failed-new"
                _remove_scoped(failed)
                os.replace(target, failed)
                os.replace(backup, target)
                _remove_scoped(failed)
            else:
                _remove_scoped(backup)
        else:
            os.replace(backup, target)
    _remove_scoped(staged)
    _remove_scoped(transaction)
    return recovered


def read_back_learning_workspace(workspace: str | Path) -> dict[str, Any]:
    """Validate generated files, immutable source bytes, IDs, and all local wikilinks."""

    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise PersonalAlphaMaterializationError(
            "workspace_not_readable",
            "The generated workspace cannot be reopened as a regular directory.",
            "Preserve the destination and rerun only after checking its filesystem state.",
        )
    manifest = _load_manifest(root)
    _reject_symlinks(root)
    _validate_managed_files(root, manifest)
    source = manifest.get("source")
    if not isinstance(source, Mapping) or not isinstance(source.get("immutable_source"), str):
        raise PersonalAlphaMaterializationError(
            "workspace_manifest_invalid",
            "The manifest has no immutable source reference.",
            "Preserve the workspace and choose a different destination.",
        )
    source_relative = _safe_relative(str(source["immutable_source"]))
    source_path = root / Path(*source_relative.parts)
    if _sha256(source_path.read_bytes()) != source.get("content_sha256"):
        raise PersonalAlphaMaterializationError(
            "immutable_source_drift",
            "The workspace source snapshot no longer matches its registered digest.",
            "Preserve the workspace for inspection; do not regenerate over it.",
        )
    record_ids = manifest.get("record_ids", {})
    for collection in ("concepts", "relations", "evidence"):
        values = record_ids.get(collection)
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise PersonalAlphaMaterializationError(
                "duplicate_record_identity",
                f"The workspace contains duplicate or malformed {collection} identities.",
                "Preserve the workspace and rerun in a separate destination.",
            )
    user_owned_paths = manifest.get("user_owned_paths")
    if not isinstance(user_owned_paths, list):
        raise PersonalAlphaMaterializationError(
            "workspace_manifest_invalid",
            "The manifest has no user-owned path inventory.",
            "Preserve the workspace and choose a different destination.",
        )
    for value in user_owned_paths:
        if not isinstance(value, str):
            raise PersonalAlphaMaterializationError(
                "workspace_manifest_invalid",
                "The user-owned path inventory is malformed.",
                "Preserve the workspace and choose a different destination.",
            )
        relative = _safe_relative(value)
        path = root / Path(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise PersonalAlphaMaterializationError(
                "user_owned_file_missing",
                f"A user-owned learning note is missing or unsafe: {relative.as_posix()}.",
                "Restore the note as a regular file or choose a separate destination.",
            )
    checked_links = 0
    for row in manifest["managed_files"]:
        relative = _safe_relative(str(row["path"]))
        if relative.suffix.casefold() != ".md":
            continue
        if relative == source_relative:
            continue
        note_path = root / Path(*relative.parts)
        text = note_path.read_text(encoding="utf-8")
        for match in _WIKILINK.finditer(text):
            target_text = match.group(1)
            target = PurePosixPath(target_text)
            if target.is_absolute():
                raise PersonalAlphaMaterializationError(
                    "generated_link_invalid",
                    f"A generated note contains an absolute wikilink: {relative.as_posix()}.",
                    "Report the generator defect; do not repair generated notes by hand.",
                )
            resolved = PurePosixPath(os.path.normpath(str(relative.parent / target)))
            if any(part == ".." for part in resolved.parts):
                raise PersonalAlphaMaterializationError(
                    "generated_link_invalid",
                    f"A generated wikilink escapes the workspace: {relative.as_posix()}.",
                    "Report the generator defect.",
                )
            candidates = [
                root / Path(*resolved.parts),
                root / Path(*(resolved.parts[:-1] + (resolved.name + ".md",))),
            ]
            linked_path = next((candidate for candidate in candidates if candidate.is_file()), None)
            if linked_path is None:
                raise PersonalAlphaMaterializationError(
                    "generated_link_missing",
                    f"A generated wikilink cannot be reopened: {target_text} from {relative.as_posix()}.",
                    "Report the generator defect; the workspace was not verified.",
                )
            anchor = match.group(2)
            if anchor:
                linked_text = linked_path.read_text(encoding="utf-8")
                if anchor.startswith("^"):
                    block_id = anchor[1:]
                    anchor_resolves = bool(
                        _BLOCK_ID.fullmatch(block_id)
                        and re.search(
                            rf"(?:^|\s)\^{re.escape(block_id)}\s*$",
                            linked_text,
                            re.MULTILINE,
                        )
                    )
                else:
                    headings = {
                        heading.group(1).strip()
                        for heading in _MARKDOWN_HEADING.finditer(linked_text)
                    }
                    anchor_resolves = anchor in headings
                if not anchor_resolves:
                    raise PersonalAlphaMaterializationError(
                        "generated_link_anchor_missing",
                        f"A generated wikilink anchor cannot be reopened: {anchor} from {relative.as_posix()}.",
                        "Report the generator defect; the workspace was not verified.",
                    )
            checked_links += 1
    entry = root / str(manifest.get("entry_note", ""))
    if not entry.is_file():
        raise PersonalAlphaMaterializationError(
            "entry_note_missing",
            "The generated learning entry note is missing.",
            "Preserve the workspace and rerun in a separate destination.",
        )
    return {
        "status": "loaded",
        "workspace_path": str(root.resolve()),
        "entry_note": str(entry.resolve()),
        "source_sha256": source["content_sha256"],
        "managed_files": len(manifest["managed_files"]),
        "checked_links": checked_links,
        "record_counts": {key: len(value) for key, value in record_ids.items()},
    }


def _resolve_note_path(root: Path, from_relative: PurePosixPath, target_text: str) -> Path:
    target = PurePosixPath(target_text)
    if target.is_absolute():
        raise PersonalAlphaMaterializationError(
            "continuation_target_invalid",
            "The manual continuation link uses an absolute note path.",
            "Use a workspace-relative Obsidian wikilink to a note heading or block.",
        )
    resolved = PurePosixPath(os.path.normpath(str(from_relative.parent / target)))
    if any(part == ".." for part in resolved.parts):
        raise PersonalAlphaMaterializationError(
            "continuation_target_invalid",
            "The manual continuation link escapes the learning workspace.",
            "Link to a note inside this generated workspace.",
        )
    candidates = [
        root / Path(*resolved.parts),
        root / Path(*(resolved.parts[:-1] + (resolved.name + ".md",))),
    ]
    note_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if note_path is None:
        raise PersonalAlphaMaterializationError(
            "continuation_target_missing",
            f"The recorded continuation note cannot be reopened: {target_text}.",
            "Update Continue Here.md to link to an existing note heading or block.",
        )
    return note_path


def read_back_manual_continuation(workspace: str | Path) -> dict[str, str]:
    """Validate one user-recorded exact note heading/block without inferring activity."""

    root = Path(workspace).expanduser().resolve()
    read_back_learning_workspace(root)
    continuation = root / str(_CONTINUE_PATH)
    text = continuation.read_text(encoding="utf-8")
    link = _CONTINUATION_LINK.search(text)
    fields = {name: value.strip() for name, value in _CONTINUATION_FIELD.findall(text)}
    required = ("Current note", "Current section", "Next", "Question to revisit")
    if link is None or any(not fields.get(name) for name in required):
        raise PersonalAlphaMaterializationError(
            "continuation_not_recorded",
            "Continue Here is still an unconfigured starter or has an empty required field.",
            "Record a Resume link, current note, current section, next action, and question before stopping.",
        )
    target_text, anchor = link.groups()
    if fields["Current note"] != target_text or fields["Current section"] != anchor:
        raise PersonalAlphaMaterializationError(
            "continuation_fields_mismatch",
            "The Resume link does not match the recorded current note and section.",
            "Make the Resume link target equal the Current note and Current section fields.",
        )
    note_path = _resolve_note_path(root, _CONTINUE_PATH, target_text)
    note_text = note_path.read_text(encoding="utf-8")
    if anchor.startswith("^"):
        block_id = anchor[1:]
        resolved = bool(
            _BLOCK_ID.fullmatch(block_id)
            and re.search(rf"(?:^|\s)\^{re.escape(block_id)}\s*$", note_text, re.MULTILINE)
        )
        target_kind = "block"
    else:
        headings = {match.group(1).strip() for match in _MARKDOWN_HEADING.finditer(note_text)}
        resolved = anchor in headings
        target_kind = "heading"
    if not resolved:
        raise PersonalAlphaMaterializationError(
            "continuation_anchor_stale",
            f"The recorded continuation {target_kind} no longer resolves: {anchor}.",
            "Choose an existing heading/block in the recorded note and update Continue Here.md.",
        )
    return {
        "status": "recorded",
        "note": target_text,
        "section": anchor,
        "target_kind": target_kind,
        "target_path": str(note_path.resolve()),
        "next": fields["Next"],
        "question": fields["Question to revisit"],
    }


def materialize_learning_workspace(
    preview: PersonalAlphaPreview,
    destination: str | Path,
    *,
    failure_injector: Callable[[str], None] | None = None,
) -> PersonalAlphaMaterializationResult:
    """Atomically create or update one generated workspace under an explicit destination."""

    if preview.payload.get("status") != "planned" or preview.payload.get("writes_performed") != 0:
        raise PersonalAlphaMaterializationError(
            "preview_not_applicable",
            "Only a current zero-write Personal Alpha preview can be materialized.",
            "Build a fresh preview from the selected Markdown source.",
        )
    destination_path = Path(destination).expanduser()
    if destination_path.is_symlink() or not destination_path.is_dir():
        raise PersonalAlphaMaterializationError(
            "destination_not_directory",
            "The destination must already exist as a regular, non-symlink directory.",
            "Create or select a disposable Obsidian vault/directory, then rerun.",
        )
    destination_path = destination_path.resolve()
    workspace_relative = _safe_relative(str(preview.payload["planned_artifacts"]["workspace_root"]))
    target = destination_path / Path(*workspace_relative.parts)
    source_id = str(preview.payload["source"]["id"])
    transaction = destination_path / f".kgnote-transaction-{source_id[-16:]}"
    recovered = _recover_transaction(
        transaction,
        target,
        source_id=source_id,
        workspace_relative=workspace_relative,
    )
    artifacts, _, learner_projection = _artifact_bytes(preview)
    manifest_bytes = _manifest_bytes(preview, artifacts, learner_projection)
    desired = dict(artifacts)
    desired[_MANIFEST_PATH.as_posix()] = manifest_bytes
    old_manifest: dict[str, Any] | None = None
    old_hashes: dict[str, str] = {}
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise PersonalAlphaMaterializationError(
                "workspace_target_conflict",
                "The planned workspace path is already occupied by a non-workspace target.",
                "Choose a different destination; KGnote will not overwrite it.",
            )
        _reject_symlinks(target)
        old_manifest = _load_manifest(target)
        if old_manifest.get("source", {}).get("id") != source_id:
            raise PersonalAlphaMaterializationError(
                "workspace_source_conflict",
                "The existing workspace belongs to a different source identity.",
                "Choose a different destination; KGnote will not merge it implicitly.",
            )
        _validate_managed_files(target, old_manifest)
        old_hashes = {str(row["path"]): str(row["sha256"]) for row in old_manifest["managed_files"]}
        old_managed = set(old_hashes)
        for relative in sorted(set(artifacts) - old_managed):
            candidate = target / Path(*_safe_relative(relative).parts)
            if candidate.exists() or candidate.is_symlink():
                raise PersonalAlphaMaterializationError(
                    "user_owned_path_collision",
                    f"A new generated path would overwrite a user-owned file: {relative}.",
                    "Move or rename that file yourself, then rerun; KGnote will not overwrite it.",
                )
        existing_manifest_bytes = (target / Path(*_MANIFEST_PATH.parts)).read_bytes()
        if existing_manifest_bytes == manifest_bytes and all(
            (target / Path(*PurePosixPath(path).parts)).read_bytes() == content
            for path, content in artifacts.items()
        ):
            audit = read_back_learning_workspace(target)
            return PersonalAlphaMaterializationResult(
                status="unchanged",
                workspace_path=str(target),
                entry_note=audit["entry_note"],
                source_sha256=str(audit["source_sha256"]),
                created_files=0,
                updated_files=0,
                unchanged_files=len(desired),
                read_back=True,
                recovered_interrupted_transaction=recovered,
            )
    transaction.mkdir(mode=0o700)
    staged = transaction / "staged"
    backup = transaction / "backup"
    original_existed = target.exists()
    committed = False
    try:
        _write_file(
            transaction / "journal.json",
            _transaction_journal(source_id, workspace_relative, "staging"),
        )
        if original_existed:
            shutil.copytree(target, staged)
            old_managed = {str(row["path"]) for row in old_manifest["managed_files"]}
            for old_path in sorted(old_managed - set(artifacts)):
                _remove_scoped(staged / Path(*_safe_relative(old_path).parts))
        else:
            staged.mkdir(parents=True)
            _write_file(
                staged / str(_USER_NOTES_PATH),
                (
                    "# My notes\n\n"
                    "This file is yours. KGnote will preserve it on generated workspace updates.\n"
                ).encode("utf-8"),
            )
        if not (staged / str(_CONTINUE_PATH)).exists():
            _write_file(
                staged / str(_CONTINUE_PATH),
                (
                    "# Continue Here\n\n"
                    "This file is yours. KGnote preserves its bytes and never infers progress from recency, "
                    "clicks, or time.\n\n"
                    "Before you stop, add one exact Obsidian heading or block link below and fill every field. "
                    "After reopening, use Start Here → Continue Here → Resume link.\n\n"
                    "Heading example: `[[Concepts/Port#Related concepts|Resume at my recorded position]]`  \n"
                    "Block example: `[[Source/lesson#^stable-block-id|Resume at my recorded position]]`\n\n"
                    "## Current position\n\n"
                    "- Resume link:\n"
                    "- Current note:\n"
                    "- Current section:\n"
                    "- Next:\n"
                    "- Question to revisit:\n"
                ).encode("utf-8"),
            )
        for relative, content in sorted(artifacts.items()):
            _write_file(staged / Path(*_safe_relative(relative).parts), content)
        _write_file(staged / Path(*_MANIFEST_PATH.parts), manifest_bytes)
        read_back_learning_workspace(staged)
        _write_file(
            transaction / "journal.json",
            _transaction_journal(source_id, workspace_relative, "prepared"),
        )
        if failure_injector:
            failure_injector("after_stage")
        target.parent.mkdir(parents=True, exist_ok=True)
        if original_existed:
            os.replace(target, backup)
            if failure_injector:
                failure_injector("after_backup")
        os.replace(staged, target)
        committed = True
        if failure_injector:
            failure_injector("after_commit")
        audit = read_back_learning_workspace(target)
        if failure_injector:
            failure_injector("before_cleanup")
        _remove_scoped(backup)
        _remove_scoped(transaction)
        _fsync_directory(target.parent)
    except Exception as error:
        try:
            if backup.exists():
                failed = transaction / "failed-new"
                _remove_scoped(failed)
                if target.exists():
                    os.replace(target, failed)
                os.replace(backup, target)
                _remove_scoped(failed)
            elif committed and target.exists() and not original_existed:
                _remove_scoped(target)
            _remove_scoped(transaction)
        except OSError as rollback_error:
            raise PersonalAlphaMaterializationError(
                "rollback_failed",
                "Materialization failed and automatic rollback could not restore a known state.",
                "Stop using this destination and preserve it for recovery inspection.",
            ) from rollback_error
        if isinstance(error, PersonalAlphaMaterializationError):
            raise
        raise PersonalAlphaMaterializationError(
            "materialization_failed_rolled_back",
            "Materialization failed; KGnote rolled the destination back to its previous complete state.",
            "Correct the reported filesystem condition and rerun the same preview.",
        ) from error
    created = sum(1 for path in desired if path not in old_hashes)
    updated = sum(
        1 for path, content in desired.items()
        if path in old_hashes and old_hashes[path] != _sha256(content)
    )
    unchanged = len(desired) - created - updated
    return PersonalAlphaMaterializationResult(
        status="applied",
        workspace_path=str(target),
        entry_note=str(Path(audit["entry_note"])),
        source_sha256=str(audit["source_sha256"]),
        created_files=created,
        updated_files=updated,
        unchanged_files=unchanged,
        read_back=True,
        recovered_interrupted_transaction=recovered,
    )
