"""Project real cross-unit encounter history into optional Reading Assist."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping


def prior_encounters(reading_assist: Mapping[str, Any], events: Iterable[Mapping[str, Any]], *, current_unit_id: str) -> list[dict[str, Any]]:
    gloss_concepts = {gloss.get("id"): gloss.get("concept_ref") for gloss in reading_assist.get("glosses", []) if gloss.get("concept_ref")}
    result = []
    seen = set()
    for event in events:
        if event.get("learning_unit_id") == current_unit_id or event.get("concept_id") not in gloss_concepts.values():
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or event_id in seen:
            continue
        seen.add(event_id)
        for gloss_id, concept_id in gloss_concepts.items():
            if concept_id == event.get("concept_id"):
                result.append({"gloss_id": gloss_id, "concept_id": concept_id, "learning_unit_id": event.get("learning_unit_id"), "kind": event.get("kind"), "occurred_at": event.get("occurred_at"), "source_refs": json.loads(json.dumps(event.get("source_refs", []), ensure_ascii=False)), "event_id": event_id})
    return sorted(result, key=lambda item: (str(item["occurred_at"]), item["event_id"]), reverse=True)


__all__ = ["prior_encounters"]
