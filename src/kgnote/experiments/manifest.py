"""Fail-closed validation and read-back for formative H0 manifests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "formative-test-manifest" / "v1"
_RANGE = re.compile(r"^L([1-9][0-9]*)-L([1-9][0-9]*)$")


class FormativeManifestError(ValueError):
    def __init__(self, code: str, path: tuple[object, ...] = (), validator: str = "semantic"):
        self.code = code
        self.path = path
        self.validator = validator
        super().__init__(f"{code} at {'/'.join(map(str, path)) or '/'} ({validator})")


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


_MANIFEST_VALIDATOR = _validator("manifest.schema.json")
_RUN_VALIDATOR = _validator("run-record.schema.json")


def _schema_validate(payload: Any, validator: Draft202012Validator, code: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda error: tuple(str(part) for part in error.absolute_path))
    if errors:
        error = errors[0]
        raise FormativeManifestError(code, tuple(error.absolute_path), str(error.validator))


def _line_range(value: str, path: tuple[object, ...]) -> tuple[int, int]:
    match = _RANGE.fullmatch(value)
    if match is None:
        raise FormativeManifestError("invalid_line_range", path)
    start, end = (int(item) for item in match.groups())
    if start > end:
        raise FormativeManifestError("reversed_line_range", path)
    return start, end


def validate_formative_manifest(payload: Any, *, project_root: Path = PROJECT_ROOT) -> None:
    _schema_validate(payload, _MANIFEST_VALIDATOR, "invalid_formative_manifest")
    source = payload["source"]
    selected_start, selected_end = _line_range(source["selected_range"], ("source", "selected_range"))
    fixture = project_root / source["fixture_path"]
    try:
        resolved_root = project_root.resolve(strict=True)
        resolved = fixture.resolve(strict=True)
        resolved.relative_to(resolved_root)
        content = resolved.read_bytes()
    except (OSError, ValueError):
        raise FormativeManifestError("source_fixture_unavailable", ("source", "fixture_path")) from None
    if resolved.is_symlink() or resolved.suffix != ".md":
        raise FormativeManifestError("unsafe_source_fixture", ("source", "fixture_path"))
    if hashlib.sha256(content).hexdigest() != source["content_sha256"]:
        raise FormativeManifestError("source_digest_mismatch", ("source", "content_sha256"))
    try:
        line_count = len(content.decode("utf-8", errors="strict").splitlines())
    except UnicodeDecodeError:
        raise FormativeManifestError("source_invalid_utf8", ("source", "fixture_path")) from None
    if selected_end > line_count:
        raise FormativeManifestError("source_range_out_of_bounds", ("source", "selected_range"))
    claim_ids: set[str] = set()
    for index, claim in enumerate(source["reviewed_claims"]):
        if claim["id"] in claim_ids:
            raise FormativeManifestError("duplicate_claim_id", ("source", "reviewed_claims", index, "id"))
        claim_ids.add(claim["id"])
        start, end = _line_range(claim["source_range"], ("source", "reviewed_claims", index, "source_range"))
        if start < selected_start or end > selected_end:
            raise FormativeManifestError("claim_outside_selected_range", ("source", "reviewed_claims", index, "source_range"))
        for range_index, upstream_range in enumerate(claim["upstream_ranges"]):
            _line_range(upstream_range, ("source", "reviewed_claims", index, "upstream_ranges", range_index))
    ratings = [item["value"] for item in payload["pretest"]["rating_scale"]]
    if len(ratings) != len(set(ratings)) or ratings != sorted(ratings):
        raise FormativeManifestError("invalid_pretest_scale", ("pretest", "rating_scale"))
    if not set(payload["pretest"]["eligible_ratings"]).issubset(ratings):
        raise FormativeManifestError("unknown_eligible_rating", ("pretest", "eligible_ratings"))
    condition_ids = [condition["condition_id"] for condition in payload["conditions"]]
    if set(condition_ids) != {"baseline_markdown", "kgnote_no_graph"}:
        raise FormativeManifestError("missing_required_condition", ("conditions",))
    for index, condition in enumerate(payload["conditions"]):
        start, end = _line_range(condition["source_range"], ("conditions", index, "source_range"))
        if start < selected_start or end > selected_end:
            raise FormativeManifestError("condition_outside_selected_range", ("conditions", index, "source_range"))
    dimensions = [item["dimension"] for item in payload["rubric"]]
    if len(dimensions) != len(set(dimensions)):
        raise FormativeManifestError("duplicate_rubric_dimension", ("rubric",))


def validate_formative_run_record(payload: Any, manifest: Any) -> None:
    _schema_validate(payload, _RUN_VALIDATOR, "invalid_formative_run_record")
    validate_formative_manifest(manifest)
    if payload["manifest_id"] != manifest["id"] or payload["source_sha256"] != manifest["source"]["content_sha256"]:
        raise FormativeManifestError("run_manifest_mismatch")
    observation_ids = [item["condition_id"] for item in payload["observations"]]
    if len(observation_ids) != len(set(observation_ids)):
        raise FormativeManifestError("duplicate_condition_observation", ("observations",))
    if payload["pretest"] is not None:
        expected = payload["pretest"]["rating"] in manifest["pretest"]["eligible_ratings"]
        if payload["pretest"]["eligible"] is not expected:
            raise FormativeManifestError("pretest_eligibility_mismatch", ("pretest", "eligible"))
    rubric_maximums = {item["dimension"]: item["max_points"] for item in manifest["rubric"]}
    for index, observation in enumerate(payload["observations"]):
        for dimension, score in observation["rubric_scores"].items():
            if dimension not in rubric_maximums:
                raise FormativeManifestError("unknown_rubric_dimension", ("observations", index, "rubric_scores", dimension))
            if score > rubric_maximums[dimension]:
                raise FormativeManifestError("rubric_score_exceeds_maximum", ("observations", index, "rubric_scores", dimension))
    if payload["status"] == "completed":
        complete_scores = all(set(item["rubric_scores"]) == set(rubric_maximums) for item in payload["observations"])
        complete_fields = ("ended_at", "help_count", "save_reopen_success", "lookup_seconds", "lookup_errors", "notes_sha256", "unaided_response", "confidence")
        complete_observations = all(all(item[field] is not None for field in complete_fields) for item in payload["observations"])
        if set(observation_ids) != {"baseline_markdown", "kgnote_no_graph"} or not complete_scores or not complete_observations or payload["decision"] is None or payload["completed_at"] is None:
            raise FormativeManifestError("incomplete_completed_run")
    if payload["status"] == "pretest_excluded" and (payload["pretest"] is None or payload["pretest"]["eligible"]):
        raise FormativeManifestError("invalid_pretest_exclusion")


def load_formative_manifest(path: str | Path, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    supplied = Path(path)
    try:
        content = supplied.read_text(encoding="utf-8")
        payload = yaml.safe_load(content)
    except (OSError, UnicodeError, yaml.YAMLError):
        raise FormativeManifestError("manifest_unreadable") from None
    validate_formative_manifest(payload, project_root=project_root)
    return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


__all__ = [
    "FormativeManifestError", "load_formative_manifest",
    "validate_formative_manifest", "validate_formative_run_record",
]
