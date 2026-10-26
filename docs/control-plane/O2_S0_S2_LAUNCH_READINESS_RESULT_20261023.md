# O2 S0–S2 啟動準備結果

Status: `READY_FOR_EXACT_CANDIDATE_REVIEW`

Observed at: 2026-10-23 Asia/Taipei. This is an engineering-readiness result, not Product Owner authority, independent review PASS, deployment approval, or live-product evidence.

## Outcome

S0 and the G1–G3 S1 runtime repairs are implemented. The real code path now derives and seals one O2 order, passes exact O2 identity and epoch admission, runs a fixed Codex/Publisher/Claude lane, persists a canonical result before route completion, reconciles checkpoint/state/ledger, and selects the next eligible Work Item. The integrated proof uses the real Runner/adapter/router/checkpoint code with a controlled no-model transport substitute; no formal O2 model work was launched. S2 deployment and configuration-first rollback rehearsals passed in isolated temporary locations. Exact-candidate full verification and independent Ubuntu Claude review remain the next milestone, so this intermediate status is not yet Owner authorization.

| Claim | Result | Evidence boundary |
| --- | --- | --- |
| IMPLEMENTED | yes for G1–G3 | O2-only dynamic builder, shared result adapter, fixed lane entrypoint and exact Linux identity/admission |
| DETERMINISTIC_VERIFIED | pending final candidate verifier | targeted and full control-plane regression pass before candidate sealing |
| INTEGRATION_VERIFIED | yes for engineering data flow | actual code path plus controlled no-model transport; not a provider product result |
| INDEPENDENT_REVIEWED | pending for this candidate | PR #32 `de5c8c0` PASS remains separate and unchanged |
| DEPLOYMENT_PREPARED | yes, isolated | Ubuntu compile/import and Mac plist add/read-back/restore rehearsal; formal deployment untouched |
| LIVE_PRODUCT_TRIAL_NOT_STARTED | yes | existing Legacy LaunchAgent runs without Product Goal arguments; O2 model launches remain zero |

## S0 result

- Work Item A is `WI-O2-A-IMPLEMENT` through A verify/publish/review/repair and covers the Obsidian reading entry, source-bounded prose, shared identity read-back and A exact-candidate evidence.
- Work Item B is `WI-O2-B-IMPLEMENT` through B verify/publish/review/repair and covers context-local source-sentence notes plus B exact-candidate evidence. B depends on terminal A review and repair states; A cannot close B or O2.
- Codex and Ubuntu Claude each have `max_launches_per_window=3`, `max_total_launches=8`, 300-second minimum launch interval and 3600-second quota backoff. Global concurrency is one; paid API is forbidden; the Goal total never resets by day or session.
- The eight-launch proposal covers two A/B initial launches, four bounded repair/re-review launches and two invalid-start/envelope or quota contingencies. The historical basis is three Codex repair attempts, four valid Claude verdicts and one Claude 429 attempt in Issue #9 history; legacy counters are preserved rather than inherited or reset.
- Proposed observation dates are 2026-10-28, 10-29, 10-30, 11-02 and 11-03. Proposed activation is 2026-10-28 09:00, observation ends 2026-11-03 18:00, and the tenth-Goal-workday hard stop is 2026-11-10 18:00. A late activation requires a new immutable version and new dates.
- Gates are: successor start within 600 seconds, two cross-window resumptions, one safe Runner restart, zero ordinary human relay and no more than 50 engineering-supervision minutes.

Canonical JSON digest: `82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604`. File SHA-256: `8434386012c09546b5c3dd17a86c78ef05248d5391699398efc8beea526e7fd9`.

## S1 G1–G3 closure

### G1 — trusted dynamic order planner/binder

`ensure_bound_order` is enabled only for the exact O2 goal/version/spec digest. It derives the lane from the immutable Work Item, binds current authority and candidate identity, selects a fixed command template, atomically writes context/order, seals the digest into state and then reuses the same attempt binding on restart. It rejects a stale action, replaced bytes, out-of-root path, Stop Marker, unmet dependency and exhausted provider total. Non-O2 and Legacy paths retain the prior sealed-binding behavior.

### G2 — durable real worker-result bridge

