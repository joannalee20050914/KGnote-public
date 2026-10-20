# Canonical public repository migration

Status: active execution record. This document changes repository operations only; it does not change KGnote product authority or promote any human acceptance gate.

## Decision

The previous `joannalee20050914/KGnote` repository remains private as a historical archive because closed pull-request refs retain pre-sanitization material. It is not a publication or future-development target.

The sanitized rewritten history is being promoted to a new canonical public repository:

- preferred repository: `joannalee20050914/KGnote-public`;
- fallback only if unavailable: `joannalee20050914/KGnote-next`;
- canonical base: `main`;
- autonomous implementation/review branch: `codex/kg-note-autonomous-review`;
- primary reviewer contract: `.ai/REVIEWER_BOOTSTRAP.md`.

Only the approved `main` and autonomous-review refs may be pushed. Stale pull refs, old temporary branches, backup refs, private review history, raw learner feedback, private conversation artifacts, and unsafe fixtures are excluded.

## Operational invariants

- `origin` becomes the new public canonical repository only after its public-history audit passes.
- `archive-origin` retains access to the old private repository.
- No long-term mirror, custom webhook service, GitHub Action calling OpenAI, polling daemon, or OpenAI API usage is introduced.
- Deterministic verification, Codex self-review, independent AI product review, and final human acceptance remain distinct.
- `PA-HUMAN-1`, `NS-HUMAN-SMOKE`, and `release_verified=false` remain unchanged.

## Additional publication hygiene

Before publication, obsolete connector-installation evidence is removed and historical author/committer email metadata is normalized to the repository owner's GitHub noreply identity. This changes commit object IDs without changing project trees or weakening product history. A verified pre-normalization bundle is retained outside the repository for recovery.
