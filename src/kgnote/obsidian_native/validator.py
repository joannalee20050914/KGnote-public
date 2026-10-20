"""Semantic read-back for the bounded JSON Canvas subset used by KGnote."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from kgnote.personal_alpha import PersonalAlphaPreview, read_back_learning_workspace

from .spike import (
    APPEARANCE_PATH,
    CANVAS_PATH,
    ENTRY_PATH,
    GUIDE_PATH,
    MANIFEST_PATH,
    NATIVE_MANIFEST_VERSION,
    READING_CSS_PATH,
    NativeSpikeError,
    _EDGE_STYLE,
    _canonical_digest,
    _markdown_digest,
    _sha256,
)


_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_BLOCK_ID = re.compile(r"^[A-Za-z0-9-]+$")
_WIKILINK = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FILE_NODE_KEYS = {"id", "type", "file", "subpath", "x", "y", "width", "height", "color"}
_TEXT_NODE_KEYS = {"id", "type", "text", "x", "y", "width", "height", "color"}
_EDGE_KEYS = {
    "id",
    "fromNode",
    "fromSide",
    "fromEnd",
    "toNode",
    "toSide",
    "toEnd",
    "color",
    "label",
}
_SIDES = {"top", "right", "bottom", "left"}
_ENDS = {"none", "arrow"}
_ALLOWED_KINDS = set(_EDGE_STYLE)


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise NativeSpikeError(
            "canvas_path_invalid",
            f"Canvas references an unsafe path: {value}.",
            "Regenerate the disposable spike; do not repair generated JSON by hand.",
        )
    return path


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_color(value: Any) -> bool:
    return value is None or value in {"1", "2", "3", "4", "5", "6"} or (
        isinstance(value, str) and bool(_HEX_COLOR.match(value))
    )


def validate_markdown_subpath(path: Path, subpath: str) -> None:
    """Validate one exact Obsidian heading or block subpath against Markdown bytes."""

    if not subpath.startswith("#") or subpath == "#":
        raise NativeSpikeError(
            "canvas_subpath_invalid",
            f"Canvas subpath is malformed: {subpath}.",
            "Regenerate the Canvas from current source headings or block IDs.",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise NativeSpikeError(
            "canvas_file_unreadable",
            f"Canvas Markdown target cannot be read: {path.name}.",
            "Preserve the workspace and regenerate in another disposable destination.",
        ) from error
    anchor = subpath[1:]
    if anchor.startswith("^"):
        block_id = anchor[1:]
        if not _BLOCK_ID.fullmatch(block_id):
            raise NativeSpikeError(
                "canvas_block_id_invalid",
                f"Canvas block ID is invalid: {block_id}.",
                "Use only Latin letters, numbers, and dashes in generated block IDs.",
            )
        if not re.search(rf"(?:^|\s)\^{re.escape(block_id)}\s*$", text, re.MULTILINE):
            raise NativeSpikeError(
                "canvas_block_anchor_stale",
                f"Canvas block anchor no longer resolves: {subpath}.",
                "Regenerate the Canvas against the current Markdown snapshot.",
            )
        return
    headings = {
        re.sub(r"\s+#+$", "", match.group(1)).strip()
        for line in text.splitlines()
        if (match := _HEADING.match(line))
    }
    if anchor not in headings:
        raise NativeSpikeError(
            "canvas_heading_anchor_stale",
            f"Canvas heading anchor no longer resolves: {subpath}.",
            "Regenerate the Canvas against the current Markdown snapshot.",
        )


def _validate_text_links(workspace: Path, text: str) -> int:
    count = 0
    for match in _WIKILINK.finditer(text):
        relative = _safe_relative(match.group(1))
        candidates = [
            workspace / Path(*relative.parts),
            workspace / Path(*(relative.parts[:-1] + (relative.name + ".md",))),
        ]
        if not any(path.is_file() and not path.is_symlink() for path in candidates):
            raise NativeSpikeError(
                "canvas_text_link_missing",
                f"A Canvas text-node wikilink cannot be reopened: {match.group(1)}.",
                "Regenerate the Canvas from the current Markdown workspace.",
            )
        count += 1
    return count


def _load_json(path: Path, code: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeSpikeError(
            code,
            f"Native JSON is malformed or unreadable: {path.name}.",
            "Preserve the workspace and regenerate in another disposable destination.",
        ) from error
    if not isinstance(value, Mapping):
        raise NativeSpikeError(
            code,
            f"Native JSON root must be an object: {path.name}.",
            "Regenerate the native artifacts.",
        )
    return value


def validate_native_workspace(
    preview: PersonalAlphaPreview, workspace: str | Path
) -> dict[str, Any]:
    """Read back Canvas, files, anchors, edge semantics, and fallback invariants."""

    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise NativeSpikeError(
            "workspace_not_directory",
            "The native workspace is not a regular directory.",
            "Choose an intact disposable workspace.",
        )
    root = root.resolve()
    for current, directories, files in os.walk(root):
        base = Path(current)
        for name in directories + files:
            if (base / name).is_symlink():
                raise NativeSpikeError(
                    "workspace_symlink_unsafe",
                    "The native workspace contains a symlink.",
                    "Use a disposable workspace containing regular local files only.",
                )

    manifest_path = root / Path(*MANIFEST_PATH.parts)
    manifest = _load_json(manifest_path, "native_manifest_invalid")
    if manifest.get("schema_version") != NATIVE_MANIFEST_VERSION:
        raise NativeSpikeError(
            "native_manifest_version_unsupported",
            "The native manifest version is unsupported.",
            "Preserve it and regenerate without implicit migration.",
        )
    if manifest.get("vault_root") != ".":
        raise NativeSpikeError(
            "native_vault_root_invalid",
            "Native artifacts are not bound to the generated workspace as the Obsidian vault root.",
            "Regenerate and open the exact printed Workspace directory as the disposable vault.",
        )
    for row in manifest.get("managed_files", []):
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise NativeSpikeError(
                "native_manifest_invalid",
                "The native managed-file inventory is malformed.",
                "Preserve the workspace and regenerate.",
            )
        relative = _safe_relative(str(row["path"]))
        path = root / Path(*relative.parts)
        if path.is_symlink() or not path.is_file() or _sha256(path.read_bytes()) != row.get("sha256"):
            raise NativeSpikeError(
                "native_managed_file_conflict",
                f"A native managed file changed: {relative.as_posix()}.",
                "Preserve local work and use another disposable destination.",
            )

    canvas_path = root / Path(*CANVAS_PATH.parts)
    canvas = _load_json(canvas_path, "canvas_json_malformed")
    if set(canvas) != {"nodes", "edges"}:
        raise NativeSpikeError(
            "canvas_subset_unsupported",
            "Canvas contains unsupported top-level fields.",
            "Regenerate using the bounded JSON Canvas subset.",
        )
    nodes = canvas.get("nodes")
    edges = canvas.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise NativeSpikeError(
            "canvas_subset_unsupported",
            "Canvas nodes and edges must be arrays.",
            "Regenerate the Canvas.",
        )

    node_ids: set[str] = set()
    checked_files = 0
    checked_anchors = 0
    checked_text_links = 0
    for node in nodes:
        if not isinstance(node, Mapping) or node.get("type") not in {"file", "text"}:
            raise NativeSpikeError(
                "canvas_node_unsupported",
                "Canvas contains an unsupported node.",
                "Regenerate using file and text nodes only.",
            )
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id or node_id in node_ids:
            raise NativeSpikeError(
                "canvas_duplicate_node_id",
                "Canvas node IDs are missing or duplicated.",
                "Regenerate deterministic node identities.",
            )
        node_ids.add(node_id)
        allowed = _FILE_NODE_KEYS if node["type"] == "file" else _TEXT_NODE_KEYS
        if not set(node).issubset(allowed):
            raise NativeSpikeError(
                "canvas_node_unsupported",
                f"Canvas node {node_id} contains unsupported fields.",
                "Regenerate using the bounded JSON Canvas subset.",
            )
        for key in ("x", "y", "width", "height"):
            if not _integer(node.get(key)) or (key in {"width", "height"} and node[key] <= 0):
                raise NativeSpikeError(
                    "canvas_geometry_invalid",
                    f"Canvas node {node_id} has invalid geometry.",
                    "Regenerate deterministic integer coordinates.",
                )
        if not _validate_color(node.get("color")):
            raise NativeSpikeError(
                "canvas_color_invalid",
                f"Canvas node {node_id} has an unsupported color.",
                "Use a JSON Canvas preset or six-digit hex color.",
            )
        if node["type"] == "file":
            if not isinstance(node.get("file"), str):
                raise NativeSpikeError(
                    "canvas_path_invalid",
                    f"Canvas file node {node_id} has no path.",
                    "Regenerate the Canvas.",
                )
            relative = _safe_relative(str(node["file"]))
            path = root / Path(*relative.parts)
            if path.is_symlink() or not path.is_file():
                raise NativeSpikeError(
                    "canvas_file_missing",
                    f"Canvas file node does not resolve: {relative.as_posix()}.",
                    "Regenerate against the current workspace.",
                )
            checked_files += 1
            if "subpath" in node:
                if not isinstance(node["subpath"], str):
                    raise NativeSpikeError(
                        "canvas_subpath_invalid",
                        f"Canvas node {node_id} has a non-text subpath.",
                        "Regenerate the Canvas.",
                    )
                validate_markdown_subpath(path, str(node["subpath"]))
                checked_anchors += 1
        else:
            if not isinstance(node.get("text"), str):
                raise NativeSpikeError(
                    "canvas_node_unsupported",
                    f"Canvas text node {node_id} has no text.",
                    "Regenerate the Canvas.",
                )
            checked_text_links += _validate_text_links(root, str(node["text"]))

    edge_ids: set[str] = set()
    edge_kinds = manifest.get("edge_kinds")
    if not isinstance(edge_kinds, Mapping):
        raise NativeSpikeError(
            "native_manifest_invalid",
            "The native manifest has no edge-kind map.",
            "Regenerate the native artifacts.",
        )
    for edge in edges:
        if not isinstance(edge, Mapping) or not set(edge).issubset(_EDGE_KEYS):
            raise NativeSpikeError(
                "canvas_edge_unsupported",
                "Canvas contains an unsupported edge.",
                "Regenerate using the bounded JSON Canvas subset.",
            )
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id or edge_id in edge_ids or edge_id in node_ids:
            raise NativeSpikeError(
                "canvas_duplicate_edge_id",
                "Canvas edge IDs are missing, duplicated, or collide with node IDs.",
                "Regenerate deterministic edge identities.",
            )
        edge_ids.add(edge_id)
        if edge.get("fromNode") not in node_ids or edge.get("toNode") not in node_ids:
            raise NativeSpikeError(
                "canvas_edge_dangling",
                f"Canvas edge {edge_id} has a dangling endpoint.",
                "Regenerate against the current node set.",
            )
        if edge.get("fromSide") not in _SIDES or edge.get("toSide") not in _SIDES:
            raise NativeSpikeError(
                "canvas_edge_unsupported",
                f"Canvas edge {edge_id} has an unsupported side.",
                "Regenerate the Canvas.",
            )
        if edge.get("fromEnd", "none") not in _ENDS or edge.get("toEnd", "none") not in _ENDS:
            raise NativeSpikeError(
                "canvas_edge_unsupported",
                f"Canvas edge {edge_id} has an unsupported endpoint style.",
                "Regenerate the Canvas.",
            )
        if not isinstance(edge.get("label"), str) or not edge["label"].strip():
            raise NativeSpikeError(
                "canvas_edge_label_missing",
                f"Canvas edge {edge_id} has no readable label.",
                "Regenerate the Canvas with short organization labels.",
            )
        if not _validate_color(edge.get("color")):
            raise NativeSpikeError(
                "canvas_color_invalid",
                f"Canvas edge {edge_id} has an unsupported color.",
                "Use a JSON Canvas preset or six-digit hex color.",
            )
        kind = edge_kinds.get(edge_id)
        if kind not in _ALLOWED_KINDS or _EDGE_STYLE[kind][0] != edge["label"]:
            raise NativeSpikeError(
                "canvas_edge_kind_drift",
                f"Canvas edge {edge_id} disagrees with its organization kind.",
                "Regenerate Canvas and companion metadata together.",
            )
    if set(edge_kinds) != edge_ids:
        raise NativeSpikeError(
            "canvas_edge_kind_drift",
            "Canvas edge-kind metadata does not match the edge set.",
            "Regenerate Canvas and companion metadata together.",
        )

    shape = manifest.get("source_shape")
    kinds = set(edge_kinds.values())
    if shape == "hierarchical":
        if not {"contains_topic", "contains_subtopic"}.issubset(kinds):
            raise NativeSpikeError(
                "canvas_hierarchy_missing",
                "Hierarchical source lacks the required topic/subtopic navigation.",
                "Regenerate all source-supported heading levels.",
            )
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            if edge_kinds[edge["id"]] in {"contains_topic", "contains_subtopic"}:
                adjacency.setdefault(str(edge["fromNode"]), []).append(str(edge["toNode"]))
        def depth(node_id: str, seen: set[str]) -> int:
            if node_id in seen:
                raise NativeSpikeError(
                    "canvas_hierarchy_cycle",
                    "Canvas hierarchy contains a cycle.",
                    "Regenerate the source-heading tree.",
                )
            children = adjacency.get(node_id, [])
            return 1 if not children else 1 + max(depth(child, seen | {node_id}) for child in children)
        if max((depth(node, set()) for node in node_ids), default=0) < 3:
            raise NativeSpikeError(
                "canvas_hierarchy_missing",
                "Hierarchical source does not expose a real three-level path.",
                "Regenerate all source-supported heading levels.",
            )
    elif shape == "heading_free":
        if kinds & {"contains_topic", "contains_subtopic", "next_step", "next_section"}:
            raise NativeSpikeError(
                "canvas_fake_glossary_hierarchy",
                "Heading-free source was projected as a hierarchy or sequence.",
                "Keep the glossary Canvas flat.",
            )
        if any(node.get("subpath") for node in nodes):
            raise NativeSpikeError(
                "canvas_fake_glossary_hierarchy",
                "Heading-free source contains an invented heading anchor.",
                "Keep the glossary Canvas flat.",
            )
    elif shape == "procedural":
        if kinds & {"contains_topic", "contains_subtopic"}:
            raise NativeSpikeError(
                "canvas_procedural_hierarchy_invalid",
                "Procedural steps were promoted to topic hierarchy.",
                "Represent source order as navigation only.",
            )
        forbidden = {"cause", "causes", "therefore", "prerequisite"}
        if any(str(edge.get("label", "")).casefold() in forbidden for edge in edges):
            raise NativeSpikeError(
                "canvas_procedural_causality_invalid",
                "Procedural order was promoted to unsupported causality.",
                "Use an order-only organization edge.",
            )
    else:
        raise NativeSpikeError(
            "native_manifest_invalid",
            "The native manifest has an unknown source shape.",
            "Regenerate the native artifacts.",
        )

    expected_canonical = _canonical_digest(preview.payload)
    if manifest.get("canonical_digest") != expected_canonical:
        raise NativeSpikeError(
            "native_canonical_identity_drift",
            "Canvas on/off no longer preserves canonical identity.",
            "Regenerate against the exact preview snapshot.",
        )
    current_markdown = _markdown_digest(root)
    if manifest.get("markdown_digest") != current_markdown:
        raise NativeSpikeError(
            "native_markdown_fallback_drift",
            "Native augmentation no longer preserves the Markdown baseline.",
            "Preserve the workspace and regenerate in a separate destination.",
        )
    entry_text = (root / Path(*ENTRY_PATH.parts)).read_text(encoding="utf-8")
    canvas_heading = "## Optional Canvas"
    if canvas_heading not in entry_text or "[[Learning Structure.canvas|" not in entry_text:
        raise NativeSpikeError(
            "native_canvas_entry_missing",
            "Start Here does not expose the optional Canvas.",
            "Regenerate the disposable native workspace.",
        )
    golden_sections = (
        "## Learning path",
        "## Key concepts",
        "## Key relationships",
        "## Continue",
        "## My notes",
    )
    offsets = [entry_text.index(value) for value in golden_sections]
    if offsets != sorted(offsets) or entry_text.index(canvas_heading) <= offsets[-1]:
        raise NativeSpikeError(
            "native_canvas_entry_order_invalid",
            "The optional Canvas entry displaced the learner-first Start Here sections.",
            "Regenerate without changing the Golden section order.",
        )
    appearance_path = root / Path(*APPEARANCE_PATH.parts)
    css_path = root / Path(*READING_CSS_PATH.parts)
    try:
        appearance = json.loads(appearance_path.read_text(encoding="utf-8"))
        css = css_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeSpikeError(
            "native_reading_view_config_invalid",
            "The disposable vault Reading-view configuration is unreadable.",
            "Regenerate the disposable native workspace.",
        ) from error
    if "kgnote-reading" not in appearance.get("cssSnippets", []) or (
        ".markdown-reading-view .metadata-container" not in css
    ):
        raise NativeSpikeError(
            "native_reading_view_config_invalid",
            "The disposable vault does not enable the KGnote Reading-view snippet.",
            "Regenerate the disposable native workspace.",
        )
    fallback = read_back_learning_workspace(root)
    guide = root / Path(*GUIDE_PATH.parts)
    if not guide.is_file():
        raise NativeSpikeError(
            "native_guide_missing",
            "The companion Markdown edge guide is missing.",
            "Regenerate the native artifacts.",
        )
    return {
        "status": "loaded",
        "workspace_path": str(root),
        "source_shape": shape,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "edge_kinds": sorted(kinds),
        "checked_files": checked_files,
        "checked_anchors": checked_anchors,
        "checked_text_links": checked_text_links,
        "canonical_digest": expected_canonical,
        "markdown_digest": current_markdown,
        "fallback_entry_note": fallback["entry_note"],
        "vault_root": str(root),
        "canvas_discoverable": True,
        "reading_view_configured": True,
    }


__all__ = ["validate_markdown_subpath", "validate_native_workspace"]
