# Local Web boundary

The Phase 3 server is a local development and acceptance adapter, not a public deployment target.
It binds to `127.0.0.1`, serves regular files only from `web/`, and exposes the read-only graph route
`POST /api/graph-view`, the existing Concept-review routes, and—only when both explicit Guided Map
model and review-root arguments are supplied—`POST /api/guided-reviews`. Every POST accepts at most
32 KiB of JSON. The server has no apply, extraction, model-provider, or canonical mutation route.
When an explicit `--notes-root` is supplied, bounded LearningNote GET/search/source routes are
available. `PUT /api/notes/<safe-id>` is available only with the separate `--enable-note-writes`
flag, accepts at most 300 KiB, requires a strong `If-Match`, and writes only under that root's direct
`notes/` directory. It cannot write Source, Evidence, Concept, Edge, Claim, or review records.

Static path resolution decodes and normalizes the URL, rejects parent traversal and null bytes,
requires the resolved file to remain under `web/`, and rejects symlinks and directories. Canonical
Markdown, repository metadata, schemas, tests, environment files, and directory listings are not
part of the static surface. Query and error responses use `no-store`, CSP, no-referrer, no-sniff,
and frame-denial headers; server and date identification headers are omitted.

HTTP-layer failures use `kgnote.graph-view-http-error.v1` with only a stable code. Application
contract rejections retain `kgnote.graph-view-application.v1`. Neither form includes request bodies,
absolute paths, raw Markdown, exception text, or secrets. A rejected browser query clears the old
canvas and detail panel and labels the result unavailable, so stale data cannot look like success.

The graph boundary test starts a real loopback server, exercises successful and adversarial requests
while canonical write/delete/rename/apply/process/clock calls are forbidden, and compares every
canonical store path and byte before and after. Guided Review has a separate real-HTTP test: the
browser-supplied snapshot and Edge must match the server-trusted map, and the server reconstructs
question, canonical proposition, and Evidence before atomically creating an append-only record in
the explicitly configured review root. The endpoint is 404 when that configuration is absent.
These checks are not authentication, TLS, sandboxing, or production hardening. Public hosting
remains out of scope.
