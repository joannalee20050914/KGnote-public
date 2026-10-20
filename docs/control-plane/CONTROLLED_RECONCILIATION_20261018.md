# KGnote Controlled Reconciliation and Resume Authority

Status: `APPROVED` by the product owner on 2026-10-18. This record extends the existing goal `GOAL-KGNOTE-D2-T01-SOURCE-LIBRARY-V1`; it does not create a new goal or replace historical review evidence.

The owner authorizes preservation and controlled adoption of the uncommitted Issue #8 `finding-r-004` repair left after External Round 6, plus the minimum control-plane work required to reconcile PLAN, STATUS, the work-package envelope, budget counters, checkpoint identity, and preflight. The historical sealed candidate remains HEAD `53c71a81a7c1a1483c7490f652007e5db1c7b6a5`, fingerprint `ae69844871ccb00f1d2058107d0008d78b86cf206e75e0dde49770e0c25ab7b7`, with External Round 6 `CHANGES_REQUIRED`; its result must not be rebound to later bytes.

The additive Issue #8 work-package limits are three further local repairs, three internal independent reviews through Cycle 22, and two external Work reviews through Round 8. Historical usage is preserved: local repair 3, internal review 19, external review 6. A started review context consumes one unit. Two consecutive rounds without material progress stop the package. These limits do not authorize paid API use, protected-branch writes, force push, modification or merge of PR #1, PR #22, or `main`, or promotion of PA-HUMAN-1, NS-HUMAN-SMOKE, or `release_verified`.

Before Runner restoration, the existing control plane must prevent an Implementer launch when the required downstream external-review budget is exhausted, even if local or internal capacity remains. The repair must cover CHANGES_REQUIRED routing, restart/duplicate wake, scheduler resume, exact launch counts, isolation of independent packages, and a valid fully-authorized path.

Reconciliation must preserve an exact dirty-worktree snapshot and hashes, use a path-explicit checkpoint commit, compute a new candidate identity, run deterministic verification/read-back/preflight, and retain `AUTOMATION_BLOCKED` until all restoration conditions pass. It may not rewrite old review results or sealed manifests, copy a fingerprint merely to silence preflight, or activate the Runner before preflight passes.

The durable receipt for this authorization and its evidence is `docs/control-plane/CONTROLLED_RECONCILIATION_RECEIPT_20261018.md`.
