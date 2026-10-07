# Incident: concentrated-trial identity drift across worktrees

Date: 2026-10-07 (Asia/Taipei)

Status: repair implemented; deterministic verification, internal review, publication, and fresh external product
review remain required before either human gate is eligible.

## What happened

After the exact external product review had passed, the pre-human handoff audit regenerated the documented
Personal Alpha trial. The source bytes matched the recorded SHA-256, but the documented workspace
`network-path-a178f811` regenerated as `network-path-45d20eb5` in the canonical review worktree.

The Personal Alpha preview derived `source_id` from the source's resolved absolute path. Repository migration and
worktree relocation therefore changed source identity, every derived record identity, and the workspace suffix even
when source bytes and the documented command were otherwise the same.

## Why safeguards did not catch it

Existing tests proved repeatability only inside one path. They covered same-input reruns, content updates,
transactional recovery, and learner-owned byte preservation, but not the same logical source checked out under two
different repository/worktree roots. Static review also checked source content and generated links without executing
the final handoff from the migrated canonical worktree.

## Impact and fail-closed response

Opening the regenerated directory would have tested a candidate whose identity did not match its durable handoff.
The prior internal and external PASS artifacts were therefore archived as historical/stale, human eligibility was
withdrawn, and no native or subjective verdict was requested from the owner.

The repair also exposed `KG-CTRL-ROUND-BUDGET-001`: this recovery PLAN and durable orchestrator state authorize eight
cycles, while the external publication marker parser and product-review schema still capped round numbers at five.
Those transport contracts are now aligned to the explicit eight-cycle envelope; the repository-wide default remains
five unless an active PLAN supplies a narrower or broader explicit bound.

## Repair and permanent invariant

Portable review/handoff candidates now bind source identity to an explicit namespaced stable external source key.
The immutable source SHA-256 remains independent and continues to detect byte changes. Local workflows that omit a
key retain canonical-path identity but cannot claim cross-worktree portability.

Permanent invariant: a documented portable candidate must regenerate the same source ID, workspace suffix, and
artifact digests from the same source bytes and stable source key regardless of repository/worktree root. Its exact
handoff path must match generator read-back before a human gate becomes eligible.

## Regression coverage

- preview tests compare two distinct machine paths with and without the same explicit source key;
- invalid unscoped and file-path keys fail closed;
- native CLI tests materialize from two simulated worktrees and require an identical workspace name plus successful
  read-back;
- the real canonical and archival worktree source paths are exercised with the same key and must emit
  `network-path-8f242796` with identical canonical and Markdown digests.
- publication accepts the configured last round, rejects a round outside the configured envelope, and removes stale
  request markers independently of the current maximum.

Durable run evidence: `docs/requirements/evidence/personal-alpha-portability-repair-20261007.json`.
