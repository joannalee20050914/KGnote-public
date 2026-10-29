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

New Product Goal worktrees use the host path policy at `${HOME}/Library/Application Support/KGnote/tooling/path-policy.json` and the existing `kgnote_worktree_guard.py`. The worktree path is derived from the sealed slug as a direct child of the configured concentrated root; the guard rejects symlink escape, a root inside a non-bare Git working tree, and a mismatched Git common directory. Already-sealed Legacy work items retain their exact original paths for read/replay, but an absent Legacy Home worktree is not automatically recreated and no new formal admission may choose `${HOME}/KGnote-*`.

After those gates pass, the exact O2 proposal can derive one provisional Runner-owned WorkOrder from the immutable Work Item, current state/ledger, exact authority, current candidate, current Ubuntu runtime generation and a fixed worker profile. For a model-bearing action this provisional order is written only under the repository evidence root; it is not bound into formal state and does not increment an attempt. Other Product Goals and Legacy work continue to require their existing `dispatch_binding` or action-keyed `dispatch_bindings`; the O2 builder is deliberately not a generic shell-command generator. The existing Writer Lock, Stop Marker, epoch/scope admission and Linux router remain on the dispatch path.

Before `MODEL_ATTEMPT_STARTED` / `DISPATCH_RESERVED`, Runner asks the existing Router to discover the live immutable Ubuntu generation and route an `admission` stage through SSH, bootstrap, transient systemd unit, guard, Landlock and the deployed Worker lane. That stage uses the exact product checkout and tool/dependency probes but contains no Codex/Claude command. Its fresh receipt binds the WorkOrder SHA-256, candidate, durable state/authority projection, reviewed revision/tree, runtime manifest and installed file hashes. `reserve_dispatch()` independently validates that receipt, its two-minute lifetime and single use before its first ledger append. It also opens the referenced Router checkpoint only from the repository evidence root, verifies its file hash, event and command identity, and recomputes the canonical Worker receipt hash before comparing the exact candidate, authority, runtime, no-model and Landlock facts. A free-standing or hand-written receipt without those Router, Bootstrap and Worker evidence bytes fails closed. Runner then persists the exact binding/reservation and calls the ordinary model route. Both the Codex and Claude model lanes execute from the pinned generation and re-read the current generation, receipt, lock and installed file hashes immediately before any provider process; pointer or byte drift fails closed. A restart that sees a reservation without a reconciled checkpoint consumes that checkpoint before any redispatch. Missing/running checkpoints remain pending, identity/digest mismatches fail closed, and terminal failures become bounded recovery facts.

Exact independent review uses the repository's two-phase candidate seal. The tracked `.ai/REVIEW_REQUEST.md` and `CODEX_STATUS.md` inside a candidate commit are historical checkpoints because a commit cannot contain its own SHA. After the candidate commit, deterministic verification and `review-request` produce the fingerprint-excluded live seal. The production review handoff must copy that live request, live status and exact verifier receipt into an ignored evidence directory in the clean review checkout, record each copy's SHA-256 in the WorkOrder, and name those copies in reviewer authority/scope. The reviewer must compare them with the recomputed checkout HEAD/tree/fingerprint and the canonical GitHub marker; the tracked historical copies alone are insufficient review authority. These copies do not change candidate bytes or make a failed/stale seal valid.

### PAUSED deployment admission-only acceptance

Deployment acceptance has its own `DEPLOYMENT_ACCEPTANCE` identity, challenge and evidence directory. Its fixed fields are `authority_lease=PAUSED`, `go_live_authorized=false` and `formal_dispatch_authorized=false`; Product Goal identity/context and WorkOrder SHA are null. It therefore cannot act as `APPROVE`, `RESUME`, a product reservation or launch accounting.

After installing an exact reviewed generation, create and route the request against the existing clean Product Goal checkout. `ADMISSION_CHECKOUT_*` identifies that checkout; the separately discovered runtime identity already binds the deployed repair HEAD/tree, manifest and file hashes. The example paths are evidence paths, not formal Product Goal state/checkpoint paths:

