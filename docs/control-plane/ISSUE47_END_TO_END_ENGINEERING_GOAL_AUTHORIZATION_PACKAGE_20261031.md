# Issue #47 — 限時週末自治架設工程特例授權包
Status: OWNER_APPROVAL_REQUIRED until the exact GitHub comment is posted and validated.
This is an immutable successor version of the existing Codex App engineering Goal; not a KGnote Product Goal, canary or standing go-live approval.

## Exact identity
- Repository / Issue: `joannalee20050914/KGnote-public` / `#47`
- Goal ID: `CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION` (unchanged)
- Goal version: `2026-10-31.2-weekend-engineering-exception`
- Spec path: `docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json`
- Canonical JSON SHA-256: `8f3036ec6429e2f8f1e546aea3a8b3bf1c0cb1459e742991a4228612836958cd`
- Frozen predecessor: `2026-10-30.1-owner-approval-proposal` with digest `f78a49397822bf17a89f7477be2efe840c0dddfa58cf767153cf31281bdcdce4`
- Branch for this Owner amendment: `owner/issue47-weekend-engineering-exception-20261031`, based on `7b4accdbff4869284217dd96fc6857271ec690c3`; do not force-push or rewrite the Codex working branch.

## Exactly what changes
- Engineering start moves to Saturday 2026-10-31 09:15 Asia/Taipei. The existing Monday-Friday 09:00–18:00 envelope and Nov 20 hard stop are unchanged.
- **Only** Saturday Oct 31 09:15–18:00 and Sunday Nov 1 09:00–18:00 are additional engineering work windows. Later weekends are **not** opened. The new `work_period.exception_work_windows` must be schema-validated and explicitly enforced by the local no-model time gate before any model attempt.
- Scope is Issue #47 infrastructure setup and verified engineering review only. No Pikambler/Product Goal work, model-bearing product canary, standing go-live, or activation of standing scheduler under the weekend exception.
- Codex total ceiling remains 18, and now conservatively carries **at least 7** observed launches as of Saturday morning; 11 or fewer remain. Claude total remains 12 with 0 observed. Same per-day ceilings, one concurrent model, subscription login only, and no paid API.
- All other operations, O2 read-only protection, PR/branch protection, reviewer independence, human gates, security, and rollback are unchanged.
- Existing 3/3 time-only blocked audit and prior run evidence must not be erased. If and only if the exact weekend authority and no-model time gate PASS and no other blocker exists, append a scoped resolution and continue. No reset to launch counters, blocked history, or modified evidence.

## Deployment/safety proviso
This new version does not amend or disable the existing O2 Runner. Before model work, Codex must import and validate the new exact spec and the extended time gate, update its current PLAN/STATUS/checkpoint consistently, and run positive/negative tests for Oct31, Nov1, Nov7, Nov8 and out-of-window times. A stale local checkout or prior version cannot use this approval. If code lacks explicit exception support, fail closed and adapt it without bypassing the guard. If a separate human Product Goal approval or final go-live gate is reached, stop there as before.

## Exact Owner reply
The GitHub repository Owner posts this exact marker and JSON as a **new** Issue #47 comment, not a reply to an old comment. This approves only this amended engineering Goal spec and does not itself start a Mac/Ubuntu model session.

<!-- kgnote-codex-app-engineering-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "goal_version": "2026-10-31.2-weekend-engineering-exception",
  "goal_spec_sha256": "8f3036ec6429e2f8f1e546aea3a8b3bf1c0cb1459e742991a4228612836958cd",
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
    "work_window": "MON-FRI 09:00-18:00 + 2026-10-31 09:15-18:00 / 2026-11-01 09:00-18:00 engineering-only Asia/Taipei",
    "max_model_concurrency": 1,
    "codex_max_per_workday": 3,
    "codex_max_total": 18,
    "codex_known_preapproval": 7,
    "claude_max_per_workday": 2,
    "claude_max_total": 12,
    "claude_known_preapproval": 0,
    "paid_api_fallback": false,
    "history_reset_forbidden": true
  },
  "product_goal_coexistence": "BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE",
  "product_goal_authorized": false,
  "standing_b_scheme_go_live_authorized": false
}
```
