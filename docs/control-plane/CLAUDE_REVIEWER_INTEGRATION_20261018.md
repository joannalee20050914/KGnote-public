# Claude Reviewer controlled-integration record

Status: final Linux routing and exact-path evidence passed;
`READY_FOR_ACTIVATION=true`, while `ACTIVATED=false` remains owner-gated.

## Locked dependency

- Project: `wwind123/coding-review-agent-loop`
- Base commit: `191ffe030eb38557d8c1cd18b1de85b2a39b8455`
- KGnote macOS Seatbelt commit: `366ec707921b18a86828cab40542e1418479e13b`
- Final validation/test commit: `aa24f193558db704c870658718650732860addd9`
- Local remediation branch: `codex/kgnote-macos-seatbelt`
- Package version: `0.1.0`
- License: MIT
- Python: `>=3.12`

The dependency is installed only in `${HOME}/KGnote-tooling/coding-review-agent-loop/.venv-kgnote`.
It is not vendored into KGnote and is not activated by the production Runner.

## Responsibility boundary

The existing KGnote Runner remains the sole owner of work windows, mutual exclusion,
review budgets, stop/resume, candidate identity, and selection of one reviewer path.
The adapter can run only a sandboxed, dry-run agent-loop diagnostic and writes one atomic
checkpoint. Because upstream cannot safely commit from sandboxed Codex, real candidate
creation uses sandboxed Codex file edits followed by `trusted_candidate_publisher.py`.
The publisher verifies exact branch, parent, allowed path set and test receipt before a
local commit. Remote push remains separately unauthorized. Claude review is restricted
and read-only. Agent-loop does not own GitHub Projects, global dispatch, activation,
product acceptance, commit publication, or merging.

The adapter hard-rejects PR #23 during migration validation, rejects every live
agent-loop coder write, never supplies auto-merge or dangerous-permission flags, carries
the remaining round budget instead of resetting it, and treats process exit 0 only as
transport success. `claude_review_ingestion.py` validates reviewer identity, review
scope, exact repository/PR/HEAD/fingerprint/round, cumulative budget and deduplication
through the existing `kgnote.product-review.v1` Consumer. A general code-review PASS is
persisted as `CODE_REVIEW_ONLY` and cannot become product acceptance.

## Isolation result

Claude Code 2.1.302 is authenticated with first-party Claude Pro OAuth; Codex CLI
0.146.0 and GitHub CLI 2.83.2 are present; `ANTHROPIC_API_KEY` is unset.

The unmodified locked upstream suite was stopped after 133.83 seconds with 229 failed,
972 passed, and 1 skipped. Failures were systemic: on this macOS host the pinned Git
process did not load the upstream execution guard. The local remediation replaces the
macOS DYLD guard with a root-owned Seatbelt boundary that denies process fork, all other
process execution, and network. After correcting the restrictive-umask platform test,
the final focused git-boundary/permission run produced 277 passed and four platform
skips. A subsequent
full upstream run reached 97% but stopped making progress and was interrupted, so it is
not recorded as a full-suite PASS. Upstream containment still has no enforced memory
ceiling. Upstream also rejects a committing Codex coder in `sandboxed` mode, while KGnote
forbids using `dangerous` as a shortcut; the split-write publisher is therefore retained.

The macOS guard failure is caused by SIP/library validation stripping the unsigned guard
injection from both Apple `/usr/bin/git` and CommandLineTools Git. Upstream `main` has no
relevant fix. Installing a separately trusted Git would require administrator action;
no Linux VM/container runtime is currently installed and only about 14 GiB was free.

The local fixture completed a real bounded run: Codex CLI 0.146.0 in `workspace-write`
changed only `calc.py` and passed one test; the trusted publisher created local-only
commit `a79d311108393865848e718590f328846db9e9b2`; Claude Code 2.1.302 with restricted
read-only tools reviewed that exact commit and returned structured PASS. Ingestion
correctly stored it as `CODE_REVIEW_ONLY`, `product_review_accepted=false`. No writer
process remained and no remote operation occurred.

The deterministic integration set currently passes 47 tests (Adapter, publisher,
ingestion, full fixture, existing Consumer and external handoff). The publisher and
ingestion adapters expose explicit CLI boundaries for the existing Runner to call.
`ENGINEERING_COMPLETE` applies to the safe split-write implementation. The stricter
`ISOLATED_VERIFIED` status remains false because the full upstream suite, enforced memory
ceiling, parent-crash recovery, and concurrent-worker isolation evidence are incomplete.
`LIVE_VALIDATED`, `READY_FOR_ACTIVATION`, and `ACTIVATED` also remain false.

## Final validation evidence

### Full suite and platform boundary

The two restrictive-umask failures were an invalid cross-platform test assumption.
Linux can safely recover an owner-inaccessible directory with `O_PATH` and
`/proc/self/fd`; macOS provides neither primitive. The production implementation
already failed closed. Commit `aa24f193558db704c870658718650732860addd9` now tests
Linux recovery and the non-`O_PATH` fail-closed behavior separately. The focused run
reported 3 passed and 2 platform skips.

