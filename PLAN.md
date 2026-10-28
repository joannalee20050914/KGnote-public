# KGnote active execution plan

This file contains one bounded Control Plane recovery Goal. It does not authorize another O2 product-model attempt or a `RESUME` command.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-RUNTIME-CONTEXT-RECOVERY-20261028",
  "active_goal": "CODEX-APP-GOAL-O2-RUNTIME-CONTEXT-RECOVERY-20261028",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "以同一個有界候選修復 Ubuntu Codex 的 Runner-verified O2 上下文、正式開發環境與證據式錯誤分類；append-only 更正兩次既有失敗，經 deterministic verification、既有 Ubuntu Claude 獨立審查、正常 PR 合併與正式部署讀回完成，全程維持 PAUSE 且不新增模型派工。",
  "status": "active",
  "active_milestone_id": "R3-INDEPENDENT-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-runtime-context-recovery-2026-10-28",
  "explicit_direction": {
    "date": "2026-10-28",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_RUNTIME_CONTEXT_RECOVERY_DIRECTION_20261028.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_RUNTIME_CONTEXT_RECOVERY_DIRECTION_20261028.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
    "docs/control-plane/O2_BOUNDED_TRIAL_AUTHORIZATION_PACKAGE_20261023.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "DEVELOPMENT_PLAIN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07", "KG-PLAT-08"],
    "acceptance_criteria": ["RC-05", "RC-07", "RC-08", "RC-12", "RC-14", "RC-15", "RC-16", "RC-27", "RC-28", "RC-29", "RC-31", "RC-32", "RC-33", "RC-34"],
    "feature_dispositions": ["FD-17", "FD-18", "FD-19", "FD-21", "FD-23"],
    "scenarios": ["SC-32", "SC-33", "SC-35", "SC-48"],
    "formal_runtime_baseline": {
      "deployed_commit": "9271bf8645858eed49effa8eca3df8ea491bfc17",
      "pause_comment_id": "6458880366",
      "ledger_cursor": 15,
      "state_sha256": "b2f2e37c3e15ba9733f07ea31f4b27276da7f69aa1434f07a7ee658d72cf446d",
      "ledger_sha256": "19515c795f59e10cdcfacdb3dad47f06c9c526548c2ba7aa13a04de1b0c21415",
      "work_item_attempts": 2,
      "model_attempts": 2,
      "third_attempt_present": false
    },
    "forbidden_substitutes": [
      "以 repository PLAN.md 或 CODEX_STATUS.md 冒充 Runner 已驗證的執行授權與即時工作狀態",
      "只在 prompt 解釋環境問題，而未在模型啟動前驗證 exact checkout、Python、Node/npm、gh 與必要工具",
      "掃描任意文件／transcript 的 quota、429 或 rate limit 字樣後宣稱 provider RATE_LIMITED",
      "覆寫舊 ledger、checkpoint 或 raw logs，或重置 attempt／launch／resource accounting",
      "發布 RESUME、重新 APPROVE、啟動第三次模型工作或提升任何 human/release gate",
      "force push、管理員繞過、直接寫 main、重用 stale PASS 或部署未經 exact review 的 bytes"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "9271bf8645858eed49effa8eca3df8ea491bfc17",
    "branch": "codex/o2-runtime-context-recovery-20261028",
    "base_branch": "main",
    "draft_pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under the 2026-10-28 bounded repair instruction"
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
      "id": "R0-PRODUCTION-EVIDENCE-RECONCILIATION",
      "title": "讀回正式 PAUSE、兩次 raw stdout/stderr、checkpoint 與部署身分",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_RUNTIME_CONTEXT_RECOVERY_DIRECTION_20261028.md"],
      "acceptance": [
        "正式 state/ledger 為 BLOCKED/PAUSED/go_live_authorized=false 且 ledger cursor=15",
        "兩次 raw stdout/stderr 與 checkpoint hashes 相符，沒有 provider HTTP 429、quota response 或 recovery time",
        "Work Item A attempts=2，沒有第三次 reservation、attempt 或 Ubuntu checkpoint",
        "PR #35 merge/deploy commit、LaunchAgent Python 與 Runner journal 已唯讀讀回"
      ]
    },
    {
      "id": "R1-THREE-ISSUE-REPAIR",
      "title": "修復 sealed runtime context、Ubuntu dev environment 與 evidence-based classification/recovery",
      "status": "complete",
      "dependencies": ["R0-PRODUCTION-EVIDENCE-RECONCILIATION"],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "requirements-runtime.lock",
        "scripts/codex_jsonl_evidence.py", "scripts/goal_continuity.py", "scripts/goal_runner_adapter.py",
        "scripts/product_goal_worker_result.py", "scripts/product_goal_worker_lane.py",
        "scripts/product_goal_worker_identity.py", "scripts/linux_worker_bootstrap.py", "scripts/linux_worker_router.py",
        "scripts/local_autonomy_runner.py", "scripts/successor_codex_entrypoint.py",
        "scripts/install_ubuntu_worker_runtime.py", "scripts/reconcile_o2_attempt_classification.py",
        "schemas/", "tests/control_plane/"
      ],
      "acceptance": [
        "每個 Ubuntu order 帶有完整、sealed、Runner-verified Goal/Owner/lifecycle/work/candidate/ledger context，Codex 不從 stale PLAN/STATUS 推導執行授權",
        "Ubuntu 在模型前驗證 exact repository/ref/HEAD/tree/cleanliness、Python、Node/npm、gh 與依賴；失敗不呼叫 provider/model process，既有 conservative reservation accounting 不重置",
        "failure classifier 只接受可定位的 structured provider/error evidence，文件或 transcript prose 中 quota/429 不會命中 RATE_LIMITED",
        "append-only correction helper 驗證兩次 immutable evidence、正式 PAUSE 與 ledger tail，追加正確分類而不改舊 ledger 或重置計數",
        "所有新增 schema、replay、tamper、negative-path 與 compatibility tests 通過"
      ]
    },
    {
      "id": "R2-EXACT-VERIFICATION",
      "title": "全套正反向驗證與 exact-candidate sealing",
      "status": "complete",
      "dependencies": ["R1-THREE-ISSUE-REPAIR"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "tests/control_plane/", "output/control-plane/"],
      "acceptance": [
        "requirements guard、targeted/full Python、Node、public-safety、diff check 與 completion verifier 全綠",
        "隔離 projection 證明 PAUSE 下不派工、pre-model environment failure 不呼叫 provider/model process、context/replay/tamper fail closed",
        "exact candidate commit/tree/fingerprint/manifest 與 evidence read-back 相符"
      ]
    },
    {
      "id": "R3-INDEPENDENT-REVIEW",
      "title": "正常 Draft PR 與既有 Ubuntu Claude exact-candidate review",
      "status": "active",
      "dependencies": ["R2-EXACT-VERIFICATION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub repair PR metadata", "existing Ubuntu Claude review runtime"],
      "acceptance": [
        "單一 base=main repair PR 綁定 exact candidate commit/tree/fingerprint",
        "Ubuntu Claude 直接檢查三個原始問題、negative tests、append-only reconciliation 與 no-RESUME boundary",
        "只有 exact PASS 且 GitHub rules satisfied 才能正常合併；CHANGES_REQUIRED 進入新 candidate cycle"
      ]
    },
    {
      "id": "R4-MERGE-DEPLOY-RECONCILE-READBACK",
      "title": "正常合併、正式 Runner 部署、append-only 歷史更正與 PAUSE 讀回",
      "status": "pending",
      "dependencies": ["R3-INDEPENDENT-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub main/PR metadata", "Mac Runner deployment/runtime", "Ubuntu runtime", "formal append-only state/ledger evidence"],
      "acceptance": [
        "正式 Runner、Ubuntu runtime 與 LaunchAgent 使用 reviewed merge commit/tree 及可信 Python/toolchain",
        "兩次 classification correction 以 append-only events 綁定原 checkpoint/raw hashes，舊 events 與 launch/attempt accounting 不變",
        "正式狀態仍為 BLOCKED/PAUSED/go_live_authorized=false，Runner 為 WAIT_AUTHORITY",
        "Work Item A attempts 仍為 2，沒有第三次 reservation、attempt、model launch 或 Ubuntu checkpoint",
        "未發布 RESUME；部署與 reconciliation receipts 可重放、可稽核"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The formal Runner has consumed PAUSE comment `6458880366`; Work Item A remains at exactly two attempts. The active slice repairs the runtime context, pre-model Ubuntu environment, and evidence-based failure classification as one candidate. Deployment and append-only historical reconciliation are authorized only after exact verification and independent review. `RESUME` and a third product-model attempt remain forbidden.
