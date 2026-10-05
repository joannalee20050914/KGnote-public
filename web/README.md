# KGnote read-only graph canvas

This first Web slice uses native ES modules and SVG with no runtime dependencies. At the current
fixture scale, a framework or graph package would add a build pipeline and supply-chain surface
without improving the contract test. `package-lock.json` still pins the toolchain metadata.

Run `npm test`, then `npm run serve:web` and open `http://localhost:4173/`. The demo fetches a
checked-in `kgnote.graph-view-application.v1` result produced by Issue #16 as its safe facet catalog.
The server exposes only `web/` as static content. Versioned view queries go to `POST /api/graph-view`,
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
Search, persistence, deployment, authentication, and all canonical mutation remain outside this slice.

See `SECURITY.md` for the explicit local-server surface, safe error behavior, static containment,
security headers, and the byte-for-byte canonical immutability test.
