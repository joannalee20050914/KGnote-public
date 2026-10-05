> **HISTORICAL EVIDENCE：**2026-09-20 Web beta 的 point-in-time review；不是目前 execution plan 或最新 verifier evidence。

# Mutation thought experiment · 2026-09-20

These mutations target semantic substitutions that could leave ordinary happy-path tests green.

| # | Deliberate mutation | Scenario expected to catch it | Protection/result |
|---:|---|---|---|
| 1 | Treat zero notes as “not started” and block activities | SC-01 | read-first UI and zero-note HTTP/browser path; protected |
| 2 | Count a Soak card as an incorrect Attempt | SC-02, SC-18, SC-24 | typed exposure schema forbids outcome/attempt fields; protected |
| 3 | Resume only the unit, not the exact breadcrumb/question | SC-03 | catalog + browser exact-resume journey; protected |
| 4 | Add DMA to a glossary merely because it is a Concept | SC-05 | explicit negative assertion in `learn-workspace.test.js`; protected |
| 5 | Flatten hierarchy into groups or canonical edges | SC-07, SC-08, SC-09 | recursive structure and cross-view identity tests; protected |
| 6 | Make `PID=define` or `Process=apply` a global Concept property | SC-11, SC-12 | context-local dual-depth test; protected |
| 7 | Embed answer/Evidence in the Practice document before submit | SC-19 | isolated document/source assertions and real browser journey; protected |
| 8 | Overwrite the first wrong answer with its corrected retry | SC-20, SC-22 | immutable identity/conflict tests and browser wrong→correct history; protected |
| 9 | Let a missing Gloss/Structure make Source unreadable | SC-30 | explicit degraded-catalog regression; protected |
| 10 | Treat natural exposure as successful retrieval for scheduling | SC-24 | Due projection consumes the signal but asserts `counts_as_retrieval_success=false` and leaves milestone/outcome unchanged; protected |

This is a mutation review, not a mutation-testing score: only the cited executable tests count as verification.
