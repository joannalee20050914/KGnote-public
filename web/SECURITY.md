# Read-only Web boundary

The Phase 3 server is a local development and acceptance adapter, not a public deployment target.
It binds to `127.0.0.1`, serves regular files only from `web/`, and exposes one application route:
`POST /api/graph-view`. That route accepts at most 32 KiB of JSON and calls the existing read-only
canonical-store → projector → planner boundary. It has no apply, extraction, model, or write route.

Static path resolution decodes and normalizes the URL, rejects parent traversal and null bytes,
requires the resolved file to remain under `web/`, and rejects symlinks and directories. Canonical
Markdown, repository metadata, schemas, tests, environment files, and directory listings are not
part of the static surface. Query and error responses use `no-store`, CSP, no-referrer, no-sniff,
and frame-denial headers; server and date identification headers are omitted.

HTTP-layer failures use `kgnote.graph-view-http-error.v1` with only a stable code. Application
contract rejections retain `kgnote.graph-view-application.v1`. Neither form includes request bodies,
absolute paths, raw Markdown, exception text, or secrets. A rejected browser query clears the old
canvas and detail panel and labels the result unavailable, so stale data cannot look like success.

The automated boundary test starts a real loopback server, exercises successful and adversarial
requests while write/delete/rename/apply/process/clock calls are forbidden, and compares every
canonical store path and byte before and after. This proves the tested adapter is read-only; it is
not authentication, TLS, sandboxing, or production hardening. Public hosting remains out of scope.
