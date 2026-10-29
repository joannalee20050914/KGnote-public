# KGnote active execution plan

This file contains one bounded S2 admission-safety repair Goal. It does not
authorize `RESUME` or another O2 product-model attempt.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-RUNTIME-RECEIPT-PRE-RESERVATION-20261029",
  "active_goal": "CODEX-APP-GOAL-O2-RUNTIME-RECEIPT-PRE-RESERVATION-20261029",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "在正式 O2 保持 PAUSED、既有三次 reservation 與額度不變的前提下，讓所有正式 model-bearing dispatch 在 MODEL_ATTEMPT_STARTED/DISPATCH_RESERVED 前通過綁定 exact WorkOrder、candidate、正式授權與 immutable runtime generation 的最新 Ubuntu 無模型實機准入，並由 reserve_dispatch 本身 fail closed 防止繞過。",
  "status": "active",
  "active_milestone_id": "A2-EXACT-VERIFICATION-AND-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-runtime-receipt-pre-reservation-2026-10-29",
  "explicit_direction": {
    "date": "2026-10-29",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07", "KG-PLAT-08"],
    "acceptance_criteria": ["RC-05", "RC-07", "RC-08", "RC-12", "RC-14", "RC-15", "RC-16", "RC-27", "RC-28", "RC-29", "RC-31", "RC-32", "RC-33", "RC-34"],
    "feature_dispositions": ["FD-17", "FD-18", "FD-19", "FD-21", "FD-23"],
    "scenarios": ["SC-32", "SC-33", "SC-35", "SC-48"],
    "reused_read_only_audit": {
      "codex_task_title": "審核部署後模型派工關卡",
      "baseline": "8fc5a7f99cf5d01afa9bb544ba3774ee7cdf11ba",
      "conclusion": "Existing Ubuntu checks occur after reservation; add a real no-model admission route plus a mandatory fresh receipt gate inside reserve_dispatch."
    },
    "formal_runtime_baseline": {
      "main_commit": "44f36b40791d375d74b9b161c81c92e9f8e65ea7",
      "runtime_generation": "44f36b40791d375d74b9b161c81c92e9f8e65ea7",
      "runtime_manifest_sha256": "b86d9e4ee94dfa2ad9b058ce784bb712aa242ec13aa9311afcf5b3c248863a42",
      "runtime_receipt_sha256": "484da34d3da35432f861e6b4cbf9a83d6fcd25b847778a2b66ea71346ca9fd95",
      "state_sha256": "5786046a481f412b945dc58664758dbe3d7202040ba275fa77ced617acbb3765",
      "ledger_sha256": "a88d1f1c563a3845ae3e75ec6fb302352fe9648978e444c28c5b8f8b559afbdb",
      "ledger_cursor": 26,
      "work_item_attempts": 3,
      "goal_launches_used": 3,
      "model_attempts": 2,
      "fourth_attempt_present": false
    },
    "forbidden_substitutes": [
      "建立第二套 Runner、Router、Worker、systemd、Landlock 或自治派工框架",
      "用 repository mock、--help 或部署 receipt 單獨冒充正式 pre-reservation live admission",
      "重用 PAUSED Product Goal 的歷史 ACTIVE/RESUME order、context 或 authority 作為測試身分",
      "只在 local_autonomy_runner 呼叫前檢查而允許其他 caller 直接繞過 reserve_dispatch",
      "接受缺失、stale、已使用或 WorkOrder/candidate/authority/runtime 身分不符的 receipt",
      "通過 admission 後允許 model execution 改用不同 runtime generation 或 drifted bytes",
      "刪除、重分類或重置三次歷史 reservation/launch accounting，或增加正式額度",
      "發布 RESUME、新增 O2 產品派工、修改正式 Goal 時程或提升人工/release gate"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "44f36b40791d375d74b9b161c81c92e9f8e65ea7",
    "branch": "codex/o2-runtime-receipt-pre-reservation-20261029",
    "base_branch": "main",
    "draft_pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under this bounded repair direction"
  },
  "immutable_product_goal": {
    "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
    "goal_version": "2026-10-23.2-s0-s2-proposal",
    "goal_spec_sha256": "82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604",
    "authority_lease": "PAUSED",
    "lifecycle": "BLOCKED",
    "go_live_authorized": false,
    "trial_start": "2026-10-28T09:00:00+08:00",
    "hard_stop": "2026-11-10T18:00:00+08:00"
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
    {"id": "O2-AUTHORITY-LEASE", "status": "PAUSED", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "A0-BASELINE-AND-MINIMAL-DESIGN",
      "title": "重用唯讀審核並固定最小 receipt/admission 契約",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md", "docs/control-plane/B_SCHEME_OPERATIONS.md"],
      "acceptance": [
        "以 44f36b4 為基準，讀回 Codex B 唯讀審核與 PR #38 W4 實機證據，不重新設計自治架構",
        "最小方案明確區分 deployment admission identity 與正式 PAUSED Product Goal identity",
        "receipt 契約綁定 exact order/candidate/authority/runtime 並定義 freshness、single-use 與 execution pinning"
      ]
    },
    {
      "id": "A1-IMPLEMENT-AND-NEGATIVE-TESTS",
      "title": "實作 no-model admission、reserve gate 與版本 pinning",
      "status": "complete",
      "dependencies": ["A0-BASELINE-AND-MINIMAL-DESIGN"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "config/", "scripts/goal_runner_adapter.py", "scripts/local_autonomy_runner.py", "scripts/linux_worker_router.py", "scripts/linux_worker_bootstrap.py", "scripts/product_goal_worker_identity.py", "scripts/product_goal_worker_lane.py", "scripts/product_goal_worker_result.py", "scripts/install_ubuntu_worker_runtime.py", "tests/control_plane/", "docs/control-plane/B_SCHEME_OPERATIONS.md"],
      "acceptance": [
        "deployment admission-only 使用獨立測試身分與證據目錄，完整走 SSH/bootstrap/systemd/guard/Landlock/Worker 且 model_launches=0",
        "reserve_dispatch 缺少、過期、已使用或身分不符 receipt 時 fail closed 且不追加 ledger/state",
        "normal dispatch 綁定同一 immutable generation，model Popen 前重驗 manifest/file hashes",
        "缺模組、缺 lock、hash drift、錯 checkout、SSH/bootstrap/Landlock 失敗與 stale receipt 負例通過",
        "任何 admission FAIL 都證明 attempt/dispatch/checkpoint/model 不增加且正式 state/ledger bytes 不變"
      ]
    },
    {
      "id": "A2-EXACT-VERIFICATION-AND-REVIEW",
      "title": "exact-candidate verification、Draft PR 與 Ubuntu Claude 獨立審查",
      "status": "active",
      "dependencies": ["A1-IMPLEMENT-AND-NEGATIVE-TESTS"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "output/control-plane/", "config/", "scripts/goal_runner_adapter.py", "scripts/local_autonomy_runner.py", "scripts/linux_worker_router.py", "scripts/linux_worker_bootstrap.py", "scripts/product_goal_worker_identity.py", "scripts/product_goal_worker_lane.py", "scripts/product_goal_worker_result.py", "scripts/product_goal_runtime_admission.py", "scripts/install_ubuntu_worker_runtime.py", "tests/control_plane/", "docs/control-plane/B_SCHEME_OPERATIONS.md", "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md", "GitHub Draft PR metadata", "existing Ubuntu Claude review runtime"],
      "acceptance": [
        "targeted/full tests、requirements guard、strict diff、public safety 與 exact fingerprint/read-back 全綠",
        "Draft PR 綁定 exact HEAD/fingerprint；只有既有 Ubuntu Claude 對同一候選的 canonical PASS 可授權整合"
      ]
    },
    {
      "id": "A3-MERGE-DEPLOY-PAUSED-ADMISSION",
      "title": "正常整合、限縮部署與 PAUSE 下實機無模型正反向驗收",
      "status": "pending",
      "dependencies": ["A2-EXACT-VERIFICATION-AND-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub PR/main metadata", "Ubuntu immutable runtime", "formal read-only state/ledger/checkpoint evidence", "output/control-plane/"],
      "acceptance": [
        "依正常 GitHub rules 整合 exact PASS candidate，未 direct push/force/bypass",
        "限縮部署到新 immutable generation，於 PAUSE 下執行 admission-only 正向與指定負向驗收且模型啟動為 0",
        "正式 state/ledger/checkpoints 前後完整 SHA、cursor、attempt 與歷史計帳完全相同",
        "最終明確區分無模型准入 PASS 與真正產品模型開發 NOT VERIFIED"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The minimal contract and implementation milestone are complete on the isolated
repair worktree. Formal O2 remains `PAUSED`/`BLOCKED`; state, ledger and formal
checkpoints remain read-only. The active milestone is exact-candidate
verification and the existing Ubuntu Claude independent review. Merge,
deployment and PAUSED real-host acceptance remain downstream of exact PASS.
