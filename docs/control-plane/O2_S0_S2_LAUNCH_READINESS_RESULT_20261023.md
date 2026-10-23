# O2 S0–S2 啟動準備結果

Status: `BLOCKED_WITH_SPECIFIC_GAPS`

Observed at: 2026-10-23 Asia/Taipei. This is an engineering-readiness result, not Product Owner authority, independent review PASS, deployment approval, or live-product evidence.

## Outcome

S0 is implemented and deterministically verified as proposal version `2026-10-23.2-s0-s2-proposal`. S1 fails on the actual runtime boundary before a lawful first O2 order can be dispatched, so S2 cannot produce an exact deployable candidate. The formal LaunchAgent remains dormant and unchanged; O2 was not activated.

| Claim | Result | Evidence boundary |
| --- | --- | --- |
| IMPLEMENTED | partial | S0 spec/schema/backlog/package only |
| DETERMINISTIC_VERIFIED | yes for S0 | Product Goal contract validation and seven targeted tests pass |
| INTEGRATION_VERIFIED | no | current end-to-end PASS uses a no-model fixture that creates orders and worker results inside the harness |
| INDEPENDENT_REVIEWED | no for this proposal | PR #32 baseline `de5c8c0` retains its prior exact PASS; this delta has not been submitted as a deployable candidate |
| DEPLOYMENT_PREPARED | no | exact delta and rollback are documented, but S1 runtime bytes do not exist |
| LIVE_PRODUCT_TRIAL_NOT_STARTED | yes | LaunchAgent has no `--product-goal-*` arguments and active count is zero |

## S0 result

- Work Item A is `WI-O2-A-IMPLEMENT` through A verify/publish/review/repair and covers the Obsidian reading entry, source-bounded prose, shared identity read-back and A exact-candidate evidence.
- Work Item B is `WI-O2-B-IMPLEMENT` through B verify/publish/review/repair and covers context-local source-sentence notes plus B exact-candidate evidence. B depends on terminal A review and repair states; A cannot close B or O2.
- Codex and Ubuntu Claude each have `max_launches_per_window=3`, `max_total_launches=8`, 300-second minimum launch interval and 3600-second quota backoff. Global concurrency is one; paid API is forbidden; the Goal total never resets by day or session.
- The eight-launch proposal covers two A/B initial launches, four bounded repair/re-review launches and two invalid-start/envelope or quota contingencies. The historical basis is three Codex repair attempts, four valid Claude verdicts and one Claude 429 attempt in Issue #9 history; legacy counters are preserved rather than inherited or reset.
- Proposed observation dates are 2026-10-28, 10-29, 10-30, 11-02 and 11-03. Proposed activation is 2026-10-28 09:00, observation ends 2026-11-03 18:00, and the tenth-Goal-workday hard stop is 2026-11-10 18:00. A late activation requires a new immutable version and new dates.
- Gates are: successor start within 600 seconds, two cross-window resumptions, one safe Runner restart, zero ordinary human relay and no more than 50 engineering-supervision minutes.

Canonical JSON digest: `82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604`. File SHA-256: `8434386012c09546b5c3dd17a86c78ef05248d5391699398efc8beea526e7fd9`.

## S1 direct blockers

### G1 — no trusted dynamic order planner/binder

`scripts/goal_runner_adapter.py::validated_bound_order` explicitly resolves only an existing `dispatch_binding` or a finite `dispatch_bindings` queue and says it never synthesizes an order from Goal prose. The real O2 initial state contains neither. Reproduction against the proposed spec returns:

```json
{"error":"selected work item has no Runner-owned sealed dispatch binding","probe":"runner_dynamic_order","status":"REJECTED"}
```

Impact: there is no lawful non-human source for the first A order, a repair order with a new candidate, the successor review order, or A-to-B dispatch.

Minimum repair: a Runner-owned planner must derive the next order from the selected immutable Work Item and current exact state, atomically seal it, validate its digest/path/authority, and append its binding before reservation. It must never predict a future commit SHA. Positive coverage must traverse A implementation → verification/publication → review → repair/new candidate/re-review → B; negative coverage must reject stale, replaced, out-of-root and exhausted bindings.

