# Autonomous external product-review contract

Status: active execution contract. This extends the repository review control plane; it does not change product requirements or promote a human gate.

## Canonical identities

- canonical repository: `joannalee20050914/KGnote-public`
- candidate repository: `joannalee20050914/KGnote-public`
- configured ChatGPT Work trigger repository: `joannalee20050914/KGnote-public`
- review-request repository: `joannalee20050914/KGnote-public`
- canonical pull request: `joannalee20050914/KGnote-public#1`
- archival repository: `joannalee20050914/KGnote`

All four active repository identities must be equal. The archival repository must remain private and must not receive candidate publication or review-trigger events unless a later explicit migration decision supersedes `CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md`.

## Required pipeline

```text
Codex implementation
→ deterministic verification
→ internal reviewer
→ exact candidate publication
→ ChatGPT Work external product review
→ blocking findings: repair → verify → republish → re-review
→ external PASS with no blocking findings
→ PA-HUMAN-1 / NS-HUMAN-SMOKE eligibility
```

Internal reviewer evidence and external product-review evidence are different artifacts. An internal PASS never satisfies the external gate. The external artifact must be an actual GitHub PR review or top-level PR comment on the canonical pull request, name the exact repository, PR, head commit, and candidate fingerprint, and carry a parseable verdict and findings. Exact candidate identity is resolved by `.ai/PUBLICATION_RECEIPT.md`; mutable local execution receipts are not competing identity authorities. Absence, ambiguity, stale identity, wrong repository, or a local role assertion means the external review has not happened.

## State invariants

1. `candidate_repository == canonical_repository == trigger_repository == review_request_repository` or fail closed.
2. A candidate may enter `AWAITING_EXTERNAL_PRODUCT_REVIEW` only after deterministic verification, internal review, exact publication, and remote read-back bind the same commit and fingerprint.
3. `EXTERNAL_CHANGES_REQUIRED` automatically routes every blocking finding to repair; the owner is not a message broker.
4. `AWAITING_HUMAN_ACCEPTANCE`, `HUMAN_CHECKPOINT_REQUIRED`, `PA-HUMAN-1`, and `NS-HUMAN-SMOKE` are unreachable until a verified external artifact says PASS and contains no blocking finding for the exact current candidate.
5. Goal completion is non-terminal while external review is pending or blocking findings remain.
6. Context rollover and orchestrator restart recover these facts from repository state, not chat history.

## External evidence boundary

GitHub metadata, a successful push, an internal `.ai/REVIEW_RESULT.md`, a Codex code-review summary, a reaction, or an automation run without a matching product-review artifact is insufficient. The accepted evidence record must retain the GitHub record ID/URL, author, source type, submitted time, reviewed commit, repository, PR, verdict, findings, and a digest of the original body.

`PA-HUMAN-1`, `NS-HUMAN-SMOKE`, native-device behavior, learner usability, learning effectiveness, and `release_verified` remain human/external gates and are not promoted by this contract.
