# KGnote repository review protocol

Protocol version: `kgnote.review-protocol.v1` plus the durable autonomous-orchestration extension. The v1 artifact schemas and history remain intact for compatibility; orchestration changes routine execution ownership, not product or release authority. This protocol extends the existing KGnote control plane and is not a competing authority.

## Canonical artifacts

| Artifact | Role | Normal writer |
|---|---|---|
| `PLAN.md` | single active execution goal, milestones, owned paths, gates | Codex under explicit user direction |
| `CODEX_STATUS.md` | factual resume state and exact next action | Codex |
| `.ai/REVIEW_REQUEST.md` | current candidate request | Codex only |
| `.ai/REVIEW_RESULT.md` | current independent semantic result | separate independent reviewer context only after repository inspection |
| `.ai/DECISIONS.md` | structured pending and decided human questions | Codex/reviewer may open; human alone decides |
| `.ai/REVIEW_HISTORY/` | immutable snapshots and append-only event log | protocol helper; existing entries may not be edited or deleted |
| `.ai/ORCHESTRATOR_STATE.json` | durable goal/work package, machine state, agent, custody, cycle, blockers, next action, and human-action flag | orchestrator only |
| `.ai/ORCHESTRATION_HISTORY/` | append-only orchestration transitions and recovery evidence | orchestrator only |
| `.ai/IMPLEMENTER_BOOTSTRAP.md` | fresh implementation/repair-context instructions | control-plane maintainer under explicit execution direction |

Product truth remains in the sources named by `docs/control-plane/AUTHORITY.md`. Review artifacts report conformance; they do not redefine approved behavior.

## Review state machine and autonomous owner

```text
IMPLEMENTING
  └─ implementer exits ─> orchestrator validation + stable identity
       └─ READY_FOR_AI_REVIEW (v1 review-artifact name: READY_FOR_REVIEW)
       └─ orchestrator assigns custody to a separate reviewer context ─> UNDER_REVIEW
            ├─ reviewer ─> CHANGES_REQUIRED ─> Codex records resolutions ─> IMPLEMENTING
            ├─ reviewer ─> PRODUCT_DECISION_REQUIRED ─> human decision ─> IMPLEMENTING
            └─ reviewer ─> PASS ─> orchestrator advances or completes the goal
```

`READY_FOR_AI_REVIEW` is a machine handoff, never a human-blocking state. The durable orchestrator maps it to the retained v1 request value `READY_FOR_REVIEW`, immediately acquires custody, and launches a new ephemeral reviewer context. `CHANGES_REQUIRED` similarly routes to a fresh implementer context after preserving every finding. Agent/thread completion and context rollover are not stop states.

Allowed exceptional transition: `READY_FOR_REVIEW -> IMPLEMENTING` when Codex runs `review-invalidate --reason ...` before reviewer custody. The helper preserves the request snapshot, appends an `INVALIDATED` event, allocates a new review ID, clears the candidate binding, and synchronizes `CODEX_STATUS.md`. Candidate byte drift after `UNDER_REVIEW` is handled by the stale-candidate helper: the old result cannot be used, an immutable event and new review ID are created, and the orchestrator returns to implementation automatically.

| From | To | Writer | Required evidence and stop rule |
|---|---|---|---|
| `IMPLEMENTING` | `READY_FOR_REVIEW` | Codex/orchestrator | stable candidate fingerprint, exact validation evidence, complete request, no unresolved protocol errors; implementation freezes and machine review begins |
| `READY_FOR_REVIEW` | `UNDER_REVIEW` | reviewer | request validates and repository fingerprint matches; implementation is frozen for that review |
| `UNDER_REVIEW` | `CHANGES_REQUIRED` | reviewer | at least one authority-traceable unresolved finding; progression blocked |
| `UNDER_REVIEW` | `PRODUCT_DECISION_REQUIRED` | reviewer | at least one structured undecided question proving existing authority insufficient; affected scope blocked |
| `UNDER_REVIEW` | `PASS` | reviewer | exact candidate matches, all reviewed requirements accounted for, no unresolved blocker, human gates preserved |
| `CHANGES_REQUIRED` | `IMPLEMENTING` | Codex | all findings retained; attempted fixes marked `FIXED_PENDING_REVIEW`, never `VERIFIED` by Codex |
| `PRODUCT_DECISION_REQUIRED` | `IMPLEMENTING` | human then Codex | human decision is durably recorded in the appropriate existing authority/decision system and linked from `.ai/DECISIONS.md` |

`PASS` is terminal for one exact candidate. The orchestrator archives and consumes it before changing PLAN or beginning another package. Any candidate-affecting byte change makes it stale and returns execution to `IMPLEMENTING` under a new review cycle. PASS permits automatic work-package progression when `PLAN.md` permits it and the next package has no explicit human checkpoint. It never promotes `release_verified`.

## Autonomous orchestration state

