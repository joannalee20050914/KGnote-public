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
