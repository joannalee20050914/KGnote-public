# KGnote active execution plan

This file contains one bounded Ubuntu Worker deployment-repair Goal. It does not authorize `RESUME` or another O2 product-model attempt.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-WORKER-RUNTIME-IMPORT-REPAIR-20261028",
  "active_goal": "CODEX-APP-GOAL-O2-WORKER-RUNTIME-IMPORT-REPAIR-20261028",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "在維持正式 O2 PAUSE 與既有三次 launch accounting 不變的前提下，限縮修復 Ubuntu Worker runtime 的 Python 模組、dependency lock、部署完整性與無模型冷啟動驗收；只有 exact candidate 經獨立審查後才能正式部署，全程禁止 RESUME 與第四次派工。",
  "status": "active",
  "active_milestone_id": "W2-EXACT-VERIFICATION",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-worker-runtime-import-repair-2026-10-28",
  "explicit_direction": {
    "date": "2026-10-28",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md",
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
    "formal_runtime_baseline": {
      "deployed_commit": "8fc5a7f99cf5d01afa9bb544ba3774ee7cdf11ba",
      "pause_comment_id": "6461719798",
      "ledger_cursor": 26,
      "work_item_attempts": 3,
      "model_attempts": 2,
      "fourth_attempt_present": false
    },
    "forbidden_substitutes": [
      "以 repository PLAN.md 或 CODEX_STATUS.md 冒充正式 Runner state/ledger",
      "只跑 repository 測試而未驗證正式 Ubuntu runtime 的完整匯入鏈與冷啟動",
      "把 dependency lock 加入 sealed product checkout 而改變候選身分",
      "刪除第三次已預留 attempt 或重置 launch/resource accounting",
      "發布 RESUME、啟動第四次派工或提升任何 human/release gate",
      "部署未經 exact review 的程式碼或重用 stale PASS"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "8fc5a7f99cf5d01afa9bb544ba3774ee7cdf11ba",
    "branch": "codex/o2-worker-runtime-import-repair-20261028",
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
      "id": "W0-PAUSE-AND-FAILURE-READBACK",
      "title": "唯讀確認正式 PAUSE、第三次失敗與沒有第四次派工",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md"],
      "acceptance": [
        "正式 state/ledger 為 BLOCKED/PAUSED/go_live_authorized=false 且 cursor=26",
        "Work Item A attempts=3、model attempts=2、第三次 Codex event_count=0",
        "沒有第四次 reservation、attempt、dispatch、checkpoint 或 model launch"
      ]
    },
    {
      "id": "W1-RUNTIME-IMPORT-AND-LOCK-REPAIR",
      "title": "限縮修復 Worker runtime 模組、dependency lock 與部署 fail-closed gate",
      "status": "complete",
      "dependencies": ["W0-PAUSE-AND-FAILURE-READBACK"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md", "config/ubuntu-worker-runtime-manifest.json", "scripts/product_goal_worker_lane.py", "scripts/install_ubuntu_worker_runtime.py", "tests/control_plane/test_product_goal_worker_lane.py", "tests/control_plane/test_ubuntu_worker_runtime.py"],
      "acceptance": [
        "Worker 從 reviewed deployed runtime 取得 dependency lock 而不修改 sealed product checkout",
        "installer 將固定 runtime module manifest 與 lock 綁定 exact reviewed source SHA-256",
        "缺檔、hash drift、import failure 或 entrypoint cold-start failure 在 model 前 fail closed",
        "正向、缺檔、tamper 與 compatibility tests 通過"
      ]
    },
    {
      "id": "W2-EXACT-VERIFICATION",
      "title": "全套 deterministic verification 與 exact-candidate sealing",
      "status": "active",
      "dependencies": ["W1-RUNTIME-IMPORT-AND-LOCK-REPAIR"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "tests/control_plane/", "output/control-plane/"],
      "acceptance": ["targeted/full tests、requirements guard、strict diff 與 public-safety 全綠", "exact commit/tree/fingerprint 與 evidence read-back 相符"]
    },
    {
      "id": "W3-INDEPENDENT-REVIEW",
      "title": "Draft PR 與 Ubuntu Claude exact-candidate review",
      "status": "pending",
      "dependencies": ["W2-EXACT-VERIFICATION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub repair PR metadata", "existing Ubuntu Claude review runtime"],
      "acceptance": ["reviewer 檢查 exact candidate、部署 fail-closed gate 與 no-RESUME boundary", "只有 exact PASS 且 GitHub rules satisfied 才能正常合併"]
    },
    {
      "id": "W4-MERGE-DEPLOY-COLD-START-READBACK",
      "title": "正常合併、限縮部署、正式無模型冷啟動與最終 PAUSE 讀回",
      "status": "pending",
      "dependencies": ["W3-INDEPENDENT-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "GitHub main/PR metadata", "Ubuntu runtime", "formal read-only state/ledger evidence"],
      "acceptance": [
        "正式 runtime 的 module/lock hashes、import closure、兩個 entrypoint --help 與 full no-model admission 全綠",
        "正式狀態仍為 BLOCKED/PAUSED，attempts=3，沒有第四次派工",
        "未發布 RESUME，release_verified 與 human gates 不變"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Formal PAUSE comment `6461719798` is applied at ledger cursor `26`. The third launch reservation is preserved and no fourth dispatch exists. The active slice repairs only the reviewed Ubuntu Worker runtime import/dependency closure; `RESUME` remains forbidden until a later explicit Owner action after all completion criteria pass.
