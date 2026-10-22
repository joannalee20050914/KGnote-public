# KGnote active execution plan

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-CODEX-COMPLETION-GATE-20261022",
  "objective": "最小化強化既有 Codex candidate-complete 與送交 Ubuntu Claude 前的驗證：以 PR #29 三輪真實 findings 證明錯誤替代實作與缺少精確候選證據會被 fail closed，不修改 Issue #9 產品候選、不新增 Agent、不改預算或 Stop Marker。",
  "status": "active",
  "active_milestone_id": "CONTROL-REVIEW-COMPLETION-GATE",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {
    "date": "2026-10-22",
    "speaker": "product owner",
    "source_path": "current task: KGnote Goal 強化 Codex 產品修復完成標準與送審前驗證",
    "durable_goal_record": "PLAN.md"
  },
  "requirement_context": {
    "requirements": ["KG-GOV-01", "KG-GOV-04", "KG-GOV-05", "KG-GOV-06", "KG-GOV-07", "KG-VAL-01"],
    "scenarios": ["SC-35"],
    "review_cases": [
      "https://github.com/joannalee20050914/KGnote-public/pull/29#issuecomment-6285208843",
      "https://github.com/joannalee20050914/KGnote-public/pull/29#issuecomment-6285487763",
      "https://github.com/joannalee20050914/KGnote-public/pull/29#issuecomment-6285693992"
    ],
    "candidate_case": "be8fc7eeaac93d86b6921504ce11a1bac51a0dc0",
    "forbidden_substitutes": [
      "以同源 JSON 自我比對或新建靜態 HTML 取代真正既有 Web 消費端驗證",
      "以測試程序 exit 0 取代 exact HEAD、fingerprint、完整 gate 與 evidence read-back",
      "將 NOT_VERIFIED、FIXED_PENDING_REVIEW 或人工產品品質提升為 PASS／VERIFIED",
      "修改 PR #29 產品功能、歷史 Claude findings、預算、Stop Marker 或正式 Runner 部署"
    ]
  },
  "auto_advance": {
    "enabled": false,
    "automatic_merge": false,
    "automatic_deploy": false,
    "automatic_review_dispatch": false
  },
  "preserved_human_gates": [
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false},
    {"id": "ISSUE9-CLAUDE-BUDGET", "status": "exhausted_3_of_3_preserved", "release_verified": false},
    {"id": "ISSUE9-CODEX-REPAIR-BUDGET", "status": "exhausted_2_of_2_preserved", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "CONTROL-REVIEW-COMPLETION-GATE",
      "title": "Codex 修復完成與送審前證據 gate",
      "status": "active",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/REVIEW_REQUEST.md",
        ".ai/ORCHESTRATOR_STATE.json",
        ".ai/REVIEW_PROTOCOL.md",
        ".ai/schemas/review-request.schema.json",
        "docs/requirements/evidence/codex-review-completion-gate-20261022.json",
        "scripts/codex_control.py",
        "tests/control_plane/"
      ],
      "completion_gate": {
        "evidence_path": "docs/requirements/evidence/codex-review-completion-gate-20261022.json",
        "required_claims": [
          {
            "claim_id": "issue9-false-web-identity-proof",
            "required_product_entrypoints": ["scripts/codex_control.py"],
            "required_evidence_kinds": ["positive_test", "negative_test", "read_back"],
            "required_scenarios": ["SC-35"]
          },
          {
            "claim_id": "issue9-missing-exact-candidate-evidence",
            "required_product_entrypoints": ["scripts/codex_control.py"],
            "required_evidence_kinds": ["positive_test", "negative_test", "read_back"],
            "required_scenarios": ["SC-35"]
          }
        ]
      },
      "acceptance": [
        "PR #29 的假 Web/Obsidian 身分驗證反例會在 review-request sealing 前失敗",
        "缺少 exact candidate full verification 或 evidence read-back 的反例會在 review-request sealing 前失敗",
        "有 authority、正反向測試、真正 entrypoint 與必要證據的案例通過",
        "未宣告 completion_gate 的其他 milestone 不被強加此檢查",
        "必要 render/click/read-back 若為 NOT_VERIFIED 則不得進入正式 review request",
        "Reviewer finding 只能由 Codex 標 FIXED_PENDING_REVIEW，不能標 VERIFIED",
        "完整 deterministic verification 對精確 HEAD/fingerprint 通過，成果保存於獨立 Draft PR，且不觸發 Claude 或部署"
      ],
      "stop_conditions": [
        "需要修改 Issue #9 產品功能、重做 Runner/Router/Publisher/Consumer 或新增 Reviewer/Agent",
        "需要改動全域預算、清除 Stop Marker、合併 main 或觸發正式 Claude review",
        "既有產品契約不足以裁決且需要真正產品決策"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Work only in the isolated worktree on branch `codex/issue9-completion-gate-20261022`, based on `origin/main` commit `0b4adf8e3eebd48db3c240db63606a97ae0a7103`. PR #29 remains an untouched Draft at `be8fc7ee`; its three canonical findings are test fixtures and authority evidence only. The production Runner LaunchAgent remains deployed but stopped by existing runtime state; do not edit its checkout or Stop Marker.
