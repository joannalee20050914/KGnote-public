# Canonical publication receipt resolver

This contract resolves the active mainline integration candidate without embedding a commit SHA inside that same commit. Legacy PR #23 remains historical provenance only.

- canonical repository: `joannalee20050914/KGnote-public`
- canonical pull request: `28`
- canonical branch: `codex/mainline-integration-20261020`
- request marker: `KGNOTE_PRODUCT_REVIEW_REQUEST_V2`
- fingerprint algorithm: `sha256-canonical-json-v3-branch-independent-review-bus-exclusions`

The resolver requires open Draft PR #28 directly based on `main` and exactly one marker. It requires marker `candidate_commit` to equal the live PR head SHA, then must recompute the repository fingerprint and match the exact Consumer identity. Missing or mismatched evidence fails closed.

A literal current commit SHA must never be required inside the bytes of that same commit.
