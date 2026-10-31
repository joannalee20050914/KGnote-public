# KGnote active execution plan

This file contains one Codex App engineering Goal for Issue #47. It does not
authorize a KGnote Product Goal. The exact immutable engineering specification
was approved by the GitHub repository Owner on 2026-10-31 and amended by the
exact engineering-only weekend exception in comment `6537070839`; model work,
formal deployment, and gated external execution remain limited by the approved
work window, milestone dependencies, and separate Product Goal / go-live gates.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "active_goal": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "EXACT_GITHUB_OWNER_APPROVED_CODEX_APP_EXECUTION_GOAL",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "以單一、有界且可跨工作日恢復的工程 Goal，保存現有 Issue #47 readiness candidate，固定 exact spec／checkpoint／預算，取得 GitHub Owner 授權後，連續完成獨立審查、one-shot dispatch、無模型整合測試、安全部署、受控 canary、跨日接續與 rollback 證據，最後停在真人產品驗收與常設 go-live 的集中決策；不修改或冒充 O2 v4 Product Goal。",
  "status": "active",
  "active_milestone_id": "EG-1-INDEPENDENT-REVIEW-AND-PR",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-reconciliation-2026-09-27-r8",
  "execution_direction_id": "kgnote-issue47-weekend-engineering-exception-2026-10-31",
  "goal_spec": {
    "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json",
    "schema_path": "schemas/codex-app-engineering-goal/v1/goal-spec.schema.json",
    "version": "2026-10-31.2-weekend-engineering-exception",
    "canonical_sha256": "8f3036ec6429e2f8f1e546aea3a8b3bf1c0cb1459e742991a4228612836958cd",
    "authority_status": "EXACT_GITHUB_OWNER_APPROVED",
    "authorization_request": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261031.md",
    "authority_receipt": {
      "comment_id": 6537070839,
      "comment_url": "https://github.com/joannalee20050914/KGnote-public/issues/47#issuecomment-6537070839",
      "author_login": "joannalee20050914",
      "author_association": "OWNER",
      "created_at": "2026-10-31T01:19:02Z",
      "body_sha256": "d01c5fe57c73f99750ff2ec145f4d495897b4062c4e20a97950b4b00d8507e92",
      "command_canonical_sha256": "6bc2d545b3c116c17d66de592780cd685f0c004306c20dd109ec74b95c4931fc",
      "marker": "kgnote-codex-app-engineering-goal-authority:v1",
      "validation": "EXACT_SEMANTIC_MATCH_AND_REMOTE_SPEC_BLOB_READ_BACK"
    }
  },
  "explicit_direction": {
    "date": "2026-10-31",
    "speaker": "product owner",
    "source_path": "PLAN.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/ISSUE47_ONESHOT_ENGINEERING_DIRECTION_20261030.md",
    "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json",
    "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json",
    "docs/control-plane/ISSUE47_WEEKEND_ENGINEERING_EXCEPTION_DIRECTION_20261031.md",
    "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261031.md",
    "schemas/codex-app-engineering-goal/v1/goal-spec.schema.json",
    ".ai/REVIEW_PROTOCOL.md",
    "schemas/product-goal/v1/goal-spec.schema.json",
    "schemas/product-goal/v1/runner-state.schema.json",
    "schemas/product-goal/v1/ledger-event.schema.json",
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
      "KG-PLAT-07"
    ],
    "acceptance_criteria": [
      "RC-31",
      "RC-32"
    ],
    "feature_dispositions": [],
    "scenarios": [
      "SC-32",
      "SC-33",
      "SC-35"
    ],
    "issue_authority": {
      "repository": "joannalee20050914/KGnote-public",
      "issue": 47,
      "url": "https://github.com/joannalee20050914/KGnote-public/issues/47",
      "strategy_comment": "https://github.com/joannalee20050914/KGnote-public/issues/47#issuecomment-6522962957",
      "strategy_comment_status": "DRAFT_ONLY_NOT_AUTHORIZED"
    },
    "forbidden_substitutes": [
      "把 Codex App 工程 Goal 或 Issue #47 DRAFT 留言當成 Product Goal APPROVE",
      "把 readiness checker、單元測試、Draft PR、scheduler 安裝或 no-model admission 當成端到端自治完成",
      "建立第二套 planner、ledger、Router、worker 或 state machine",
      "修改、合併、重設或搬用 O2 v4 authority、state、ledger cursor 9、Codex 4/5、checkpoint 或封存 evidence",
      "啟用或共用舊 com.kgnote.local-autonomy-runner",
      "在 exact Owner approval 前或一般／明列週末例外時段外啟動背景 Codex／Claude、正式 deploy 或 dispatch",
      "把 2026-10-31／2026-11-01 工程例外用於 Product Goal canary、產品模型派工、常設排程啟用或 go-live",
      "使用付費 API、force push、直接 push main、修改 branch protection 或未批准資料外送",
      "把 Codex-primary／Claude-reviewer 的證據宣稱為 Claude-primary／Codex-reviewer 已完成",
      "用 restart、日期、Goal version、branch、PR 或 session 重置 launch/accounting history"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "e3a2102f1d4822e2526c3b9db90903b1ee88f6dc",
    "branch": "codex/issue-47-collaboration-wiring",
    "base_branch": "main",
    "pull_request": null,
    "automatic_merge": false,
    "merge_authority": "proposed only for the exact Issue #47 PR after GitHub Owner spec approval, required checks, independent review, branch protection, and remote read-back"
  },
  "previous_goal_disposition": {
    "goal_id": "CODEX-APP-GOAL-ISSUE47-ONESHOT-WIRING-20261030",
    "milestone_id": "D2-ONESHOT-WIRING",
    "disposition": "preserved_as_verified_readiness_baseline_inside_successor_goal",
    "candidate_fingerprint": "025295008f940ba5b55ebef2691556cafe82bd110eadae57cc9fb8e7e281aed6",
    "evidence": "output/control-plane/verification-20261030T200856+0800.json",
    "verified_scope": "readiness-only one-shot, 11 boundary tests, no dispatch, no model, no scheduler, no GitHub write",
    "unverified_scope": "checkpoint commit, independent infrastructure review, PR integration, real dispatch, deployment, canary, schedule continuation and rollback"
  },
  "resource_budget": {
    "work_period": "2026-10-31T09:15:00+08:00 through 2026-11-20T18:00:00+08:00",
    "work_window": "Monday-Friday Asia/Taipei 09:00-18:00 plus engineering-only 2026-10-31 09:15-18:00 and 2026-11-01 09:00-18:00",
    "model_concurrency": 1,
    "codex": {
      "max_total": 18,
      "max_per_workday": 3,
      "known_preapproval": 7,
      "remaining_if_approved": 11
    },
    "claude": {
      "max_total": 12,
      "max_per_workday": 2,
      "known_preapproval": 0,
      "remaining_if_approved": 12
    },
    "payment": "existing subscription login only; paid API fallback forbidden",
    "reset_rule": "all retries, contexts/sessions, reviews, repairs, cross-day work and unknown reserved attempts share the same totals and cannot be reset"
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "external_review_required_before_merge_or_deploy": true,
    "max_review_cycles_per_milestone": 5,
    "max_same_failure_attempts": 2,
    "max_strategy_adjustments": 1,
    "stop_on_review_state": [
      "PRODUCT_DECISION_REQUIRED",
      "AUTHORITY_CONFLICT",
      "AUTOMATION_BLOCKED",
      "BUDGET_EXHAUSTED",
      "GOAL_COMPLETE",
      "STOPPED"
    ]
  },
  "legacy_o2_protection": {
    "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
    "lifecycle": "ACTIVE",
    "ledger_cursor": 9,
    "codex_accounting": "4/5",
    "formal_runner": "DISABLED_UNLOADED",
    "runtime_records": "IMMUTABLE_READ_ONLY",
    "coexistence_rule": "Owner approval of the exact engineering spec may approve only a bounded exclusive trial policy: O2 remains inactive/read-only, a future canary still needs a separate Product Goal approval, state/ledger/worktree/PR/review config stay isolated, and a global writer lock forbids concurrent model dispatch."
  },
  "preserved_human_gates": [
    {
      "id": "ISSUE47-ENGINEERING-GOAL-OWNER-APPROVAL",
      "status": "COMPLETE",
      "release_verified": false,
      "rule": "Current exact authority is Owner comment 6537070839 for v2026-10-31.2; it binds the weekend engineering-only windows, at least Codex 7/18 carry-over, permissions, resources and unchanged O2 coexistence."
    },
    {
      "id": "ISSUE47-EXACT-PRODUCT-GOAL-CANARY-APPROVAL",
      "status": "NOT_STARTED",
      "release_verified": false,
      "rule": "Engineering Goal approval cannot authorize the live Product Goal canary."
    },
    {
      "id": "ISSUE47-FINAL-OWNER-ACCEPTANCE-AND-GO-LIVE",
      "status": "NOT_STARTED",
      "release_verified": false,
      "rule": "Trial evidence precedes a separate Owner product acceptance and standing B-scheme go-live decision."
    },
    {
      "id": "ISSUE47-CLAUDE-PRIMARY-CODEX-REVIEW-PROOF",
      "status": "NOT_VERIFIED",
      "release_verified": false,
      "rule": "Do not claim bidirectional provider switching without a live exact-candidate proof."
    },
    {
      "id": "O2-V4-FORMAL-RUNTIME-PROTECTION",
      "status": "ACTIVE_UNCHANGED",
      "release_verified": false,
      "rule": "O2 remains ACTIVE but formal Runner is disabled/unloaded and all runtime records stay read-only."
    },
    {
      "id": "D2-T14-FINAL-HUMAN-ACCEPTANCE",
      "status": "not_promoted",
      "release_verified": false,
      "rule": "Engineering evidence cannot promote product acceptance."
    },
    {
      "id": "PA-HUMAN-1",
      "status": "not_promoted",
      "release_verified": false,
      "rule": "Requires native learner evidence."
    },
    {
      "id": "NS-HUMAN-SMOKE",
      "status": "not_promoted",
      "release_verified": false,
      "rule": "Requires native product evidence."
    }
  ],
  "milestones": [
    {
      "id": "EG-0-SPEC-SEAL",
      "title": "固定單一工程 Goal spec、checkpoint、資源與 Owner 授權請求",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/ISSUE47_ONESHOT_ENGINEERING_DIRECTION_20261030.md",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261030.md",
        "schemas/codex-app-engineering-goal/v1/",
        "scripts/collaboration_goal_wakeup.py",
        "tests/control_plane/test_collaboration_goal_wakeup.py",
        "tests/control_plane/test_issue47_engineering_goal_spec.py",
        "output/control-plane/"
      ],
      "acceptance": [
        "保留且不重做既有 readiness checker、11 項邊界測試與 verification evidence",
        "engineering Goal spec 通過 schema、dependency、budget 與 canonical digest validation",
        "PLAN、STATUS、review bus 與 spec identity 一致且 preflight/review-validate 綠燈",
        "以 path-explicit checkpoint commit/push 固定 exact branch bytes，GitHub read-back 一致",
        "Issue #47 發布一份非自批的 Owner authorization request，清楚列出 exact Goal ID/version/SHA、permissions、resource ceilings、O2 coexistence 與 required reply marker",
        "在 Owner exact approval 前不啟動背景 Codex／Claude、dispatch、scheduler 或 formal deployment"
      ]
    },
    {
      "id": "EG-0-OWNER-AUTHORITY",
      "title": "等待並讀回 exact GitHub Owner 工程 Goal 授權",
      "status": "complete",
      "dependencies": [
        "EG-0-SPEC-SEAL"
      ],
      "human_gate": "complete",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261030.md",
        "output/control-plane/",
        "GitHub Issue #47 exact Owner reply"
      ],
      "acceptance": [
        "Owner-authored Issue #47 comment 綁定 exact Goal ID、version、canonical SHA-256、完整 permissions、resource acknowledgement 與 bounded coexistence",
        "comment author login 與 author_association=OWNER 讀回一致，body digest 與 comment identity 有 durable receipt",
        "任何舊 DRAFT、agent-authored、自動生成、stale digest、縮減或擴張 permissions 的留言均拒絕",
        "授權仍明示 product_goal_authorized=false 與 standing_b_scheme_go_live_authorized=false"
      ]
    },
    {
      "id": "EG-0-WEEKEND-AUTHORITY-AMENDMENT",
      "title": "讀回並整合限時週末工程例外，不重置歷史或產品 gate",
      "status": "complete",
      "dependencies": [
        "EG-0-OWNER-AUTHORITY"
      ],
      "human_gate": "complete",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json",
        "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261031.md",
        "docs/control-plane/ISSUE47_WEEKEND_ENGINEERING_EXCEPTION_DIRECTION_20261031.md",
        "schemas/codex-app-engineering-goal/v1/",
        "scripts/codex_orchestrator.py",
        "tests/control_plane/",
        "output/control-plane/",
        "GitHub Issue #47 exact Owner reply 6537070839"
      ],
      "acceptance": [
        "successor spec canonical SHA-256 8f3036ec... and Owner comment 6537070839 read back exactly",
        "predecessor spec, checkpoint, 3/3 blocked audit, review history and at least Codex 7/18 usage remain preserved",
        "no-model positive/negative tests enforce Oct31/Nov1 only, exact version/authority, O2 read-only and Product Goal/go-live denial",
        "only the historical future-start time blocker may be resolved; every other blocker remains fail closed"
      ]
    },
    {
      "id": "EG-1-INDEPENDENT-REVIEW-AND-PR",
      "title": "readiness exact candidate 的獨立審查、修復與 PR 整合",
      "status": "active",
      "dependencies": [
        "EG-0-WEEKEND-AUTHORITY-AMENDMENT"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "schemas/codex-app-engineering-goal/",
        "scripts/codex_orchestrator.py",
        "scripts/collaboration_goal_wakeup.py",
        "tests/control_plane/",
        "output/control-plane/",
        "GitHub Issue #47 and the exact Issue #47 PR"
      ],
      "acceptance": [
        "checkpoint candidate 經 deterministic verifier 與獨立 Ubuntu Claude infrastructure review",
        "CHANGES_REQUIRED 自動回 Codex repair、重驗與復審，所有 launch 計入同一 budget",
        "Draft PR、remote HEAD、fingerprint、review round 與 Consumer read-back identity 一致",
        "只在 branch protection、required checks、independent PASS 與 allowed operation 全部成立後整合 PR"
      ]
    },
    {
      "id": "EG-2-ONESHOT-DISPATCH",
      "title": "沿用既有 planner／ledger／Router／worker 的真正 one-shot dispatch",
      "status": "pending",
      "dependencies": [
        "EG-1-INDEPENDENT-REVIEW-AND-PR"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "schemas/",
        "scripts/",
        "tests/control_plane/",
        "config/",
        "output/control-plane/"
      ],
      "acceptance": [
        "只有 exact Product Goal Owner authority 才會 durable reserve 與 route，未授權維持 WAITING_AUTHORIZATION",
        "重用 goal_continuity、github_product_goal_control、goal_runner_adapter、linux_worker_router 與 worker lane，不建立第二套 state machine",
        "WorkOrder 與結果綁定 Goal、Work Item、authority、candidate、checkpoint、review、usage 與 next action",
        "舊 O2 Runner、O2 state/ledger、舊 singleton review config 均未使用或修改"
      ]
    },
    {
      "id": "EG-3-ZERO-MODEL-E2E",
      "title": "無模型整合、失敗安全、停止與 rollback 證據",
      "status": "pending",
      "dependencies": [
        "EG-2-ONESHOT-DISPATCH"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "schemas/",
        "scripts/",
        "tests/control_plane/",
        "config/",
        "output/control-plane/"
      ],
      "acceptance": [
        "未授權、wrong repository/identity、old O2、single writer、duplicate、restart、stale version/commit/review 全部 fail closed",
        "可信 GitHub write/read-back、CHANGES_REQUIRED→repair/re-review、Stop Marker、rollback 經真實非模型路徑驗證",
        "restart 先 reconcile 未決 reservation/checkpoint/side effect，絕不 blind redispatch"
      ]
    },
    {
      "id": "EG-4-TRUSTED-DEPLOYMENT",
      "title": "安全部署 exact reviewed generation 與唯一 disabled-by-default 入口",
      "status": "pending",
      "dependencies": [
        "EG-3-ZERO-MODEL-E2E"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "scripts/",
        "tests/control_plane/",
        "config/",
        "output/control-plane/",
        "trusted Mac and Ubuntu deployment paths explicitly named by the approved spec"
      ],
      "acceptance": [
        "Mac/Ubuntu runtime identity、manifest、installed hashes 與 no-model admission receipt 綁定 exact reviewed commit",
        "新 scheduler/launcher 唯一、預設 disabled、可逆且不共用 O2 state/ledger",
        "old O2 Runner 維持 disabled/unloaded；duplicate service、unexpected process、stop 與 rollback negative tests 通過"
      ]
    },
    {
      "id": "EG-5-LIVE-CANARY",
      "title": "受控真實 Product Goal canary 與 Codex→Claude repair/review",
      "status": "pending",
      "dependencies": [
        "EG-4-TRUSTED-DEPLOYMENT"
      ],
      "human_gate": "ISSUE47-EXACT-PRODUCT-GOAL-CANARY-APPROVAL",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "scripts/",
        "tests/control_plane/",
        "config/",
        "output/control-plane/",
        "separately approved canary repository/Issue/branch/PR/runtime records"
      ],
      "acceptance": [
        "另有 immutable Product Goal spec、exact Owner approval、privacy boundary 與剩餘 budget admission",
        "真實 Codex implementation→verification→PR→Claude review→GitHub read-back→必要 repair/re-review→READY_FOR_ACCEPTANCE",
        "#46 或私人 Pikambler 資料沒有被工程 Goal 自動授權或公開外送",
        "Claude-primary/Codex-reviewer 未實測時保持 NOT_VERIFIED"
      ]
    },
    {
      "id": "EG-6-SCHEDULE-RESUME-ROLLBACK",
      "title": "跨工作日恢復、唯一排程、停止不復活與 rollback",
      "status": "pending",
      "dependencies": [
        "EG-5-LIVE-CANARY"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "scripts/",
        "tests/control_plane/",
        "config/",
        "output/control-plane/",
        "approved scheduler and runtime configuration"
      ],
      "acceptance": [
        "至少一次跨工作日恢復與安全 restart，不需人工重貼 Prompt 或 finding",
        "重啟不重複 model dispatch 或 GitHub write，手動停止後不自行復活",
        "rollback 回到新入口 STOPPED、保留 evidence 且舊 O2 Runner 仍 disabled/unloaded"
      ]
    },
    {
      "id": "EG-7-FINAL-OWNER-GATE",
      "title": "集中真人產品驗收與 standing B-scheme go-live 決策",
      "status": "pending",
      "dependencies": [
        "EG-6-SCHEDULE-RESUME-ROLLBACK"
      ],
      "human_gate": "ISSUE47-FINAL-OWNER-ACCEPTANCE-AND-GO-LIVE",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/",
        "output/control-plane/",
        "GitHub Issue #47 and exact canary PR/review evidence"
      ],
      "acceptance": [
        "GitHub 可讀 evidence 區分 confirmed、not verified、blocked、resource usage 與 rollback",
        "Owner 可分別接受 trial product outcome 與決定 standing go-live；trial PASS 不自動授權常設政策",
        "未經真人產品驗收、standing go-live 或未驗證 provider 方向不得標示完成"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current execution note

`EG-0-SPEC-SEAL` completed at checkpoint `2b60fbc399e41b016f695b82644ca0dbe106b358`
and fingerprint `5aea9a8015f1ca926d1444fcd8373ce02aef7cf289b71baaf21461a9f51a3a4b`.
The exact authorization request was published at
`https://github.com/joannalee20050914/KGnote-public/issues/47#issuecomment-6523223111`.
The repository Owner then posted the exact marker and command at
`https://github.com/joannalee20050914/KGnote-public/issues/47#issuecomment-6536884383`;
its body SHA-256 is
`ab27554c2388587cf8e6cd0fce48a0e7247c095bcf872b12f78cc96e4e57e4a3` and
the command matches the immutable spec exactly. `EG-1-INDEPENDENT-REVIEW-AND-PR`
is now the only active milestone. No background Codex or Claude context may
start before 2026-11-02 09:00 Asia/Taipei or outside the approved work window.
This approval still does not authorize any Product Goal, live canary, standing
B-scheme go-live, or mutation of O2 v4 runtime records.
