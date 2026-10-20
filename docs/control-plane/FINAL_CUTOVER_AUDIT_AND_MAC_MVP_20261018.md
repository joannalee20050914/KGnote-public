# KGnote Claude Reviewer final cutover audit and Mac MVP delivery report

Date: 2026-10-18 (Asia/Taipei)

This report records a bounded audit and an isolated Mac demonstration. It does
not activate the Ubuntu reviewer, remove `.ai/ORCHESTRATOR_STOP`, resume the
Issue #8 review loop, modify PR #23, or promote a human/product/release gate.

## Executive result

The prior integration baseline, OAuth billing admission, exact-path smoke,
cgroup controls, crash/restart evidence, and duplicate-ingestion evidence are
still valid. The final audit found one previously unproven production boundary:
Codex `danger-full-access` and Claude currently run as the same Guest user that
owns both OAuth stores. User-level systemd path-hardening properties did not
hide those files in an actual Guest probe. The Guest network is NAT/shared and
has no destination allow-list. Consequently the cgroup remains a valid resource
and process-lifetime boundary, but it is not a credential or network boundary.

The follow-up repair adds a kernel Landlock allow-list outside Codex's own
sandbox. Actual routed probes prove that the Codex stage can read only its own
OAuth and writable candidate, while the Claude stage can read only its own OAuth
and a read-only candidate; neither can read `.ssh`. Minimal real ChatGPT OAuth
and Claude Pro OAuth calls then succeeded through those profiles without a
worktree change. A final GitHub read-back found that the old Work reviewer has
already submitted External Round 8 `CHANGES_REQUIRED` with one finding for the
exact PR #23 HEAD/fingerprint. The local control plane remains
`AWAITING_EXTERNAL_PRODUCT_REVIEW` because that result has not been consumed.
Formal activation therefore remains blocked until cutover authority permits the
pending result to be checkpointed without starting a repair/new round, followed
by the sequential trigger switch.

An independent Mac Demo Vault was generated and re-read successfully at:

`${HOME}/KGnote-MVP-Demo-20261018/KGnote Alpha/network-path-147bb293`

It demonstrates the current Markdown/Obsidian learner projection, source and
evidence links, optional Canvas, and a filled manual continuation that survives
same-input regeneration. It is not a formal release or a substitute for the
pending native Obsidian and learner judgments.

## A. Claude Reviewer audit

### Baseline and billing

| Check | Result | Evidence |
| --- | --- | --- |
| Integration commits | PASS | `f37ea23d749ea9b22ce46535e1ba0302a6f5090c`, `f002b694097e5986631f6f451a3e0db5e88ae858`, `f9fcdfba061f4b4ab6ca840f86495938e1b07643` exist on `codex/claude-reviewer-integration`. |
| Product preflight | PASS | Branch `codex/issue-8-source-library`, HEAD `4b6e6eebcddcbd4ef21259a3ece6d92b276473ea`, fingerprint `38eae708123a99a7abd04327ce079b05248e18646402285a6f83fb49f69a2330`; no unexpected dirty paths. |
| Review artifacts | PASS | `review-validate` accepted internal Cycle 20 PASS for the exact candidate; it grants routing only. |
| Claude billing admission | PASS | Guest read-back: `claude.ai`, `firstParty`, `pro`; forbidden metered environment absent; credential values not logged; `total_cost_usd` remains usage-reference-only. |
| Codex authentication | PASS | Guest reports `Logged in using ChatGPT`. |
| Live smoke | PASS, retained | Draft PR #1 remains at `ebe805b39eb5fc2e0cb17efd2a8d974c415629fd`; exact-path evidence comment `6248713537` remains the retained evidence. |
| Production resources | UNCHANGED | PR #23 remains Draft/Open at `4b6e6eeb`; Issue #8 remains Open; repository Actions workflow count is zero; Stop Marker remains present. External Round 8 review `5561321715` is exact-candidate `CHANGES_REQUIRED` and remains pending local ingestion. |

The follow-up boundary validation made one successful minimal Claude call and
one successful minimal Codex call. Claude ran only after the Guest billing
preflight in the same restricted worker. One earlier Codex attempt reached the
bounded timeout before model output because DNS resolution was not yet admitted;
it failed closed and made no worktree change.

### `danger-full-access` boundary

