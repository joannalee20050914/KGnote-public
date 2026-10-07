"""Pure learner-facing projection for Personal Alpha Markdown workspaces."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping


LEARNER_PROJECTION_VERSION = "kgnote.personal-alpha-learner-projection.v1"
_SPACE = re.compile(r"\s+")
_ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_RESERVED_FILENAME = re.compile(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.I)
_MARKUP = re.compile(r"(?:\*\*|__)")


@dataclass(frozen=True, repr=False)
class LearnerProjection:
    """Copy-safe serializable view model with no filesystem or network behavior."""

    _model_json: str = field(repr=False)

    @property
    def model(self) -> dict[str, Any]:
        return json.loads(self._model_json)

    def as_dict(self) -> dict[str, Any]:
        return self.model


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _plain(value: str) -> str:
    return _SPACE.sub(" ", _MARKUP.sub("", value)).strip()


def _sentence(value: str) -> str:
    text = value.strip()
    return text if not text or text.endswith((".", "!", "?", "。", "！", "？")) else text + "."


def _safe_label_filename(label: str) -> str:
    value = unicodedata.normalize("NFC", label)
    value = _ILLEGAL_FILENAME.sub("-", value)
    value = _SPACE.sub(" ", value).strip(" .")
    if value in {"", ".", ".."}:
        value = "Concept"
    if _RESERVED_FILENAME.match(value):
        value = value + " concept"
    return value[:96].rstrip(" .") or "Concept"


def _collision_key(filename: str) -> str:
    return unicodedata.normalize("NFKC", filename).casefold()


def _projected_concept_paths(concepts: list[Mapping[str, Any]]) -> dict[str, str]:
    by_key: dict[str, list[Mapping[str, Any]]] = {}
    base_by_id: dict[str, str] = {}
    for concept in concepts:
        concept_id = str(concept["id"])
        base = _safe_label_filename(str(concept["canonical_name_candidate"]))
        base_by_id[concept_id] = base
        by_key.setdefault(_collision_key(base), []).append(concept)
    by_key.setdefault(_collision_key("Index"), [])

    paths: dict[str, str] = {}
    for key, rows in sorted(by_key.items()):
        if not rows:
            continue
        collision = len(rows) > 1 or key == _collision_key("Index")
        for concept in sorted(rows, key=lambda item: str(item["id"])):
            concept_id = str(concept["id"])
            base = base_by_id[concept_id]
            suffix = ""
            if collision:
                suffix = " — " + hashlib.sha256(concept_id.encode("utf-8")).hexdigest()[:8]
            paths[concept_id] = f"Concepts/{base}{suffix}.md"
    return paths


def _relation_phrase(relation: str | None) -> str:
    return {
        "is_a": "is a kind of",
        "part_of": "is part of",
        "requires": "requires",
        "maps_to": "maps to",
        "causes": "causes",
        "contrasts_with": "contrasts with",
        "related_to": "is related to",
        None: "is mentioned together with",
    }[relation]


def _group_evidence(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in payload["evidence"]:
        locator = item["locator"]
        key = (
            str(item["source_id"]),
            str(locator["kind"]),
            str(locator["value"]),
            str(item["excerpt"]),
        )
        group = groups.setdefault(
            key,
            {
                "source_id": item["source_id"],
                "locator": {"kind": locator["kind"], "value": locator["value"]},
                "excerpt": item["excerpt"],
                "evidence_ids": [],
                "propositions": [],
                "review_statuses": [],
            },
        )
        group["evidence_ids"].append(item["id"])
        if item["proposition"] not in group["propositions"]:
            group["propositions"].append(item["proposition"])
        if item["review_status"] not in group["review_statuses"]:
            group["review_statuses"].append(item["review_status"])
    result = list(groups.values())
    for group in result:
        group["evidence_ids"].sort()
        group["propositions"].sort()
        group["review_statuses"].sort()
    result.sort(
        key=lambda item: (
            int(re.search(r"\d+", str(item["locator"]["value"])).group())
            if re.search(r"\d+", str(item["locator"]["value"]))
            else 0,
            item["locator"]["value"],
            _plain(str(item["excerpt"])).casefold(),
        )
    )
    return result


def _concept_explanation(
    concept: Mapping[str, Any],
    relations: list[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str | None, str]:
    name = str(concept["canonical_name_candidate"])
    definition = None
    for evidence_id in concept["evidence_ids"]:
        candidate = evidence_by_id[str(evidence_id)]
        match = re.search(
            r"(?:\*\*|__)([^\n]+?)(?:\*\*|__)\s*[:：]",
            str(candidate["excerpt"]),
        )
        if match and _plain(match.group(1)).strip().casefold() == name.strip().casefold():
            definition = candidate
            break
    if definition:
        excerpt = str(definition["excerpt"]).strip()
        tail = re.split(r"[:：]", excerpt, maxsplit=1)[1].strip()
        first_word = _plain(tail).split(" ", 1)[0].casefold()
        if first_word in {"a", "an", "the"}:
            connector = "is "
        elif first_word in {
            "identifies",
            "means",
            "refers",
            "maps",
            "requires",
            "contrasts",
            "keeps",
            "is",
            "are",
        }:
            connector = ""
        else:
            connector = "refers to "
        explanation = f"In this material, **{name}** {connector}{_sentence(tail).lstrip()}"
        return explanation, None, explanation

    outgoing = next(
        (item for item in relations if str(item["subject_concept_id"]) == str(concept["id"])),
        None,
    )
    incoming = next(
        (item for item in relations if str(item["object_concept_id"]) == str(concept["id"])),
        None,
    )
    if outgoing:
        other = str(outgoing["object_label"])
        phrase = _relation_phrase(outgoing["relation"])
        if outgoing["review_status"] in {"verified", "accepted", "corrected"}:
            explanation = f"In this material, **{name}** {phrase} **{other}**."
            role = (
                f"The lesson uses the **{name}** → **{other}** relationship: "
                f"**{name}** {phrase} **{other}**."
            )
        else:
            explanation = (
                f"The source contains an unreviewed candidate connecting **{name}** to "
                f"**{other}** with “{phrase}”. KGnote keeps it provisional."
            )
            role = explanation
    elif incoming:
        other = str(incoming["subject_label"])
        phrase = _relation_phrase(incoming["relation"])
        if incoming["review_status"] not in {"verified", "accepted", "corrected"}:
            explanation = (
                f"The source contains an unreviewed candidate connecting **{other}** to "
                f"**{name}** with “{phrase}”. KGnote keeps it provisional."
            )
        elif incoming["relation"] == "maps_to":
            explanation = f"In this material, **{name}** is the endpoint that **{other}** maps to."
        elif incoming["relation"] == "requires":
            explanation = f"In this material, **{name}** is required by **{other}**."
        elif incoming["relation"] is None:
            explanation = f"In this material, **{name}** is mentioned together with **{other}**."
        else:
            explanation = f"In this material, **{other}** {phrase} **{name}**."
        role = explanation
    else:
        explanation = f"In this material, **{name}** appears in the selected source."
        role = explanation
    limitation = (
        f"This source does not provide a broader standalone definition of "
        f"{'ports' if name.casefold() == 'port' else name}, "
        "so KGnote does not invent one here."
    )
    return explanation, limitation, role


def _related_concepts(
    concept: Mapping[str, Any],
    concepts: list[Mapping[str, Any]],
    relations: list[Mapping[str, Any]],
    paths: Mapping[str, str],
) -> list[dict[str, str]]:
    related: list[dict[str, str]] = []
    concept_id = str(concept["id"])
    for item in relations:
        approved = item["review_status"] in {"verified", "accepted", "corrected"}
        if str(item["subject_concept_id"]) == concept_id:
            other_id = str(item["object_concept_id"])
            phrase = _relation_phrase(item["relation"])
            label = str(item["object_label"])
            if not approved:
                description = (
                    f"has an unreviewed source-linked candidate from "
                    f"{concept['canonical_name_candidate']} using “{phrase}”."
                )
            elif item["relation"] == "maps_to":
                description = (
                    f"the endpoint {concept['canonical_name_candidate']} maps to in the lesson."
                )
            elif item["relation"] == "requires":
                description = (
                    f"required by {concept['canonical_name_candidate']} in the material."
                )
            elif item["relation"] is None:
                description = (
                    f"is mentioned together with {concept['canonical_name_candidate']} in this source."
                )
            else:
                description = (
                    f"connects because {concept['canonical_name_candidate']} {phrase} it."
                )
        elif str(item["object_concept_id"]) == concept_id:
            other_id = str(item["subject_concept_id"])
            label = str(item["subject_label"])
            if not approved:
                description = (
                    f"has an unreviewed source-linked candidate to "
                    f"{concept['canonical_name_candidate']} using “{_relation_phrase(item['relation'])}”."
                )
            elif item["relation"] == "maps_to":
                description = f"maps to {concept['canonical_name_candidate']} in the lesson."
            elif item["relation"] == "requires":
                description = f"requires {concept['canonical_name_candidate']} in the lesson."
            elif item["relation"] is None:
                description = "is mentioned together in this source."
            else:
                description = f"connects through “{_relation_phrase(item['relation'])}”."
        else:
            continue
        related.append(
            {"id": other_id, "label": label, "path": paths[other_id], "description": description}
        )
    related.sort(key=lambda item: (item["label"].casefold(), item["id"]))
    return related


def _learning_goal(title: str) -> str:
    if title.casefold() == "how a browser reaches a local service":
        return "How does a browser reach the intended local service and get a result back?"
    if title.endswith(("?", "？")):
        return title
    return f"What should you understand about {title}?"


def _learning_path(payload: Mapping[str, Any]) -> list[str]:
    labels = {str(item["canonical_name_candidate"]).casefold() for item in payload["concepts"]}
    relation_types = {item["relation"] for item in payload["relations"]}
    if {
        "ip address",
        "network connection",
        "http request",
        "port",
        "service endpoint",
        "http response",
        "status code",
    }.issubset(labels) and {"requires", "maps_to", None}.issubset(relation_types):
        return [
            "Establish the network path.",
            "Identify the host.",
            "Select the service.",
            "Send the HTTP request.",
            "Read the HTTP response and status code.",
        ]
    numbered_steps: dict[int, str] = {}
    for evidence in payload["evidence"]:
        excerpt = str(evidence["excerpt"]).strip()
        match = re.match(r"^(\d+)[.)]\s+(.+)$", excerpt)
        if not match:
            continue
        step = _plain(match.group(2)).strip()
        if step:
            numbered_steps.setdefault(int(match.group(1)), _sentence(step))
    if numbered_steps:
        return [numbered_steps[index] for index in sorted(numbered_steps)[:8]]
    structure = list(payload["structure"])
    if structure:
        root_level = min(int(item["level"]) for item in structure)
        headings = [
            str(item["title"])
            for item in structure
            if int(item["level"]) > root_level
        ]
        if headings:
            return [f"Read: {heading}." for heading in headings[:6]]
    return [
        "Read the original material.",
        "Use the key concepts as a reference while reading.",
    ]


def project_learner_workspace(payload: Mapping[str, Any]) -> LearnerProjection:
    """Project canonical preview records into a deterministic learner-facing view model."""

    concepts = list(payload["concepts"])
    relations = list(payload["relations"])
    evidence_by_id = {str(item["id"]): item for item in payload["evidence"]}
    paths = _projected_concept_paths(concepts)
    evidence_groups = _group_evidence(payload)
    groups_by_evidence_id = {
        str(evidence_id): group
        for group in evidence_groups
        for evidence_id in group["evidence_ids"]
    }

    projected_concepts: list[dict[str, Any]] = []
    for concept in concepts:
        explanation, limitation, role = _concept_explanation(concept, relations, evidence_by_id)
        groups: list[dict[str, Any]] = []
        seen_groups: set[tuple[str, str, str]] = set()
        for evidence_id in concept["evidence_ids"]:
            group = groups_by_evidence_id[str(evidence_id)]
            key = (
                str(group["source_id"]),
                str(group["locator"]["value"]),
                str(group["excerpt"]),
            )
            if key not in seen_groups:
                seen_groups.add(key)
                groups.append(group)
        projected_concepts.append(
            {
                "id": concept["id"],
                "label": concept["canonical_name_candidate"],
                "aliases": concept["aliases"],
                "review_status": concept["review_status"],
                "path": paths[str(concept["id"])],
                "explanation": explanation,
                "limitation": limitation,
                "role": role,
                "related": _related_concepts(concept, concepts, relations, paths),
                "evidence_groups": groups,
            }
        )

    projected_relations: list[dict[str, Any]] = []
    for item in relations:
        relation = item["relation"]
        projected_relations.append(
            {
                "id": item["id"],
                "subject_id": item["subject_concept_id"],
                "subject_label": item["subject_label"],
                "subject_path": paths[str(item["subject_concept_id"])],
                "relation": relation,
                "phrase": _relation_phrase(relation),
                "object_id": item["object_concept_id"],
                "object_label": item["object_label"],
                "object_path": paths[str(item["object_concept_id"])],
                "resolved": relation is not None
                and item["review_status"] in {"verified", "accepted", "corrected"},
                "evidence_groups": [
                    groups_by_evidence_id[str(evidence_id)]
                    for evidence_id in item["evidence_ids"]
                ],
                "review_status": item["review_status"],
                "confidence": item["confidence"],
            }
        )

    structure = list(payload["structure"])
    levels = [int(item["level"]) for item in structure]
    short_structure = bool(structure) and len(structure) <= 6 and (max(levels) - min(levels) <= 2)
    source_shape = (
        "heading_free"
        if not structure
        else "procedural"
        if any(re.match(r"^\s*\d+[.)]\s+", str(item["excerpt"])) for item in payload["evidence"])
        else "hierarchical"
    )
    source_title = str(payload["source"]["title"])
    if not structure and "-" in source_title:
        source_title = source_title.replace("-", " ").strip()
        source_title = source_title[:1].upper() + source_title[1:]
    model = {
        "schema_version": LEARNER_PROJECTION_VERSION,
        "source": {
            "id": payload["source"]["id"],
            "title": source_title,
            "content_sha256": payload["source"]["content_sha256"],
        },
        "summary": payload["topic_summary"]["text"],
        "summary_locator": payload["topic_summary"]["source_locator"],
        "learning_goal": _learning_goal(source_title),
        "learning_path": _learning_path(payload),
        "structure": structure,
        "structure_inline": short_structure,
        "source_shape": source_shape,
        "concepts": projected_concepts,
        "relationships": projected_relations,
        "evidence_groups": evidence_groups,
        "canonical_ids": {
            "concepts": [item["id"] for item in concepts],
            "relations": [item["id"] for item in relations],
            "evidence": [item["id"] for item in payload["evidence"]],
        },
    }
    return LearnerProjection(_canonical_json(model))


__all__ = ["LEARNER_PROJECTION_VERSION", "LearnerProjection", "project_learner_workspace"]
