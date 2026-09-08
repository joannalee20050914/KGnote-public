# Issue #17 visual QA

Start from the repository root with `npm run serve:web`, then open
`http://127.0.0.1:4173/web/`. Do not change the fixture or canonical Markdown during QA.

## Mac — 1440 × 1000

- Header, graph card, controls, legend, 7 nodes, and 8 links fit without page-level horizontal overflow.
- Badge reads `Full graph`; Concept circles and the LearningEvent rounded rectangle are visibly distinct.
- Canonical links are blue, learning links mint, and the unresolved soft association is amber/dashed.
- Wheel zoom, `+`, `−`, Reset, and pointer drag visibly change/restore the canvas without changing data.

## iPad — 1024 × 768

- Badge still reads `Full graph`; the full 7-node graph remains usable.
- Canvas labels and zoom controls do not collide or leave the viewport.
- Page can scroll vertically if needed but has no horizontal overflow.

## iPhone — 390 × 844

- Badge reads `Local · 1 hop`; count is lower than the desktop 7-node graph.
- The portrait graph is readable without horizontal page overflow, and the focused Concept is emphasized.
- Canvas controls remain tappable and the legend wraps within the viewport.

## Contract checks

- No Save, Delete, Merge, Rename, Apply, editing, or proficiency control is present.
- Stable IDs appear only in the native node tooltip, while renderer labels appear on canvas.
- No visual language implies that `question`, `encountered`, or `explained` means understood.
- Record screenshot paths and PASS/FAIL observations in `DEVELOPMENT_PLAIN.md`; remove browser-generated
  project files before checking Git status.
# Issue #18 node detail panel

- Open a Concept with pointer and keyboard; confirm summary, status/spaces, Evidence, Source,
  Learning history, and the explicit empty known-confusion state.
- Open the LearningEvent; confirm event type/context/time, Concepts, Evidence, and Source.
- Confirm Enter/Space opens, Escape and close button dismiss, and focus returns to the node.
- Check 1440×1000, 1024×768, and 390×844: desktop/tablet side panel and mobile bottom sheet must
  remain readable without horizontal overflow or permanently hiding the graph.
- Confirm no editing or mutation controls, stable IDs, raw source content, or private paths appear.

# Issue #19 hop and facet controls

- At 1440×1000, confirm the default is `Full filtered graph`, 7 nodes / 8 links, and filters expand
  without colliding with the canvas or Issue #18 panel.
- Focus Correlation and verify 1 / 2 / 3 hops update via the server; labels and counts must match the
  materialized response. Confirm changing a view closes any open stale detail panel.
- Exercise node kind, edge class, relation, and space groups. Confirm OR within a group, AND across
  populated groups, filter-first behavior, isolated zero-link state, and deterministic Reset.
- At 1024×768, confirm controls, full graph, and detail panel remain keyboard/pointer accessible.
- At 390×844, confirm initial planner-backed `Local · 1 hop`, collapsible filters, bounded scrolling,
  no horizontal overflow, and Reset returns to the same local default.
- Confirm safe UI messages for rejected/empty views and no stable ID, absolute path, raw source,
  mutation control, console error, or console warning.

# Issue #20 Phase 3 boundary closure

- Repeat the Mac 1440×1000, iPad 1024×768, and iPhone 390×844 smoke paths from Issues #17–#19:
  pan/zoom/reset, full/local graph, node panel, LearningEvent-only, one filtered/isolated view, and
  deterministic query reset.
- Trigger a rejected focus/filter query after a successful result. Confirm the old graph and detail
  panel disappear, `View unavailable` / `Graph unavailable` are visible, and Reset recovers.
- Inspect successful and rejected requests: only `POST /api/graph-view` succeeds as an application
  route; repository/canonical/traversal paths and PUT/PATCH/DELETE are non-successful.
- Confirm CSP, no-store, no-referrer, no-sniff, and frame-denial headers; no Server/Date identification
  headers; zero browser console errors/warnings.
- Confirm no editing, persisted drag/layout, proficiency score, understood inference, stable ID,
  absolute path, raw Markdown, or request/exception content appears.
