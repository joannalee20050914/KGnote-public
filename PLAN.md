# KGnote active execution plan

This file contains exactly one active execution goal. It does not change KGnote product direction or promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-PUBLIC-READINESS-PR-WORKFLOW-V1",
  "objective": "Remediate public-readiness blockers without weakening product intent, rewrite affected Git history with verified recovery, re-audit all reachable history, make the existing GitHub repository public only after PASS, and initialize one canonical Draft PR for autonomous product review.",
  "status": "active",
  "active_milestone_id": "PRW-HISTORY",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-reconciliation-2026-09-27-r8",
  "explicit_direction": {
    "date": "2026-10-05",
    "speaker": "product owner",
    "source_path": "docs/control-plane/PUBLIC_READINESS_REMEDIATION_20261005.md",
    "durable_goal_record": "docs/control-plane/PUBLIC_READINESS_REMEDIATION_20261005.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/PUBLIC_READINESS_REMEDIATION_20261005.md",
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
      "weakening or deleting product requirements in place of removing private provenance",
      "removing the independent reviewer contract because adjacent .ai artifacts are private",
      "deleting only current files while leaving non-public blobs reachable in Git history",
      "making the repository public before rewritten-history re-audit passes",
      "using blind force push, flattening all history, or discarding the pre-existing CODEX_STATUS.md update",
      "adding a custom webhook service, OpenAI API worker, or mirror repository"
    ]
  },
  "scope": [
    "verified offline backup and exact pre-rewrite ref capture",
    "public-safe requirements provenance and machine/path identifier normalization",
    "synthetic replacements for uncertain redistribution fixtures",
    "minimal public .ai state with the reviewer contract preserved",
    "conservative ignore/config hygiene",
    "path-scoped git-filter-repo rewrite and all-reachable-history re-audit",
    "force-with-lease remote transition after a no-drift fetch",
    "public visibility transition for joannalee20050914/KGnote",
    "one canonical codex/kg-note-autonomous-review Draft PR and machine-readable review state"
  ],
  "non_goals": [
    "product redesign or requirement weakening",
    "promotion of PA-HUMAN-1, NS-HUMAN-SMOKE, release verification, native-device behavior, or learning effectiveness",
    "mirror repository, ownership/name change, custom webhook infrastructure, OpenAI API use, auto-merge, or unrelated product work"
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
  "completed_goals": [
    {"goal_id": "GOAL-OBSIDIAN-PERSONAL-ALPHA-INTEGRATED-V1", "status": "complete", "release_verified": false},
    {"goal_id": "GOAL-KGNOTE-AI-REVIEWER-CONTROL-PLANE-V1", "status": "complete", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "PRW-SNAPSHOT",
      "title": "Pre-rewrite snapshot and verified recovery bundle",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["all refs and the dirty CODEX_STATUS.md bytes are recoverable from the verified external bundle and patch"]
    },
    {
      "id": "PRW-HEAD-SAFE",
      "title": "Public-safe HEAD remediation and deterministic verification",
      "status": "complete",
      "dependencies": ["PRW-SNAPSHOT"],
      "human_gate": "none",
      "owned_paths": [".ai/", ".env.example", ".gitignore", "AGENTS.md", "CODEX_STATUS.md", "DEVELOPMENT_PLAIN.md", "PLAN.md", "README.md", "docs/", "fixtures/", "schemas/", "scripts/", "src/", "tests/", "web/", "package.json", "package-lock.json", "requirements.txt", "requirements-dev.txt"],
      "acceptance": [
        "private source wording and machine identifiers are absent while normalized requirements and reviewer semantics remain intact",
        "uncertain redistribution fixtures are replaced by original synthetic fixtures with equivalent contract coverage",
        "credential, sensitive-data, path, configuration, requirements, control-plane, Python, and Node verification pass"
      ]
    },
    {
      "id": "PRW-HISTORY",
      "title": "Path-scoped history rewrite and reachable-history re-audit",
      "status": "active",
      "dependencies": ["PRW-HEAD-SAFE"],
      "human_gate": "none",
      "owned_paths": [".git/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["all intended refs are rewritten without flattening unrelated code history and every reachable blob passes the public-readiness audit"]
    },
    {
      "id": "PRW-REMOTE",
      "title": "Lease-protected remote transition and public visibility",
      "status": "pending",
      "dependencies": ["PRW-HISTORY"],
      "human_gate": "none",
      "owned_paths": [".git/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["remote refs have not drifted, rewritten refs are pushed with force-with-lease, stale PRs are explicitly closed, final audit passes, and repository identity is public with main unchanged as default"]
    },
    {
      "id": "PRW-CANONICAL-PR",
      "title": "Canonical autonomous-review branch and Draft PR",
      "status": "pending",
      "dependencies": ["PRW-REMOTE"],
      "human_gate": "none",
      "owned_paths": [".ai/", "docs/control-plane/", "PLAN.md", "CODEX_STATUS.md"],
      "acceptance": ["codex/kg-note-autonomous-review is based on rewritten main, review-state is current, deterministic verification and Codex self-review pass, and one canonical Draft PR is ready for the Pull Request opened trigger"]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The product direction remains Obsidian-first. This execution goal is limited to publication safety and PR-based review transport. The verified pre-rewrite recovery bundle remains outside the repository. `PA-HUMAN-1`, `NS-HUMAN-SMOKE`, and `release_verified=false` are unchanged.
