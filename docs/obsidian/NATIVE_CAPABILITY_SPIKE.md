# Obsidian native capability spike

Checked: 2026-09-23. Scope: official Obsidian Help and the official JSON Canvas 1.0 specification only.

This document separates advertised platform capability from KGnote artifact evidence. `supported` means the
official format or feature is sufficient for deterministic generation and local semantic validation. It does
not mean that visual or interaction behavior has passed an Obsidian human smoke.

## Capability matrix

| Capability | Status | Official basis | KGnote evidence required |
| --- | --- | --- | --- |
| Ordinary Markdown remains directly readable | `supported` | Obsidian describes itself as a Markdown editor and states that data primarily lives on the local hard disk. | `Start Here.md` and `Structure.md` must provide complete navigation without opening Canvas. |
| Wikilinks and one-off display aliases | `supported` | Internal links support `[[Note]]`, vault-relative folders, and `[[Note\|display text]]`. | Read-back resolves every generated wikilink target. |
| Reusable note aliases | `supported` | The `aliases` YAML property is an official list-valued property. | If emitted, frontmatter is parsed and the canonical file target remains unambiguous. |
| Backlinks | `requires human smoke` | Backlinks is an Obsidian core plugin and derives linked/unlinked mentions. | Static Markdown links are validator-checkable; sidebar/in-document backlink behavior needs Obsidian interaction. |
| Heading links | `supported` | Cross-note anchors use `[[Note#Heading]]`; nested heading syntax is documented. | Validator must find the exact target heading and reject stale anchors. |
| Block links | `partially supported` | Obsidian supports `[[Note#^block-id]]`; IDs are Obsidian-specific and limited to Latin letters, numbers, and dashes. | Validator must enforce the ID grammar and find the exact block ID; portability outside Obsidian is not claimed. |
| Hover preview | `requires human smoke` | Page preview is a core plugin and is on by default; editing view may require Cmd/Ctrl-hover. | Link targets can be checked automatically, but rendering and pointer behavior require desktop/mobile smoke. |
| JSON Canvas file nodes | `supported` | JSON Canvas file nodes use a vault-relative `file` and optional `subpath` beginning with `#`. | Validator must prove each path exists and each heading/block subpath resolves. |
| Directed Canvas connections | `supported` | Canvas documents directed connections; JSON Canvas edges default `toEnd` to `arrow`. | Generated edges explicitly store endpoints and direction; validator rejects dangling endpoints. |
| Canvas edge labels | `supported` | Canvas supports editing a connection label; JSON Canvas defines optional edge `label`. | Short typed labels are validated against companion Markdown descriptions. |
| Canvas colors | `supported` | Canvas supports card/connection color; JSON Canvas accepts preset or hex color strings. | Color remains redundant presentation metadata and never carries the only relation meaning. |
| Deterministic node/edge order and coordinates | `supported` | JSON Canvas defines ordered node arrays and integer geometry; it does not prescribe an auto-layout algorithm. | KGnote owns stable IDs, ordering, coordinates, and canonical JSON serialization. |
| Plugin-disabled readability | `partially supported` | Markdown remains plain text, while Canvas and Page preview are core plugins that can be disabled. | Markdown fallback must retain the full structure and typed-edge explanation; `.canvas` usability while disabled is not claimed. |
| Local/offline data boundary | `partially supported` | Obsidian states that data primarily lives on the local hard disk. | This spike performs no network/provider calls; actual offline Obsidian operation remains a human smoke. |
| Mobile availability | `requires human smoke` | Official mobile apps exist and Obsidian says mobile works similarly with mobile-specific navigation. | Static artifacts can be checked locally, but iPhone/iPad Canvas layout, hover alternatives, and interaction remain unverified. |
| Community plugin capability or telemetry | `out of scope` | This goal authorizes no third-party plugin installation or evaluation. | Any later proposal needs separate permission and evidence. |
| Full edge-description hover UI | `unsupported` | Native Canvas documents short connection labels but no native arbitrary long-description hover contract. | Companion `Structure.md`/metadata must provide complete descriptions; whether a later adapter is needed is decided after the spike. |

## Official sources

