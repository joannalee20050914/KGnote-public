# Issue #47 dormant one-shot engineering direction

Direction ID: `kgnote-issue47-oneshot-wiring-2026-10-30`

Status: active Codex App execution direction for one bounded infrastructure
slice. It is not Product Goal authority and does not change product authority.

## 1. Source and authority boundary

On 2026-10-30 the product owner directed the current Codex App task to enter
Issue #47 formal Goal authorization preparation and engineering implementation,
starting with a one-shot connection that cannot automatically start a model,
then enabling scheduling and real development only in later steps.

This direction grants execution authority to change the isolated repository
worktree for `D2-ONESHOT-WIRING`. It does **not** mint the GitHub Owner marker
required by `GITHUB_OWNER_APPROVAL`, activate any Product Goal, or authorize a
scheduler, GitHub write, paid API, model launch, product canary, commit, push,
pull request, merge, or release claim.

Canonical Issue: `https://github.com/joannalee20050914/KGnote-public/issues/47`.
At the start of this slice the Issue remains open and its body still says
`BACKLOG / NOT AUTHORIZED FOR EXECUTION`. The current user direction supersedes
that wording only for this repository engineering slice; it does not silently
rewrite the Issue or authorize future Product Goal execution.

## 2. Exact authorized slice

The implementation may:

- add one read-only CLI entrypoint and its deterministic tests;
- read an exact Product Goal spec, runner state, append-only ledger, GitHub
  Issue comments, current branch, current HEAD, and an optional stop marker;
- reuse `goal_continuity`, `github_product_goal_control`, and
  `goal_runner_adapter.next_action`;
- report a stable, source-bound next-action snapshot to stdout;
- use local fixtures and read-only live GitHub reads for verification;
- update PLAN, STATUS, review-bus artifacts, and ignored verification evidence.

It must not:

- call authority reconciliation or append to a Product Goal ledger;
- create a dispatch reservation, WorkOrder, checkpoint, commit, PR, or review;
- call the Ubuntu Router, Codex entrypoint, Claude adapter, or any model CLI;
- install or enable a persistent scheduler, LaunchAgent, or systemd unit;
- reload `com.kgnote.local-autonomy-runner` or reuse its O2 runtime directory;
- modify formal O2 v4 authority, state, ledger cursor, checkpoint, 4/5 Codex
  accounting, archived successor evidence, or resource policy;
- write to GitHub or treat a read-only snapshot as a publication receipt;
- send private Pikambler content or local private paths to an external model.

## 3. One-shot contract

The CLI accepts:

- repository root;
- exact Goal spec, runner state, and ledger paths;
- either a comments fixture or a read-only live GitHub comments fetch;
- an optional stop marker;
- an optional explicit timezone-aware `--now` for deterministic replay.

Before planning it validates the repository remote identity, Goal contract,
state binding, ledger hash chain and cursor, and GitHub Owner authority record.
It rejects the protected historical Goal
`GOAL-KGNOTE-O2-READING-EXPERIENCE` regardless of its state. It hashes the
three durable inputs before and after planning and fails if any byte changes.

The only planner call is `goal_runner_adapter.next_action(..., trial=True)`.
This pure call may identify what an activated runner would do; it cannot apply
authority or reserve/dispatch work. The result maps to one user-facing status:

| Public status | Meaning in this one-shot |
|---|---|
| `STOPPED` | explicit stop, closed Goal, temporary work-window/capacity wait, or hard stop |
| `WAITING_AUTHORIZATION` | exact authority or durable go-live receipt is absent |
| `RUNNING` | a non-review next action is ready, but this CLI did not start it |
| `REVIEWING` | an independent-review action is ready, but this CLI did not start it |
| `BLOCKED` | identity, contract, decision, dependency, or other fail-closed condition |
| `READY_FOR_ACCEPTANCE` | deterministic completion reached the preserved human gate |

Every normal output states `execution_started=false`, `dispatch_performed=false`,
`reservation_created=false`, `model_launch_started=false`,
`schedule_enabled=false`, `github_write_performed=false`, and
`legacy_o2_runner_used=false`; a fail-closed input-drift result instead sets
`input_mutation_detected=true`. The snapshot binds repository branch/HEAD,
Goal identity/digest, state digest, ledger cursor/digest, authority identity,
planner result, observation time, and a deterministic snapshot digest.

With identical files, comments, repository identity, and explicit `--now`, two
invocations must produce byte-identical JSON. The CLI writes no result file;
stdout redirection, durable activation, and scheduling belong to later gates.

## 4. Required negative evidence

Tests must prove:

1. no Owner marker returns `WAITING_AUTHORIZATION`;
2. a valid marker without a ledger-bound durable activation still cannot run;
3. wrong repository, spec/state mismatch, broken ledger binding, malformed time,
   or input drift fails closed;
4. the historical O2 Goal is rejected before planning;
5. an explicit stop marker returns `STOPPED` without fetching GitHub;
6. fixed input plus fixed time is byte-identical across duplicate invocations;
7. state and ledger bytes/digests are unchanged and no router/model function is
   called;
8. public status mapping distinguishes implementation, review, blocked, and
   acceptance-ready planner results.

## 5. Later gates

`D2-SCHEDULER-ACTIVATION` requires a new explicit owner authorization naming the
single scheduler, durable runtime location, writer lock, check interval,
work-hour policy, stop/rollback, and no-model behavior. It may not reuse the old
O2 Runner merely because this one-shot passes.

`D2-LIVE-DEVELOPMENT-CANARY` separately requires an exact Product Goal Owner
approval, primary implementer, reviewer, subscription/resource ceilings,
GitHub write permissions, real product canary, privacy boundary, and acceptance
method. Issue #46 remains backlog until such authority exists. The existing
Codex-primary/Claude-reviewer path may be reused first, but that is not evidence
that Claude-primary/Codex-reviewer works.

## 6. Stop condition

After the one-shot implementation and deterministic verification are ready,
stop before enabling scheduling or starting a model. Independent infrastructure
review also requires a later model-use gate; local tests cannot self-award that
review or `release_verified`.
