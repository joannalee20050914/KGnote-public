"""Pure kgnote.normalize.v1 canonical candidate generation."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from kgnote.contracts.extraction import (
    ExtractionOutputValidationError,
    validate_extraction_output,
)


NORMALIZATION_RULESET_VERSION = "kgnote.normalize.v1"
CANONICAL_SCHEMA_VERSION = "kgnote.v0.1"
COLLECTION_KINDS = {
    "concepts": "concept",
    "evidence": "evidence",
    "learning_events": "learning_event",
    "edges": "edge",
}
CANONICAL_PREFIXES = ("concept_", "evidence_", "event_", "edge_")
REFERENCE_FIELDS = {
    "local_ref",
    "source_ref",
    "target_ref",
    "concept_refs",
    "evidence_refs",
}


@dataclass(frozen=True)
class NormalizationProblem:
    code: str
    path: tuple[object, ...] = ()
    reference: str | None = None
    canonical_id: str | None = None
    local_refs: tuple[str, ...] = ()


@dataclass(frozen=True, repr=False)
class NormalizationResult:
    status: Literal["normalized", "rejected", "conflict"]
    ruleset_version: str = NORMALIZATION_RULESET_VERSION
    _records_json: str | None = field(default=None, repr=False)
    _ref_map_json: str | None = field(default=None, repr=False)
    problem: NormalizationProblem | None = None

    @property
    def records(self) -> dict[str, Any] | None:
        if self._records_json is None:
            return None
        return json.loads(self._records_json)

    @property
    def ref_map(self) -> dict[str, str] | None:
        if self._ref_map_json is None:
            return None
        return json.loads(self._ref_map_json)

    def __repr__(self) -> str:
        return (
            "NormalizationResult("
            f"status={self.status!r}, "
            f"ruleset_version={self.ruleset_version!r}, "
            f"problem={self.problem!r})"
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _stable_id(prefix: str, identity: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _display_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def _identity_text(value: str) -> str:
    return _display_text(value).casefold()


def _normalized_unique(values: list[str], *, casefold: bool) -> list[str]:
    candidates = {_display_text(value) for value in values}
    if casefold:
        grouped: dict[str, list[str]] = {}
        for value in candidates:
            grouped.setdefault(value.casefold(), []).append(value)
        selected = [min(group) for group in grouped.values()]
        return sorted(selected, key=lambda value: (value.casefold(), value))
    return sorted(candidates)


def _problem(
    status: Literal["rejected", "conflict"],
    *,
    code: str,
    path: tuple[object, ...] = (),
    reference: str | None = None,
    canonical_id: str | None = None,
    local_refs: tuple[str, ...] = (),
) -> NormalizationResult:
    return NormalizationResult(
        status=status,
        problem=NormalizationProblem(
            code=code,
            path=path,
            reference=reference,
            canonical_id=canonical_id,
            local_refs=local_refs,
        ),
    )


def _value_at_path(value: Any, path: tuple[object, ...]) -> Any:
    current = value
    for part in path:
        current = current[part]
    return current


def _schema_problem(
    candidate_result: Mapping[str, Any], error: ExtractionOutputValidationError
) -> NormalizationResult:
    reference = None
    code = "candidate_schema_invalid"
    if error.path and error.validator == "pattern":
        field_name = next(
            (part for part in reversed(error.path) if isinstance(part, str)),
            None,
        )
        if field_name in REFERENCE_FIELDS:
            value = _value_at_path(candidate_result, error.path)
            if isinstance(value, str):
                reference = value
                code = (
                    "canonical_id_not_allowed"
                    if value.startswith(CANONICAL_PREFIXES)
                    else "wrong_reference_kind"
                )
    return _problem(
        "rejected",
        code=code,
        path=error.path,
        reference=reference,
    )


def _build_local_index(
    candidate_result: Mapping[str, Any]
) -> tuple[dict[str, tuple[str, int]], NormalizationResult | None]:
    index: dict[str, tuple[str, int]] = {}
    for collection, kind in COLLECTION_KINDS.items():
        for position, candidate in enumerate(candidate_result[collection]):
            local_ref = candidate["local_ref"]
            if local_ref in index:
                return {}, _problem(
                    "rejected",
                    code="duplicate_local_ref",
                    path=(collection, position, "local_ref"),
                    reference=local_ref,
                    local_refs=(local_ref,),
                )
            index[local_ref] = (kind, position)
    return index, None


def _check_reference(
    *,
    index: Mapping[str, tuple[str, int]],
    reference: str,
    expected_kind: str,
    path: tuple[object, ...],
) -> NormalizationResult | None:
    resolved = index.get(reference)
    if resolved is None:
        return _problem(
            "rejected",
            code="dangling_local_ref",
            path=path,
            reference=reference,
        )
    if resolved[0] != expected_kind:
        return _problem(
            "rejected",
            code="wrong_reference_kind",
            path=path,
            reference=reference,
        )
    return None


def _validate_integrity(
    candidate_result: Mapping[str, Any], index: Mapping[str, tuple[str, int]]
) -> NormalizationResult | None:
    source_id = candidate_result["source_id"]
    for collection in ("evidence", "learning_events"):
        for position, candidate in enumerate(candidate_result[collection]):
            if candidate["source_id"] != source_id:
                return _problem(
                    "rejected",
                    code="source_id_mismatch",
                    path=(collection, position, "source_id"),
                    reference=candidate["source_id"],
                )

    checks: list[tuple[str, str, tuple[object, ...]]] = []
    for position, concept in enumerate(candidate_result["concepts"]):
        checks.extend(
            (reference, "evidence", ("concepts", position, "evidence_refs", index_))
            for index_, reference in enumerate(concept["evidence_refs"])
        )
    for position, event in enumerate(candidate_result["learning_events"]):
        checks.extend(
            (reference, "concept", ("learning_events", position, "concept_refs", index_))
            for index_, reference in enumerate(event["concept_refs"])
        )
        checks.extend(
            (reference, "evidence", ("learning_events", position, "evidence_refs", index_))
            for index_, reference in enumerate(event["evidence_refs"])
        )
    for position, edge in enumerate(candidate_result["edges"]):
        source_kind = "learning_event" if edge["edge_class"] == "learning" else "concept"
        checks.append(
            (edge["source_ref"], source_kind, ("edges", position, "source_ref"))
        )
        checks.append((edge["target_ref"], "concept", ("edges", position, "target_ref")))
        checks.extend(
            (reference, "evidence", ("edges", position, "evidence_refs", index_))
            for index_, reference in enumerate(edge["evidence_refs"])
        )

    for reference, expected_kind, path in checks:
        problem = _check_reference(
            index=index,
            reference=reference,
            expected_kind=expected_kind,
            path=path,
        )
        if problem is not None:
            return problem
    return None


def _identity_maps(candidate_result: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    maps: dict[str, dict[str, str]] = {kind: {} for kind in COLLECTION_KINDS.values()}
    for concept in candidate_result["concepts"]:
        identity = {
            "kind": "concept",
            "name": _identity_text(concept["name"]),
            "ruleset_version": NORMALIZATION_RULESET_VERSION,
            "spaces": sorted({_identity_text(space) for space in concept["spaces"]}),
        }
        maps["concept"][concept["local_ref"]] = _stable_id("concept", identity)
    for evidence in candidate_result["evidence"]:
        identity = {
            "kind": "evidence",
            "locator": {
                "kind": evidence["locator"]["kind"],
                "value": _display_text(evidence["locator"]["value"]),
            },
            "proposition": _display_text(evidence["proposition"]),
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "source_id": evidence["source_id"],
        }
        maps["evidence"][evidence["local_ref"]] = _stable_id("evidence", identity)
    for event in candidate_result["learning_events"]:
        identity = {
            "event_type": event["event_type"],
            "kind": "learning_event",
            "locator": {
                "kind": event["locator"]["kind"],
                "value": _display_text(event["locator"]["value"]),
            },
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "source_id": event["source_id"],
        }
        maps["learning_event"][event["local_ref"]] = _stable_id("event", identity)
    for edge in candidate_result["edges"]:
        source_kind = "learning_event" if edge["edge_class"] == "learning" else "concept"
        identity = {
            "edge_class": edge["edge_class"],
            "kind": "edge",
            "relation": edge["relation"],
            "ruleset_version": NORMALIZATION_RULESET_VERSION,
            "source_id": maps[source_kind][edge["source_ref"]],
            "target_id": maps["concept"][edge["target_ref"]],
        }
        maps["edge"][edge["local_ref"]] = _stable_id("edge", identity)
    return maps


def _identity_conflict(
    identity_maps: Mapping[str, Mapping[str, str]]
) -> NormalizationResult | None:
    for kind in ("concept", "evidence", "learning_event", "edge"):
        refs_by_id: dict[str, list[str]] = {}
        for local_ref, canonical_id in identity_maps[kind].items():
            refs_by_id.setdefault(canonical_id, []).append(local_ref)
        conflicts = [
            (canonical_id, tuple(sorted(local_refs)))
            for canonical_id, local_refs in refs_by_id.items()
            if len(local_refs) > 1
        ]
        if conflicts:
            canonical_id, local_refs = sorted(conflicts)[0]
            return _problem(
                "conflict",
                code="identity_conflict",
                canonical_id=canonical_id,
                local_refs=local_refs,
            )
    return None


def _emit_records(
    candidate_result: Mapping[str, Any], identity_maps: Mapping[str, Mapping[str, str]]
) -> dict[str, list[dict[str, Any]]]:
    source_id = candidate_result["source_id"]
    extractor_version = candidate_result["extractor_version"]
    generated_at = candidate_result["generated_at"]
    records: dict[str, list[dict[str, Any]]] = {
        "concepts": [],
        "evidence": [],
        "learning_events": [],
        "edges": [],
    }

    for candidate in candidate_result["concepts"]:
        canonical_name = _display_text(candidate["name"])
        aliases = [
            alias
            for alias in _normalized_unique(candidate["aliases"], casefold=True)
            if alias.casefold() != canonical_name.casefold()
        ]
        records["concepts"].append(
            {
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "id": identity_maps["concept"][candidate["local_ref"]],
                "type": "concept",
                "canonical_name": canonical_name,
                "aliases": aliases,
                "spaces": sorted(
                    {_identity_text(space) for space in candidate["spaces"]}
                ),
                "summary": _display_text(candidate["summary"]),
                "status": "needs_review",
                "evidence_ids": sorted(
                    identity_maps["evidence"][reference]
                    for reference in candidate["evidence_refs"]
                ),
                "integration_version": NORMALIZATION_RULESET_VERSION,
                "integrated_at": generated_at,
            }
        )
    for candidate in candidate_result["evidence"]:
        records["evidence"].append(
            {
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "id": identity_maps["evidence"][candidate["local_ref"]],
                "type": "evidence",
                "source_id": source_id,
                "locator": {
                    "kind": candidate["locator"]["kind"],
                    "value": _display_text(candidate["locator"]["value"]),
                },
                "proposition": _display_text(candidate["proposition"]),
                "observed_at": candidate["observed_at"],
                "extractor_version": extractor_version,
                "extracted_at": generated_at,
                "extraction_confidence": candidate["extraction_confidence"],
                "review_status": "unreviewed",
            }
        )
    for candidate in candidate_result["learning_events"]:
        records["learning_events"].append(
            {
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "id": identity_maps["learning_event"][candidate["local_ref"]],
                "type": "learning_event",
                "event_type": candidate["event_type"],
                "occurred_at": candidate["occurred_at"],
                "context": _display_text(candidate["context"]),
                "source_ids": [source_id],
                "concept_ids": sorted(
                    identity_maps["concept"][reference]
                    for reference in candidate["concept_refs"]
                ),
                "evidence_ids": sorted(
                    identity_maps["evidence"][reference]
                    for reference in candidate["evidence_refs"]
                ),
                "extractor_version": extractor_version,
                "extracted_at": generated_at,
                "extraction_confidence": candidate["extraction_confidence"],
            }
        )
    for candidate in candidate_result["edges"]:
        source_kind = (
            "learning_event" if candidate["edge_class"] == "learning" else "concept"
        )
        records["edges"].append(
            {
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "id": identity_maps["edge"][candidate["local_ref"]],
                "type": "edge",
                "source_id": identity_maps[source_kind][candidate["source_ref"]],
                "relation": candidate["relation"],
                "target_id": identity_maps["concept"][candidate["target_ref"]],
                "edge_class": candidate["edge_class"],
                "evidence_ids": sorted(
                    identity_maps["evidence"][reference]
                    for reference in candidate["evidence_refs"]
                ),
                "confidence": candidate["confidence"],
                "ruleset_version": NORMALIZATION_RULESET_VERSION,
                "generated_at": generated_at,
            }
        )
    for collection in records.values():
        collection.sort(key=lambda record: record["id"])
    return records


def normalize_candidate_result(
    candidate_result: Mapping[str, Any],
) -> NormalizationResult:
    """Normalize one candidate result without I/O, time, randomness, or merging."""

    try:
        validate_extraction_output(candidate_result)
    except ExtractionOutputValidationError as error:
        return _schema_problem(candidate_result, error)

    index, index_problem = _build_local_index(candidate_result)
    if index_problem is not None:
        return index_problem
    integrity_problem = _validate_integrity(candidate_result, index)
    if integrity_problem is not None:
        return integrity_problem

    identity_maps = _identity_maps(candidate_result)
    conflict = _identity_conflict(identity_maps)
    if conflict is not None:
        return conflict

    records = _emit_records(candidate_result, identity_maps)
    ref_map = {
        local_ref: canonical_id
        for kind_map in identity_maps.values()
        for local_ref, canonical_id in kind_map.items()
    }
    return NormalizationResult(
        status="normalized",
        _records_json=_canonical_json(records),
        _ref_map_json=_canonical_json(ref_map),
    )
