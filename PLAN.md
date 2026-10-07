# KGnote active execution plan

This file contains exactly one active execution goal. It does not promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-EXTERNAL-REVIEW-RECOVERY-V1",
  "objective": "Repair the canonical-review split brain, consume every blocking finding from KGnote-public#1, publish an exact verified candidate to the one canonical ChatGPT Work review surface, and continue autonomous repair/re-review until external product review has no blocking findings before any human acceptance gate becomes eligible.",
  "status": "active",
  "active_milestone_id": "AR-EXTERNAL-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-reconciliation-2026-09-27-r8",
  "explicit_direction": {
    "date": "2026-10-07",
    "speaker": "product owner",
    "source_path": "docs/control-plane/INCIDENT_EXTERNAL_REVIEW_BYPASS_20261007.md",
    "durable_goal_record": "docs/control-plane/INCIDENT_EXTERNAL_REVIEW_BYPASS_20261007.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    "docs/control-plane/INCIDENT_EXTERNAL_REVIEW_BYPASS_20261007.md",
    ".ai/GITHUB_WORK_PRODUCT_REVIEWER.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/PRODUCT_CONTRACT.md",
    "docs/REPRESENTATION_CONSISTENCY_CONTRACT.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "PLAN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirement_ids": [
      "KG-GOV-07",
      "KG-KNOW-03",
      "KG-KNOW-04",
      "KG-KNOW-06",
      "KG-KNOW-07",
      "KG-ING-04",
      "KG-ALPHA-02",
      "KG-ALPHA-03",
      "KG-ALPHA-05",
      "KG-PRAC-07",
      "KG-PRAC-08"
    ],
    "scenario_ids": [
      "SC-31",
      "SC-33",
      "SC-38",
      "SC-45",
      "SC-47"
    ],
    "external_finding_ids": [
      "KG-SEM-001",
      "KG-ALPHA-RECOVERY-001",
      "KG-PRACTICE-001",
      "KG-PRACTICE-002",
      "KG-CTRL-001"
    ],
    "completion_audit_finding_ids": [
      "KG-ALPHA-PORTABILITY-001",
      "KG-CTRL-ROUND-BUDGET-001"
    ],
    "forbidden_substitutes": [
      "treating internal reviewer PASS as external product-review PASS",
      "publishing to the archival KGnote repository or any repository other than KGnote-public",
      "transitioning to a human checkpoint without exact external PASS evidence",
      "asking the owner to transport findings or trigger routine repair",
      "dropping or renaming unresolved external findings instead of carrying their stable IDs"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "candidate_repository": "joannalee20050914/KGnote-public",
    "trigger_repository": "joannalee20050914/KGnote-public",
    "review_request_repository": "joannalee20050914/KGnote-public",
    "archive_repository": "joannalee20050914/KGnote",
    "pull_request": 1
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "external_review_required_before_human_gate": true,
    "max_review_cycles_per_milestone": 12,
    "stop_on_review_state": [
      "PRODUCT_DECISION_REQUIRED",
      "AUTHORITY_CONFLICT",
      "AUTOMATION_BLOCKED",
      "BUDGET_EXHAUSTED",
      "GOAL_COMPLETE"
    ]
  },
  "preserved_human_gates": [
    {
      "id": "PA-HUMAN-1",
      "status": "not_eligible_candidate_repair_pending",
      "release_verified": false,
      "rule": "Eligible only after exact external product-review PASS with no blocking findings."
    },
    {
      "id": "NS-HUMAN-SMOKE",
      "status": "not_eligible_candidate_repair_pending",
      "release_verified": false,
      "rule": "Eligible only after exact external product-review PASS with no blocking findings."
    }
  ],
  "milestones": [
    {
      "id": "AR-REPAIR",
      "title": "Authority/routing regression and external blocking-finding repair",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        ".ai/",
        "AGENTS.md",
        "PLAN.md",
        "CODEX_STATUS.md",
        "DEVELOPMENT_PLAIN.md",
        "docs/control-plane/",
        "docs/requirements/",
        "scripts/",
        "schemas/product-review/",
        "src/kgnote/personal_alpha/",
        "src/kgnote/obsidian_native/",
        "src/kgnote/review/",
        "tests/"
      ],
      "acceptance": [
        "all five external findings remain visible and are fixed with direct regressions",
        "canonical/candidate/trigger/request repositories are identical and the archive is excluded",
        "missing external evidence and internal-only PASS cannot enter a human checkpoint",
        "the formal incident and canonical lesson survive fresh-session recovery"
      ]
    },
    {
      "id": "AR-INTERNAL-VERIFY",
      "title": "Deterministic verification and internal independent review",
      "status": "complete",
      "dependencies": [
        "AR-REPAIR"
      ],
      "human_gate": "none",
      "owned_paths": [
        ".ai/",
        "PLAN.md",
        "CODEX_STATUS.md",
        "output/control-plane/"
      ],
      "acceptance": [
        "full verifier is stable and internal review has no blocking findings for the exact candidate"
      ]
    },
    {
      "id": "AR-PUBLISH",
      "title": "Exact candidate publication to canonical PR",
      "status": "complete",
      "dependencies": [
        "AR-INTERNAL-VERIFY"
      ],
      "human_gate": "none",
      "owned_paths": [
        ".ai/",
        ".git/",
        "PLAN.md",
        "CODEX_STATUS.md",
        "docs/control-plane/"
      ],
      "acceptance": [
        "remote PR #1 head, request repository, trigger repository, commit, and fingerprint match by read-back"
      ]
    },
    {
      "id": "AR-EXTERNAL-REVIEW",
      "title": "ChatGPT Work external product-review and autonomous repair loop",
      "status": "active",
      "dependencies": [
        "AR-PUBLISH"
      ],
      "human_gate": "none",
      "owned_paths": [
        ".ai/",
        "PLAN.md",
        "CODEX_STATUS.md",
        "docs/control-plane/",
        "docs/DATA_MODEL.md",
        "DEVELOPMENT_PLAIN.md",
        "docs/obsidian/",
        "docs/requirements/evidence/",
        "scripts/",
        "src/",
        "tests/"
      ],
      "acceptance": [
        "an actual canonical-PR external artifact binds the exact head and fingerprint and reports PASS with zero blocking findings",
        "the documented concentrated-trial command regenerates the same source/workspace identity from a different repository worktree without embedding an absolute machine path in that identity",
        "the exact trial handoff path matches the generator's authoritative read-back before human eligibility"
      ]
    },
    {
      "id": "AR-HUMAN-ELIGIBILITY",
      "title": "Enable only genuinely human acceptance gates",
      "status": "pending",
      "dependencies": [
        "AR-EXTERNAL-REVIEW"
      ],
      "human_gate": "PA-HUMAN-1_AND_NS-HUMAN-SMOKE",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        "docs/requirements/evidence/"
      ],
      "acceptance": [
        "external PASS evidence is exact and all remaining questions require native Obsidian use or subjective learner judgment"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Autonomous orchestration state: `VALIDATING`. Active work package: `AR-EXTERNAL-REVIEW`.
Next action: seal the multi-item question-block scope repair for `KG-SEM-001`, publish authorized round 8, and obtain a fresh exact external product-review artifact.
Repository artifacts remain authoritative; PA-HUMAN-1, NS-HUMAN-SMOKE, and release_verified=false remain unchanged.