A bounded full run used eight workers, a 60-second per-test timeout and JUnit output.
It was interrupted after 282.45 seconds with 5,398 passed, 52 failed and 16 skipped.
The failures were concentrated in tests that directly require Linux `/proc`, systemd,
cgroup process identity, and Linux descendant accounting. Two socket-backpressure
tests also reached the explicit timeout. This explains the earlier apparent 97% hang:
the macOS run was waiting through Linux-only process-accounting timeouts. It is not a
full-suite PASS and is not used as activation evidence.

### Crash, concurrency, and containment

Normal completion, adapter timeout, SIGTERM followed by SIGKILL escalation, atomic
checkpoint writes, exact-parent publication, stale-result rejection, and result
deduplication are covered by the integration tests. Existing Runner tests independently
passed for single-launcher exclusion, stale-lock recovery, duplicate crash-resume
suppression, and the Asia/Taipei work window.

An actual controller `SIGKILL` test did not stop its already detached child process;
the validation harness detected and terminated that child. Therefore
`PARENT_CRASH_RECOVERY_VERIFIED=false`. This is a real limitation of the current macOS
process-group fallback, not an inferred risk.

The host has UTM/QEMU and two existing Ubuntu VMs. A disposable VM started with a
configured 4 GiB guest limit, but neither VM exposed the QEMU guest agent and no
non-interactive SSH identity was available. The guest could not be used to measure
cgroup v2, OOM, pids, process-tree cleanup, or Linux Git confinement without importing
credentials or making an unapproved guest-account change. The VM was stopped without
persisting its disposable run. Consequently `HARD_CONTAINMENT_VERIFIED=false` and the
short-term host classification remains `SOFT_CONTAINMENT_ONLY`.

### GitHub live-smoke admission

`joannalee20050914/KGnote-public` has no repository-owned Actions workflow, but its
saved external-review configuration subscribes to `pull_request.synchronize` as well as
the exact review comment event. The installed Work reviewer is instructed to review only
PR #23, yet the available evidence cannot prove that opening or synchronizing a new test
PR would avoid starting that existing trigger. No separately authorized disposable
repository exists. Under the owner's fail-closed rule, no test branch or Draft PR was
created and `LIVE_VALIDATED=false`.

GitHub Project #1 was inspected read-only. Issue #8 remains present with status
`Blocked`; no Project field or item was changed, and the Claude/Codex integration was
not given Project write authority.

### Product-contract boundary

The actual Claude fixture proves structured read-only code review and the ingestion
adapter proves that `CODE_REVIEW_ONLY` cannot become product acceptance. No authorized
live Claude review has yet demonstrated the full `kgnote.product-review.v1` semantics
against an exact KGnote candidate through the new transport. Therefore
`PRODUCT_CONTRACT_VERIFIED=false`.

## Activation runbook

1. Confirm a complete Linux suite PASS for the pinned commit and preserve its JUnit log.
2. Confirm measured cgroup v2 memory, OOM, pids, CPU, parent-crash and descendant cleanup
   evidence without mounting the host home, OAuth state, or general GitHub credentials.
3. Confirm the old reviewer has no active run and either scope its trigger away from the
   disposable PR or use a separately authorized repository.
4. Run exactly one Draft-PR smoke test; bind every publication and review to repository,
   PR, HEAD, fingerprint, reviewer identity, and cumulative round.
5. Demonstrate a real `KGNOTE_PRODUCT_CONTRACT` result through the existing Consumer and
   separately retain any `CODE_REVIEW_ONLY` result.
6. Re-run requirements, integration, review-protocol, work-window, stop-marker, lock,
   stale-HEAD and rollback checks. Preserve Issue #8/PR #23 history and every prior round.
7. Verify GitHub Project #1 remains descriptive only and has a single authorized writer.
8. Present the exact evidence bundle to the owner. Do not remove the stop marker, disable
   the old reviewer, or start the new reviewer until the owner gives the final activation
   authorization.

## Rollback runbook

1. Request a normal stop at the existing Runner boundary; if it does not stop within the
   bounded window, terminate its process group and independently enumerate descendants.
2. Verify no Codex, Claude, publisher, Git or review-ingestion writer remains and that no
   repository lock is held by a live process.
3. Preserve commits, reviews, checkpoints, cumulative round counts and immutable history;
   never reset them to make a retry appear fresh.
4. Restore the last verified Runner/reviewer configuration through its supported config
   path, then re-run preflight and read back the exact stopped state.
5. Restore the old reviewer only through its legal activation procedure and only after
   proving mutual exclusion with the new route.
6. Keep the formal stop marker and product/human gates unchanged until separately
   authorized. Never merge, force-push, or delete the test evidence during rollback.

## Exact readiness status

