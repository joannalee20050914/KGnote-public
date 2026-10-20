> **HISTORICAL EVIDENCE：**2026-09-20 Web beta 的 point-in-time audit；不是現行 product direction、roadmap 或 current verification result。

# Architecture audit · 2026-09-20

Scope: the local, data-driven beta represented by `web/fixtures/learning-units.json`. This is an engineering audit, not a claim that all requirements or learning outcomes pass.

## Boundary map

| Boundary | Canonical input / output | Mutation authority | Audit result |
|---|---|---|---|
| Source ingestion | immutable source bytes + hash | import adapters only | Reader projections do not rewrite source |
| Concept / Claim / Evidence | versioned guided-map model | reviewed pipeline | structure/grouping cannot create canonical edges |
| Learning Structure | recursive view projection | fixture/import projection | failure now falls back to one source-scoped root |
| Context Gloss | contextual supplement with provenance | fixture/import projection | failure now becomes an empty optional assist; Source remains readable |
| Practice | reviewed claim + server-built item | user starts an Attempt | answer/Evidence withheld until submission |
| Soak / natural exposure | typed non-assessment event | user presentation/reveal/skip/encounter | never writes Attempt, outcome, score, or due item |
| Attempt / feedback | immutable submitted response + append-only assessment | learner action | stable client identity, conflict instead of overwrite |
| Due Queue | projection from submitted Attempt + feedback | explicit schedule/action | due identity is separate; voluntary retry does not advance it |
| Exact continuation | append-only source scope/breadcrumb/selection/question | navigation or explicit save | latest exact context, not merely recent-card history |

## Genericity and semantic checks

- The Reader, Practice, Soak, continuation, and catalog code contain no OS- or BitePacer-specific control branch. Unit-specific meaning stays in fixtures. The current catalog has two real fixtures; arbitrary live import and a third independently authored fixture remain unverified.
- View hierarchy uses `parent_id` and `organizing_relation`; it is not copied into canonical propositions. Flat Guided Map groups remain a separate projection.
- Concept identity is stable across Source, Map, Graph, and activities. Learner-facing wording may paraphrase reviewed propositions; equivalence is not implemented as exact-string matching.
- `related_to` remains an unresolved/general relation and is not promoted to a causal edge by structure or renderer code.
- A Context Gloss carries its own locator and suggested depth. `glossesForScope` selects it by the current source range; the Concept object is not assigned a global `required_depth`.

## Reliability findings and disposition

| Severity | Finding | Disposition |
|---|---|---|
| P1 fixed | Missing/invalid Learning Structure or Reading Assist rejected the whole unit, coupling optional projections to Reader availability. | Catalog now emits explicit `degradations`, a source-only structure fallback, and empty optional assist. Regression: `test_structure_and_context_gloss_projection_failures_do_not_block_source_reader`. |
| P1 fixed | Concurrent first writes with the same append-only ID could both pass the existence check and replace each other. | Attempt, feedback, due, exposure, and exact-continuation mutators are serialized within the local server process; affected atomic replaces fsync the parent directory. Concurrency regressions cover same-ID and multi-event writers. |
| P1 fixed | Context depth had only one fixture value, so it did not prove context locality. | SC-12 now exercises the same Concept at `define` and `apply` depths in separate source scopes and verifies no Concept-level depth is created. |
| P1 fixed | Natural exposure was typed separately, but the Due scheduler could not see it. | Due projection now exposes a traceable `exposure_signal` and only recommends manual snooze/changed-context; it never advances or scores retrieval. |
| P1 fixed | Prior-knowledge display depended only on a reviewed synthetic link. | Reader projection now derives `prior_encounters` only from real events in another unit with the same Concept identity. Concept existence alone produces nothing. |
| P1 fixed | A concrete confusion could be displayed but did not alter the next review shape. | Explicit confusion evidence now produces a distinction prompt; ordinary co-occurrence does not, and source history is not mutated. |
| P2 deferred | The checked-in catalog has two authored units; a third synthetic unit passes the same renderer, but live arbitrary-source import has not passed all UI journeys. | `SC-31` is `automated_partial`; no claim of arbitrary-material support. |

There are no known in-scope P0/P1 findings after the third audit pass. Remaining partial items are explicitly deferred capability breadth or manual learning judgments, not known data-loss, attribution, answer-isolation, or core-flow defects.
