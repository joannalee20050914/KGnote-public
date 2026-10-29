# O2 v4 admission event identity repair direction

Status: active Product Owner execution direction dated 2026-10-29.
Direction ID: `kgnote-o2-admission-event-id-repair-2026-10-29`.

This direction authorizes one bounded Control Plane repair for the first O2 v4
dispatch failure. It is not a new Product Goal, does not authorize a product
model launch, and does not alter the immutable v4 Goal version, digest,
authority, schedule, Work Items, provider ceilings or historical trial result.

## Exact baseline

- Canonical repository: `joannalee20050914/KGnote-public`.
- Merged and deployed baseline: `8a242fff318af636b937e9f9540d0121fa9c0191`.
- Product Goal: `GOAL-KGNOTE-O2-READING-EXPERIENCE`.
- Goal version: `2026-10-29.4-bounded-trial-day0-proposal`.
- Goal spec SHA-256:
  `7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f`.
- Formal ledger cursor: `3`; Codex accounting: `3/5`; v4 attempts: `0`.
- The 2026-10-29 transition-start SLO remains `VIOLATED`.

The confirmed defect is limited to the Mac-side reservation receipt validator:
the Router correctly derives a separate `o2-admission-*` event identity from
the challenge, exact WorkOrder SHA-256 and exact runtime identity, while the
validator and shared fixtures incorrectly expected the product WorkOrder event
identity.

## Required repair

1. Preserve the independent product WorkOrder and admission Router identities.
2. Share the Router canonical JSON plus SHA-256 admission-ID algorithm with the
   receipt validator and require the exact derived ID.
3. Continue to bind the product `order_event_id` exactly across WorkOrder,
   receipt and Worker evidence.
4. Replace the misleading fixture and add a real Router-path no-model positive
   integration plus wrong event ID, challenge, WorkOrder hash, runtime identity
   and checkpoint-tamper negatives.
5. Every negative must stop before reservation or ledger append and must never
   start Codex, Claude or another product model.
6. Complete exact verification, independent Ubuntu Claude review, normal PR
   merge, controlled Mac/Ubuntu deployment and deployed no-model acceptance.

## Preserved formal boundary

Formal v4 state, ledger, checkpoints, activation receipts, Owner APPROVE,
provider accounting and the failed 2026-10-29 observations are read-only. No
`APPROVE`, `RESUME`, `DISPATCH_RESERVED`, attempt or fabricated execution event
may be added by this repair. A new runtime generation must receive current
deployment and no-model evidence without rewriting or backdating any historical
activation receipt. If the existing v4 authority contract cannot admit a new
reviewed runtime generation without changing formal history, deployment stops
fail closed and reports the conflict.

The successful completion boundary is narrow: a genuine Router-generated
admission checkpoint is accepted by the deployed Mac validator, while an
incorrect admission identity is still rejected before accounting. Existing v4
authority may then resume only through the ordinary Runner during an authorized
work window.
