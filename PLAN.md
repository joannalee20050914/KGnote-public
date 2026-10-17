# KGnote active execution plan

This file contains exactly one active execution goal. It does not promote any human product gate.

<!-- BEGIN CODEX PLAN JSON -->
```json
{
  "schema_version": "kgnote.codex-plan.v1",
  "goal_id": "GOAL-KGNOTE-D2-T01-SOURCE-LIBRARY-V1",
  "objective": "以 GitHub Issue #8 為唯一主動工作，最大限度重用既有 Markdown 匯入、canonical store（正式資料儲存層）與 Release 1 source-library/UI 證據，只補足持久來源資料庫、多檔匯入、對話 speaker、來源版本與可追溯讀回的確認缺口。",
  "status": "active",
  "active_milestone_id": "AR-EXTERNAL-REVIEW",
  "product_direction_id": "kgnote-obsidian-first-2026-09-22",
  "requirements_baseline_id": "kgnote-stage2b-feature-disposition-ledger-2026-10-16",
  "explicit_direction": {
    "date": "2026-10-16",
    "speaker": "product owner",
    "source_path": "PLAN.md",
    "durable_goal_record": "PLAN.md"
  },
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    ".ai/PUBLICATION_RECEIPT.md",
    "docs/PRODUCT_CONTRACT.md",
    "docs/DATA_MODEL.md",
    "docs/REPRESENTATION_CONSISTENCY_CONTRACT.md",
    "docs/requirements/README.md",
    "docs/requirements/DECISIONS_AND_CONFLICTS.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
    "DEVELOPMENT_PLAIN.md",
    "PLAN.md",
    "AGENTS.md"
  ],
  "requirement_context": {
    "github_issue": "https://github.com/joannalee20050914/KGnote-public/issues/8",
    "feature_dispositions": [
      "FD-01",
      "FD-02"
    ],
    "prerequisite_dispositions": [
      "FD-17",
      "FD-18",
      "FD-19"
    ],
    "requirements": [
      "KG-ING-01",
      "KG-ING-02",
      "KG-ING-03",
      "KG-PLAT-05",
      "KG-PLAT-06",
      "KG-ALPHA-01"
    ],
    "acceptance_criteria": [
      "RC-04",
      "RC-05",
      "RC-06",
      "RC-10",
      "RC-11",
      "RC-21",
      "RC-26",
      "RC-31",
      "RC-32"
    ],
    "scenarios": [
      "SC-21",
      "SC-28",
      "SC-31",
      "SC-44"
    ],
    "delivery_principle": "Existing Evidence First -> Reuse First -> Delta Only -> Verify Integration -> Build Missing Features",
    "forbidden_substitutes": [
      "重寫既有 Markdown importer、canonical store 或 review transport",
      "把 Release 1 舊測試直接當成本候選通過證據",
      "從私人 archive 整批搬入未審核內容或可變控制狀態",
      "把匯入過的來源重新改寫成摘要或失去原始 bytes",
      "將遭遇概念或對話 speaker 推論為使用者已理解",
      "把 PR #22 或任何舊 PASS 綁定到 Issue #8 的新候選"
    ]
  },
  "repository_authority": {
    "canonical_repository": "joannalee20050914/KGnote-public",
    "candidate_repository": "joannalee20050914/KGnote-public",
    "trigger_repository": "joannalee20050914/KGnote-public",
    "review_request_repository": "joannalee20050914/KGnote-public",
    "archive_repository": "joannalee20050914/KGnote",
    "base_pull_request": 22,
    "candidate_pull_request": 23
  },
  "previous_goal_disposition": {
    "goal_id": "GOAL-KGNOTE-STAGE2B-DELIVERY-PLANNING-V1",
    "milestone_id": "S2B-REVIEW-INTEGRATION-TASK",
    "disposition": "complete",
    "issue": 19,
    "candidate_commit": "f35669e11970e42f6a3d0a9fe218fb2b904ed835",
    "candidate_fingerprint": "e9355f736f6cd352955dae3311c7f86d5f9d4b01f10634ed4afce3360eaf61f8",
    "external_review": {
      "round": 2,
      "status": "PASS",
      "consumer_status": "accepted",
      "artifact_url": "https://github.com/joannalee20050914/KGnote-public/pull/22#pullrequestreview-5544513834"
    },
    "remaining_platform_limits": [
      "Scheduled run 與 Comment ID 6210434280 的直接關聯未能獨立讀取",
      "Work 寫回 GitHub 曾要求人工核准，無人值守發布仍未證明"
    ],
    "gate_rule": "Issue #19 的 PASS 只適用 f35669e/e9355f73；它不驗證 Issue #8、PA-HUMAN-1、NS-HUMAN-SMOKE 或 release readiness。"
  },
  "base_strategy": {
    "branch": "codex/issue-8-source-library",
    "base_commit": "f35669e11970e42f6a3d0a9fe218fb2b904ed835",
    "base_status": "PR #22 is open and unmerged",
    "integration_rule": "Issue #8 may be developed as a stacked candidate; its future PR must use codex/issue-19-real-review as the temporary base until PR #22 is integrated, and must not modify or merge PR #22."
  },
  "auto_advance": {
    "enabled": true,
    "requires_current_milestone_green": true,
    "requires_dependencies_complete": true,
    "stop_on_human_gate": true,
    "external_review_required_before_human_gate": true,
    "max_review_cycles_per_milestone": 5,
    "supplemental_review_cycles": {
      "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24",
      "scope": "Issue #8 bounded internal repair/reviews through the single cycle-17 review of PR #23 external findings finding-kg-src-revision-001, finding-r-004, and finding-r-005",
      "authorized_total": 12,
      "used": 12,
      "remaining": 0,
      "base_cycles_preserved": 5,
      "authorizations": [
        {
          "cycles": 2,
          "scope": "R-008 through R-010 concentrated repair/review",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24"
        },
        {
          "cycles": 1,
          "scope": "R-009 formal schema, Consumer, canonical decision bridge, and necessary tests only",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6213300000"
        },
        {
          "cycles": 1,
          "scope": "R-009 convergence repair: linked_findings integrity, handoff metadata, durable rejection, atomic decision projection, and necessary tests only",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6228024464"
        },
        {
          "cycles": 1,
          "scope": "R-009 record_id positive-integer contract, durable rejection, symmetric metadata, restart, and decision-queue invariance tests only",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6229026175"
        },
        {
          "cycles": 1,
          "scope": "R-009 complete external evidence lifecycle validation from acceptance through durable read-back, restart, human gate, and delivery completion",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6229229689"
        },
        {
          "cycles": 1,
          "scope": "R-009 canonical authority binding for the accepted external evidence lifecycle and necessary tests only",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6229457904"
        },
        {
          "cycles": 1,
          "scope": "One replacement independent review after a minimal pre-seal budget reservation ordering fix; same R-009 candidate only",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6229686177"
        },
        {
          "cycles": 1,
          "scope": "Final R-009 External Evidence Revalidation review only, after targeted tests, pre-seal budget reservation, complete pre-review gate, and exact candidate identity read-back",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6230751022"
        },
        {
          "cycles": 1,
          "scope": "One replacement review for the committed clean candidate only, after the shared clean-candidate gate, checkpoint commit, exact verification, read-only prepublication checks, pre-seal reservation, and identity read-back",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6231047878"
        },
        {
          "cycles": 1,
          "scope": "R-011 reviewer-context launch admission only, after bounded local repair, deterministic launch-count tests, clean checkpoint, exact verification, prepublication read-back, reservation, and Seal",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6231134202"
        },
        {
          "cycles": 1,
          "scope": "PR #23 external review 5556852723 findings only: unique A-B-A revision identity and stale locking, Markdown fenced-code speaker attribution, and PUBLICATION_RECEIPT authoritative-spec declaration; only after bounded local repair, clean checkpoint, full verification, prepublication read-back, reservation, and Seal",
          "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6231346877"
        }
      ],
      "stop_rule": "Preserve all 16 historical attempts. At most one review of the three exact PR #23 external findings may run as total cycle 17 after every pre-review gate passes; once its reviewer context starts it is consumed regardless of PASS, CHANGES_REQUIRED, stale, crash, failure, or no-verdict outcome. Stop after cycle 17 and never auto-extend to cycle 18."
    },
    "post_review_local_repair": {
      "authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6231346877",
      "work_package_url": "https://github.com/joannalee20050914/KGnote-public/pull/23#pullrequestreview-5556852723",
      "scope": "Only the three blocking findings from PR #23 external review 5556852723: unique A-B-A revision identity and stale locking, Markdown fenced-code speaker attribution, and PUBLICATION_RECEIPT authoritative-spec declaration; at most two local repair attempts.",
      "attempts_used": 1,
      "review_authorized": true,
      "review_authority_url": "https://github.com/joannalee20050914/KGnote-public/issues/24#issuecomment-6231346877",
      "status": "external_review_5556852723_changes_required_local_repair_attempt_1",
      "stop_rule": "Start cycle 17 only for the committed clean candidate after every authorized gate passes, and never launch cycle 18; a started context is consumed even without a verdict. If cycle 17 passes, at most one remaining real external Work review may run and no third external review is authorized."
    },
    "stop_on_review_state": [
      "PRODUCT_DECISION_REQUIRED",
      "AUTHORITY_CONFLICT",
      "AUTOMATION_BLOCKED",
      "BUDGET_EXHAUSTED",
      "GOAL_COMPLETE",
      "STOPPED"
    ]
  },
  "preserved_human_gates": [
    {
      "id": "PA-HUMAN-1",
      "status": "not_evaluated",
      "release_verified": false,
      "rule": "Requires native product and learner evidence; deterministic tests and AI review cannot promote it."
    },
    {
      "id": "NS-HUMAN-SMOKE",
      "status": "not_evaluated",
      "release_verified": false,
      "rule": "Requires native product evidence; deterministic tests and AI review cannot promote it."
    }
  ],
  "milestones": [
    {
      "id": "D2-T01-SOURCE-LIBRARY",
      "title": "Issue #8：整合匯入與持久來源資料庫",
      "status": "complete",
      "dependencies": [],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/control-plane/authority-lock.json",
        "DEVELOPMENT_PLAIN.md",
        "docs/requirements/",
        "src/kgnote/ingestion/",
        "src/kgnote/learning/",
        "src/kgnote/storage/",
        "scripts/serve_graph_view.py",
        "scripts/codex_control.py",
        "web/",
        "tests/"
      ],
      "acceptance": [
        "一般 Markdown 與明確 speaker 的對話 Markdown 可由現有產品 UI 匯入持久來源資料庫，原始 UTF-8 bytes、來源種類、speaker、locator 與 hash 可讀回",
        "相同來源與內容重複匯入不產生無界重複資料；相同來源的新內容建立不可變 revision lineage，stale revision 更新會 fail closed",
        "多檔匯入要嘛全部提交、要嘛安全回復；錯誤副檔名、空白、非 UTF-8、模糊對話 speaker、過大輸入及路徑逸出有可操作錯誤",
        "匯入結果可從來源資料庫及 UI 讀回，且與既有 canonical ingestion/storage 整合，不重寫既有轉換管線",
        "以 ordinary Markdown、conversation、duplicate、update、malformed、provenance、rollback 與 read-back fixtures 產生目前候選的實際測試證據",
        "requirements guard、相關 Python/Node 測試、Repository Preflight、secret scan 與完整 verifier 對精確候選通過",
        "Issue #8 與 Project 狀態、證據、剩餘限制及回復方式已讀回；不把舊測試或 PR #22 PASS 當成本候選 Done",
        "候選使用既有 GitHub PR 與 independent product reviewer（獨立產品審查者）流程送審，結果只綁定精確 repository、PR、HEAD、fingerprint 與 round"
      ],
      "stop_conditions": [
        "需要未授權來源資料、付費外部服務或新的產品裁決",
        "會覆寫人工筆記、刪除 immutable evidence 或無法安全回復",
        "PR #22 基準發生不相容變更，無法在不修改或合併 PR #22 的前提下繼續",
        "平台要求新的人工授權或目前權限無法發布／接收精確候選"
      ]
    },
    {
      "id": "AR-EXTERNAL-REVIEW",
      "title": "Issue #8：發布並接收精確候選的獨立產品審查",
      "status": "active",
      "dependencies": [
        "D2-T01-SOURCE-LIBRARY"
      ],
      "human_gate": "none",
      "owned_paths": [
        "PLAN.md",
        "CODEX_STATUS.md",
        ".ai/",
        "docs/requirements/",
        "DEVELOPMENT_PLAIN.md",
        "scripts/codex_orchestrator.py",
        "scripts/external_review_control.py",
        "scripts/external_review_handoff.py",
        "scripts/github_product_review_consumer.py",
        "scripts/publish_external_candidate.py",
        "schemas/product-review/v1/review-result.schema.json",
        "tests/control_plane/",
        "tests/test_github_product_review_consumer.py",
        "GitHub PR and Issue metadata for joannalee20050914/KGnote-public"
      ],
      "acceptance": [
        "Issue #8 product bytes remain unchanged after the verified implementation milestone except for required review/publication control receipts",
        "a Draft PR on codex/issue-8-source-library uses codex/issue-19-real-review as its temporary stacked base while PR #22 remains unmerged",
        "Publication Receipt, PR marker, remote HEAD, fingerprint, review round, repository and PR identity all match the exact Issue #8 candidate",
        "the existing independent product reviewer writes PASS, CHANGES_REQUIRED, or PRODUCT_DECISION_REQUIRED for that exact candidate and the existing Consumer accepts or rejects it fail closed",
        "Issue #8 and GitHub Project record the exact evidence without promoting PA-HUMAN-1, NS-HUMAN-SMOKE, or release_verified"
      ]
    }
  ]
}
```
<!-- END CODEX PLAN JSON -->

## Current recovery note

Autonomous orchestration state: `AUTOMATION_BLOCKED`. Active work package: `AR-EXTERNAL-REVIEW`.
Next action: complete the bounded repair of all three findings from PR #23 external review 5556852723, form a clean checkpoint, and launch at most cycle 17 only after every pre-review gate passes. No cycle 18 is authorized; cycle 17 PASS permits at most one remaining real external Work review.
Repository artifacts remain authoritative; PA-HUMAN-1, NS-HUMAN-SMOKE, and release_verified=false remain unchanged.
