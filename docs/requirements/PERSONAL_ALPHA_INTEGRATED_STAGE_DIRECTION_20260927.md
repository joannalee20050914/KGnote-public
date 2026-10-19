# 2026-09-27 Obsidian Personal Alpha integrated-stage direction

Status: current explicit product-owner direction. Product direction remains
`kgnote-obsidian-first-2026-09-22`.

## Authority and evidence boundary

- Speaker: product owner.
- Date: 2026-09-27 (Asia/Taipei).
- Source: explicit current Codex task instruction.
- Local formative evidence: `docs/requirements/evidence/personal-alpha-v3-partial-feedback-20260927.json`.
- This direction supersedes only the earlier execution constraints that limited work to acceptance-delivery
  improvements, prohibited the next product milestone, or required completion of the current smoke before all
  further product development.
- It does not erase the earlier Personal Alpha `manual_fail`, promote `PA-HUMAN-1` or `NS-HUMAN-SMOKE`, or set
  `release_verified=true`.

## Authorized integrated stage

Complete an Obsidian Personal Alpha in which a user, without relying on Codex conversation history or editing
Python/JSON, can:

1. enter a learning workspace and identify the topic and starting point;
2. read the immutable source and source-scoped concept explanations;
3. inspect source-supported material hierarchy and concept relationships;
4. open Evidence on demand with honest locator precision;
5. keep personal notes, an unresolved question, and an explicit continuation position;
6. close and reopen the workspace, use Start Here to find Continue Here, and return to the recorded position.

Markdown must remain independently useful. Canvas is optional native augmentation and may not become an
unverified product core. Learning path (reading order), source-supported material hierarchy, and source-supported
semantic concept relationships remain distinct. A chapter Canvas is not a complete concept-relationship
experience. This stage preserves the expectation for richer relationships without authorizing a new concept-map
feature, invented hierarchy/causality, or outside knowledge.

## Required delivery corrections and integration

- Verify the actual Obsidian vault root against native Canvas file paths, not only a custom validator rooted in a
  child directory.
- Add a discoverable, secondary Canvas entry after the existing Start Here sections without changing Golden
  section order or making Canvas mandatory.
- Make normal Reading view prioritize the lesson rather than frontmatter. Any review-vault setting is local to the
  disposable vault and preserves provenance; no formal vault or global personal setting may be changed.
- Explain and support manual continuation: the learner records the current note/section, next action, and question;
  after reopening, Start Here leads to Continue Here and then to the exact recorded location. Regeneration preserves
  user-owned bytes and never infers progress from recency, clicks, or time.
- Evidence UI and verification must distinguish opening the source document from exact heading/block/line
  localization. Repair contract-required gaps or state the bounded limitation; do not overclaim precision.
- Deliver a directly openable workspace, documented generation/preparation entry, and end-to-end generated-artifact
  verification. Reuse the accepted fixtures and source pipeline; do not hard-code network-path content or claim
  arbitrary-material AI generation.

## Human-checkpoint policy for this stage

Disposable, local, reversible work within this stage may progress through bounded milestones without intermediate
human usability approval. Known defects still require repair, and unvalidated assumptions must remain replaceable.
`PA-HUMAN-1` and `NS-HUMAN-SMOKE` retain their history, candidate identity, and pending status. Their next coherent
use is a single concentrated trial of the integrated candidate; evidence from the same operation may support both
gates, but each verdict remains separate.

Human intervention is required only when the integrated flow is ready for that concentrated trial, when existing
authority cannot resolve a genuinely mutually exclusive product choice with a safe reversible default, when work
would cross private-data/external-transmission/paid/formal-vault/plugin/destructive/release boundaries, or when the
existing review/repair budget or a necessary capability is exhausted. Completing a small milestone, passing a test,
or lacking preference feedback is not a stop condition.

## Preserved boundaries

- No formal/private vault write or scan, live AI/API, paid provider, external transmission, plugin installation,
  destructive operation, public release, commit, push, or merge.
- Do not rebuild the Web UI or a full plugin because Canvas or Markdown discoverability needs improvement.
- Preserve user-owned notes and historical candidates. Do not use reset, clean, stash, or destructive replacement.
- Native UI behavior may be called verified only after actual Obsidian operation. JSON validation, Markdown
  read-back, screenshots, or HTML simulation are not native smoke evidence.
- Existing orchestrator budget and recovery limits continue across the whole stage and may not be reset by renaming
  a subgoal.
- `release_verified=false` until separately authorized and evidenced.

## 2026-10-19 amendment: two-level human experience acceptance

