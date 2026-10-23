# B 方案操作、切換與回復

Status: implementation runbook. This document does not authorize go-live or any Product Goal.

## Current state

The Product Goal adapter is dormant. The deployed LaunchAgent and its arguments were not changed. The existing Runner follows its legacy path unless an operator explicitly supplies all three new paths:

```text
--product-goal-spec
--product-goal-state
--product-goal-ledger
```

`--product-goal-backlog` is additionally required for automatic post-closure selection and notification. It is planning input only; omitting it leaves a closed Goal safely closed and does not authorize a successor.

Supplying only some paths fails closed. Supplying all paths still does not grant authority: the adapter reads the exact GitHub Issue comments, verifies repository Owner identity, Goal version, canonical spec digest and exact permissions, then the Mac Runner durably reconciles each new command into the append-only ledger and local state. `APPROVE` records the required `APPROVED -> ACTIVE` transitions; `PAUSE`, `RESUME`, `REVOKE` and final `ACCEPT` are checked against current lifecycle prerequisites. A validly formatted early acceptance or close request is recorded as rejected, not treated as authority. `go_live_authorized=false`, a missing exact approval receipt, a paused/revoked lease, or a stale command prevents live action.

After those gates pass, a live Work Item still requires a Runner-owned `dispatch_binding`, or an action-keyed bounded `dispatch_bindings` queue, that fixes each repository-contained Linux worker order to its path, SHA-256 and event ID. The existing Writer Lock, Stop Marker, epoch/scope admission and Linux router remain on the dispatch path. Runner appends and fsyncs an exact dispatch reservation before calling the router; a restart that sees a reservation without a reconciled checkpoint consumes that checkpoint before any redispatch. Missing/running checkpoints remain pending, identity/digest mismatches fail closed, and terminal failures become bounded recovery facts.

A successful router return records only `DISPATCHED`. Product state changes only after the checkpoint contains an exact `kgnote.product-goal-worker-result.v1` envelope. Runner then records attempt completion, observed-or-unknown usage, review verdict, publication and obligation evaluation independently. A valid `CHANGES_REQUIRED` activates the already-authorized repair lane; repair completion reopens the evidence pipeline without requiring another Owner approval. Once every Work Item is terminal and every stable obligation was independently verified, Runner enters `ACCEPTANCE_REQUIRED`, queues one deduplicated notification, and still waits for an exact Owner `ACCEPT` before `CLOSED`.

An unknown or interrupted terminal-looking checkpoint is not consumed as a failed completion. Its unchanged bytes produce one idempotent digest-bound probe, the reservation stays unreconciled, and the model attempt remains unfinished until a conclusive checkpoint appears. Reconciled `WORK_WINDOW_CLOSED`, deterministic/evidence, Publisher/GitHub write-back, and Completion Gate failures each require a no-model ledger transition that clears only the exact attempt's runtime block. The next plan still passes the immutable Work Item, launch/resource policy, sealed-order binding, Writer Lock and epoch/scope admission. Bounded same-failure exhaustion leaves the affected Work Item blocked but clears the global block so independent legal work can continue.

Closure creates a digest-bound dependency receipt in the same Runner state/ledger. With the optional maintained backlog path, the next tick selects only the next dependency-satisfied Goal and queues a deduplicated GitHub-native approval request on the closing Issue. The successor remains `APPROVAL_REQUIRED`; its own exact spec refuses `APPROVE` unless all named dependency receipts are present.

Each new independent-review order also carries an explicit `program_id`, `review_scope`, and repository-relative `review_authority_paths`. Goal-specific external-review config/state paths are supported by the Publisher and Consumer handoff; do not edit the singleton configuration of an older PR to impersonate a new Goal. The Ubuntu Runner request marker does not invoke ChatGPT Work.

When the repository orchestrator owns that handoff, bind both Goal-scoped runtime paths on its first start/resume:

```bash
python3 scripts/codex_orchestrator.py --repo . resume \
  --external-review-config output/control-plane/<goal-review>/config.json \
  --external-review-state output/control-plane/<goal-review>/state.json
```

The orchestrator persists a repository-relative `external_review_binding` containing the exact `program_id`, `goal_id`, config path and state path. Later wakeups reuse it without CLI memory. A missing half, path outside the repository, Goal/program mismatch, or attempt to switch an existing binding fails closed. This binding selects evidence only; it cannot approve, activate, accept or close a Product Goal.

`--product-goal-trial` returns only a plan. It does not dispatch Codex, Claude, Publisher, GitHub writes or SSH work. Without `--product-goal-trial`, the live path can route only an exact sealed binding after every authority and admission gate above passes.

