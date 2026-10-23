# KGnote active execution plan

This file contains one Codex App execution Goal. It prepares a bounded real-product trial but does not authorize or start a KGnote Product Goal.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-B-TRIAL-READINESS-20261023",
  "active_goal": "CODEX-APP-GOAL-B-TRIAL-READINESS-20261023",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "收斂 B 方案集中目錄部署相容性，保留 Legacy Ledger、Stop Marker、Checkpoint 與既有授權身分，並為第一個合法真實 Product Goal 準備一次可由 Product Owner 單次核准的有界試行契約、部署步驟、回復方式與 Draft PR；不得啟動 Product Goal 或 B-SCHEME-GO-LIVE。",
  "status": "active",
  "active_milestone_id": "BTR-3-VERIFY-REVIEW-DRAFT-PR",
  "milestone_id": "BTR-3-VERIFY-REVIEW-DRAFT-PR",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-bounded-product-trial-readiness-2026-10-23",
  "explicit_direction": {
    "date": "2026-10-23",
    "speaker": "product owner",
    "source_path": "Codex App attachment pasted-text.txt",
    "durable_goal_record": "docs/control-plane/BOUNDED_TRIAL_READINESS_DIRECTION_20261023.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md",
    "docs/control-plane/BOUNDED_TRIAL_READINESS_DIRECTION_20261023.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/CLAUDE_REVIEWER_ROLE_DECISION_20261020.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
    "DEVELOPMENT_PLAIN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07"],
    "acceptance_criteria": ["RC-27", "RC-28", "RC-29", "RC-32", "RC-33", "RC-34"],
    "feature_dispositions": ["FD-12", "FD-14", "FD-17", "FD-18", "FD-19", "FD-23"],
    "scenarios": ["SC-32", "SC-33", "SC-35"],
    "forbidden_substitutes": [
      "為使測試通過而跳過 Stop Marker、移除負向斷言或放寬路徑驗證",
      "移動或刪除既有 Home 平行 KGnote 資產，或改寫 sealed Legacy work item 的精確路徑",
      "把 Codex App Goal、Draft PR 或測試 PASS 視為 Product Goal 授權、Owner APPROVE、B-SCHEME-GO-LIVE 或人類產品驗收",
      "用 ChatGPT Work 通知未驗證阻擋 GitHub Issue 通知的首次試行",
      "以不可觀測的訂閱剩餘比例假造資源授權，或新增付費 API",
      "新增 Agent、第二套 Orchestrator、Dashboard、資料庫或管理平台"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "7bb0ffb4be6d5eb19398f249f45fa8e32a083131",
    "branch": "codex/b-scheme-trial-readiness-20261023",
    "draft_pull_request": null,
    "automatic_merge": false
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "formal_product_goal_go_live": false,
    "max_review_cycles_per_milestone": 5
  },
  "preserved_human_gates": [
    {"id": "B-SCHEME-GO-LIVE", "status": "not_authorized", "release_verified": false},
    {"id": "BOUNDED-TRIAL-AUTHORIZATION", "status": "not_authorized", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "BTR-1-PATH-SAFETY-COMPATIBILITY",
      "title": "集中目錄測試與建立器安全相容性",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "scripts/cross_issue_admission.py", "scripts/local_autonomy_runner.py", "tests/control_plane/"],
      "acceptance": [
        "重現並精確診斷 test_stop_marker_allows_only_private_smoke_canary_order 的集中目錄失敗",
        "測試與正式 Runner 使用同一 integration-root 解析契約，Stop Marker、private smoke canary、work admission 與執行身分限制均保留",
        "錯誤路徑、symlink escape、不合法 canary、越權工作及 non-bare repository 內嵌 worktree 仍 fail closed",
        "Legacy sealed path 原樣可讀；新 Product Goal worktree 預設落在核准集中根目錄，不再自動建立新的 Home 平行 KGnote-* 目錄",
        "舊路徑 fixture 與集中目錄 fixture 均通過，正式 Runner 維持 dormant 且零模型啟動"
      ]
    },
    {
      "id": "BTR-2-FIRST-PRODUCT-GOAL-PACKAGE",
      "title": "首個真實 Product Goal 與 Legacy disposition 核准包",
      "status": "complete",
      "dependencies": ["BTR-1-PATH-SAFETY-COMPATIBILITY"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "docs/control-plane/", "docs/requirements/", "DEVELOPMENT_PLAIN.md", "tests/control_plane/"],
      "acceptance": [
        "依 Backlog、Issue #9、PR #29、Round 4 finding 與 Feature Disposition Ledger 選出第一個合法真實 Product Goal",
        "保留所有歷史 1/1、3/3、8/8 等 budget、Ledger、Stop Marker、Checkpoint 與 review 身分，不把未解 finding 宣稱完成",
        "產出精確 Goal ID/version/spec digest、成功條件、禁止替代、工作時段、concurrency=1、provider／付費限制、launch ceilings、quota/no-progress/rollback、Claude review 與人類驗收",
        "清楚區分 bounded trial authorization 與 full B-SCHEME-GO-LIVE，採 GitHub Issue 做正式核准與通知，ChatGPT Work 保持可選"
      ]
    },
    {
      "id": "BTR-3-VERIFY-REVIEW-DRAFT-PR",
      "title": "完整驗證、獨立審查與 Draft PR",
      "status": "active",
      "dependencies": ["BTR-2-FIRST-PRODUCT-GOAL-PACKAGE"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "docs/requirements/", "scripts/", "tests/control_plane/"],
      "acceptance": [
        "原有環境與集中目錄環境的 targeted regression、完整 deterministic verification、requirements guard、secret/public-safety scan 與 read-back 通過",
        "精確候選完成 repository-mediated independent review，所有 blocking findings 關閉或保留為直接證據阻擋",
        "建立 main-based Draft PR，內容含目的、範圍、驗證、風險、回復與正式 Runner dormant read-back",
        "若所有工程與核准材料完備，狀態只能提升為 READY_FOR_BOUNDED_TRIAL_AUTHORIZATION；不得啟動 trial 或 Go-live"
      ]
    },
    {
      "id": "BOUNDED-TRIAL-AUTHORIZATION",
      "title": "Product Owner 首次真實有界試行授權",
      "status": "pending",
      "dependencies": ["BTR-3-VERIFY-REVIEW-DRAFT-PR"],
      "human_gate": "required",
      "owned_paths": [],
      "acceptance": ["Product Owner 以核准包指定的 GitHub Issue 精確核准 Goal version、spec digest、資源上限與試行權限"]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

PR #31 已合併至 `main`，B 方案程式已部署但 `B-SCHEME-GO-LIVE` 未授權。本 Goal 只處理集中目錄相容性與首次真實 Product Goal 核准準備；正式 Runner、Product Goal 與 Owner 命令均保持 dormant／未發布。完成工程、獨立審查與 Draft PR 後，唯一允許的人類停點是 `BOUNDED-TRIAL-AUTHORIZATION`。