Canonical runtime states are `IMPLEMENTING`, `VALIDATING`, `READY_FOR_AI_REVIEW`, `REVIEWING`, `REPAIRING`, machine-owned `AWAITING_EXTERNAL_PRODUCT_REVIEW`, `HUMAN_CHECKPOINT_REQUIRED`, `PRODUCT_DECISION_REQUIRED`, `AUTHORITY_CONFLICT`, `AUTOMATION_BLOCKED`, `BUDGET_EXHAUSTED`, `GOAL_COMPLETE`, and operator-requested `STOPPED`. `AWAITING_EXTERNAL_PRODUCT_REVIEW` is valid only after exact publication plus remote read-back; it names the configured event transport as next actor and never requests owner continuation. Normal human interruption is limited to:

- `HUMAN_CHECKPOINT_REQUIRED`: the next PLAN package explicitly names a coherent observable-product checkpoint.
- `PRODUCT_DECISION_REQUIRED`: existing authority genuinely cannot select observable behavior.
- `AUTHORITY_CONFLICT`: locked authority conflicts or required consent authority is missing.
- `AUTOMATION_BLOCKED`: structured evidence proves the runtime cannot continue safely; ordinary failing tests do not qualify.
- `BUDGET_EXHAUSTED`: an actual model usage/quota error, not context length or agent completion.
- `GOAL_COMPLETE`: every package for this goal passed; report the next preserved HUMAN checkpoint.

The default automated review/repair budget is five reviewer cycles. `CHANGES_REQUIRED` below the budget returns findings to a fresh implementer context, validates a new fingerprint, and invokes a fresh reviewer. Five unresolved cycles transition to `AUTOMATION_BLOCKED` with the cycle count and unresolved IDs. Implementer and reviewer run as separate `codex exec --ephemeral` contexts and reconstruct authority from repository artifacts. Context/token-window rollover therefore creates a new context and continues without human prompting.

Candidate custody is explicit in `.ai/ORCHESTRATOR_STATE.json`: `NONE`, `SEALED`, or `REVIEWER`, with review ID, exact fingerprint, and owner. A reviewer may mutate only reviewer-bus artifacts. The orchestrator compares candidate identity around reviewer execution and rejects stale custody before interpreting a verdict.

The reviewer validates a newly written result with `review-validate-pending`, which deliberately does not require orchestrator-owned `CODEX_STATUS.md` to predict unsubmitted findings. On normal return or crash recovery, the orchestrator detects a durable `SUBMITTED` result while custody is still `UNDER_REVIEW`, atomically archives it through `review-submit`, synchronizes STATUS/history, and only then runs status-coupled preflight and verdict routing. The reviewer must not run submit/resume transitions.

Operations are deliberately small:

```bash
python3 scripts/codex_orchestrator.py --repo . start
python3 scripts/codex_orchestrator.py --repo . resume
python3 scripts/codex_orchestrator.py --repo . status
python3 scripts/codex_orchestrator.py --repo . stop
```

`start`/`resume` run until a terminal state; `stop` requests a safe boundary stop. Durable state and append-only history allow crash recovery without conversation history.

## Candidate identity and fingerprint

`candidate_revision` is `<git-head>+worktree:<candidate_fingerprint>`. `base_revision` is the checkpoint or comparison commit. Because the repository may be intentionally dirty, Git HEAD alone is insufficient.

The candidate fingerprint extends the existing deterministic repository fingerprint. It includes tracked and non-ignored untracked files, file kind, mode, and byte digest, plus branch and HEAD. Only mutable communication/orchestration-bus artifacts are excluded:

- `CODEX_STATUS.md`
- `.ai/REVIEW_REQUEST.md`
- `.ai/REVIEW_RESULT.md`
- `.ai/DECISIONS.md`
- `.ai/REVIEW_HISTORY/**`
- `.ai/ORCHESTRATOR_STATE.json`, `.ai/ORCHESTRATOR_STOP`, `.ai/ORCHESTRATOR.lock`
- `.ai/ORCHESTRATION_HISTORY/**`

The protocol document, schemas, both role bootstraps, orchestrator implementation, tests, PLAN, AGENTS, authority files, and product files remain included. Exact exclusions are part of the algorithm and tested.

Every request, result, and history snapshot records candidate revision and fingerprint. The request also seals the canonical per-path candidate manifest and the positive human-decision identity set derived from the reviewed PLAN. A result whose `review_id`, revision, or fingerprint differs from the current request is stale and cannot authorize progression.

While `PRODUCT_DECISION_REQUIRED` is pending, decision resume compares the live repository with that sealed manifest. Only the exact validated external authority-record path(s) named by the required decisions may differ; a PLAN/identity-anchor change or any unrelated implementation, protocol, test, or owned-path drift remains terminal without changing STATUS, history, request, or custody. The live identity anchor must still equal the sealed positive identity set.

## Field ownership

