# KGnote Web prototypes

## Morning beta routes

- `/home.html`：OS、BitePacer、熟悉材料 三單元 catalog 與最近 Attempt continuity；零筆記可用。
- `/learn.html?unit=os|bitepacer|pvz`：共用 recursive Learning Structure、Reader、Reading Assist 與 scope-local graph。熟悉材料 使用本機 Whisper 逐字稿的有界節選，只把逐字稿內主張標為 reviewed，不冒充外部事實查核。
- `/practice.html?unit=...`：隔離式 Practice；提交後才取得 canonical answer／Evidence，之後追加 self-assessment。
- `/review.html`：Due Queue；1／3／7／21 天 prototype milestones，snooze／skip／stop 不建立 Attempt。

以 `npm run serve:web` 啟動；server 會載入 `web/fixtures/learning-units.json`，machine-managed records 寫到 ignored `tmp/os-learning/`。

## Phase 3c Learn → Practice prototype

Run `npm test`, then `npm run serve:web`, and open
`http://127.0.0.1:4173/learn.html`.

The supported material is the checked-in OS overview fixture. Learn is the
default and requires no note or answer: it shows a structured topic overview,
the immutable source, concept/claim explanations, supporting Evidence, exact
locators, and a visible erratum warning. `Interrupt → Driver` remains readable
but its snapshot-bound review overlay blocks it from the practice set.

`Start practice` navigates to the separate `/practice.html` document. That
document does not load the map, graph, Reader excerpt, selection state, or
canonical answers. It fetches prompt-only reviewed items and supports distinct
relation-recall and free-explanation activities. The first input or requested
hint creates a client-ID Attempt draft; submit atomically persists the raw
response and only then returns the answer, rubric, and Evidence. Retry creates a
new Attempt, and the history is read back after reload from
`tmp/os-learning/attempts/`.

The current feedback is a deterministic/manual baseline. Non-`不知道` free text
is stored as `INSUFFICIENT_EVIDENCE` until human comparison; wording is never
graded by exact phrase equality. There is no live reviewer, mastery score,
adaptive schedule, account system, or public deployment.

# Legacy read-only graph canvas

This first Web slice uses native ES modules and SVG with no runtime dependencies. At the current
fixture scale, a framework or graph package would add a build pipeline and supply-chain surface
without improving the contract test. `package-lock.json` still pins the toolchain metadata.

Run `npm test`, then `npm run serve:web` and open `http://localhost:4173/`. At runtime the browser
first posts JSON `null` to `POST /api/graph-view`; the application boundary interprets this as the
default full-view request and returns the current store's snapshot-bound facet catalog. Checked-in
graph results are test fixtures only and are never runtime catalogs. The server exposes only `web/`
as static content. Subsequent versioned view queries go to `POST /api/graph-view`,
whose read-only adapter invokes the existing Issue #16 application boundary against an explicit
canonical store; browser code never reads canonical Markdown or implements graph traversal.

The initial layout is deterministic: stable-ID-sorted Concept nodes occupy an ellipse and
LearningEvents occupy an inner lane. Desktop/tablet use the full graph. At 600 CSS pixels or less,
the canvas chooses the highest-degree Concept (stable ID breaks ties) and its one-hop neighbors as
a bounded local fallback in a portrait 720×900 scene. This is presentation-only and does not
replace the Issue #15 planner.

Wheel/pinch-compatible zoom controls and pointer drag change only the SVG viewBox. Selecting a node
by pointer or Enter/Space opens a read-only detail panel. It projects summary/context, deduplicated
Evidence and Source metadata, related LearningEvent history, and only explicitly evidenced
`confusion` / `confused_with` records. Escape or the close button dismisses it and restores focus.

The panel is a side column on desktop/iPad and a bounded bottom sheet on iPhone. It uses only the
materialized Issue #16 read model: no raw source body, path, canonical Markdown, or mutation adapter
is available to browser code.

Focus, 1/2/3-hop, node-kind, edge-class, relation, and space controls build a deterministic
`kgnote.graph-view-query.v1`. Multiple values are OR within one filter group; populated groups are
AND across groups. The Python planner applies filters before direction-neutral traversal and returns
the materialized result rendered by the browser. Changing the view closes stale node details. Reset
returns desktop/iPad to the full graph and iPhone to the deterministic one-hop Confounder view.
Search, deployment, authentication, and all canonical graph mutation remain outside this slice.

