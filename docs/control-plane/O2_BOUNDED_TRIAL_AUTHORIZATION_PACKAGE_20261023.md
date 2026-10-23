# O2 首次真實 Product Goal 有界試行核准包

Status: prepared, not authorized. This package becomes actionable only after the trial-readiness Draft PR has exact-candidate independent review, the Product Owner explicitly authorizes its merge/deployment, and the exact GitHub Owner command below is published and read back. It does not itself authorize merge, deployment, Product Goal execution, or full B-scheme go-live.

## Decision summary

Selected real Product Goal: `GOAL-KGNOTE-O2-READING-EXPERIENCE`

- Version: `2026-10-23.1-bounded-trial`
- Canonical spec: `docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.1.json`
- Canonical JSON spec digest: `cd9f03754142ff1e0f34b6bd9229afd893965d8b7bbd1d3644c7523893f6cbcc`
- File SHA-256: `d3a5e541292b8c53e6fe61b7dee8cbf05b8959c38672ea5c836a4c1576a82413`
- GitHub authority location: Issue [#9](https://github.com/joannalee20050914/KGnote-public/issues/9)
- Lifecycle owner: Mac Runner
- Model concurrency: `1`
- Merge: forbidden to agents; requires a separate explicit Product Owner decision
- Final acceptance: required from the Product Owner before `CLOSED`

The Legacy dependency is legally dispositioned by `LEGACY_ISSUE9_DISPOSITION_20261023.md`: no history is reset, PR #29 is untouched, and its three Round 4 findings are explicit unfinished O2 obligations.

## Product outcome and forbidden substitutes

Success means ordinary Obsidian Markdown is the primary reading entry; Obsidian and the secondary Web reference read back the same Concept/Relation/Evidence identities; context-local notes retain source revision, anchor and provenance; held-out beginner prose and gaps remain source-bounded; exact-candidate verification, publication and independent review pass; and a real Mac Obsidian human trial is accepted.

Forbidden substitutes:

- Web-first UI or a second generic Markdown editor.
- PR #29 commits, old tests, old PASS-like records, ignored output or same-source self-comparison presented as current completion evidence.
- AI-authored unsupported clauses, silent source rewriting, invented prerequisite relations, or stale anchor guessing.
- Deterministic tests or Claude review promoted to Mac/iPad/iPhone human acceptance.
- Automatic merge, force-push, Stop Marker removal, branch-protection changes, paid API, fallback provider or unapproved data egress.

## Resource envelope proposed for Owner approval

The 10% reserve remains a desired policy, not a measurable fact: both providers are `PERCENTAGE_UNOBSERVABLE`. The trial therefore uses hard limits reconstructed from its own append-only ledger.

| Control | Codex | Ubuntu Claude | Basis |
| --- | ---: | ---: | --- |
| Subscription only | yes | yes | Existing B contract |
| Paid API fallback | no | no | Product Owner instruction |
| Concurrent model work | \- | \- | Global maximum `1` |
| Minimum launch interval | 300 s | 300 s | Existing B fallback |
| Per authorized work window | 3 | 3 | Existing tested B fallback; no increase |
| Goal-version total launches | 4 | 4 | One initial implementation/review plus at most three bounded repair/re-review opportunities; matches the observed four PR #29 review rounds instead of the generic 12-launch fixture ceiling |
| Quota backoff | 3600 s | 3600 s | Existing tested B fallback and observed 429 recovery behavior |

Work window: Monday–Friday, Asia/Taipei `09:00–18:00`. A new day may restore only the per-window allowance; it never resets the Goal total. A started context consumes one launch even when it ends with 429 or unknown usage. No-progress is evaluated after two consecutive rounds; at most one in-scope strategy adjustment is allowed. The same operational failure may be attempted at most twice before that Work Item blocks. These bounds can be enlarged only by a new Owner-approved Goal version or explicit additive grant; normal `CHANGES_REQUIRED`, quota waiting and in-envelope repair need no per-round approval.

## Review, stop and rollback rules

- Every product obligation has an independent Ubuntu Claude review lane. ChatGPT Work is notification-only and remains optional.
- Completion Gate must run before each formal review; missing current-candidate render/click, positive/negative receipts, HEAD/fingerprint or read-back blocks review without spending Claude capacity.
- Two consecutive rounds with no obligation progress trigger the one permitted strategy adjustment. A third unchanged outcome is not launched under this version.
- Stop immediately on product-WHAT conflict, authority/spec drift, new expense, unapproved data egress, destructive or irreversible change, provider mismatch, exhausted Goal total, unsafe symlink/path/common-directory result, or stale sealed order.
- `PAUSE` blocks new launches but preserves checkpoint reconciliation. `REVOKE` is terminal for this exact version. `RESUME` must bind the same version/digest and cannot reset counters.
- Rollback removes the Product Goal arguments from LaunchAgent and reloads the prior trusted plist, while preserving spec, state, ledger, checkpoints, reviews, GitHub receipts and Stop Marker. Rollback pauses dispatch; it does not silently close or accept the Goal.

## Bounded trial versus full B-scheme go-live

This package uses two authority stages without bypassing `go_live_authorized=false`:

1. **Bounded trial authorization.** The Owner approves one exact Product Goal version/digest and its enumerated `activate_runner` permission. Runner's `go_live_authorized=true` is then scoped only to this immutable Goal record, work window, operations and launch ceilings. Repository-level `B-SCHEME-GO-LIVE` remains `NOT_AUTHORIZED`; no successor Goal inherits this trial permission.
2. **Full B-scheme go-live.** Only after O2 trial evidence, final human acceptance, closure and rollback review may the Owner separately authorize the standing continuous-delegation policy. That later decision may enable maintained backlog handoff, but each successor still needs its own exact Owner approval.

Thus the first stage is a real product trial, not a temporary code bypass. The second stage is not implied by trial success.

## Exact GitHub Owner approval command

Publish this only after approving the reviewed infrastructure Draft PR for merge/deployment and confirming the deployed spec digest. Codex is not authorized to publish it in the current task.

<!-- kgnote-product-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.product-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
  "goal_version": "2026-10-23.1-bounded-trial",
  "goal_spec_sha256": "cd9f03754142ff1e0f34b6bd9229afd893965d8b7bbd1d3644c7523893f6cbcc",
  "permissions": [
    "activate_runner",
    "commit",
    "push",
    "draft_pr",
    "review",
    "verify"
  ]
}
```

The Owner-authored comment must have GitHub `author_association=OWNER`. Any changed order, permission, version, digest, Issue or author fails closed.

## LaunchAgent deployment delta (do not apply in this task)

After deploying the reviewed candidate to a new immutable concentrated worktree, append all of these arguments together to `com.kgnote.local-autonomy-runner.plist`; a partial set must fail closed. The operator must render `${HOME}` to the trusted account's absolute Home path when writing the plist because LaunchAgent arguments do not perform shell expansion:

```text
--product-goal-spec
${HOME}/Library/Application Support/KGnote/runtime/product-goals/GOAL-KGNOTE-O2-READING-EXPERIENCE/2026-10-23.1-bounded-trial/spec.json
--product-goal-state
${HOME}/Library/Application Support/KGnote/runtime/product-goals/GOAL-KGNOTE-O2-READING-EXPERIENCE/2026-10-23.1-bounded-trial/state.json
--product-goal-ledger
${HOME}/Library/Application Support/KGnote/runtime/product-goals/GOAL-KGNOTE-O2-READING-EXPERIENCE/2026-10-23.1-bounded-trial/ledger.jsonl
--product-goal-backlog
${HOME}/Library/Application Support/KGnote/runtime/product-goals/PRODUCT_GOAL_BACKLOG.json
```

Do not add `--product-goal-trial` for the real run; that flag is no-model planning only. Do not add a local comments fixture path; live authority must be read from GitHub Issue #9. Preserve the existing router, epoch, scope-admission, pending-goal, integration-root environment, Writer Lock and Stop Marker arguments.

## Deployment and acceptance sequence

1. Confirm the trial-readiness PR is independently reviewed at its exact HEAD/fingerprint and remains Draft/unmerged until Owner authority.
2. On explicit Owner authorization, merge only that reviewed PR and deploy its exact merge commit to a new guard-created concentrated `runner-deploy-<sha>` worktree; verify Git common directory and clean bytes.
3. Copy the exact Goal spec and maintained backlog to the runtime paths, initialize empty state/ledger through existing Goal helpers, and read back both spec digests.
4. Back up the current plist, apply the all-or-none argument delta, reload LaunchAgent, and read back program arguments plus deployed Runner SHA before any model launch.
5. Publish the exact Owner approval command on Issue #9. Runner must record comment ID/URL/author/body digest and activate only this Goal version.
6. Observe one bounded real-product flow through implementation, deterministic verification, Trusted Publisher, Ubuntu Claude, in-scope repair if needed, and Mac Obsidian human acceptance. GitHub Issue notifications are canonical; ChatGPT Work absence is not a blocker.
7. On failure, pause/revoke as appropriate and perform configuration-first rollback. On success, require exact Owner `ACCEPT`, close this Goal, then prepare the separate full-go-live decision from actual trial evidence.

No ordinary engineering command needs another Product Owner round. The only remaining decisions are exact merge/deployment authority, this fixed resource envelope and trial activation, final human acceptance, and any later full B-scheme go-live.
