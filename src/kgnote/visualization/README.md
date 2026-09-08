# Visualization projection boundary

`project_graph_read_model(records)` is a pure in-memory adapter from a complete, validated
canonical-record snapshot to `kgnote.graph-read-model.v1`.

It normalizes record and set-like array order, derives safe renderer-owned labels and facets,
computes the snapshot digest, validates the completed model, and returns an immutable result
whose `model` property is a fresh JSON copy. Rejected inputs return stable problem metadata
without echoing record bodies.

The projector does not locate or read a vault. A future filesystem/application adapter may call
the canonical store reader first and then pass `StoreSnapshot.records` here. HTTP serialization,
layout, filtering, neighborhood selection, UI state, and mutation remain outside this module.

`plan_graph_view(model, query)` is the next pure boundary. It validates an explicit snapshot-bound
query, applies type/relation/space filters, traverses retained links direction-neutrally for up to
three hops, and returns only sorted selected IDs plus stable exclusion reasons. It never changes
link direction or treats Evidence/Source support records as canvas nodes. The versioned query and
plan decisions are documented under `schemas/graph-view/v1/`.

`load_graph_view(explicit_root, query=None)` is the sole filesystem-facing application boundary. It
composes the canonical reader, projector, and planner, then returns a plan-materialized read model
containing only selected provenance support. Missing query means full graph; supplied queries must
match the current projected snapshot digest. Its versioned envelope and safe error mapping are
documented under `schemas/graph-view-application/v1/`. It performs no writes and is not an HTTP or
UI adapter.
