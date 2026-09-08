# Read-only graph view application v1

`load_graph_view(explicit_root, query=None)` is the filesystem-facing application boundary for a
future Web adapter. It reads one explicitly supplied canonical store, reuses the canonical reader,
projects the complete validated snapshot, plans a snapshot-bound selection, then materializes only
the selected nodes, links, Evidence, and Sources.

Materialization preserves canonical IDs and link direction. A selected LearningEvent keeps only
`concept_ids` that are also present in the selected node set, so the partial view remains a valid,
self-contained graph read model instead of emitting ghost references to hidden nodes.

A missing query means a full-graph selection with empty filters. A supplied query must contain the
exact projected snapshot digest; stale queries fail closed. The returned `view` remains a valid
`kgnote.graph-read-model.v1`, while `plan` remains a valid `kgnote.graph-view-plan.v1`.

Rejected results expose only a component (`store`, `projector`, or `planner`), stable code, and safe
contract-relative path. They do not include the canonical root, absolute paths, Markdown bodies, or
record content.

This boundary may read the explicit store. It does not write files, inspect environment settings,
call a network/model API, launch UI, use a clock, cache, watch, or mutate canonical Markdown. HTTP
serialization, authentication, layout, search, browser state, and deployment are non-goals.
