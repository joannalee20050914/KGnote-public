# KGnote repository authority map

Status: active control-plane policy. This file separates product truth from execution control; it does not create or weaken product requirements.

## Product authority

Product authority is evaluated in this order for locating the current source, but conflicts among the first three layers are never silently resolved by precedence:

1. Current explicit user product decisions, durably recorded in `docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md`, `docs/requirements/USER_DIRECTION_DELTA_20260922.md`, `docs/requirements/PERSONAL_ALPHA_DIRECTION_20260922.md`, `docs/requirements/PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md`, `docs/requirements/OBSIDIAN_LEARNER_PROJECTION_NATIVE_SPIKE_DIRECTION_20260923.md`, or a later approved decision record.
2. Requirements/scenarios/sources SSOT: `docs/requirements/requirements.json`, `scenarios.json`, and `sources.json`.
3. Active product and data contracts: `docs/PRODUCT_CONTRACT.md`, `docs/DATA_MODEL.md`, and `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`.
4. Active delivery ordering: root `DEVELOPMENT_PLAIN.md`.
5. Historical or superseded provenance.

The active product direction ID is `kgnote-obsidian-first-2026-09-22`. Knowledge-graph-first describes the data-integration model; Obsidian-first describes the daily product surface and delivery order. They are complementary, not competing UI directions.

If a current user decision, the requirements SSOT, or an active contract disagree, the state is `authority_drift`. Preflight must fail closed and request reconciliation. It must not pick a winner by precedence or infer that an older unmet checkbox is current scope.

## Execution authority

Execution authority is separate from product authority:

1. Safety, privacy, data-consent, and destructive-operation constraints.
2. Current explicit user execution instructions.
3. Root `AGENTS.md` and any applicable scoped agent instructions.
4. The single active goal in root `PLAN.md`.
5. Factual checkpoint and handoff state in root `CODEX_STATUS.md`.

Execution documents may govern how Codex works, verifies, advances, or stops. They may not override, weaken, or silently reinterpret product requirements.

## Document roles

| Document | Role | Authority status |
|---|---|---|
| `docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md` | Current integrated Personal Alpha stage, concentrated-human-review policy, and partial-feedback boundary | active |
| `docs/requirements/USER_DIRECTION_DELTA_20260922.md` | Current explicit product decision record | active |
| `docs/requirements/PERSONAL_ALPHA_DIRECTION_20260922.md` | Current explicit Personal Alpha product and delivery decision | active |
| `docs/requirements/PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md` | Current Personal Alpha human result and native-spike interruption boundary | active |
| `docs/requirements/OBSIDIAN_LEARNER_PROJECTION_NATIVE_SPIKE_DIRECTION_20260923.md` | Current Golden learner-projection specification and bounded native-spike direction | active |
| `docs/requirements/{requirements,scenarios,sources}.json` | Machine-readable product SSOT | active |
| `docs/PRODUCT_CONTRACT.md` | Product contract, with 2026-09-22 amendment | active |
| `docs/DATA_MODEL.md` | Data contract; old phase labels are historical sequencing | active |
| `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md` | Cross-representation semantic contract, renderer-agnostic after amendment | active |
| `DEVELOPMENT_PLAIN.md` | Active roadmap and next product slice | active, not requirements SSOT |
| `docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md` | Canonical/archival repository identity and migration boundary | active execution authority |
| `docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md` | Internal→publication→external-review→human gate ordering and repository identity invariants | active execution authority |
| `docs/control-plane/INCIDENT_EXTERNAL_REVIEW_BYPASS_20261007.md` | Durable incident analysis and regression lessons | active corrective evidence |
| `README.md` | Orientation only | informative |
| `docs/DEVELOPMENT_PLAIN_SUPERSEDED_20260922.md` | Prior roadmap | historical provenance |
| `docs/chatgpt_6pro_20260919_review.txt` | Historical AI review | historical provenance |
| `docs/requirements/CODEX_INTEGRATION_PROMPT.md` | Consumed integration prompt | historical provenance |
| `docs/requirements/{ARCHITECTURE_AUDIT,FAILURE_MATRIX,MUTATION_REVIEW}.md` | Dated Web-beta evidence | historical provenance |
| `docs/requirements/MANIFEST.json` | Imported candidate-bundle snapshot | historical provenance |
| `docs/requirements/TOOL_VALIDATION.txt` | Dated validation transcript | historical provenance |

Historical provenance may support why a decision was made or what was once verified. Its incomplete work, imperative wording, or status claims never become current scope without a new explicit decision and SSOT update.

## Drift control

`docs/control-plane/authority-lock.json` binds the exact active authority files after reconciliation. Any byte change to a locked file without a matching deliberate lock update is authority drift. Updating the lock is evidence that reconciliation was performed; it is not proof that a product change was approved.

Preflight also requires every locked active product document to declare the same direction ID through the lock metadata. A hash match, schema pass, or clean Git status cannot resolve a semantic conflict reported by a human or an explicit decision record.
