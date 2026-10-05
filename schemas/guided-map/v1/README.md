# Guided Map v1

This directory defines two deliberately separate versioned boundaries:

- `kgnote.guided-map-spec.v1` is a human-reviewed view artifact. It references a frozen
  Graph Read Model snapshot and stores only teaching choices: one focus question, ordered
  view-only groups, selected Concept/Edge/Evidence IDs, and natural-language linking phrases.
- `kgnote.guided-map-read-model.v1` is the resolved, JSON-safe renderer input produced by
  joining that spec to `kgnote.graph-read-model.v1`.

## Ownership decision

Teaching Propositions live in the Guided Map Spec in v1. They do **not** extend canonical
Edge records and do **not** live in renderer code. The projector copies Concept labels, Edge
direction/relation, and Evidence from the Graph Read Model. A stale snapshot or dangling
reference is rejected instead of silently rewriting the lesson.

Groups are navigation metadata, never Concept nodes or graph edges. Each selected Concept has
exactly one primary group in v1; Teaching Propositions may cross groups. Only canonical graph
edges are eligible. Learning Overlay edges and unresolved soft associations are excluded.

## Determinism and safety

IDs and set-like lists are lexicographically sorted; groups are ordered by `order`, then `id`.
The projector is pure and has no filesystem, network, provider, or clock access. Output retains
Evidence provenance but excludes raw source bodies and source paths.
