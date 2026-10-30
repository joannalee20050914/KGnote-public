# Issue #47 單一工程 Goal 授權包

Status: `OWNER_APPROVAL_REQUIRED`. This package requests execution authority for
one Codex App engineering Goal. It does not approve a KGnote Product Goal, a
live canary, product acceptance, or standing B-scheme go-live.

## Exact identity

- Repository: `joannalee20050914/KGnote-public`
- Issue: `#47`
- Goal ID: `CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION`
- Goal version: `2026-10-30.1-owner-approval-proposal`
- Spec: `docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json`
- Canonical JSON SHA-256: `f78a49397822bf17a89f7477be2efe840c0dddfa58cf767153cf31281bdcdce4`
- Schema: `schemas/codex-app-engineering-goal/v1/goal-spec.schema.json`

Canonical digest means SHA-256 over the parsed JSON serialized with UTF-8,
sorted object keys, no insignificant whitespace, and separators `,` / `:`.
The file-byte digest is evidence only; authority binds the canonical digest.

## Resource proposal to confirm once

- Work period: 2026-11-02 09:00 through 2026-11-20 18:00, `Asia/Taipei`.
- Work window: Monday-Friday, 09:00-18:00.
- Model concurrency: one.
- Codex: at most 3 launches per workday and 18 total. Two known Issue #47
  preapproval Codex contexts are conservatively carried, so 16 remain if
  approved.
- Claude: at most 2 launches per workday and 12 total; none carried.
- Every retry, review, repair, unknown reserved attempt, context/session restart,
  and cross-day continuation shares the same provider total. A new date,
  version, branch, PR, worktree, or restart cannot reset it.
- Existing subscription login only; paid API fallback is forbidden.

## What approval would permit

Approval permits the exact operations enumerated in the immutable spec,
including path-explicit checkpoint commits, the Issue #47 branch and PR,
bounded Codex implementation/repair, bounded independent Ubuntu Claude
infrastructure review, no-model remote verification, exact reviewed deployment,
and a new disabled-by-default scheduler entrypoint. Merge is limited to the
Issue #47 PR after branch protection, required checks, independent review, and
remote identity read-back pass.

Approval does not permit a live Product Goal merely because infrastructure is
ready. A live canary still requires its own immutable Product Goal spec, exact
Owner approval, privacy/data-egress boundary, and remaining-resource admission.
Standing B-scheme go-live still requires a separate Owner decision after trial.

## O2 uniqueness resolution

The proposed policy is `BOUNDED_EXCLUSIVE_TRIAL_COEXISTENCE`:

- O2 v4 remains `ACTIVE`, but its formal Runner stays disabled/unloaded and its
  authority, state, ledger cursor 9, Codex 4/5 accounting, checkpoints, quota,
  and archive are immutable read-only.
- A future canary may use a separate Product Goal only after its own exact Owner
  approval. It receives separate state, ledger, worktree, PR, and review config.
- The existing global writer lock plus the new launcher must prove there is at
  most one model-bearing writer. Detecting a runnable O2 path, old Runner,
  competing reservation, or duplicate scheduler fails closed.
- The old O2 Runner is never re-enabled and no O2 runtime bytes or usage are
  copied into the new Goal.

Approving this engineering spec approves only that bounded governance policy and
the engineering work. It does not itself activate the future Product Goal.

## Exact Owner reply

The Owner must post the following marker and JSON as a new comment on Issue #47.
Codex must not post this approval on the Owner's behalf or infer it from the
earlier DRAFT comment.

<!-- kgnote-codex-app-engineering-goal-authority:v1 -->
```json
{
  "schema_version": "kgnote.codex-app-engineering-goal-authority-command.v1",
  "action": "APPROVE",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "goal_version": "2026-10-30.1-owner-approval-proposal",
  "goal_spec_sha256": "f78a49397822bf17a89f7477be2efe840c0dddfa58cf767153cf31281bdcdce4",
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
    "work_period": "2026-11-02T09:00:00+08:00/2026-11-20T18:00:00+08:00",
    "work_window": "MON-FRI 09:00-18:00 Asia/Taipei",
    "max_model_concurrency": 1,
    "codex_max_per_workday": 3,
    "codex_max_total": 18,
    "codex_known_preapproval": 2,
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

Any changed Goal version, digest, permission, resource value, coexistence choice,
or repository/Issue identity requires a new immutable spec and new Owner reply.
