# KGnote active execution plan

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-MAINLINE-INTEGRATION-20261020",
  "objective": "以 main 為基準建立單一、可審查、可回復的正式整合候選，納入既有產品與 Source Library，採用現行 Ubuntu Claude Reviewer 與 Runner 契約，不合併 main。",
  "status": "active",
  "active_milestone_id": "MAINLINE-INTEGRATION-CANDIDATE",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {"date":"2026-10-20","speaker":"product owner","source_path":"current task: formal integration option A","durable_goal_record":"PLAN.md"},
  "auto_advance": {"enabled":false,"automatic_merge":false,"requires_explicit_work_item_authority":true},
  "preserved_human_gates": [
    {"id":"D2-T14-FINAL-HUMAN-ACCEPTANCE","status":"not_eligible_incomplete_product_scope","release_verified":false},
    {"id":"PA-HUMAN-1","status":"not_promoted","release_verified":false},
    {"id":"NS-HUMAN-SMOKE","status":"not_promoted","release_verified":false}
  ],
  "milestones": [{
    "id":"MAINLINE-INTEGRATION-CANDIDATE","title":"乾淨正式主線整合候選","status":"active","dependencies":[],"human_gate":"github_required_approval_before_merge",
    "owned_paths":["PLAN.md","CODEX_STATUS.md",".ai/","docs/control-plane/","docs/requirements/","schemas/","scripts/","src/","tests/","web/"],
    "acceptance":["main-based non-stacked Draft PR","Source Library and full deterministic verification pass","authority PLAN STATUS fingerprint and reviewer identity agree","new exact candidate receives Ubuntu Claude review through Runner GitHub relay","main merge remains protected and manual"],
    "stop_conditions":["required GitHub approval missing","deterministic verification fails","review budget unavailable","would require force push, automatic merge, or history deletion"]
  }]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Integration source provenance: PR #1 historical product/control foundation, PR #22 reusable review plumbing only, PR #26 Source Library product candidate. Historical active snapshots are referenced by their original PRs and are not activated here.
