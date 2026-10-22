# KGnote active execution plan

This file contains one Codex App execution Goal. It implements the B-scheme control plane but is not a KGnote Product Goal authorization.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-B-CONTINUOUS-DELEGATION-20261022",
  "active_goal": "CODEX-APP-GOAL-B-CONTINUOUS-DELEGATION-20261022",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "實作 B 方案 Goal 級持續委任：保留既有欄位相容性，以 GitHub Owner 精確核准作為 KGnote Product Goal 唯一執行授權，由 Mac Runner 管理跨 Session／工作時段的有界開發、驗證、發布、Claude 審查、修復、結案與下一 Goal 核准交接；完成測試、隔離試行與 Draft PR 後停止，不直接 go-live。",
  "status": "active",
  "active_milestone_id": "B5-REPLAY-TRIAL-DELIVERY",
  "milestone_id": "B5-REPLAY-TRIAL-DELIVERY",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-goal-scoped-continuous-delegation-2026-10-22",
  "explicit_direction": {
    "date": "2026-10-22",
    "speaker": "product owner",
    "source_path": "Codex App user instruction and attached B-scheme implementation brief",
    "durable_goal_record": "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md",
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
      "將 Codex App Goal 狀態視為 KGnote Product Goal 授權或結案",
      "以 Agent 建立的 Issue、一般留言、Project 欄位或 session 變更自行增加權限",
      "以 token、context 或估算冒充可信訂閱剩餘百分比",
      "把模型啟動、usage、verdict、產品義務完成合併成一個 used 計數",
      "清除或重置 Issue #9 Ledger、429、review、checkpoint、Stop Marker 或 budgets",
      "新增第二套 Orchestrator、Dashboard、資料庫或 Agent",
      "自動 merge main、修改 branch protection、付費 API fallback 或啟用無界委任"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "f81ccdde369c7ab9468ed07ca1fdab6d8f0b60e0",
    "branch": "codex/goal-continuous-delegation-20261022",
    "draft_pull_request": 31,
    "automatic_merge": false
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "formal_product_goal_go_live": false
  },
  "preserved_human_gates": [
    {"id": "B-SCHEME-GO-LIVE", "status": "not_authorized", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "B1-ARCHITECTURE-AUTHORITY-AUDIT",
      "title": "正式架構、部署與授權語意核對",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "scripts/", "tests/control_plane/", "schemas/product-goal/"],
      "acceptance": [
        "正式 Mac Runner、Ubuntu Codex/Claude、Verifier/Publisher、PR #29 與 Ledger 身分均有 read-back",
        "Codex App Goal、Product Goal 與 Work Item 身分、authority source 及 lifecycle 明確分離",
        "既有 PR #29 Round 4 與 429 事件被指定為 immutable migration fixtures，不取得新權限"
      ]
    },
    {
      "id": "B2-GOAL-CONTRACT-LEDGER",
      "title": "Product Goal 委任、狀態與分離結算契約",
      "status": "complete",
      "dependencies": ["B1-ARCHITECTURE-AUTHORITY-AUDIT"],
      "human_gate": "none",
      "owned_paths": ["docs/control-plane/", "schemas/product-goal/", "scripts/goal_continuity.py", "scripts/github_product_goal_control.py", "tests/control_plane/"],
      "acceptance": [
        "GitHub Owner、Goal version、spec digest、權限與撤回狀態 fail closed 驗證",
        "authorization、model attempt、usage、verdict、publication 與 obligation progress 分別記錄",
        "舊 schema/fields 可讀且不被重寫；App Goal 狀態不得轉成 Product Goal transition"
      ]
    },
    {
      "id": "B3-RUNNER-RECOVERY-CONVERGENCE",
      "title": "Runner 有界恢復與產品義務收斂",
      "status": "complete",
      "dependencies": ["B2-GOAL-CONTRACT-LEDGER"],
      "human_gate": "none",
      "owned_paths": ["scripts/local_autonomy_runner.py", "scripts/goal_continuity.py", "scripts/goal_runner_adapter.py", "tests/control_plane/"],
      "acceptance": [
        "CHANGES_REQUIRED、429、工作時段、未知結果、Publisher/GitHub failure 可按既有 authority 自動續接",
        "同一產品義務跨 finding rename 可識別，兩次無進展先做 bounded strategy adjustment",
        "受影響 dependency subgraph 可停，無依賴的合法工作仍可選；不重複模型或副作用"
      ]
    },
    {
      "id": "B4-BACKLOG-APPROVAL-NOTIFICATION",
      "title": "預備 Goal backlog、核准／結案交接與通知",
      "status": "complete",
      "dependencies": ["B3-RUNNER-RECOVERY-CONVERGENCE"],
      "human_gate": "none",
      "owned_paths": ["docs/control-plane/", "scripts/goal_continuity.py", "scripts/github_product_goal_control.py", "tests/control_plane/"],
      "acceptance": [
        "O2–O7 依現有成果整理成可維護 Goal specs 與依賴，不把舊 active 宣告當授權",
        "前一 Product Goal 未 CLOSED 時下一 Goal 不可核准或執行；Owner 舊版本／錯誤身分核准被拒",
        "決策通知具唯一身分、持久化、去重及 ack；Work 未實測時如實使用 GitHub fallback"
      ]
    },
    {
      "id": "B5-REPLAY-TRIAL-DELIVERY",
      "title": "歷史重播、隔離試行、完整驗證與 Draft PR",
      "status": "active",
      "dependencies": ["B4-BACKLOG-APPROVAL-NOTIFICATION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "schemas/product-goal/", "scripts/", "tests/control_plane/", "tests/fixtures/control_plane/"],
      "acceptance": [
        "Issue #9 指定歷史事件無模型 replay 通過，舊 Ledger 與新 reducer 共存且不重置",
        "路徑 A 證明同一已批准 Goal 可跨 CHANGES_REQUIRED、quota、工作時段續接；路徑 B 證明 CLOSED 後下一 Goal 仍等待 Owner 核准",
        "完整 deterministic verification、preflight、secret scan、read-back 與 isolated no-model trial 通過",
        "建立 main-based 可回復 Draft PR；正式 Product Goal go-live 保持未授權"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Milestones B1–B4 are complete. Product Goal identity/authority schemas, append-only separated accounting, dormant Runner recovery adapter, O2–O7 backlog, decision-only notification layer and rollback runbook are implemented. The 25-event Issue #9 replay and 53-event isolated paths A/B pass with zero model calls and zero external writes. Draft PR #31 is open. Review 008 was invalidated before reviewer custody after a completion audit found recovery deadlocks; the repaired candidate now has durable no-model recovery releases, unknown-checkpoint idempotence, affected-subgraph blocking and GitHub notification delivery/read-back evidence. B5 remains active for exact-candidate Review 009 and final publication read-back; `B-SCHEME-GO-LIVE` remains a separate preserved Owner gate and is not part of this implementation milestone.
