# Offline import pipeline

`offline_import.py` is a narrow Phase 2 orchestration boundary. It reads exactly one
caller-selected Markdown source and one caller-selected replay response, then composes
the existing importer, offline response validator, normalizer, dry-run planner, and
canonical store adapter.

`build_offline_import_preview` performs no writes. Its approval digest binds the
canonical plan, resolved store root, raw relative path, and immutable source SHA-256.
`apply_offline_import` accepts only that exact digest, creates the raw source without
overwrite, applies the canonical plan, and performs read-back. A second identical run
must produce only `UNCHANGED` operations and zero writes.

The caller must create an explicit store root containing `sources`, `concepts`,
`evidence`, `learning-events`, `edges`, and `raw` directories. This module does not scan
directories for inputs, call a provider, read credentials, create `.obsidian`, or import
private material automatically.
