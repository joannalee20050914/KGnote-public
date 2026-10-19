# Autonomous external product-review contract

Status: active execution contract. This extends the repository review control plane; it does not change product requirements or promote a human gate.

## Canonical identities

- canonical repository: `joannalee20050914/KGnote-public`
- candidate repository: `joannalee20050914/KGnote-public`
- configured ChatGPT Work trigger repository: `joannalee20050914/KGnote-public`
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
→ ChatGPT Work external product review
→ blocking findings: repair → verify → republish → re-review
→ external PASS with no blocking findings
→ component evidence saved and next Ready work selected
→ optional deduplicated SOFT_FEEDBACK_AVAILABLE when operable
→ FINAL_HUMAN_ACCEPTANCE_REQUIRED only after complete Issue #21 delivery evidence
```

Internal reviewer evidence and external product-review evidence are different artifacts. An internal PASS never satisfies the external gate. The external artifact must be an actual GitHub PR review or top-level PR comment on the canonical pull request, name the exact repository, PR, head commit, and candidate fingerprint, and carry a parseable verdict and findings. Exact candidate identity is resolved by `.ai/PUBLICATION_RECEIPT.md`; mutable local execution receipts are not competing identity authorities. Absence, ambiguity, stale identity, wrong repository, or a local role assertion means the external review has not happened.

## State invariants

1. `candidate_repository == canonical_repository == trigger_repository == review_request_repository` or fail closed.
2. A candidate may enter `AWAITING_EXTERNAL_PRODUCT_REVIEW` only after deterministic verification, internal review, exact publication, and remote read-back bind the same commit and fingerprint.
3. `EXTERNAL_CHANGES_REQUIRED` automatically routes every blocking finding to repair; the owner is not a message broker.
4. `FINAL_HUMAN_ACCEPTANCE_REQUIRED` is unreachable until a verified external artifact says PASS with no blocking finding for the exact complete product candidate and every final-gate prerequisite is positively evidenced. Historical `AWAITING_HUMAN_ACCEPTANCE` and `HUMAN_CHECKPOINT_REQUIRED` are superseded emission names.
5. Goal completion is non-terminal while external review is pending or blocking findings remain.
6. Context rollover and orchestrator restart recover these facts from repository state, not chat history.
7. Event transport is part of exact candidate publication. The configured one-line comment trigger is `@kgnote-ai-review <current PR head SHA>`; its entire body must match the configured template byte-for-byte, its repository/PR/head must match the candidate, and its GitHub artifact URL must be read back before publication can progress. Extra explanatory text makes the event invalid and fails closed rather than silently waiting or routing to a human.
8. A `CHANGES_REQUIRED -> PASS` transition for the same commit and fingerprint is invalid unless the later result contains structured, independently checkable new evidence linked to every prior blocking finding. A new reviewer invocation or an empty finding list is not new evidence. The item becomes `WORK_ITEM_BLOCKED`; the Runner must not repeatedly invoke reviewers until one returns PASS.

## Runner blocking scope and continuity

The product-review state of one Issue/PR and the scheduling state of the whole Runner are separate. The existing Pending Goal, work-package envelope, worker order, checkpoint, budget, writer lock, and GitHub queue metadata remain the control plane; this contract does not create a second queue database.

| State | Scope | Required effect |
|---|---|---|
| `WORK_ITEM_BLOCKED` | one Issue/PR | Preserve its reason, affected work, release condition, and next legal action; evaluate independent ready work. |
| `DEPENDENCY_BLOCKED` | the blocked item plus its dependency subgraph | Do not dispatch dependants; unrelated work remains eligible. |
| `GLOBAL_BLOCKED` | Runner or named shared resource | Stop every affected dispatch for authority, work-window, billing, safety, or shared-isolation reasons. |
| `FINAL_HUMAN_ACCEPTANCE_REQUIRED` | one exact complete product candidate | Preserve the final gate, exclude the item from formal delivery completion, and evaluate only work that is independently authorized without bypassing the final gate. It never implies merge or release permission. |
| `SOFT_FEEDBACK_AVAILABLE` | non-blocking event for one operable experience | Store exact candidate/scope, entry point, steps, questions, notification key/status, and any late reply. Never block Ready selection or infer PASS/FAIL from silence. |
| `NO_ELIGIBLE_READY_WORK` | scheduler outcome, not a failure | Remain idle and record why no authorized, dependency-complete, in-window, budgeted, safely isolated sealed order exists. |

An exact component-review PASS records `COMPONENT_REVIEW_COMPLETE`; it does not by itself select a human gate. The Runner may emit `FINAL_HUMAN_ACCEPTANCE_REQUIRED` only when the durable scheduler record names gate `D2-T14-FINAL-HUMAN-ACCEPTANCE`, identifies the exact complete product candidate and trial entry point, proves the formally approved scope, dependencies, cross-module integration, required scenarios, installation/setup/daily-use/backup/restore delivery evidence, RC, independent review and integrated verification complete for that same candidate, proves no known delivery blocker, and shows that formal human acceptance is still unevaluated. Otherwise it evaluates the next independently authorized Ready item, or records `NO_ELIGIBLE_READY_WORK` and waits normally.

The earlier generic “component/external PASS → human checkpoint,” stage-candidate concentrated trial, and mandatory intermediate smoke execution rules are `SUPERSEDED`. Their artifacts, failures, candidate identities, `PA-HUMAN-1`, and `NS-HUMAN-SMOKE` remain evidence; they are not executable current stop commands. Safety, privacy, consent, budget, destructive-operation, publication and merge constraints are not superseded.

Every block record must contain `scope`, `reason`, `affected_work`, `release_condition`, and `next_legal_action`. A GitHub `queue:ready` label is discovery metadata, not execution authority by itself. Dispatch additionally requires explicit authority, satisfied dependencies, an existing bounded budget, isolated worktree, `automatic_merge=false`, and a pre-sealed worker order accepted by the existing epoch/scope gate.

The legacy `.ai/ORCHESTRATOR_STOP` marker applies to the legacy goal/worktree named by its durable policy unless that policy explicitly says `GLOBAL`. The Runner never deletes or weakens it. An isolated successor or unrelated work item may proceed only when its own authority and safety envelope prove that the legacy marker is out of scope. Restart, next-day wake, or human acceptance does not reset completed work, reviewer/implementer usage, PR protection, or merge restrictions.

## External evidence boundary

GitHub metadata, a successful push, an internal `.ai/REVIEW_RESULT.md`, a Codex code-review summary, a reaction, or an automation run without a matching product-review artifact is insufficient. The accepted evidence record must retain the GitHub record ID/URL, author, source type, submitted time, reviewed commit, repository, PR, verdict, findings, and a digest of the original body.

`PA-HUMAN-1`, `NS-HUMAN-SMOKE`, native-device behavior, learner usability, learning effectiveness, and `release_verified` remain human/external gates and are not promoted by this contract.