### G2 — real workers do not produce the Product Goal result envelope

Only `scripts/goal_runner_adapter.py` and `scripts/run_product_goal_isolated_trial.py` reference `product_goal_result` or `kgnote.product-goal-worker-result.v1`. The former consumes it; the latter fabricates it in a no-model fixture. Codex, Publisher and Claude production entrypoints emit their own evidence/checkpoint shapes but no canonical Product Goal result.

Impact: a completed worker checkpoint is downgraded to `EVIDENCE_INSUFFICIENT`; attempt identity, candidate commit/fingerprint, verification, publication read-back, review findings/verdict, usage/429 and next-work evidence cannot reach the Runner through the required envelope.

Minimum repair: one shared result adapter must translate each real worker's durable output into the schema, preserve raw output on invalid envelopes, bind the exact order/candidate and write the result before the route checkpoint becomes complete. Restart must reconcile that checkpoint first and must not blindly relaunch a model. Positive tests must cover all three lanes; negative tests must cover missing/mismatched/invalid envelopes and 429 without verdict.

### G3 — Linux admission identity rejects O2 work items

Both `scripts/linux_worker_router.py::validate_bootstrap_identity` and `scripts/linux_worker_bootstrap.py::_validate_generic_identity` restrict generic work items to `D2-T[0-9]{2}`, a Codex-only stage and a 2026-10-19 event suffix. Reproduction returns:

```json
{"error":"generic bootstrap work-item identity is invalid","probe":"linux_o2_identity","status":"REJECTED"}
```

Impact: even a correctly sealed `WI-O2-A-IMPLEMENT` order cannot pass the deployed generic router/bootstrap. Review and deterministic publisher lanes also lack an O2-compatible generic identity route.

Minimum repair: validate the existing Product Goal `WI-[A-Z0-9-]+` identity together with goal/version/spec digest, order event, provider stage, exact branch/worktree and Owner authority. Preserve the legacy D2 route as a separate compatibility path. Add positive O2 Codex/Publisher/Claude cases and negative cross-goal, wrong-stage, wrong-digest and path-escape cases.

## S2 read-back and boundary

- PR #32 remains Draft/open at exact HEAD `de5c8c01c86ffc87896dca1337817892bfb5eff6`, base `7bb0ffb4be6d5eb19398f249f45fa8e32a083131`; its earlier exact independent PASS is unchanged and does not review this proposal.
- Draft PR #33 contains this blocked preparation result and is stacked on PR #32; it is not a deployable candidate and has not been submitted for independent review.
- Deployed Runner: `7bb0ffb4be6d5eb19398f249f45fa8e32a083131`.
- Deployed router: `7dbaeb6872cea07f5f8eb6ebdff8b29359cd2d66`.
- Deployed epoch/scope admission: `b3293908847ac8296c37402ab1a3876e50b2b38a`.
- LaunchAgent read-back: `com.kgnote.local-autonomy-runner`, active count `0`, state `not running`, no `--product-goal-spec`, `--product-goal-state`, `--product-goal-ledger` or `--product-goal-backlog` arguments.
- The existing isolated trial returns `PASS` only with `fixture_repository=example.invalid`, `production_activation=false`, `model_invocations=0` and `external_writes=0`. Its harness creates `_order` and `_worker_result` directly. This verifies reducer/recovery behavior, not the missing real integration.

Because G1–G3 block the runtime path, no LaunchAgent mutation, reload, model launch, Owner command publication or live trial was attempted. The configuration-first rollback remains: remove the all-or-none Product Goal argument set, reload the previously backed-up trusted plist, read back the prior Runner/router/epoch paths and active count, and preserve spec/state/ledger/checkpoints/reviews/receipts/Stop Marker. That procedure must be rehearsed on the repaired exact candidate before authorization.

## Owner decision boundary

Do not authorize or publish the prepared `APPROVE` command yet. The next engineering slice is exactly G1–G3, followed by the real Mac Runner → Linux worker → result → checkpoint → state/ledger proof, isolated deployment/read-back/rollback rehearsal, full verification and exact-candidate independent review. Only then may the package status become `READY_FOR_OWNER_AUTHORIZATION`.
