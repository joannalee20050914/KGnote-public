# Safe Reader application boundary v1

`load_reader(explicit_root, query)` reads only a Source already registered in a validated
canonical store. Callers provide `source_id`, the exact Graph Read Model snapshot digest, and an
optional `line_range` locator. They never provide a filesystem path.

The adapter resolves the registered `uri_or_path` beneath the explicit store root, requires a
regular non-symlink Markdown file under `raw/`, verifies its exact SHA-256 against the Source
record, and decodes strict UTF-8. Absolute paths, `..`, backslashes, symlinked path components,
non-Markdown files, stale snapshots, oversized sources, and out-of-range locators fail closed.

A ready result includes the exact source text, its byte and line counts, an exact focus excerpt,
and overlapping Evidence annotations with stable Concept/Edge IDs. It never returns
`uri_or_path`, the store root, or another local path. Reading or focusing does not create a
LearningEvent and does not imply understanding.

Both ready and rejected results carry the fixed no-store and browser security-header policy for
a future HTTP adapter. This boundary may read the explicit store and registered raw file; it does
not write, call a network/model API, inspect ambient configuration, launch UI, or use a clock.
