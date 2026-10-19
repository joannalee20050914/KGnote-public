"""Validation for versioned Guided Map specifications and read models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


SPEC_SCHEMA_VERSION = "kgnote.guided-map-spec.v1"
READ_MODEL_SCHEMA_VERSION = "kgnote.guided-map-read-model.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "guided-map" / "v1"


class GuidedMapValidationError(ValueError):
    """Stable validation error that does not echo caller-owned content."""

    def __init__(self, code: str, path: tuple[object, ...] = (), validator: str = "semantic"):
        self.code = code
        self.path = path
        self.validator = validator
        pointer = "/" + "/".join(str(part) for part in path) if path else "/"
        super().__init__(f"{code} at {pointer} ({validator})")


def _load_validator(filename: str) -> Draft202012Validator:
    with (SCHEMA_ROOT / filename).open(encoding="utf-8") as handle:
        schema = json.load(handle)
    return Draft202012Validator(schema, format_checker=FormatChecker())


_SPEC_VALIDATOR = _load_validator("guided-map-spec.schema.json")
_READ_MODEL_VALIDATOR = _load_validator("guided-map-read-model.schema.json")
_GENERIC_LINKING_PHRASES = {
    "related_to", "related to", "maps_to", "maps to", "相關", "有關", "對應", "關聯", "連結"
}


def _reject(code: str, *path: object) -> None:
    raise GuidedMapValidationError(code, tuple(path))


def _validate_schema(
    payload: Mapping[str, Any], validator: Draft202012Validator, code: str
) -> None:
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if errors:
        error = errors[0]
        raise GuidedMapValidationError(code, tuple(error.absolute_path), str(error.validator))


def _require_sorted_unique(values: list[Any], path: tuple[object, ...]) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        raise GuidedMapValidationError("non_deterministic_order", path)


def _validate_grouping(groups: list[dict[str, Any]]) -> tuple[set[str], dict[str, str]]:
    expected_order = list(range(1, len(groups) + 1))
    actual_order = [group["order"] for group in groups]
    if actual_order != expected_order:
        _reject("non_contiguous_group_order", "groups")
    group_ids = [group["id"] for group in groups]
    if len(group_ids) != len(set(group_ids)):
        _reject("duplicate_group_id", "groups")

    concept_to_group: dict[str, str] = {}
    for index, group in enumerate(groups):
        _require_sorted_unique(group["concept_ids"], ("groups", index, "concept_ids"))
        for concept_id in group["concept_ids"]:
            if concept_id in concept_to_group:
                _reject("concept_in_multiple_groups", "groups", index, "concept_ids")
            concept_to_group[concept_id] = group["id"]
    return set(group_ids), concept_to_group


def validate_guided_map_spec(payload: Mapping[str, Any]) -> None:
    """Validate a human-reviewed Guided Map spec without resolving graph references."""

    _validate_schema(payload, _SPEC_VALIDATOR, "invalid_guided_map_spec")
    _validate_grouping(payload["groups"])
    edge_ids = [item["edge_id"] for item in payload["teaching_propositions"]]
    _require_sorted_unique(edge_ids, ("teaching_propositions",))
    for index, proposition in enumerate(payload["teaching_propositions"]):
        _require_sorted_unique(
            proposition["evidence_ids"],
            ("teaching_propositions", index, "evidence_ids"),
        )
        if proposition["linking_phrase"].strip().casefold() in _GENERIC_LINKING_PHRASES:
            _reject("generic_linking_phrase", "teaching_propositions", index, "linking_phrase")


def validate_guided_map_read_model(payload: Mapping[str, Any]) -> None:
    """Validate resolved references, view-only groups, and deterministic ordering."""

    _validate_schema(payload, _READ_MODEL_VALIDATOR, "invalid_guided_map_read_model")
    group_ids, grouped_concepts = _validate_grouping(payload["groups"])
    concept_ids = [item["id"] for item in payload["concepts"]]
    edge_ids = [item["edge_id"] for item in payload["propositions"]]
    evidence_ids = [item["id"] for item in payload["evidence"]]
    _require_sorted_unique(concept_ids, ("concepts",))
    _require_sorted_unique(edge_ids, ("propositions",))
    _require_sorted_unique(evidence_ids, ("evidence",))

    concepts = {item["id"]: item for item in payload["concepts"]}
    evidence = {item["id"]: item for item in payload["evidence"]}
    if set(concepts) != set(grouped_concepts):
        _reject("group_membership_does_not_match_concepts", "groups")
    for index, concept in enumerate(payload["concepts"]):
        if concept["group_id"] not in group_ids or grouped_concepts[concept["id"]] != concept["group_id"]:
            _reject("concept_group_mismatch", "concepts", index, "group_id")
        _require_sorted_unique(concept["aliases"], ("concepts", index, "aliases"))
        _require_sorted_unique(concept["evidence_ids"], ("concepts", index, "evidence_ids"))
        if not set(concept["evidence_ids"]).issubset(evidence):
            _reject("dangling_evidence_reference", "concepts", index, "evidence_ids")

    used_evidence: set[str] = {
        evidence_id
        for concept in payload["concepts"]
        for evidence_id in concept["evidence_ids"]
    }
    for index, proposition in enumerate(payload["propositions"]):
        _require_sorted_unique(proposition["evidence_ids"], ("propositions", index, "evidence_ids"))
        if proposition["linking_phrase"].strip().casefold() in _GENERIC_LINKING_PHRASES:
            _reject("generic_linking_phrase", "propositions", index, "linking_phrase")
        if proposition["projection_version"] != payload["projection_version"]:
            _reject("projection_version_mismatch", "propositions", index, "projection_version")
        subject = concepts.get(proposition["subject_concept_id"])
        object_ = concepts.get(proposition["object_concept_id"])
        if subject is None or object_ is None:
            _reject("dangling_proposition_endpoint", "propositions", index)
        if subject["label"] != proposition["subject_label"] or object_["label"] != proposition["object_label"]:
            _reject("proposition_label_mismatch", "propositions", index)
        if not set(proposition["evidence_ids"]).issubset(evidence):
            _reject("dangling_evidence_reference", "propositions", index, "evidence_ids")
        used_evidence.update(proposition["evidence_ids"])

    if used_evidence != set(evidence):
        _reject("evidence_set_does_not_match_propositions", "evidence")
    for index, record in enumerate(payload["evidence"]):
        if record["source_id"] != payload["source"]["id"]:
            _reject("evidence_outside_learning_unit_source", "evidence", index, "source_id")


__all__ = [
    "GuidedMapValidationError",
    "READ_MODEL_SCHEMA_VERSION",
    "SPEC_SCHEMA_VERSION",
    "validate_guided_map_read_model",
    "validate_guided_map_spec",
]
