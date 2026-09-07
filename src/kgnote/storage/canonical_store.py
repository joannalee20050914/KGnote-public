"""Explicit-root canonical Markdown reader and approved idempotent apply."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

import yaml

from kgnote.planning import DryRunPlan, validate_existing_snapshot


STORE_ADAPTER_VERSION = "kgnote.canonical-store.v1"
TYPE_DIRECTORIES = {
    "source": "sources",
    "concept": "concepts",
    "evidence": "evidence",
    "learning_event": "learning-events",
    "edge": "edges",
}
DIRECTORY_TYPES = {directory: record_type for record_type, directory in TYPE_DIRECTORIES.items()}


@dataclass(frozen=True)
class StoreProblem:
    code: str
    path: str | None = None
    record_id: str | None = None


@dataclass(frozen=True, repr=False)
class StoreDocument:
    record_id: str
    relative_path: str
    content_sha256: str
    original_bytes: bytes = field(repr=False)
    body: str = field(repr=False)


@dataclass(frozen=True, repr=False)
class StoreSnapshot:
    status: Literal["loaded", "rejected"]
    root: str
    adapter_version: str = STORE_ADAPTER_VERSION
    _records_json: str = field(default="[]", repr=False)
    documents: tuple[StoreDocument, ...] = field(default=(), repr=False)
    problem: StoreProblem | None = None

    @property
    def records(self) -> list[dict[str, Any]]:
        return json.loads(self._records_json)

    def __repr__(self) -> str:
        return (
            "StoreSnapshot("
            f"status={self.status!r}, root={self.root!r}, "
            f"adapter_version={self.adapter_version!r}, problem={self.problem!r})"
        )


@dataclass(frozen=True, repr=False)
class ApplyResult:
    status: Literal["applied", "rejected", "failed"]
    plan_digest: str | None = None
    created_paths: tuple[str, ...] = ()
    updated_paths: tuple[str, ...] = ()
    unchanged_paths: tuple[str, ...] = ()
    backup_paths: tuple[str, ...] = ()
    recovered: bool = False
    write_count: int = 0
    audit_snapshot: StoreSnapshot | None = field(default=None, repr=False)
    problem: StoreProblem | None = None

    def __repr__(self) -> str:
        return (
            "ApplyResult("
            f"status={self.status!r}, plan_digest={self.plan_digest!r}, "
            f"write_count={self.write_count!r}, recovered={self.recovered!r}, "
            f"problem={self.problem!r})"
        )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_value(child) for child in value]
    return value


def _reject_snapshot(root: Path, code: str, path: str | None = None) -> StoreSnapshot:
    return StoreSnapshot(
        status="rejected",
        root=str(root),
        problem=StoreProblem(code=code, path=path),
    )


def _split_markdown(content: bytes) -> tuple[dict[str, Any], str] | StoreProblem:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return StoreProblem("invalid_utf8")
    if not text.startswith("---\n"):
        return StoreProblem("missing_front_matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        return StoreProblem("malformed_front_matter")
    front_matter = text[4:end]
    body = text[end + 5 :]
    try:
        loaded = yaml.safe_load(front_matter)
    except yaml.YAMLError:
        return StoreProblem("malformed_yaml")
    if not isinstance(loaded, dict):
        return StoreProblem("front_matter_not_object")
    return _json_value(loaded), body


def read_canonical_store(root: str | os.PathLike[str]) -> StoreSnapshot:
    """Read only direct Markdown children of canonical directories under root."""

    supplied_root = Path(root)
    if supplied_root.is_symlink():
        return _reject_snapshot(supplied_root, "store_root_symlink")
    try:
        resolved_root = supplied_root.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return _reject_snapshot(supplied_root, "store_root_missing")
    if not resolved_root.is_dir():
        return _reject_snapshot(resolved_root, "store_root_not_directory")

    records: list[dict[str, Any]] = []
    documents: list[StoreDocument] = []
    for directory_name in sorted(DIRECTORY_TYPES):
        directory = resolved_root / directory_name
        if not directory.exists():
            return _reject_snapshot(resolved_root, "canonical_directory_missing", directory_name)
        if directory.is_symlink() or not directory.is_dir():
            return _reject_snapshot(resolved_root, "unsafe_canonical_directory", directory_name)
        try:
            entries = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return _reject_snapshot(resolved_root, "canonical_directory_unreadable", directory_name)
        for entry in entries:
            relative = entry.relative_to(resolved_root).as_posix()
            if entry.is_symlink():
                return _reject_snapshot(resolved_root, "store_symlink_not_allowed", relative)
            if not entry.is_file() or entry.suffix != ".md":
                return _reject_snapshot(resolved_root, "unexpected_store_entry", relative)
            try:
                original = entry.read_bytes()
            except OSError:
                return _reject_snapshot(resolved_root, "store_file_unreadable", relative)
            parsed = _split_markdown(original)
            if isinstance(parsed, StoreProblem):
                return _reject_snapshot(resolved_root, parsed.code, relative)
            record, body = parsed
            record_id = record.get("id")
            if not isinstance(record_id, str) or entry.name != f"{record_id}.md":
                return _reject_snapshot(resolved_root, "filename_id_mismatch", relative)
            if record.get("type") != DIRECTORY_TYPES[directory_name]:
                return _reject_snapshot(resolved_root, "directory_type_mismatch", relative)
            records.append(record)
            documents.append(
                StoreDocument(record_id, relative, _sha256(original), original, body)
            )

    validation = validate_existing_snapshot(records)
    if validation.status == "rejected":
        problem = validation.problem
        return StoreSnapshot(
            status="rejected",
            root=str(resolved_root),
            problem=StoreProblem(
                code=f"snapshot_{problem.code}",
                path="/".join(str(part) for part in problem.path),
                record_id=problem.record_id,
            ),
        )
    records.sort(key=lambda record: (record["type"], record["id"]))
    documents.sort(key=lambda document: document.relative_path)
    return StoreSnapshot(
        status="loaded",
        root=str(resolved_root),
        _records_json=_canonical_json(records),
        documents=tuple(documents),
    )


def plan_digest(plan: DryRunPlan) -> str:
    """Bind approval to the exact ruleset and plan items."""

    payload = {"ruleset_version": plan.ruleset_version, "items": plan.items}
    return _sha256(_canonical_json(payload).encode("utf-8"))


def _render_record(record: Mapping[str, Any], body: str) -> bytes:
    front_matter = yaml.safe_dump(
        dict(record),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=4096,
    )
    return f"---\n{front_matter}---\n{body}".encode("utf-8")


def _created_body(record: Mapping[str, Any]) -> str:
    title = record.get("canonical_name") or record.get("proposition") or record.get("event_type") or record["id"]
    links: list[str] = []
    if record["type"] == "source":
        raw_path = str(record["uri_or_path"])
        links.append(f"Raw evidence: [[{raw_path.removesuffix('.md')}]]")
    elif record["type"] == "concept":
        links.extend(f"Evidence: [[{record_id}]]" for record_id in record["evidence_ids"])
    elif record["type"] == "evidence":
        links.append(f"Source: [[{record['source_id']}]]")
    elif record["type"] == "learning_event":
        links.extend(f"Source: [[{record_id}]]" for record_id in record["source_ids"])
        links.extend(f"Concept: [[{record_id}]]" for record_id in record["concept_ids"])
        links.extend(f"Evidence: [[{record_id}]]" for record_id in record["evidence_ids"])
    elif record["type"] == "edge":
        links.extend((f"Source node: [[{record['source_id']}]]", f"Target node: [[{record['target_id']}]]"))
        links.extend(f"Evidence: [[{record_id}]]" for record_id in record["evidence_ids"])
    link_section = "\n".join(links)
    return f"\n# {title}\n" + (f"\n{link_section}\n" if link_section else "")


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_create(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _rollback(completed: Sequence[tuple[str, str, Path, bytes | None]]) -> bool:
    recovered = True
    for operation, _, target, original in reversed(completed):
        try:
            if operation == "CREATE":
                target.unlink(missing_ok=True)
            elif original is not None:
                _atomic_write(target, original)
        except OSError:
            recovered = False
    return recovered


def _apply_problem(code: str, path: str | None = None, record_id: str | None = None) -> ApplyResult:
    return ApplyResult(status="rejected", problem=StoreProblem(code, path, record_id))


def apply_approved_plan(
    root: str | os.PathLike[str],
    snapshot: StoreSnapshot,
    plan: DryRunPlan,
    approved_digest: str | None,
    *,
    atomic_writer: Callable[[Path, bytes], None] = _atomic_write,
    atomic_creator: Callable[[Path, bytes], None] = _atomic_create,
) -> ApplyResult:
    """Apply only an exact approved, conflict-free plan and audit by re-reading."""

    if snapshot.status != "loaded":
        return _apply_problem("snapshot_not_loaded")
    try:
        resolved_root = Path(root).resolve(strict=True)
    except (FileNotFoundError, OSError):
        return _apply_problem("store_root_missing")
    if str(resolved_root) != snapshot.root:
        return _apply_problem("snapshot_root_mismatch")
    if plan.status != "planned":
        return _apply_problem("plan_not_applicable")
    digest = plan_digest(plan)
    if approved_digest is None:
        return _apply_problem("approval_required")
    if approved_digest != digest:
        return _apply_problem("approval_digest_mismatch")
    items = plan.items
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return _apply_problem("invalid_plan_item", str(index))
        if set(item) != {"operation", "record_id", "record_type", "changes", "problem"}:
            return _apply_problem("invalid_plan_item", str(index))
        if item["operation"] not in {"CREATE", "UPDATE", "UNCHANGED", "CONFLICT", "REJECT"}:
            return _apply_problem("invalid_plan_operation", str(index))
        if item["record_type"] not in TYPE_DIRECTORIES or not isinstance(item["record_id"], str):
            return _apply_problem("invalid_plan_target", str(index))
        if not isinstance(item["changes"], list):
            return _apply_problem("invalid_plan_changes", str(index), item["record_id"])
    if any(item["operation"] in {"CONFLICT", "REJECT"} for item in items):
        return _apply_problem("plan_contains_blocking_operation")

    records_by_id = {record["id"]: record for record in snapshot.records}
    documents_by_id = {document.record_id: document for document in snapshot.documents}
    projected = json.loads(_canonical_json(records_by_id))
    actions: list[tuple[str, str, Path, bytes, bytes | None]] = []
    unchanged_paths: list[str] = []

    for item in items:
        operation = item["operation"]
        record_id = item["record_id"]
        record_type = item["record_type"]
        relative = f"{TYPE_DIRECTORIES[record_type]}/{record_id}.md"
        target = resolved_root / relative
        if operation == "UNCHANGED":
            if record_id not in records_by_id or records_by_id[record_id]["type"] != record_type:
                return _apply_problem("unchanged_record_missing", relative, record_id)
            unchanged_paths.append(relative)
            continue
        if operation == "CREATE":
            if target.exists() or target.is_symlink():
                return _apply_problem("create_target_exists", relative, record_id)
            change = next((change for change in item["changes"] if change["field"] == "$record"), None)
            if change is None or change["before"] is not None or not isinstance(change["after"], dict):
                return _apply_problem("invalid_create_preview", relative, record_id)
            projected[record_id] = change["after"]
            actions.append((operation, relative, target, _render_record(change["after"], _created_body(change["after"])), None))
            continue
        if operation != "UPDATE" or record_id not in records_by_id:
            return _apply_problem("invalid_update_preview", relative, record_id)
        document = documents_by_id[record_id]
        try:
            current = target.read_bytes() if target.is_file() and not target.is_symlink() else None
        except OSError:
            return _apply_problem("target_unreadable", relative, record_id)
        if current is None or _sha256(current) != document.content_sha256:
            return _apply_problem("stale_precondition", relative, record_id)
        updated = json.loads(_canonical_json(records_by_id[record_id]))
        for change in item["changes"]:
            if change["field"] not in {"evidence_ids", "integration_version", "integrated_at"}:
                return _apply_problem("update_field_not_allowed", relative, record_id)
            if updated.get(change["field"]) != change["before"]:
                return _apply_problem("update_before_mismatch", relative, record_id)
            updated[change["field"]] = change["after"]
        if not set(records_by_id[record_id]["evidence_ids"]) < set(updated["evidence_ids"]):
            return _apply_problem("update_not_additive", relative, record_id)
        projected[record_id] = updated
        actions.append((operation, relative, target, _render_record(updated, document.body), current))

    validation = validate_existing_snapshot(list(projected.values()))
    if validation.status == "rejected":
        return _apply_problem("projected_snapshot_invalid")

    # Recheck every planned snapshot file immediately before the first write.
    for directory_name in TYPE_DIRECTORIES.values():
        directory = resolved_root / directory_name
        if directory.is_symlink() or not directory.is_dir():
            return _apply_problem("unsafe_canonical_directory", directory_name)
    for document in snapshot.documents:
        path = resolved_root / document.relative_path
        try:
            unchanged = (
                not path.is_symlink()
                and path.is_file()
                and _sha256(path.read_bytes()) == document.content_sha256
            )
        except OSError:
            unchanged = False
        if not unchanged:
            return _apply_problem("stale_precondition", document.relative_path, document.record_id)

    backup_root = resolved_root / ".kgnote-backups" / digest
    backup_paths: list[str] = []
    created_paths: list[str] = []
    updated_paths: list[str] = []
    completed: list[tuple[str, str, Path, bytes | None]] = []
    backup_base = resolved_root / ".kgnote-backups"
    if backup_base.exists() and (backup_base.is_symlink() or not backup_base.is_dir()):
        return _apply_problem("unsafe_backup_directory", ".kgnote-backups")
    if backup_root.exists() and (backup_root.is_symlink() or not backup_root.is_dir()):
        return _apply_problem("unsafe_backup_directory", backup_root.relative_to(resolved_root).as_posix())
    for operation, relative, _, _, original in actions:
        if operation == "UPDATE" and original is not None:
            backup = backup_root / relative
            if backup.parent.exists() and (backup.parent.is_symlink() or not backup.parent.is_dir()):
                return _apply_problem("unsafe_backup_directory", backup.parent.relative_to(resolved_root).as_posix())
            try:
                collision = backup.exists() and (
                    backup.is_symlink() or not backup.is_file() or backup.read_bytes() != original
                )
            except OSError:
                return _apply_problem("backup_unreadable", backup.relative_to(resolved_root).as_posix())
            if collision:
                return _apply_problem("backup_collision", backup.relative_to(resolved_root).as_posix())
    try:
        for operation, relative, target, content, original in actions:
            target.parent.mkdir(parents=True, exist_ok=True)
            if operation == "UPDATE":
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                if not backup.exists():
                    shutil.copyfile(target, backup)
                backup_paths.append(backup.relative_to(resolved_root).as_posix())
            (atomic_creator if operation == "CREATE" else atomic_writer)(target, content)
            completed.append((operation, relative, target, original))
            (created_paths if operation == "CREATE" else updated_paths).append(relative)
    except (OSError, RuntimeError):
        recovered = _rollback(completed)
        return ApplyResult(
            status="failed",
            plan_digest=digest,
            created_paths=tuple(created_paths),
            updated_paths=tuple(updated_paths),
            unchanged_paths=tuple(unchanged_paths),
            backup_paths=tuple(backup_paths),
            recovered=recovered,
            write_count=len(completed),
            problem=StoreProblem("write_failed_recovered" if recovered else "write_failed_recovery_incomplete"),
        )

    audit = read_canonical_store(resolved_root)
    expected = sorted(projected.values(), key=lambda record: (record["type"], record["id"]))
    if audit.status != "loaded" or audit.records != expected:
        recovered = _rollback(completed)
        return ApplyResult(
            status="failed",
            plan_digest=digest,
            created_paths=tuple(created_paths),
            updated_paths=tuple(updated_paths),
            unchanged_paths=tuple(unchanged_paths),
            backup_paths=tuple(backup_paths),
            recovered=recovered,
            write_count=len(completed),
            audit_snapshot=audit,
            problem=StoreProblem("read_back_mismatch"),
        )
    return ApplyResult(
        status="applied",
        plan_digest=digest,
        created_paths=tuple(created_paths),
        updated_paths=tuple(updated_paths),
        unchanged_paths=tuple(unchanged_paths),
        backup_paths=tuple(backup_paths),
        write_count=len(completed),
        audit_snapshot=audit,
    )
