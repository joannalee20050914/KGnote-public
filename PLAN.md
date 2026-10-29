# KGnote active execution plan

This file contains one bounded O2 Day 0 acceleration readiness Goal. It does not authorize `APPROVE`, `RESUME`, `ACCEPT` or a product-model launch.

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
  "objective": "以已合併並部署的 PR #40 / dc7faa2 為基準，建立最小 O2 v4 Day 0 immutable schedule identity，重用既有 v3 工程與安全成果，完成 exact verification、Ubuntu Claude PASS、正常 GitHub 整合、Mac/Ubuntu 同版部署、無模型正反驗收及等待 Product Owner 的 exact APPROVE 包。",
  "status": "active",
  "active_milestone_id": "D1-EXACT-VERIFICATION-AND-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-day0-acceleration-2026-10-29",
  "explicit_direction": {
    "date": "2026-10-29",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_DAY0_ACCELERATION_DIRECTION_20261029.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_DAY0_ACCELERATION_DIRECTION_20261029.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "AGENTS.md"
  ],
  "requirement_context": {
    "requirements": [
      "KG-GOV-04",
      "KG-GOV-05",
      "KG-GOV-07",
      "KG-PLAT-05",
      "KG-PLAT-07",
      "KG-PLAT-08"
    ],
    "acceptance_criteria": [
      "RC-05",
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
    "scenarios": [
      "SC-32",
      "SC-33",
      "SC-35",
      "SC-40",
      "SC-44",
      "SC-45",
      "SC-48"
    ],
    "reused_v3_baseline": {
      "pull_request": 40,
      "reviewed_commit": "531b23826364610f943367161dad3228acf86833",
      "reviewed_fingerprint": "679dd9e2f84b470ef951d1939524bdc094d51a2b57a40887d91de3e22b55fae7",
      "merge_commit": "dc7faa2a374fad5b3ec895ef85001f4c32457281",
      "deployment_status": "PASS",
      "no_model_acceptance_status": "PASS"
    },
    "forbidden_substitutes": [
      "修改或覆寫 immutable v3 spec、state、ledger、checkpoints 或 receipts",
      "建立第二套自治框架或重做 PR #40 已完成的 admission engineering",
      "把 Day 0 排除在模型 reservation、attempt 或 provider ceiling 計帳之外",
      "把 Day 0 誤列為五個完整觀察工作日之一",
      "重置舊版三次 Codex charge、增加 Codex 5 / Claude 8 ceiling 或使用 paid API",
      "略過 exact verification、Ubuntu Claude review、正常 GitHub merge、雙主機部署或無模型驗收",
      "發布 APPROVE、RESUME、ACCEPT 或在正式 Owner authority 前啟動產品模型",
      "提升 PA-HUMAN-1、NS-HUMAN-SMOKE、human acceptance 或 release_verified"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "dc7faa2a374fad5b3ec895ef85001f4c32457281",
    "branch": "codex/o2-day0-acceleration-20261029",
    "base_branch": "main",
    "pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under this bounded Day 0 direction"
  },
  "candidate_product_goal": {
    "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
    "goal_version": "2026-10-29.4-bounded-trial-day0-proposal",
    "goal_spec_sha256": "7e9a31e87d36a2cb23789602f3bafb4fe29469d0fa57dcda33b9e8ba1295e08f",
    "authority_lease": "PAUSED",
    "lifecycle": "APPROVAL_REQUIRED",
    "go_live_authorized": false,
    "proposed_start": "2026-10-29T17:00:00+08:00",
    "day_zero": "2026-10-29",
    "day_zero_is_full_observation_day": false,
    "day_zero_model_usage_counts": true,
    "observation_work_dates": [
      "2026-10-30",
      "2026-11-02",
      "2026-11-03",
      "2026-11-04",
      "2026-11-05"
    ],
    "hard_stop": "2026-11-11T18:00:00+08:00",
    "hard_stop_goal_workday_ordinal": 10,
    "provider_ceilings": {
      "codex": 5,
      "claude": 8
    },
    "carried_charges": {
      "codex": 3,
      "claude": 0
    },
    "remaining": {
      "codex": 2,
      "claude": 8
    }
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
    {
      "id": "O2-AUTHORITY-LEASE",
      "status": "PAUSED",
      "release_verified": false
    },
    {
      "id": "O2-PRODUCT-OWNER-REAUTHORIZATION",
      "status": "not_issued",
      "release_verified": false
    },
    {
      "id": "D2-T14-FINAL-HUMAN-ACCEPTANCE",
      "status": "not_promoted",
      "release_verified": false
    },
    {
      "id": "PA-HUMAN-1",
      "status": "not_promoted",
      "release_verified": false
    },
    {
      "id": "NS-HUMAN-SMOKE",
      "status": "not_promoted",
      "release_verified": false
    }
  ],
  "milestones": [
    {
      "id": "D0-MINIMAL-VERSION-SEAL",
      "title": "封存最小 v4 Day 0 identity 與計數契約",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/O2_DAY0_ACCELERATION_DIRECTION_20261029.md",
        "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json",
        "docs/control-plane/O2_V4_CARRYOVER_EVIDENCE_20261029.json",
        "docs/control-plane/B_SCHEME_OPERATIONS.md",
        "schemas/product-goal/v1/goal-spec.schema.json",
        "scripts/goal_continuity.py",
        "scripts/product_goal_worker_identity.py",
        "config/ubuntu-worker-runtime-manifest.json",
        "tests/control_plane/"
      ],
      "acceptance": [
        "v3 bytes 不變；v4 只改 immutable version/schedule identity、carryover target 與必要 exact admission constants",
        "Day 0 與五個完整觀察工作日分離，十個 Goal 工作日於 11/11 18:00 結束",
        "Day 0 模型使用正常計入 Codex 5 / Claude 8；Codex carried 3、remaining 2 不變"
      ]
    },
    {
      "id": "D1-EXACT-VERIFICATION-AND-REVIEW",
      "title": "exact deterministic verification 與 Ubuntu Claude 獨立審查",
      "status": "active",
      "dependencies": [
        "D0-MINIMAL-VERSION-SEAL"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "output/control-plane/",
        "GitHub PR metadata"
      ],
      "acceptance": [
        "targeted/full tests、requirements guard、strict diff、public safety 與 exact fingerprint/read-back 全綠",
        "PR 綁定 exact HEAD/fingerprint 且 Ubuntu Claude canonical verdict 為 PASS"
      ]
    },
    {
      "id": "D2-MERGE-DEPLOY-NO-MODEL-ACCEPTANCE",
      "title": "正常整合、雙主機同版部署與 PAUSED 無模型驗收",
      "status": "pending",
      "dependencies": [
        "D1-EXACT-VERIFICATION-AND-REVIEW"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "output/control-plane/",
        "GitHub PR/main metadata",
        "Mac immutable Runner runtime",
        "Ubuntu immutable worker runtime"
      ],
      "acceptance": [
        "normal GitHub merge 後 Mac Runner 與 Ubuntu read back 同一 integrated revision/tree/manifest",
        "正反 no-model admission 不新增正式 reservation、attempt、checkpoint 或 provider process",
        "v3 與舊版 state/ledger/checkpoint hashes 完全不變"
      ]
    },
    {
      "id": "D3-OWNER-APPROVAL-PACKAGE",
      "title": "封存三份 dependency receipts 與 exact APPROVE 草稿",
      "status": "pending",
      "dependencies": [
        "D2-MERGE-DEPLOY-NO-MODEL-ACCEPTANCE"
      ],
      "human_gate": "O2-PRODUCT-OWNER-REAUTHORIZATION",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        "output/control-plane/",
        "new version authorization package"
      ],
      "acceptance": [
        "包內列出 exact version/digest、Day 0/五完整日/十工作日規則、額度承接與雙主機證據",
        "只產生 Owner 可發布的 APPROVE 草稿，不代為發布",
        "若 Owner command 或 Runner observation 未嚴格早於 17:00，保持 PAUSE 並要求新 immutable version"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The work starts from normally merged and deployed PR #40 at `dc7faa2`. The v3 identity and all formal historical state remain read-only. Only the minimum v4 schedule/identity delta and its exact review/deployment evidence are in scope.
