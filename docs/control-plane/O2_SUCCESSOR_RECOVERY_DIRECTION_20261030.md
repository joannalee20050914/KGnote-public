# O2 v4 exact successor recovery direction (2026-10-30)

Source authority: the product owner instruction titled **KGnote O2 v4：一次性
successor recovery 工程授權**, received on 2026-10-30 Asia/Taipei.

This is bounded execution authority for infrastructure engineering and, only after
every named gate passes, one append-only formal recovery transition. It is not a new
Product Goal `APPROVE` or `RESUME`, does not add model quota, and does not authorize a
second product Codex launch.

## Exact sealed identities

- Canonical repository: `joannalee20050914/KGnote-public`
- Infrastructure base: `4388aa2a8d7c63cf2b81a7314176f646eec9a276`
- Goal version: `2026-10-29.4-bounded-trial-day0-proposal`
- Goal canonical digest: `7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f`
- Attempt: `attempt-2026-10-29.4-bounded-trial-day0-proposal-WI-O2-A-IMPLEMENT-1`
- Parent: `483f9e64066821d5d647d411e6da8ddb50ad88e5`
- Successor: `95d437a20ee31e48a49e2ee9b6f83ca3d4a931a6`
- Successor tree: `b2a66a296d2a76d8b79ce5343eb8447f6e9421ff`
- Successor fingerprint: `a08eccbee8f62560a8c5e279096b5a9befd94755b40e4b40f648e0ffa17a8904`
- Formal baseline ledger cursor: `8`
- Codex accounting: `4/5`; remaining quota: `1`

## Required recovery semantics

1. Preserve and rehash the saved bundle, failed checkpoint, raw model output,
   worker evidence, failed verification and formal state/ledger snapshot. Do not
   reset or rewrite the Ubuntu product checkout.
2. Add an O2 pre-publication verification profile. Before a product PR exists it
   runs all local deterministic gates, Completion Gate, fingerprint stability,
   safety checks and evidence read-back. It preserves the legacy PR #28 contract
   and leaves live PR identity verification as a required downstream gate.
3. Publication remains trusted infrastructure work. The product model receives no
   GitHub write credentials. A published PR must be read back with exact repository,
   branch, HEAD and fingerprint before downstream review.
4. A trusted one-time writer may append exactly one idempotent
   `WORK_STATE_TRANSITION` for the exact attempt and exact successor. It must fail
   closed on any evidence, authority, state, ledger, identity, verification or
   accounting drift. Prior failure events remain unchanged.
5. After recovery, `WI-O2-A-IMPLEMENT` may become verified only for the recovered
   successor; `WI-O2-A-VERIFY` remains the next planned no-model work. Recovery must
   not create a reservation, attempt, product review verdict or completion claim.
6. Keep the formal Runner unloaded throughout engineering, deployment validation and
   the recovery append so it cannot spend the remaining Codex attempt.
7. A controlled runtime upgrade may add a reviewed compatibility entrypoint that is
   absent from the prior immutable generation only when no prior shim exists for that
   name. All prior present files, the complete new manifest, cold start, atomic current
   pointer and rollback remain exact and fail closed; an existing or dangling shim for
   an absent old-generation file is drift, not an upgrade signal.

## Ordered gates

1. Isolated implementation and positive/negative deterministic tests.
2. Exact repository verification and stable evidence read-back.
3. Independent Ubuntu Claude infrastructure review of the exact candidate.
4. Normal PR publication, exact read-back and merge.
5. Controlled Mac and Ubuntu immutable-runtime deployment with read-back.
6. No-model isolated acceptance using the real Router/publication paths.
7. New exact-successor pre-publication verification on Ubuntu.
8. Check-only recovery validation, then one append, then formal read-back.

The recovery writer must independently re-read the normally merged GitHub PR, the
clean immutable Mac Runner checkout and Python receipt, the unloaded LaunchAgent
plist, and the live Ubuntu generation/deployment receipt. It must bind the exact
infrastructure verification, Ubuntu Claude infrastructure verdict and deployed
no-model acceptance hashes before either check-only readiness or apply can pass.
The new exact-successor verification must run after the controlled deployment, and
the acceptance receipt must bind its SHA-256 and creation time to the live merged
infrastructure revision, Ubuntu generation ID and runtime-manifest SHA-256. A
pre-merge or archived verification cannot satisfy that gate.

Idempotent replay is valid only for the single sequence-9 recovery event whose full
payload matches the authorized successor, original state/ledger hashes and cursor,
all evidence hashes, deployment identity, accounting and state patch. Matching only
an event-ID prefix or a subset of payload fields is forbidden.

Any failure stops closed. The writer must not append until every earlier gate is
complete, and deployment alone does not authorize append.

## Preserved gates and forbidden substitutes

- Preserve the original Owner `APPROVE`, activation receipts, goal date, violated
  transition-start SLO, human gates and all ledger sequences 1–8.
- Do not start product Codex or Claude, manufacture model output, spend paid API
  quota, reset accounting, create a reservation, reclassify the failed attempt, or
  mark product review as passed.
- Do not weaken legacy PR #28 validation, fabricate a GitHub snapshot, or entrust
  GitHub publication credentials to the product model environment.
- Do not rebuild v5, change cross-version quota, or treat successor recovery as
  Product Goal completion.
