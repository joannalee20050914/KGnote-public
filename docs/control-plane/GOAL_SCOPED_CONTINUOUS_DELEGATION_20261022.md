# Goal 級持續委任與自主產品開發契約

Status: implementation authority for the B-scheme control-plane Goal. This document does not authorize any KGnote Product Goal, product feature, merge, paid API use, or release.

Direction ID: `kgnote-goal-scoped-continuous-delegation-2026-10-22`
Product direction preserved: `kgnote-obsidian-first-2026-09-22`

## 1. Authority and identity layers

KGnote uses three non-interchangeable lifecycle layers:

| Layer | Canonical identity | Authority source | Lifecycle owner | What its completion means |
| --- | --- | --- | --- | --- |
| Codex App execution Goal | the App/thread Goal plus the execution `PLAN.md` goal | current user instruction in Codex App | Codex App | this bounded B-scheme implementation task ended |
| KGnote Product Goal | `goal_id` + `goal_version` + canonical spec digest | exact GitHub Issue approval authored by the repository Owner and read back by Runner | Mac Runner | the approved product outcome reached its recorded final acceptance/closure state |
| Work Item / Milestone | `work_item_id` / compatibility `milestone_id` under one Product Goal | the approved Product Goal envelope and its dependency graph | Mac Runner | one bounded engineering or review obligation reached a terminal state |

Compatibility fields such as `goal_id`, `active_goal`, and `milestone_id` remain readable. Every new record must also carry `identity_kind`, `authority_kind`, `authority_record`, and `lifecycle_owner`, so the shared names cannot erase the layer boundary.

The following implications are forbidden:

- Codex App Goal start, pause, completion, budget, token usage, context rollover, or thread archival does not approve, pause, close, fund, or revoke a KGnote Product Goal.
- A Product Goal may not be authorized by Agent-created Issues, labels, Project fields, ordinary comments, a PR, a session change, or a copied App prompt.
- `candidate_verified`, a Claude `PASS`, publication, Product Goal `CLOSED`, human product acceptance, and merge authorization remain separate facts.
- An implementation may not change Issue, PR, branch, Goal version, or finding ID to reset attempts, no-progress history, quota history, or authority.

## 2. Product Goal authorization

A Product Goal specification is immutable for one `goal_version`. It names the outcome, Requirement/RC/FD bindings, dependencies, allowed operations, forbidden substitutes, work window, provider policy, review duties, completion conditions, human gates, pause/resume/revoke rules, and total resource ceilings.

Execution authority exists only when Runner verifies all of the following from GitHub:

1. the canonical repository and Issue match the Goal specification;
2. the approval comment is authored by the configured repository Owner and has `author_association=OWNER`;
3. the approval marker names the exact `goal_id`, `goal_version`, and specification SHA-256;
4. the approval grants only enumerated permissions and has not expired, paused, or been revoked;
5. the local Goal state and every Work Item remain within that exact envelope.

Runner, not the GitHub parser, applies a valid command. It appends the exact comment identity and body digest before atomically advancing local state; if the process stops between ledger fsync and state replacement, the next tick replays the Runner-owned `state_patch`. Invalid lifecycle requests such as an early `ACCEPT` or a `CLOSE` that would bypass required product acceptance are durably rejected and never become authority merely because the comment syntax was valid.

The lifecycle is `PLANNED -> APPROVAL_REQUIRED -> APPROVED -> ACTIVE -> ACCEPTANCE_REQUIRED -> CLOSED`. `BLOCKED` is entered only with a durable stop reason and release condition. `PAUSED` and `REVOKED` are authority-lease conditions, not substitutes for lifecycle closure. Only the Owner's exact GitHub transition may approve, accept, pause, resume, revoke, or close a Product Goal.

Only after the prior Product Goal is `CLOSED` may Runner select the next dependency-satisfied backlog entry and request approval. A closure adds a digest-bound dependency receipt to Runner state; a later Goal cannot enter `APPROVED` or `ACTIVE` unless every dependency named in its immutable spec has a receipt. Runner carries the prior closure receipts forward, selects the next backlog entry, and queues one deduplicated approval notification. Selection and notification never grant execution authority.

## 3. Continuous delegation inside one approved Goal

Within the exact approved envelope, Runner may continue across sessions and authorized work windows through:

`Goal -> Work Item -> Codex -> deterministic verification -> Trusted Publisher -> Ubuntu Claude -> Codex repair -> re-verification -> re-review -> next legal Work Item`.

