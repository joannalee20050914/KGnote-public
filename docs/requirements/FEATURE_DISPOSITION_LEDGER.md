# KGnote Feature Disposition Ledger

Status: **Stage 2B canonical ledger**
Baseline date: 2026-10-16
Repository / branch / HEAD: `joannalee20050914/KGnote-public` / `codex/kg-note-autonomous-review` / `b975bb5def2ae26e379e5390cbde01c15fa40b46`

## 1. Purpose and authority boundary

This is the **only Feature Disposition Ledger** for Stage 2B. It is the shared input for selective integration, GitHub Projects planning, and RC v1 delivery. Do not create a parallel ledger; update this file.

The ledger records what already exists, what may be reused, what is superseded or private-only, and the smallest remaining delta. It does not claim that an old test result passes RC v1, authorize migration, or start implementation.

The disposition vocabulary is fixed:

- `REUSE_AS_IS`: retain the current public implementation; only integration/read-back verification remains.
- `REUSE_WITH_DELTA`: retain the implementation and make a bounded change.
- `PARTIAL_REUSE`: reuse identifiable modules or tests, but not the whole old feature.
- `SUPERSEDED`: an old implementation or product role has been replaced.
- `ARCHIVE_ONLY`: preserve in private history; do not publish or integrate.
- `NEW_BUILD_REQUIRED`: no adequate implementation was found; build the missing capability.
- `UNKNOWN`: evidence is insufficient; perform only the named bounded check.

Evidence precedence for this ledger:

1. R-01–R-13 product decisions and RC-01–RC-34 acceptance text approved on 2026-10-13.
2. Stage 2A final asset inventory and the 2026-10-14 incremental inventory.
3. Release 1–4 code, tests, and candidate evidence preserved in the sealed private archive.
4. Public repository code and tests at `b975bb5`, including the already-classified 26-commit range `15d043c..b975bb5`.
5. GitHub Review Transport, Control Plane, Public Readiness, and Phase 1 evidence already present in the public repository.

Private `.ai` history, absolute machine paths, credentials, and recovery artifacts are evidence locations, not public integration inputs. File names from the sealed archive are recorded only to prevent rediscovery; their contents must pass public-safety review before any selective copy.

## 2. Decision summary

| Disposition | Count | Meaning for Stage 2B |
|---|---:|---|
| `REUSE_AS_IS` | 3 | Keep public code/tests; verify the integrated path rather than rebuild. |
| `REUSE_WITH_DELTA` | 8 | Reuse the existing feature and implement only the named RC delta. |
| `PARTIAL_REUSE` | 5 | Select modules/tests; do not port the old feature wholesale. |
| `SUPERSEDED` | 2 | Do not restore the old product role or gate. |
| `ARCHIVE_ONLY` | 1 | Keep private historical state out of the public repository. |
| `NEW_BUILD_REQUIRED` | 3 | Build the consolidated missing capability; do not split it into duplicate systems. |
| `UNKNOWN` | 1 | One bounded feasibility check is still required. |
| **Total feature families** | **23** | RC-01–RC-34 are covered below. |

Roll-up requested for planning: **11 reusable** (`REUSE_AS_IS` + `REUSE_WITH_DELTA`), **5 partially reusable**, **3 new-build**, **1 pending confirmation**, and **3 retired/private-only**.

## 3. Canonical feature disposition ledger

