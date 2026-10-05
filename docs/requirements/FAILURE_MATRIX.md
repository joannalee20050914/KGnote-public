> **HISTORICAL EVIDENCE：**2026-09-20 Web beta 的 point-in-time matrix；其 `pass` 欄不代表目前 release gate 已執行。

# Failure-injection matrix · 2026-09-20

| Injected failure | Required unaffected path | Expected behavior | Executable evidence | Result |
|---|---|---|---|---|
| Learning Structure missing/invalid | Source Reader | Load source through a one-root fallback; report degradation | `tests/test_learning_catalog.py` | pass |
| Context Gloss missing/invalid | Source + Learning Structure | Empty optional assist; no invented definition | `tests/test_learning_catalog.py` | pass |
| Prior Knowledge malformed | Context Gloss + Source | Drop only prior links; preserve contextual explanation | `tests/test_learning_catalog.py` | pass |
| disputed Claim | Source Reader + safe claims | Preserve disputed source with warning; exclude it from teaching answer | `web/tests/learn-workspace.test.js`, `tests/test_practice_http.py` | pass |
| missing Evidence / stale Claim revision | safe Practice items | reject malformed/stale item; do not reveal or submit against it | `tests/test_practice_planner.py`, `tests/test_practice_http.py` | pass |
| submitted Attempt response lost, same payload retried | Attempt history | one immutable record; retry is unchanged | `tests/test_attempt_store.py` | pass |
| same Attempt ID with changed answer | original Attempt | conflict; original answer read back | `tests/test_attempt_store.py` | pass |
| concurrent append-only writers | existing/new event histories | no silent overwrite or lost event in local server process | `tests/test_attempt_store.py`, `tests/test_feedback_scheduling.py`, `tests/test_exposure_store.py`, `tests/test_resume_context.py` | pass |
| corrupt Exposure/Resume/Due record | immutable Source and unrelated stores | affected endpoint fails closed; source bytes not mutated; corrupt Due does not hide Attempt history | store tests + `tests/test_feedback_scheduling.py` | pass |
| Soak presentation/reveal/skip | Attempt and Due Queue | no Attempt/outcome/debt created | `tests/test_exposure_store.py`, `web/tests/soak-workspace.test.js` | pass |
| voluntary retry after feedback | Due schedule | preserve due milestone; a scheduled-review Attempt alone advances it | `tests/test_feedback_scheduling.py` | pass |
| malformed/traversal fixture reference | repository/external paths | do not follow symlink or traversal; required unit input rejects | `tests/test_learning_catalog.py` | pass |
| optional note save with stale ETag | latest note | conflict rather than last-writer-wins | `tests/test_learning_note_store.py` | pass |
| Graph projector unavailable | source-only Reader | `/reader.html` remains an independent source-range path | `tests/test_graph_view_server.py`, `web/tests/source-reader.test.js` | pass |
| server restart | Attempt and feedback history | reopening the same local roots returns both wrong and corrected Attempts | in-app browser Journey B restart read-back, `loop3-20260920.json` | pass |

Known boundary: locks are process-local. Multi-process writers to the same derived-data directory are not a supported deployment shape for this local beta and remain a future storage-adapter concern.
