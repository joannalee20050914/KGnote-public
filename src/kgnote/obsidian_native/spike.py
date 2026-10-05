"""Build deterministic JSON Canvas navigation over a Personal Alpha workspace."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from kgnote.personal_alpha import PersonalAlphaPreview, project_learner_workspace


NATIVE_MANIFEST_VERSION = "kgnote.obsidian-native-spike.v1"
CANVAS_PATH = PurePosixPath("Learning Structure.canvas")
GUIDE_PATH = PurePosixPath("Canvas Guide.md")
MANIFEST_PATH = PurePosixPath(".kgnote/native-manifest.json")
ENTRY_PATH = PurePosixPath("Start Here.md")
WORKSPACE_MANIFEST_PATH = PurePosixPath(".kgnote/manifest.json")
APPEARANCE_PATH = PurePosixPath(".obsidian/appearance.json")
READING_CSS_PATH = PurePosixPath(".obsidian/snippets/kgnote-reading.css")


class NativeSpikeError(RuntimeError):
    def __init__(self, code: str, message: str, action: str):
        self.code = code
        self.action = action
        super().__init__(message)


@dataclass(frozen=True)
class NativeSpikeResult:
    status: str
    workspace_path: str
    canvas_path: str
    guide_path: str
    source_shape: str
    canonical_digest: str
    markdown_digest: str
    node_count: int
    edge_count: int
    recovered_interrupted_transaction: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "workspace_path": self.workspace_path,
            "canvas_path": self.canvas_path,
            "guide_path": self.guide_path,
            "source_shape": self.source_shape,
            "canonical_digest": self.canonical_digest,
            "markdown_digest": self.markdown_digest,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "recovered_interrupted_transaction": self.recovered_interrupted_transaction,
        }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_id(kind: str, *parts: str) -> str:
    value = "\0".join((kind, *parts)).encode("utf-8")
    return f"{kind}-" + hashlib.sha256(value).hexdigest()[:16]


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    identity = {
        "source": {
            "id": payload["source"]["id"],
            "content_sha256": payload["source"]["content_sha256"],
        },
        "concepts": [item["id"] for item in payload["concepts"]],
        "relations": [
            {
                "id": item["id"],
                "subject": item["subject_concept_id"],
                "relation": item["relation"],
                "object": item["object_concept_id"],
                "evidence_ids": item["evidence_ids"],
            }
            for item in payload["relations"]
        ],
        "evidence": [item["id"] for item in payload["evidence"]],
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical.encode("utf-8"))


def _markdown_digest(workspace: Path) -> str:
    """Bind native artifacts to generated Markdown without owning learner notes.

    The Personal Alpha manifest is the ownership boundary. User-owned files such as
    My Notes and Continue Here, plus any unmanaged learner Markdown, must remain
    editable without making the optional Canvas candidate stale.
    """

    manifest = _load_workspace_manifest(workspace)
    rows: list[dict[str, str]] = []
    managed_paths = sorted(
        str(row.get("path", ""))
        for row in manifest["managed_files"]
        if isinstance(row, Mapping)
    )
    for relative in managed_paths:
        relative_path = _safe_relative(relative)
        if relative_path.suffix.casefold() != ".md":
            continue
        path = workspace / Path(*relative_path.parts)
        if path.is_symlink() or not path.is_file():
            raise NativeSpikeError(
                "workspace_symlink_unsafe",
                "The generated Markdown baseline contains a symlink or non-file entry.",
                "Use a separate disposable workspace with regular local files.",
            )
        rows.append(
            {
                "path": relative_path.as_posix(),
                "sha256": _sha256(path.read_bytes()),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(canonical)


def _file_node(
    *,
    node_id: str,
    file: str,
    x: int,
    y: int,
    subpath: str | None = None,
    width: int = 400,
    height: int = 260,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id,
        "type": "file",
        "file": file,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }
    if subpath:
        node["subpath"] = subpath
    return node


def _text_node(*, node_id: str, text: str, x: int, y: int) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "text",
        "text": text,
        "x": x,
        "y": y,
        "width": 360,
        "height": 180,
    }


_EDGE_STYLE = {
    "opens_source": ("read", "1"),
    "contains_topic": ("topic", "4"),
    "contains_subtopic": ("subtopic", "5"),
    "concept_reference": ("concepts", "3"),
    "next_step": ("next", "2"),
    "next_section": ("next section", "6"),
}


def _edge(
    *, source_id: str, target_id: str, kind: str, ordinal: int
) -> dict[str, Any]:
    label, color = _EDGE_STYLE[kind]
    return {
        "id": _stable_id("edge", source_id, target_id, kind, str(ordinal)),
        "fromNode": source_id,
        "fromSide": "right",
        "toNode": target_id,
        "toSide": "left",
        "toEnd": "arrow",
        "label": label,
        "color": color,
        "kgnoteOrganizationKind": kind,
    }


def build_native_canvas(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic Canvas plus companion-guide data without I/O."""

    projection = project_learner_workspace(payload).as_dict()
    source_name = PurePosixPath(str(payload["planned_artifacts"]["immutable_source"])).name
    source_file = f"Source/{source_name}"
    source_id = str(payload["source"]["id"])
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    edge_descriptions: list[dict[str, str]] = []

    start_id = _stable_id("node", source_id, "start")
    nodes.append(
        _file_node(node_id=start_id, file="Start Here.md", x=0, y=0, width=380, height=300)
    )

    shape = str(projection["source_shape"])
    if shape == "hierarchical":
        structure = list(projection["structure"])
        min_level = min(int(item["level"]) for item in structure)
        node_by_section: dict[str, str] = {}
        sibling_index: dict[tuple[int, str | None], int] = {}
        for item in structure:
            level = int(item["level"])
            parent_id = str(item["parent_id"]) if item["parent_id"] else None
            key = (level, parent_id)
            index = sibling_index.get(key, 0)
            sibling_index[key] = index + 1
            node_id = _stable_id("node", source_id, str(item["id"]))
            node_by_section[str(item["id"])] = node_id
            nodes.append(
                _file_node(
                    node_id=node_id,
                    file=source_file,
                    subpath="#" + str(item["title"]),
                    x=(level - min_level + 1) * 520,
                    y=index * 330,
                )
            )
        roots = [item for item in structure if item["parent_id"] is None]
        for ordinal, root in enumerate(roots):
            target = node_by_section[str(root["id"])]
            edges.append(
                _edge(source_id=start_id, target_id=target, kind="opens_source", ordinal=ordinal)
            )
        for ordinal, item in enumerate(structure):
            if item["parent_id"] is None:
                continue
            parent = next(row for row in structure if row["id"] == item["parent_id"])
            kind = (
                "contains_topic"
                if int(parent["level"]) == min_level
                else "contains_subtopic"
            )
            edges.append(
                _edge(
                    source_id=node_by_section[str(parent["id"])],
                    target_id=node_by_section[str(item["id"])],
                    kind=kind,
                    ordinal=ordinal,
                )
            )
    elif shape == "heading_free":
        source_node = _stable_id("node", source_id, "source")
        concept_node = _stable_id("node", source_id, "concept-index")
        nodes.extend(
            [
                _file_node(node_id=source_node, file=source_file, x=520, y=0),
                _file_node(node_id=concept_node, file="Concepts/Index.md", x=1040, y=0),
            ]
        )
        edges.extend(
            [
                _edge(source_id=start_id, target_id=source_node, kind="opens_source", ordinal=0),
                _edge(
                    source_id=source_node,
                    target_id=concept_node,
                    kind="concept_reference",
                    ordinal=1,
                ),
            ]
        )
    else:
        source_node = _stable_id("node", source_id, "source")
        nodes.append(
            _file_node(
                node_id=source_node,
                file=source_file,
                subpath="#" + str(projection["source"]["title"]),
                x=520,
                y=0,
            )
        )
        edges.append(
            _edge(source_id=start_id, target_id=source_node, kind="opens_source", ordinal=0)
        )
        previous = source_node
        for index, step in enumerate(projection["learning_path"], 1):
            step_id = _stable_id("node", source_id, "step", str(index), str(step))
            nodes.append(
                _text_node(
                    node_id=step_id,
                    text=f"**Step {index}**\n\n{step}\n\n[[{source_file[:-3]}|Open source]]",
                    x=520 + index * 430,
                    y=0,
                )
            )
            edges.append(
                _edge(
                    source_id=previous,
                    target_id=step_id,
                    kind="next_step",
                    ordinal=index,
                )
            )
            previous = step_id
        later_sections = [
            item for item in projection["structure"] if int(item["level"]) > 1
        ]
        for offset, item in enumerate(later_sections, len(projection["learning_path"]) + 1):
            section_id = _stable_id("node", source_id, str(item["id"]))
            nodes.append(
                _file_node(
                    node_id=section_id,
                    file=source_file,
                    subpath="#" + str(item["title"]),
                    x=520 + offset * 430,
                    y=0,
                )
            )
            edges.append(
                _edge(
                    source_id=previous,
                    target_id=section_id,
                    kind="next_section",
                    ordinal=offset,
                )
            )
            previous = section_id

    for kind in sorted({edge["kgnoteOrganizationKind"] for edge in edges}):
        label, _ = _EDGE_STYLE[kind]
        description = {
            "opens_source": "Opens the original material from the learner entry.",
            "contains_topic": "Navigates from the source topic to a source-supported child topic.",
            "contains_subtopic": "Navigates from a topic to a deeper source-supported subtopic or anchor.",
            "concept_reference": "Moves from the heading-free source to a flat concept reference; it does not invent hierarchy.",
            "next_step": "Shows source-supported reading order only; it is not a canonical causal relation.",
            "next_section": "Continues to the next source heading after the ordered steps.",
        }[kind]
        edge_descriptions.append({"kind": kind, "label": label, "description": description})

    nodes.sort(key=lambda item: (item["x"], item["y"], item["id"]))
    edges.sort(key=lambda item: item["id"])
    edge_kinds = {
        str(edge["id"]): str(edge["kgnoteOrganizationKind"]) for edge in edges
    }
    canvas_edges = [
        {key: value for key, value in edge.items() if key != "kgnoteOrganizationKind"}
        for edge in edges
    ]
    canvas = {"nodes": nodes, "edges": canvas_edges}
    return {
        "schema_version": NATIVE_MANIFEST_VERSION,
        "source_shape": shape,
        "canvas": canvas,
        "edge_kinds": edge_kinds,
        "edge_descriptions": edge_descriptions,
        "canonical_digest": _canonical_digest(payload),
    }