| ID | Feature family and source | Existing implementation | Existing test/evidence | RC | Disposition | Remaining gap | Expected verification | Downstream destination |
|---|---|---|---|---|---|---|---|---|
| FD-01 | Release 1: Markdown import and persistent source library. Stage 2A sealed archive. | Archive: `source_library.py`, import/source Web surfaces. Public basis: `src/kgnote/ingestion/markdown_source.py`, `scripts/import_markdown.py`, import pipelines. | `tests/test_markdown_source_importer.py`, `tests/test_import_markdown_cli.py`, `tests/test_live_import_pipeline.py`, `tests/test_offline_import_pipeline.py`; old candidate evidence only. | 04–06, 31–32 | `REUSE_WITH_DELTA` | Selectively carry the persistent library and UI; add conversation-format attribution, multi-file input, and source-version handling. | Fresh public-branch tests for ordinary Markdown, conversation Markdown, duplicate import, update, malformed input, and byte read-back. | Project item P1; public source-library slice. |
| FD-02 | Immutable source, provenance, stable identity, idempotency. Phase 0/1 and Release 1. | `src/kgnote/ingestion/`, `src/kgnote/normalization/`, `src/kgnote/storage/`, schemas and canonical store. | Import/normalization/store tests; Phase 1 branch history; RC-05 had old validation evidence in the 10/14 inventory. | 05–06, 10–11, 21, 26, 32 | `REUSE_WITH_DELTA` | Preserve source revisions and conflict lineage across the selected Release 1 library; never treat old validation as RC PASS. | Schema, provenance, idempotency, malformed input, conflicting update, rollback, and exact-source locator read-back. | P1 shared data boundary. |
| FD-03 | Cross-source concept identity, aliases, conflict/version handling, domain/media dimensions. Phase 1 + existing graph data model. | `normalize.py`, canonical store, concept/evidence/edge records, `docs/DATA_MODEL.md`. | Normalization/store tests and graph fixture tests. | 07–11, 21, 26, 30, 32 | `PARTIAL_REUSE` | Add explicit source/project/domain/media separation and safe same-name/different-meaning behavior; retain uncertain relations. | Cross-source merge and non-merge fixtures, conflicting claims, correction without history rewrite, non-IT text source. | Later knowledge-integration slice after P1. |
| FD-04 | Release 2: imported-source teaching projection. Stage 2A sealed archive. | Archive: `preview.py`, learner projection, source teaching UI. Public basis: `src/kgnote/personal_alpha/preview.py`, `learner_projection.py`, Obsidian projection. | `release-2-imported-source-teaching-20261008.md`; public Personal Alpha tests. Evidence is candidate/history, not RC PASS. | 07–14, 16, 31–32 | `PARTIAL_REUSE` | Select the safe source-bounded projection; improve coherent beginner prose, prerequisite gaps, and independent validation. Do not port iterative review history. | Held-out natural prose, unsupported/ambiguous clauses, exact evidence, readability rubric, independent same-candidate review. | P1 teaching sub-slice. |
| FD-05 | Obsidian-first native learner projection and ordinary-note entry. Personal Alpha / native spike. | `src/kgnote/obsidian_native/`, `docs/obsidian/`, `scripts/kgnote_obsidian_spike.py`. | `tests/test_obsidian_native_spike.py`, projection evidence JSON, portability regression. | 01–02, 05, 12–16, 25, 31 | `REUSE_WITH_DELTA` | Bind the projection to the persistent Release 1 library and supported packaged entry; preserve ordinary Obsidian reading and stable anchors. | Materialize/open/read-back on a non-development vault; same-input regeneration; moved-worktree portability; physical Obsidian remains a human/external gate. | P1 then P3. |
| FD-06 | KGnote Web learning surfaces: source reader, learning workspace, practice/review UI. Existing public Web app + Release 1–3 archive UI. | Public `web/source-reader.*`, `learning-workspace.js`, `practice-*`, `review-*`; archive source/import/teaching UI. | Public Node UI tests; archive UI regressions. | 02, 12–18, 22–25, 31 | `PARTIAL_REUSE` | Keep learning-specific interaction; do not restore a second generic editor/file tree. Consolidate archive UI with current public surfaces. | DOM tests plus rendered/clicked packaged journey; no opaque IDs or repository paths in learner UI. | P1/P2 shared UI. |
| FD-07 | Guided structure and graph views. Earlier Web graph + Obsidian Canvas. | `src/kgnote/visualization/`, graph/guided contracts, `web/graph.js`, native Canvas generator. | Graph projector/planning/application tests and native spike tests. | 10–11, 15–16, 30 | `PARTIAL_REUSE` | Reuse local neighborhood and Canvas adapters; keep graph secondary and distinguish structure membership from canonical knowledge edges. Roaming eligibility is not yet RC-complete. | Same concept IDs/evidence across note/Canvas/Web; unresolved relations remain unresolved; no graph-first landing page. | Post-P1 enhancement, not a prerequisite for first import. |
| FD-08 | Release 3: Soak, staged Practice, immutable Attempts, Exposure, feedback, scheduling, readable history. | Public `src/kgnote/review/`, attempt/exposure schemas and Web practice. Archive: `learning_loop.py` and integrated source actions. | Public review/attempt/exposure/practice/scheduling tests; `product-3-learning-loop-20261008.md`. | 22–24, 31–32 | `REUSE_WITH_DELTA` | Selectively integrate source-supported item selection and learner-facing loop; extend evidence-based review timing without mastery percentage or debt. | Soak creates Exposure only; Practice answer isolation; immutable retry/feedback; skip/snooze negative cases; close/reopen read-back. | Project item P2. |
| FD-09 | Exact continuation: unresolved question, anchor, selected item, response/feedback and version. | Public continuity/context/workspace modules; archive return-continuity and Resume Here implementation. | Public continuity tests; `product-4-return-continuity-20261008.md`; RC-25 had old validation evidence. | 03, 19, 23, 25–26, 31 | `REUSE_WITH_DELTA` | Port item-scoped continuation and question chain; bind it to persistent source versions and packaged reopen flow. | Two-item switch/reopen, stale/tampered anchor, source revision, exact Attempt-feedback pairing, byte preservation. | P2; dependency for P3 E2E. |
| FD-10 | Inline contextual glossary, fuzzy internal retrieval, anchored questions and follow-up tree. R-08/R-09; no complete match in 10/14 inventory. | Nearby building blocks: reader search/catalog, evidence locators, continuity contexts. No complete product flow found. | RC-13 and RC-17 were `Not found`; RC-18/19 were partial. | 13, 17–19, 21, 25, 31 | `NEW_BUILD_REQUIRED` | Build one shared retrieval/context service and UI, not separate glossary, search, and question stores. | Imprecise query finds/not-finds honestly; definition returns to reading position; anchored parent/child questions survive revision/reopen. | New-build project after P1/P2. |
| FD-11 | External AI tutor handoff with precise, non-duplicative context and lawful subscription path. R-09. | Context/evidence export can be reused; no verified supported automatic subscription integration found. | RC-20 was `Not found`; current provider evidence does not establish ChatGPT subscription automation. | 20–21, 28, 31 | `UNKNOWN` | Bounded feasibility check of supported authorization. Always retain a low-friction manual handoff/import fallback; never automate browser cookies. | Provider documentation/authorization proof or explicit unsupported result; round-trip delta de-duplication fixture. | One bounded spike, then update this row to delta/new-build. |
| FD-12 | Local-first bounded AI job pipeline: batch, stop/resume, capability escalation. R-03/R-04. | Reusable extraction contracts, offline response validation and adapters; no complete job controller matching RC-09. | Offline/live import and extraction contract tests. RC-09 was `Not found`. | 07–09, 14, 27–29, 32 | `NEW_BUILD_REQUIRED` | Add persistent bounded jobs, local-first selection, retry ceilings and honest unsupported states. | Batch interruption/resume, malformed model output, hard retry limit, no-network path, private-data non-egress. | Consolidated AI infrastructure project. |
| FD-13 | Existing Gemini/provider transport and extraction run adapters. Phase 1 / issue-9. | `src/kgnote/extraction/gemini_transport.py`, run adapter, live import adapter. | `tests/test_gemini_transport.py`, run-adapter/live-import tests. | 09, 11, 27–29, 32 | `PARTIAL_REUSE` | Reuse transport boundary and response validation only. Old provider path does not satisfy local-first consent, cost visibility, or payment denial. | Explicit consent and data-scope preview; no key leakage; quota/price unknown states; adapter disabled by default. | Adapter under FD-12/FD-14, never a default path. |
| FD-14 | AI run transparency, quota/cost ledger, egress consent and double-confirmed bounded payment. R-04. | Consent-gated run concepts and provider metadata are partial; no complete UI/policy was found. | RC-27 and RC-29 were `Not found`; RC-28 was conflict. | 09, 20, 27–29, 32 | `NEW_BUILD_REQUIRED` | Build one policy/envelope for run status, model/location, source scope, limits, cost state, consent and hard payment cap. | Unknown quota/price stays unknown; unauthorized egress/payment blocked; two confirmations bound to one job; post-run cost state. | Consolidated with FD-12; precedes any live provider. |
| FD-15 | Release 4 macOS app packaging and onboarding. Stage 2A sealed archive. | Archive: `build_macos_app.py`, `packaging.py`, Home/Settings UI and bundle manifest. | `release-4-packaging-onboarding-20261008.md`, packaging/UI tests; artifact was ad-hoc signed and not notarized. | 01–03, 15, 25–26, 31–32, 34 | `REUSE_WITH_DELTA` | Selectively port the builder/runtime/onboarding; bind integrated R1–R3 product; add supported signing/notarization/distribution evidence when authorized. | Fresh clean-Mac install/launch, no Terminal/dev paths, quit/relaunch, failure recovery, exact artifact digest, Gatekeeper/notarization status. | Project item P3. |
| FD-16 | Release 4 backup, preview, guarded restore and rollback. | Archive packaging module and Settings UI. | Packaging evidence/tests; RC-26 had old validation evidence. | 03, 21, 23, 25–26, 31–32 | `REUSE_WITH_DELTA` | Selectively port; include source versions, corrections, question chains and learning history from integrated store. | Manifest/hash/traversal/symlink/oversize negatives; preview identity; pre-restore snapshot; injected-failure rollback; full read-back. | P3 recovery sub-slice. |
| FD-17 | GitHub Review Transport and exact publication/result ingestion. Existing public HEAD, including classified 26-commit range. | `github_product_review_consumer.py`, `external_review_control.py`, `publish_external_candidate.py`, product-review schema and reviewer contract. | Dedicated consumer/external-control/publication tests; commit subjects show fail-closed ingestion, exact read-back, portable requests and resolver precedence. | 33–34 | `REUSE_AS_IS` | No code rebuild. Verify it against the future integrated product candidate; do not port mutable `.ai` history. | Exact PR/HEAD/fingerprint round trip; stale/wrong-repo/internal-only results rejected; blocking finding survives repair. | Shared CI/review service for every integration PR. |
| FD-18 | Control Plane candidate identity, custody, review budget, fail-closed progression and recovery. Existing public HEAD. | `codex_control.py`, `codex_orchestrator.py`, protocol/schema and control-plane tests. | Control-plane negative/integration tests and preflight; classified 26 commits cover stale PASS, custody, portability and review budget. | 33–34 | `REUSE_AS_IS` | Keep mechanics. Rebind future PLAN/status to RC v1 work packages only when implementation is explicitly started; old state is not product authority. | Fresh candidate seal/review/repair/reseal; candidate drift rejection; budget; no premature human/release gate. | Project workflow foundation; not a product feature ticket. |
| FD-19 | Public Readiness: secret/private-path scanning, canonical repository identity and publication safety. | Public-readiness scripts/docs/checkpoints and publication receipt contracts. | Public-readiness remediation evidence and control-plane tests. | 27–29, 32–34 | `REUSE_AS_IS` | Retain checks; scan each selectively copied archive path before staging. | Secret, absolute-path, private-history and wrong-repository negative fixtures; exact remote read-back. | Required check on P1–P3. |
| FD-20 | Mutable/private `.ai` history, dirty orchestration state, recovery images and historical absolute-path receipts. Stage 2A private archive. | Historical requests/results/events/status from old worktrees and recovery sources. | Preservation/restore evidence only; not executable product evidence. | 33–34 | `ARCHIVE_ONLY` | None for public product. Reference immutable public-safe lessons, not private bytes. | Public-safety scan confirms none are copied; archive recovery remains private. | Private archive only. |
| FD-21 | Old Web-first/dashboard-as-primary product role. Superseded roadmap. | Existing Web components remain reusable only as learning interactions and comparison harnesses. | Historical Web tests do not establish current primary-surface acceptance. | 01–02, 15–18, 31 | `SUPERSEDED` | Do not restore Web as a replacement for ordinary Obsidian reading. | Entry-path test proves Obsidian/ordinary note remains primary; Web opens only for KGnote-specific interaction. | No ticket; enforced as negative acceptance. |
| FD-22 | Old Personal Alpha/manual smoke gates and `CANDIDATE_MATURE` release interpretation. Superseded by RC v1. | Historical PA/NS gates and review artifacts remain provenance only. | Old PA evidence is not external-user RC evidence. | 31, 33–34 | `SUPERSEDED` | Replace only the gate semantics in the eventual RC plan; preserve genuine physical-device/human evidence boundaries. | RC-34 cannot pass from Personal Alpha, component tests, internal PASS, or `release_verified=false`. | No migration; RC v1 gate only. |
| FD-23 | RC evidence binding and external-user release gate. Existing traceability/control-plane skeleton. | Requirements/scenario traceability, product-review schema, fingerprints, receipts. | Current guard/review validation proves structure, not RC product completion. | 31–34 | `REUSE_WITH_DELTA` | Add RC-01–34 evidence bindings for the integrated artifact and `RELEASE_CANDIDATE_FOR_EXTERNAL_USER`; do not duplicate requirements SSOT. | Every required RC has same-artifact automated + independent product evidence; no blocker; ordinary supported-Mac journey; then and only then set the flag. | Final RC audit after P3 and missing-feature projects. |

