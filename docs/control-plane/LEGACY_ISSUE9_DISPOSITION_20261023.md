# Legacy Issue #9 / PR #29 disposition for O2 bounded trial

Status: `DISPOSITIONED_PRESERVED_OPEN_FINDINGS` for backlog admission only. This record does not close Issue #9, merge or close PR #29, mark a finding fixed, reset any budget, or authorize a Product Goal.

Disposition ID: `LEGACY-ISSUE-9-DISPOSITION`

## Exact preserved identity

- Repository: `joannalee20050914/KGnote-public`
- Issue: [#9](https://github.com/joannalee20050914/KGnote-public/issues/9), still open
- Draft PR: [#29](https://github.com/joannalee20050914/KGnote-public/pull/29), still open and currently conflicting with `main`
- Candidate HEAD: `4c11eb425f98030d6181abb74e67b0e7594d87bc`
- Candidate fingerprint: `4684cc28b9e90f1b26bcbc5364656e9978b9b60469b2b17ab3b1e3bf13a62d72`
- Round 4 canonical review: comment `6334516526`, `CHANGES_REQUIRED`
- Runtime Ledger revision after read-back/restart: `1840`

The PR #29 branch is not the base of the new O2 Goal. The new candidate must start from the then-current canonical `main`. Product code, fixtures and techniques from PR #29 may be selectively reused only after current source/version identity, tests, and exact-candidate evidence are re-established. Old commits and tests are evidence, not completion.

## Current open product obligations

The latest canonical Round 4 review leaves exactly these findings open:

1. `finding-render-click-evidence-stale-and-untracked`: the claimed render/click receipt was ignored and bound to an older parent/fingerprint; current-candidate positive/negative receipts and executable Obsidian/Web identity read-back are still required.
2. `finding-control-plane-state-stale-vs-candidate`: PLAN, STATUS and review artifacts did not bind the reviewed HEAD/fingerprint and verification facts.
3. `finding-unsupported-clause-not-gap-and-leaks-into-brief`: unsupported glossary clauses were omitted from gap handling and leaked tool-internal wording into beginner prose.

These findings become stable O2 obligations in `O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.1.json`. They are not marked fixed. Round 1–3 findings and all earlier product evidence remain immutable historical regression context; the Round 4 canonical result is the current unresolved finding set.

No product-WHAT conflict needs a new Product Owner decision. All three findings ask for behavior already required by FD-04–06/21, RC-07/08/12/14–16/31/32 and the Obsidian-first direction. Engineering may choose HOW within those constraints.

## Budget preservation

The following Legacy namespaces remain separate, sealed and non-transferable to the new Goal:

| Namespace | Preserved fact |
| --- | --- |
| D3 implementation dispatch | `3/3` used |
| Historical global Claude budget | `8/8` used |
| Issue #9 supplemental Claude reviews | `3/3` used |
| Issue #9 supplemental Codex repairs | `2/2` used |
| Original local repair | `0/1` used; not converted into new capacity |
| Completion Gate trial Codex repair | `1/1` used |
| Completion Gate Round 4 Claude attempt | `1/1` used; ended `QUOTA_BLOCKED`, zero tokens, no verdict |
| Round 4 recovery Claude grant | `1/1` used; produced canonical `CHANGES_REQUIRED` |

The old quota event, recovery event, canonical comments, checkpoint, Stop Marker and Ledger bytes remain at their original locations. A new Goal version receives only the new resource ceilings in its own append-only ledger; it does not inherit unused Legacy counters and cannot reset used counters.

## Legal continuation

`LEGACY-ISSUE-9-DISPOSITION` is satisfied for backlog selection by this explicit preservation-and-carry-forward record. It means:

- Legacy authorization is closed to new work and stays historical.
- Legacy product findings remain open as named O2 obligations.
- The new O2 version needs a new exact Owner approval bound to its spec digest.
- PR #29 remains untouched; no merge, force-push, review rewrite or budget migration occurs.

This is the minimum continuation that preserves history without requiring every old finding to be repaired before the new Goal can be authorized.
