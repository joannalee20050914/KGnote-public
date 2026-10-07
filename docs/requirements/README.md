# KGnote requirements and traceability package

Status: active baseline `kgnote-reconciliation-2026-09-27-r8`.

This directory contains KGnote's public, normalized product requirements and acceptance scenarios. Private conversation wording, private learning records, original-machine paths, and unpublished source artifacts are not redistributed.

## Sources of truth

- `requirements.json`: normative requirement and delivery ledger.
- `scenarios.json`: positive and negative acceptance specifications.
- `sources.json`: public-safe source-role catalog. Stable source IDs remain for traceability, while private wording and locators are withheld.
- `DECISIONS_AND_CONFLICTS.md`: durable reconciliation decisions that must not be silently weakened.
- `REQUIREMENTS_TRACE.md`, `ACCEPTANCE_SCENARIOS.md`, `SOURCE_INDEX.md`, and `TRACEABILITY_MATRIX.md`: generated human-readable views.

The generated Markdown views do not replace their JSON sources. Historical reviews, roadmaps, and AI proposals do not become current authority merely because they remain in the repository.

## Public provenance policy

For private-source-derived requirements, the public catalog preserves:

- a stable source ID and source role;
- the normalized requirement obligation;
- forbidden substitutes;
- positive and negative acceptance behavior;
- linked scenarios and actual test/evidence bindings.

It deliberately omits verbatim private excerpts, private filenames, private source hashes, and local filesystem locations. The verified pre-publication recovery bundle retains the original private history outside this repository.

## Commands

Python 3.10 or newer is required. The guard uses only the standard library.

```bash
python3 docs/requirements/requirements_guard.py check --repo .
python3 docs/requirements/requirements_guard.py render
python3 docs/requirements/requirements_guard.py packet --area context --area structure --output task-packet.md
python3 docs/requirements/requirements_guard.py diff --base /path/to/previous/public/baseline/requirements.json --candidate docs/requirements/requirements.json
python3 -m unittest -v docs/requirements/test_requirements_guard.py
```

`check` validates structure, references, scenario bindings, and repository paths. It does not prove semantic completeness, UI fitness, test execution, native-app behavior, or learning effectiveness.

`diff` reports removals and semantic-field changes. It does not approve those changes or replace independent review.

`packet` selects requirements by ID or area. It does not dump private source material.

## Requirements continuity

Requirement → source role → decision → scenario → implementation/test/evidence must remain traceable. Removing or weakening a requirement, changing a must/forbidden behavior, merging away a capability, or promoting a human gate requires a durable decision record and impact review.

Private-source withholding is a publication boundary, not permission to reinterpret product intent.