## 4. RC-01–RC-34 coverage and gap matrix

`2026-10-14 state` deliberately retains the earlier inventory classification: 21 `PARTIAL`, 4 `OLD_EVIDENCE`, 7 `NOT_FOUND`, and 2 `CONFLICT_BLOCKED`. `OLD_EVIDENCE` means reuse evidence exists; it is not RC PASS.

| RC | Acceptance focus | 2026-10-14 state | Feature destination | Existing evidence / present location | Remaining proof or gap |
|---|---|---|---|---|---|
| RC-01 | Normal Mac install/open; no Terminal/Git/dev paths | `PARTIAL` | FD-05, FD-15 | Native projection; Release 4 builder/onboarding evidence | Selectively integrate, sign/notarize when authorized, clean-Mac operate. |
| RC-02 | First-run space selection and persistent return | `PARTIAL` | FD-01, FD-06, FD-15 | Release 1 library and Release 4 Home UI | Integrated packaged first-run/reopen evidence. |
| RC-03 | Durable confirmed data across restart/crash | `OLD_EVIDENCE` | FD-09, FD-15, FD-16 | Return-continuity and recovery candidate evidence | Same packaged artifact, crash injection, full store read-back. |
| RC-04 | UI import for ordinary and conversation Markdown | `PARTIAL` | FD-01 | Importer/pipeline plus archived source UI | Multi-file and conversation attribution through packaged UI. |
| RC-05 | Immutable source and honest locator | `OLD_EVIDENCE` | FD-02, FD-05 | Import/provenance tests and projection evidence | Bind to integrated persistent library and fresh held-out source. |
| RC-06 | Idempotent import and source-version handling | `PARTIAL` | FD-01, FD-02 | Import/normalization tests; archive library | Explicit update lineage without duplicate knowledge/history reset. |
| RC-07 | Select important reusable knowledge, not every noun | `PARTIAL` | FD-04, FD-12 | Source-bounded projection and review findings | Held-out divergent conversation plus independent quality review. |
| RC-08 | Separate worth, factual readiness and learning evidence | `PARTIAL` | FD-03, FD-04, FD-08 | Concept/Evidence vs Learning Overlay contracts | Integrated UI/read-back; no mastery inference. |
| RC-09 | Bounded local-first batch AI with stop/resume | `NOT_FOUND` | FD-12 | Reusable extraction/offline adapters only | New bounded job controller and negative tests. |
| RC-10 | Cross-source identity without uncontrolled growth | `PARTIAL` | FD-02, FD-03 | Normalization and canonical store | Cross-source merge/non-merge and source-context preservation. |
| RC-11 | Traceable claims and independent verification | `PARTIAL` | FD-02–04, FD-17 | Evidence records and independent review transport | Product-level claim verification on same candidate. |
| RC-12 | Coherent beginner teaching prose | `PARTIAL` | FD-04, FD-06 | Release 2 projection candidate evidence | Held-out readability/correctness/load review. |
| RC-13 | Contextual Chinese glossary with English term | `NOT_FOUND` | FD-10 | Evidence locators only | New shared retrieval/glossary flow. |
| RC-14 | Fill prerequisites; expose unsupported depth | `PARTIAL` | FD-04, FD-10, FD-12 | Conservative projection boundaries | Prerequisite retrieval and explicit gap/escalation behavior. |
| RC-15 | Obsidian general notes + connected KGnote interaction | `PARTIAL` | FD-05–06, FD-21 | Native projection and Web learning surfaces | Supported installed entry and reliable links; no duplicate editor. |
| RC-16 | Teaching/concepts/source/local relations interoperate | `PARTIAL` | FD-04–07 | Projection, reader, graph and Canvas tests | One-identity integrated read-back with learning-first UI. |
| RC-17 | Imprecise retrieval of prior teaching/questions | `NOT_FOUND` | FD-10 | Catalog/search building blocks only | New honest retrieval, including not-found/near-match cases. |
| RC-18 | In-place small question and return to reading | `PARTIAL` | FD-10 | Reader and context anchors | New combined inline interaction and reopen verification. |
| RC-19 | Anchored question/follow-up chain survives revisions | `PARTIAL` | FD-09–10 | Continuity context is reusable | Parent/child question model and revision-safe read-back. |
| RC-20 | Precise lawful tutor handoff and fallback | `NOT_FOUND` | FD-11, FD-14 | Context export pieces only | Bounded authorization feasibility + manual fallback. |
| RC-21 | Re-import tutor delta without duplicate evidence | `PARTIAL` | FD-01–03, FD-10–11 | Import/idempotency foundations | Round-trip link to original question; delta-only integration. |
| RC-22 | Teaching before staged Practice; answer isolation | `PARTIAL` | FD-08 | Practice/attempt/exposure code and tests | Integrated source-driven stages and learner-operated evidence. |
| RC-23 | Immutable factual learning history | `PARTIAL` | FD-08–09, FD-16 | Attempt/feedback/continuity stores | Version-bound packaged read-back and backup/restore. |
| RC-24 | Evidence-based review without notifications/debt | `PARTIAL` | FD-08 | Scheduling/Exposure code | Due rationale, skip/snooze/no-use negative behavior in product UI. |
| RC-25 | Exact reopen to unresolved learning context | `OLD_EVIDENCE` | FD-09 | Return-continuity candidate evidence | Selectively integrate and prove from packaged entry. |
| RC-26 | Preserve sources/corrections/versions; full recovery | `OLD_EVIDENCE` | FD-02–03, FD-16 | Canonical store and Release 4 recovery evidence | Integrated full-data backup/restore on exact artifact. |
| RC-27 | Visible model/location/scope/status/quota/cost | `NOT_FOUND` | FD-12, FD-14 | Provider metadata fragments only | New honest run ledger/UI; unknown remains unknown. |
| RC-28 | Local/no-new-cost default; authorized egress only | `CONFLICT_BLOCKED` | FD-13–14 | Old provider adapter conflicts with current policy if reused whole | Reuse boundary only; add consent/policy and default-off live adapter. |
| RC-29 | No automatic extra payment; bounded double confirmation | `NOT_FOUND` | FD-14 | No adequate implementation found | New per-job hard-cap confirmation and denial tests. |
| RC-30 | Separate source/project/domain/media; no IT lock-in | `PARTIAL` | FD-03, FD-07 | General source/graph model | Add explicit dimensions and non-IT text fixture; no multimedia parser required. |
| RC-31 | Unknown end-to-end Mac learning journey | `PARTIAL` | FD-01–16, FD-23 | Product-envelope candidate covers a bounded old journey | Held-out cross-source branched journey on packaged artifact, including missing capabilities. |
| RC-32 | Negative/error matrix protects data | `PARTIAL` | FD-01–19 | Many component negative tests | Consolidated same-artifact malformed/conflict/quota/payment/crash run. |
| RC-33 | Same-version Codex + independent product review | `CONFLICT_BLOCKED` | FD-17–19, FD-23 | Transport/control plane now reusable at public HEAD | Operate exact integrated artifact through real external review; internal PASS is insufficient. |
| RC-34 | External-user RC gate only after all evidence | `NOT_FOUND` | FD-22–23 | Current release gates intentionally remain false | This is a final state/gate, not a feature module; pass only after all required RC evidence and no blockers. |

