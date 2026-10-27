# Current review request

Writer: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.

<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->
```json
{
  "schema_version": "kgnote.review-request.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "review_id": "review-o2-prelaunch-hotfix-20261027-001",
  "goal_id": "CODEX-APP-GOAL-O2-PRELAUNCH-HOTFIX-20261027",
  "milestone_id": "H1-THREE-BLOCKER-REPAIR",
  "status": "IMPLEMENTING",
  "author_role": "CODEX_IMPLEMENTER",
  "base_revision": "483f9e64066821d5d647d411e6da8ddb50ad88e5",
  "candidate_revision": null,
  "candidate_fingerprint": null,
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_PRELAUNCH_HOTFIX_DIRECTION_20261027.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
    "docs/control-plane/O2_BOUNDED_TRIAL_AUTHORIZATION_PACKAGE_20261023.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/CLAUDE_REVIEWER_ROLE_DECISION_20261020.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
    "DEVELOPMENT_PLAIN.md",
    "AGENTS.md"
  ],
  "changed_areas": [
    "PLAN.md",
    "CODEX_STATUS.md",
    ".ai/",
    "docs/control-plane/",
    "requirements-runtime.lock",
    "scripts/goal_runner_adapter.py",
    "scripts/product_goal_worker_identity.py",
    "scripts/linux_worker_bootstrap.py",
    "scripts/linux_worker_router.py",
    "scripts/local_autonomy_runner.py",
    "scripts/product_goal_worker_lane.py",
    "scripts/install_runner_python_runtime.py",
    "tests/control_plane/"
  ],
  "acceptance_criteria": [
    "detached Runner 只對固定 O2 version/digest 從遠端 product seed branch 讀回真實 commit/tree 並計算 fingerprint，首次 pull_request=null 合法",
    "首次 candidate/order binding 以 append-only ledger state_patch 持久化且 restart 可重放，錯 branch/commit/common-dir/digest/remote fail closed",
    "Ubuntu bootstrap 在模型前建立或重用 exact clean branch checkout，驗證 repository、HEAD、tree、owner/mode、非 symlink 與 Git common directory，非空或 dirty 不覆寫",
    "O2 Reviewer WorkOrder 從正式 projection 取得三項 Schema Admission，真實 WorkOrder 與 command/schema preflight 在模型前驗證",
    "pinned Python runtime 安裝與驗證程序記錄 interpreter、dependencies、sources、imports、sys.executable/sys.path、commit/tree、owner/mode 與 rollback，不依賴舊 dirty worktree"
  ],
  "negative_requirements": [
    "修改 O2 Goal WHAT、Requirement、Work Item DAG、模型額度、試行開始或硬截止",
    "直接手改正式 state／ledger、預填未來 SHA 或以 Legacy PR／candidate 冒充首次 O2 候選",
    "空目錄冒充 Ubuntu Git checkout，或覆寫非空、dirty、symlink、錯 owner／mode／common-dir 的工作目錄",
    "mock 掉正式 WorkOrder admission 後宣稱 Claude schema path 通過，或恢復 Legacy final-smoke schema",
    "複製舊 dirty worktree .venv 冒充 immutable Python runtime，或讓 sys.path 回讀舊工作樹",
    "force push、管理員繞過、直接寫 main、重用 stale PASS、增加 reviewer agent／排程／transport",
    "啟動 O2 Work Item A、產品模型 attempt、合併產品 PR、重發 Owner APPROVE 或提升任何 human/release gate"
  ],
  "validation_performed": [],
  "validation_results": [],
  "known_deviations": [],
  "known_uncertainties": [],
  "reviewer_focus": [],
  "preserved_human_gates": [
    "D2-T14-FINAL-HUMAN-ACCEPTANCE",
    "PA-HUMAN-1",
    "NS-HUMAN-SMOKE",
    "O2-PRODUCT-MODEL-DISPATCH"
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

Review `review-o2-prelaunch-hotfix-20261027-001` is `IMPLEMENTING`.
It has no active candidate binding and cannot be interpreted as a review request or PASS.
Codex must complete deterministic verification before issuing this request.
