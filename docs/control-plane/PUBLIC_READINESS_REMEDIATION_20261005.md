# Public-readiness remediation record

Status: active execution record. This document does not change KGnote product requirements or product direction.

## Objective

Prepare the existing `joannalee20050914/KGnote` repository for public visibility while preserving the Obsidian-first product contract, reviewer contract, requirements semantics, and recoverability.

## Blocker classification

| Path or class | Classification | Action | Reason |
|---|---|---|---|
| `.ai/REVIEWER_BOOTSTRAP.md` and current protocol/schema files | reviewer contract | `KEEP_AS_IS` or narrow identifier normalization | Required independent-review semantics must remain authoritative. |
| `.ai/REVIEW_HISTORY/**`, `.ai/ORCHESTRATION_HISTORY/**` | private orchestration provenance | `REMOVE_FROM_HEAD` + `PURGE_FROM_HISTORY` | Raw historical transcripts and manifests are unnecessary for the public workflow. |
| `.ai/REVIEW_REQUEST.md`, `.ai/REVIEW_RESULT.md`, `.ai/ORCHESTRATOR_STATE.json` | useful current machine state | `SANITIZE_IN_PLACE` + `PURGE_OLD_HISTORY` | Keep only the minimum current state without local paths, raw transcripts, or personal identifiers. |
| `docs/requirements/sources.json` and generated source views | private conversation provenance | `REWRITE_TO_PUBLIC_SAFE_FORM` + `PURGE_OLD_HISTORY` | Preserve stable source IDs and requirement links while withholding private wording, locators, and source hashes. |
| `docs/requirements/requirements.json`, `scenarios.json`, decision records | normalized product semantics | `SANITIZE_IN_PLACE` + `PURGE_OLD_HISTORY` | Keep obligations, forbidden substitutes, acceptance criteria, and scenarios unchanged except identifier normalization. |
| `docs/REFERENCE_SOURCES.md` | local paths and private project provenance | `REWRITE_TO_PUBLIC_SAFE_FORM` + `PURGE_OLD_HISTORY` | Retain reusable design lessons and public references without local paths or private project identifiers. |
| `docs/chatgpt_6pro_20260919_review.txt` | private-review-derived historical artifact | `REWRITE_TO_PUBLIC_SAFE_FORM` + `PURGE_OLD_HISTORY` | Retain only a concise normalized historical summary. |
| control-plane checkpoint and current status artifacts | local path / historical candidate metadata | `SANITIZE_IN_PLACE` + `PURGE_OLD_HISTORY` | Preserve deterministic control-plane behavior without machine-specific data. |
| `web/fixtures/pvz-*` and associated catalog/test expectations | uncertain third-party transcript derivatives | `REPLACE_WITH_SYNTHETIC_FIXTURE` + `PURGE_OLD_HISTORY` | Preserve renderer, provenance, locator, review, Soak, and Practice test characteristics using original synthetic material. |
| `web/fixtures/os-overview-review.md` | uncertain source provenance | `REPLACE_WITH_SYNTHETIC_FIXTURE` + `PURGE_OLD_HISTORY` | Preserve line-locator and source-hash behavior using newly authored fixture text. |
| machine-specific absolute paths and unnecessary personal names | personal/local metadata | `SANITIZE_IN_PLACE` + `PURGE_OLD_HISTORY` | Repository-relative or role-based labels are sufficient. |
| `.gitignore` and `.env.example` | public configuration hygiene | `SANITIZE_IN_PLACE` | Prevent accidental future commits and document the optional secret variable with an empty placeholder. |

## Semantic preservation rule

Private source wording is not public evidence. The public repository retains the normative requirement IDs, obligations, forbidden substitutes, acceptance criteria, scenarios, and durable product decisions. Stable source IDs remain as traceability anchors, but their private text and original-machine locators are withheld. The verified pre-rewrite bundle is the recovery source for the original private history.

## History rewrite boundary

Only paths containing the classified non-public artifacts are purged and reintroduced in public-safe form. Source-code history and unrelated product history remain intact. Remote mutation is permitted only after HEAD verification, full reachable-history re-audit, backup verification, and a no-drift remote fetch.
