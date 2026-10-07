# Incident: external product-review cycle bypass and repository split brain

Date: 2026-10-07
Status: active corrective-action record

## What happened

The accepted migration contract designated `joannalee20050914/KGnote-public` as the only canonical public repository and `joannalee20050914/KGnote` as a private archive. A later public-readiness goal omitted that migration record from its authoritative specs, made the archive public, published candidate PR `KGnote#23`, and treated a local ephemeral internal-reviewer PASS as sufficient to proceed toward `PA-HUMAN-1`.

PR `KGnote#23` had no GitHub comments or reviews. Meanwhile `KGnote-public#1` contained the actual ChatGPT Work external product review for head `15d043c786a33e7a1a97c61519a49f6eb7c1091d`: `CHANGES_REQUIRED`, five blocking findings, and no required human decision. The external findings were therefore stranded on the canonical review surface while implementation advanced on the wrong repository.

## Why safeguards did not stop it

- repository authority was represented in a migration record but was not a required locked invariant for later publication plans;
- candidate, canonical, trigger, and review-request repository identities were not compared;
- the state machine modeled one generic reviewer role and allowed an internal ephemeral reviewer to satisfy wording that also referred to ChatGPT Work;
- the canonical branch did not contain the prepared fail-closed GitHub review consumer;
- human-checkpoint progression checked only internal review completion, not existence of an exact external GitHub product-review artifact.

## Impact

The owner was incorrectly made the next actor despite available autonomous AI review and repair work. This duplicated supervision, split evidence across repositories, left blocking findings unconsumed, and spent substantial review and implementation tokens on candidates that could not trigger the configured transport.

## Corrective invariants

- Internal reviewer PASS is not external product-review PASS.
- Human gate eligibility requires a verified exact-candidate external artifact with no blocking findings.
- Repository identity must agree across authority, publication, event trigger, request, and evidence.
- External findings automatically route to repair, verification, republication, and re-review.
- An archived repository cannot become an active review surface without a new explicit migration decision.
- Goal completion cannot terminate the autonomous pipeline while external review remains pending.

## Regression coverage

Automated tests cover wrong-repository publication, migration split brain, missing external evidence, internal PASS with external review absent, external `CHANGES_REQUIRED`, stale candidate identity, and premature human-checkpoint transition. Durable PLAN, STATUS, external-review state, and this incident record allow a fresh session to recover the same constraints.

## Canonical lesson

> Human gate 前必須先耗盡已授權的 autonomous AI review / repair 能力。Internal PASS 不代表可以叫 human。External review transport 沒有實際產生 review evidence，就視為 review 尚未發生。
