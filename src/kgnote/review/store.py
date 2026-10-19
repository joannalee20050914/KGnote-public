"""Append-only local persistence for human-reviewed recall interactions."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from .application import load_reviewer_context


REVIEW_RECORD_VERSION = "kgnote.review-interaction.v1"
OUTCOMES = {"CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"}
ID_PATTERN = re.compile(r"review_[a-f0-9]{64}")


@dataclass(frozen=True, repr=False)
class ReviewStoreResult:
    status: Literal["ready", "recorded", "unchanged", "rejected"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


def _result(status: str, payload: dict[str, Any] | None = None, problem: str | None = None) -> ReviewStoreResult:
    return ReviewStoreResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _safe_text(value: Any, maximum: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _reviews_dir(root: Path, *, create: bool) -> Path | None:
    directory = root / "reviews"
    if directory.exists():
        return directory if directory.is_dir() and not directory.is_symlink() else None
    if not create:
        return directory
    try:
        directory.mkdir(mode=0o700)
    except OSError:
        return None
    return directory


def _previous_reviews(root: Path, concept_id: str) -> list[dict[str, Any]]:
    directory = _reviews_dir(root, create=False)
    if directory is None or not directory.exists():
        return []
    reviews = []
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []
    for path in entries:
        if path.is_symlink() or not path.is_file() or not ID_PATTERN.fullmatch(path.stem):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n") or "\n---\n" not in text[4:]:
                continue
            record = yaml.safe_load(text[4:text.find("\n---\n", 4)])
        except (OSError, UnicodeError, yaml.YAMLError):
            continue
        if isinstance(record, dict) and record.get("schema_version") == REVIEW_RECORD_VERSION and record.get("concept_ids") == [concept_id]:
            reviews.append({key: record.get(key) for key in ("id", "occurred_at", "question", "response", "hint_used", "outcome", "reviewer_version")})
    return sorted(reviews, key=lambda item: (str(item["occurred_at"]), str(item["id"])), reverse=True)


def build_prompt_from_context(context: dict[str, Any]) -> dict[str, Any]:
    """Prefer an evidence-backed distinction when an explicit confusion pair exists."""
    focus = context["focus"]
    nodes = {node["id"]: node for node in [focus, *context["neighborhood"]["nodes"]]}
    pairs: list[tuple[str, str]] = []
    for event in context["previous_confusion"]["events"]:
        concept_ids = sorted({concept_id for concept_id in event.get("concept_ids", []) if concept_id in nodes and nodes[concept_id].get("kind") == "concept"})
        if focus["id"] in concept_ids:
            pairs.extend((focus["id"], concept_id) for concept_id in concept_ids if concept_id != focus["id"])
    for link in context["previous_confusion"]["links"]:
        endpoints = [concept_id for concept_id in (link.get("source_id"), link.get("target_id")) if concept_id in nodes and nodes[concept_id].get("kind") == "concept"]
        if len(endpoints) == 2 and focus["id"] in endpoints:
            pairs.append((focus["id"], next(concept_id for concept_id in endpoints if concept_id != focus["id"])))
    if pairs:
        left_id, right_id = sorted(set(pairs))[0]
        left, right = nodes[left_id]["label"], nodes[right_id]["label"]
        return {"activity_type": "distinction", "question": f"請區分「{left}」與「{right}」，並用一個判斷線索說明何時是哪一個。", "hint": f"先說共同點，再找能把「{left}」和「{right}」分開的條件。", "confusion_pair": [left_id, right_id]}
    return {"activity_type": "free_recall", "question": f"請用自己的話解釋「{focus['label']}」，並說明它在什麼情況下有用。", "hint": focus["summary"], "confusion_pair": None}


def build_review_prompt(root: str | os.PathLike[str], concept_id: str) -> ReviewStoreResult:
    """Build one deterministic free-recall question from bounded reviewer context."""
    context_result = load_reviewer_context(root, concept_id)
    if context_result.status != "ready":
        return _result("rejected", problem="context_unavailable")
    context = context_result.response["context"]
    focus = context["focus"]
    prompt_spec = build_prompt_from_context(context)
    return _result("ready", {
        "schema_version": "kgnote.review-prompt.v1",
        "concept_id": concept_id,
        "concept_label": focus["label"],
        "question": prompt_spec["question"],
        "hint": prompt_spec["hint"],
        "activity_type": prompt_spec["activity_type"],
        "confusion_pair": prompt_spec["confusion_pair"],
        "snapshot_sha256": context["snapshot_sha256"],
        "evidence": context["evidence"],
        "evidence_ids": [item["id"] for item in context["evidence"]],
        "previous_reviews": _previous_reviews(Path(root), concept_id),
    })


def append_review(root: str | os.PathLike[str], request: Any, *, recorded_at: str | None = None) -> ReviewStoreResult:
    """Validate and atomically append one self-assessed interaction."""
    if not isinstance(request, dict) or set(request) != {"concept_id", "question", "response", "hint_used", "outcome", "snapshot_sha256", "evidence_ids"}:
        return _result("rejected", problem="invalid_request")
    if not (_safe_text(request["concept_id"], 160) and _safe_text(request["question"], 1000) and _safe_text(request["response"], 4000)):
        return _result("rejected", problem="invalid_text")
    if not isinstance(request["hint_used"], bool) or request["outcome"] not in OUTCOMES:
        return _result("rejected", problem="invalid_assessment")
    if re.fullmatch(r"[a-f0-9]{64}", str(request["snapshot_sha256"])) is None:
        return _result("rejected", problem="invalid_snapshot")
    if not isinstance(request["evidence_ids"], list) or not all(isinstance(item, str) for item in request["evidence_ids"]):
        return _result("rejected", problem="invalid_evidence")

    prompt = build_review_prompt(root, request["concept_id"])
    if prompt.status != "ready":
        return prompt
    expected = prompt.payload
    if any((request["question"] != expected["question"], request["snapshot_sha256"] != expected["snapshot_sha256"], request["evidence_ids"] != expected["evidence_ids"])):
        return _result("rejected", problem="stale_review")

    timestamp = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return _result("rejected", problem="invalid_recorded_at")
    identity = json.dumps({**request, "recorded_at": timestamp}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    review_id = "review_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    record = {
        "schema_version": REVIEW_RECORD_VERSION,
        "id": review_id,
        "type": "review_interaction",
        "concept_ids": [request["concept_id"]],
        "occurred_at": timestamp,
        "prompt_stage": expected["activity_type"],
        "question": request["question"],
        "response": request["response"],
        "hint_used": request["hint_used"],
        "outcome": request["outcome"].lower(),
        "evidence_ids": request["evidence_ids"],
        "snapshot_sha256": request["snapshot_sha256"],
        "reviewer_version": "human-self-assessment.v1",
        "recorded_at": timestamp,
    }
    root_path = Path(root)
    directory = _reviews_dir(root_path, create=True)
    if directory is None:
        return _result("rejected", problem="unsafe_reviews_directory")
    target = directory / f"{review_id}.md"
    body = yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=4096)
    content = f"---\n{body}---\n\n# Review · {expected['concept_label']}\n".encode("utf-8")
    if target.exists():
        try:
            return _result("unchanged" if target.read_bytes() == content else "rejected", {"review_id": review_id}, None if target.read_bytes() == content else "review_id_conflict")
        except OSError:
            return _result("rejected", problem="review_read_failed")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{review_id}.", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except OSError:
        return _result("rejected", problem="review_write_failed")
    finally:
        temporary.unlink(missing_ok=True)
    return _result("recorded", {"review_id": review_id, "recorded_at": timestamp})