def _canvas_bytes(model: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(model["canvas"], ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _guide_bytes(model: Mapping[str, Any]) -> bytes:
    lines = [
        "---",
        f'kgnote_schema: "{NATIVE_MANIFEST_VERSION}"',
        "kgnote_generated: true",
        "---",
        "# Canvas guide",
        "",
        "This Canvas is optional structure navigation. Start Here and the ordinary Markdown notes remain the learning baseline.",
        "",
        "Canvas grouping, coordinates, and organization edges are view data. They do not create canonical knowledge relations.",
        "",
        "## Organization edges",
        "",
    ]
    for item in model["edge_descriptions"]:
        lines.append(f"- **{item['label']}** — {item['description']}")
    lines.extend(
        [
            "",
            "[[Learning Structure.canvas|Open the Canvas]] · [[Start Here|Back to Start Here]]",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _entry_bytes(content: bytes) -> bytes:
    """Add one optional Canvas affordance without reordering the Golden sections."""

    marker = "## Optional Canvas\n"
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise NativeSpikeError(
            "native_entry_unreadable",
            "Start Here is not valid UTF-8.",
            "Preserve the workspace and regenerate in another disposable destination.",
        ) from error
    if marker in text:
        return content
    details = "> [!info]- KGnote details"
    block = (
        "## Optional Canvas\n\n"
        "[[Learning Structure.canvas|Open the optional structure Canvas]]\n\n"
        "The Markdown lesson above remains the complete learning baseline. "
        "Canvas is secondary navigation and does not create knowledge relationships.\n\n"
    )
    if details not in text:
        raise NativeSpikeError(
            "native_entry_shape_unsupported",
            "Start Here does not contain the expected learner-first details boundary.",
            "Regenerate the Markdown workspace with the current Personal Alpha generator.",
        )
    return text.replace(details, block + details, 1).encode("utf-8")


def _reading_css_bytes() -> bytes:
    return (
        "/* Vault-local KGnote review presentation. Reading view only. */\n"
        ".markdown-reading-view .metadata-container { display: none; }\n"
        ".markdown-reading-view .markdown-preview-sizer { max-width: 760px; }\n"
        ".markdown-reading-view h1 { margin-bottom: 1.25rem; }\n"
    ).encode("utf-8")


def _appearance_bytes() -> bytes:
    return b'{\n  "cssSnippets": ["kgnote-reading"]\n}\n'


def _load_workspace_manifest(root: Path) -> dict[str, Any]:
    path = root / Path(*WORKSPACE_MANIFEST_PATH.parts)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeSpikeError(
            "workspace_manifest_invalid",
            "The Personal Alpha workspace manifest is unreadable.",
            "Preserve the workspace and regenerate in another disposable destination.",
        ) from error
    if not isinstance(value, dict) or not isinstance(value.get("managed_files"), list):
        raise NativeSpikeError(
            "workspace_manifest_invalid",
            "The Personal Alpha workspace manifest is malformed.",
            "Preserve the workspace and regenerate in another disposable destination.",
        )
    return value


def _workspace_managed_hash(manifest: Mapping[str, Any], relative: str) -> str | None:
    for row in manifest.get("managed_files", []):
        if isinstance(row, Mapping) and row.get("path") == relative:
            value = row.get("sha256")
            return str(value) if isinstance(value, str) else None
    return None


def _updated_workspace_manifest_bytes(
    manifest: Mapping[str, Any], *, entry_sha256: str
) -> bytes:
    updated = json.loads(json.dumps(manifest))
    for row in updated["managed_files"]:
        if row.get("path") == str(ENTRY_PATH):
            row["sha256"] = entry_sha256
            break
    else:
        raise NativeSpikeError(
            "workspace_manifest_invalid",
            "The Personal Alpha manifest does not manage Start Here.",
            "Regenerate the Markdown workspace with the current generator.",
        )
    return (json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _manifest_bytes(
    model: Mapping[str, Any], artifacts: Mapping[str, bytes], markdown_digest: str
) -> bytes:
    manifest = {
        "schema_version": NATIVE_MANIFEST_VERSION,
        "source_shape": model["source_shape"],
        "canonical_digest": model["canonical_digest"],
        "markdown_digest": markdown_digest,
        "canvas_path": str(CANVAS_PATH),
        "guide_path": str(GUIDE_PATH),
        "vault_root": ".",
        "entry_path": str(ENTRY_PATH),
        "reading_view": {
            "appearance_path": str(APPEARANCE_PATH),
            "css_path": str(READING_CSS_PATH),
            "scope": "disposable_vault_local",
        },
        "managed_files": [
            {"path": path, "sha256": _sha256(content)}
            for path, content in sorted(artifacts.items())
        ],
        "node_count": len(model["canvas"]["nodes"]),
        "edge_count": len(model["canvas"]["edges"]),
        "edge_kinds": model["edge_kinds"],
    }
    return (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise NativeSpikeError(
            "native_path_invalid",
            "A native artifact path is unsafe.",
            "Preserve the workspace and report the generator defect.",
        )
    return path


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _remove(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def _reject_symlinks(root: Path) -> None:
    for current, directories, files in os.walk(root):
        base = Path(current)
        for name in directories + files:
            if (base / name).is_symlink():
                raise NativeSpikeError(
                    "workspace_symlink_unsafe",
                    "The workspace contains a symlink, so native augmentation was refused.",
                    "Use a disposable workspace containing regular local files only.",
                )


def _recover(transaction: Path, target: Path) -> bool:
    if not transaction.exists():
        return False
    if transaction.is_symlink() or not transaction.is_dir():
        raise NativeSpikeError(
            "native_transaction_conflict",
            "The reserved native transaction path is unsafe.",
            "Preserve it for inspection and choose another disposable vault.",
        )
    backup = transaction / "backup"
    staged = transaction / "staged"
    if backup.exists():
        if target.exists():
            _remove(target)
        os.replace(backup, target)
    _remove(staged)
    _remove(transaction)
    return True


def augment_native_workspace(
    preview: PersonalAlphaPreview,
    workspace: str | Path,
    *,
    failure_injector: Callable[[str], None] | None = None,
) -> NativeSpikeResult:
    """Transactionally add optional Canvas artifacts to one disposable workspace."""

    target = Path(workspace)
    if target.is_symlink() or not target.is_dir():
        raise NativeSpikeError(
            "workspace_not_directory",
            "The native spike target must be an existing regular Personal Alpha workspace.",
            "Generate a disposable workspace first, then retry.",
        )
    target = target.resolve()
    _reject_symlinks(target)
    source_id = str(preview.payload["source"]["id"])
    transaction = target.parent / f".kgnote-native-transaction-{source_id[-16:]}"
    recovered = _recover(transaction, target)
    model = build_native_canvas(preview.payload)
    workspace_manifest = _load_workspace_manifest(target)
    entry_path = target / Path(*ENTRY_PATH.parts)
    if entry_path.is_symlink() or not entry_path.is_file():
        raise NativeSpikeError(
            "native_entry_missing",
            "Start Here is missing from the Personal Alpha workspace.",
            "Regenerate the Markdown workspace before adding Canvas navigation.",
        )
    entry = _entry_bytes(entry_path.read_bytes())
    artifacts = {
        str(CANVAS_PATH): _canvas_bytes(model),
        str(GUIDE_PATH): _guide_bytes(model),
        str(ENTRY_PATH): entry,
        str(APPEARANCE_PATH): _appearance_bytes(),
        str(READING_CSS_PATH): _reading_css_bytes(),
    }
    workspace_manifest_bytes = _updated_workspace_manifest_bytes(
        workspace_manifest, entry_sha256=_sha256(entry)
    )
    old_manifest: Mapping[str, Any] | None = None
    old_managed: set[str] = set()
    manifest_path = target / Path(*MANIFEST_PATH.parts)
    if manifest_path.exists():
        try:
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise NativeSpikeError(
                "native_manifest_invalid",
                "The existing native manifest is unreadable.",
                "Preserve the workspace and use another disposable destination.",
            ) from error
        if old_manifest.get("schema_version") != NATIVE_MANIFEST_VERSION:
            raise NativeSpikeError(
                "native_manifest_version_unsupported",
                "The existing native manifest uses an unsupported version.",
                "Preserve the workspace; do not migrate it implicitly.",
            )
        for row in old_manifest.get("managed_files", []):
            relative = _safe_relative(str(row.get("path", "")))
            path = target / Path(*relative.parts)
            digest_matches = (
                not path.is_symlink()
                and path.is_file()
                and _sha256(path.read_bytes()) == row.get("sha256")
            )
            if not digest_matches and relative == ENTRY_PATH:
                digest_matches = (
                    path.is_file()
                    and not path.is_symlink()
                    and _sha256(path.read_bytes())
                    == _workspace_managed_hash(workspace_manifest, str(ENTRY_PATH))
                )
            if not digest_matches:
                raise NativeSpikeError(
                    "native_managed_file_conflict",
                    f"A native managed file has local edits or is missing: {relative.as_posix()}.",
                    "Preserve the file and use another disposable destination.",
                )
            old_managed.add(relative.as_posix())
    for relative in artifacts:
        candidate = target / Path(*_safe_relative(relative).parts)
        base_managed_entry = (
            relative == str(ENTRY_PATH)
            and _workspace_managed_hash(workspace_manifest, relative)
            == _sha256(candidate.read_bytes())
        )
        if (
            relative not in old_managed
            and not base_managed_entry
            and (candidate.exists() or candidate.is_symlink())
        ):
            raise NativeSpikeError(
                "native_user_collision",
                f"A native artifact would overwrite a user-owned file: {relative}.",
                "Move or rename that file yourself, then rerun.",
            )
    markdown_after = _markdown_digest(target)
    if entry_path.read_bytes() != entry:
        markdown_after = ""
    manifest_bytes = _manifest_bytes(model, artifacts, markdown_after)
    if old_manifest is not None:
        current_manifest = manifest_path.read_bytes()
        if current_manifest == manifest_bytes and all(
            (target / Path(*PurePosixPath(relative).parts)).read_bytes() == content
            for relative, content in artifacts.items()
        ) and (target / Path(*WORKSPACE_MANIFEST_PATH.parts)).read_bytes() == workspace_manifest_bytes:
            return NativeSpikeResult(
                status="unchanged",
                workspace_path=str(target),
                canvas_path=str(target / str(CANVAS_PATH)),
                guide_path=str(target / str(GUIDE_PATH)),
                source_shape=str(model["source_shape"]),
                canonical_digest=str(model["canonical_digest"]),
                markdown_digest=markdown_after,
                node_count=len(model["canvas"]["nodes"]),
                edge_count=len(model["canvas"]["edges"]),
                recovered_interrupted_transaction=recovered,
            )

    transaction.mkdir(mode=0o700)
    staged = transaction / "staged"
    backup = transaction / "backup"
    committed = False
    try:
        shutil.copytree(target, staged)
        for relative, content in sorted(artifacts.items()):
            _write(staged / Path(*_safe_relative(relative).parts), content)
        _write(staged / Path(*WORKSPACE_MANIFEST_PATH.parts), workspace_manifest_bytes)
        markdown_after = _markdown_digest(staged)
        manifest_bytes = _manifest_bytes(model, artifacts, markdown_after)
        _write(staged / Path(*MANIFEST_PATH.parts), manifest_bytes)
        if failure_injector:
            failure_injector("after_stage")
        os.replace(target, backup)
        if failure_injector:
            failure_injector("after_backup")
        os.replace(staged, target)
        committed = True
        if failure_injector:
            failure_injector("after_commit")
        if _markdown_digest(target) != markdown_after:
            raise NativeSpikeError(
                "markdown_baseline_drift",
                "Native augmentation did not preserve its prepared Markdown baseline.",
                "Stop and preserve the transaction for inspection.",
            )
        _remove(backup)
        _remove(transaction)
    except Exception as error:
        try:
            if backup.exists():
                if target.exists():
                    _remove(target)
                os.replace(backup, target)
            elif committed and target.exists():
                _remove(target)
            _remove(transaction)
        except OSError as rollback_error:
            raise NativeSpikeError(
                "native_rollback_failed",
                "Native augmentation failed and rollback could not restore the workspace.",
                "Stop using this destination and preserve it for recovery.",
            ) from rollback_error
        if isinstance(error, NativeSpikeError):
            raise
        raise NativeSpikeError(
            "native_augmentation_failed_rolled_back",
            "Native augmentation failed and the Markdown workspace was restored.",
            "Correct the filesystem condition and rerun.",
        ) from error

    return NativeSpikeResult(
        status="applied",
        workspace_path=str(target),
        canvas_path=str(target / str(CANVAS_PATH)),
        guide_path=str(target / str(GUIDE_PATH)),
        source_shape=str(model["source_shape"]),
        canonical_digest=str(model["canonical_digest"]),
        markdown_digest=markdown_after,
        node_count=len(model["canvas"]["nodes"]),
        edge_count=len(model["canvas"]["edges"]),
        recovered_interrupted_transaction=recovered,
    )