```bash
mkdir -p output/control-plane/runtime-admission-acceptance

python3 scripts/linux_worker_router.py --discover-runtime \
  > output/control-plane/runtime-admission-acceptance/runtime-identity.json

python3 scripts/product_goal_runtime_admission.py --make-deployment-request \
  --runtime-identity output/control-plane/runtime-admission-acceptance/runtime-identity.json \
  --challenge "${ADMISSION_CHALLENGE}" \
  --candidate-commit "${ADMISSION_CHECKOUT_HEAD}" \
  --candidate-tree "${ADMISSION_CHECKOUT_TREE}" \
  --candidate-fingerprint "${ADMISSION_CHECKOUT_FINGERPRINT}" \
  --candidate-branch "${ADMISSION_CHECKOUT_BRANCH}" \
  > output/control-plane/runtime-admission-acceptance/request.json

python3 scripts/linux_worker_router.py \
  --deployment-admission output/control-plane/runtime-admission-acceptance/request.json \
  --admission-receipt output/control-plane/runtime-admission-acceptance/receipt.json
```

`ADMISSION_CHALLENGE` must be a newly generated 64-character lowercase hexadecimal value. Read back the request, receipt, Router checkpoint and Worker receipt digests; require `status=PASS`, all five isolation fields `PASS`, `model_process_started=false`, `model_launches=0` and `model_processes=[]`. Snapshot the formal Product Goal state, ledger and formal checkpoint-set hashes before and after both positive and negative cases. A positive result proves only the deployed no-model admission path. It does not verify a real product-model development result and does not authorize `RESUME`.

A successful router return records only `DISPATCHED`. Product state changes only after the checkpoint contains an exact `kgnote.product-goal-worker-result.v1` envelope. Runner then records attempt completion, observed-or-unknown usage, review verdict, publication and obligation evaluation independently. A valid `CHANGES_REQUIRED` activates the already-authorized repair lane; repair completion reopens the evidence pipeline without requiring another Owner approval. Once every Work Item is terminal and every stable obligation was independently verified, Runner enters `ACCEPTANCE_REQUIRED`, queues one deduplicated notification, and still waits for an exact Owner `ACCEPT` before `CLOSED`.

For the first O2 publication only, deployment seeds fixed branch `codex/o2-reading-experience` at the exact clean infrastructure commit. Ubuntu later pushes the first product successor through its credential-isolated `push` stage and reads back the public branch. If no PR is bound, the authenticated Mac Runner creates one Draft PR, verifies number/HEAD/branch/open/draft state, appends `CANDIDATE_PULL_REQUEST_BOUND`, and only then creates a Claude review order. This idempotent transition is not a human-filled dispatch binding and cannot mark a candidate reviewed or accepted.

An unknown or interrupted terminal-looking checkpoint is not consumed as a failed completion. Its unchanged bytes produce one idempotent digest-bound probe, the reservation stays unreconciled, and the model attempt remains unfinished until a conclusive checkpoint appears. Reconciled `WORK_WINDOW_CLOSED`, deterministic/evidence, Publisher/GitHub write-back, and Completion Gate failures each require a no-model ledger transition that clears only the exact attempt's runtime block. The next plan still passes the immutable Work Item, launch/resource policy, sealed-order binding, Writer Lock and epoch/scope admission. Bounded same-failure exhaustion leaves the affected Work Item blocked but clears the global block so independent legal work can continue.

Closure creates a digest-bound dependency receipt in the same Runner state/ledger. With the optional maintained backlog path, the next tick selects only the next dependency-satisfied Goal and queues a deduplicated GitHub-native approval request on the closing Issue. The successor remains `APPROVAL_REQUIRED`; its own exact spec refuses `APPROVE` unless all named dependency receipts are present.

Each new independent-review order also carries an explicit `program_id`, descriptive `review_scope`, and repository-relative `review_authority_paths`. The goal-scoped external-review config binds exactly one `product_contract_review_scope` to that full descriptive scope; Ingestion must not require the order to masquerade as a generic scope token, and any other scope remains `CODE_REVIEW_ONLY`. Adapter completion is converted to `REVIEW_SUBMITTED` only through the exact checkpoint/work-order identity bridge. Goal-specific external-review config/state paths are supported by the Publisher and Consumer handoff; do not edit the singleton configuration of an older PR to impersonate a new Goal. The Ubuntu Runner request marker does not invoke ChatGPT Work.

When the repository orchestrator owns that handoff, bind both Goal-scoped runtime paths on its first start/resume:

