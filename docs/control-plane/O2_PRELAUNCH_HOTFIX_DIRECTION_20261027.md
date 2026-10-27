# O2 首次派工三項阻擋集中修復方向

Status: current Product Owner execution direction dated 2026-10-27. This is a bounded Control Plane hotfix authority. It is not a new KGnote Product Goal and does not change the immutable O2 product contract.

## Exact baseline

- Repository: `joannalee20050914/KGnote-public`
- Baseline `main`: `483f9e64066821d5d647d411e6da8ddb50ad88e5`
- Product Goal: `GOAL-KGNOTE-O2-READING-EXPERIENCE`
- Goal version: `2026-10-23.2-s0-s2-proposal`
- Goal spec SHA-256: `82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604`
- Product seed branch: `codex/o2-reading-experience`
- Product seed commit: `483f9e64066821d5d647d411e6da8ddb50ad88e5`
- Owner APPROVE: Issue #9 comment `6431195804`
- Authoritative host-local prelaunch receipt: `<host-runtime>/preflight/o2-20261027/PRELAUNCH_RECEIPT.md`, SHA-256 `0e8ad81ed66c453edc527449960a0ba40e8274b886db5cf2dbf0e786a1f8df1e`

The receipt is `PRELAUNCH_BLOCKED`. At authority read-back, formal O2 state and ledger remain byte-identical to the receipt, `candidate_identity` is absent, all Work Item attempts remain zero, and the Ubuntu work directory is a private empty non-Git directory.

## Authorized hotfix scope

One independent branch/worktree may repair only:

1. exact first-candidate binding for the fixed O2 version from the verified product seed branch while the Runner deployment is detached;
2. trusted, idempotent Ubuntu product checkout creation and validation before any model process starts;
3. the three formal Claude Schema Admission fields produced by the existing `claude_reviewer_adapter.py` projection;
4. a reproducible Python runtime and LaunchAgent cutover that no longer imports or executes from the old dirty/status-drift worktree;
5. directly necessary tests, deployment/read-back tooling and receipts.

The implementation must reject wrong branch, commit, Git common directory, Goal digest, schema/projection, interpreter, ownership, mode, symlink, dirty checkout, stale state and duplicate dispatch. Initial `pull_request=null` remains valid. PR #29, #32, #33 and other Legacy candidates are not valid O2 initial candidates.

Initial binding must be persisted through the existing append-only Product Goal ledger and state reconciliation. Formal JSON must not be hand-edited. The Ubuntu checkout must be prepared by a trusted pre-model bootstrap, must not overwrite a non-empty or dirty directory, and must be reusable on restart.

## Verification, review and conditional integration

The exact candidate must pass focused positive/negative tests, the 2026-10-28 09:00 Asia/Taipei isolated first-dispatch path, full deterministic verification, requirements guard and public-safety scan. It must then be pushed to one Draft PR based on `main` and reviewed by the existing Ubuntu Claude independent-review transport. Review evidence must bind the exact PR, HEAD, fingerprint and unchanged formal Consumer schema. This Control Plane review is not an O2 Work Item attempt.

Only an exact-candidate Claude `PASS`, no blocking findings and satisfied GitHub rules authorize normal PR merge under this one-time instruction. Force push, administrator bypass and direct `main` writes are forbidden.

After a legal merge, deployment may create a clean detached Runner worktree from the actual merge commit, deploy corresponding Ubuntu runtime files, install a pinned Python environment with source/version receipt, update and reload the existing LaunchAgent, perform no-model live state read-back, run the isolated first-dispatch matrix, and rehearse configuration rollback. Formal O2 state, ledger, Owner authority, checkpoints, attempts and Stop Markers must be preserved.

## Immutable boundaries

This direction does not authorize changing the O2 Goal WHAT, requirement set, Work Item DAG, model ceilings, `2026-10-28T09:00:00+08:00` start, `2026-11-10T18:00:00+08:00` hard stop, or published Owner APPROVE. It does not authorize starting Work Item A, merging a product PR, performing a model attempt, removing safety gates, adding a reviewer agent/schedule/transport, or using paid APIs.

If legal deployment and verification cannot complete before the trial start, the Runner must remain safely unable to dispatch and the outcome is `TRIAL_DATE_REAUTHORIZATION_REQUIRED`; no backdating, manual Run Now, shortened observation period or new Owner approval may be fabricated.

Allowed terminal outcomes are:

- `HOTFIX_REVIEWED_MERGED_DEPLOYED_PRELAUNCH_VERIFIED`
- `HOTFIX_BLOCKED_UNMERGED`
- `DEPLOYMENT_BLOCKED_OR_ROLLED_BACK`
- `TRIAL_DATE_REAUTHORIZATION_REQUIRED`

This direction is consumed when the centralized repair, exact review, conditional merge/deployment and Gate A–F read-back finish. It does not authorize O2 product model work.
