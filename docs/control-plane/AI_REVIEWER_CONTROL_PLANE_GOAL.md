# AI reviewer control-plane goal

Status: current explicit execution direction, recorded 2026-09-23. This is governance authority only; it does not change KGnote product semantics.

## Source identity

- Speaker: product owner
- Original attachment: `local-source-withheld`
- SHA-256: `463f39f2e3bb71326333ca31be4d461590f66afd5377fa31007e785265f9e490`
- Goal ID: `GOAL-KGNOTE-AI-REVIEWER-CONTROL-PLANE-V1`

## Autonomous orchestration amendment

- Speaker: product owner
- Date: 2026-09-23
- Source: explicit current thread objective, durably restated here because conversation history is not a recovery dependency
- Effect: upgrades the already-built reviewer protocol without replacing it; routine READY/review/repair/progression and context rollover become machine-owned, with a default five-cycle budget and the named human/runtime terminal states

## Accepted execution direction

Build a durable repository-mediated control plane among Codex implementation contexts, separate independent reviewer contexts, and the human as product and architecture decision authority. A fresh session must recover intended behavior, candidate identity, validation evidence, unresolved findings, human blockers, and exact next action without conversation history.

The repository remains the communication bus. Codex owns implementation within approved semantics. A separate ephemeral reviewer context reviews observable semantic conformance and does not edit product implementation. The human decides genuine ambiguity, authority conflict, new observable behavior, privacy/consent changes, destructive migration, and explicit human gates.

The protocol must provide fingerprint-bound request/result artifacts, persistent finding lifecycle, structured product-decision escalation, deterministic validation and stale-result rejection, role bootstraps, append-only history, and an autonomous start/resume/status/stop loop. READY_FOR_AI_REVIEW is a machine handoff; PASS advances authorized work, CHANGES_REQUIRED repairs and re-reviews for up to five cycles, and only named terminal states interrupt for human or runtime recovery.

## Preserved authority and conflicts

No conflict with current higher authority was found. The goal is interpreted under `docs/control-plane/AUTHORITY.md`, the `kgnote-obsidian-first-2026-09-22` direction, baseline `kgnote-reconciliation-2026-09-23-r6`, and requirement `KG-GOV-07` with scenarios `SC-33` and `SC-35`.

The following boundaries are non-negotiable:

- Product authority, requirement SSOT, representation/data contracts, traceability, dirty-worktree ownership, consent rules, and fail-closed behavior remain unchanged.
- Reviewer PASS is semantic evidence for the exact candidate only. It is not human, device, release, or learning-effectiveness acceptance.
- `PA-HUMAN-1` and `NS-HUMAN-SMOKE` remain pending external gates.
- An implementer context may never author or self-approve a reviewer PASS; reviewer execution must use a separate context and exact candidate custody.
- This goal changes no KGnote product feature or observable learning behavior.

The detailed executable scope and milestone order live only in root `PLAN.md`; factual recovery state lives only in root `CODEX_STATUS.md`.
