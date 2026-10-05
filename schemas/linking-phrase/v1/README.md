# Linking phrase candidate staging v1

This boundary is separate from extraction output, canonical Edge records, and accepted Guided Map
specifications. A trusted adapter supplies snapshot-bound canonical Edges and source-grounded
Evidence. Fresh extraction Evidence may still be `unreviewed`; it is present only to support a
`pending` proposal. An untrusted model may return only `{edge_id, linking_phrase}` proposals.

The adapter rejects missing, duplicate, extra, generic, or malformed proposals; reconstructs every
endpoint, direction, relation, Evidence ID, and locator from trusted context; and emits candidates
with `review_status: pending`. Human `accept`, `correct`, or `reject` decisions are saved in an
append-only reviewed set. An accepted/corrected phrase is eligible for later Guided Map promotion
only when every supporting Evidence is also `accepted` or `corrected`.
