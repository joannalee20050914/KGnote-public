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
  "objective": "保留 PR #32 與 PR #33 已審查證據，先關閉 O2 試行開始與硬截止的執行層缺口並取得新精確候選 PASS，再依法合併、部署、讀回及演練 rollback，最後停在唯一的 GitHub Owner Product Goal APPROVE。",
  "status": "active",
  "active_milestone_id": "S3-TRIAL-SCHEDULE-ADMISSION",
  "milestone_id": "S3-TRIAL-SCHEDULE-ADMISSION",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-formal-merge-deploy-handoff-2026-10-26",
  "explicit_direction": {
    "date": "2026-10-26",
    "speaker": "product owner",
    "source_path": "Codex App attachment pasted-text.txt (S2 formal merge, deployment and O2 bounded-trial handoff instruction)",
    "durable_goal_record": "PLAN.md"
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
    "base_revision": "204a3ef951c441dbdafb1e31bf14297820bc0577",
    "branch": "codex/o2-trial-schedule-admission-20261026",
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
      "status": "complete",
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
      "id": "S3-TRIAL-SCHEDULE-ADMISSION",
      "title": "部署前補足 O2 試行開始與硬截止准入",
      "status": "active",
      "dependencies": ["S02-VERIFY-REVIEW-DRAFT-PR"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "scripts/goal_runner_adapter.py", "tests/control_plane/test_product_goal_runtime_wiring.py", "tests/control_plane/test_product_goal_dynamic_order.py"],
      "acceptance": [
        "即使 Owner 提前 APPROVE，2026-10-28T09:00:00+08:00 前的正式 next_action、dynamic order 與 dispatch reservation 都拒絕新 O2 派工",
        "2026-11-10T18:00:00+08:00 起永久拒絕新 O2 派工，重啟 Runner、重開 Codex App、切換工作窗或重讀 GitHub 命令不能繞過",
        "硬截止後仍可結算截止前已持久化的 dispatch reservation 與 checkpoint evidence，但不能建立另一項工作",
        "邊界測試覆蓋提前一天、開始瞬間、截止前、截止瞬間、截止後與 restart；時間來自 Runner clock 且固定 spec/version/digest 不由模型更改",
        "requirements guard、targeted/full tests、exact-candidate verification 與 Ubuntu Claude formal review 對新候選通過；舊 Review 005 PASS 不被重綁"
      ]
    },
    {
      "id": "S4-FORMAL-MERGE-DEPLOY-HANDOFF",
      "title": "正式合併、部署、讀回、rollback 與 Owner 核准交接",
      "status": "pending",
      "dependencies": ["S3-TRIAL-SCHEDULE-ADMISSION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "GitHub PR #32/#33 metadata", "Mac deployment runtime", "Ubuntu deployment runtime", "LaunchAgent configuration"],
      "acceptance": [
        "依相依順序合法合併 PR #32、PR #33 與必要的精確 schedule-admission successor，不使用 force push 或管理員繞過",
        "由最終 main 建立 clean detached immutable deployment worktree，完整 staging/compile/import 後切換 Mac Runner、Ubuntu runtime、schema 與依賴",
        "LaunchAgent、Goal spec/state/ledger、Writer Lock、Stop Marker、時段、配額、GitHub/SSH 可達性及未授權零派工全部 read-back",
        "完成一次無模型、無正式 GitHub 寫入的 isolated activation/rollback rehearsal，保存可回復資產與收據",
        "部署後只交付 Issue #9 exact Owner APPROVE 原始命令；Codex 不代發且 O2 不在批准前 ACTIVE"
      ]
    },
    {
      "id": "BOUNDED-TRIAL-AUTHORIZATION",
      "title": "Product Owner 首次真實有界試行授權",
      "status": "pending",
      "dependencies": ["S4-FORMAL-MERGE-DEPLOY-HANDOFF"],
      "human_gate": "required",
      "owned_paths": [],
      "acceptance": ["Product Owner 以核准包指定的 GitHub Issue 精確核准 Goal version、spec digest、資源上限與試行權限"]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

PR #32 `de5c8c01` 與 PR #33 `204a3ef9` 的既有 PASS 均保留；Review 005 不涵蓋本次新發現的 schedule-admission 缺口。S3 現在只修正式 `next_action`、dynamic order creation 與 dispatch reservation 的 immutable trial start／hard stop 守門及必要回歸。新 exact candidate 必須完成 deterministic verification 與 Ubuntu Claude formal review，通過後才可自動進入 S4 合併部署。O2 仍未啟動，Owner APPROVE 仍未發布。
