# B 方案操作、切換與回復

Status: implementation runbook. This document does not authorize go-live or any Product Goal.

## Current state

The Product Goal adapter is dormant. The deployed LaunchAgent and its arguments were not changed. The existing Runner follows its legacy path unless an operator explicitly supplies all three new paths:

```text
--product-goal-spec
--product-goal-state
--product-goal-ledger
```

Supplying only some paths fails closed. Supplying all paths still does not grant authority: the adapter reads the exact GitHub Issue comments, verifies repository Owner identity, Goal version, canonical spec digest and exact permissions, then requires the local state authority record and a matching append-only `GOAL_AUTHORITY_VERIFIED` go-live receipt. `go_live_authorized=false`, a missing receipt, a paused/revoked lease, or a stale command prevents live action.

After those gates pass, a live Work Item still requires a Runner-owned `dispatch_binding` that fixes a repository-contained Linux worker order to its path, SHA-256 and event ID. The existing Writer Lock, Stop Marker, epoch/scope admission and Linux router remain on the dispatch path. Runner appends and fsyncs an exact dispatch reservation before calling the router; a restart that sees a reservation without a reconciled checkpoint returns `RECONCILE_CHECKPOINT` and cannot blindly dispatch it again. A successful router return records only `DISPATCHED`; it does not invent a completed model result, valid review or resolved product obligation.

`--product-goal-trial` returns only a plan. It does not dispatch Codex, Claude, Publisher, GitHub writes or SSH work. Without `--product-goal-trial`, the live path can route only an exact sealed binding after every authority and admission gate above passes.

## Deterministic trial

Run from a clean implementation checkout:

```bash
.venv/bin/python scripts/run_product_goal_isolated_trial.py \
  --spec tests/fixtures/control_plane/product_goal_isolated_trial_spec.json \
  --backlog docs/control-plane/PRODUCT_GOAL_BACKLOG.json \
  --issue9-fixture tests/fixtures/control_plane/issue9_pr29_goal_history.json
```

The fixture repository is deliberately `example.invalid`; PASS means only that paths A/B and the migration reducer behaved as specified. It is not a real Product Goal trial or product acceptance.

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

Resource capacity remains `PERCENTAGE_UNOBSERVABLE` until a trusted provider account-level percentage source is operated. Until then, the fallback is the authorized Asia/Taipei work window, concurrency one, minimum launch interval, per-window launches, provider quota backoff, checkpoint-first reconciliation and no paid API.

## Rollback

Rollback is configuration-first and preserves evidence:

1. Remove the three `--product-goal-*` LaunchAgent arguments and reload the trusted LaunchAgent.
2. Read back that the deployed process uses the legacy Runner path and expected SHA.
3. Keep the Product Goal spec, state, ledger, checkpoints, reviews, notification receipts and Stop Marker unchanged for diagnosis.
4. If the new code itself must be reverted, deploy the previously recorded clean Runner SHA through the existing trusted deployment process. Do not reset GitHub history or Product Goal ledger bytes.

Rollback pauses new Product Goal dispatch. It does not close, revoke or accept a Product Goal. Those transitions still require an exact Owner GitHub record.

## Human attention and notification

Only final product acceptance, next-Goal approval, an unresolved product WHAT conflict, new expense/permission/irreversible risk, or exhausted strategies that require a product/resource change create a human decision notification. The notification ID is stable and its queued/sent/acknowledged states are ledger events. An acknowledgment is accepted only from an allowed repository Owner, on the exact repository/Issue, with the exact notification/Goal identity; it has `authority_effect=NONE`.

ChatGPT Work is `UNVERIFIED` for this repository: no repository event trigger, connection permission and delivery/read-back path has been operated. GitHub native Issue/PR notifications are the fallback. A notification has `authority_effect=NONE`.
