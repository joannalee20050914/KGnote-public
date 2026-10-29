# KGnote active execution plan

This file continues the bounded O2 Day 0 execution Goal only for the admission
event identity repair. It does not authorize a Product Goal model launch or a
formal state/ledger mutation.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-DAY0-ACCELERATION-20261029",
  "active_goal": "CODEX-APP-GOAL-O2-DAY0-ACCELERATION-20261029",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "最小修復 O2 v4 Mac receipt validator 對 admission Router event identity 的錯誤比對，完成 exact verification、Ubuntu Claude PASS、正常 PR 合併、雙主機受控部署及真正無模型正反驗收，同時完整保留正式 v4 authority/state/ledger/receipts/accounting。",
  "status": "active",
  "active_milestone_id": "D1-EXACT-VERIFICATION-AND-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-admission-event-id-repair-2026-10-29",
  "explicit_direction": {
    "date": "2026-10-29",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_ADMISSION_EVENT_ID_REPAIR_DIRECTION_20261029.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_ADMISSION_EVENT_ID_REPAIR_DIRECTION_20261029.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json",
    "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07", "KG-PLAT-08"],
    "acceptance_criteria": ["RC-05", "RC-07", "RC-08", "RC-12", "RC-14", "RC-15", "RC-16", "RC-31", "RC-32"],
    "feature_dispositions": ["FD-04", "FD-05", "FD-06", "FD-21"],
    "scenarios": ["SC-32", "SC-33", "SC-35", "SC-40", "SC-44", "SC-45", "SC-48"],
    "formal_baseline": {
      "main_commit": "8a242fff318af636b937e9f9540d0121fa9c0191",
      "goal_version": "2026-10-29.4-bounded-trial-day0-proposal",
      "goal_spec_sha256": "7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f",
      "state_sha256": "b033d1ee0b0305d4d1dbf042b31cc6c3d4b985d6b946068d7584afb666a5bfc4",
      "ledger_sha256": "fb031f16a52f3d22ccc5b197cafd030fa34b299060a165aa339ca025b6202b13",
      "ledger_cursor": 3,
      "codex_charges": 3,
      "codex_ceiling": 5,
      "v4_attempts": 0,
      "transition_start_slo": "VIOLATED"
    },
    "forbidden_substitutes": [
      "刪除 event-ID 檢查、只驗證前綴或合併產品與 admission 事件身分",
      "修改正式 v4 state、ledger、checkpoints、三份 activation receipts、Owner APPROVE 或 Goal spec/digest",
      "手動建立 DISPATCH_RESERVED、虛構模型紀錄、重發 APPROVE/RESUME 或重置額度",
      "把 2026-10-29 transition-start SLO VIOLATED 改寫為 PASS",
      "略過 exact verification、Ubuntu Claude review、正常 GitHub merge 或受控雙主機部署",
      "在正式工作時段外啟動產品模型或建立新的自治框架"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "8a242fff318af636b937e9f9540d0121fa9c0191",
    "branch": "codex/o2-admission-event-id-repair-20261029",
    "base_branch": "main",
    "pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under this bounded repair direction"
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "external_review_required_before_merge": true,
    "max_review_cycles_per_milestone": 5
  },
  "preserved_human_gates": [
    {"id": "O2-V4-OWNER-AUTHORITY", "status": "ACTIVE_UNCHANGED", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "D0-MINIMAL-VERSION-SEAL",
      "title": "封存首次派工根因與正式唯讀基線",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "docs/control-plane/O2_ADMISSION_EVENT_ID_REPAIR_DIRECTION_20261029.md"],
      "acceptance": ["正式 v4 無 reservation/attempt 且失敗位於計帳前", "根因精確定位為 Router admission ID 與產品 WorkOrder ID 的錯誤等同比對"]
    },
    {
      "id": "D1-EXACT-VERIFICATION-AND-REVIEW",
      "title": "最小 validator/fixture 修復與 exact verification",
      "status": "active",
      "dependencies": ["D0-MINIMAL-VERSION-SEAL"],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md", "CODEX_STATUS.md", ".ai/",
        "docs/control-plane/O2_ADMISSION_EVENT_ID_REPAIR_DIRECTION_20261029.md",
        "scripts/product_goal_runtime_admission.py", "scripts/linux_worker_router.py",
        "config/ubuntu-worker-runtime-manifest.json", "tests/control_plane/", "output/control-plane/"
      ],
      "acceptance": [
        "Router 與 validator 共用 challenge + WorkOrder SHA-256 + exact runtime identity 的 canonical admission event ID",
        "產品 order_event_id 仍與 WorkOrder、receipt、Worker evidence 精確一致",
        "共用 fixture 不再冒用產品 event ID；真正 Router path 正向驗收通過",
        "錯 event ID/challenge/WorkOrder hash/runtime identity/checkpoint tamper 全在 ledger append 前 fail closed",
        "targeted/full verification、requirements guard、strict diff、public safety 與 exact fingerprint 全綠"
      ]
    },
    {
      "id": "D2-CLAUDE-REVIEW-AND-MERGE",
      "title": "Ubuntu Claude exact review 與正常 GitHub 整合",
      "status": "pending",
      "dependencies": ["D1-EXACT-VERIFICATION-AND-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "output/control-plane/", "GitHub PR metadata"],
      "acceptance": ["PR 綁定 exact HEAD/fingerprint", "Ubuntu Claude canonical verdict PASS 且無 blocking findings", "依 GitHub 規則正常合併，無 bypass/force push"]
    },
    {
      "id": "D3-DEPLOY-AND-NO-MODEL-ACCEPTANCE",
      "title": "雙主機受控部署與真正無模型正反驗收",
      "status": "pending",
      "dependencies": ["D2-CLAUDE-REVIEW-AND-MERGE"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "output/control-plane/", "Mac immutable Runner runtime", "Ubuntu immutable worker runtime"],
      "acceptance": [
        "Mac Runner 與 Ubuntu current generation 讀回同一 merged revision/tree/manifest",
        "隔離合法 authority/WorkOrder 經真正 Router admission 產生 checkpoint 並由 Mac validator 接受",
        "錯誤 admission identity 仍在計帳前拒絕，無產品模型啟動",
        "歷史 activation receipts 不回填且 v4 authority 契約無衝突",
        "正式 v4 state/ledger/checkpoints/receipts/APPROVE hashes 不變，Codex accounting 仍為 3/5"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Work occurs only in the isolated branch/worktree rooted at merged deployment
baseline `8a242ff`. Formal O2 v4 runtime data remains read-only. The first
eligible product continuation is tomorrow's ordinary Runner window and is not
part of implementation or deployment acceptance.