## First usable review flow

Start the server with an explicit store, open the printed local URL, click a Concept, and choose
`Review this concept`. Answer the deterministic free-recall question, optionally reveal the hint,
compare the answer with the displayed evidence, choose one of the four factual outcomes, and save.
The server appends one Markdown record under `<store>/reviews/`; it never rewrites prior confusion
or claims that the learner understood the Concept. Assessment is deliberately human self-assessment
in this first usable version, so no review content is sent to Gemini and no API cost is incurred.

```text
.venv/bin/python scripts/serve_graph_view.py --store /absolute/path/to/kgnote-vault --port 4173
```

For an iPad on the same trusted Wi-Fi, opt in to LAN listening with `--host 0.0.0.0`, then open
`http://<this Mac's local-network IP>:4173/` on the iPad. This mode has no authentication or TLS:
do not use it on public/shared Wi-Fi, configure router port forwarding, or expose it to the Internet.

See `SECURITY.md` for the explicit local-server surface, safe error behavior, static containment,
security headers, and the byte-for-byte canonical immutability test.

## BitePacer three-view learning workspace

Open `http://localhost:4173/guided-map.html` after starting the same local server. This Phase 3b
workspace provides `閱讀｜學習地圖｜探索` tabs over one manually reviewed BitePacer learning unit.
The Reader shows the exact numbered source, the Guided Map presents one focus question with five
view-only groups, nine Concepts, and seven Teaching Propositions, and Exploration renders the same
snapshot's bounded 9-node/7-edge Graph Read Model.

All three views share one in-memory selection containing Source, focus question, Concept, Edge, and
Evidence IDs. Selecting a relationship in the Map highlights its Evidence lines in Reader and the
same directional Edge in Exploration. Cross-view validation fails closed when snapshots, labels,
summaries, endpoints, relations, Evidence, locators, Source labels, or source digests drift.

The Web copy of the Guided Map is test-locked to the contract golden and the source copy is
SHA-256-locked to the Source record. Both are a bounded, manually reviewed product fixture for this
first usable workspace—not a general filesystem reader or an auto-generated runtime catalog. UI
selection resets when the page closes, while explicitly saved relationship-retrieval attempts remain
as append-only review evidence.

The workspace now also includes a read-only linking-phrase scaffold. It asks the learner to complete
`subject ＿＿ object`, optionally reveals a deterministic first-character/length hint, and then shows
the reviewed Teaching Proposition beside every supporting Evidence excerpt. A match means only that
the response matches the reviewed phrase; it is not a mastery score. After comparing, the learner
may save the attempt through the separate `kgnote.guided-review-request.v1` boundary. The browser
sends only learning-unit/source/snapshot/Edge identity, the response, and hint usage; the server
reconstructs the exact question, canonical proposition, and Evidence from its trusted Guided Map,
rejects stale context, and writes a new `kgnote.guided-review-interaction.v1` record atomically.

`npm run serve:web` enables that boundary for the reviewed BitePacer fixture and stores records under
the ignored local directory `tmp/bitepacer-guided-reviews/reviews/`. It does not modify the source,
Guided Map, Graph Read Model, or canonical Phase 0 store.

## Phase 3c LearningNote baseline

Open `http://localhost:4173/learning-note.html` to use the Graph-free, live-AI-free LearningNote
workspace. `npm run serve:web` explicitly enables its bounded routes and uses
`tmp/local-notebook/notes/` as the local authoritative Markdown store. A first save uses
`If-Match: *`; every update uses the strong ETag returned for the exact note bytes. The server
generates revisions, writes through a same-directory temporary file plus atomic replace, and treats
the browser-generated `save_id` as an idempotency key. Stale editors receive `412` and the browser
keeps their text for manual merge.

Notebook-scoped literal search covers title, headings, body, and source-anchor labels. Source links
reuse the registered-source Reader boundary, so locators and immutable source hashes are checked
before an excerpt is shown. The preview creates only heading, list, and paragraph DOM nodes; raw
HTML and Markdown image syntax are rejected by the storage contract. Disable `--enable-note-writes`
to keep existing notes readable while making PUT return `note_writes_disabled`.
