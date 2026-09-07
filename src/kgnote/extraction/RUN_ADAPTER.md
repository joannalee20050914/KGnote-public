# Consent-gated extraction runs v1

`kgnote.extraction-run.v1` is provider-neutral orchestration around an injected transport.
Previewing is pure: it validates `ExtractionInput`, applies an explicitly versioned caller
redactor, and exposes the exact outbound envelope, byte count, SHA-256, destination, and consent
digest. The original immutable input is not modified.

Execution requires both `allow_external_send=True` and the exact consent digest. Provider,
model, timeout, prompt, extractor, source content, and structured-response contract are bound to
the envelope or run fingerprint. A transport is called at most once; there is no retry, fallback,
streaming, SDK selection, secret lookup, or implicit network access.

Every attempted call must become an immutable run directory containing `outbound.json`,
`response.raw`, and `manifest.json`, with restrictive permissions. An exact repeated run replays
locally with zero transport calls; reuse of a run ID with a different fingerprint is a conflict.
Accepted and rejected JSON responses always pass through the offline response boundary. Ledger
content can be sensitive and must stay in an explicit ignored local directory, never the canonical
vault or repository root.
