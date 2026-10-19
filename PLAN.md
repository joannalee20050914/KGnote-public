# KGnote active execution plan

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-TUTOR-HANDOFF-20261019",
  "objective": "Issue #14/D2-T07：有限確認外部 AI 導師的受支援授權能力，保留 copy-safe manual handoff/import 與 delta de-duplication；不啟用 cookie automation、live data、付費或自動 merge。",
  "status": "active",
  "active_milestone_id": "D2-T07-BOUNDED-FEASIBILITY",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {
    "date": "2026-10-19",
    "speaker": "product owner",
    "source_path": "https://github.com/joannalee20050914/KGnote-public/issues/14",
    "durable_goal_record": "PLAN.md"
  },
  "requirement_context": {
    "github_issue": "https://github.com/joannalee20050914/KGnote-public/issues/14",
    "feature_dispositions": [
      "FD-11"
    ],
    "acceptance_criteria": [
      "RC-20",
      "RC-21",
      "RC-28",
      "RC-31"
    ],
    "requirements": [
      "KG-MEM-08",
      "KG-PLAT-03"
    ],
    "scenarios": [
      "SC-03",
      "SC-32"
    ],
    "forbidden_substitutes": [
      "browser-cookie automation",
      "未授權資料外送",
      "自動付費",
      "把手動 fallback 當成自動 connector 已驗證"
    ]
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
      "id": "D2-T07-BOUNDED-FEASIBILITY",
      "title": "合法授權與手動備援有限驗證",
      "status": "active",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/CROSS_ISSUE_ADMISSION.json",
        ".ai/work-package-envelope.json",
        ".ai/DECISIONS.md",
        ".ai/ORCHESTRATOR_STATE.json",
        ".ai/REVIEW_REQUEST.md",
        ".ai/REVIEW_RESULT.md",
        ".ai/WORK_ITEM_REVIEW_HISTORY/issue-14-d2-t07/",
        "docs/control-plane/",
        "scripts/codex_control.py",
        "scripts/cross_issue_admission.py",
        "src/kgnote/",
        "tests/"
      ],
      "acceptance": [
        "官方授權能力有來源證據或明確 unsupported 結論",
        "manual handoff/import fallback 可操作",
        "round-trip delta 不重複 evidence",
        "不啟用 live provider、cookie automation、資料外送或付費"
      ],
      "stop_conditions": [
        "需要 live data、付費、cookie 擷取、資料外送或新增 reviewer 額度",
        "超出一次 Codex implementation dispatch"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

由正式 cross-Issue admission 建立；先執行 preflight，僅處理 Issue #14 有界範圍。