Coverage check: every ID from RC-01 through RC-34 appears exactly once in this matrix. The state totals are **21 `PARTIAL` + 4 `OLD_EVIDENCE` + 7 `NOT_FOUND` + 2 `CONFLICT_BLOCKED` = 34**.

## 5. Already-classified 26 commits: disposition without re-analysis

The range `15d043c..b975bb5` is already part of the public baseline. Stage 2B must not reopen a commit-by-commit audit. Its existing classification is carried forward as four destination groups:

| Existing class | Commit subjects represented | Ledger destination |
|---|---|---|
| Review transport/publication | fail-closed GitHub consumer, reviewer contract, canonical loop, portable request, publication read-back/execution, candidate resolver | FD-17 `REUSE_AS_IS` |
| Candidate/review safety | stale marker/PASS invalidation, relation review, external handoff, status identity, round authority/budget, wait identity, custody and clean-checkout recovery | FD-18 `REUSE_AS_IS` |
| Product correctness deltas | portable trial source identity, interrogative relation rejection, question context/scope/nesting, learner projection/practice regressions | FD-02/04/08/09 `REUSE_WITH_DELTA` or `PARTIAL_REUSE` as specified above |
| Mutable historical state | archived requests/results/events and old orchestration/status bytes | FD-20 `ARCHIVE_ONLY`; regenerate future candidate state |

