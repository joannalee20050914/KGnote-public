# KGnote active execution plan

This file contains one Codex App execution Goal. It prepares a bounded real-product trial but does not authorize or start a KGnote Product Goal.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-S0-S2-LAUNCH-PACKAGE-20261023",
  "active_goal": "CODEX-APP-GOAL-O2-S0-S2-LAUNCH-PACKAGE-20261023",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "在不修改 PR #32 已審查候選、不啟動 O2 worker 或正式 LaunchAgent 的前提下，完成 O2 真實產品試行 S0 契約、S1 真實派工與結果接線、S2 隔離部署與回復驗證，交付一次性 Owner 核准包。",
  "status": "active",
  "active_milestone_id": "S02-VERIFY-REVIEW-DRAFT-PR",
  "milestone_id": "S02-VERIFY-REVIEW-DRAFT-PR",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-s0-s2-launch-preparation-2026-10-23",
  "explicit_direction": {
    "date": "2026-10-23",
    "speaker": "product owner",
    "source_path": "Codex App attachments pasted-text.txt (S0–S2 execution request and bounded-trial design proposal)",
    "durable_goal_record": "docs/control-plane/O2_S0_S2_LAUNCH_PREPARATION_DIRECTION_20261023.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md",
    "docs/control-plane/O2_S0_S2_LAUNCH_PREPARATION_DIRECTION_20261023.md",
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
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07", "KG-PLAT-08", "KG-ALPHA-02", "KG-CTX-10", "KG-KNOW-09"],
    "acceptance_criteria": ["RC-05", "RC-07", "RC-08", "RC-12", "RC-14", "RC-15", "RC-16", "RC-27", "RC-28", "RC-29", "RC-31", "RC-32", "RC-33", "RC-34"],
    "feature_dispositions": ["FD-04", "FD-05", "FD-06", "FD-12", "FD-14", "FD-17", "FD-18", "FD-19", "FD-21", "FD-23"],
    "scenarios": ["SC-32", "SC-33", "SC-35", "SC-40", "SC-44", "SC-45", "SC-48"],
    "forbidden_substitutes": [
      "為使測試通過而跳過 Stop Marker、移除負向斷言或放寬路徑驗證",
      "移動或刪除既有 Home 平行 KGnote 資產，或改寫 sealed Legacy work item 的精確路徑",
      "把 Codex App Goal、Draft PR 或測試 PASS 視為 Product Goal 授權、Owner APPROVE、B-SCHEME-GO-LIVE 或人類產品驗收",
      "用 ChatGPT Work 通知未驗證阻擋 GitHub Issue 通知的首次試行",
      "以不可觀測的訂閱剩餘比例假造資源授權，或新增付費 API",
      "新增 Agent、第二套 Orchestrator、Dashboard、資料庫或管理平台",
      "用單一 IMPLEMENT 工作項目、預填未來 SHA、有限人工補單佇列或模型成功退出冒充 A 到 B 的持續接力",
      "把離線／模擬 PASS 冒充五日真實產品試行或 Mac Obsidian 人工驗收"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "de5c8c01c86ffc87896dca1337817892bfb5eff6",
    "branch": "codex/o2-s0-s2-launch-package-20261023",
    "stacked_on_pull_request": 32,
    "draft_pull_request": 33,
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
  "deadline": "2026-10-27T18:00:00+08:00",
  "milestones": [
    {
      "id": "S0-TRIAL-CONTRACT",
      "title": "固定 A／B、資源、期限與人工介入契約",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "docs/requirements/", "tests/control_plane/"],
      "acceptance": [
        "O2 同一 Product Goal 以 A 閱讀／來源回查與 B 原句便利貼兩個獨立可驗證 Work Item 表達，且不刪減原義務",
        "Codex 與 Ubuntu Claude 各自有歷史依據、預排工作、修復／重審餘裕、每窗與 Goal-total 的確定上限；concurrency=1、09:00–18:00、backoff、no-paid-API 與不重置規則保留",
        "五日觀察、十日硬截止、10 分鐘交接、兩次跨窗、一次安全重啟、0 次普通人工接力與 50 分鐘監督上限被固定為未開始的驗收契約",
        "所有人類 gate、不授權事項、PR #29 Legacy findings 與 PR #32 精確 PASS 身分保持分離"
      ]
    },
    {
      "id": "S1-DISPATCH-RESULT-WIRING",
      "title": "證明並補足真實派工與結果接線",
      "status": "complete",
      "dependencies": ["S0-TRIAL-CONTRACT"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "schemas/product-goal/", "scripts/", "tests/control_plane/"],
      "acceptance": [
        "沿 Mac Runner 到 Linux router、Codex／Publisher／Claude、worker result、checkpoint、state／ledger 的實際路徑完成可重現稽核",
        "IMPLEMENT、VERIFY／PUBLISH、REVIEW、CHANGES_REQUIRED REPAIR、新候選再驗證／審查及 A→B 都有非人工補檔的合法 order／binding 產生來源",
        "真實 worker result envelope 保留 attempt、commit／fingerprint、失敗分類、verification、publication read-back、review verdict/findings、usage／429 與 next Work Item",
        "任何缺口以最小修復、正反測試、checkpoint-first restart 及 integration read-back 關閉；未知結果不盲目重派模型"
      ]
    },
    {
      "id": "S2-DEPLOYMENT-READINESS",
      "title": "隔離部署演練與一次性 Owner 核准包",
      "status": "complete",
      "dependencies": ["S1-DISPATCH-RESULT-WIRING"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "docs/requirements/", "scripts/", "tests/control_plane/"],
      "acceptance": [
        "重用 PR #32 de5c8c0 的精確 PASS 且不修改該候選；新候選只審查新差異與完整整合結果",
        "無模型隔離演練核對集中 worktree/common-dir、Runner/router/worker/schema、Goal state/ledger、binding、checkpoint-first、Writer Lock、Stop Marker、epoch/scope、Owner identity 與 rollback",
        "正式部署的合併順序、immutable commit、LaunchAgent 全參數、spec path/digest、初始化/read-back、啟用前檢查、Owner command、資源上限、日期算法、停止與回復被集中成一次決策",
        "正式 Runner 保持 dormant、O2 未啟動，模擬證據不冒充 live trial"
      ]
    },
    {
      "id": "S02-VERIFY-REVIEW-DRAFT-PR",
      "title": "完整驗證、獨立審查與相依 Draft PR",
      "status": "active",
      "dependencies": ["S2-DEPLOYMENT-READINESS"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "docs/requirements/", "scripts/", "tests/control_plane/"],
      "acceptance": [
        "requirements guard、targeted/integration/full tests、public safety scan、git diff --check 與 exact-candidate verifier 通過",
        "精確候選完成獨立 Ubuntu Claude review，findings 關閉或形成具體阻擋",
        "建立 stacked Draft PR，清楚列出 PR #32 依賴、目的、範圍、驗證、風險與回復",
        "最終狀態只能是 READY_FOR_OWNER_AUTHORIZATION、BLOCKED_WITH_SPECIFIC_GAPS 或 NOT_READY_WITHIN_TIMEBOX"
      ]
    },
    {
      "id": "BOUNDED-TRIAL-AUTHORIZATION",
      "title": "Product Owner 首次真實有界試行授權",
      "status": "pending",
      "dependencies": ["S02-VERIFY-REVIEW-DRAFT-PR"],
      "human_gate": "required",
      "owned_paths": [],
      "acceptance": ["Product Owner 以核准包指定的 GitHub Issue 精確核准 Goal version、spec digest、資源上限與試行權限"]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

This Goal is stacked on immutable PR #32 candidate `de5c8c01c86ffc87896dca1337817892bfb5eff6`; PR #32 and its exact PASS remain unchanged. S0, S1 and S2 are complete. Review 004 full-contact preflight proved that its legitimate descriptive `review_scope` would be downgraded to `CODE_REVIEW_ONLY` and that the Adapter checkpoint lacked a canonical `REVIEW_SUBMITTED` bridge. Review 004 was invalidated before model dispatch; its trigger and evidence remain immutable. The bounded repair now binds the exact descriptive scope in the goal-scoped config, preserves non-matching scopes as code-review-only, and converts only an exact terminal Adapter checkpoint plus matching work order into Ingestion. Targeted tests and the first post-repair deterministic verifier passed; checkpoint commit, final exact-candidate re-verification, Review 005 sealing/publication/deployment and live reviewer execution remain. O2 is not active and no Owner command was published.