```bash
python3 scripts/codex_orchestrator.py --repo . resume \
  --external-review-config output/control-plane/<goal-review>/config.json \
  --external-review-state output/control-plane/<goal-review>/state.json
```

The orchestrator persists a repository-relative `external_review_binding` containing the exact `program_id`, `goal_id`, config path and state path. Later wakeups reuse it without CLI memory. A missing half, path outside the repository, Goal/program mismatch, or attempt to switch an existing binding fails closed. This binding selects evidence only; it cannot approve, activate, accept or close a Product Goal.

`--product-goal-trial` returns only a plan. It does not dispatch Codex, Claude, Publisher, GitHub writes or SSH work. Without `--product-goal-trial`, the live path can route only an exact sealed binding after every authority and admission gate above passes.

## Bounded real-product trial versus full policy go-live

An exact Product Goal approval may authorize one bounded real-product trial without authorizing the standing B-scheme policy. The approval must bind one immutable `goal_id`, version, spec digest, operation list, work window and provider launch ceilings. In that Goal's Runner state, `go_live_authorized=true` means only that this exact scoped approval permits live dispatch; repository-level `B-SCHEME-GO-LIVE` remains `NOT_AUTHORIZED`, successor Goals inherit no permission, and the maintained backlog cannot start another Goal without a fresh Owner approval.

Full B-scheme go-live is a later, independent Owner decision based on the completed trial's authority, duplicate-dispatch, accounting, review, rollback and human-acceptance evidence. A successful trial does not automatically make the policy live. This two-stage interpretation avoids both unsafe bypass (`go_live_authorized=false` is never manually flipped) and a circular requirement that full standing delegation exist before its first bounded trial.

### O2 v3 reauthorization boundary

The immutable reauthorization candidate is Goal ID
`GOAL-KGNOTE-O2-READING-EXPERIENCE`, version
`2026-10-29.3-bounded-trial-reauthorization-proposal`, canonical digest
`83ddf1cf95c27ec2646e143d4ade88eaedec8f38d5149d3621be090ff6c41e3f`.
It preserves the prior product direction, Work Items, obligations, completion
conditions and safety policy. Its five observation work dates are 2026-11-02
through 2026-11-06 in `Asia/Taipei`; its hard stop is 2026-11-13 18:00 in
the same timezone.

The prior version's three Codex reservations remain historical charges against
the candidate ceiling of five, including the third reservation whose provider
event count is zero. The prior two actual Codex provider processes remain
actual process history. Therefore, before any v3 dispatch, Codex has two
candidate charges remaining and Claude has eight. Neither a new version nor a
new state file resets these counts. The immutable carryover evidence is
`docs/control-plane/O2_V3_CARRYOVER_EVIDENCE_20261029.json`; Runner validates
its file digest, old spec/state/ledger identities, cursor, reservation totals
and candidate checkout before it reads mutable v3 runtime state.

Activation is timely only when the exact Owner `APPROVE` record and all named
activation dependency receipts have timestamps earlier than 2026-11-02 09:00
`Asia/Taipei`. A receipt for carryover sealing, exact Mac/Ubuntu deployment or
no-model acceptance that is missing or verified at/after that instant makes
the immutable version `TRIAL_ACTIVATION_MISSED`. The Goal then remains
`APPROVAL_REQUIRED` / `PAUSED`; the later hard stop cannot revive it. Recovery
requires a later immutable Goal version with five newly named observation work
dates and a corresponding tenth-workday hard stop.

Every Codex or Claude model-bearing order for this Goal ID must match the exact
v3 version and digest and must obtain a fresh Ubuntu pre-reservation receipt.
The same Goal ID with an old, unknown or mistyped version/digest is not legacy
work and cannot use a receipt-free dispatch path. The receipt must also bind
the exact authority projection, WorkOrder SHA-256, candidate checkout and
current immutable runtime generation. Deployment admission-only acceptance
remains no-model evidence and cannot create or substitute for Owner approval,
a reservation, an attempt, a product checkpoint or product acceptance.

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
8. The deployed O2 dynamic builder creates a read-back-valid sealed order for every eligible A/B lane, while non-O2 work retains its existing binding contract; a restart test proves the exact reservation/result reconciles instead of redispatching.
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
