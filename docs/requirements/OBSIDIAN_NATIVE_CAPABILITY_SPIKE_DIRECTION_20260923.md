# 2026-09-23 explicit execution direction: Obsidian native capability spike

Status: active bounded execution authority for `GOAL-OBSIDIAN-NATIVE-CAPABILITY-SPIKE-V1`. This record does not
replace the requirements SSOT, alter product direction, or promote any human acceptance gate.

## Source and speaker

- Speaker: product owner.
- Date received: 2026-09-23 (Asia/Taipei).
- Source: `local-source-withheld`.
- Source SHA-256: `dcc68f3e27a5895f63b1cee2c61b7f249989adb1925871a5e09edcd3292f6ede`.
- Starting requirements baseline: `kgnote-reconciliation-2026-09-22-r4`.
- Starting `requirements.json` SHA-256: `f6b3424d98cbf0f40b5808fb0d62031e0ee4a85e103b5df94ab0b354f64c87f8`.

## Delta from the previous goal

The Personal Alpha engineering candidate is preserved as the starting point. The new work is a separate,
bounded technical spike that must determine whether ordinary Markdown, wikilinks, heading/block anchors, and
JSON Canvas are sufficient for the next minimal Obsidian-first reading slice. It adds executable native
artifacts, semantic validation, three-source replay, and an architecture decision; it does not reopen or replace
the Personal Alpha human gate.

The final decision must be exactly one of:

- `native_sufficient_for_next_reading_slice`; or
- `native_insufficient_with_bounded_gaps`.

If native Canvas is insufficient, this goal may only document a minimal adapter/plugin proposal. It must not
install a community plugin or expand into a full plugin implementation.

## Authorized scope

- Register a new single active goal with milestones NS-0 through NS-3.
- Consult only official Obsidian/JSON Canvas documentation for the platform capability matrix.
- Reuse the existing deterministic Personal Alpha analysis/workspace contracts where safe.
- Add an isolated `obsidian_native` module, one documented CLI, risk-bound tests, disposable output, and durable
  evidence.
- Generate and validate three disposable vaults from the existing hierarchical, glossary, and procedural
  fixtures.
- Update requirements/scenario delivery bindings only when actual implementation and run evidence justify it.
- Update PLAN, STATUS, roadmap acceptance notes, and the authority lock when required by a deliberate locked-file
  change.

## Explicit prohibitions

- Do not complete, cancel, replace, or promote `PA-HUMAN-1`.
- Do not install, enable, or modify third-party Obsidian plugins.
- Do not modify or scan a formal private vault or the existing PA-4 candidate output.
- Do not call live AI/API providers, transmit KGnote source data, or incur paid external work.
- Do not substitute a Web tree/Graph, flat cards, color, or screen position for a real three-level hierarchy.
- Do not promote Canvas membership, heading membership, grouping, or layout into canonical knowledge facts.
- Do not invent hierarchy for heading-free sources or unsupported causality for procedural sources.
- Do not open Resume, Soak, Practice, Due, RAG, or Knowledge Roaming implementation branches.
- Do not commit, push, merge, stash, reset, clean, force checkout, or perform destructive migration.
- Do not describe automated evidence as Obsidian human usability, mobile, release, or learning-effectiveness
  acceptance.

## Evidence boundary

Official documentation can establish platform syntax and advertised behavior. KGnote acceptance still requires
locally generated artifacts and semantic read-back. Desktop/mobile hover, layout, rendering, and interaction
remain human smoke evidence unless actually performed and recorded by product owner.
