# Graph read model v1

`kgnote.graph-read-model.v1` is the JSON-safe, read-only boundary between a validated
canonical snapshot and a future Web Graph Viewer. It is a projection contract, not a storage
format and not an API transport.

## Shape and identity

- `nodes` contains only Concept Graph nodes (`concept`) and Learning Overlay nodes
  (`learning_event`). Stable `id` is identity; renderer-owned `label` is display text.
- `links` projects canonical Edge records. `edge_class` keeps canonical knowledge,
  learning observations, and unresolved soft associations distinct.
- `evidence` and `sources` are support records for inspection and provenance. They are not
  canvas nodes. Evidence propositions are included; immutable raw Markdown bodies are not.
- `snapshot_sha256` identifies the deterministic canonical input snapshot. There is no
  render-time clock field.
- `filter_facets` advertises present values only. It does not execute filtering.
- A complete projector result keeps at least one `concept_id` on each LearningEvent. A
  plan-materialized view may have an empty `concept_ids` list when node filters intentionally
  exclude every related Concept; it means no related Concept is present in this view, not that
  canonical provenance was removed.

## Privacy and safety boundary

The model excludes absolute paths, source URI/path fields, raw source bodies, provider
responses, secrets, Markdown/HTML rendering, and filesystem handles. Labels use the ADR-0002
rules: nonblank, at most 64 characters, and no wiki-link control characters. Producers must
fall back to `Record <id-fragment>` and append an ID fragment when labels collide.

## Determinism and ownership

All record arrays and nested ID/string lists are sorted lexicographically and contain no
duplicates. `snapshot_sha256` is SHA-256 over canonical JSON (UTF-8, sorted object keys,
compact separators) of a normalized copy of the validated in-memory canonical record list,
with records sorted by `(type, id)` and set-like arrays sorted. A producer must deep-copy or rebuild its output; callers must not receive mutable
references into the canonical snapshot.

This version intentionally does not define a filesystem adapter, HTTP endpoint, browser UI,
layout coordinates, search, filter execution, mutation, or provider access.
