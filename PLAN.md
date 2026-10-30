# KGnote active execution plan

This plan covers only the owner-authorized O2 v4 exact-successor recovery. It does
not authorize another product model attempt or a new Product Goal authority event.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-SUCCESSOR-RECOVERY-20261030",
  "active_goal": "CODEX-APP-GOAL-O2-SUCCESSOR-RECOVERY-20261030",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "保全 attempt 1 的 exact successor，修正 pre-publication verification 與 trusted publication/recovery control，經 exact verification、獨立 Ubuntu Claude infrastructure review、正常合併與受控雙主機部署後，只追加一筆去重的正式 successor recovery event，讓既有無模型驗證／發布／產品審查流程承接而不再次消耗 Codex。",
  "status": "active",
  "active_milestone_id": "R2-EXACT-VERIFY-REVIEW-MERGE",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-successor-recovery-2026-10-30",
  "explicit_direction": {
    "date": "2026-10-30",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_SUCCESSOR_RECOVERY_DIRECTION_20261030.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_SUCCESSOR_RECOVERY_DIRECTION_20261030.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json",
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
      "infrastructure_main": "4388aa2a8d7c63cf2b81a7314176f646eec9a276",
      "goal_version": "2026-10-29.4-bounded-trial-day0-proposal",
      "goal_spec_sha256": "7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f",
      "state_sha256": "6c644af8ad65172dd3235e1f01fad429d11ea30864a823465bcfe226ac73f0ec",
      "ledger_sha256": "849301d3778faded3153101f318792ea390b109d7ff8f169e61c922bd9040328",
      "ledger_cursor": 8,
      "attempt_id": "attempt-2026-10-29.4-bounded-trial-day0-proposal-WI-O2-A-IMPLEMENT-1",
      "successor_commit": "95d437a20ee31e48a49e2ee9b6f83ca3d4a931a6",
      "successor_tree": "b2a66a296d2a76d8b79ce5343eb8447f6e9421ff",
      "successor_fingerprint": "a08eccbee8f62560a8c5e279096b5a9befd94755b40e4b40f648e0ffa17a8904",
      "codex_charges": 4,
      "codex_ceiling": 5,
      "transition_start_slo": "VIOLATED"
    },
    "forbidden_substitutes": [
      "再次啟動產品 Codex/Claude、建立新 reservation 或增加／重置額度",
      "直接修改正式 state/ledger/checkpoint、覆寫 seq 1–8 或重分類原失敗 attempt",
      "刪除 Legacy PR #28 契約、偽造 GitHub snapshot 或交付 GitHub 寫入憑證給產品模型",
      "未經 exact verification、Ubuntu Claude infrastructure PASS、正常 PR merge、雙主機部署與無模型驗收即 append",
      "修改 Owner APPROVE、Goal version/digest、日期、SLO 或 human gates",
      "重建 v5、擴張自治框架或把 recovery 視為 Product Goal 完成"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "4388aa2a8d7c63cf2b81a7314176f646eec9a276",
    "branch": "codex/o2-successor-recovery-20261030",
    "base_branch": "main",
    "pull_request": null,
    "automatic_merge": true,
    "merge_authority": "exact verification plus independent Ubuntu Claude infrastructure PASS and normal GitHub rules under the owner recovery direction"
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
    {"id": "O2-PRODUCT-CLAUDE-REVIEW", "status": "NOT_STARTED", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "R0-PRESERVE-AND-HOLD",
      "title": "保全 exact evidence 並停止自動派工",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["output/control-plane/"],
      "acceptance": [
        "28 份保存檔逐一 SHA-256 read-back，Git bundle 可重建 exact successor",
        "正式 state/ledger 與保存快照 byte-identical，cursor=8、Codex=4/5",
        "正式 LaunchAgent 以既有 launchctl bootout 安全卸載且 plist 未修改"
      ]
    },
    {
      "id": "R1-IMPLEMENT-AND-ISOLATED-ACCEPTANCE",
      "title": "最小 pre-publication verifier、可信 publication binding 與一次性 recovery writer",
      "status": "complete",
      "dependencies": ["R0-PRESERVE-AND-HOLD"],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_SUCCESSOR_RECOVERY_DIRECTION_20261030.md",
        "scripts/codex_control.py", "scripts/product_goal_worker_lane.py", "scripts/local_autonomy_runner.py",
        "scripts/goal_runner_adapter.py", "scripts/o2_successor_recovery.py", "scripts/o2_prepublication_control_tests.py",
        "scripts/install_ubuntu_worker_runtime.py",
        "config/ubuntu-worker-runtime-manifest.json", "tests/control_plane/", "output/control-plane/"
      ],
      "acceptance": [
        "O2 exact successor 在無產品 PR 時通過完整 local deterministic verification，並明示 remote identity gate 尚待 publication",
        "Legacy PR #28 路徑保持不變；正式 publication 仍要求 exact PR/branch/HEAD/fingerprint receipt",
        "writer 綁定 exact attempt/successor/evidence/authority/state/ledger/accounting 並只 append 一個 idempotent transition",
        "錯 parent/commit/tree/fingerprint、缺 checkpoint、bundle tamper、authority/cursor drift、verification failure 與 duplicate 均 fail closed",
        "所有測試不啟動模型、不建立正式 reservation、不改正式資料"
      ]
    },
    {
      "id": "R2-EXACT-VERIFY-REVIEW-MERGE",
      "title": "deployment migration blocker 修復、exact verification、Ubuntu Claude infrastructure review 與正常合併",
      "status": "active",
      "dependencies": ["R1-IMPLEMENT-AND-ISOLATED-ACCEPTANCE"],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md", "CODEX_STATUS.md", ".ai/", "output/control-plane/", "GitHub PR metadata",
        "docs/control-plane/O2_SUCCESSOR_RECOVERY_DIRECTION_20261030.md",
        "scripts/install_ubuntu_worker_runtime.py", "tests/control_plane/test_ubuntu_worker_runtime.py"
      ],
      "acceptance": [
        "舊 active generation 缺少新引入且無舊 shim 的 reviewed compatibility entrypoint 時可原子升級；既有／dangling shim、hash drift 與 cold-start failure 仍 fail closed 或 rollback",
        "candidate fingerprint stable 且 evidence read-back PASS",
        "independent Ubuntu Claude infrastructure verdict PASS and no blocking findings",
        "PR exact HEAD/fingerprint read-back 後依 GitHub 規則合併，不 bypass/force push"
      ]
    },
    {
      "id": "R3-CONTROLLED-DEPLOYMENT",
      "title": "Mac/Ubuntu immutable runtime 受控部署與無模型驗收",
      "status": "pending",
      "dependencies": ["R2-EXACT-VERIFY-REVIEW-MERGE"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "output/control-plane/", "Mac immutable Runner runtime", "Ubuntu immutable worker runtime"],
      "acceptance": [
        "兩端 current runtime generation 綁定同一 merged revision/tree/manifest",
        "真正無模型 Router/publication path 接受有效 exact evidence，錯誤 evidence fail closed",
        "既有 activation receipts 與 Owner authority 不回填、不失效",
        "Runner 仍保持卸載且無新增 model attempt/accounting"
      ]
    },
    {
      "id": "R4-ONE-TIME-RECOVERY-APPEND",
      "title": "驗證 exact successor 後執行一次正式 append 與 read-back",
      "status": "pending",
      "dependencies": ["R3-CONTROLLED-DEPLOYMENT"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "output/control-plane/", "formal O2 state and ledger through trusted recovery writer only"],
      "acceptance": [
        "Ubuntu exact successor 完整 pre-publication verification PASS",
        "check-only 與 apply 前正式 hashes/cursor/authority/accounting 完全相符",
        "只追加一筆去重 WORK_STATE_TRANSITION；seq 1–8 與 failed attempt 保留",
        "candidate 前進到 95d437a；WI-O2-A-VERIFY 為下一個無模型步驟，非 DISPATCH_IMPLEMENTATION",
        "Codex 仍為 4/5，沒有新增產品 Codex/Claude attempt 或 paid API"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The formal Runner remains unloaded under the existing trusted LaunchAgent control.
Only the isolated infrastructure worktree may change before merge and deployment.
The formal append is authorized only after milestones R1 through R3 are green.
