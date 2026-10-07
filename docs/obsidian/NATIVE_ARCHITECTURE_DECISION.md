# Obsidian native architecture decision

Decision date: 2026-09-23

## Decision

`native_sufficient_for_next_reading_slice`

The repaired learner-first Markdown workspace is the product baseline. Native JSON Canvas is sufficient as an
optional structure-navigation augmentation for the next reading slice; no third-party plugin or custom KGnote
renderer is justified by this spike.

## Evidence

- Ordinary Markdown alone retains Start Here, Source, Concept notes, Relationships, Evidence reference,
  Structure fallback, My Notes, and Continue Here.
- The hierarchical fixture generates deterministic file nodes for H1, H2, and H3 anchors and directed
  `read`, `topic`, and `subtopic` edges.
- The heading-free glossary remains flat: source and Concept reference navigation are present without invented
  heading hierarchy.
- The procedural fixture shows the four source-supported steps using `next` navigation and never promotes
  sequence to canonical causality.
- All file nodes, heading anchors, procedural text-node wikilinks, edge endpoints, labels, colors, IDs,
  coordinates, serialization, canonical digest, and Markdown fallback digest semantically read back.
- Three generated workspaces rerun unchanged. The native artifact inventory contains 53 files with fingerprint
  `1764fe4e962f2e169b6e41c995fdaf8b3041cc58d04bca4da961c534021e5c9f`.
- Risk-specific tests reject malformed JSON, unsupported fields, duplicate IDs, dangling endpoints, stale
  heading/block anchors, absolute/traversal paths, symlinks, user-owned collisions, canonical/Markdown drift,
  fake glossary hierarchy, procedural causality, and injected transactional failures.

Evidence record: `docs/requirements/evidence/obsidian-native-v3-20260923.json`.

## Bounded gaps

- Native Canvas has short edge labels but no verified arbitrary long-description hover contract. The generated
  `Canvas Guide.md` is the portable complete-description fallback.
- Backlinks, Page Preview interaction, visual layout, touch behavior, offline behavior in the actual app, and
  iPad/iPhone behavior remain human/device evidence.
- The spike does not test Knowledge Roaming eligibility, review overlays, or a custom plugin. Those are not
  needed to accept the native format for the next reading slice.

These gaps do not invalidate the technical decision because Markdown remains complete without Canvas and the
missing behaviors are either supplied by ordinary Markdown or reserved for the explicit human boundary.

## One next product slice

Stop at `PA-HUMAN-1`: product owner opens the repaired generated vault in Obsidian and evaluates the learner-facing
Markdown first, then checks whether Canvas adds useful structure understanding. No further feature begins
before that result.

## Exact human smoke paths

- Vault: `local-source-withheld`
- Start Here: `local-source-withheld`
- Port: `local-source-withheld`
- Relationships: `local-source-withheld`
- Canvas: `local-source-withheld`

## product owner smoke questions

1. 打開 Start Here，30 秒內知道在學什麼嗎？
2. 第一個該做的動作清楚嗎？
3. 點 Port，看起來是在教 Port 還是在講 KGnote extractor？
4. 系統 metadata 是否已退出主要閱讀視野？
5. Evidence 是否需要時容易找到、平常不干擾？
6. 短 source 是否仍自然，沒有被拆成太多頁？
7. 關閉再開，Continue Here 是否讓人知道怎麼接著讀？
8. Canvas 是否真的增加結構理解？
9. 不開 Canvas，Markdown workspace 是否本身已值得使用？

`PA-HUMAN-1=pending_human_review`; `release_verified=false`. Automated results do not establish usability,
mobile acceptance, or learning effectiveness.
