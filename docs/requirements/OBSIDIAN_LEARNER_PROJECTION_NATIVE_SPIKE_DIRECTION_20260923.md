# Obsidian learner projection and native spike V3 direction

Status: accepted implementation direction, 2026-09-23
Speaker: product owner
Goal: `GOAL-OBSIDIAN-LEARNER-PROJECTION-AND-NATIVE-SPIKE-V3`

## Reproducible source

- Attachment: `local-source-withheld`
- SHA-256: `e09e92014f60d2c7b208bf50acfb21212117f65e5a4122c9f847f7a32dc4914e`
- Size: 27,184 bytes; 1,276 lines
- Product-design authority and recovery: `L1-L239`
- Four-layer hierarchy and Golden artifacts: `L241-L507`
- continuation, projected vault, Golden-first sequence, and read-back: `L509-L900`
- Phase A gate, native spike, Canvas validator, and final boundary: `L901-L1276`

## Replacement checkpoint

This direction replaces V2 before renderer implementation. The V2 checkpoint fingerprint is
`b8d4ca72461639f16e4f75d10ea0eb502086b300c97c579571d239845c4c7b57`.

V2 completed `LP-0`: it recorded the source-grounded regression inventory, pure projection boundary,
four-layer information hierarchy, adaptive short-source rule, collision-safe filename requirement, and
user-owned continuation invariant. Its changed paths were `PLAN.md`, `CODEX_STATUS.md`, this direction
record, and `docs/obsidian/LEARNER_PROJECTION_CONTRACT.md`. No Golden fixture, semantic test, production
renderer change, repaired candidate, Canvas implementation, or native validator had started.

V2 is `superseded_by_explicit_presentation_spec`. Its compatible analysis is retained; any learner-facing
shape that conflicts with the concrete V3 Golden artifacts is not retained.

## Authoritative product-design boundary

This is implementation-directed. The attachment fixes the learner-facing information architecture, hierarchy,
section order, terminology, progressive disclosure, debug/provenance visibility, short-source behavior,
Concept/Relationship/Evidence presentation, continuation semantics, Canvas role, and Golden artifact shape.
Implementation may choose deterministic decomposition, serialization, safe filesystem handling, collision
handling, and test strategy only when observable learner-facing behavior stays the same.

The concrete Golden artifacts outrank a more generic, extensible, canonical-schema-shaped, or easier-to-test
presentation. If a Golden requirement truly conflicts with an accepted safety or data contract, execution
fails closed and records the exact conflict rather than inventing substitute UX.

## Required architecture

```text
canonical / reviewed records
  → pure deterministic learner-facing projection
  → Obsidian Markdown renderer
  → optional Canvas augmentation
```

Canonical Source, Concept, Evidence, extraction, normalization, graph semantics, and review-ledger identity
remain unchanged unless an actual contract violation is found. Canonical record fields must not be dumped
one-for-one into learner Markdown.

## Learner-facing hierarchy

1. Primary: lesson title/summary, learning goal, learning path, Concept explanation and role, readable Teaching
   Proposition, and recommended next action.
2. Secondary: related Concepts, source navigation, optional extended structure, My Notes, human-readable
   unresolved warning, and Continue Here.
3. On demand: exact Evidence, source locator, and interpretation-relevant uncertainty in native collapsed
   callouts.
4. Debug/provenance: stable/candidate/source/evidence IDs, schema, SHA, extractor/projection versions,
   confidence, signals, counts, record type, and machine status only in frontmatter, `.kgnote/`, or collapsed
   `KGnote details`.

Debug fields never compete with learning prose.

## Fixed presentation

- `Start Here.md` is a learning entry in this order: title and source-grounded summary; `Learning goal`
  callout; `Learning path`; source-reading action; `Key concepts`; `Key relationships`; `Continue`;
  `My notes`; collapsed `KGnote details`. It does not lead with counts, provenance, review status, or
  mandatory Evidence/Structure steps.