Codex owns request fields, implementation/validation evidence, and only these finding transitions: `OPEN -> FIXED_PENDING_REVIEW`. The independent reviewer owns result verdicts, finding creation, and `FIXED_PENDING_REVIEW -> VERIFIED` or back to `OPEN`. The human owns decision selection, approval evidence, and transitions to `SUPERSEDED_BY_HUMAN_DECISION`; a reviewer result may project that human-owned transition only when a linked `DECIDED` entry names the finding and its non-`.ai` `authority_record` contains valid structured human-decision proof. Pending-result validation and archival compare every known finding with its last immutable-history status and fail closed on an actor-invalid transition. The orchestrator may invoke isolated contexts, assign custody, validate, copy, timestamp, digest, archive, retry, and advance an already-authorized PLAN dependency; it may not invent a verdict, resolution, decision, or gate result.

`author_role: CHATGPT_WORK_REVIEWER` is required for submitted results and `reviewer_identity` must be non-empty. This is an auditable role assertion, not a cryptographic identity guarantee; repository permissions or signed commits are the stronger enforcement layer when available. Codex instructions explicitly prohibit impersonating this role.

## Finding lifecycle and history

Finding IDs are stable within a goal and are never reused. Allowed statuses are `OPEN`, `FIXED_PENDING_REVIEW`, `VERIFIED`, and `SUPERSEDED_BY_HUMAN_DECISION`. Codex cannot set `VERIFIED`; neither role may delete an unresolved finding.

`FIXED_PENDING_REVIEW` remains unresolved. During a new review cycle it must remain visible in `CODEX_STATUS.md`, the history index, and reviewer focus until the reviewer changes it to `VERIFIED` or a human decision legitimately supersedes it.

Before replacing a current request or result, the helper archives byte-identical snapshots under `.ai/REVIEW_HISTORY/<review_id>/` and appends an event to `events.jsonl`. Snapshot filenames include their SHA-256. The index records every known finding and last status. Validation replays event actor ownership and finding transitions. An incorrect immutable actor field is never rewritten: `review-history-correct-actor` appends one explicit audit correction naming the prior event, prior actor, required actor, and reason. Validation fails if a previously known unresolved finding disappears, if an uncorrected event actor is invalid, if a correction is ambiguous, if replay and index differ, if history changes, or if an event references a missing snapshot.

## Product-decision escalation

A decision request must contain `decision_id`, the question, why existing authority is insufficient, affected requirements, options, observable consequences, blocking scope, status, links to findings, and the exact `review_id`, `candidate_revision`, and `candidate_fingerprint` that raised it. Codex and reviewer may add options without selecting one. The human records the selection and a repository-relative `authority_record` in the existing authority/decision system. The selected option must be one of the offered options and `decided_by` must identify a human rather than an automation role. `.ai/DECISIONS.md` cannot point to itself as approval evidence.

The external authority file must be a new dedicated artifact at the exact path `docs/requirements/human-decisions/<decision_id>.md`, absent from the sealed candidate manifest, and contain only the canonical heading plus exactly one `KGNOTE HUMAN DECISION AUTHORITY JSON` marker block with schema `kgnote.human-decision-authority.v1`. It must repeat the decision ID, review/candidate identity, selected option, human identity and time, linked findings, and a non-empty `decision_evidence` statement. Those fields must match `.ai/DECISIONS.md`; `PLAN.md`, protocol, implementation, tests, other candidate-control paths, arbitrary existing files, extra same-file content, unrelated authority text, or reviewer self-assertion are invalid. Human identity is positive and repository-authoritative: `decided_by` must exactly match both the identity set sealed in the review request and the still-unchanged `PLAN.md` `explicit_direction.speaker`; machine-role blacklists, arbitrary unregistered labels, or rewriting PLAN during the decision pause are insufficient. A change to that identity anchor requires a separately sealed review cycle under the normal authority rules. Until every exact required decision has this proof, the affected scope remains blocked. `orchestrator resume` validates the canonical new records, proves that they are the only paths added after the sealed candidate manifest, performs the human-authorized transition, adopts that narrowly reconciled fingerprint into factual STATUS and durable orchestrator state, clears prior custody, and launches a fresh implementer without selecting an option itself. Conversation-only decisions are invalid.

## Fail-closed rules

Treating a missing or malformed result as PASS is forbidden. A stale result, Codex-authored reviewer fields, unresolved blocker, missing history snapshot, unowned dirty path, missing validation evidence, or relevant human checkpoint also fails closed. `READY_FOR_AI_REVIEW`, ordinary `CHANGES_REQUIRED`, test/build failure, fingerprint change during authorized implementation, context rollover, and agent completion are routing events handled automatically; they are not reasons to ask the human to continue.

Protocol validation proves structural consistency and exact identity only. It does not prove semantic correctness, human acceptance, privacy consent, device behavior, or release readiness.
