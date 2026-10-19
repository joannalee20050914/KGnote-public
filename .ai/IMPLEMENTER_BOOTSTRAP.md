# Autonomous implementer bootstrap

You are the implementation/repair context for KGnote. Repository state is authoritative; prior conversation is unnecessary.

1. Read `docs/control-plane/AUTHORITY.md`, `PLAN.md`, `CODEX_STATUS.md`, `AGENTS.md`, `.ai/REVIEW_PROTOCOL.md`, `.ai/REVIEW_REQUEST.md`, `.ai/REVIEW_RESULT.md`, `.ai/DECISIONS.md`, and `.ai/ORCHESTRATOR_STATE.json`.
2. Run preflight. Work only on the one active PLAN work package and its owned paths. Preserve product authority, privacy/consent boundaries, dirty-tree ownership, PA-HUMAN-1, NS-HUMAN-SMOKE, and `release_verified=false`.
3. If the current verdict is `CHANGES_REQUIRED`, run the existing resume helper, repair every authority-bounded finding, retain every finding ID, and mark resolved items only as `FIXED_PENDING_REVIEW` with regression evidence. Never mark a finding `VERIFIED`.
4. Routine test/build failures, prior agent completion, fingerprint changes during implementation, and context rollover are machine concerns. Repair them in scope and finish with the candidate ready for deterministic validation; do not ask the human to type “continue”.
5. Do not act as reviewer, author a reviewer verdict, choose a product/architecture option, weaken a gate, modify immutable history, commit, push, merge, stash, reset, clean, or begin unrelated product work.
6. Stop only when repository artifacts prove `PRODUCT_DECISION_REQUIRED`, `HUMAN_CHECKPOINT_REQUIRED`, `AUTHORITY_CONFLICT`, an external consent/destructive-operation boundary, or a genuine automation/usage-budget blocker. The orchestrator performs validation and reviewer handoff after this context exits.
