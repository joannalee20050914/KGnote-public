# Issue #47 — 2026-10-31 daily model-launch exception (engineering only)

Status: OWNER_APPROVAL_REQUIRED until exact new Owner comment and verified read-back.

Same engineering Goal: `CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION`
New immutable spec version: `2026-10-31.3-day-ceiling-exception`
Canonical JSON SHA-256: `c9550b812d3f7a1542cafc68af87afc1bed3a42f94ff7276ba1960c98563b805`
Spec file: `docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.3.json`
Former version `2026-10-31.2-weekend-engineering-exception` and its approval remain immutable.

Today only: Codex 5/day rather than 3; Claude 4/day rather than 2. Total Codex 18 and Claude 12 unchanged. Preserve at least Codex 10/18 (8 remaining) and Claude 2/12 (10 remaining), including today's historical daily 3/3 and 2/2. More recent actual usage overrides the conservative floor. The 2026-11-01 and ordinary weekday daily 3/2 limits are unchanged. Weekday and weekend work hours unchanged.

Only already authorized Issue #47 engineering work. No unapproved product canary, no standing go-live, no legacy O2 activation, no paid API. Exact new approval, schema and no-model pre-launch date/usage check must all pass; a legacy engine that does not validate this override must fail closed. Any historical blocked quota audit, independent review custody and findings remain unmodified except a separate evidence-backed time-limited blocker resolution.

**Success acceptance:** Actual ChatGPT/GitHub Product Goal owner authorization → trusted single launcher → Ubuntu implementer → independent reviewer → GitHub read-back → no-human-relay continuation and safe rollback, with exact live evidence. No guarantee of success within a fixed budget; never misreport tested partial functionality as fully autonomous. If the total limit is reached first, checkpoint and report a blocker rather than infer new authority or spending.

## Exact Owner reply

<!-- kgnote-codex-app-engineering-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "goal_version": "2026-10-31.3-day-ceiling-exception",
  "goal_spec_sha256": "c9550b812d3f7a1542cafc68af87afc1bed3a42f94ff7276ba1960c98563b805",
  "permissions": [
    "read_back_issue47_and_owner_authority",
    "modify_only_declared_issue47_owned_paths",
    "run_local_and_no_model_remote_verification",
    "create_path_explicit_checkpoint_commits",
    "push_only_codex_issue47_collaboration_wiring_branch",
    "create_update_and_read_back_issue47_draft_pr",
    "post_and_read_back_issue47_progress_authority_and_blocker_comments",
    "launch_bounded_codex_implementation_and_repair_contexts",
    "launch_bounded_independent_ubuntu_claude_infrastructure_reviews",
    "merge_issue47_pr_only_after_required_checks_independent_review_and_branch_protection",
    "deploy_only_an_exact_reviewed_generation_with_disabled_by_default_activation",
    "install_one_new_unique_scheduler_entrypoint_disabled_by_default",
    "enable_the_new_entrypoint_only_for_an_exact_separately_approved_product_goal_trial",
    "run_one_bounded_real_product_canary_after_all_separate_product_authority_privacy_and_governance_gates",
    "stop_and_rollback_the_new_issue47_entrypoint_while_preserving_evidence"
  ],
  "resource_acknowledgement": {
    "work_period": "2026-10-31T09:15:00+08:00/2026-11-20T18:00:00+08:00",
    "work_window": "MON-FRI 09:00-18:00 + 2026-10-31 and 2026-11-01 preapproved engineering windows; Oct31 DAILY cap override only",
    "max_model_concurrency": 1,
    "codex_max_per_workday": 3,
    "codex_max_total": 18,
    "codex_known_preapproval": 10,
    "claude_max_per_workday": 2,
    "claude_max_total": 12,
    "claude_known_preapproval": 2,
    "paid_api_fallback": false,
    "history_reset_forbidden": true,
    "daily_launch_exception": {
      "date": "2026-10-31",
      "scope": "ISSUE47_INFRA_ENGINEERING_ONLY",
      "codex_max_per_workday": 5,
      "claude_max_per_workday": 4
    }
  },
  "product_goal_coexistence": "BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE",
  "product_goal_authorized": false,
  "standing_b_scheme_go_live_authorized": false
}
```
