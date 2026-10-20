# Learner-facing Markdown projection contract

Status: accepted projection contract for `GOAL-OBSIDIAN-LEARNER-PROJECTION-AND-NATIVE-SPIKE-V3`
Baseline: `kgnote-reconciliation-2026-09-23-r5`
Applies to: Personal Alpha ordinary-Markdown workspaces and the later optional native Canvas projection

## Boundary

The existing preview payload remains the canonical input for this slice. The repair adds a pure,
deterministic learner projection between that payload and Markdown serialization. It must not rewrite Source,
Evidence, Concept/relation identity, review state, or extraction semantics. Renderer polish is downstream of
the information hierarchy and cannot substitute for it.

```text
immutable Markdown source
  → deterministic Personal Alpha preview / canonical candidate records
  → pure learner projection (this contract)
  → ordinary Markdown renderer
  → optional JSON Canvas navigation using the same projected files
```

## Four information layers

| Layer | Purpose | Default presentation | Examples |
| --- | --- | --- | --- |
| Primary | Help the learner understand and start | Visible in reading order | lesson summary, focus question, mental model/path, concept explanation, readable proposition, next step |
| Secondary | Help navigation without interrupting reading | Visible but visually subordinate | Start reading, key concept links, related concepts, inline outline, My Notes, Continue Here |
| On-demand | Support trust, uncertainty, and source checking | Collapsed callout or explicit audit link | exact excerpt, Source locator, unresolved relation explanation, preserved immutable source |
| Debug-only | Support deterministic engineering and review | YAML/frontmatter, manifest, or clearly collapsed technical details | stable IDs, SHA-256, schema/extractor version, signals, counts, confidence, internal review status |

Primary and debug-only material must never be presented as peer sections. `candidate`, `unreviewed`, extractor
signals, mention counts, record IDs, hashes, and confidence values are forbidden in the primary reading flow.
This restriction changes presentation only; the underlying values remain preserved and auditable.

## Start Here

Within the first screenful, `Start Here.md` answers:

1. What is this lesson about?
2. What question or mental model should guide reading?
3. Where should I start?
4. Which few concepts or relationships are worth noticing?
5. Where can I write or resume my own thinking?

Required section order is title and source-grounded lesson summary; `Learning goal` question callout;
`Learning path`; `Start reading`; `Key concepts`; `Key relationships`; `Continue`; `My notes`; and a
collapsed `KGnote details` callout. System counts and provenance prose are not primary sections. Evidence and
Structure are not numbered mandatory learning steps for a short source. Uncertainty and provenance are
available only on demand and through the immutable Source link.

## Adaptive structure

Structure is navigation, never canonical knowledge.

- Heading-free material receives no invented hierarchy. Start Here links directly to the immutable source.
- A short/shallow source shows its source-supported outline inline on Start Here. `Structure.md` may remain as
  a fallback artifact, but is not a required primary learning step. The implementation may use a deterministic
  bounded heuristic, but that heuristic cannot replace the observable Golden behavior.
- A longer/deeper source gets a compact inline preview plus a prominent link to `Structure.md`.
- Heading titles and parentage are copied from the source. The projection does not infer causality, taxonomy,
  or prerequisite relations from heading nesting.

## Concept projection

Each Concept note uses this fixed learner-first order:

1. title and a short source-grounded explanation of the term, including a plain limitation when no broader
   standalone definition is supported;
2. `In this material`, derived only from explicit definition/relation/co-mention wording;
3. `Related concepts` with readable source-grounded role phrases;
4. a collapsed `Source evidence` callout containing deduplicated excerpt(s) and a Source link;
5. a collapsed `KGnote details` block for the smallest useful review/debug note;
6. links back to the Concept index and Start Here.

When the source does not define a term, the note says what the source explicitly does with it rather than
inventing a general definition. Co-mention remains plainly unresolved and never becomes a precise fact.

## Relationship and Evidence projection

`Relationships.md` is titled `Key relationships` and leads with complete readable propositions. Precise
relations and unresolved associations remain distinguishable in ordinary language; an unresolved co-mention
explicitly says the source does not establish a more precise relationship. Status, confidence, rationale codes,
IDs, and raw bookkeeping do not appear in the primary flow.

Evidence excerpts are grouped by normalized `(source_id, locator, excerpt)` so the same line is quoted once
even when it supports multiple mentions and a relation. The grouped item may list the learner-facing claims it
supports. Exact IDs, kinds, review status, and extractor details remain in collapsed technical details or the
manifest. `Evidence.md` is an audit destination, not a mandatory step in the normal learning path.

## Projected filenames

