# KGnote active execution plan

This file contains exactly one active execution goal. It does not promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-HUMAN-GATE-SCHEDULER-CONTINUITY-20261019",
  "objective": "依 2026-10-19 產品擁有人決策，維持雙層 Human Gate 與 PR #26 局部阻擋，並以 Issue #14 完成一次受權、隔離、單次額度的跨 Issue 自動入場，使同一 Runner 可重用於後續完整授權的 Ready Issue。",
  "status": "complete",
  "active_milestone_id": null,
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {"date": "2026-10-19", "speaker": "product owner", "source_path": "PLAN.md", "durable_goal_record": "PLAN.md"},
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/README.md",
    "docs/requirements/DECISIONS_AND_CONFLICTS.md",
    "DEVELOPMENT_PLAIN.md",
    "PLAN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "github_issue": "https://github.com/joannalee20050914/KGnote-public/issues/24",
    "candidate_pull_request": "https://github.com/joannalee20050914/KGnote-public/pull/26",
    "requirements": ["KG-GOV-07", "KG-PLAT-05"],
    "scenarios": ["SC-32", "SC-33", "SC-35"],
    "forbidden_substitutes": [
      "把單一 Human Gate 當成 Runner 全域停止",
      "讓已 SUPERSEDED 的中途 smoke 或 component PASS → human checkpoint 規則由任何 Consumer 重新生效",
      "為保持忙碌而建立未授權需求、branch 或 PR",
      "以重啟或隔日工作時段重設 budget 或重跑完成工作",
      "以相同候選重複呼叫 reviewer 直到得到 PASS",
      "自動 Merge、解除 Legacy Stop Marker 或提升 PA-HUMAN-1、NS-HUMAN-SMOKE、release_verified",
      "修改模型選擇或帳號額度管理"
    ]
  },
  "auto_advance": {
    "enabled": true,
    "requires_dependencies_complete": true,
    "requires_explicit_work_item_authority": true,
    "requires_isolated_worktree": true,
    "requires_sealed_worker_order": true,
    "automatic_merge": false,
    "work_window": "Asia/Taipei weekdays 09:00-18:00"
  },
  "preserved_human_gates": [
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_eligible_incomplete_product_scope", "release_verified": false, "rule": "Issue #21 RC-01 through RC-34, all required features/dependencies/integration/delivery evidence and one exact complete candidate are not yet complete."},
    {"id": "PA-HUMAN-1", "status": "not_evaluated", "release_verified": false, "applicability": "historical_and_final_acceptance_input_not_independent_stop"},
    {"id": "NS-HUMAN-SMOKE", "status": "not_evaluated", "release_verified": false, "applicability": "historical_and_final_acceptance_input_not_independent_stop"}
  ],
  "milestones": [
    {
      "id": "SCHEDULER-CONTINUITY-VERIFICATION",
      "title": "Human Gate scope、Ready selection 與 restart continuity 修正",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "AGENTS.md",
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/REVIEW_PROTOCOL.md",
        ".ai/ORCHESTRATOR_STATE.json",
        "docs/control-plane/AUTHORITY.md",
        "docs/control-plane/authority-lock.json",
        "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
        "docs/control-plane/AUTONOMY_GO_LIVE_APPROVAL_PACKAGE.md",
        "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
        "scripts/codex_control.py",
        "scripts/codex_orchestrator.py",
        "scripts/external_review_control.py",
        "scripts/local_autonomy_runner.py",
        "scripts/cross_issue_admission.py",
        "tests/control_plane/test_codex_orchestrator.py",
        "tests/control_plane/test_exact_review_integration.py",
        "tests/control_plane/test_external_review_control.py",
        "tests/control_plane/test_local_autonomy_runner.py",
        "tests/control_plane/test_cross_issue_admission.py",
        "GitHub Issue #24 and PR #26 status metadata"
      ],
      "acceptance": [
        "既有 Authority 內有可追溯 supersession 對照；舊人工失敗、候選身分與 native evidence 缺口完整保留",
        "SOFT_FEEDBACK_AVAILABLE 只有可操作入口、具體問題與真人價值齊全才建立，按 goal/candidate/scope 去重，無回覆不阻塞且晚到回饋綁定原候選",
        "只有 D2-T14-FINAL-HUMAN-ACCEPTANCE 對完整正式產品候選、全部功能/相依/整合/情境/交付/RC/獨立審查證據與完整入口成立時進入 FINAL_HUMAN_ACCEPTANCE_REQUIRED，且不得自動通過",
        "A-H 無模型 fixture 對 WORK_ITEM_BLOCKED、DEPENDENCY_BLOCKED、GLOBAL_BLOCKED、WAITING_HUMAN_ACCEPTANCE 與 NO_ELIGIBLE_READY_WORK 全數通過",
        "PR #26 Round 3/4 exact identity 與 evidence delta 經一致性規則核對",
        "已修正的 Landlock、PATH、重複派工、publisher parent、full verification、GitHub writeback 與 Human Gate scope 有回歸證據",
        "Runner restart/next window 不重跑完成工作、不重設 budget、不解除 Stop Marker、PR 保護或 merge restriction",
        "真實 Ready 工作只有在既有 authority、dependency、budget、window、isolation 與 sealed order 全部成立時才派遣"
      ],
      "stop_conditions": [
        "需要擴張產品需求、安全權限、付費服務或 Merge authority",
        "無法保留現有 dirty work、checkpoint 或歷史 budget",
        "真實 Ready 工作缺少 execution authority 或安全隔離"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

本 Goal 已完成。雙層人工驗收 authority、Runner、external review 與 orchestrator Consumer 已統一；完整 verifier 綠燈。PR #26 Round 3 與 Round 4 綁定同一 commit/fingerprint，Round 4 未提供可解決 Round 3 blocking finding 的新結構化證據，仍以 `WORK_ITEM_BLOCKED` 保存，不得進入人工產品驗收。GitHub #14 雖標示 `queue:ready`，但尚無 active PLAN、隔離 worktree、bounded budget 與 sealed worker order；Runner 應記錄 `NO_ELIGIBLE_READY_WORK` 並正常 idle，未來合法 Ready work 可按既有 admission 自動接續。