`product_goal_worker_lane.py` uses fixed Codex, verifier, credential-isolated Git push/read-back and Claude adapter profiles. `product_goal_worker_result.py` preserves raw stdout/stderr, validates attempt/order/candidate, atomically saves `kgnote.product-goal-worker-result.v1`, and only then exposes the route evidence marker. Exit zero without evidence is failure; no Claude verdict cannot pass; 429/quota and interruption remain classified; usage stays `UNKNOWN` unless reliable input/output totals exist. A saved exact result is replayed without another worker launch. Ubuntu reads the public remote branch/PR through GitHub REST because it has no `gh`; the authenticated Mac Runner idempotently creates and binds the first Draft PR after branch publication and before review.

### G3 — exact O2 Linux identity with Legacy compatibility

`product_goal_worker_identity.py` accepts only the exact O2 goal/version/digest/repository/Issue and the enumerated A/B IMPLEMENT, VERIFY, PUBLISH, REVIEW and REPAIR lane mapping. It binds event, branch, one worktree slug, authority status/action/digest and path. Cross-goal, wrong provider/stage/digest/event, unauthorized Work Item and path escape fail. The previous `D2-Txx` validator remains a distinct compatibility branch and its regression tests pass.

## S2 deployment/read-back/rollback rehearsal

- PR #32 remains Draft/open at exact HEAD `de5c8c01c86ffc87896dca1337817892bfb5eff6`, base `7bb0ffb4be6d5eb19398f249f45fa8e32a083131`; its earlier exact independent PASS is unchanged and does not review this proposal.
- Draft PR #33 remains stacked on PR #32. Its remote HEAD remains the pre-repair `978dffe` until this new candidate is committed/pushed and sealed for review.
- Deployed Runner: `7bb0ffb4be6d5eb19398f249f45fa8e32a083131`.
- Deployed router: `7dbaeb6872cea07f5f8eb6ebdff8b29359cd2d66`.
- Deployed epoch/scope admission: `b3293908847ac8296c37402ab1a3876e50b2b38a`.
- LaunchAgent read-back at rehearsal time: `com.kgnote.local-autonomy-runner`, `state=running`, `active count=1`, pointing at Legacy Runner commit `7bb0ffb`; it has no Product Goal arguments. This is not O2 activation.
- Mac tools: Python `3.13.7`, Git `2.39.3`, Node `24.22.1`, npm `11.19.1`, gh `2.83.2`. Ubuntu tools: Python `3.12.3`, Git `2.43.0`, Claude Code `2.1.302`, fixed Node `24.12.0`, Codex CLI `0.146.0`, pinned agent-loop executable present; Ubuntu `gh` is absent and no longer required by the O2 publisher.
- Candidate runtime scripts were copied only to `/tmp/kgnote-o2-s2.*` on Ubuntu, compiled and imported against the existing runtime, then removed. No formal runtime path changed.
- A copy of the current plist received all four spec/state/ledger/backlog arguments, passed `plutil`, and was copied to a temporary active file. Restoring the baseline reproduced SHA-256 `0866aa272573d0e5cb0ce0a459f11f6fb75213d1b7b50fe4ea42872ca1f2d703`, equal to the untouched formal plist.
- The integration test traverses decision → dynamic order → existing admission → actual router implementation with a controlled SSH substitute → canonical result → checkpoint → state/ledger → next verify order. Separate tests prove first-branch publication and Mac Draft-PR binding without a real GitHub write. No test calls a model or claims live-provider evidence.

No LaunchAgent mutation/reload, model launch, Owner command publication or live trial was attempted. The formal deployment set must include `product_goal_worker_identity.py`, `product_goal_worker_lane.py`, `product_goal_worker_result.py`, `codex_control.py`, the modified Runner/adapter/router/bootstrap/admission files and matching schemas. Configuration-first rollback removes the all-or-none Product Goal argument set, reloads the backed-up trusted plist, reads back the prior Runner/router/epoch paths and preserves spec/state/ledger/checkpoints/reviews/receipts/Stop Marker.

## Owner decision boundary

Do not authorize or publish the prepared `APPROVE` command yet. The next step is to seal/push the repaired PR #33 candidate, run full exact-candidate verification and obtain independent Ubuntu Claude PASS. Only that exact PASS may change the package to `READY_FOR_OWNER_AUTHORIZATION`.
