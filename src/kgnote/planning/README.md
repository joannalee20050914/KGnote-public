# Deterministic dry-run planning v1

`kgnote.dry-run.v1` compares a successful normalization result with a caller-supplied
canonical snapshot. It is a pure preview: it does not scan, render, merge, or write a vault.

The snapshot is a list of complete `kgnote.v0.1` records and must include every Source or
other record needed to resolve references in the projected graph. Results are deterministically
sorted and copy-safe. Rejections expose stable codes and paths, not record contents in `repr`.

Operations are `CREATE`, `UNCHANGED`, `UPDATE`, `CONFLICT`, and `REJECT`. v1 permits
`UPDATE` only when a Concept adds (never removes) `evidence_ids`; accompanying
`integration_version` and `integrated_at` changes are allowed. Human review state is preserved.
All other same-ID differences are conflicts rather than silent merges.

Filesystem adapters, Markdown rendering, approval, apply, rollback, and post-apply read-back
belong to later slices.
