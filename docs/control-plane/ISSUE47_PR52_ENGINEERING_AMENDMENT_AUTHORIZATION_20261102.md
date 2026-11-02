# Issue #47 v5 — PR #52 generic intake engineering-only authorization package

Status: **EXACT OWNER APPROVAL REQUIRED**, no product-goal permission implied.

## Immutable engineering identity

- Repository: `joannalee20050914/KGnote-public`
- Issue: [#47](https://github.com/joannalee20050914/KGnote-public/issues/47)
- Draft PR: [#52](https://github.com/joannalee20050914/KGnote-public/pull/52)
- Authorized working branch (additional to pre-existing v4 permission): `codex/issue47-generic-product-intake-20261102`
- Goal ID: `CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION`
- Goal version: `2026-11-02.5-pr52-generic-intake-wiring`
- Exact spec: `docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-11-02.5.json`
- Canonical sorted UTF-8 JSON SHA-256: `1d1ae20a4c2eac5362b50b1b983a2c14ab643e1b527ddd42ce96ffe5245c4a2d`
- Predecessor v4 spec SHA-256: `0507d2dbc5c9780afbe3e67a3c8ca66f8fb1b93eff9507c86299baac0141ad5d` (preserved, never rewritten)
- New immutable scope: `WI-4B-PR52-GENERIC-GOAL-INTAKE-WIRING`, a #47 engineering milestone only, before any separate Product Goal canary.

## Exact scope difference from v4

1. Allow path-explicit commit/push **only** on `codex/issue47-generic-product-intake-20261102`, additionally to v4's old branch. The change is scoped to the existing #47 work.
2. Permit `PLAN.md`, `CODEX_STATUS.md`, and `.ai/` review/checkpoint updates on that branch solely to establish and execute the new engineering-only milestone, after live Mac read-back of the actual checkpoint. Previously completed review history must remain.
3. Integrate the existing PR #52 no-model Product Goal preflight with the uncommitted engineering discovery/activation/rollback candidate. The exact new candidate must be independently reviewed and safely deployed. Until that happens, PR #52 remains Draft and must not auto-merge.
4. Preserve **Codex 18 total / Claude 12 total**, with Owner's conservative observed minimum at this amendment **Codex 16/18, Claude 7/12**. Any host-side higher actual use or UNKNOWN reservation further reduces remaining capacity. No version/PR/session/day reset. Existing 300s minimum spacing, 3600s backoff, one writer, weekday work window and previously approved engineering-only weekend exceptions remain.
5. Preserve `product_goal_authorized=false`, `standing_b_scheme_go_live_authorized=false`, original O2 v4 ACTIVE/readonly and disabled Runner, no paid API, no unauthorized private data, and all original stop/rollback controls.

This package does not attest a Mac runtime check, independent Ubuntu Claude PASS, CI of the resulting combined candidate, or Product Goal activation. The Mac Executor must verify the current reviewed state and apply the scope only after reading back the exact Owner comment below. No new Product Goal or extra budget is created.

## Exact Owner GitHub Issue #47 reply

The repository Owner must publish the following marker and exact JSON under Issue #47. No Codex agent may self-approve. The authorized ChatGPT GitHub connector can submit it only pursuant to the Owner's explicit instruction and through the Owner-linked GitHub identity.

<!-- kgnote-codex-app-engineering-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "goal_version": "2026-11-02.5-pr52-generic-intake-wiring",
  "goal_spec_sha256": "1d1ae20a4c2eac5362b50b1b983a2c14ab643e1b527ddd42ce96ffe5245c4a2d",
  "permissions": [
    "read_back_issue47_and_owner_authority",
    "modify_only_declared_issue47_owned_paths",
    "run_local_and_no_model_remote_verification",
    "create_path_explicit_checkpoint_commits",
    "push_only_codex_issue47_collaboration_wiring_branch",
    "push_only_codex_issue47_generic_product_intake_20261102_branch",
    "update_plan_codex_status_and_ai_review_only_for_pr52_generic_intake_milestone",
    "create_update_and_read_back_issue47_draft_pr",
    "post_and_read_back_issue47_progress_authority_and_blocker_comments",
    "launch_bounded_codex_implementation_and_repair_contexts",
    "launch_bounded_independent_ubuntu_claude_infrastructure_reviews",
    "merge_issue47_pr_only_after_required_checks_independent_review_and_branch_protection",
    "deploy_only_an_exact_reviewed_generation_with_disabled_by_default_activation",
    "install_one_new_unique_scheduler_entrypoint_disabled_by_default",
    "enable_the_new_entrypoint_only_for_an_exact_separately_approved_product_goal_trial",
    "run_one_bounded_real_product_canary_after_all_separate_product_authority_privacy_and_governance_gates",
    "stop_and_rollback_the_new_issue47_entrypoint_while_preserving_evidence",
    "enable_one_reviewed_reversible_no_model_engineering_wakeup_for_exact_issue47_goal_only_without_product_goal_dispatch"
  ],
  "resource_acknowledgement": {
    "work_period": "2026-10-31T09:15:00+08:00/2026-11-20T18:00:00+08:00",
    "work_window": "MON-FRI 09:00-18:00 + OCT31 09:15-18:00 / NOV01 09:00-18:00 engineering-only Asia/Taipei",
    "max_model_concurrency": 1,
    "codex_max_per_workday": 18,
    "codex_max_total": 18,
    "codex_known_preapproval": 16,
    "claude_max_per_workday": 12,
    "claude_max_total": 12,
    "claude_known_preapproval": 7,
    "paid_api_fallback": false,
    "history_reset_forbidden": true
  },
  "product_goal_coexistence": "BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE",
  "product_goal_authorized": false,
  "standing_b_scheme_go_live_authorized": false
}
```

This is a new immutable v5 authority; the v4 authority and all earlier receipts remain historical evidence. If the spec content changes, a **new** version, canonical digest and Owner command are required; do not silently edit this file or reuse this approval.
