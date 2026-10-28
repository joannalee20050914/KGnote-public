# O2 runtime context recovery direction — 2026-10-28

Status: current Product Owner execution direction for one bounded Control Plane repair.
Product direction: `kgnote-obsidian-first-2026-09-22`.
Immutable Product Goal: `GOAL-KGNOTE-O2-READING-EXPERIENCE` / `2026-10-23.2-s0-s2-proposal`.

## 1. Observed production facts

- PR #35 was merged and deployed as `9271bf8645858eed49effa8eca3df8ea491bfc17`.
- The formal Mac Runner consumed GitHub PAUSE comment `6458880366`.
- Formal O2 state is `lifecycle=BLOCKED`, `authority_lease=PAUSED`, and `go_live_authorized=false` at ledger sequence 15.
- Work Item A has exactly two launch reservations/attempts. There is no third reservation, attempt, or Ubuntu checkpoint.
- The two Ubuntu Codex executions were real, but their raw stdout/stderr show repository-control and development-environment failures rather than an HTTP 429 or provider subscription/quota response.
- The former `RATE_LIMITED` projection was produced by scanning arbitrary transcript prose for words such as `quota` or `429`; it is not provider evidence and supplied no provider recovery time.
- Formal deployment admission after the first reviewed candidate proved that the Ubuntu host lacks the distro `python3-venv` package and that Python 3.12 requires the separately pinned `typing-extensions` dependency for `referencing==0.37.0`. The candidate must therefore use the already pinned Ubuntu `uv` bootstrap and close that exact lock dependency before deployment; bypassing `pip check` is forbidden.

## 2. Authorized bounded repair

The repair must solve these three dependent issues as one candidate:

1. **Authority and work context.** A dispatched Ubuntu Codex process must receive a sealed, Runner-verified runtime context containing the exact O2 Goal identity, consumed Owner authority, lifecycle/lease/go-live status, current work-item state, candidate identity, and ledger/event cursor. It must not infer execution authority from stale repository `PLAN.md` or `CODEX_STATUS.md`.
2. **Development environment.** Before Codex starts, the Ubuntu checkout must prove the expected repository, branch/ref, exact HEAD/tree, clean status, Python environment, Node/npm, `gh`, and required repository development tools. Every distribution pinned by `requirements-runtime.lock` must match the active repository venv, and an unexpected non-bootstrap distribution is a failure. An incomplete or drifted environment must fail before the provider/model process is invoked; conservative reservation accounting remains preserved and is never reset.
3. **Failure classification and recovery.** Classification must be based on structured provider/error evidence, not incidental documentation or transcript prose. The two preserved failures must receive append-only correction evidence bound to their immutable raw-log and checkpoint hashes. Correction admission must read back a canonical GitHub/Consumer PASS for the exact Goal, PR, review round, commit, fingerprint and tree, and must prove that the deployed Runner tree is the reviewed tree. Existing ledger entries and attempt/launch accounting must not be overwritten or reset.

The candidate must pass repository verification and the existing independent Ubuntu Claude review before normal PR integration and formal Runner deployment. Deployment must be read back from the Mac LaunchAgent and the formal O2 state/ledger.

## 3. Explicit prohibitions and gates

- Do not publish or synthesize `RESUME`.
- Do not start another O2 model dispatch, reservation, attempt, or Ubuntu checkpoint during repair or deployment.
- Preserve the current PAUSE and all prior state, ledger, checkpoints, raw logs, attempt counters, launch counters, dates, resource limits, Work Item DAG, and Product Goal WHAT.
- Do not hand-edit or replace the formal ledger. Historical corrections must be append-only, integrity-bound events produced by trusted code after deployment.
- Do not treat an independent review PASS as product approval, learning acceptance, physical-device evidence, or `release_verified`.
- Do not force-push, write directly to `main`, bypass GitHub rules, reuse a stale review, or deploy bytes different from the reviewed exact candidate.

## 4. Completion condition

Completion requires all of the following:

- the exact repair candidate has deterministic verification evidence and an independent Ubuntu Claude PASS;
- the normal PR is merged and the same commit/tree is deployed to the formal Runner;
- the LaunchAgent interpreter, deployment path, process, and runtime receipt are read back;
- two append-only classification-correction events are present and bound to the original immutable evidence;
- formal state remains `BLOCKED` / `PAUSED` / `go_live_authorized=false`;
- Work Item A still has exactly two attempts and no third reservation, attempt, or checkpoint;
- the Runner is waiting for authority rather than dispatching work.

This direction authorizes the repository, review, PR-integration, deployment, and append-only reconciliation operations necessary for that bounded result. It does not authorize `RESUME` or additional product-model work.
