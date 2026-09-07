"""Validate one untrusted offline JSON response without network or persistence."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from kgnote.contracts.extraction import (
    ExtractionOutputValidationError,
    validate_extraction_input,
    validate_extraction_output,
)


RAW_COLLECTIONS = frozenset({"concepts", "evidence", "learning_events", "edges"})
ADAPTER_OWNED_FIELDS = frozenset(
    {"schema_version", "source_id", "extractor_version", "generated_at"}
)


@dataclass(frozen=True)
class ExtractionRejection:
    code: str
    path: tuple[object, ...]
    validator: str


@dataclass(frozen=True, repr=False)
class ExtractionAttempt:
    status: Literal["accepted", "rejected"]
    raw_response: str = field(repr=False)
    raw_response_sha256: str
    _candidate_result_json: str | None = field(default=None, repr=False)
    rejection: ExtractionRejection | None = None

    @property
    def candidate_result(self) -> dict[str, Any] | None:
        """Return a fresh value so callers cannot mutate the recorded attempt."""

        if self._candidate_result_json is None:
            return None
        return json.loads(self._candidate_result_json)

    def __repr__(self) -> str:
        return (
            "ExtractionAttempt("
            f"status={self.status!r}, "
            f"raw_response_sha256={self.raw_response_sha256!r}, "
            f"rejection={self.rejection!r})"
        )


def _response_hash(raw_response: str) -> str:
    return hashlib.sha256(raw_response.encode("utf-8")).hexdigest()


def _reject(
    *,
    raw_response: str,
    code: str,
    path: tuple[object, ...] = (),
    validator: str,
) -> ExtractionAttempt:
    return ExtractionAttempt(
        status="rejected",
        raw_response=raw_response,
        raw_response_sha256=_response_hash(raw_response),
        rejection=ExtractionRejection(code=code, path=path, validator=validator),
    )


def _inject_source_id(collection: Any, source_id: str) -> Any:
    if not isinstance(collection, list):
        return collection
    injected = copy.deepcopy(collection)
    for candidate in injected:
        if isinstance(candidate, dict):
            candidate["source_id"] = source_id
    return injected


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON constant")


def replay_extraction_response(
    *,
    extraction_input: Mapping[str, Any],
    raw_response: str,
    extractor_version: str,
    generated_at: str,
) -> ExtractionAttempt:
    """Replay one raw response into an accepted or rejected immutable attempt."""

    validate_extraction_input(extraction_input)
    if not isinstance(raw_response, str):
        return _reject(
            raw_response="",
            code="invalid_response_type",
            validator="type",
        )

    try:
        body = json.loads(
            raw_response,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, UnicodeError, ValueError):
        return _reject(
            raw_response=raw_response,
            code="invalid_json",
            validator="json_parse",
        )

    if not isinstance(body, dict):
        return _reject(
            raw_response=raw_response,
            code="non_object_root",
            validator="type",
        )

    unknown_fields = sorted(set(body) - RAW_COLLECTIONS)
    if unknown_fields:
        field_name = unknown_fields[0]
        code = (
            "adapter_owned_field"
            if field_name in ADAPTER_OWNED_FIELDS
            else "unknown_response_field"
        )
        return _reject(
            raw_response=raw_response,
            code=code,
            path=(field_name,),
            validator="additionalProperties",
        )

    missing_fields = sorted(RAW_COLLECTIONS - set(body))
    if missing_fields:
        return _reject(
            raw_response=raw_response,
            code="missing_candidate_collection",
            path=(missing_fields[0],),
            validator="required",
        )

    for collection_name in ("evidence", "learning_events"):
        collection = body[collection_name]
        if not isinstance(collection, list):
            continue
        for index, candidate in enumerate(collection):
            if isinstance(candidate, dict) and "source_id" in candidate:
                return _reject(
                    raw_response=raw_response,
                    code="adapter_owned_field",
                    path=(collection_name, index, "source_id"),
                    validator="additionalProperties",
                )

    source_id = extraction_input["source"]["id"]
    candidate_result = {
        "schema_version": "kgnote.extraction-output.v1",
        "source_id": source_id,
        "extractor_version": extractor_version,
        "generated_at": generated_at,
        "concepts": copy.deepcopy(body["concepts"]),
        "evidence": _inject_source_id(body["evidence"], source_id),
        "learning_events": _inject_source_id(body["learning_events"], source_id),
        "edges": copy.deepcopy(body["edges"]),
    }

    try:
        validate_extraction_output(candidate_result)
    except ExtractionOutputValidationError as error:
        if error.path == ("extractor_version",):
            code = "invalid_extractor_version"
        elif error.path == ("generated_at",):
            code = "invalid_generated_at"
        else:
            code = error.code
        return _reject(
            raw_response=raw_response,
            code=code,
            path=error.path,
            validator=error.validator,
        )

    candidate_result_json = json.dumps(
        candidate_result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return ExtractionAttempt(
        status="accepted",
        raw_response=raw_response,
        raw_response_sha256=_response_hash(raw_response),
        _candidate_result_json=candidate_result_json,
    )
