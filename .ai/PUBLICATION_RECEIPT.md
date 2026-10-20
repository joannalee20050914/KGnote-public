# Historical canonical publication resolver

This preserved contract records the fail-closed resolver used for legacy PR #23. It is historical provenance, not the active integration candidate identity.

- canonical repository: `joannalee20050914/KGnote-public`
- canonical pull request: `23`
- canonical branch: `codex/issue-8-source-library`
- request marker: `KGNOTE_PRODUCT_REVIEW_REQUEST_V2`
- fingerprint algorithm: `sha256-canonical-json-v3-branch-independent-review-bus-exclusions`

The resolver requires an open PR and exactly one marker. It requires marker `candidate_commit` to equal the live PR head SHA, then must recompute the repository fingerprint and match the exact Consumer identity. Missing or mismatched evidence fails closed. A future integration publication must create its own live receipt; this file cannot authorize or verify it.

A literal current commit SHA must never be required inside the bytes of that same commit.
