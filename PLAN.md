# KGnote active execution plan

This file contains exactly one active execution goal. It does not change KGnote product direction or promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-CANONICAL-PUBLIC-MIGRATION-V1",
  "objective": "Promote the verified sanitized KGnote history into one new canonical public repository, initialize one canonical Draft PR, and validate the ChatGPT Work pull-request event transport without exposing the old repository's stale pull refs.",
  "status": "active",
  "active_milestone_id": "MIG-CANONICAL-PR",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-reconciliation-2026-09-27-r8",
  "explicit_direction": {
    "date": "2026-10-05",
    "speaker": "product owner",
    "source_path": "docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md",
    "durable_goal_record": "docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md",
    ".ai/REVIEWER_BOOTSTRAP.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "PLAN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirement_ids": ["KG-GOV-07", "KG-PLAT-03", "KG-PLAT-05", "KG-PLAT-08"],
    "scenario_ids": ["SC-31", "SC-32", "SC-33", "SC-38"],
    "forbidden_substitutes": [
      "making the old archival repository public",
      "weakening product requirements instead of removing private provenance",
      "copying stale pull refs or private review history into the new repository",
      "treating deterministic verification as AI product review or human acceptance",
      "adding a mirror, custom webhook service, OpenAI API worker, or polling daemon"
    ]
  },
  "scope": [
    "re-audit sanitized rewritten content and history",
    "normalize publication-sensitive commit metadata with verified recovery",
    "create one new public canonical repository with main as default",
    "establish origin as canonical and archive-origin as the private archive",
    "push one autonomous-review branch and open one canonical Draft PR",
    "maintain machine-readable review state and complete deterministic self-review",
    "validate a minimal ChatGPT Work Pull Request opened event trigger"
  ],
  "non_goals": [
    "product redesign or requirement weakening",
    "modifying, reviving, or deleting old PR #21 or #22",
    "promotion of PA-HUMAN-1, NS-HUMAN-SMOKE, release verification, native-device behavior, or learning effectiveness",
    "long-term mirror, custom webhook infrastructure, OpenAI API use, auto-merge, or unrelated product work"
  ],
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "max_review_cycles_across_goal": 5,
    "stop_on_review_state": ["PRODUCT_DECISION_REQUIRED", "HUMAN_CHECKPOINT_REQUIRED", "AUTHORITY_CONFLICT", "AUTOMATION_BLOCKED", "BUDGET_EXHAUSTED", "GOAL_COMPLETE"]
  },
  "preserved_human_gates": [
    {"id": "PA-HUMAN-1", "status": "pending_human_review", "release_verified": false, "rule": "Only the concentrated integrated-candidate human trial can decide this product gate."},
    {"id": "NS-HUMAN-SMOKE", "status": "not_run", "release_verified": false, "rule": "Native Obsidian desktop/mobile interaction remains externally unverified."}
  ],
  "milestones": [
    {
      "id": "MIG-PUBLIC-SAFETY",
      "title": "Public-history safety and recovery verification",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [".git/", ".ai/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["approved refs contain no credential or private-data blocker, unsafe pull-ref-only blobs are unreachable, publication-sensitive commit metadata is normalized, and recovery remains verified"]
    },
    {
      "id": "MIG-REPOSITORY",
      "title": "New public canonical repository and remote transition",
      "status": "complete",
      "dependencies": ["MIG-PUBLIC-SAFETY"],
      "human_gate": "none",
      "owned_paths": [".git/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["old repository remains private, new repository is public with main default, only approved refs are pushed, and origin/archive-origin semantics are verified"]
    },
    {
      "id": "MIG-CANONICAL-PR",
      "title": "Canonical autonomous-review branch and Draft PR",
      "status": "active",
      "dependencies": ["MIG-REPOSITORY"],
      "human_gate": "none",
      "owned_paths": [".ai/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["deterministic verification and Codex self-review pass, review-state is current, and exactly one canonical Draft PR exists"]
    },
    {
      "id": "MIG-WORK-TRIGGER",
      "title": "Minimal ChatGPT Work PR-opened transport validation",
      "status": "pending",
      "dependencies": ["MIG-CANONICAL-PR"],
      "human_gate": "none",
      "owned_paths": [".ai/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["a read-only Pull Request opened event task can be created for the new public repository without API or custom infrastructure"]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The old repository is private and archival. The current task is publication and review transport only; the Obsidian-first product direction and all product/human gates remain unchanged.
