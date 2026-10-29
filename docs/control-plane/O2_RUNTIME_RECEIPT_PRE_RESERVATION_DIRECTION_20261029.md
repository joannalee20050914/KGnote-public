# O2 runtime receipt pre-reservation repair direction

Status: active execution direction issued by the product owner on 2026-10-29.
Direction ID: `kgnote-o2-runtime-receipt-pre-reservation-2026-10-29`.

This direction authorizes one bounded S2 safety repair named
`O2-RUNTIME-RECEIPT-PRE-RESERVATION`. It does not authorize an O2 Product Goal
`RESUME`, a new product work order, another model-bearing attempt, a schedule
change, a quota increase, or promotion of any human/release gate.

## Exact baseline and reused evidence

- Development starts from merged PR #38 on `main` at
  `44f36b40791d375d74b9b161c81c92e9f8e65ea7`.
- The implementation reuses the prior Codex B read-only audit in the Codex task
  titled `審核部署後模型派工關卡`; it does not reopen the full autonomy
  architecture investigation.
- It also preserves the PR #38 W4 deployment read-back: Ubuntu current runtime
  generation `44f36b40791d375d74b9b161c81c92e9f8e65ea7`, runtime manifest SHA-256
  `b86d9e4ee94dfa2ad9b058ce784bb712aa242ec13aa9311afcf5b3c248863a42`,
  deployment receipt SHA-256
  `484da34d3da35432f861e6b4cbf9a83d6fcd25b847778a2b66ea71346ca9fd95`,
  and zero model launches during that deployment acceptance.

## Required behavior

1. Reuse the existing Runner, Router, Worker, systemd, guard, Landlock and
   immutable runtime-generation mechanisms. Do not create another autonomous
   dispatch framework.
2. Add a real Ubuntu `admission-only` route that exercises the deployed runtime
   through SSH, bootstrap, systemd, guard, Landlock and Worker admission without
   starting Codex, Claude, a successor agent, or any model process.
3. Deployment acceptance uses a dedicated probe identity, order/context and
   evidence directory. It must not reuse or impersonate the paused Product
   Goal's historical `ACTIVE`/`RESUME` authority.
4. Every model-bearing reservation must present the latest successful live
   admission receipt. `reserve_dispatch()` itself validates it before appending
   `MODEL_ATTEMPT_STARTED` with operation `DISPATCH_RESERVED`, so no caller can
   bypass the gate.
5. The receipt must bind the exact WorkOrder bytes/digest, candidate revision,
   current formal authority/state identity, runtime generation, reviewed
   revision/tree, manifest digest and installed file digests. It must be fresh
   and single-use for the exact reservation.
6. After admission succeeds, normal execution must remain pinned to the same
   immutable runtime generation and revalidate its manifest/file hashes before
   any model process starts. Runtime pointer or file drift fails closed.
7. Missing modules, missing dependency lock, file/hash drift, wrong checkout,
   SSH/bootstrap/systemd/guard/Landlock failures, malformed/stale/mismatched
   receipts and generation changes are negative acceptance cases.
8. Every pre-reservation admission failure must leave formal state, ledger,
   cursor, attempts, dispatches, checkpoints and model launches unchanged.

## Preserved production boundary

Throughout implementation, review, merge, deployment and no-model acceptance:

- `GOAL-KGNOTE-O2-READING-EXPERIENCE` remains `PAUSED` / `BLOCKED` with
  `go_live_authorized=false`;
- the three historical reservations/launch-accounting entries remain intact and
  are not deleted, reclassified or reset;
- no fourth Product Goal reservation, dispatch, attempt or model launch is
  authorized;
- no formal quota or schedule is increased;
- `release_verified=false`, `D2-T14-FINAL-HUMAN-ACCEPTANCE`, `PA-HUMAN-1` and
  `NS-HUMAN-SMOKE` remain unpromoted.

## Delivery and claim boundary

The exact candidate must pass deterministic verification, a Draft PR and the
existing independent Ubuntu Claude review before normal GitHub integration.
Only an exact independent PASS plus satisfied repository rules authorizes merge
and bounded deployment. After deployment, positive and negative real-Ubuntu
admission acceptance runs under PAUSE with before/after formal state and ledger
hashes.

A successful result proves only `無模型准入已通過` for the exact deployed
generation and evidence tuple. It does not prove `真正產品模型開發已通過`; that
claim requires a later, separately authorized Product Goal trial.