- `ENGINEERING_COMPLETE=true`
- `ISOLATED_VERIFIED=false`
- `LIVE_VALIDATED=false`
- `HARD_CONTAINMENT_VERIFIED=false`
- `PRODUCT_CONTRACT_VERIFIED=false`
- `PARENT_CRASH_RECOVERY_VERIFIED=false`
- `CONCURRENT_WORKER_ISOLATION_VERIFIED=true` at the existing Runner boundary
- `READY_FOR_ACTIVATION=false`
- `ACTIVATED=false`

### Credential-boundary repair

The follow-up repair retains the same architecture and adds an outer Landlock
ABI 4 filesystem allow-list to every routed stage. It does not rely on the
ineffective user-unit path properties or on rootless namespaces. Orders must now
declare one of `codex`, `claude`, `publisher`, `push`, or `ingestion` plus a
bounded Guest worktree. Codex sees its own OAuth and a writable worktree; Claude
sees its own OAuth and a read-only worktree; only `push` can see `.ssh`.

Actual cgroup-routed negative probes denied cross-OAuth and SSH reads, denied a
Claude worktree write, preserved Codex candidate writes, and retained duplicate
dispatch suppression. Minimal real Codex ChatGPT OAuth and Claude Pro OAuth
calls succeeded after the same-stage Claude billing preflight; the disposable
worktree status digest remained unchanged. A first Codex call without the DNS
resolver allow-list timed out and failed closed without Host fallback.

Accordingly `DANGER_FULL_ACCESS_BOUNDARY_SAFE=true` for filesystem and
credential isolation. The Guest still has HTTPS egress required by the official
model CLIs; this is disclosed residual exposure, not destination-level network
isolation. GitHub read-back subsequently found exact-candidate External Round 8
`CHANGES_REQUIRED` at review `5561321715`; the local control plane has not
consumed it and remains `AWAITING_EXTERNAL_PRODUCT_REVIEW`. Activation therefore
still requires authorized checkpointing without repair or Round 9, followed by
old-trigger disable/read-back and owner cutover approval.

The integration worktree preflight remains fail-closed because the active product PLAN
does not own these maintenance paths, its STATUS is bound to another branch/HEAD, and
the worktree intentionally has no private `.venv`. The authorized files remain intact
and uncommitted; no PLAN/STATUS or sealed Issue #8 candidate bytes were rewritten to
manufacture commit eligibility.

## Completion-gate run — 2026-10-18

The owner explicitly authorized a bounded maintenance registration on the isolated
`codex/claude-reviewer-integration` branch. The registration preserves the Issue #8
active goal, PR #23, its Stop Marker, every historical review round, and all human
gates. The original preflight now passes without disabling or weakening its dirty-path,
branch, HEAD, fingerprint, authority-lock, review-artifact, or tooling checks.

### Linux hard-containment evidence

The existing `Linux_ubuntu` VM was started through its existing UTM/SSH configuration.
No account, key, Guest Agent, disk, OAuth credential, GitHub token, or host share was
added. The guest is Ubuntu 24.04.4 LTS aarch64 with cgroup v2 and `memory`/`pids`
controllers. The host worktree path was absent and no `/Users`, virtiofs, or 9p mount
was present.

- A transient user unit had `memory.max=67108864`, `memory.current=45858816` while a
  40 MiB allocation was live, and a 256 MiB allocation ended as `oom-kill`. Swap was
  disabled for the unit.
- A transient unit had `pids.max=12`, reached `pids.current=12`, recorded
  `pids.events max 1`, and the next fork failed with `errno=11`.
- Killing the controller main PID with `SIGKILL` stopped the child writer: its log stayed
  at 10 lines and the child PID no longer existed after two seconds.
- With two separately constrained writers, killing worker A left its count at 10 while
  worker B advanced from 10 to 20, proving per-worker cgroup isolation.
- Replaying the same durable event twice left the atomic budget state at
  `{"used": 1, "events": ["evt-1"]}`.
- A process that ignored `SIGTERM` was killed after the one-second stop timeout with
  `Result=timeout`, `ExecMainCode=2`, and `ExecMainStatus=9`.
- Cleanup read-back found zero matching processes, zero zombies, and zero `kgnote-*`
  transient units; the disposable guest directory was removed.

These results verify the VM execution primitive, not the current production Agent path.
Codex and Claude still execute on macOS. Moving their actual worker processes into the
guest requires official in-guest login and Runner routing; credentials must not be
copied from the Mac. Therefore `CGROUP_MEMORY_VERIFIED=true`,
`CGROUP_PIDS_VERIFIED=true`, `PARENT_CRASH_RECOVERY_VERIFIED=true` for the Linux unit
path, and `CONCURRENT_WORKER_ISOLATION_VERIFIED=true`, while
`HARD_CONTAINMENT_VERIFIED=false` for the formal Agent path.

### Product-contract and live GitHub evidence

Claude Code 2.1.302 ran with first-party OAuth, `ANTHROPIC_API_KEY` unset, restricted
mode, no tool permission, no session persistence, and synthetic data only. It produced
a schema-shaped `kgnote.product-review.v1` `CHANGES_REQUIRED` for the controlled R-004
post-block-quote speaker-attribution defect. The existing Consumer accepted the same
contract form. Deterministic tests separately prove `CODE_REVIEW_ONLY` cannot become
product acceptance, stale identity is rejected, round budget cannot overflow, a round
cannot regress after restart, and duplicate events are idempotent.

