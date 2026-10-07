"""Load a bounded data-driven catalog and its reviewed local fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from kgnote.review.practice import build_practice_set


SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}")


@dataclass(frozen=True, repr=False)
class CatalogResult:
    status: Literal["ready", "rejected"]
    _payload_json: str = field(default="{}", repr=False)
    problem_code: str | None = None
    @property
    def payload(self) -> dict[str, Any]: return json.loads(self._payload_json)


def _result(status: str, payload: dict[str, Any] | None = None, problem: str | None = None) -> CatalogResult:
    return CatalogResult(status, json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), problem)


def _read_json(root: Path, name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"): return None
    path = root / name
    if path.is_symlink() or not path.is_file(): return None
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError): return None
    return value if isinstance(value, dict) else None


def _read_text(root: Path, name: Any) -> str | None:
    if not isinstance(name, str) or Path(name).name != name: return None
    path = root / name
    if path.is_symlink() or not path.is_file(): return None
    try: return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError): return None


def _fallback_structure(entry: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Keep the immutable source readable when its optional structure projection fails."""
    return {
        "schema_version": "kgnote.learning-structure.v1",
        "structure_id": f"fallback_{entry['slug']}",
        "learning_unit_id": entry["unit_id"],
        "revision": 0,
        "title": entry["title"],
        "provenance": {"basis": "source_fallback", "author": "kgnote.catalog.v1"},
        "nodes": [{
            "id": f"{entry['slug']}_source_root",
            "title": entry["title"],
            "parent_id": None,
            "order": 1,
            "kind": "source",
            "organizing_relation": "source_scope",
            "source_anchors": [{"source_id": model["source"]["id"], "locator": model["learning_unit"]["source_locator"]}],
            "concept_refs": [],
            "claim_refs": [],
        }],
    }


def _empty_assist(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "kgnote.reading-assist.v1",
        "learning_unit_id": entry["unit_id"],
        "revision": 0,
        "glosses": [],
        "prior_knowledge": [],
    }


def _valid_structure(value: Any, unit_id: str) -> bool:
    if not isinstance(value, dict) or value.get("schema_version") != "kgnote.learning-structure.v1" or value.get("learning_unit_id") != unit_id or not isinstance(value.get("nodes"), list):
        return False
    nodes = value["nodes"]
    ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    return len(ids) == len(nodes) and len([node for node in nodes if node.get("parent_id") is None]) == 1 and all(node.get("parent_id") is None or node.get("parent_id") in ids for node in nodes)


def _valid_assist_base(value: Any, unit_id: str) -> bool:
    return isinstance(value, dict) and value.get("schema_version") == "kgnote.reading-assist.v1" and value.get("learning_unit_id") == unit_id and isinstance(value.get("glosses"), list)