- A Concept note starts with what the Concept means in this material, plainly states when no broader definition
  is supported, then shows `In this material`, `Related concepts`, collapsed `Source evidence`, collapsed
  `KGnote details`, and navigation. `Why it is included`, `Signals`, `Marked mentions`, and
  `Unreviewed concept candidate` are forbidden primary sections.
- `Relationships.md` is titled `Key relationships`, leads with learner-readable propositions, expresses an
  unresolved co-mention in ordinary language, and keeps Evidence collapsed. Raw enums, confidence, rationale
  codes, Evidence IDs, and candidate reasons are not primary content.
- `Evidence.md`, if present, is a reference destination rather than a numbered mandatory step. Same
  `(source_id, locator, excerpt)` evidence is grouped deterministically for learners without merging or
  deleting canonical Evidence records.
- `Concepts/Index.md` is titled `Key concepts` and lists a concept with a source-grounded role, not mention
  counts or review bookkeeping.

Dynamic prose must be supported by Source or an accepted projection. The renderer shortens unsupported
summaries and never adds general domain knowledge merely to fill the template.

## Structure, paths, and user-owned notes

- Structure is source navigation, not ontology. Short sources inline the outline on Start Here and may retain
  `Structure.md` only as reference; larger hierarchical sources may use it as extended navigation.
  Heading-free sources gain no invented hierarchy. Procedural order is not promoted to canonical causality.
- Concept filenames are human-readable. Unicode normalization, illegal/reserved names, duplicate labels,
  case-fold collisions, and stable regeneration are handled deterministically; only a real collision gets a
  bounded disambiguator. Stable IDs stay in metadata.
- `Continue Here.md` and `My Notes.md` are user-owned. Continue Here is created only when missing with
  `Current note`, `Current section`, `Next`, and `Question to revisit`; regeneration preserves its bytes
  and never infers progress from clicks, time, or file opens.

## Golden-first and verification order

1. Save independent hand-authored Start Here, Port, and Relationships Golden fixtures.
2. Add semantic tests and demonstrate at least one RED failure against the old renderer.
3. Implement the pure projection and renderer until those tests are GREEN.
4. Generate the network-path workspace, re-read actual Markdown bytes, reject all named bad primary patterns,
   and require all named learner patterns.
5. Run hierarchical, heading-free glossary, and procedural fixtures through the same command; verify
   deterministic/idempotent output, readable paths, collision behavior, Source/Evidence read-back, metadata
   separation, and preservation of user-owned notes.
6. Only after the complete Phase A gate, resume the retained native capability spike.

## Native spike boundary

Canvas is optional secondary navigation over an already useful Markdown workspace. It cannot replace Start
Here, Source, Concept notes, or Relationships; cannot turn layout/grouping/headings into canonical relations;
and cannot change Source, Concept, Evidence, or canonical relation identity. The three fixtures must prove a
real source-supported three-level hierarchy where available, at least two organization-edge types, no invented
glossary hierarchy, and no procedural causality promotion.

The semantic validator covers deterministic JSON/IDs/coordinates/serialization, endpoint and file resolution,
heading/block anchors, fallback Markdown, Canvas on/off identity, reruns, user collisions, unsafe paths,
symlink escape, malformed/dangling/stale data, and injected-write recovery.

The final technical decision is exactly `native_sufficient_for_next_reading_slice` or
`native_insufficient_with_bounded_gaps`. The latter names the exact gap, evidence, and smallest next
adapter/plugin proposal without installing or building that plugin in this goal.

## Human and release boundary

`PA-HUMAN-1` remains `pending_human_review` throughout automated work. Automated results cannot claim
usability, mobile acceptance, learning effectiveness, or release verification. `release_verified=false`.
The final handoff gives product owner exact Start Here, Port, Relationships, and Canvas paths plus the nine learner-UX
smoke questions from the source attachment.

## Prohibitions

- No third-party plugin installation or modification.
- No formal/private-vault scan or write.
- No live AI/API, paid provider use, or external source transmission.
- No Web replacement UI, RAG, scheduling, forgetting curve, full Practice, Knowledge Roaming, voice, LINE/LIFF,
  graph database migration, destructive migration, or public deployment.
- No commit, push, merge, stash, reset, clean, or force checkout.