The one authorized private disposable repository is
`joannalee20050914/kgnote-reviewer-smoke-20261018`. It has one Draft PR and no Actions,
Projects, deployment, auto-merge, production data, or production secret:

- Draft PR: `https://github.com/joannalee20050914/kgnote-reviewer-smoke-20261018/pull/1`
- Baseline: `dc8401e4892212f1e83ec78a7ce6d1ec0083642e`
- Round-1 candidate: `0ebe2790c937f3b6bf24ff35829cb0eaeca4569b`, fingerprint
  `3fa10b78551914043c46715095587807e3ebfd0923eb934aea111267d1e93f36`
- Round-1 result: `CHANGES_REQUIRED`; two findings were ingested and written back at
  `https://github.com/joannalee20050914/kgnote-reviewer-smoke-20261018/pull/1#issuecomment-6248381834`
- Repair candidate: `7b06dcffd97925172b7de4950ebbec465cfdd741`, fingerprint
  `e62552294a952cb52fedb05895e2f3ea9ed2d313a807cae813b0a3c85af1cd43`
- Round-2 result: exact-candidate `PASS`; Consumer persistence and duplicate replay were
  read back at `https://github.com/joannalee20050914/kgnote-reviewer-smoke-20261018/pull/1#issuecomment-6248389592`.

The trusted publisher created both candidate commits after exact parent, path set, test
receipt, index, and staged-tree checks. Push remained a separate explicit operation.
The PR stayed Draft/Open; PR #23, Issue #8, PR #22, `main`, and the production Runner
were not modified. After the run there was no matching Codex, Claude, agent-loop, Git,
publisher, or ingestion writer.

### Cutover and rollback readiness

Before activation, install no new credentials by copying. Instead, perform official
Claude/Codex login inside the VM, route the existing Runner's worker launch through the
verified user transient-unit boundary, and repeat exact-candidate crash/resume and live
review once on that path. Then prove the old Work reviewer is stopped or scoped away,
read back the unchanged cumulative production review budget and Stop Marker, and obtain
the owner's separate activation authorization. Mac sleep must be treated as controller
unavailability; VM shutdown must prevent dispatch; controller restart must resume from
the durable checkpoint without re-consuming a round.

Rollback remains: stop at the existing Runner boundary; enumerate and terminate the
single worker cgroup; verify no writer/lock; preserve commits, reviews, checkpoints and
round counts; restore the prior Runner route; and restore the old Work reviewer only by
its legal activation procedure after proving mutual exclusion. Do not merge or delete
the disposable PR or reset evidence during rollback.

### Final gate values

- `ENGINEERING_COMPLETE=true`
- `CGROUP_MEMORY_VERIFIED=true`
- `CGROUP_PIDS_VERIFIED=true`
- `HARD_CONTAINMENT_VERIFIED=false`
- `PARENT_CRASH_RECOVERY_VERIFIED=true` for the Linux transient-unit path
- `CONCURRENT_WORKER_ISOLATION_VERIFIED=true`
- `PRODUCT_CONTRACT_VERIFIED=true`
- `INTEGRATION_COMMITTED=true` at local integration commit
  `3231db1fd97fb8d162e7e153835eb34467831230`
- `LIVE_VALIDATED=true`
- `READY_FOR_ACTIVATION=false`
- `ACTIVATED=false`

## Final Linux routing work — 2026-10-18

Permanent billing policy was committed locally as
`f37ea23d749ea9b22ce46535e1ba0302a6f5090c`. The Mac admission check positively
verified `claude.ai` / `firstParty` / `pro` and no forbidden metered-provider
environment. The same check is installed in the Guest runtime and remains fail
closed until Guest OAuth is complete.

The existing `Linux_ubuntu` guest has 11 GiB free disk and 3.5 GiB available
memory. Official checksummed user-level artifacts were installed without sudo:
Node 24.12.0, Claude Code 2.1.302, Codex CLI 0.146.0, uv 0.13.1, and the locked
agent-loop commit `aa24f193558db704c870658718650732860addd9`. No Mac OAuth, API key,
SSH private key, or home directory was copied. Claude and Codex correctly report
not logged in and have independent official login sessions pending.

`linux_worker_router.py` is a narrow Mac Runner adapter, not a new orchestrator.
It accepts one bounded event and always dispatches through SSH to a Guest
`systemd-run --user` transient unit. It has no host execution fallback. The unit
enforces `MemoryMax`, `MemorySwapMax=0`, `TasksMax`, `KillMode=control-group`,
`NoNewPrivileges=yes`, and `PrivateTmp=yes`. A Guest lease watchdog requires a
heartbeat from the Mac adapter; Mac sleep, SSH failure, or controller death makes
the lease stale and terminates the complete worker process group.

Actual routing evidence:

- A quoted-argument probe completed in the Guest at `MemoryMax=128M` and
  `TasksMax=16`; replay returned `ALREADY_COMPLETED` without a second launch.
- A live worker read-back showed `memory.max=100663296`, `memory.swap.max=0`,
  `pids.max=12`, `pids.current=3`, `KillMode=control-group`,
  `NoNewPrivileges=yes`, and `PrivateTmp=yes`.
- After the Mac controller was interrupted, the five-second lease expired, the
  Guest unit became inactive, the `/bin/sleep` child disappeared, and zero
  zombies remained.
- The pre-dispatch atomic `RUNNING` checkpoint survived controller interruption.
  Restart observed the inactive prior unit and returned
  `FAILED_CLOSED/controller_interrupted`; it did not relaunch the event.
- A Guest-generated SSH deploy key is installed only on the private disposable
  smoke repository with write access. Its private key remains in the Guest. The
  verified GitHub Ed25519 host fingerprint is
  `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`; the Guest read back smoke
  branch HEAD `7b06dcffd97925172b7de4950ebbec465cfdd741`.

### Guest OAuth and billing admission

Both official Guest login flows completed without copying any Mac credential.
`claude auth status` reported `loggedIn=true`, `authMethod=claude.ai`,
`apiProvider=firstParty`, and `subscriptionType=pro`; `codex login status`
reported `Logged in using ChatGPT`. The Guest environment contained none of
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, Bedrock, Vertex, AWS, or Google
application-credential variables. The Guest billing preflight returned `PASS`
with `credential_values_logged=false` and
`total_cost_usd_interpretation=usage_reference_only` before the Claude call.

### Final exact-path smoke

The existing Mac Runner adapter dispatched every worker event through the
Ubuntu transient-unit boundary. The exact path was:

`Mac Runner -> Linux cgroup -> Codex -> Trusted Publisher -> push to the
authorized disposable branch -> Claude Reviewer -> Result Ingestion ->
Checkpoint`.

- Codex CLI 0.146.0 authenticated through ChatGPT OAuth and changed only
  `README.md` in the disposable worktree. Its normal `workspace-write` profile
  failed closed because `bwrap` could not create a nested namespace under the
  systemd hardening. The successful retry used Codex `danger-full-access` only
  inside the isolated Guest/cgroup and disposable worktree; Codex still had no
  commit or push authority. Four unit tests passed.
- Trusted Publisher verified parent `7b06dcffd97925172b7de4950ebbec465cfdd741`,
  exact path `README.md`, and test-receipt digest, then created local commit
  `ebe805b39eb5fc2e0cb17efd2a8d974c415629fd`. The separately bounded Guest
  deploy key pushed only `codex/reviewer-smoke` in the authorized private test
  repository.
- The final candidate fingerprint (SHA-256 of the exact recursive Git tree
  listing) is
  `ddcabee097654d4a75ad86d57981cd7c83805f6de530a3a8d200a0d8e99550ee`.
- Claude Code 2.1.302 ran only after the Guest billing preflight, with no tools,
  no session persistence, and the exact candidate bytes embedded in its prompt.
  It returned schema-shaped `PASS`, zero findings, and
  `native_ui_observed=false`. Its reported `total_cost_usd=0.145916` is recorded
  only as a usage reference and is not evidence of actual billing.
- The existing Consumer accepted the exact identity as Product Contract
  `PASS` at review round 3 of cumulative limit 5. Replaying the identical event
  returned `ALREADY_CONSUMED`; neither the round nor budget was reset.
- Evidence comment:
  `https://github.com/joannalee20050914/kgnote-reviewer-smoke-20261018/pull/1#issuecomment-6248713537`.
  PR #1 remains Draft/Open.

### Reviewer mutual exclusion and activation boundary

The disposable repository has zero GitHub Actions workflows. The old Work
Reviewer configuration remains bound to `joannalee20050914/KGnote-public`, PR
#23, and its existing trigger contract; the Linux smoke route is bound to the
separate disposable repository and PR #1. Therefore the two paths cannot claim
the same PR. Read-back found production PR #23 still Draft/Open at
`4b6e6eebcddcbd4ef21259a3ece6d92b276473ea`, and Issue #8 still Open. Existing
product findings, round history, Stop Marker, and product/human gates were not
changed. Claude code-review transport success remains distinct from KGnote
Product Contract acceptance, and this fixture PASS has no authority over PR
#23 or the native human gates.

Cutover remains an explicit owner action: confirm the old reviewer has no
active work for the target PR, preserve its cumulative state, switch the single
Mac Runner worker launch to `linux_worker_router.py`, verify Guest OAuth and
billing preflight again, then remove the Stop Marker only with separate owner
approval. Rollback is executable without resetting history: stop dispatch at
the Mac Runner, stop the one named Guest unit, enumerate writers and locks,
preserve every checkpoint/round, restore the previous Runner route, and restore
the old reviewer only after re-proving mutual exclusion.

Final maintenance gate values:

- `ENGINEERING_COMPLETE=true`
- `CGROUP_MEMORY_VERIFIED=true`
- `CGROUP_PIDS_VERIFIED=true`
- `HARD_CONTAINMENT_VERIFIED=true`
- `PARENT_CRASH_RECOVERY_VERIFIED=true`
- `CONCURRENT_WORKER_ISOLATION_VERIFIED=true`
- `PRODUCT_CONTRACT_VERIFIED=true`
- `LIVE_VALIDATED=true`
- `GUEST_CLAUDE_OAUTH=claude.ai/firstParty/pro`
- `GUEST_CODEX_OAUTH=ChatGPT`
- `EXACT_PATH_SMOKE=PASS`
- `READY_FOR_ACTIVATION=true`
- `ACTIVATED=false`

The formal Linux routing implementation and final readiness evidence are
committed at `f002b694097e5986631f6f451a3e0db5e88ae858`. The separately required
billing-policy commit remains
`f37ea23d749ea9b22ce46535e1ba0302a6f5090c`.

## Authorized production cutover attempt — 2026-10-18

The owner authorized the sequential production cutover and preservation of
External Round 8. The existing Consumer accepted GitHub review `5561321715`
for PR #23, round 8, HEAD `4b6e6eebcddcbd4ef21259a3ece6d92b276473ea`,
fingerprint `38eae708123a99a7abd04327ce079b05248e18646402285a6f83fb49f69a2330`,
verdict `CHANGES_REQUIRED`, and finding `finding-r-004`. Repeating the same
Consumer operation preserved the external-review-state digest and did not
change review cycle 20 or supplemental usage 15/17. No repair or Round 9 was
started.

The old scheduled reviewer is owner-confirmed disabled (`is_enabled=false`).
Its platform does not expose an independently queryable in-flight-work state to
this local control plane. Local process inspection found no old reviewer or
writer, and GitHub still showed Round 8 as the latest production review, but
those facts cannot prove the platform queue empty.

Activation was therefore stopped fail-closed. The installed LaunchAgent still
executes `scripts/local_autonomy_runner.py`, which directly calls the Host
`codex_orchestrator.py resume`; it is not wired to `linux_worker_router.py`.
Loading it would consume `.ai/ORCHESTRATOR_STOP`, transition the durable state
to `STOPPED`, and a later resume could route the accepted `CHANGES_REQUIRED`
result into the prohibited R-004 repair. The LaunchAgent remains unloaded.
Claiming that this is the Mac Runner -> Ubuntu Claude Reviewer production path
would be false. No replacement Runner or second orchestrator was created.

The Guest Landlock helper digest matched the tracked helper. Claude billing
admission again reported `claude.ai` / `firstParty` / `pro`, no forbidden
metered environment, no credential values logged, and usage-reference-only
interpretation for `total_cost_usd`. Codex remained logged in with ChatGPT.
Cross-profile probes again denied Codex access to Claude/SSH credentials and
denied Claude access to Codex/SSH credentials and worktree writes.

Cutover attempt gates:

- `ROUND8_INGESTED=true`
- `OLD_REVIEWER_DISABLED=true` (owner/platform read-back)
- `OLD_REVIEWER_IN_FLIGHT_INDEPENDENTLY_VERIFIED=false`
- `LANDLOCK_VERIFIED=true`
- `BILLING_PREFLIGHT=PASS`
- `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false`
- `CLAUDE_REVIEWER_ACTIVATED=false`
- `PRODUCT_STOP_MARKER_PRESERVED=true`
- `PR23_ROUND9_STARTED=false`

## Cutover Epoch scoped activation — 2026-10-18

The owner accepted epoch-scoped non-overlap while explicitly preserving
`GLOBAL_REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false`. Durable epoch
`claude-reviewer-epoch-20261018t143601z` began at the actual UTC time
`2026-10-18T14:36:01Z`. Its tracked record preserves the disabled old task,
last known run `2026-10-18T03:50:42Z`, every existing canonical PR (1, 22, 23)
as legacy, the exact Round 8 checkpoint, activation scope
`EPOCH_NEW_AUTHORIZED_PRS_ONLY`, and implementation commit
`d72dcb21877352a9a43df101228f31bfb5877330`.

The scope gate is executable before Linux dispatch. It fetches canonical GitHub
PR metadata and requires repository allow-list membership, `created_at`
strictly after the epoch, non-legacy identity, exact HEAD/fingerprint/round,
approved goal authority, available budget, open work window, clear applicable
Stop Marker, and no existing exact-candidate result. Missing or malformed data
fails closed. PR #23 was tested against its live GitHub metadata and rejected as
legacy even when the fixture supplied a forged approval and available budget.
Changing its HEAD, comments, updated time, draft state, or reopen state cannot
change its immutable creation time or legacy inventory membership.