- Concept filenames use a sanitized human-readable label, for example `Concepts/IP address.md`.
- Stable IDs remain in frontmatter and the manifest, not in the ordinary filename.
- Path separators, control characters, platform-reserved punctuation, terminal spaces/dots, and `.`/`..` are
  made safe deterministically.
- Comparisons use Unicode NFKC plus case folding. Only actual collisions receive a bounded deterministic suffix
  derived from the stable ID. Non-colliding labels never receive an ID/hash suffix.
- All emitted wikilinks use the resolved projected paths; rerunning the same payload yields identical paths.

## Pure-Markdown continuation

`Continue Here.md` is user-owned, alongside `My Notes.md`. KGnote creates a starter only when the file does
not exist and never manages or overwrites it afterward. The starter explains the manual close/reopen path and
provides `Resume link`, `Current note`, `Current section`, `Next`, and `Question to revisit` fields. `Resume
link` must be an ordinary Obsidian link to an exact heading or block, and its note/anchor must agree with the
two descriptive fields. An empty starter is not a recorded continuation. The file makes no claim that KGnote
observed reading, understanding, completion, recency, clicks, or time. A same-input rerun or source update
preserves its bytes exactly.

Evidence line ranges identify exact bytes in the preserved source, but Obsidian does not treat a line range as
a native link anchor. When a unique enclosing source heading exists, generated Evidence links open that
heading and say that the line range locates the exact excerpt within it. Otherwise the link is explicitly
document-only and the learner uses the line range manually. KGnote does not add block IDs to the immutable
source or describe a document link as exact-line navigation.

## Projection interface and invariants

The projection function accepts only the canonical preview mapping and returns an immutable/serializable view
model. It performs no filesystem or network I/O. The Markdown renderer consumes the view model rather than
re-deriving presentation decisions independently.

Required invariants:

- identical input produces byte-equivalent serialized projection and Markdown;
- canonical source, Concept, relation, and Evidence IDs/digests are preserved;
- every projected link resolves after materialization;
- a filled manual continuation resolves to the recorded note heading/block after reopen, while an empty
  starter, mismatched fields, or stale anchor is rejected as a completed continuation;
- Source bytes remain exact;
- My Notes and Continue Here remain user-owned across updates;
- a locally edited managed file still fails closed;
- short, heading-free, and procedural fixtures retain materially different navigation;
- primary content remains meaningful after frontmatter and collapsed audit/debug sections are removed;
- no test promotes `PA-HUMAN-1`, mobile acceptance, release verification, or learning effectiveness.

## Regression inventory (PA-4 candidate)

| Artifact | Observed regression | Cause in current renderer | Required repair |
| --- | --- | --- | --- |
| `Start Here.md` | Behaves as an index/debug report; counts and review warnings compete with the lesson | `_render_entry` puts a five-page system itinerary, counts, uncertainty, and provenance in the main flow | Lead with summary/focus/path/start; demote audit data; inline short outline |
| `Structure.md` | Four-heading material becomes a mandatory extra page | Structure record existence is treated as a required learning step | Apply the documented short/shallow heuristic; keep separate page only as fallback or long-source navigation |
| `Concepts/Index.md` | Names “candidates” and counts mentions instead of teaching | `_render_concept_index` renders extraction status | Show concept label plus short source-grounded role; keep status in metadata |
| Concept notes | Start with warning, signals, counts, and raw evidence | `_render_concept` mirrors extraction records rather than learner semantics | Explain what/role/related first; evidence collapsed; debug metadata hidden |
| `Relationships.md` | Readable proposition exists but is followed by status/confidence/rationale and duplicated quote | `_render_relationships` treats audit fields as peer content | Proposition first; concise unresolved wording; one collapsed evidence group |
| `Evidence.md` | Same source line is repeated once per mention and relation record | `_render_evidence` serializes records one-by-one | Group identical source spans/excerpts and preserve record IDs in debug details |
| Concept filenames | Hash suffixes dominate visible filenames | preview `planned_artifacts` is reused as user-facing path authority | Resolve readable projected names in the learner projection with collision-only suffixes |
| `My Notes.md` | Safe and preserved, but no explicit continuation affordance exists | only one user-owned path is modeled | Preserve My Notes and add separately user-owned `Continue Here.md` |

The inspected PA-4 artifacts were the networking workspace under
`output/personal-alpha/pa4-vault/KGnote Alpha/network-path-a178f811/`. The other two fixtures are required in
LP-8 so the repair cannot overfit this example.

## V3 Golden authority

The hand-authored Golden fixtures for network-path Start Here, Port, and Relationships are test oracles. Their
section order and learner-facing terminology are authoritative and are not generated by production code.
Semantic tests must first show the old renderer RED, then the production projection/renderer must make them
GREEN. Code-level tests do not replace re-reading the generated Markdown bytes.