Only the unresolved destination question was added: code/tests stay in public and are exercised against future integrated candidates; mutable historical `.ai` state is never treated as reusable product code.

## 6. Duplicate work merged or superseded

- General Markdown editing, file browsing, backlinks and Canvas remain Obsidian responsibilities. KGnote does not build a second generic notes application (FD-21).
- Glossary, imprecise internal search, anchored questions and tutor-context preparation share one retrieval/context layer (FD-10/11), not four independent stores.
- Local batch execution, provider metadata, quota/cost visibility, egress consent and payment blocking share one AI job policy envelope (FD-12–14), not separate per-provider systems.
- Source identity/versioning is shared by import, teaching, question anchors, practice and backup (FD-01–04/08–10/16).
- The Web graph is a secondary navigation/verification surface; it does not replace the Obsidian-first entry or create a second concept identity (FD-05–07/21).
- Old Personal Alpha/manual smoke readiness and historical `.ai` state cannot substitute for RC-33/34 (FD-20/22/23).

## 7. Next GitHub Projects delivery items

These are ordered by reuse-first dependencies. Creating Project records is outside this documentation-only task.

### P1 — 選擇性整合 Release 1–2：來源庫到可讀教材

**中文說明：** 從 Stage 2A 已保全的 Release 1/2 中，只搬入持久來源庫、匯入介面、來源版本與安全教學投影；接到目前 public 的 importer、canonical store、Obsidian projection 和學習型 Web surface。不得整包搬移私人工作樹或 `.ai` 歷史，也不得重造 Markdown editor。

