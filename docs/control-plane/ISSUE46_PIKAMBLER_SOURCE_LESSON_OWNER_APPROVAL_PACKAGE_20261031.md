# Issue #46 — Pikambler 原文教材 Product Goal Owner 授權提案

**STATUS: PROPOSAL ONLY / DO NOT POST APPROVE UNTIL ALL FOUR DEPENDENCIES PASS.**

- Issue: https://github.com/joannalee20050914/KGnote-public/issues/46
- Goal ID: `GOAL-KGNOTE-PIKAMBLER-SOURCE-LESSON-CANARY`
- Goal version: `2026-10-31.1-isolated-canary-proposal`
- Canonical spec SHA-256: `5e19072c3ea7b27e66e70a01f40bdc5d85d354017a7366cef510e3c96c69429e`
- Exact JSON: `docs/control-plane/ISSUE46_PIKAMBLER_SOURCE_LESSON_GOAL_SPEC_v2026-10-31.1.json`
- Readiness and O2 isolation policy: `docs/control-plane/ISSUE46_PIKAMBLER_SOURCE_LESSON_READINESS_20261031.md`
- Single selected private original Pikambler source only; read original in Obsidian, add user notes separately, preserve source bytes and role attribution.
- This is an **isolated one-Goal canary**, not successor in O2-ordered backlog. O2 remains ACTIVE but read-only, legacy runner unloaded, separate state/ledger/PR, global writer lock, no paid API or private data egress.
- Codex goal total ≤6, Claude goal total ≤6, max per work window ≤2 each, one model at a time, min interval 300s, quota backoff 3600s. Never borrow or reset O2 or Issue #47 charges. No automatic merge or full B-scheme go-live.
- Current #47 Mac engineering intake is **hardcoded to one earlier #47 comment ID**; it cannot yet accept a general #46 Product Goal APPROVE. General intake adapter, source selection and O2 isolation receipts must be independently tested first.
- Owner exact approval after dependencies are met may grant only this one bounded product trial; a separate human final acceptance and standing B-scheme go-live decision remain required. User will not relay engineering prompts.

## Exact future Owner reply — **not currently authorized to post**

<!-- kgnote-product-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.product-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "GOAL-KGNOTE-PIKAMBLER-SOURCE-LESSON-CANARY",
  "goal_version": "2026-10-31.1-isolated-canary-proposal",
  "goal_spec_sha256": "5e19072c3ea7b27e66e70a01f40bdc5d85d354017a7366cef510e3c96c69429e",
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

This future comment must be posted by the actual repository Owner on Issue #46 and validated with `author_association=OWNER`, repository, Goal ID/version, canonical digest, exact permissions and dependency receipts. This proposed text is *not* a comment or a launch instruction. If this spec changes, its digest must change; do not reuse approval across versions.
