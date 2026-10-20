# KGnote active execution plan

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-D2-T02-TEACHING-PROJECTION",
  "objective": "整合安全教材投影與 Obsidian 優先入口，只處理 Issue #9 已封存產品範圍。",
  "status": "active",
  "active_milestone_id": "D2-T02-TEACHING-PROJECTION",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {
    "date": "2026-10-19",
    "speaker": "product owner",
    "source_path": "https://github.com/joannalee20050914/KGnote-public/issues/9",
    "durable_goal_record": "PLAN.md"
  },
  "requirement_context": {
    "acceptance_criteria": [
      "RC-07",
      "RC-08",
      "RC-12",
      "RC-14",
      "RC-15",
      "RC-16",
      "RC-31",
      "RC-32"
    ],
    "feature_dispositions": [
      "FD-04",
      "FD-05",
      "FD-06",
      "FD-21"
    ],
    "forbidden_substitutes": [
      "Web-first",
      "第二個 editor",
      "猜測 unsupported content",
      "產生新 concept identity"
    ],
    "github_issue": "https://github.com/joannalee20050914/KGnote-public/issues/9"
  },
  "auto_advance": {
    "enabled": true,
    "requires_dependencies_complete": true,
    "automatic_merge": false,
    "implementation_dispatch_budget": 1,
    "claude_review_budget_added": 0
  },
  "milestones": [
    {
      "id": "D2-T02-TEACHING-PROJECTION",
      "title": "整合安全教材投影與 Obsidian 優先入口，只處理 Issue #9 已封存產品範圍。",
      "status": "active",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "src/kgnote/learner_projection/",
        "src/kgnote/obsidian_native/",
        "src/kgnote/personal_alpha/",
        "tests/",
        "docs/requirements/",
        "DEVELOPMENT_PLAIN.md"
      ],
      "acceptance": [
        "held-out natural prose 與 unsupported clause fail-closed",
        "same-input regeneration stable",
        "Obsidian/Web identity read-back",
        "render/click 與實際測試證據"
      ],
      "stop_conditions": [
        "投影需要猜測 unsupported content",
        "產生新 concept identity",
        "取代普通筆記",
        "需要 Claude 第 9 次審查",
        "自動 merge main"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

本次唯一 Codex dispatch 已完成 D2-T02 的有界程式修改，未碰 Source Library、概念 identity、Web-first 或第二 editor。候選加入 source-bounded 初學者入口文字、既有 concept identity 的先備缺口，以及 Obsidian 主入口／Web 次要學習互動的封裝 identity read-back。局部 deterministic suite（42 tests）通過；完整 suite 受此 worker 缺少 `.venv`、`referencing`、Node/npm 與 `gh` 阻擋，尚不得提升 `candidate_verified` 或觸發 review。下一步只能由既有 Runner 在受支援環境重新驗證並處理 publication；不得由本 dispatch 直接發布、merge 或啟動 Claude／ChatGPT Work。