- [Internal links](https://help.obsidian.md/links): wikilinks, Markdown links, heading/block anchors, display text,
  and linked-file preview behavior.
- [Aliases](https://help.obsidian.md/aliases): list-valued YAML aliases and canonical-target link rendering.
- [Backlinks](https://help.obsidian.md/plugins/backlinks): linked/unlinked mentions and core-plugin UI.
- [Page preview](https://help.obsidian.md/plugins/page-preview): default core-plugin hover behavior and editor modifier.
- [Canvas](https://help.obsidian.md/plugins/canvas): file cards, directed connections, labels, colors, groups, and
  open `.canvas` storage.
- [JSON Canvas 1.0](https://jsoncanvas.org/spec/1.0/): node/edge schema, file `subpath`, endpoints, labels,
  colors, z-order, and integer geometry.
- [Mobile app](https://help.obsidian.md/mobile): official mobile availability and mobile-specific interaction.
- [About Obsidian](https://help.obsidian.md/obsidian): Markdown foundation and local-file ownership boundary.

## Reuse inventory

| Existing asset | Reuse in spike | Boundary |
| --- | --- | --- |
| `personal_alpha.preview.build_learning_workspace_preview` | Stable Source digest, headings, Concepts, relations, Evidence locators, uncertainty, and three source shapes. | The preview remains canonical analysis input; Canvas never mutates it. |
| `personal_alpha.workspace` renderers | Ordinary Markdown entry, immutable Source snapshot, human-readable Structure/Concept/Relationship/Evidence material. | Reuse pure rendering/link ideas; do not modify the PA-4 candidate output or default workflow. |
| `materialize_learning_workspace` transaction pattern | Staging, ownership manifest, collision detection, rollback, and read-back pattern. | Spike writes only into a new disposable root and has a separate manifest/schema version. |
| `read_back_learning_workspace` | Link/source/manifest validation model. | Extend with a native Canvas semantic validator rather than file-existence checks. |
| `tests/fixtures/personal-alpha/*` | Hierarchical, heading-free glossary, and procedural inputs. | All three use the same documented spike command; no fixture-specific manual edits. |
| Guided structure tests/projector | Risks around real recursive hierarchy and navigation-vs-canonical semantics. | Reuse contract knowledge, not Web UI or renderer code. |
| Graph planner/read model | Canonical Concept/relation identity and digest comparison vocabulary. | Do not use it to render a Knowledge Roaming view in this goal. |
| Requirements guard/control plane | Scenario selectors, run evidence, fingerprint, dirty ownership, and durable handoff. | Structural pass never promotes human or learning acceptance. |

## NS-0 conclusion

The official formats can encode the needed ordinary notes, anchors, directed labeled edges, color, and stable
geometry. Native Canvas does not promise a long-description hover surface, plugin-disabled Canvas rendering, or
desktop/mobile interaction equivalence. NS-1 and NS-2 must therefore prove the fallback/read-back contract before
the final A/B decision; documentation alone is insufficient.

## Interruption checkpoint

On 2026-09-23, product owner's first Personal Alpha Obsidian review found a blocking learner-facing Markdown projection
regression. This spike stopped after NS-0 so Canvas mechanics would not be validated against a rejected product
baseline. The matrix and reuse inventory above remain reusable. No Canvas artifact module, CLI, validator, test,
or disposable spike vault had been created. Resume conditions are recorded in `PLAN.md` and
`docs/requirements/PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md`.

## V3 resumed spike command

The learner-facing projection repair passed its Phase A automated gate on 2026-09-23. The retained matrix is
now exercised only as optional navigation over that repaired Markdown baseline.

Use one explicitly selected fixture and an existing disposable destination:

```bash
python3 scripts/kgnote_obsidian_spike.py tests/fixtures/personal-alpha/hierarchical/network-path.md \
  --vault output/obsidian-native-spike/v3-vault \
  --space networking
```

The command creates or safely reuses the corresponding Personal Alpha workspace, then transactionally adds
`Learning Structure.canvas`, `Canvas Guide.md`, and `.kgnote/native-manifest.json`. It does not scan or
modify a formal/private vault, install a plugin, or call an external service. The same command is used for the
heading-free glossary and procedural fixtures by changing only the explicit source and space.
