# KGnote active execution plan

This file contains one bounded O2 reauthorization-readiness engineering Goal.
It does not authorize `APPROVE`, `RESUME`, `ACCEPT` or a product-model launch.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-V3-REAUTHORIZATION-READINESS-20261029",
  "active_goal": "CODEX-APP-GOAL-O2-V3-REAUTHORIZATION-READINESS-20261029",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "以已部署 main 93b6b1f 為基準，建立 O2 v3 immutable 候選、歷史承接與不可繞過的 exact pre-reservation admission，經獨立 Claude PASS、正常 GitHub 整合、Mac/Ubuntu 同版部署及隔離無模型正反驗收後，產生等待 Product Owner 決策的最小重新授權包。",
  "status": "active",
  "active_milestone_id": "A2-EXACT-VERIFICATION-AND-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-v3-reauthorization-readiness-2026-10-29",
  "explicit_direction": {
    "date": "2026-10-29",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_V3_REAUTHORIZATION_READINESS_DIRECTION_20261029.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_V3_REAUTHORIZATION_READINESS_DIRECTION_20261029.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.3.json",
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
    "formal_history_baseline": {
      "goal_version": "2026-10-23.2-s0-s2-proposal",
      "goal_spec_sha256": "82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604",
      "state_sha256": "5786046a481f412b945dc58664758dbe3d7202040ba275fa77ced617acbb3765",
      "ledger_sha256": "a88d1f1c563a3845ae3e75ec6fb302352fe9648978e444c28c5b8f8b559afbdb",
      "ledger_cursor": 26,
      "reservations_charged": 3,
      "actual_model_processes": 2
    },
    "forbidden_substitutes": [
      "建立或擴建第二套自治框架",
      "以版本更新重置三次 reservation、重分類兩次實際模型啟動或擴大額度",
      "修改舊版正式 state、ledger、checkpoint 或重算其歷史",
      "讓錯 version/digest 的 O2 模型派工退回不需要 live receipt 的舊路徑",
      "以 repository mock、--help、部署 receipt 或隔離 PASS 冒充正式產品試行",
      "只更新 GitHub main 而未讀回 Mac Runner 與 Ubuntu 同版部署",
      "發布 APPROVE、RESUME、ACCEPT 或啟動 O2 產品模型",
      "提升 Product Owner、Mac Obsidian、mobile、release_verified 或其他 human gate"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "93b6b1f641de1ff4516925c877d6bfd03b44b279",
    "branch": "codex/o2-v3-reauthorization-readiness-20261029",
    "base_branch": "main",
    "draft_pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under this bounded readiness direction"
  },
  "candidate_product_goal": {
    "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
    "goal_version": "2026-10-29.3-bounded-trial-reauthorization-proposal",
    "goal_spec_sha256": "83ddf1cf95c27ec2646e143d4ade88eaedec8f38d5149d3621be090ff6c41e3f",
    "authority_lease": "PAUSED",
    "lifecycle": "APPROVAL_REQUIRED",
    "go_live_authorized": false,
    "trial_start": "2026-11-02T09:00:00+08:00",
    "observation_work_dates": ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"],
    "hard_stop": "2026-11-13T18:00:00+08:00",
    "candidate_provider_ceilings": {"codex": 5, "claude": 8},
    "carried_charges": {"codex": 3, "claude": 0}
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
    {"id": "O2-PRODUCT-OWNER-REAUTHORIZATION", "status": "not_issued", "release_verified": false},
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "A0-IDENTITY-CARRYOVER-AND-DESIGN",
      "title": "固定 v3 immutable identity、歷史承接與最小執行設計",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_V3_REAUTHORIZATION_READINESS_DIRECTION_20261029.md", "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.3.json", "docs/control-plane/O2_V3_CARRYOVER_EVIDENCE_20261029.json", "schemas/product-goal/v1/goal-spec.schema.json"],
      "acceptance": [
        "新 spec 只改版本、日期、carryover 與候選 ceiling；原產品方向、Work Items、obligations、完成條件及安全政策逐欄沿用",
        "canonical digest 從最終 spec 重新計算，carryover evidence 綁定舊 state/ledger/cursor、三次 reservation、兩次模型 process 與候選 checkout",
        "明確定義三次歷史 Codex charge 計入新版 ceiling 5，版本更新不產生自動重置"
      ]
    },
    {
      "id": "A1-ENFORCEMENT-AND-ISOLATED-TESTS",
      "title": "實作 exact identity、carryover ceiling 與 late-activation fail closed",
      "status": "complete",
      "dependencies": ["A0-IDENTITY-CARRYOVER-AND-DESIGN"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_V3_REAUTHORIZATION_READINESS_DIRECTION_20261029.md", "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.3.json", "docs/control-plane/O2_V3_CARRYOVER_EVIDENCE_20261029.json", "docs/control-plane/B_SCHEME_OPERATIONS.md", "schemas/product-goal/v1/", "config/ubuntu-worker-runtime-manifest.json", "scripts/goal_continuity.py", "scripts/goal_runner_adapter.py", "scripts/product_goal_worker_identity.py", "scripts/local_autonomy_runner.py", "scripts/product_goal_runtime_admission.py", "scripts/run_product_goal_isolated_trial.py", "tests/control_plane/", "tests/fixtures/control_plane/product_goal_isolated_trial_spec.json"],
      "acceptance": [
        "Codex 與 Claude model-bearing lane 只接受 exact v3 version/digest 且 reservation 前強制 fresh Ubuntu receipt",
        "同 Goal ID 的錯 version/digest fail closed，不能走 legacy order",
        "Owner APPROVE created_at 未早於 11/02 09:00 時維持 PAUSED/APPROVAL_REQUIRED 並回報 TRIAL_ACTIVATION_MISSED",
        "隔離正向與錯 version、錯 digest、錯 checkout、stale receipt、missed activation 負例均證明零正式副作用"
      ]
    },
    {
      "id": "A2-EXACT-VERIFICATION-AND-REVIEW",
      "title": "exact-candidate verification、Draft PR 與 Ubuntu Claude 獨立審查",
      "status": "active",
      "dependencies": ["A1-ENFORCEMENT-AND-ISOLATED-TESTS"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "output/control-plane/", "GitHub Draft PR metadata", "existing Ubuntu Claude review runtime"],
      "acceptance": [
        "targeted/full tests、requirements guard、strict diff、public safety 與 exact fingerprint/read-back 全綠",
        "Draft PR 綁定 exact HEAD/fingerprint；只有既有 Ubuntu Claude 對同一候選的 canonical PASS 可授權整合"
      ]
    },
    {
      "id": "A3-MERGE-DEPLOY-NO-MODEL-ACCEPTANCE",
      "title": "正常整合、Mac/Ubuntu 同版部署及 PAUSED 無模型正反驗收",
      "status": "pending",
      "dependencies": ["A2-EXACT-VERIFICATION-AND-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub PR/main metadata", "Mac immutable Runner runtime", "Ubuntu immutable worker runtime", "output/control-plane/", "formal old O2 read-only evidence"],
      "acceptance": [
        "依 GitHub rules 整合 exact PASS candidate；Mac LaunchAgent 與 Ubuntu read-back同一 integrated revision/tree/manifest",
        "隔離 PAUSED identity 正向與負向 no-model admission 均不產生正式 reservation、attempt、checkpoint 或 provider process",
        "舊版 state/ledger/checkpoint SHA、cursor、三次 reservation 與兩次實際模型啟動完全不變"
      ]
    },
    {
      "id": "A4-AUTHORIZATION-PACKAGE",
      "title": "產生等待 Product Owner 決策的 exact 重新授權包",
      "status": "pending",
      "dependencies": ["A3-MERGE-DEPLOY-NO-MODEL-ACCEPTANCE"],
      "human_gate": "O2-PRODUCT-OWNER-REAUTHORIZATION",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "output/control-plane/", "new version authorization package"],
      "acceptance": [
        "包內列出 exact version/digest、工作日期、hard stop、carryover charge/remaining ceiling、候選 checkout 與雙主機部署證據",
        "只產生可由 Owner 發布的 APPROVE 草稿，不發布任何 authority command",
        "若 activation prerequisites 未在 11/02 09:00 前滿足，結論保持 PAUSE 並要求新日期與新 immutable version"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The work starts from clean commit `93b6b1f641de1ff4516925c877d6bfd03b44b279`
in an isolated worktree. The prior formal O2 version remains byte-for-byte
read-only and PAUSED. The immutable candidate identity and carryover design are
fixed; the active milestone verifies exact pre-reservation admission, late
activation and historical accounting without a product-model launch.
