# Review artifact schemas

These JSON Schemas document `kgnote.review-protocol.v1`. The control engine performs an equivalent standard-library validation so preflight does not depend on a network fetch or optional package. Schema files themselves remain inside the candidate fingerprint.

- `review-request.schema.json`: Codex-owned request, including an `IMPLEMENTING` placeholder and a fully bound `READY_FOR_REVIEW` candidate.
- `review-result.schema.json`: reviewer-owned submitted result or the explicit `EMPTY` template.
- `review-decisions.schema.json`: pending/decided human escalation records.
- `review-history-index.schema.json`: materialized append-only history index.
- `orchestrator-state.schema.json`: durable autonomous runtime, candidate-custody, blocker, and resume projection.
