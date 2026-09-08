# ADR-0002: Obsidian display labels remain a renderer-owned read model

Status: accepted for Issue #12 implementation and visual validation

## Observed problem

Phase 0, Issue #10, and Issue #11 kept every canonical filename equal to its stable record ID.
This produced correct links, deterministic read-back, zero duplicate basenames, and idempotent
apply. In the 24-node Issue #11 global graph, full SHA labels overlapped slightly even though the
graph remained connected and usable.

## Options considered

1. **Front matter/heading only.** Existing Concept `canonical_name`, Source `title`, generated
   headings, and Concept aliases are already human-readable. They help note reading and search,
   but do not replace stable filenames as graph node identity.
2. **Stable targets with aliased wiki-link text.** `[[stable-id|Human label]]` keeps resolution
   deterministic while making generated note bodies, backlinks, and navigation understandable.
3. **Human-readable filenames.** This gives graph nodes readable filenames but requires collision,
   rename, migration, and external-link policies, and breaks the v1 reader invariant that
   `filename == record ID`.

## Decision

Keep stable IDs as canonical filenames and link targets. Add only renderer-owned aliased link text
for newly created Markdown bodies. Derive labels from existing canonical fields, remove wiki-link
control characters, cap their length, and append an eight-character stable-ID fragment when labels
collide. Do not add an extraction or canonical-schema field.

This is intentionally a partial usability improvement. Obsidian global graph labels that continue
to use filenames remain long; KGnote will solve that at the Phase 3 read-model boundary if the
problem becomes material. Existing files are not renamed or migrated, and UPDATE continues to
preserve human Markdown bodies byte-for-byte.

## Consequences

- Identity, provenance, deterministic normalization, and idempotent apply remain unchanged.
- Link text becomes readable without making display text authoritative.
- Display-label collisions are harmless and visibly disambiguated.
- Malformed label characters cannot inject or terminate a wiki link.
- A fresh disposable Obsidian artifact must confirm actual global/local graph, backlink, link-text,
  quick-switcher, and note-title behavior before Issue #12 closes.