## Deterministic trial

Run from a clean implementation checkout:

```bash
.venv/bin/python scripts/run_product_goal_isolated_trial.py \
  --spec tests/fixtures/control_plane/product_goal_isolated_trial_spec.json \
  --backlog docs/control-plane/PRODUCT_GOAL_BACKLOG.json \
  --issue9-fixture tests/fixtures/control_plane/issue9_pr29_goal_history.json
```

The fixture repository is deliberately `example.invalid`. The trial now uses file-backed state, the append-only ledger, exact Owner command reconciliation, durable dispatch reservations, real checkpoint consumption, GitHub write-back recovery, a work-window deadline and next-window resume, quota backoff, `CHANGES_REQUIRED -> repair -> republish -> re-review`, Completion Gate recovery, acceptance notification, exact Owner close and backlog handoff. Every recovery release is a no-model ledger transition. The trial launches no model and performs no external write. PASS is not a real Product Goal trial or product acceptance.

## One-time go-live checklist

All items are required before adding Product Goal arguments to the LaunchAgent:

1. A canonical GitHub Issue contains the exact Owner-authored approval command for one immutable Goal spec.
2. The Goal spec includes the work window, one-model concurrency, provider fallback bounds, no-paid-API rule, exact permissions, completion conditions and human gates.
3. A separate Owner go-live decision authorizes `activate_runner`; Runner records and reads back the matching authority event.
4. The migration replay and full Runner regression suite pass on the deployment candidate.
5. A bounded real-product trial confirms no authority expansion, duplicate model dispatch, duplicate GitHub side effect or false accounting.
6. The deployed Runner SHA, Ubuntu tools, verifier, Publisher, writer lock, Stop Marker and state locations are read back again.
7. The operator explicitly updates the trusted deployment and LaunchAgent. A code merge or Codex App Goal completion is insufficient.
8. Every initially eligible Work Item has a read-back-valid sealed order binding, and a restart test proves its reservation reconciles instead of redispatching.
9. Every Claude review order and GitHub Consumer state bind the same Goal, PR, commit, fingerprint, program, round and review scope; no legacy hard-coded finding remains in a new Goal order.
10. The maintained backlog path is configured if automatic Goal-to-Goal handoff is desired; the successor spec contains the prior closure receipts and remains unapproved until a new exact Owner command is read back.

Resource capacity remains `PERCENTAGE_UNOBSERVABLE` until a trusted provider account-level percentage source is operated. The authorized Asia/Taipei work window, concurrency one, minimum launch interval, Owner-approved per-window launch ceiling, separate Owner-approved Goal-version total launch ceiling, provider quota backoff, checkpoint-first reconciliation and no paid API remain hard bounds whether or not a trusted percentage is available. Both launch counts are reconstructed from append-only attempt events; a high trusted percentage cannot enlarge them, and opening a later work window does not erase the total ceiling. An elapsed quota backoff is cleared by its own no-model ledger transition before replanning. A planned action is not authority: final reservation reads back durable state and ledger and rejects stale resource evidence, an intervening runtime block, or a changed Work Item.

## Rollback

Rollback is configuration-first and preserves evidence:

1. Remove the three `--product-goal-*` LaunchAgent arguments and reload the trusted LaunchAgent.
2. Read back that the deployed process uses the legacy Runner path and expected SHA.
3. Keep the Product Goal spec, state, ledger, checkpoints, reviews, notification receipts and Stop Marker unchanged for diagnosis.
4. If the new code itself must be reverted, deploy the previously recorded clean Runner SHA through the existing trusted deployment process. Do not reset GitHub history or Product Goal ledger bytes.

Rollback pauses new Product Goal dispatch. It does not close, revoke or accept a Product Goal. Those transitions still require an exact Owner GitHub record.

## Human attention and notification

Only final product acceptance, next-Goal approval, an unresolved product WHAT conflict, new expense/permission/irreversible risk, or exhausted strategies that require a product/resource change create a human decision notification. The notification ID is stable and its queued/sent/acknowledged states are ledger events. Each live Runner tick retries an eligible queued GitHub notice only after any durable five-minute backoff, stops after the Goal's bounded same-failure attempt limit, verifies the exact Issue-comment body and comment identity by read-back, and records the receipt before treating it as sent. An acknowledgment is accepted only from an allowed repository Owner, on the exact repository/Issue, with the exact notification/Goal identity; it has `authority_effect=NONE`.

ChatGPT Work is `UNVERIFIED` for this repository: no repository event trigger, connection permission and delivery/read-back path has been operated. GitHub native Issue comments are the implemented fallback. A notification has `authority_effect=NONE`.