Sixteen epoch/router tests and seven Runner tests passed. The production
LaunchAgent is loaded with the epoch record and admission executable. Initial
idle health encountered expected checkpoint-version drift and failed closed;
Runner commit `f432ecd169b5b7a51ce455347a6a07432683cb71`
versioned the idle event without deleting v1 history. Idle v2 then completed
through Ubuntu at `MemoryMax=128M`, `TasksMax=16`; the next wake returned
`ALREADY_COMPLETED`. No model call, review trigger, writer, or product mutation
occurred. Guest process read-back found zero residual workers.

Activation read-back preserved PR #23 HEAD `4b6e6eeb`, review `5561321715`,
Round 8 ingestion, orchestrator cycle 20, supplemental usage 15/17, and the
product Stop Marker. The VM remains started for the loaded safe-idle Runner.

- `OLD_REVIEWER_DISABLED=true`
- `OLD_REVIEWER_IN_FLIGHT_INDEPENDENTLY_VERIFIED=false`
- `GLOBAL_REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false`
- `CUTOVER_EPOCH_RECORDED=true`
- `LEGACY_PR23_EXCLUDED=true`
- `EPOCH_SCOPED_NON_OVERLAP_VERIFIED=true`
- `EPOCH_SCOPED_REVIEWER_ACTIVATED=true`
- `MAC_RUNNER_TO_LINUX_ROUTER_VERIFIED=true`
- `LANDLOCK_VERIFIED=true`
- `BILLING_PREFLIGHT=PASS`
- `PRODUCT_STOP_MARKER_PRESERVED=true`
- `PRODUCT_DEVELOPMENT_RESUMED=false`
- `PR23_REPAIR_STARTED=false`
- `PR23_ROUND9_STARTED=false`

Rollback remains: boot out the one LaunchAgent, stop named Guest units and
verify no descendants, stop the VM, preserve the epoch record/checkpoints and
legacy inventory, and leave the old task disabled. Rollback must never move the
epoch backward or admit a legacy PR.

## Final activation-unblock canary — 2026-10-18

The existing GitHub deploy key `kgnote-linux-exact-path-smoke-20261018`
(`id=166832464`) was read back as verified, writable, and scoped to only the
private smoke repository. No new key was created. Its private key was moved
from the shared Guest runtime tree to mode-0600 `.ssh`, which only the Router's
`push` profile exposes. Actual open probes were denied for Codex, Claude,
Publisher, and Ingestion and succeeded only for Push. A deploy key is
repository-scoped, not branch-scoped; no broader claim is made.

Runner commit `35a7dd84b4241f49eedf5b6d89ad30ce94758317`
adds an explicit canary-order admission restricted to event IDs beginning
`production-canary-`, the private smoke worktree, and integration evidence
checkpoints. Router support for a separate Claude/Ingestion handoff directory
keeps the candidate read-only while permitting the schema result to cross the
stage boundary.

The formal LaunchAgent executed every new canary stage through the existing
Runner and Router. Codex changed only README and ran four tests. Trusted
Publisher verified parent `ebe805b39eb5fc2e0cb17efd2a8d974c415629fd`,
allowed path README, and test receipt, producing
`40ca0161b071170b8b095373a4ea1a210db03749`. The Push-only stage published that
commit and GitHub read-back matched it. Claude ran after same-worker Pro billing
admission with no tools and returned a schema-valid Round 4
`CHANGES_REQUIRED`: the prompt omitted the README bytes, so it correctly refused
to infer the literal content. The Consumer accepted and persisted that exact
finding; replay preserved the same checkpoint. This is a successful transport,
isolation, negative-review, ingestion, and deduplication canary, not a Product
Contract PASS.

The old scheduled task remains owner-confirmed disabled, but the platform still
returned no machine-readable active-run, pending-execution, cancellation, or
write-credential revocation evidence. Its GitHub connector cannot be revoked
without affecting other GitHub work, which is expressly forbidden. Therefore
mutual exclusion is not independently enforceable and formal activation remains
blocked. The LaunchAgent was restored to safe-idle configuration and unloaded;
the VM was stopped after worker cleanup.

- `TEST_REPO_PUSH_CREDENTIAL_VERIFIED=true`
- `PUSH_STAGE_ISOLATION_VERIFIED=true`
- `MAC_LAUNCHAGENT_WIRING_VERIFIED=true`
- `PRODUCTION_EXACT_PATH_VERIFIED=true` (transport and negative verdict path)
- `OLD_REVIEWER_DISABLED=true`
- `OLD_REVIEWER_IN_FLIGHT_INDEPENDENTLY_VERIFIED=false`
- `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false`
- `ROUND8_INGESTED=true`
- `LANDLOCK_VERIFIED=true`
- `BILLING_PREFLIGHT=PASS`
- `CLAUDE_REVIEWER_ACTIVATED=false`
- `PRODUCT_DEVELOPMENT_RESUMED=false`
- `PR23_REPAIR_STARTED=false`
- `PR23_ROUND9_STARTED=false`
- `PR23_REPAIR_STARTED=false`

