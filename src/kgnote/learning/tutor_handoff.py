"""Copy-safe, provider-neutral manual tutor handoff and delta import.

This module deliberately has no provider, credential, browser, or network dependency.
It prepares a small, source-grounded continuation packet for a person to copy into
an AI tutor, then accepts only an explicitly pasted structured delta back.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping


HANDOFF_VERSION = "kgnote.manual-tutor-handoff.v1"
DELTA_VERSION = "kgnote.manual-tutor-delta.v1"
HANDOFF_ID = re.compile(r"handoff_[a-f0-9]{32}")
DELTA_ID = re.compile(r"delta_[a-f0-9]{32}")
_LOCK = threading.Lock()


@dataclass(frozen=True, repr=False)
class TutorHandoffResult:
    status: Literal["ready", "imported", "unchanged", "conflict", "rejected", "failed"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: Mapping[str, Any] | None = None, problem: str | None = None) -> TutorHandoffResult:
    return TutorHandoffResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _safe_text(value: Any, *, maximum: int = 2000) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum and "\x00" not in value


def _valid_time(value: Any) -> bool:
    try:
        return isinstance(value, str) and dt.datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_id(prefix: str, value: Mapping[str, Any]) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()[:32]


def build_manual_tutor_handoff(*, resume_context: Mapping[str, Any], evidence: list[Mapping[str, Any]]) -> TutorHandoffResult:
    """Build an exact, copyable continuation packet from local evidence only."""

    if not isinstance(resume_context, Mapping):
        return _result("rejected", problem="invalid_resume_context")
    required = {"learning_unit_id", "source_scope", "structural_breadcrumb", "selected", "unresolved_question"}
    if not required <= set(resume_context) or not _safe_text(resume_context["learning_unit_id"], maximum=300):
        return _result("rejected", problem="invalid_resume_context")
    source_scope = resume_context["source_scope"]
    if not isinstance(source_scope, Mapping) or set(source_scope) != {"source_id", "locator"} or not all(_safe_text(source_scope.get(key), maximum=300) for key in source_scope):
        return _result("rejected", problem="invalid_resume_scope")
    if not _safe_text(resume_context["unresolved_question"]):
        return _result("rejected", problem="missing_unresolved_question")
    if not isinstance(resume_context["structural_breadcrumb"], list) or not resume_context["structural_breadcrumb"]:
        return _result("rejected", problem="invalid_resume_breadcrumb")
    clean_evidence = []
    for item in evidence:
        if not isinstance(item, Mapping) or set(item) != {"source_id", "locator", "proposition"}:
            return _result("rejected", problem="invalid_handoff_evidence")
        if not all(_safe_text(item.get(key)) for key in item):
            return _result("rejected", problem="invalid_handoff_evidence")
        clean_evidence.append(dict(item))
    if not clean_evidence:
        return _result("rejected", problem="missing_handoff_evidence")
    packet = {
        "schema_version": HANDOFF_VERSION,
        "learning_unit_id": resume_context["learning_unit_id"],
        "source_scope": dict(source_scope),
        "structural_breadcrumb": resume_context["structural_breadcrumb"],
        "selected": resume_context["selected"],
        "current_question": resume_context["unresolved_question"],
        "evidence": clean_evidence,
        "known_unknowns": [resume_context["unresolved_question"]],
        "manual_only": True,
        "provider_authorization": "not_requested",
        "import_instructions": "Copy this packet manually. Paste only a separately reviewed delta back; no account authorization or automatic provider access is used.",
    }
    packet["handoff_id"] = _digest_id("handoff_", packet)
    return _result("ready", {"handoff": packet})


def render_manual_tutor_handoff(handoff: Mapping[str, Any]) -> str:
    """Return one copy-safe fenced JSON block; it never embeds credentials or HTML."""

    problem = validate_manual_tutor_handoff(handoff)
    if problem:
        raise ValueError(problem)
    return "```kgnote-manual-tutor-handoff\n" + _canonical(handoff) + "\n```\n"


def validate_manual_tutor_handoff(value: Any) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != HANDOFF_VERSION:
        return "invalid_handoff"
    required = {"schema_version", "handoff_id", "learning_unit_id", "source_scope", "structural_breadcrumb", "selected", "current_question", "evidence", "known_unknowns", "manual_only", "provider_authorization", "import_instructions"}
    if set(value) != required or not HANDOFF_ID.fullmatch(str(value["handoff_id"])):
        return "invalid_handoff_identity"
    canonical = dict(value); handoff_id = canonical.pop("handoff_id")
    if handoff_id != _digest_id("handoff_", canonical) or value["manual_only"] is not True or value["provider_authorization"] != "not_requested":
        return "invalid_handoff_identity"
    if not _safe_text(value["learning_unit_id"], maximum=300) or not _safe_text(value["current_question"]):
        return "invalid_handoff_content"
    if not isinstance(value["evidence"], list) or not value["evidence"]:
        return "invalid_handoff_evidence"
    return None


def make_manual_tutor_delta(*, handoff_id: str, observations: list[Mapping[str, Any]], recorded_at: str) -> TutorHandoffResult:
    """Make the explicit paste-back shape; callers may show it for human review first."""

    if not HANDOFF_ID.fullmatch(handoff_id) or not _valid_time(recorded_at) or not isinstance(observations, list) or not observations:
        return _result("rejected", problem="invalid_delta")
    clean = []
    for item in observations:
        if not isinstance(item, Mapping) or set(item) != {"kind", "text", "evidence_refs"}:
            return _result("rejected", problem="invalid_delta_observation")
        if item.get("kind") not in {"clarification", "question", "application"} or not _safe_text(item.get("text")):
            return _result("rejected", problem="invalid_delta_observation")
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs or any(not _safe_text(ref, maximum=300) for ref in refs):
            return _result("rejected", problem="invalid_delta_observation")
        clean.append({"kind": item["kind"], "text": item["text"], "evidence_refs": list(refs)})
    delta = {"schema_version": DELTA_VERSION, "handoff_id": handoff_id, "recorded_at": recorded_at, "observations": clean, "imported_via": "manual_paste"}
    delta["delta_id"] = _digest_id("delta_", delta)
    return _result("ready", {"delta": delta})


def validate_manual_tutor_delta(value: Any) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != DELTA_VERSION:
        return "invalid_delta"
    required = {"schema_version", "delta_id", "handoff_id", "recorded_at", "observations", "imported_via"}
    if set(value) != required or not DELTA_ID.fullmatch(str(value["delta_id"])) or not HANDOFF_ID.fullmatch(str(value["handoff_id"])):
        return "invalid_delta_identity"
    canonical = dict(value); delta_id = canonical.pop("delta_id")
    if delta_id != _digest_id("delta_", canonical) or value["imported_via"] != "manual_paste" or not _valid_time(value["recorded_at"]):
        return "invalid_delta_identity"
    return None if make_manual_tutor_delta(handoff_id=value["handoff_id"], observations=value["observations"], recorded_at=value["recorded_at"]).status == "ready" else "invalid_delta_observation"


def import_manual_tutor_delta(root: str | os.PathLike[str], delta: Mapping[str, Any]) -> TutorHandoffResult:
    """Append one manually pasted delta once; repeated import is byte-identical no-op."""

    problem = validate_manual_tutor_delta(delta)
    if problem:
        return _result("rejected", problem=problem)
    directory = Path(root) / "manual-tutor-deltas"
    with _LOCK:
        try:
            if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
                return _result("rejected", problem="unsafe_delta_directory")
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            target = directory / f"{delta['delta_id']}.json"
            encoded = (_canonical(delta) + "\n").encode("utf-8")
            if target.exists():
                if target.is_symlink():
                    return _result("rejected", problem="unsafe_delta_target")
                return _result("unchanged", {"delta": dict(delta)}) if target.read_bytes() == encoded else _result("conflict", problem="delta_identity_conflict")
            descriptor, temporary = tempfile.mkstemp(prefix=".delta-", dir=directory)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
        except OSError:
            return _result("failed", problem="delta_write_failed")
    return _result("imported", {"delta": dict(delta)})


__all__ = ["DELTA_VERSION", "HANDOFF_VERSION", "TutorHandoffResult", "build_manual_tutor_handoff", "import_manual_tutor_delta", "make_manual_tutor_delta", "render_manual_tutor_handoff", "validate_manual_tutor_delta", "validate_manual_tutor_handoff"]
