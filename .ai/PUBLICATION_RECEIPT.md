# Canonical publication receipt resolver

This tracked artifact defines how a fresh process resolves the exact external-review candidate without attempting to embed a commit's own SHA inside that same commit.

- canonical repository: `joannalee20050914/KGnote-public`
- canonical pull request: `1`
- canonical branch: `codex/kg-note-autonomous-review`
- request marker: `KGNOTE_PRODUCT_REVIEW_REQUEST_V2`
- fingerprint algorithm: `sha256-canonical-json-v3-branch-independent-review-bus-exclusions`

Resolution is fail closed:

1. Read the live canonical PR and require it to be open in the configured repository.
2. Parse exactly one request marker from the PR body.
3. Require marker `candidate_commit` to equal the live PR head SHA.
4. Check out that SHA and recompute the repository fingerprint.
5. Require the recomputed value to equal marker `candidate_fingerprint`.
6. Only that resolved tuple may be passed to the external-result consumer.

Snapshot acquisition is adapter-specific, but validation is not. A local runtime may
resolve the live PR with the declared `gh` dependency. A connected-GitHub reviewer
runtime without `gh` must read the PR through its authenticated connector and inject
that exact response as `KGNOTE_VERIFIED_PR_SNAPSHOT_JSON`, including
`transport=connected_github`, `repository`, `pull_request`, `headRefOid`, `body`,
`state`, and `url`. Both paths execute the same repository/PR/head/marker/fingerprint
checks. Missing tooling, malformed snapshots, or mismatched identity return a
structured `publication_adapter` failure; they must never traceback or skip checks.

The branch name is diagnostic metadata only and is excluded from the v3 digest. A branch checkout and a detached checkout of the same commit and candidate entries must recompute the same fingerprint.

`CODEX_STATUS.md`, `.ai/REVIEW_REQUEST.md`, `.ai/review-state.json`, and `.ai/external-review-state.json` are execution receipts and may describe a later local state. They are not competing external candidate authorities. A literal current commit SHA must never be required inside the bytes of that same commit.