| Boundary | Verified fact | Decision |
| --- | --- | --- |
| Host filesystem | UTM config has only the Guest qcow2 disk and read-only CD; Guest mount read-back found no `/Users`, virtiofs, or 9p mount. | PASS: no Host shared-folder path was found. |
| Guest privilege | Worker identity is only `uid=1002(kgnote) gid=1004(kgnote)` with no supplementary groups and no passwordless sudo. | PASS for root separation. |
| cgroup/process lifetime | Existing measured `MemoryMax`, `MemorySwapMax=0`, `TasksMax`, `KillMode=control-group`, lease timeout, SIGKILL, restart and duplicate evidence remains valid. | PASS for resources and descendant cleanup only. |
| Mac SSH key | Host private key and SSH config are mode `0600`; agent forwarding and interactive password authentication are disabled. Dispatch adds `ClearAllForwardings=yes`. | PASS for Host-to-Guest access. |
| Guest OAuth files | `.claude/.credentials.json` and `.codex/auth.json` remain mode `0600`. A Landlock ABI 4 wrapper now gives each stage only its own store; routed negative probes denied reads of the other store. | PASS under the final routed profiles. |
| Guest GitHub key | No private key or SSH agent was present at audit time; only `authorized_keys` and `known_hosts` remained. The prior repo-scoped smoke deploy key is therefore not currently usable from the Guest. | PASS for current stopped state; a future publisher key must be isolated from model users. |
| Commit/push authority | Trusted Publisher still checks exact parent/path/test receipt and produces a local-only commit. Codex/Claude/publisher/ingestion profiles cannot read `.ssh`; only the separately selected push profile exposes it. | PASS for filesystem credential separation; no deploy private key was present during this audit. |
| Network | UTM uses Shared/NAT networking with `IsolateFromHost=false`; no Guest egress allow-list was found. | UNRESTRICTED EGRESS. This is not a PASS and must be treated as exfiltration exposure. |
| Mac failure | Lease heartbeat and no-host-fallback behavior remain verified; VM-off dispatch fails closed. | PASS. |

Actual probes using `systemd-run --user` with `InaccessiblePaths` and
`ProtectHome=tmpfs` both still observed the protected credential paths. Those
properties are not credited. Rootless bubblewrap was also rejected by Ubuntu's
AppArmor user-namespace restriction. The replacement uses Landlock ABI 4,
`NoNewPrivileges`, and an allow-list installed before `exec`; it is irreversible
and inherited by descendants. A first Codex compatibility call timed out because
the DNS resolver target was not allowed and failed closed. After adding only
`/run/systemd/resolve` read access, the real Codex and Claude OAuth calls passed.

### Reviewer mutual exclusion

Current state is safe because the new production route is disabled and the Stop
Marker exists. The old path remains bound to `joannalee20050914/KGnote-public`
PR #23, while the completed Linux smoke is bound to the separate private smoke
repository PR #1. Duplicate Consumer events and restart do not reset rounds.

Production cutover is not yet proven mutually exclusive: the old control plane
is locally `AWAITING_EXTERNAL_PRODUCT_REVIEW` even though GitHub already holds
the exact Round 8 result, and the prior separate-repo smoke does not prove an
atomic trigger handoff for the same production PR.
Therefore `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false` for production activation,
even though the design and rollback checks are ready.

### Cutover runbook

1. Obtain the owner's explicit cutover approval. Do not remove the Stop Marker.
2. Verify the deployed Landlock helper digest matches the tracked helper and
   select the explicit `codex`, `claude`, `publisher`, `push`, or `ingestion`
   worker profile; reject an absent or unknown stage.
3. Re-run the Claude billing preflight in the Claude profile and read back the
   existing official ChatGPT/Claude OAuth status. Never copy Mac credentials.
4. Re-run the cross-profile denial probes. Install any future repository-scoped
   deploy key only for the push stage and verify both model profiles cannot read
   it. Record metadata only, never credential contents.
5. Keep the Runner stopped. Read back PR #23 HEAD, fingerprint, review round,
   cumulative budget, Consumer checkpoint, and Stop Marker. Confirm the old
   reviewer has no active or queued work; consume/checkpoint review
   `5561321715` through the existing legal control path without launching repair,
   inventing a fresh round, or authorizing External Round 9.
6. Disable the old trigger by its supported platform method. Read back that it
   rejects a new event and has no live worker.
7. Point the single Mac Runner worker-launch adapter at the separated Guest
   stage identities and transient cgroups. There must remain one coordinator.
8. Run one bounded post-switch canary against the authorized disposable Draft
   PR. Verify exact identity, billing admission, publisher-only push, Consumer
   deduplication, checkpoint, resource limits, and zero residual workers.
9. Only after the owner separately authorizes formal product work may the Stop
   Marker be removed. Record activation state and never reset historical rounds.

### Rollback runbook

1. Stop new dispatch at the Mac Runner and keep/create the Stop Marker.
2. Stop the named Guest worker units; wait for the lease deadline, enumerate
   descendants, and verify zero model, Git, publisher, ingestion, or writer
   process and zero live repository lock.
3. Preserve PR/HEAD/fingerprint, every review result, cumulative round, Consumer
   checkpoint, and the failure evidence. Do not retry under a new identity.
4. Disable the Ubuntu route and verify VM-off dispatch fails closed.
5. Restore the old reviewer only through its supported trigger configuration,
   after proving the new route rejects events and has no queued work.
6. Re-run preflight and one read-only status check. Do not merge, force-push,
   reset a budget, or promote a human/release gate.

## B. Mac MVP gap matrix

