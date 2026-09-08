# Canonical Markdown store v1

`kgnote.canonical-store.v1` is the first explicit filesystem boundary. It reads only the five
canonical directories below an explicit root, rejects symlinks/path escapes, and preserves each
document's original bytes and Markdown body separately from typed front matter.

Apply requires a SHA-256 approval digest for the exact dry-run plan, rejects blocking operations,
checks file-content preconditions, and validates projected references before writing. CREATE and
the narrowly allowlisted Concept provenance UPDATE use same-directory atomic replacement; UPDATE
also creates a recoverable `.kgnote-backups/<plan-digest>/` copy. Apply then re-reads and compares
the complete projected snapshot. No delete, rename, merge, schema migration, directory watching,
model call, or Git operation belongs to this adapter.

Canonical filenames and wiki-link targets remain full stable record IDs. For newly created notes,
the Markdown body adds a renderer-owned human label (`[[stable-id|Human label]]`) derived from
existing canonical fields. Duplicate labels receive an eight-character ID disambiguator, and
wiki-link control characters are removed. These labels improve in-note navigation only: they are
not identity, are not written into the canonical schema, and do not rename files. Existing human
bodies remain byte-preserved on update.
