# Autonomous external product-review contract

Status: active execution contract. This extends the repository review control plane; it does not change product requirements or promote a human gate.

## Canonical identities

- canonical repository: `joannalee20050914/KGnote-public`
- candidate repository: `joannalee20050914/KGnote-public`
- configured Runner review-evidence repository: `joannalee20050914/KGnote-public`
- review-request repository: `joannalee20050914/KGnote-public`
- canonical pull request for the authorized Issue #19 single-round verification: `joannalee20050914/KGnote-public#22`
- historical pull request retained without mutation: `joannalee20050914/KGnote-public#1`
- archival repository: `joannalee20050914/KGnote`

All four active repository identities must be equal. The archival repository must remain private and must not receive candidate publication or review-trigger events unless a later explicit migration decision supersedes `CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md`. The PR #22 binding is limited to this single-round transport verification and does not supersede or modify the historical evidence on PR #1.

## Required pipeline

```text
Codex implementation
→ deterministic verification
→ internal reviewer
→ exact candidate publication
→ Ubuntu Claude independent product review
→ Runner GitHub top-level-comment relay and canonical Consumer read-back
→ blocking findings: repair → verify → republish → re-review
→ external PASS with no blocking findings
→ PA-HUMAN-1 / NS-HUMAN-SMOKE eligibility
```

Internal reviewer evidence and external product-review evidence are different artifacts. An internal PASS never satisfies the external gate. The external artifact must be an actual GitHub PR review or top-level PR comment on the canonical pull request, name the exact repository, PR, head commit, and candidate fingerprint, and carry a parseable verdict and findings. Exact candidate identity is resolved by `.ai/PUBLICATION_RECEIPT.md`; mutable local execution receipts are not competing identity authorities. Absence, ambiguity, stale identity, wrong repository, or a local role assertion means the external review has not happened.

As approved in `CLAUDE_REVIEWER_ROLE_DECISION_20261020.md`, Ubuntu Claude is the
routine independent product reviewer. The Runner may relay its complete, unmodified
result through the authenticated GitHub publisher, but the comment must name the true
Claude transport and must not claim to be a ChatGPT Work review. The Consumer accepts
only the fetched GitHub record and retains both reviewer and publisher identities.
ChatGPT Work is notification-only for eligible soft feedback or final human acceptance;
routine review, retry, progress and dispatch events never trigger it. The former
Work-per-round reviewer and one-line Work trigger requirements are `SUPERSEDED`.

## State invariants

1. `candidate_repository == canonical_repository == trigger_repository == review_request_repository` or fail closed.
2. A candidate may enter `AWAITING_EXTERNAL_PRODUCT_REVIEW` only after deterministic verification, internal review, exact publication, and remote read-back bind the same commit and fingerprint.
3. `EXTERNAL_CHANGES_REQUIRED` automatically routes every blocking finding to repair; the owner is not a message broker.
4. `AWAITING_HUMAN_ACCEPTANCE`, `HUMAN_CHECKPOINT_REQUIRED`, `PA-HUMAN-1`, and `NS-HUMAN-SMOKE` are unreachable until a verified external artifact says PASS and contains no blocking finding for the exact current candidate.
5. Goal completion is non-terminal while external review is pending or blocking findings remain.
6. Context rollover and orchestrator restart recover these facts from repository state, not chat history.
7. Event transport is part of exact candidate publication. The Runner writes one schema-bound top-level PR comment only after exact identity and authority checks, then fetches the record from GitHub and validates its real ID, URL, author, submitted time and body digest. Duplicate exact evidence is reused, not rewritten. Write or read-back failure fails closed and never consumes another Claude round.
8. ChatGPT Work notification is permitted only for deduplicated `SOFT_FEEDBACK_AVAILABLE` or fully evidenced `FINAL_HUMAN_ACCEPTANCE_REQUIRED`. Unverified delivery remains `NOT_VERIFIED` with the event retained; it cannot block routine product work or be reported as sent.

## External evidence boundary

GitHub metadata, a successful push, an internal `.ai/REVIEW_RESULT.md`, a Codex code-review summary, a reaction, or an automation run without a matching product-review artifact is insufficient. The accepted evidence record must retain the GitHub record ID/URL, author, source type, submitted time, reviewed commit, repository, PR, verdict, findings, and a digest of the original body.

`PA-HUMAN-1`, `NS-HUMAN-SMOKE`, native-device behavior, learner usability, learning effectiveness, and `release_verified` remain human/external gates and are not promoted by this contract.
