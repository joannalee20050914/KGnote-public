# KGnote active execution plan

This file contains exactly one active execution goal. It does not promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-STAGE2B-DELIVERY-PLANNING-V1",
  "objective": "Preserve the accepted Feature Disposition Ledger as the reuse-first delivery baseline, create or reuse the D2 GitHub Projects structure without duplicating work, and define the next bounded Codex-to-ChatGPT Work integration task without starting product implementation.",
  "status": "active",
  "active_milestone_id": "S2B-GITHUB-PROJECTS",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {
    "date": "2026-10-16",
    "speaker": "product owner",
    "source_path": "PLAN.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/GITHUB_WORK_PRODUCT_REVIEWER.md",
    ".ai/PUBLICATION_RECEIPT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/README.md",
    "docs/requirements/DECISIONS_AND_CONFLICTS.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
    "PLAN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "product_decisions": "R-01 through R-13",
    "acceptance_criteria": "RC-01 through RC-34",
    "feature_families": 23,
    "delivery_principle": "Existing Evidence First -> Reuse First -> Delta Only -> Verify Integration -> Build Missing Features",
    "forbidden_substitutes": [
      "re-running Stage 2A or the classified 26-commit inventory",
      "creating duplicate issues for every RC without a feature hierarchy",
      "treating legacy tests as proof that the current delivery is Done",
      "starting Release 1 through 4 product migration from this planning goal",
      "binding the b975bb5 round-14 PASS to any later commit or fingerprint"
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
  "previous_goal_disposition": {
    "goal_id": "GOAL-KGNOTE-EXTERNAL-REVIEW-RECOVERY-V1",
    "candidate_commit": "b975bb5def2ae26e379e5390cbde01c15fa40b46",
    "candidate_fingerprint": "c38fe014aacfe1562728a6cc0c6ca7784ae2b7f2e817bee5f1afff7380a586a4",
    "external_review": {
      "round": 14,
      "status": "PASS",
      "finding_count": 0,
      "consumer_status": "accepted",
      "artifact_url": "https://github.com/joannalee20050914/KGnote-public/pull/1#pullrequestreview-5444572548"
    },
    "milestones": [
      {"id": "AR-REPAIR", "disposition": "complete"},
      {"id": "AR-INTERNAL-VERIFY", "disposition": "complete_for_recorded_candidate"},
      {"id": "AR-PUBLISH", "disposition": "complete_for_b975bb5"},
      {"id": "AR-EXTERNAL-REVIEW", "disposition": "complete_for_b975bb5_round_14"},
      {"id": "AR-HUMAN-ELIGIBILITY", "disposition": "superseded_not_completed", "reason": "The product owner redirected execution to Stage 2B planning; native Obsidian and learner acceptance evidence was not produced."}
    ],
    "gate_rule": "The round-14 PASS is historical exact-candidate evidence only. It does not verify the Stage 2B Ledger, any later commit, PA-HUMAN-1, NS-HUMAN-SMOKE, or release readiness."
  },
  "auto_advance": {
    "enabled": false,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "external_review_required_before_human_gate": true,
    "max_review_cycles_per_milestone": 5,
    "stop_on_review_state": [
      "PRODUCT_DECISION_REQUIRED",
      "AUTHORITY_CONFLICT",
      "AUTOMATION_BLOCKED",
      "BUDGET_EXHAUSTED",
      "GOAL_COMPLETE",
      "STOPPED"
    ]
  },
  "preserved_human_gates": [
    {
      "id": "PA-HUMAN-1",
      "status": "not_evaluated_by_stage2b_planning",
      "release_verified": false,
      "rule": "Requires native product and learner evidence; planning documents cannot promote it."
    },
    {
      "id": "NS-HUMAN-SMOKE",
      "status": "not_evaluated_by_stage2b_planning",
      "release_verified": false,
      "rule": "Requires native product evidence; planning documents cannot promote it."
    }
  ],
  "milestones": [
    {
      "id": "S2B-CONTROL-ALIGNMENT",
      "title": "Reconcile stale execution state with the authorized Stage 2B direction",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "docs/requirements/human-decisions/"
      ],
      "acceptance": [
        "round-14 is consumed by the existing Review Consumer against the exact b975bb5 identity",
        "the old human-eligibility milestone is preserved as superseded and not completed",
        "PLAN, STATUS, review bus, and Orchestrator identify the same Stage 2B goal and next work package",
        "release_verified remains false and no old PASS is rebound to a new fingerprint"
      ]
    },
    {
      "id": "S2B-LEDGER-BASELINE",
      "title": "Accept and preserve the unique Feature Disposition Ledger",
      "status": "complete",
      "dependencies": [
        "S2B-CONTROL-ALIGNMENT"
      ],
      "human_gate": "none",
      "owned_paths": [
        "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
        "PLAN.md",
        "CODEX_STATUS.md"
      ],
      "acceptance": [
        "all 23 feature families record source, disposition, RC mapping, remaining gap, and verification condition",
        "RC-01 through RC-34 each map to an existing result or explicit gap",
        "no private path, raw conversation, credential, or secret is present",
        "requirements_guard passes without rewriting requirements or acceptance specifications"
      ]
    },
    {
      "id": "S2B-GITHUB-PROJECTS",
      "title": "Create or reuse the D2 GitHub Projects delivery structure",
      "status": "active",
      "dependencies": [
        "S2B-CONTROL-ALIGNMENT",
        "S2B-LEDGER-BASELINE"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
        "GitHub Project and Issue metadata for joannalee20050914/KGnote-public"
      ],
      "acceptance": [
        "existing Projects, Issues, and planning documents are inspected before creating anything",
        "one D2 hierarchy maps requirements, feature families, RC evidence, Release 1 through 4 reuse, and review transport work without one-Issue-per-RC duplication",
        "each executable task has a Chinese purpose, sources and RC mapping, existing evidence, delta, dependencies, acceptance, stop condition, and rollback",
        "Owner View, Ready Queue, Blocked, and Review Queue are visible in GitHub or each unsupported operation has a concrete permission/tool blocker",
        "evidence-backed status does not mark work Done merely because a legacy test exists"
      ]
    },
    {
      "id": "S2B-REVIEW-INTEGRATION-TASK",
      "title": "Define the next minimal Codex-to-ChatGPT Work review integration task",
      "status": "pending",
      "dependencies": [
        "S2B-GITHUB-PROJECTS"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
        "GitHub Project and Issue metadata for joannalee20050914/KGnote-public"
      ],
      "acceptance": [
        "the task starts from actual Review Consumer, Review Transport, and PR #1 state",
        "the task reuses existing protocol, version identity, validators, and tests",
        "acceptance proves one bounded handoff and fail-closed rejection path without starting product implementation"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Autonomous orchestration state: `STOPPED`. Active work package: `S2B-GITHUB-PROJECTS`.
Next action: inspect and reuse existing GitHub Projects and Issues, then create only the missing D2 hierarchy and views; do not push PR #1 or start product implementation.
Repository artifacts remain authoritative; PA-HUMAN-1, NS-HUMAN-SMOKE, and release_verified=false remain unchanged.
