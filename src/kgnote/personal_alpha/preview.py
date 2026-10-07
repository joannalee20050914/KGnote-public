"""Build a source-grounded, zero-write Personal Alpha workspace preview.

This module deliberately performs no external I/O beyond reading the one explicit
Markdown path. It does not call a model, create a vault, or promote candidates to
reviewed canonical knowledge.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


PERSONAL_ALPHA_PREVIEW_VERSION = "kgnote.personal-alpha-preview.v1"
EXTRACTOR_VERSION = "kgnote.personal-alpha-deterministic.v1"
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_CONCEPTS = 16
MAX_RELATIONS = 24

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_WIKILINK = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
_BOLD = re.compile(r"\*\*([^*\n]{1,80})\*\*|__([^_\n]{1,80})__")
_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]{1,80})`(?!`)")
_DEFINITION = re.compile(
    r"^\s*(?:(?:[-*+]\s+)|(?:\d+[.)]\s+))?"
    r"(?:\*\*|__)?"
    r"([A-Z][A-Za-z0-9 +_./-]{1,48}|[\u3400-\u9fff][\u3400-\u9fffA-Za-z0-9 ·_./-]{1,28})"
    r"(?:\*\*|__)?\s*(?::|：|\s[-–—]\s)"
)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_SPACE = re.compile(r"\s+")

_GENERIC_LABELS = {
    "introduction",
    "overview",
    "summary",
    "example",
    "examples",
    "notes",
    "steps",
    "conclusion",
    "介紹",
    "概覽",
    "摘要",
    "範例",
    "步驟",
    "結論",
}


class PersonalAlphaPreviewError(ValueError):
    """An actionable preview failure that never embeds source content."""

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
class PersonalAlphaPreview:
    """Serializable preview payload plus its learner-facing Markdown rendering."""

    payload: Mapping[str, Any]
    markdown: str

    def as_dict(self) -> dict[str, Any]:
        return json.loads(
            json.dumps(self.payload, ensure_ascii=False, sort_keys=True)
        )


@dataclass(frozen=True)
class _Mention:
    name: str
    normalized_name: str
    line: int
    start: int
    end: int
    signal: str
    excerpt: str


def _digest(*parts: str, length: int = 24) -> str:
    joined = "\0".join(parts).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:length]


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _SPACE.sub(" ", normalized.strip())
    return normalized.casefold()


def _clean_label(value: str) -> str | None:
    label = unicodedata.normalize("NFKC", value)
    label = re.sub(r"[*_~]", "", label)
    label = _SPACE.sub(" ", label.strip(" \t\r\n.,;:：()[]{}<>「」『』\"'"))
    if not 2 <= len(label) <= 64:
        return None
    if label.casefold() in _GENERIC_LABELS:
        return None
    if label.startswith(("http://", "https://")):
        return None
    if len(label.split()) > 8:
        return None
    if label.endswith(("。", "！", "？", ".", "!", "?")):
        return None
    return label


def _slug(value: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    pieces: list[str] = []
    previous_dash = False
    for character in normalized:
        if character.isalnum():
            pieces.append(character)
            previous_dash = False
        elif not previous_dash and pieces:
            pieces.append("-")
            previous_dash = True
    slug = "".join(pieces).strip("-")
    return slug[:64] or fallback


def _safe_filename(value: str, fallback: str) -> str:
    label = re.sub(r"[\\/:*?\"<>|]", "-", value).strip(" .")
    return label[:96] or fallback


def _read_source(path: str | Path) -> tuple[Path, bytes, str]:
    source_path = Path(path).expanduser()
    if not source_path.exists():
        raise PersonalAlphaPreviewError(
            "source_not_found",
            "The selected Markdown source does not exist.",
            "Choose one existing .md file and rerun the preview.",
        )
    if source_path.is_symlink() or not source_path.is_file():
        raise PersonalAlphaPreviewError(
            "source_not_regular_file",
            "The selected source must be a regular, non-symlink file.",
            "Select the real Markdown file rather than a directory or symlink.",
        )
    if source_path.suffix.casefold() != ".md":
        raise PersonalAlphaPreviewError(
            "source_extension_not_markdown",
            "The selected source is not a .md file.",
            "Export or select one UTF-8 Markdown file.",
        )
    try:
        source_bytes = source_path.read_bytes()
    except OSError as error:
        raise PersonalAlphaPreviewError(
            "source_read_failed",
            "The selected Markdown source could not be read.",
            "Check file permissions and retry without moving the file.",
        ) from error
    if len(source_bytes) > MAX_SOURCE_BYTES:
        raise PersonalAlphaPreviewError(
            "source_too_large",
            f"The selected source exceeds the {MAX_SOURCE_BYTES}-byte Personal Alpha limit.",
            "Select a smaller single learning Markdown file for this workflow.",
        )
    try:
        content = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise PersonalAlphaPreviewError(
            "source_not_utf8",
            "The selected Markdown source is not valid UTF-8.",
            "Save a UTF-8 copy, then select that copy.",
        ) from error
    if not content.strip():
        raise PersonalAlphaPreviewError(
            "source_empty",
            "The selected Markdown source contains no readable text.",
            "Choose a non-empty learning Markdown file.",
        )
    return source_path.resolve(), source_bytes, content


def _markdown_lines(content: str) -> tuple[list[str], set[int], set[int]]:
    lines = content.splitlines()
    ignored: set[int] = set()
    code_lines: set[int] = set()
    if lines and lines[0].strip() == "---":
        ignored.add(1)
        for index in range(1, len(lines)):
            ignored.add(index + 1)
            if lines[index].strip() == "---":
                break
    fence: str | None = None
    for number, line in enumerate(lines, 1):
        match = _FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            code_lines.add(number)
            fence = None if fence == marker else marker
            continue
        if fence is not None:
            code_lines.add(number)
    return lines, ignored, code_lines


def _extract_structure(
    source_id: str, lines: list[str], ignored: set[int], code_lines: set[int]
) -> tuple[list[dict[str, Any]], str | None]:
    nodes: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    document_title: str | None = None
    for number, line in enumerate(lines, 1):
        if number in ignored or number in code_lines:
            continue
        match = _HEADING.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = re.sub(r"\s+#+$", "", match.group(2)).strip()
        if not title:
            continue
        if document_title is None and level == 1:
            document_title = title
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_id = stack[-1][1] if stack else None
        node_id = "section_" + _digest(source_id, str(number), str(level), title)
        nodes.append(
            {
                "id": node_id,
                "title": title,
                "level": level,
                "parent_id": parent_id,
                "organization_relation": "subsection_of" if parent_id else "document_section",
                "knowledge_edge_created": False,
                "source_locator": {"kind": "line_range", "value": f"L{number}-L{number}"},
            }
        )
        stack.append((level, node_id))
    return nodes, document_title


def _record_mention(
    found: list[_Mention], *, value: str, line_number: int, start: int, end: int,
    signal: str, excerpt: str,
) -> None:
    label = _clean_label(value)
    if label is None:
        return
    normalized = _normalize_name(label)
    if any(item.normalized_name == normalized and item.start == start for item in found):
        return
    found.append(_Mention(label, normalized, line_number, start, end, signal, excerpt.strip()))


def _extract_mentions(
    lines: list[str], ignored: set[int], code_lines: set[int]
) -> list[_Mention]:
    mentions: list[_Mention] = []
    for number, line in enumerate(lines, 1):
        if number in ignored or number in code_lines or _HEADING.match(line):
            continue
        per_line: list[_Mention] = []
        for match in _WIKILINK.finditer(line):
            display = match.group(2) or match.group(1)
            _record_mention(
                per_line, value=display, line_number=number, start=match.start(), end=match.end(),
                signal="wikilink", excerpt=line,
            )
        for match in _BOLD.finditer(line):
            value = match.group(1) or match.group(2)
            _record_mention(
                per_line, value=value, line_number=number, start=match.start(), end=match.end(),
                signal="emphasis", excerpt=line,
            )
        for match in _INLINE_CODE.finditer(line):
            _record_mention(
                per_line, value=match.group(1), line_number=number, start=match.start(), end=match.end(),
                signal="inline_code", excerpt=line,
            )
        definition = _DEFINITION.match(line)
        if definition:
            _record_mention(
                per_line, value=definition.group(1), line_number=number,
                start=definition.start(1), end=definition.end(1), signal="definition_label", excerpt=line,
            )
        mentions.extend(per_line)
    return mentions


def _signal_score(signal: str) -> int:
    return {
        "wikilink": 5,
        "definition_label": 4,
        "emphasis": 3,
        "inline_code": 2,
    }[signal]


def _build_concepts(
    source_id: str, space: str, mentions: list[_Mention]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[_Mention]] = {}
    for mention in mentions:
        grouped.setdefault(mention.normalized_name, []).append(mention)
    ranked = sorted(
        grouped.items(),
        key=lambda item: (
            -sum(_signal_score(mention.signal) for mention in item[1]),
            -len({mention.line for mention in item[1]}),
            item[0],
        ),
    )[:MAX_CONCEPTS]
    concepts: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    by_name: dict[str, dict[str, Any]] = {}
    for normalized_name, concept_mentions in ranked:
        display = sorted(
            {mention.name for mention in concept_mentions}, key=lambda value: (len(value), value.casefold())
        )[0]
        concept_id = "concept_candidate_" + _digest(source_id, space, normalized_name)
        evidence_ids: list[str] = []
        unique_lines: dict[int, _Mention] = {}
        for mention in concept_mentions:
            unique_lines.setdefault(mention.line, mention)
        for line_number, mention in sorted(unique_lines.items())[:5]:
            evidence_id = "evidence_" + _digest(
                source_id, f"L{line_number}-L{line_number}", "concept_mention", normalized_name
            )
            evidence_ids.append(evidence_id)
            evidence.append(
                {
                    "id": evidence_id,
                    "source_id": source_id,
                    "locator": {"kind": "line_range", "value": f"L{line_number}-L{line_number}"},
                    "excerpt": mention.excerpt,
                    "proposition": f"{display} is explicitly marked in the selected source.",
                    "evidence_kind": "source_mention",
                    "extractor_version": EXTRACTOR_VERSION,
                    "review_status": "unreviewed",
                }
            )
        aliases = sorted(
            {mention.name for mention in concept_mentions if mention.name != display}, key=str.casefold
        )
        concept = {
            "id": concept_id,
            "canonical_name_candidate": display,
            "aliases": aliases,
            "space": space,
            "identity_status": "source_scoped_candidate",
            "signals": sorted({mention.signal for mention in concept_mentions}),
            "mention_count": len(concept_mentions),
            "evidence_ids": evidence_ids,
            "review_status": "unreviewed",
        }
        concepts.append(concept)
        by_name[normalized_name] = concept
    return concepts, by_name, evidence


def _relation_between(text: str) -> str | None:
    normalized = _SPACE.sub(" ", text.casefold())
    # Relation extraction is deliberately conservative.  A lexical trigger inside
    # a negated or modal clause is not affirmative evidence for a canonical edge.
    blockers = (
        " no longer ", " not ", " never ", " doesn't ", " does not ",
        " without ", " may ", " might ", " could ", " sometimes ",
        "不再", "不是", "不需要", "不依賴", "可能", "未必",
    )
    padded = f" {normalized} "
    if any(blocker in padded for blocker in blockers):
        return None
    tests = (
        ("is part of", "part_of"),
        ("是一部分", "part_of"),
        ("requires", "requires"),
        ("depends on", "requires"),
        ("需要", "requires"),
        ("依賴", "requires"),
        ("causes", "causes"),
        ("leads to", "causes"),
        ("導致", "causes"),
        ("contrasts with", "contrasts_with"),
        ("different from", "contrasts_with"),
        ("不同於", "contrasts_with"),
        ("對比", "contrasts_with"),
        ("maps to", "maps_to"),
        ("corresponds to", "maps_to"),
        ("對應", "maps_to"),
        (" is a ", "is_a"),
        ("是一種", "is_a"),
    )
    for phrase, relation in tests:
        if phrase in padded:
            return relation
    return None


def _build_relations(
    source_id: str,
    lines: list[str],
    mentions: list[_Mention],
    concepts_by_name: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_line: dict[int, list[_Mention]] = {}
    for mention in mentions:
        if mention.normalized_name in concepts_by_name:
            by_line.setdefault(mention.line, []).append(mention)
    relations: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None, int]] = set()
    for line_number, line_mentions in sorted(by_line.items()):
        unique: dict[str, _Mention] = {}
        for mention in sorted(line_mentions, key=lambda item: (item.start, item.end)):
            unique.setdefault(mention.normalized_name, mention)
        ordered = sorted(unique.values(), key=lambda item: (item.start, item.end))
        for left, right in zip(ordered, ordered[1:]):
            left_concept = concepts_by_name[left.normalized_name]
            right_concept = concepts_by_name[right.normalized_name]
            relation = _relation_between(lines[line_number - 1][left.end:right.start])
            edge_class = "canonical_candidate" if relation else "soft_association"
            key = (str(left_concept["id"]), str(right_concept["id"]), relation, line_number)
            if key in seen:
                continue
            seen.add(key)
            locator_value = f"L{line_number}-L{line_number}"
            evidence_kind = "explicit_relation_statement" if relation else "co_mention_only"
            evidence_id = "evidence_" + _digest(
                source_id, locator_value, evidence_kind,
                str(left_concept["id"]), str(right_concept["id"]), relation or "unresolved",
            )
            if relation:
                proposition = lines[line_number - 1].strip()
                confidence = "medium"
                rationale = "The selected source places an explicit relation phrase between both marked concepts."
            else:
                proposition = (
                    f"{left_concept['canonical_name_candidate']} and "
                    f"{right_concept['canonical_name_candidate']} are co-mentioned; "
                    "the source line does not assert a precise relation."
                )
                confidence = "unresolved"
                rationale = "Co-mention is preserved as an unresolved association, not promoted to a fact."
            relation_id = "relation_candidate_" + _digest(
                str(left_concept["id"]), relation or "unresolved",
                str(right_concept["id"]), evidence_id,
            )
            evidence.append(
                {
                    "id": evidence_id,
                    "source_id": source_id,
                    "locator": {"kind": "line_range", "value": locator_value},
                    "excerpt": lines[line_number - 1].strip(),
                    "proposition": proposition,
                    "evidence_kind": evidence_kind,
                    "extractor_version": EXTRACTOR_VERSION,
                    "review_status": "unreviewed",
                }
            )
            relations.append(
                {
                    "id": relation_id,
                    "subject_concept_id": left_concept["id"],
                    "subject_label": left_concept["canonical_name_candidate"],
                    "relation": relation,
                    "object_concept_id": right_concept["id"],
                    "object_label": right_concept["canonical_name_candidate"],
                    "edge_class": edge_class,
                    "confidence": confidence,
                    "evidence_ids": [evidence_id],
                    "rationale": rationale,
                    "review_status": "unreviewed",
                }
            )
            if len(relations) >= MAX_RELATIONS:
                return relations, evidence
    return relations, evidence


def _topic_excerpt(
    lines: list[str], ignored: set[int], code_lines: set[int]
) -> dict[str, Any]:
    paragraph: list[str] = []
    start: int | None = None
    end: int | None = None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if number in ignored or number in code_lines or _HEADING.match(line):
            if paragraph:
                break
            continue
        if not stripped:
            if paragraph:
                break
            continue
        cleaned = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        cleaned = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), cleaned)
        cleaned = re.sub(r"[*_`]", "", cleaned)
        if start is None:
            start = number
        end = number
        paragraph.append(cleaned)
        if sum(len(item) for item in paragraph) >= 320:
            break
    text = _SPACE.sub(" ", " ".join(paragraph)).strip()
    if len(text) > 360:
        text = text[:357].rstrip() + "…"
    start = start or 1
    end = end or start
    return {
        "kind": "source_excerpt",
        "text": text or "No prose excerpt was available; inspect the immutable source directly.",
        "source_locator": {"kind": "line_range", "value": f"L{start}-L{end}"},
        "is_generated_summary": False,
    }


def _planned_artifacts(
    source_id: str, source_path: Path, title: str, concepts: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    del title
    root = f"KGnote Alpha/{_slug(source_path.stem, 'learning-source')}-{source_id[-8:]}"
    source_name = _safe_filename(source_path.name, "source.md")
    if not source_name.casefold().endswith(".md"):
        source_name += ".md"
    concept_notes = []
    for concept in concepts:
        name = str(concept["canonical_name_candidate"])
        filename = f"{_slug(name, 'concept')}-{str(concept['id'])[-8:]}.md"
        concept_notes.append(f"{root}/Concepts/{filename}")
    return {
        "workspace_root": root,
        "entry_note": f"{root}/Start Here.md",
        "immutable_source": f"{root}/Source/{source_name}",
        "structure_note": f"{root}/Structure.md",
        "relations_note": f"{root}/Relationships.md",
        "evidence_note": f"{root}/Evidence.md",
        "manifest": f"{root}/.kgnote/manifest.json",
        "concept_notes": concept_notes,
    }


def _render_markdown(payload: Mapping[str, Any]) -> str:
    source = payload["source"]
    summary = payload["topic_summary"]
    artifacts = payload["planned_artifacts"]
    structure = payload["structure"]
    concepts = payload["concepts"]
    relations = payload["relations"]
    uncertainties = payload["uncertainties"]
    lines = [
        f"# Preview: {source['title']}",
        "",
        "> Preview only — no files were written and no external service was called.",
        "",
        "## What this material is about",
        "",
        str(summary["text"]),
        "",
        f"Source: `{summary['source_locator']['value']}` · SHA-256 `{source['content_sha256']}`",
        "",
        "## Planned Obsidian entry",
        "",
        f"- Entry note: `{artifacts['entry_note']}`",
        f"- Immutable source: `{artifacts['immutable_source']}`",
        "",
        "## Major topics and sections",
        "",
    ]
    if structure:
        node_by_id = {item["id"]: item for item in structure}
        for item in structure:
            depth = 0
            parent = item["parent_id"]
            while parent:
                depth += 1
                parent = node_by_id.get(parent, {}).get("parent_id")
            lines.append(
                f"{'  ' * depth}- {item['title']} — `{item['source_locator']['value']}`"
            )
    else:
        lines.append("- No Markdown headings were found; use the concept list and immutable source as the first navigation layer.")
    lines.extend(["", "## Important concept candidates", ""])
    if concepts:
        lines.extend(["| Concept | Why included | Source evidence | Status |", "|---|---|---|---|"])
        for item in concepts:
            locators = ", ".join(
                evidence["locator"]["value"]
                for evidence in payload["evidence"]
                if evidence["id"] in item["evidence_ids"]
            )
            signals = ", ".join(item["signals"])
            lines.append(
                f"| {item['canonical_name_candidate']} | {signals} | {locators} | unreviewed candidate |"
            )
    else:
        lines.append("- No concept candidate met the explicit Markdown-signal rules; the source remains fully available.")
    lines.extend(["", "## Relationship candidates", ""])
    if relations:
        for item in relations:
            relation = item["relation"] or "unresolved association"
            evidence_id = item["evidence_ids"][0]
            evidence = next(row for row in payload["evidence"] if row["id"] == evidence_id)
            lines.append(
                f"- **{item['subject_label']}** — {relation} → **{item['object_label']}** "
                f"(`{evidence['locator']['value']}`): {item['rationale']}"
            )
    else:
        lines.append("- No source-grounded relationship candidate was found; none was invented.")
    lines.extend(["", "## Needs review", ""])
    for item in uncertainties:
        lines.append(f"- {item['message']}")
    lines.extend(
        [
            "",
            "## Preview result",
            "",
            f"Planned {len(structure)} section nodes, {len(concepts)} concept candidates, "
            f"{len(relations)} relationship candidates, and {len(payload['evidence'])} evidence records.",
            "All derived items remain unreviewed until a later safe materialization step.",
            "",
        ]
    )
    return "\n".join(lines)


def build_learning_workspace_preview(
    source_path: str | Path, *, space: str = "personal"
) -> PersonalAlphaPreview:
    """Read one explicit Markdown file and return a deterministic, zero-write preview."""

    if not isinstance(space, str) or not space.strip():
        raise PersonalAlphaPreviewError(
            "space_invalid",
            "The workspace space name must be non-empty text.",
            "Use a short space name such as personal, networking, or music.",
        )
    selected_path, source_bytes, content = _read_source(source_path)
    content_sha256 = hashlib.sha256(source_bytes).hexdigest()
    canonical_path = str(selected_path)
    source_id = "src_" + _digest("document", canonical_path, length=32)
    lines, ignored, code_lines = _markdown_lines(content)
    structure, heading_title = _extract_structure(source_id, lines, ignored, code_lines)
    title = heading_title or selected_path.stem
    mentions = _extract_mentions(lines, ignored, code_lines)
    concepts, concepts_by_name, concept_evidence = _build_concepts(
        source_id, space.strip(), mentions
    )
    relations, relation_evidence = _build_relations(
        source_id, lines, mentions, concepts_by_name
    )
    evidence = sorted(
        concept_evidence + relation_evidence,
        key=lambda item: (item["locator"]["value"], item["id"]),
    )
    uncertainties: list[dict[str, str]] = [
        {
            "code": "deterministic_scope",
            "message": (
                "This offline preview uses explicit Markdown signals and source wording; "
                "it does not claim semantic completeness or factual review."
            ),
        }
    ]
    if not structure:
        uncertainties.append(
            {
                "code": "no_heading_structure",
                "message": "No Markdown heading hierarchy was found; no artificial topic tree was invented.",
            }
        )
    if not concepts:
        uncertainties.append(
            {
                "code": "no_concept_candidates",
                "message": "No explicit concept signal was found; concepts require review or richer source markup.",
            }
        )
    if not any(item["relation"] for item in relations):
        uncertainties.append(
            {
                "code": "no_explicit_relations",
                "message": "No precise relation phrase was found between marked concepts; none was promoted to a fact.",
            }
        )
    if any(item["edge_class"] == "soft_association" for item in relations):
        uncertainties.append(
            {
                "code": "unresolved_associations",
                "message": "Co-mentioned concepts remain unresolved associations until their relation is supported and reviewed.",
            }
        )
    payload: dict[str, Any] = {
        "schema_version": PERSONAL_ALPHA_PREVIEW_VERSION,
        "status": "planned",
        "writes_performed": 0,
        "external_calls": 0,
        "extractor_version": EXTRACTOR_VERSION,
        "source": {
            "id": source_id,
            "source_kind": "document",
            "title": title,
            "selected_path": canonical_path,
            "content_sha256": content_sha256,
            "byte_count": len(source_bytes),
            "line_count": len(lines),
            "immutable": True,
        },
        "space": space.strip(),
        "topic_summary": _topic_excerpt(lines, ignored, code_lines),
        "structure": structure,
        "concepts": concepts,
        "relations": relations,
        "evidence": evidence,
        "uncertainties": uncertainties,
        "planned_artifacts": _planned_artifacts(source_id, selected_path, title, concepts),
    }
    return PersonalAlphaPreview(payload=payload, markdown=_render_markdown(payload))