Ordinary `CHANGES_REQUIRED`, product-test failure, bounded infrastructure recovery, provider quota waiting, GitHub write-back recovery, a new agent context, and a new work window do not require another Owner approval. They also do not permit broader files, operations, providers, PRs, Issues, product behavior, or resources.

The initial concurrency remains one model-bearing Work Item. Main merge, branch-protection changes, destructive data operations, unapproved egress, paid API fallback, and old-Issue authority migration are prohibited.

## 4. Separate accounting facts

The append-only Goal ledger records distinct event identities for:

- authority admitted for a logical Work Item;
- a concrete model attempt starting and reaching a known/unknown terminal state;
- actual usage, including `UNKNOWN` when no reliable measurement exists;
- a valid independent Claude verdict;
- publication/write-back of an already-produced result;
- a product obligation's evidence-backed progress state;
- lifecycle, checkpoint, notification, pause, resume, revoke, and closure transitions.

One counter may never stand for all of these. A 429 with zero tokens and no verdict is an attempted launch and quota observation, not a valid review. A preserved verdict whose GitHub write-back failed is published without another model call. Completion Gate or Publisher rejection does not consume a Claude verdict. Existing raw Ledger events, canonical reviews, checkpoints, Stop Markers, and budget usage remain immutable; the new reducer explains them without rewriting history.

Logical work identity and attempt identity are separate. An unknown execution state must be reconciled against its checkpoint/process/result before any redispatch.

Every external dispatch uses a Runner-owned sealed order binding (repository path, content digest, and order event ID). Runner first passes the existing Writer Lock, Stop Marker, epoch/scope admission and authority gates, then durably reserves the attempt in the Goal ledger before invoking the existing Linux router. A reserved attempt without a reconciled checkpoint blocks redispatch after restart. Routing success is not model completion, review validity, publication, or obligation resolution.

A terminal routing checkpoint changes Product Goal state only when its command digest and event ID match the sealed order. A successful checkpoint must also carry a schema-validated `kgnote.product-goal-worker-result.v1` envelope bound to the exact Goal spec, Work Item and order. Usage, independent review verdict, publication receipt and obligation evaluation are then appended as separate events. Only an independent `REVIEW_PASS` may set `VERIFIED_RESOLVED`; Codex, a commit, or a successful process exit cannot do so. `CHANGES_REQUIRED` activates a pre-authorized repair lane, whose completion reopens the verification/publication/review evidence path for the same stable obligations.

Independent review orders must bind the exact `program_id`, Product Goal identity, PR, commit, fingerprint, round, review scope and repository-relative authority paths. The Ubuntu Claude adapter may retain compatibility defaults for already-issued legacy orders, but every new Product Goal order supplies those fields explicitly; it may not inherit a legacy finding or product scope from a singleton prompt. Publication and Consumer read-back accept Goal-specific config/state paths so parallel or later Goals do not rewrite an older PR's review identity. The native Ubuntu Runner trigger is a non-Work marker; ChatGPT Work remains notification-only.

## 5. Resource policy

Codex ChatGPT OAuth and Claude Pro OAuth are independent subscription resources. No metered API fallback is permitted.

The desired 10% reserve is enforceable only from a trusted account-level remaining-percentage observation with source and observation time. Token counts, context capacity, cost estimates, session reset text, or absence of a 429 are not subscription percentage. Independently of percentage observability, the Owner-approved per-window and Goal-version total launch ceilings are hard upper bounds; a high trusted percentage cannot enlarge them.

When the percentage is unavailable, Runner records `PERCENTAGE_UNOBSERVABLE` and uses the verifiable fallback envelope: approved Asia/Taipei work window, one active model Work Item, minimum launch interval, provider-specific quota backoff, an explicit per-window launch ceiling, an explicit Goal-version total launch ceiling, bounded strategy counts, and checkpoint-first recovery. Window and total counts are reconstructed from the append-only ledger; a date, Session or mutable state edit may open a new window allowance but cannot reset the Goal total. Planning is read-only: immediately before the durable dispatch reservation, Runner reads back the current state and ledger and rechecks authority, work eligibility, runtime blocks, work window, provider, interval, both launch ceilings and the plan's resource evidence. It must not claim that the 10% reserve has been implemented accurately.

Goal admission rejects cyclic Work Item dependencies, a model-bearing Work Item assigned to the wrong provider, a Work Item lacking the permission required for its action, or an obligation with no independent Claude REVIEW lane. Runner state must retain the exact milestone, dependencies and obligation bindings from the immutable Goal spec.

## 6. Recovery and progress

Runner distinguishes at least:

- provider quota: wait until the recorded retry condition, append a no-model ledger transition that clears the exact backoff, then re-plan and re-admit under the unchanged Goal;
- closed work window: checkpoint and continue in the next window;
- model started/result unknown: reconcile, never blind-redispatch;
- GitHub/Publisher transient failure: read back possible side effects and reuse completed Worker output;
- deterministic/product failure or `CHANGES_REQUIRED`: route an in-scope repair;
- product requirement conflict, authority conflict, safety overreach, irreversible risk, or new spending: block affected work and request Owner action.

A terminal checkpoint with an unknown or interrupted outcome remains an unreconciled dispatch. Runner records at most one digest-bound probe for unchanged checkpoint bytes, does not append attempt-finished/usage/verdict facts, and does not redispatch until the same checkpoint becomes conclusive. Owner pause, revocation, or go-live withdrawal blocks every new launch but does not block this evidence-preserving checkpoint reconciliation. A reconciled work-window, deterministic/evidence, Publisher/GitHub, or Completion Gate failure is released only by its own no-model ledger transition. Runner then replans through the original immutable Work Item, resource policy, sealed order, Writer Lock and admission gates. Repeated operational failures use the Goal's bounded same-failure count; exhaustion blocks only that Work Item and releases the global runtime block so unrelated dependency subgraphs can continue.

Progress is evaluated by stable product obligations derived from Requirement, RC, FD, and canonical finding history. Finding renames do not create a new obligation. Allowed evaluations are `VERIFIED_RESOLVED`, `FUNCTIONAL_PROGRESS_UNVERIFIED`, `NO_OBLIGATION_PROGRESS`, `EVIDENCE_INSUFFICIENT`, `REGRESSION`, and `AUTHORITY_CHANGED`.

Two consecutive rounds without obligation progress trigger a bounded strategy adjustment, not an automatic request for more budget. Strategy adjustment may locate the real entrypoint, add a negative test, reconcile all related findings, or change an engineering method within the approved WHAT. Exhausting the bounded strategies blocks only the affected dependency subgraph; independent approved work may continue.

## 7. Backlog and notifications

The maintained Product Goal backlog is derived once from `DEVELOPMENT_PLAIN.md`, the requirements/scenario SSOT, `FEATURE_DISPOSITION_LEDGER.md`, and current delivery evidence. Later closure checks only the next Goal's dependencies and relevant version drift; it does not rescan and reinvent the whole roadmap.

Human-attention events are limited to final product acceptance, next-Goal approval after closure, unresolved product WHAT conflict, new expense/permission/irreversible risk, or bounded strategy exhaustion that requires changing product outcome or total resources. Each event has a stable deduplication key and durable queued/sent/acknowledged states. On each live Runner tick, queued GitHub fallback notices are read-before-write, posted at most once, read back with an exact body/comment identity, and then recorded as sent. Delivery failures enter a five-minute durable backoff and are bounded by the Goal's same-failure attempt limit; they do not grant authority or stop unrelated work. Runner consumes only an exact Owner-authored ACK for the same repository, Issue, notification, Goal ID, and Goal version. Acknowledgment never grants execution authority.

ChatGPT Work is notification-only. It never grants authority. Until an event trigger, connection, delivery, and read-back are operated successfully for this repository, its status is `UNVERIFIED`; a GitHub native Issue comment is the implemented reliable fallback.

## 8. Migration and go-live boundary

The existing Issue #9 / PR #29 history is a mandatory replay fixture, not a migrated unlimited Product Goal. Its three earlier valid `CHANGES_REQUIRED` reviews, Codex commits, 429/no-verdict attempt, Round 4 canonical verdict, Completion Gate blocks, Publisher recoveries, budgets, and findings remain unchanged.

This implementation Goal may build, test, replay, run an isolated no-model trial, and prepare a reversible Draft PR. It may not activate long-running Product Goal delegation until all of these are true:

- an exact GitHub Product Goal approval exists;
- resource/payment boundaries are explicit;
- legacy ledger migration read-back and recovery tests pass;
- the real Runner version can read old and new states;
- a bounded real-product trial shows no authority expansion, duplicate dispatch, or false accounting;
- Stop Marker, manual merge, independent review, and final acceptance remain protected;
- the Owner makes the separately verifiable one-time go-live authorization.

## 9. This implementation Goal's delivery boundary

The Codex App execution Goal ends after the dormant-compatible implementation, contracts, schemas, regression/replay evidence, isolated trial, rollback instructions, and Draft PR are complete. Formal Product Goal go-live remains a separate Owner decision. Completing or exhausting the App Goal does not mutate Product Goal authority.
