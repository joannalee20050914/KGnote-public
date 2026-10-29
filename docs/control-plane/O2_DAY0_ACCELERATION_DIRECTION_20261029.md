# O2 Day 0 acceleration readiness direction

Status: active execution direction from the Product Owner on 2026-10-29. This
record selects schedule option A and authorizes only the minimum immutable
successor version, exact verification, independent Ubuntu Claude review,
normal GitHub integration, matching Mac/Ubuntu deployment, no-model acceptance
and Owner-approval package. It is not the Product Owner APPROVE command and
does not authorize an O2 product-model reservation, attempt or dispatch.

## Reused authority and immutable predecessor

- Goal ID remains `GOAL-KGNOTE-O2-READING-EXPERIENCE`.
- Product direction, title, outcome, requirements, RC/FD bindings, Work Items,
  obligations, completion conditions, safety policy and human gates remain
  unchanged.
- PR #40 and merged revision
  `dc7faa2a374fad5b3ec895ef85001f4c32457281` are the engineering baseline.
- v3 version, digest, state, ledger, checkpoints, deployment evidence and
  acceptance receipts are immutable and may not be edited or backdated.
- The minimum successor is
  `2026-10-29.4-bounded-trial-day0-proposal`, canonical digest
  `7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f`.

## Schedule contract

- Proposed start: `2026-10-29T17:00:00+08:00`.
- Day 0 is the remaining 2026-10-29 work window after lawful activation. It is
  not one of the five full observation work dates.
- Five full observation work dates: 2026-10-30, 2026-11-02, 2026-11-03,
  2026-11-04 and 2026-11-05.
- The ten Goal work dates are 2026-10-29, 2026-10-30, 2026-11-02,
  2026-11-03, 2026-11-04, 2026-11-05, 2026-11-06, 2026-11-09,
  2026-11-10 and 2026-11-11.
- The tenth-Goal-workday hard stop is
  `2026-11-11T18:00:00+08:00`.
- The daily work window remains 09:00-18:00 Asia/Taipei.
- Every Day 0 model reservation and attempt counts normally; the partial day is
  excluded only from the five-full-observation-day count.

## Resource and history boundary

Codex remains capped at five charges across versions. The prior three charges
remain charged, so only two are available. Claude remains capped at eight.
No extra quota, paid API, history rewrite, ledger concatenation, checkpoint
replacement or human-gate promotion is authorized.

The existing product checkout remains branch `codex/o2-reading-experience`,
commit `483f9e64066821d5d647d411e6da8ddb50ad88e5`, fingerprint
`4fc43f5da4dc5af6037546b6c0e67ee22f6081bf8d509cae9a4f839d5dd240b4`.
A version change does not reset its Work Items or create product progress.

## Ordered launch gates

The required order is:

1. Seal the new spec and canonical digest.
2. Run exact-candidate deterministic verification.
3. Obtain independent Ubuntu Claude PASS for the exact candidate.
4. Merge normally through GitHub.
5. Deploy and read back the same integrated tree on Mac Runner and Ubuntu.
6. Pass deployed no-model positive and negative admission acceptance.
7. Seal three activation dependency receipts for carryover, deployment and
   no-model acceptance.
8. Produce an exact Owner APPROVE draft without publishing it.
9. After the Product Owner publishes it, the Runner must read back the exact
   command and begin observation strictly before the proposed start.

If any prerequisite or Runner observation misses 17:00, v4 remains
`APPROVAL_REQUIRED` / `PAUSED`; no RESUME, backfill or shortened launch is
allowed. A later immutable version is then required.

## Forbidden actions

- Do not publish Owner APPROVE, RESUME or ACCEPT.
- Do not create an O2 product reservation, attempt, checkpoint or model launch
  before exact Owner approval is read back.
- Do not edit v3 or the prior formal v2 state, ledger or checkpoints.
- Do not bypass independent review, GitHub rules, matching deployment or
  no-model acceptance.
- Do not increase provider ceilings, use paid API or promote human/release
  gates.