def load_learning_unit_catalog(catalog_path: str | Path) -> CatalogResult:
    path = Path(catalog_path)
    if path.is_symlink() or not path.is_file(): return _result("rejected", problem="catalog_unavailable")
    try: catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError): return _result("rejected", problem="invalid_catalog")
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "kgnote.learning-unit-catalog.v1" or not isinstance(catalog.get("units"), list): return _result("rejected", problem="invalid_catalog")
    root = path.parent
    bundles: dict[str, Any] = {}
    for entry in catalog["units"]:
        required = {"slug", "unit_id", "title", "description", "map", "source", "claim_reviews", "structure", "reading_assist", "practice", "soak"}
        if not isinstance(entry, dict) or set(entry) != required or not SLUG.fullmatch(str(entry["slug"])) or entry["slug"] in bundles: return _result("rejected", problem="invalid_catalog_entry")
        model = _read_json(root, entry["map"]); overlay = _read_json(root, entry["claim_reviews"]); structure = _read_json(root, entry["structure"]); assist = _read_json(root, entry["reading_assist"]); supplement = _read_json(root, entry["practice"]); soak = _read_json(root, entry["soak"]); source = _read_text(root, entry["source"])
        if None in (model, overlay, supplement, soak, source): return _result("rejected", problem="unit_fixture_unavailable")
        if model["learning_unit"]["id"] != entry["unit_id"]: return _result("rejected", problem="unit_identity_drift")
        if hashlib.sha256(source.encode()).hexdigest() != model["source"]["content_sha256"]: return _result("rejected", problem="unit_source_hash_drift")
        degradations = []
        if not _valid_structure(structure, entry["unit_id"]):
            structure = _fallback_structure(entry, model)
            degradations.append({"component": "learning_structure", "code": "source_fallback"})
        if not _valid_assist_base(assist, entry["unit_id"]):
            assist = _empty_assist(entry)
            degradations.append({"component": "reading_assist", "code": "unavailable"})
        elif not isinstance(assist.get("prior_knowledge"), list):
            assist = {**assist, "prior_knowledge": []}
            degradations.append({"component": "prior_knowledge", "code": "unavailable"})
        practice = build_practice_set(model, overlay, supplement)
        if practice.status != "ready": return _result("rejected", problem=practice.problem_code or "practice_unavailable")
        if soak.get("schema_version") != "kgnote.soak-set.v1" or soak.get("learning_unit_id") != entry["unit_id"] or not isinstance(soak.get("items"), list) or not soak["items"]:
            return _result("rejected", problem="invalid_soak_set")
        concept_ids = {item["id"] for item in model.get("concepts", [])}
        practice_by_id = {item["item_id"]: item for item in practice.payload["items"]}
        propositions = {item["edge_id"]: item for item in model.get("propositions", [])}
        seen_soak = set()
        for item in soak["items"]:
            required_soak = {"item_id", "concept_id", "label", "familiar_context", "answer", "support_progression", "source_refs", "related_practice_item_id"}
            if not isinstance(item, dict) or set(item) != required_soak or item["item_id"] in seen_soak or item["concept_id"] not in concept_ids or not all(isinstance(item[key], str) and item[key].strip() for key in ("item_id", "label", "familiar_context", "answer", "related_practice_item_id")) or not isinstance(item["source_refs"], list) or not item["source_refs"]:
                return _result("rejected", problem="invalid_soak_item")
            progression = item["support_progression"]
            allowed_stages = {"high_similarity", "cued", "changed_context", "explanation", "application"}
            stage_values = [step.get("stage") for step in progression if isinstance(step, dict)] if isinstance(progression, list) else []
            if not 2 <= len(stage_values) <= 8 or len(set(stage_values)) != len(stage_values) or not set(stage_values) <= allowed_stages or any(set(step) != {"stage", "label", "content", "response_expected"} or not isinstance(step["label"], str) or not step["label"].strip() or not isinstance(step["content"], str) or not step["content"].strip() or not isinstance(step["response_expected"], bool) for step in progression):
                return _result("rejected", problem="invalid_support_progression")
            linked = practice_by_id.get(item["related_practice_item_id"])
            proposition = propositions.get(linked["claim_ref"]["claim_id"]) if linked else None
            if proposition is None or item["concept_id"] not in {proposition["subject_concept_id"], proposition["object_concept_id"]}:
                return _result("rejected", problem="invalid_soak_practice_link")
            seen_soak.add(item["item_id"])
        bundles[entry["slug"]] = {"catalog": {key: entry[key] for key in ("slug", "unit_id", "title", "description")}, "model": model, "source_text": source, "claim_reviews": overlay, "structure": structure, "reading_assist": assist, "practice_supplement": supplement, "practice": practice.payload, "soak": soak, "degradations": degradations}
    summaries = []
    for slug, bundle in bundles.items():
        summaries.append({**bundle["catalog"], "topic_count": sum(1 for item in bundle["structure"]["nodes"] if item["parent_id"] == bundle["structure"]["nodes"][0]["id"]), "reviewed_claims_count": sum(1 for item in bundle["claim_reviews"]["reviews"] if item["teaching_answer_status"] == "ready"), "practice_items_count": len(bundle["practice"]["items"]), "soak_items_count": len(bundle["soak"]["items"]), "unavailable_items_count": len(bundle["practice"]["blocked_claims"])})
    return _result("ready", {"schema_version": "kgnote.learning-unit-registry.v1", "summaries": summaries, "bundles": bundles})


__all__ = ["CatalogResult", "load_learning_unit_catalog"]
