# Control-plane baseline waivers

This register contains exact, one-time acceptance exceptions for immutable baselines. It is not a verifier ignore list.

## CP0-W001 — approved pre-control-plane EOF whitespace

| Field | Bound value |
|---|---|
| Scope | CP-0 checkpoint acceptance only |
| Checkpoint commit | `47269690f3d389f6ce2ddf43a79b1e7e7f6324e2` |
| Approved manifest SHA-256 | `5a4c89a5d313e5255f2f95506803f46fee221a1b5a532ddeb43c9a9b42fcf809` |
| Path | `docs/requirements/REQUIREMENTS_TRACE.md` |
| Finding | Existing blank line at EOF reported by `git diff --check` |
| Purpose | Preserve the exact approved pre-control-plane repository snapshot |
| User decision | Approved 2026-09-22 as a precise, one-time baseline waiver |

Rules:

- The checkpoint bytes and manifest are immutable and were not represented as having passed strict `git diff --check`.
- The waiver covers no other path, line, whitespace finding, commit, or verification run.
- The defect is removed in the first normal tracked control-plane change by correcting the deterministic requirements renderer and regenerating the view.
- `scripts/codex_verify.sh` has no waiver mechanism for this finding. All post-checkpoint verification requires strict whitespace success.
