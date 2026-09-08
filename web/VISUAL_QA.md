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