Rollback state is already the safe state: keep the LaunchAgent unloaded, retain
the Stop Marker and accepted Round 8 checkpoint, stop all named Guest units,
shut down the VM, and do not re-enable the old scheduled task while its in-flight
state is unknown. A future activation requires a legally registered modification
of the single existing Mac Runner so every model/publisher/ingestion launch goes
through the Linux router, followed by a zero-round canary and sequential
mutual-exclusion read-back. It must not resume PR #23 or reset any budget.

## Production Runner wiring follow-up — 2026-10-18

The owner subsequently authorized the minimum modification of the single
existing Mac Runner. Commit `9f24ccf64b934e27b17126995bbe67ea2d78df3c`
changes that Runner so it never executes the Host `codex_orchestrator.py`
agent path. It probes `kgnote-ubuntu` and submits only a validated order to the
existing `linux_worker_router.py`. Missing Guest connectivity, missing Router,
or missing product Linux order now fails closed; there is no Mac agent fallback.

The production LaunchAgent remains the same label and Runner. Its explicit
entry is now:

`product .venv Python -> issue24 local_autonomy_runner.py --repo product --router integration/scripts/linux_worker_router.py`

With the product Stop Marker present, the Runner does not read or mutate the
product review state and does not consume the Marker. It routes only the fixed
`production-idle-health-v1` event (`/usr/bin/true`, ingestion Landlock profile,
`MemoryMax=128M`, `TasksMax=16`). The first LaunchAgent run completed in the
Guest; later runs returned `ALREADY_COMPLETED`. With the VM stopped, the same
formal entry returned `guest_unavailable` and exit 2 without spawning any Host
Codex, Claude, orchestrator, writer, or fallback. After the VM restarted, the
LaunchAgent returned to the deduplicated idle result. Six focused Runner tests
passed.

Read-back after the LaunchAgent runs preserved the Stop Marker and Round 8
checkpoint digest, orchestrator state `AWAITING_EXTERNAL_PRODUCT_REVIEW`, cycle
20, supplemental usage 15/17, PR #23 HEAD `4b6e6eeb`, and latest GitHub review
`5561321715`. No Round 9, repair, product commit, or live model call occurred.
The Guest had zero residual KGnote worker/model processes after collection.

This closes the Mac LaunchAgent -> existing Runner -> Linux Router wiring and
safe-idle gates. It does not establish the complete post-wiring
Codex/Publisher/Claude/Ingestion path through the LaunchAgent: the retained
full-chain smoke predates this Runner wiring, and the Guest smoke deploy private
key is intentionally absent. More importantly, the old ChatGPT Work platform
still provides no machine-readable in-flight/queue result to this local control
plane. Viewing the supplied task ID rendered its automation card but returned
no independent run-state evidence. Consequently production reviewer mutual
exclusion remains unproven and activation remains fail-closed. The LaunchAgent
was unloaded and the VM stopped after evidence capture; its corrected plist is
retained for the next bounded attempt.

Follow-up gates:

- `MAC_LAUNCHAGENT_WIRING_VERIFIED=true`
- `MAC_RUNNER_TO_LINUX_ROUTER_VERIFIED=true`
- `LINUX_CGROUP_VERIFIED=true`
- `LANDLOCK_VERIFIED=true`
- `BILLING_PREFLIGHT=PASS`
- `PRODUCTION_IDLE_GATE_VERIFIED=true`
- `STOP_MARKER_NON_CONSUMPTION_VERIFIED=true`
- `ROUND8_INGESTED=true`
- `OLD_REVIEWER_DISABLED=true`
- `OLD_REVIEWER_IN_FLIGHT_INDEPENDENTLY_VERIFIED=false`
- `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false`
- `PRODUCTION_EXACT_PATH_VERIFIED=false`
- `CLAUDE_REVIEWER_ACTIVATED=false`
- `PRODUCT_DEVELOPMENT_RESUMED=false`
- `PR23_REPAIR_STARTED=false`
- `PR23_ROUND9_STARTED=false`

## Final cutover-audit correction — 2026-10-18

The later production cutover audit in
`docs/control-plane/FINAL_CUTOVER_AUDIT_AND_MAC_MVP_20261018.md` supersedes only
the activation-readiness conclusion above; it does not invalidate the exact-path
smoke, billing admission, cgroup, crash, or ingestion evidence. An actual Guest
probe showed that `systemd-run --user` `InaccessiblePaths` and
`ProtectHome=tmpfs` did not hide the same-user Claude/SSH credential paths.
Because `danger-full-access` therefore shares the `kgnote` credential namespace
and the Guest has unrestricted NAT egress, `HARD_CONTAINMENT_VERIFIED` applies
only to resource/process containment, not credential or network containment.

Until separate Guest service identities are installed and measured, and the old
production reviewer is quiescent rather than
`AWAITING_EXTERNAL_PRODUCT_REVIEW`, the corrected gates are:

- `DANGER_FULL_ACCESS_BOUNDARY_AUDITED=true`
- `DANGER_FULL_ACCESS_BOUNDARY_SAFE=false`
- `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false` for production cutover
- `READY_FOR_ACTIVATION=false`
- `ACTIVATED=false`
