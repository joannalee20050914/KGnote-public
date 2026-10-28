# Current review request

Writer: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.

<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->
```json
{
  "schema_version": "kgnote.review-request.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "review_id": "review-o2-worker-runtime-import-repair-20261028-001",
  "goal_id": "CODEX-APP-GOAL-O2-WORKER-RUNTIME-IMPORT-REPAIR-20261028",
  "milestone_id": "W1-RUNTIME-IMPORT-AND-LOCK-REPAIR",
  "status": "IMPLEMENTING",
  "author_role": "CODEX_IMPLEMENTER",
  "base_revision": "8fc5a7f99cf5d01afa9bb544ba3774ee7cdf11ba",
  "candidate_revision": null,
  "candidate_fingerprint": null,
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
  "changed_areas": [
    "PLAN.md",
    "CODEX_STATUS.md",
    ".ai/",
    "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md",
    "config/ubuntu-worker-runtime-manifest.json",
    "scripts/product_goal_worker_lane.py",
    "scripts/install_ubuntu_worker_runtime.py",
    "tests/control_plane/test_product_goal_worker_lane.py",
    "tests/control_plane/test_ubuntu_worker_runtime.py"
  ],
  "acceptance_criteria": [
    "Worker 從 reviewed deployed runtime 取得 dependency lock 而不修改 sealed product checkout",
    "installer 將固定 runtime module manifest 與 lock 綁定 exact reviewed source SHA-256",
    "缺檔、hash drift、import failure 或 entrypoint cold-start failure 在 model 前 fail closed",
    "正向、缺檔、tamper 與 compatibility tests 通過"
  ],
  "negative_requirements": [
    "以 repository PLAN.md 或 CODEX_STATUS.md 冒充正式 Runner state/ledger",
    "只跑 repository 測試而未驗證正式 Ubuntu runtime 的完整匯入鏈與冷啟動",
    "把 dependency lock 加入 sealed product checkout 而改變候選身分",
    "刪除第三次已預留 attempt 或重置 launch/resource accounting",
    "發布 RESUME、啟動第四次派工或提升任何 human/release gate",
    "部署未經 exact review 的程式碼或重用 stale PASS"
  ],
  "validation_performed": [],
  "validation_results": [],
  "known_deviations": [],
  "known_uncertainties": [],
  "reviewer_focus": [],
  "preserved_human_gates": [
    "O2-AUTHORITY-LEASE",
    "D2-T14-FINAL-HUMAN-ACCEPTANCE",
    "PA-HUMAN-1",
    "NS-HUMAN-SMOKE"
  ],
  "requested_at": null,
  "authorized_human_decision_identities": [
    "product owner"
  ],
  "candidate_manifest": null,
  "completion_evidence": {
    "schema_version": "kgnote.review-completion-summary.v1",
    "applicable": false,
    "passed": true,
    "evidence_path": null,
    "evidence_sha256": null,
    "claims": [],
    "test_receipts": []
  }
}
```
<!-- END KGNOTE REVIEW REQUEST JSON -->

## Human-readable status

Review `review-o2-worker-runtime-import-repair-20261028-001` is `IMPLEMENTING`.
It has no active candidate binding and cannot be interpreted as a review request or PASS.
Codex must complete deterministic verification before issuing this request.