| MVP capability | Status | Evidence / remaining gap |
| --- | --- | --- |
| Import one or more sources | Implemented candidate, formal review pending | Issue #8/PR #23 contains persistent source import and read-back; current candidate is waiting for external product review and remains stopped. |
| Reusable persistent source | Implemented candidate, formal review pending | Source/revision/hash/idempotency tests pass; not promoted to released MVP. |
| Natural-language learning material | Demonstrated | Demo `Start Here.md`, Concepts, Relationships, Structure, Evidence, and immutable Source were generated on Mac. Arbitrary-source quality still needs product evaluation. |
| Know the current topic and first step | Needs human judgment | Static entry and navigation exist; clarity is a `PA-HUMAN-1` question. |
| Return from a note to source/evidence | Automatically verified | Generator read-back passed source paths, generated links, and four anchors. |
| Save basic learning progress | Automatically verified for the demo | Filled learner-owned `Continue Here.md` and `My Notes.md` survived same-input regeneration byte-for-byte; web continuity is also covered by targeted tests. Progress is intentionally explicit, not inferred. |
| Close/reopen and continue | Static contract verified; native smoke pending | Resume heading link resolves under validator; actual close/reopen in Obsidian remains `NS-HUMAN-SMOKE`. |
| Use directly on Mac | Demo delivered; formal MVP not delivered | The independent vault can be opened now with Obsidian **Open folder as vault**. Formal candidate activation/release remains blocked. |
| Canvas helps understanding | Human judgment required | Canvas has 5 nodes/4 edges and valid local file targets; usefulness cannot be automated. |
| Markdown useful without Canvas | Human judgment required | Complete Markdown fallback exists; learner usefulness remains human evidence. |

Targeted Mac verification used the existing `.venv` and ran 85 tests covering
Obsidian native projection, Personal Alpha presentation/workspace/CLI, source
library and HTTP read-back, Reader, continuity, and learning-note HTTP behavior:
`Ran 85 tests ... OK`. The first plain-system-Python invocation was invalid
because it lacked the repository environment; it made no product changes and
is not counted as a product failure.

### Minimal human product smoke

1. In Obsidian, choose **Open folder as vault** and open
   `${HOME}/KGnote-MVP-Demo-20261018/KGnote Alpha/network-path-147bb293`.
2. Open `Start Here.md` in Reading view. State what the lesson is about and what
   you believe the first action is.
3. Follow one concept link, then open its evidence/source link. Confirm whether
   the explanation teaches rather than merely lists facts.
4. Open `Continue Here.md`, follow its filled Resume link, close Obsidian, reopen
   the same vault, and repeat Start Here → Continue Here → Resume.
5. Complete one useful path without Canvas; then open
   `Learning Structure.canvas` and state whether it adds understanding.
6. Record separate PASS/FAIL notes for learner clarity (`PA-HUMAN-1`) and native
   operation (`NS-HUMAN-SMOKE`). Do not treat preference alone as a technical
   failure, and do not infer release readiness from either result.

## C. Cost and final state

- Claude model calls this audit: `1` successful minimal compatibility call,
  after same-worker Pro Billing Preflight.
- Codex CLI model calls this audit: `1` successful minimal compatibility call;
  one earlier transport attempt timed out before output and failed closed.
- Model usage/cost: no new monetary charge is inferred. Historical
  `total_cost_usd=0.145916` remains usage reference only.
- Tests: 85 targeted product tests and 39 integration/security tests passed;
  repository preflight, `review-validate`, and requirements structural guard
  passed.
- Product commits/pushes: none. PR #23, Issue #8, PR #1, PR #22, and `main` were
  not modified.
- Demo files: isolated under `${HOME}/KGnote-MVP-Demo-20261018`.
- Ubuntu final state: stopped. No KGnote worker unit or residual writer was found
  before shutdown.

## Gate values

- `INTEGRATION_BASELINE_VERIFIED=true`
- `BILLING_POLICY_VERIFIED=true`
- `LINUX_RUNTIME_VERIFIED=true`
- `DANGER_FULL_ACCESS_BOUNDARY_AUDITED=true`
- `DANGER_FULL_ACCESS_BOUNDARY_SAFE=true` for the routed filesystem/credential boundary; HTTPS egress remains explicit and is not claimed as destination isolation
- `REVIEWER_MUTUAL_EXCLUSION_VERIFIED=false` (production cutover)
- `CUTOVER_RUNBOOK_READY=true`
- `ROLLBACK_RUNBOOK_READY=true`
- `READY_FOR_ACTIVATION=false`
- `ACTIVATED=false`
- `MVP_SCOPE_FROZEN=true`
- `MVP_GAP_MATRIX_COMPLETE=true`
- `MVP_CORE_FLOW_IMPLEMENTED=false` (formal integrated candidate remains stopped)
- `MAC_READBACK_VERIFIED=true` (isolated demo/static Mac read-back)
- `SOURCE_PROVENANCE_VERIFIED=true` (isolated demo and candidate tests)
- `LEARNING_PROGRESS_PERSISTENCE_VERIFIED=true` (explicit demo continuation)
- `HUMAN_PRODUCT_SMOKE=false`
- `MAC_MVP_DELIVERED=false`

The minimum remaining authorizations/evidence are: quiescence and sequential
handoff of the old reviewer, explicit owner cutover approval, legal resumption
of the stopped Issue #8 product flow, and the concentrated human Obsidian smoke.