**依賴：** FD-17～19 的既有 public checks；Stage 2A sealed archive 可讀；無產品功能前置依賴。

**驗收：** 在乾淨 public 工作分支，以一般 Markdown 與一份對話 Markdown 完成 UI 匯入；原文 byte-preserved；重複匯入不重複；更新產生版本關聯；Obsidian `Start Here` 與 Web 教材使用相同來源/概念/證據 identity；內容不足時誠實顯示缺口。

**證據要求：** 對應 RC-04～06、07～12、15～16 的測試名稱與 exact commit；source/provenance/idempotency/malformed/update read-back；渲染或實際開啟證據；public-safety scan；同一 candidate 的獨立 review artifact。

### P2 — 選擇性整合 Release 3：Soak、Practice、學習歷史與精確續學

**中文說明：** 重用 Exposure、Attempt、feedback、scheduling 與舊 learning-loop/return-continuity 成果，把它們接到 P1 的 persistent source/review item；不建立 mastery 百分比、懲罰性 debt 或另一套 history store。

**依賴：** P1 的 stable source/version/evidence identity。

**驗收：** 同一 source-supported item 可先 Soak（只寫 Exposure），再 Practice（答案隔離）；回答、提示、feedback、retry 均 append-only；skip/snooze 不偽造成功；保存問題後關閉再開可回到相同 item、locator、來源版本、問題與 response/feedback；切換兩個 item 不串線。

