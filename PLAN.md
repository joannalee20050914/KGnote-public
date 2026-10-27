# KGnote active execution plan

This file contains one bounded Control Plane hotfix execution Goal. It does not replace or change the authorized O2 Product Goal.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "CODEX-APP-GOAL-O2-PRELAUNCH-HOTFIX-20261027",
  "active_goal": "CODEX-APP-GOAL-O2-PRELAUNCH-HOTFIX-20261027",
  "goal_layer": "CODEX_APP_EXECUTION_GOAL",
  "authority_kind": "CURRENT_USER_EXECUTION_INSTRUCTION",
  "lifecycle_owner": "CODEX_APP",
  "product_goal_authorized": false,
  "objective": "集中修復 O2 首次 candidate identity、Ubuntu 真實 checkout、Claude Schema Admission 與 LaunchAgent Python runtime 三項阻擋；只在同一精確 Hotfix 候選取得 Ubuntu Claude PASS 且 GitHub 規則允許時合併，之後部署並重跑 Gate A–F，而不啟動任何 O2 產品模型工作。",
  "status": "active",
  "active_milestone_id": "H3-CLAUDE-INDEPENDENT-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "execution_direction_id": "kgnote-o2-prelaunch-hotfix-2026-10-27",
  "explicit_direction": {
    "date": "2026-10-27",
    "speaker": "product owner",
    "source_path": "docs/control-plane/O2_PRELAUNCH_HOTFIX_DIRECTION_20261027.md",
    "durable_goal_record": "PLAN.md"
  },
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
  "requirement_context": {
    "requirements": ["KG-GOV-04", "KG-GOV-05", "KG-GOV-07", "KG-PLAT-05", "KG-PLAT-07", "KG-PLAT-08"],
    "acceptance_criteria": ["RC-05", "RC-07", "RC-08", "RC-12", "RC-14", "RC-15", "RC-16", "RC-27", "RC-28", "RC-29", "RC-31", "RC-32", "RC-33", "RC-34"],
    "feature_dispositions": ["FD-17", "FD-18", "FD-19", "FD-21", "FD-23"],
    "scenarios": ["SC-32", "SC-33", "SC-35", "SC-48"],
    "baseline_evidence": {
      "receipt": "<host-runtime>/preflight/o2-20261027/PRELAUNCH_RECEIPT.md",
      "sha256": "0e8ad81ed66c453edc527449960a0ba40e8274b886db5cf2dbf0e786a1f8df1e",
      "outcome": "PRELAUNCH_BLOCKED"
    },
    "forbidden_substitutes": [
      "修改 O2 Goal WHAT、Requirement、Work Item DAG、模型額度、試行開始或硬截止",
      "直接手改正式 state／ledger、預填未來 SHA 或以 Legacy PR／candidate 冒充首次 O2 候選",
      "空目錄冒充 Ubuntu Git checkout，或覆寫非空、dirty、symlink、錯 owner／mode／common-dir 的工作目錄",
      "mock 掉正式 WorkOrder admission 後宣稱 Claude schema path 通過，或恢復 Legacy final-smoke schema",
      "複製舊 dirty worktree .venv 冒充 immutable Python runtime，或讓 sys.path 回讀舊工作樹",
      "force push、管理員繞過、直接寫 main、重用 stale PASS、增加 reviewer agent／排程／transport",
      "啟動 O2 Work Item A、產品模型 attempt、合併產品 PR、重發 Owner APPROVE 或提升任何 human/release gate"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "base_revision": "483f9e64066821d5d647d411e6da8ddb50ad88e5",
    "branch": "codex/o2-prelaunch-hotfix-20261027",
    "base_branch": "main",
    "draft_pull_request": null,
    "automatic_merge": false,
    "merge_authority": "exact Ubuntu Claude PASS plus satisfied GitHub rules under the 2026-10-27 one-time Owner instruction"
  },
  "immutable_product_goal": {
    "goal_id": "GOAL-KGNOTE-O2-READING-EXPERIENCE",
    "goal_version": "2026-10-23.2-s0-s2-proposal",
    "goal_spec_sha256": "82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604",
    "seed_branch": "codex/o2-reading-experience",
    "seed_commit": "483f9e64066821d5d647d411e6da8ddb50ad88e5",
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
    {"id": "D2-T14-FINAL-HUMAN-ACCEPTANCE", "status": "not_promoted", "release_verified": false},
    {"id": "PA-HUMAN-1", "status": "not_promoted", "release_verified": false},
    {"id": "NS-HUMAN-SMOKE", "status": "not_promoted", "release_verified": false},
    {"id": "O2-PRODUCT-MODEL-DISPATCH", "status": "forbidden_in_hotfix", "release_verified": false}
  ],
  "milestones": [
    {
      "id": "H0-BASELINE-RECONCILIATION",
      "title": "讀回 PRELAUNCH_BLOCKED、正式 state／ledger、遠端 refs 與部署入口",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/O2_PRELAUNCH_HOTFIX_DIRECTION_20261027.md"],
      "acceptance": [
        "PRELAUNCH_RECEIPT SHA-256 與使用者指定值相符",
        "遠端 main 與 codex/o2-reading-experience 都仍為 483f9e64066821d5d647d411e6da8ddb50ad88e5",
        "正式 state／ledger hashes 未變、candidate identity 無、attempts 為 0、Ubuntu 目錄為空且非 Git checkout",
        "舊 Issue #8 status drift 與其他合法成果被保留，不在其工作樹修改"
      ]
    },
    {
      "id": "H1-THREE-BLOCKER-REPAIR",
      "title": "集中修復首次 binding／checkout、Claude schema admission 與 Python runtime 部署",
      "status": "complete",
      "dependencies": ["H0-BASELINE-RECONCILIATION"],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "requirements-runtime.lock",
        "scripts/goal_runner_adapter.py", "scripts/product_goal_worker_identity.py", "scripts/linux_worker_bootstrap.py",
        "scripts/linux_worker_router.py", "scripts/local_autonomy_runner.py", "scripts/product_goal_worker_lane.py",
        "scripts/install_runner_python_runtime.py", "tests/control_plane/"
      ],
      "acceptance": [
        "detached Runner 只對固定 O2 version/digest 從遠端 product seed branch 讀回真實 commit/tree 並計算 fingerprint，首次 pull_request=null 合法",
        "首次 candidate/order binding 以 append-only ledger state_patch 持久化且 restart 可重放，錯 branch/commit/common-dir/digest/remote fail closed",
        "Ubuntu bootstrap 在模型前建立或重用 exact clean branch checkout，驗證 repository、HEAD、tree、owner/mode、非 symlink 與 Git common directory，非空或 dirty 不覆寫",
        "O2 Reviewer WorkOrder 從正式 projection 取得三項 Schema Admission，真實 WorkOrder 與 command/schema preflight 在模型前驗證",
        "pinned Python runtime 安裝與驗證程序記錄 interpreter、dependencies、sources、imports、sys.executable/sys.path、commit/tree、owner/mode 與 rollback，不依賴舊 dirty worktree"
      ]
    },
    {
      "id": "H2-EXACT-VERIFICATION",
      "title": "正反向測試、首次派工隔離驗收與 exact-candidate verifier",
      "status": "complete",
      "dependencies": ["H1-THREE-BLOCKER-REPAIR"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "docs/requirements/", "tests/control_plane/", "output/control-plane/"],
      "acceptance": [
        "2026-10-28 09:00 隔離 state/ledger 完整走過 ACTION_READY、initial binding、sealed order、Ubuntu checkout、pull-request 0、successor、verification、publication substitute、review schema、Consumer/Orchestrator substitute",
        "相同 attempt replay 不重複 reservation/dispatch，首次環境故障不會未結算連續重派",
        "10/27 不新增模型工作，10/28 09:00 開窗，18:00 與 11/10 hard stop 阻止新派工",
        "requirements guard、targeted/full Python/Node、public safety、git diff check 與 exact-candidate verifier 綁定同一 fingerprint"
      ]
    },
    {
      "id": "H3-CLAUDE-INDEPENDENT-REVIEW",
      "title": "單一 Draft PR 與既有 Ubuntu Claude 精確候選審查",
      "status": "active",
      "dependencies": ["H2-EXACT-VERIFICATION"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "GitHub Hotfix PR metadata", "existing Ubuntu Claude review runtime"],
      "acceptance": [
        "commit/push 後只有一個 base=main 的 Hotfix Draft PR，HEAD/fingerprint/diff/receipt 可讀回",
        "既有 Ubuntu Claude transport 審查三個原始缺陷與首次派工全鏈路，正式 Consumer 接受 exact result",
        "CHANGES_REQUIRED 只修 findings 並以新 exact candidate 重審；舊 PASS 不重用",
        "沒有 exact PASS 或 GitHub 規則不允許時停止為 HOTFIX_BLOCKED_UNMERGED"
      ]
    },
    {
      "id": "H4-MERGE-DEPLOY-PRELAUNCH",
      "title": "條件式合併、Mac／Ubuntu／Python 部署、Gate A–F 與 rollback read-back",
      "status": "pending",
      "dependencies": ["H3-CLAUDE-INDEPENDENT-REVIEW"],
      "human_gate": "none",
      "owned_paths": ["PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "GitHub Hotfix PR/main metadata", "Mac Runner deployment/runtime", "Ubuntu runtime/checkout", "LaunchAgent configuration", "prelaunch and rollback receipts"],
      "acceptance": [
        "正常 merge 後讀回真正 main merge commit/tree，建立 clean detached deployment 並部署相同版本 Mac/Ubuntu 程式",
        "LaunchAgent 使用新可信 Python，ProgramArguments/process/sys.executable/sys.path/owner/mode 與 runtime receipt 全部 read-back",
        "正式 state/ledger/Owner APPROVE/attempts/checkpoints 保留，正式時間檢查不啟動模型，隔離環境重跑完整首次派工",
        "rollback 實際 read-back 後正式環境保持正確新版本；若失敗則回復並標 DEPLOYMENT_BLOCKED_OR_ROLLED_BACK",
        "Gate A–F 與前次 PRELAUNCH_BLOCKED 逐項比較，O2 model attempts 仍為 0"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

The exact prelaunch receipt, remote refs and formal O2 state/ledger were read back unchanged. Work proceeds only in `codex/o2-prelaunch-hotfix-20261027`; the old Issue #8 and deployment worktrees remain untouched. The active slice is the centralized three-blocker repair. No O2 model work, product PR merge, Owner command, Goal date or resource change is authorized.
