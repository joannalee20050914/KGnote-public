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
  "active_milestone_id": "W3-INDEPENDENT-REVIEW",
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
    "draft_pull_request": 38,
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
  "unresolved_permanent_admission_issues": [
    {
      "id": "O2-RUNTIME-RECEIPT-PRE-RESERVATION",
      "status": "NOT_IMPLEMENTED",
      "requirement": "在任何正式 Product Goal reservation 前，必須讀回最新 Ubuntu runtime receipt，驗證 exact reviewed revision、manifest、installed module hashes、import closure、兩個 Worker entrypoint --help 與 model_launches=0。",
      "evidence": "scripts/goal_runner_adapter.py 的 reserve_dispatch 目前只重驗 state、ledger、authority、schedule、resource policy 與 sealed order，沒有讀取 ubuntu-worker-runtime-receipt.json。",
      "boundary": "這是永久准入缺口；在另有明示 authority 將 receipt gate 接入 reservation 前，不得以 installer PASS 或 W4 部署讀回冒充已完成。"
    }
  ],
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
        "正向、缺檔、tamper、import failure、entrypoint non-zero 與 compatibility tests 通過",
        "八個 Worker runtime 檔案以 immutable generation 加單一 current pointer 整組切換；第三檔中斷仍完整保留舊 generation",
        "正式 8fc5a7f flat runtime 只缺 requirements-runtime.lock；首次 migration 只允許以已驗證的新 lock 建立 legacy bridge，其他部分缺檔仍 fail closed，且 pointer 切換後 cold-start 失敗會退回 bridge",
        "reviewed_revision 必須等於 clean release Git checkout HEAD，manifest 與每個 source blob 必須與該 commit 完全一致"
      ]
    },
    {
      "id": "W2-EXACT-VERIFICATION",
      "title": "全套 deterministic verification 與 exact-candidate sealing",
      "status": "complete",
      "dependencies": ["W1-RUNTIME-IMPORT-AND-LOCK-REPAIR"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "tests/control_plane/", "output/control-plane/"],
      "acceptance": ["targeted/full tests、requirements guard、strict diff 與 public-safety 全綠", "exact commit/tree/fingerprint 與 evidence read-back 相符"]
    },
    {
      "id": "W3-INDEPENDENT-REVIEW",
      "title": "Draft PR 與 Ubuntu Claude exact-candidate review",
      "status": "active",
      "dependencies": ["W2-EXACT-VERIFICATION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "scripts/install_ubuntu_worker_runtime.py", "tests/control_plane/test_ubuntu_worker_runtime.py", "GitHub repair PR metadata", "existing Ubuntu Claude review runtime"],
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
        "以 clean real Git checkout 建立 reviewed release；既有無 .git 的 o2-8fc5a7f tar extraction 不得冒充 reviewed source identity",
        "正式 runtime 的 module/lock hashes、import closure、兩個 entrypoint --help 與 full no-model admission 全綠",
        "正式部署 receipt 已產生並讀回；但 O2-RUNTIME-RECEIPT-PRE-RESERVATION 在另有授權修復前仍維持 NOT_IMPLEMENTED，不得發布任何新 reservation",
        "正式狀態仍為 BLOCKED/PAUSED，attempts=3，沒有第四次派工",
        "未發布 RESUME，release_verified 與 human gates 不變"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Formal PAUSE comment `6461719798` is applied at ledger cursor `26`. The third launch reservation is preserved and no fourth dispatch exists. Final no-model audit invalidated review `review-o2-worker-runtime-import-repair-20261028-001` after reproducing non-atomic flat-runtime promotion and unbound `reviewed_revision`; W3 remains active and owns only the bounded generation-pointer/release-Git repair plus exact re-verification and replacement review input. `O2-RUNTIME-RECEIPT-PRE-RESERVATION` remains a durable `NOT_IMPLEMENTED` admission issue outside this milestone's owned reservation paths. `RESUME` remains forbidden.