**證據要求：** 對應 RC-22～25、31～32 的 positive/negative tests；same-input regeneration byte comparison；tampered/stale context rejection；learner-facing UI render/click read-back；exact candidate independent review。

### P3 — 選擇性整合 Release 4：Mac 安裝、onboarding、持久化、備份與復原

**中文說明：** 重用 Release 4 builder、packaging、Home/Settings 和 guarded restore，把 P1/P2 的完整產品打包成一般 Mac 使用者可操作的候選；不以 development server、ad-hoc artifact 或 component tests 冒充正式交付。

**依賴：** P1、P2；如要公開下載，另需明示授權 Developer ID/notarization credential use。RC-13/17/20/27/29 等後續新功能未完成時，P3 只能是 integration candidate，不能設定 RC-34 flag。

**驗收：** 乾淨受支援 Mac 正常安裝/啟動；不需 Terminal/Git/repo path；first-run 建立或選擇 space；匯入、學習、關閉/重開、異常恢復；backup preview、exact confirmation、restore/rollback 完整保存 source versions、questions 和 learning history；artifact digest/read-back；簽章、公證與 Gatekeeper 狀態如實呈現。

**證據要求：** 對應 RC-01～03、25～26、31～34 的 exact artifact manifest；fresh-machine operated journey；crash/restore negative evidence；codesign/notarization/Gatekeeper receipt when applicable；public-safety scan；same-artifact external product review。`RELEASE_CANDIDATE_FOR_EXTERNAL_USER` 保持 false，直到 FD-10/12/14 等必要缺口與全部 RC gate 通過。

## 8. Update rule

Future discoveries do not reopen Stage 2A. Add or amend one row here with its evidence, disposition, RC impact and destination. A disposition may change only when new code-level or operated evidence is recorded. Do not silently turn `UNKNOWN` or `PARTIAL_REUSE` into `NEW_BUILD_REQUIRED`, and do not turn candidate/old evidence into RC PASS.
