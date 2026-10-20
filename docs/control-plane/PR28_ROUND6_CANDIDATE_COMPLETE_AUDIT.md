# PR #28 Round 6 candidate-complete audit

Status: repair prepared; final identity is resolved post-commit through the existing Publisher/Consumer contract.

This audit covers only Round 6 control-plane findings. It does not modify Source Library product behavior, authorize another reviewer call, or authorize merge.

## Authority boundary

- The tracked commit is a checkpoint and cannot contain its own SHA.
- `CODEX_STATUS.md`, `.ai/REVIEW_REQUEST.md`, `.ai/REVIEW_RESULT.md`, orchestrator state and review history are fingerprint-excluded mutable bus artifacts.
- The sealed candidate is the final GitHub PR HEAD plus the recomputed fingerprint.
- The final deterministic evidence is an ignored post-commit receipt with stable before/after fingerprints and read-back.
- `.ai/PUBLICATION_RECEIPT.md` and the canonical Consumer validate the live PR marker and external GitHub record. No committed checkpoint may substitute for them.

## Round 6 findings

| Finding | Consolidated repair | Regression/read-back requirement | Status before any future reviewer |
| --- | --- | --- | --- |
| `finding-no-deterministic-evidence` | Require post-commit verifier receipt bound to the live HEAD/fingerprint; committed checkpoint is not presented as final evidence. | Full verifier PASS, stable fingerprint, evidence read-back, exact PR marker read-back. | `FIXED_PENDING_REVIEW` |
| `finding-status-identity-mismatch` | Document checkpoint versus final identity; clean publication validation ignores historical bus bytes only after exact live HEAD/marker/fingerprint resolution. | Negative tests reject stale HEAD, marker or fingerprint; live PR read-back must match. | `FIXED_PENDING_REVIEW` |
| `finding-review-state-not-ready` | Invalidate the old local request, allocate `review-mainline-integration-20261020-002`, and seal it only after final verification. Orchestrator/request/custody must agree. | `review-validate`, immutable request snapshot digest, and candidate-complete audit. | `FIXED_PENDING_REVIEW` |
| `finding-review-budget-inconsistent` | Preserve distinct counters: legacy repository review history; successor Ubuntu Claude cumulative budget `6/6`; integration-local request cycle. The local cycle is an identifier, not additional model authority. | Tests assert namespace separation and `READY_FOR_REVIEW_BUDGET_BLOCKED`; no model invocation. | `FIXED_PENDING_REVIEW` |

## Mandatory stop

After verification and request sealing, Runner state must be `READY_FOR_REVIEW_BUDGET_BLOCKED`. Ubuntu Claude is 6/6. A seventh review, ChatGPT Work notification, merge, Issue #9 admission, and D3 dispatch remain forbidden without separate authority.