Status: current explicit product-owner decision. This amendment is the single current authority for the timing and
blocking effect of human experience feedback. It changes neither the approved product scope nor the independent
safety, privacy, consent, budget, destructive-operation, publication, or merge boundaries above.

### SOFT_FEEDBACK_AVAILABLE

During development, an operable local feature or integration may offer optional human feedback only when all of the
following are present: a concrete usable result, a specific experience question that a human can meaningfully judge,
a direct entry point, suggested steps, and an exact source/candidate identity. This is a non-blocking event:

- no reply is neither PASS nor FAIL and never stops selection of the next otherwise eligible reversible work;
- a late reply remains bound to the original candidate and experience scope, and creates or updates a bounded
  follow-up only according to its demonstrated impact;
- source-only completion, automated PASS, a backend repair, a UI skeleton, or a non-interactive demonstration is
  insufficient;
- the same goal, candidate identity, and experience scope may be notified at most once;
- the notification must say that feedback is optional, identify the version and entry point, give suggested steps
  and the concrete experience question, and say that development continues without a reply.

### FINAL_HUMAN_ACCEPTANCE_REQUIRED

The only product-experience state that blocks ordinary delivery progression is
`FINAL_HUMAN_ACCEPTANCE_REQUIRED`, with final gate ID `D2-T14-FINAL-HUMAN-ACCEPTANCE` and authority in GitHub
Issue #21. It is reachable only for one complete integrated product candidate after all formally approved required
features and dependencies are complete; cross-module integration is complete; normal, error, conflict, restart,
recovery, and safety scenarios have the required evidence; installation, first setup, daily use, backup, and restore
have operable product evidence; no known delivery blocker remains; RC, independent review, and integration evidence
bind the same candidate; and a complete user trial entry point exists. The product owner's formal result must still
be absent when entering the state. Automation must never convert absence of a human verdict into acceptance.

Issue #21, RC-01 through RC-34, and the existing approved delivery plan determine completeness. Future exploratory
ideas do not become prerequisites automatically, and required features may not be removed, downgraded, deferred, or
redefined merely to make this final gate reachable.

### Supersession and preserved history

`SUPERSEDED` below means “retained as history, but no longer executable as a current intermediate stop rule.” It
does not rewrite any past verdict or candidate identity.

| Earlier source and clause | Earlier runtime effect | Current applicability | Current rule | History retained |
|---|---|---|---|---|
| `PERSONAL_ALPHA_DIRECTION_20260922.md`, “工程 candidate … 之後停在真人 Obsidian usability gate” | every Personal Alpha engineering candidate stopped before later product work | **SUPERSEDED** as an intermediate stop | optional `SOFT_FEEDBACK_AVAILABLE`, or the single final gate only after Issue #21 completeness | yes; all candidate evidence remains |
| `PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md`, native-spike resume required a new smoke result | failed PA candidate blocked its dependent rejected-baseline spike | active only for that rejected candidate and dependent baseline; **SUPERSEDED** as a global development stop | preserve the failure; independent authorized work continues and later feedback is candidate-bound | yes; `manual_fail` remains |
| `OBSIDIAN_LEARNER_PROJECTION_NATIVE_SPIKE_DIRECTION_20260923.md`, final handoff with nine smoke questions | supplied a stage-specific human trial after V3 | **SUPERSEDED** as a mandatory intermediate gate; questions remain reusable observations | may be soft feedback when operable, and must be included when relevant in final acceptance | yes; no native evidence is invented |
| this file's earlier “single concentrated trial of the integrated candidate” | could be read as a stage-completion hard stop | **SUPERSEDED** if the candidate is less than the complete Issue #21 delivery scope | only `D2-T14-FINAL-HUMAN-ACCEPTANCE` is the blocking product-experience gate | yes; `PA-HUMAN-1` and `NS-HUMAN-SMOKE` remain not evaluated |
| generic Runner/Reviewer rules that mapped any component PASS or external PASS to `HUMAN_CHECKPOINT_REQUIRED` | stopped the Runner after a subfeature | **SUPERSEDED** | record component evidence, optionally emit deduplicated soft feedback, then select the next eligible work | yes; exact review artifacts and failures remain |

`PA-HUMAN-1` and `NS-HUMAN-SMOKE` therefore retain their exact historical failures, pending status, questions, and
native-evidence requirements. They are not PASS and are not independently executable intermediate stop commands.
Their still-relevant observations are inputs to the final gate. Native-device behavior remains unverified until it is
actually observed. `release_verified` remains false until its separate release authority and evidence are satisfied.
