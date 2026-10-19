# Offline import pipeline

`offline_import.py` is a narrow Phase 2 orchestration boundary. It reads exactly one
caller-selected Markdown source and one caller-selected replay response, then composes
the existing importer, offline response validator, normalizer, dry-run planner, and
canonical store adapter.

`build_offline_import_preview` performs no writes. Its approval digest binds the
canonical plan, resolved store root, raw relative path, and immutable source SHA-256.
`apply_offline_import` accepts only that exact digest, creates the raw source without
overwrite, applies the canonical plan, and performs read-back. A second identical run
must produce only `UNCHANGED` operations and zero writes.

The caller must create an explicit store root containing `sources`, `concepts`,
`evidence`, `learning-events`, `edges`, and `raw` directories. This module does not scan
directories for inputs, call a provider, read credentials, create `.obsidian`, or import
private material automatically.

## Live single-file extraction preview

`live_import.py` composes the same boundaries without requiring a hand-written replay file.
`build_live_import_preview` imports one explicit Markdown source and returns the exact provider
envelope digest. `run_live_import` requires that exact consent digest, executes at most one injected
transport call, validates and records the response through the immutable ledger, then converts an
accepted candidate into a canonical dry-run. It never applies the dry-run.

`scripts/import_markdown.py` exposes this as three explicit commands. All commands must receive the
same metadata and paths. First run `preview` and inspect its destination, hashes, redaction report,
request limits, cost notice, and consent digest. Only then run `extract` with
`--approve-send <consent_digest>`. The extraction command reads `GEMINI_API_KEY` only after the
digest matches and returns a separate `apply_approval_digest`; it still performs no canonical or
raw-source writes. Finally run `apply` once without approval to reconstruct the current ledger-backed
dry-run, inspect it, and repeat with `--approve-apply <apply_approval_digest>`. Apply never reads the
API key or calls the transport, and returns canonical read-back counts plus an explicit viewer command.

After an accepted extraction, both `extract` and the no-approval `apply` preview now include a
versioned `kgnote.import-review-preview.v1` human review block. It resolves stable IDs to Concept
names, spells out every Edge as a directional subject → relation → object record, and repeats the
exact numbered source lines supporting each Evidence and relationship. Out-of-range locators are
rejected before the canonical store is read. `CONFLICT` and `REJECT` operations appear in
`blocking_items`, set `apply_blocked: true`, and cannot be bypassed by supplying an approval digest.

The current extraction contract does not ask the provider for learner-facing linking phrases.
Accordingly, the preview reports `linking_phrase: null` and
`linking_phrase_status: not_proposed`; it never turns a canonical relation token such as
`contrasts_with` into invented teaching prose. A separate
`kgnote.linking-phrase-context.v1` → `kgnote.linking-phrase-candidate-set.v1` staging contract now
exists for this purpose. After first-stage `extract`, `phrase-preview` replays the immutable ledger,
selects canonical Edges only, binds the context to the dry-run approval digest, and prints the exact
second-stage outbound context plus a separate consent digest. It performs no transport or writes.
Freshly extracted Evidence remains `unreviewed`, and the Gemini result always remains `pending`.
`phrase-extract --approve-phrase-send <digest>` performs at most one separate structured-output
request, then atomically creates `linking-phrase/manifest.json`, `raw-response.json`, and (for a
valid response) `candidate-set.json`. Exact replays verify all three files and use zero transport
calls or API-key reads. The model cannot change endpoints, direction, canonical relation, or
Evidence references.

Human review is another separate approval boundary. Supply a JSON file matching
`decisions.schema.json`, with exactly one `accept`, `correct`, or `reject` decision for every
candidate. `phrase-review --phrase-decisions <file>` first prints the complete reviewed-set preview
and digest; repeat it with `--approve-phrase-review <digest>` to append `reviewed-set.json` using
exclusive create. A different second review is a conflict, not an overwrite. Accept/correct records
over fresh `unreviewed` Evidence remain `guided_map_promotion_eligible: false`; this command records
human phrase review but does not silently modify the Guided Map spec.

```text
.venv/bin/python scripts/import_markdown.py preview \
  --source /absolute/path/to/note.md \
  --source-id src_my_note --source-kind learning_note --title "My note" \
  --locator-basis line_range --generated-at 2026-09-08T12:00:00+08:00 \
  --run-id my_note_20260908 --ledger /absolute/ignored/ledger \
  --store /absolute/path/to/kgnote-vault
```

There is deliberately no interactive confirmation, implicit key lookup during preview/apply,
automatic approval, directory scan, retry, or currency-denominated cost guarantee. Current provider pricing and
the data-retention boundary must be verified before the first live authorization.
