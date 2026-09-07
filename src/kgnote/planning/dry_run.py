"""Pure comparison of normalized candidates with a canonical snapshot."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

from kgnote.normalization import NormalizationResult


DRY_RUN_RULESET_VERSION = "kgnote.dry-run.v1"
SUPPORTED_SCHEMA_VERSION = "kgnote.v0.1"
TYPE_PREFIXES = {
    "source": "src_",
    "concept": "concept_",
    "evidence": "evidence_",
    "learning_event": "event_",
    "edge": "edge_",
}
REQUIRED_FIELDS = {
    "source": {
        "schema_version", "id", "type", "source_kind", "title", "uri_or_path",
        "content_sha256", "captured_at", "registered_at",
    },
    "concept": {
        "schema_version", "id", "type", "canonical_name", "aliases", "spaces",
        "summary", "status", "evidence_ids", "integration_version", "integrated_at",
    },
    "evidence": {
        "schema_version", "id", "type", "source_id", "locator", "proposition",
        "observed_at", "extractor_version", "extracted_at", "extraction_confidence",
        "review_status",
    },
    "learning_event": {
        "schema_version", "id", "type", "event_type", "occurred_at", "context",
        "source_ids", "concept_ids", "evidence_ids", "extractor_version",
        "extracted_at", "extraction_confidence",
    },
    "edge": {
        "schema_version", "id", "type", "source_id", "relation", "target_id",
        "edge_class", "evidence_ids", "confidence", "ruleset_version", "generated_at",
    },
}
LIST_FIELDS = {
    "concept": ("aliases", "spaces", "evidence_ids"),
    "learning_event": ("source_ids", "concept_ids", "evidence_ids"),
    "edge": ("evidence_ids",),
}
ENUM_FIELDS = {
    "concept": {"status": {"active", "needs_review", "deprecated"}},
    "evidence": {
        "review_status": {"unreviewed", "accepted", "corrected", "rejected"}
    },
    "edge": {
        "edge_class": {"canonical", "learning", "soft_association"},
    },
}


@dataclass(frozen=True)
class DryRunProblem:
    code: str
    path: tuple[object, ...] = ()
    record_id: str | None = None
    reference: str | None = None


@dataclass(frozen=True, repr=False)
class DryRunPlan:
    status: Literal["planned", "rejected"]
    ruleset_version: str = DRY_RUN_RULESET_VERSION
    _items_json: str = field(default="[]", repr=False)
    problem: DryRunProblem | None = None

    @property
    def items(self) -> list[dict[str, Any]]:
        return json.loads(self._items_json)

    def __repr__(self) -> str:
        return (
            "DryRunPlan("
            f"status={self.status!r}, ruleset_version={self.ruleset_version!r}, "
            f"problem={self.problem!r})"
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject(
    code: str,
    *,
    path: tuple[object, ...] = (),
    record_id: str | None = None,
    reference: str | None = None,
) -> DryRunPlan:
    problem = DryRunProblem(code, path, record_id, reference)
    item = {
        "operation": "REJECT",
        "record_id": record_id,
        "record_type": None,
        "changes": [],
        "problem": {
            "code": code,
            "path": list(path),
            "record_id": record_id,
            "reference": reference,
        },
    }
    return DryRunPlan(
        status="rejected",
        _items_json=_canonical_json([item]),
        problem=problem,
    )


def _validate_record(
    record: Any, path: tuple[object, ...]
) -> DryRunProblem | None:
    if not isinstance(record, Mapping):
        return DryRunProblem("record_not_object", path)
    try:
        _canonical_json(record)
    except (TypeError, ValueError):
        return DryRunProblem("record_not_json", path)
    record_id = record.get("id")
    record_type = record.get("type")
    if not isinstance(record_id, str) or not record_id:
        return DryRunProblem("invalid_record_id", path + ("id",))
    if record_type not in TYPE_PREFIXES:
        return DryRunProblem("unsupported_record_type", path + ("type",), record_id)
    if not record_id.startswith(TYPE_PREFIXES[record_type]):
        return DryRunProblem("record_id_type_mismatch", path + ("id",), record_id)
    if re.fullmatch(r"[a-z]+_[A-Za-z0-9][A-Za-z0-9_-]*", record_id) is None:
        return DryRunProblem("unsafe_record_id", path + ("id",), record_id)
    if record.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        return DryRunProblem(
            "unsupported_schema_version", path + ("schema_version",), record_id
        )
    required = REQUIRED_FIELDS[record_type]
    missing = sorted(required - set(record))
    if missing:
        return DryRunProblem("missing_record_field", path + (missing[0],), record_id)
    extra = sorted(set(record) - required)
    if extra:
        return DryRunProblem("unexpected_record_field", path + (extra[0],), record_id)
    for field_name in LIST_FIELDS.get(record_type, ()):
        value = record[field_name]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return DryRunProblem(
                "invalid_reference_list", path + (field_name,), record_id
            )
        if len(value) != len(set(value)):
            return DryRunProblem(
                "duplicate_record_reference", path + (field_name,), record_id
            )
    for field_name, allowed_values in ENUM_FIELDS.get(record_type, {}).items():
        if not isinstance(record[field_name], str) or record[field_name] not in allowed_values:
            return DryRunProblem("invalid_record_enum", path + (field_name,), record_id)

    reference_specs: list[tuple[str, str]] = []
    if record_type == "concept":
        reference_specs.extend((reference, "evidence") for reference in record["evidence_ids"])
    elif record_type == "evidence":
        reference_specs.append((record["source_id"], "source"))
    elif record_type == "learning_event":
        reference_specs.extend((reference, "source") for reference in record["source_ids"])
        reference_specs.extend((reference, "concept") for reference in record["concept_ids"])
        reference_specs.extend((reference, "evidence") for reference in record["evidence_ids"])
    elif record_type == "edge":
        source_type = "learning_event" if record["edge_class"] == "learning" else "concept"
        reference_specs.extend(
            ((record["source_id"], source_type), (record["target_id"], "concept"))
        )
        reference_specs.extend((reference, "evidence") for reference in record["evidence_ids"])
    for reference, expected_type in reference_specs:
        if not isinstance(reference, str) or not reference.startswith(TYPE_PREFIXES[expected_type]):
            return DryRunProblem("invalid_reference_format", path, record_id)
    return None


def _flatten_normalized_records(
    normalized: NormalizationResult,
) -> tuple[list[dict[str, Any]], DryRunPlan | None]:
    if not isinstance(normalized, NormalizationResult) or normalized.status != "normalized":
        return [], _reject("normalization_not_accepted", path=("normalized",))
    records = normalized.records
    if not isinstance(records, Mapping):
        return [], _reject("normalized_records_invalid", path=("normalized", "records"))
    flattened: list[dict[str, Any]] = []
    expected_collections = ("concepts", "evidence", "learning_events", "edges")
    if set(records) != set(expected_collections):
        return [], _reject("normalized_collections_invalid", path=("normalized", "records"))
    for collection in expected_collections:
        values = records[collection]
        if not isinstance(values, list):
            return [], _reject(
                "normalized_collection_not_list",
                path=("normalized", "records", collection),
            )
        for index, record in enumerate(values):
            problem = _validate_record(record, ("normalized", "records", collection, index))
            if problem:
                return [], _reject(
                    problem.code,
                    path=problem.path,
                    record_id=problem.record_id,
                    reference=problem.reference,
                )
            flattened.append(dict(record))
    return flattened, None


def _index_snapshot(
    existing_records: Any,
) -> tuple[dict[str, dict[str, Any]], DryRunPlan | None]:
    if not isinstance(existing_records, Sequence) or isinstance(
        existing_records, (str, bytes, bytearray)
    ):
        return {}, _reject("snapshot_not_list", path=("existing_records",))
    indexed: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(existing_records):
        path = ("existing_records", index)
        problem = _validate_record(record, path)
        if problem:
            return {}, _reject(
                problem.code,
                path=problem.path,
                record_id=problem.record_id,
                reference=problem.reference,
            )
        record_id = record["id"]
        if record_id in indexed:
            return {}, _reject(
                "duplicate_existing_id", path=path + ("id",), record_id=record_id
            )
        indexed[record_id] = json.loads(_canonical_json(record))
    return indexed, None


def _references(record: Mapping[str, Any]) -> list[tuple[str, str, tuple[str, ...]]]:
    record_type = record["type"]
    if record_type == "concept":
        return [(ref, "evidence", ("evidence_ids",)) for ref in record["evidence_ids"]]
    if record_type == "evidence":
        return [(record["source_id"], "source", ("source_id",))]
    if record_type == "learning_event":
        return (
            [(ref, "source", ("source_ids",)) for ref in record["source_ids"]]
            + [(ref, "concept", ("concept_ids",)) for ref in record["concept_ids"]]
            + [(ref, "evidence", ("evidence_ids",)) for ref in record["evidence_ids"]]
        )
    if record_type == "edge":
        source_type = "learning_event" if record["edge_class"] == "learning" else "concept"
        return [
            (record["source_id"], source_type, ("source_id",)),
            (record["target_id"], "concept", ("target_id",)),
            *((ref, "evidence", ("evidence_ids",)) for ref in record["evidence_ids"]),
        ]
    return []


def _preserve_review_state(
    existing: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    effective = json.loads(_canonical_json(candidate))
    if candidate["type"] == "concept" and existing["status"] != "needs_review":
        effective["status"] = existing["status"]
    if candidate["type"] == "evidence" and existing["review_status"] != "unreviewed":
        effective["review_status"] = existing["review_status"]
    return effective


def _changes(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        {"field": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def _is_allowlisted_update(
    before: Mapping[str, Any], after: Mapping[str, Any], changes: list[dict[str, Any]]
) -> bool:
    if before["type"] != "concept" or after["type"] != "concept":
        return False
    changed_fields = {change["field"] for change in changes}
    allowed = {"evidence_ids", "integration_version", "integrated_at"}
    if not changed_fields or not changed_fields <= allowed or "evidence_ids" not in changed_fields:
        return False
    return set(before["evidence_ids"]) < set(after["evidence_ids"])


def _validate_projected_references(
    records_by_id: Mapping[str, Mapping[str, Any]]
) -> DryRunPlan | None:
    for record_id in sorted(records_by_id):
        record = records_by_id[record_id]
        for reference, expected_type, field_path in _references(record):
            target = records_by_id.get(reference)
            if target is None:
                return _reject(
                    "unresolved_projected_reference",
                    path=("projected_records", record_id, *field_path),
                    record_id=record_id,
                    reference=reference,
                )
            if target["type"] != expected_type:
                return _reject(
                    "projected_reference_type_mismatch",
                    path=("projected_records", record_id, *field_path),
                    record_id=record_id,
                    reference=reference,
                )
    return None


def plan_dry_run(
    normalized: NormalizationResult,
    existing_records: Sequence[Mapping[str, Any]],
    *,
    source_candidate: Mapping[str, Any] | None = None,
) -> DryRunPlan:
    """Build an immutable preview without reading, writing, merging, or applying."""

    candidates, rejected = _flatten_normalized_records(normalized)
    if rejected:
        return rejected
    if source_candidate is not None:
        source_problem = _validate_record(source_candidate, ("source_candidate",))
        if source_problem:
            return _reject(
                source_problem.code,
                path=source_problem.path,
                record_id=source_problem.record_id,
                reference=source_problem.reference,
            )
        if source_candidate["type"] != "source":
            return _reject(
                "source_candidate_wrong_type",
                path=("source_candidate", "type"),
                record_id=source_candidate["id"],
            )
        candidates.append(json.loads(_canonical_json(source_candidate)))
    existing_by_id, rejected = _index_snapshot(existing_records)
    if rejected:
        return rejected

    candidate_by_id: dict[str, dict[str, Any]] = {}
    for record in candidates:
        if record["id"] in candidate_by_id:
            return _reject(
                "duplicate_candidate_id",
                path=("normalized", "records"),
                record_id=record["id"],
            )
        candidate_by_id[record["id"]] = record

    items: list[dict[str, Any]] = []
    projected = dict(existing_by_id)
    for record_id in sorted(candidate_by_id):
        candidate = candidate_by_id[record_id]
        existing = existing_by_id.get(record_id)
        if existing is None:
            operation = "CREATE"
            changes = [{"field": "$record", "before": None, "after": candidate}]
            projected[record_id] = candidate
        elif existing["type"] != candidate["type"]:
            operation = "CONFLICT"
            changes = _changes(existing, candidate)
        else:
            effective = _preserve_review_state(existing, candidate)
            changes = _changes(existing, effective)
            if not changes:
                operation = "UNCHANGED"
                projected[record_id] = existing
            elif _is_allowlisted_update(existing, effective, changes):
                operation = "UPDATE"
                projected[record_id] = effective
            else:
                operation = "CONFLICT"
        items.append(
            {
                "operation": operation,
                "record_id": record_id,
                "record_type": candidate["type"],
                "changes": changes,
                "problem": (
                    {"code": "non_allowlisted_difference", "path": [], "record_id": record_id, "reference": None}
                    if operation == "CONFLICT"
                    else None
                ),
            }
        )

    reference_problem = _validate_projected_references(projected)
    if reference_problem:
        return reference_problem
    items.sort(key=lambda item: (item["record_type"] or "", item["record_id"] or ""))
    return DryRunPlan(status="planned", _items_json=_canonical_json(items))


def validate_existing_snapshot(existing_records: Sequence[Mapping[str, Any]]) -> DryRunPlan:
    """Validate a complete canonical snapshot with the same rules used by planning."""

    indexed, rejected = _index_snapshot(existing_records)
    if rejected:
        return rejected
    reference_problem = _validate_projected_references(indexed)
    if reference_problem:
        return reference_problem
    return DryRunPlan(status="planned")
