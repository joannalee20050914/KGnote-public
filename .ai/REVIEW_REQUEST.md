# Current review request

Writer: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.

<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->
```json
{
  "schema_version": "kgnote.review-request.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "review_id": "review-issue47-end-to-end-autonomous-collaboration-004",
  "goal_id": "CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION",
  "milestone_id": "EG-4-TRUSTED-DEPLOYMENT",
  "status": "IMPLEMENTING",
  "author_role": "CODEX_IMPLEMENTER",
  "base_revision": "e3a2102f1d4822e2526c3b9db90903b1ee88f6dc",
  "candidate_revision": "e9955c778d0aa1ae0d2cc839345dbcbca0e4cc5d+worktree:428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716",
  "candidate_fingerprint": "428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716",
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
  "changed_areas": [
    "Owner v4 spec/schema/accounting and preserved v2 history",
    "no-model engineering wakeup admission, reservation and duplicate suppression",
    "unique LaunchAgent activation receipt, runtime separation, stop and rollback"
  ],
  "acceptance_criteria": [
    "Mac/Ubuntu runtime identity、manifest、installed hashes 與 no-model admission receipt 綁定 exact reviewed commit",
    "新 scheduler/launcher 唯一、預設 disabled、可逆且不共用 O2 state/ledger",
    "old O2 Runner 維持 disabled/unloaded；duplicate service、unexpected process、stop 與 rollback negative tests 通過",
    "舊 kgnote-47-goal Heartbeat 保持 PAUSED；唯一新入口在任何 Codex／Claude continuation 前以無模型方式驗證 v4 authority、time window、quota、backoff、Stop Marker、writer lock、paused heartbeat 與 dispatch identity",
    "相同 dispatch key 在 restart 後不得重送；不同且已完成的後續 review/repair identity 可接續，未決 reservation 則 fail closed"
  ],
  "negative_requirements": [
    "把 Codex App 工程 Goal 或 Issue #47 DRAFT 留言當成 Product Goal APPROVE",
    "把 readiness checker、單元測試、Draft PR、scheduler 安裝或 no-model admission 當成端到端自治完成",
    "建立第二套 planner、ledger、Router、worker 或 state machine",
    "修改、合併、重設或搬用 O2 v4 authority、state、ledger cursor 9、Codex 4/5、checkpoint 或封存 evidence",
    "啟用或共用舊 com.kgnote.local-autonomy-runner",
    "在 exact Owner approval 前或工作時段外啟動背景 Codex／Claude、正式 deploy 或 dispatch",
    "使用付費 API、force push、直接 push main、修改 branch protection 或未批准資料外送",
    "把 Codex-primary／Claude-reviewer 的證據宣稱為 Claude-primary／Codex-reviewer 已完成",
    "用 restart、日期、Goal version、branch、PR 或 session 重置 launch/accounting history"
  ],
  "validation_performed": [
    "./.venv/bin/python docs/requirements/requirements_guard.py check --repo .",
    "./.venv/bin/python -m unittest discover -s docs/requirements -p test_requirements_guard.py -v",
    "./.venv/bin/python -m unittest discover -s tests/control_plane -p test_*.py -v",
    "./.venv/bin/python -m unittest discover -s tests -p test_*.py -v",
    "npm test",
    "git diff --check",
    "internal validate_review_completion_gate",
    "internal public_safety_errors --scope fingerprint-manifest",
    "internal untracked_whitespace_errors"
  ],
  "validation_results": [
    {
      "name": "requirements_guard",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#requirements_guard"
    },
    {
      "name": "requirements_guard_tests",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#requirements_guard_tests"
    },
    {
      "name": "control_plane_negative_tests",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#control_plane_negative_tests"
    },
    {
      "name": "python_product_tests",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#python_product_tests"
    },
    {
      "name": "node_tests",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#node_tests"
    },
    {
      "name": "strict_git_diff_check",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#strict_git_diff_check"
    },
    {
      "name": "review_completion_gate",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#review_completion_gate"
    },
    {
      "name": "public_safety_scan",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#public_safety_scan"
    },
    {
      "name": "untracked_whitespace",
      "status": "PASS",
      "evidence": "output/control-plane/verification-20261031T113511+0800.json#untracked_whitespace"
    }
  ],
  "known_deviations": [
    "The old kgnote-47-goal Codex App heartbeat remains PAUSED and the new LaunchAgent is not enabled before this review passes."
  ],
  "known_uncertainties": [
    "Live provider launch and cross-workday resume are later authorized milestones and are not claimed by this candidate."
  ],
  "reviewer_focus": [
    "Prove no Codex or Claude continuation can run before exact v4 authority/window/quota/backoff/Stop Marker/writer-lock/paused-heartbeat checks",
    "Audit same-key restart suppression, new-key progression only after completion, and conservative unknown-reservation behavior",
    "Audit Product Goal and O2 isolation, exact reviewed-byte activation, runtime Stop Marker and rollback irreversibility boundaries"
  ],
  "preserved_human_gates": [
    "ISSUE47-ENGINEERING-GOAL-OWNER-APPROVAL",
    "ISSUE47-EXACT-PRODUCT-GOAL-CANARY-APPROVAL",
    "ISSUE47-FINAL-OWNER-ACCEPTANCE-AND-GO-LIVE",
    "ISSUE47-CLAUDE-PRIMARY-CODEX-REVIEW-PROOF",
    "O2-V4-FORMAL-RUNTIME-PROTECTION",
    "D2-T14-FINAL-HUMAN-ACCEPTANCE",
    "PA-HUMAN-1",
    "NS-HUMAN-SMOKE"
  ],
  "requested_at": "2026-10-31T11:36:57+08:00",
  "authorized_human_decision_identities": [
    "product owner"
  ],
  "candidate_manifest": {
    "algorithm": "sha256-canonical-json-v3-branch-independent-review-bus-exclusions",
    "branch": "codex/issue-47-collaboration-wiring",
    "head": "e9955c778d0aa1ae0d2cc839345dbcbca0e4cc5d",
    "excluded_paths": [
      ".ai/DECISIONS.md",
      ".ai/ORCHESTRATOR.lock",
      ".ai/ORCHESTRATOR_STATE.json",
      ".ai/ORCHESTRATOR_STOP",
      ".ai/REVIEW_REQUEST.md",
      ".ai/REVIEW_RESULT.md",
      ".ai/external-review-state.json",
      "CODEX_STATUS.md"
    ],
    "excluded_prefixes": [
      ".ai/ORCHESTRATION_HISTORY/",
      ".ai/REVIEW_HISTORY/",
      ".ai/WORK_ITEM_REVIEW_HISTORY/"
    ],
    "entries": [
      {
        "path": ".ai/CLAUDE_REVIEWER_CUTOVER_EPOCH.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "82f821fa11fccf630dce13d4df75aece38f1374b45ab9b227ca3982faedb5cd0"
      },
      {
        "path": ".ai/IMPLEMENTER_BOOTSTRAP.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a73223df1a1b8d7acab5435eb94387d48bf6a146d1eb77b10a6398e0773956ea"
      },
      {
        "path": ".ai/PUBLICATION_RECEIPT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "faa782db79750fd2a31c5564ce00861ebfb26b33a37b2d447abfb2f56c3d694e"
      },
      {
        "path": ".ai/REVIEWER_BOOTSTRAP.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "251c865e67f8f099caa0528964c6d209d9c645fc1f2d1ab009c7941e70d0aef8"
      },
      {
        "path": ".ai/REVIEW_PROTOCOL.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7e3f2f1295b6cb0b391ad2e462f169f8c70a28a3448299eb315f96821b7ef247"
      },
      {
        "path": ".ai/SUCCESSOR_CANDIDATE_IDENTITY.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9f744872d48dad33d8ef9d55c0bff95864864a9ebe2ffb6c1e528ee0e1d971a0"
      },
      {
        "path": ".ai/github-product-reviewer.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bc56ce794fc43e179b4112dbee45a2d46891e7b9078c34e968e4c248f9ccbde8"
      },
      {
        "path": ".ai/schemas/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "04dc3b6fb4e551596a453a02d7a5ec774a25ddf4cb62904892fe17f712e70d5f"
      },
      {
        "path": ".ai/schemas/orchestrator-state.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d3d08af3370dceec3bddc9f97c4e9be6fa400d2c6b0665c2247dd428810c1ec5"
      },
      {
        "path": ".ai/schemas/review-decisions.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "954a2194d347fe9ba8c584b0ba9cd5de448f8f046fd312585da4bda58b7466aa"
      },
      {
        "path": ".ai/schemas/review-history-index.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f5f8a51fca00f746071ad07077eb42d1b6f5a59b093cc383f64ef67a00d262ef"
      },
      {
        "path": ".ai/schemas/review-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "72be5fa170bb2f329b33ae26b31417f5f834668b387ec2c4cdb807831b8ba1e8"
      },
      {
        "path": ".ai/schemas/review-result.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7b129cca0b306c5e8a38c4409d28730a3b411aac741a993c201ec3b8e3a01e90"
      },
      {
        "path": ".env.example",
        "kind": "file",
        "mode": "0o644",
        "sha256": "25fcdfeb10eb260d15a604f33ae20e719e36f5d759a753b94311b32d613fa4ca"
      },
      {
        "path": ".gitignore",
        "kind": "file",
        "mode": "0o644",
        "sha256": "653a8436a8cb234ab231644d103028753ca389811c260b8c2a716126c56ab05c"
      },
      {
        "path": "AGENT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "04e012613ee91ec401c2a37597d1da3cb9a2a61556a85ed3bd0b1e6353c9cd68"
      },
      {
        "path": "AGENTS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "407f9a883f59b5ee93822fb47bcfd130b5e3791ec0734c061f402ab07ba37dfa"
      },
      {
        "path": "DEVELOPMENT_PLAIN.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b37392c8ea2544cd5e16248c413b72240b84f3e96295f8ceeb7c6580164ce758"
      },
      {
        "path": "PLAN.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5610fc01d39088be33e4bf7f5fccae432516abeff2fe3a69b9f8a4841255f30c"
      },
      {
        "path": "README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f78c0e8df9bf35683039e71d4f5956532bd09dfd6751d0e5476e411fe61a841a"
      },
      {
        "path": "config/ubuntu-worker-runtime-manifest.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e17c0471ed727d71319842f204988860e258a47ef35d8d017604966a3e99781b"
      },
      {
        "path": "docs/ADR-0001-GEMINI-EXTRACTION-TRANSPORT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "938a6dda25927d4874ac883bd90799470bde9f5f29d12162878997a138eb6b7e"
      },
      {
        "path": "docs/ADR-0002-OBSIDIAN-DISPLAY-LABELS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "678e4e7b318f7ed0e62ff91842f1d68bf28531c3e2e0dc74bd35b18d89c28e4d"
      },
      {
        "path": "docs/DATA_MODEL.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fad89739d1eb1fed6342c6367383ab0e2cdebaab0f8ea605aed181ecec34b7b2"
      },
      {
        "path": "docs/PRODUCT_CONTRACT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "baf77edc9edde436c325c1454ca104a2994ef329170997c486fa99efcddf48e0"
      },
      {
        "path": "docs/REFERENCE_SOURCES.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d63d7a7def82e2cab5607a7bb4f972eb3325cc0e1ff40204ad1f26de2ad8901c"
      },
      {
        "path": "docs/REPRESENTATION_CONSISTENCY_CONTRACT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "19a25bdfa850125e475884fcd6ae2984fc25537c8451f78f10b04c78d294124c"
      },
      {
        "path": "docs/WORKFLOW.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c2c802bf290e47123639b27fb8de9bc571e7dddef6623d82d41fa786ab3955dc"
      },
      {
        "path": "docs/control-plane/AI_REVIEWER_CONTROL_PLANE_COMPLETION_AUDIT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "dc1a8c15058ad4ab2c1f78c65152156f29e4cba7cc7934dbee6ee22334d1261a"
      },
      {
        "path": "docs/control-plane/AI_REVIEWER_CONTROL_PLANE_GOAL.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6ca005c1fc4b2b64d8190f52e0440a0903ce2a9fec76dade59f1cfc9b9eab9cc"
      },
      {
        "path": "docs/control-plane/AUTHORITY.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "34061a0415e76d15b2273e1e39ed5de08bd7952307c54d9f0fe96de1038676dc"
      },
      {
        "path": "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c2fd7abbcd0cb9d756d7929cae1512008d2d1b969ca81d2686b75ff4d0803e8a"
      },
      {
        "path": "docs/control-plane/AUTONOMY_GO_LIVE_APPROVAL_PACKAGE.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fc82d0db2b9179149dcc643ba55b1bfde83d4658f2ac080a51cce2319a6b3634"
      },
      {
        "path": "docs/control-plane/BASELINE_WAIVERS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c2f4e6e6edb7e034d9a25119a2b92961452fe61fc54d1421661ad84620b52113"
      },
      {
        "path": "docs/control-plane/BOUNDED_TRIAL_READINESS_DIRECTION_20261023.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8f62cd4ab95fa2de9e718dc95e67cbeb4eff45a3af9f00ae94d3eaeb8b0b0b3f"
      },
      {
        "path": "docs/control-plane/B_SCHEME_OPERATIONS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e8a065de7ae77270e220c5aaf718e70358f1fb2cdc8bb4c16c1b4ed1aaf4193b"
      },
      {
        "path": "docs/control-plane/CANONICAL_PUBLIC_REPOSITORY_MIGRATION_20261005.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f21e3034915d30cd4fcaabfb1d3628ecc1f522f2140f53970b56960f313d160f"
      },
      {
        "path": "docs/control-plane/CLAUDE_REVIEWER_BILLING_POLICY.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "233ec41928855ba4c74702077517a86a91678d65ae5c833b4400e92181125212"
      },
      {
        "path": "docs/control-plane/CLAUDE_REVIEWER_INTEGRATION_20261018.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "87cd5e85153e8e9570b2a379b506c112531c2f8ff55a7dd915568468e8de64f0"
      },
      {
        "path": "docs/control-plane/CLAUDE_REVIEWER_ROLE_DECISION_20261020.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "46704b79add5fa6ec325279c63286c4ee9d23779a7d6a6f95cbadcee586190b6"
      },
      {
        "path": "docs/control-plane/CONTROLLED_RECONCILIATION_20261018.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ef19c8bc29c2dab69b61d394cc9cfc070bd596b2e0d0b936f9a17f9c1a73f175"
      },
      {
        "path": "docs/control-plane/CONTROLLED_RECONCILIATION_RECEIPT_20261018.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fafcac0a9458ea537415e9640a7a5eb807ca3e962aab15a88425722c5036582b"
      },
      {
        "path": "docs/control-plane/FINAL_CUTOVER_AUDIT_AND_MAC_MVP_20261018.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8f03a37e20fc1cd0269f7e89a923383b2d412498a018f2a122f07caa205584f5"
      },
      {
        "path": "docs/control-plane/GOAL_SCOPED_CONTINUOUS_DELEGATION_20261022.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0e49c6256742c17c04043820f5ef4f0a06e3560b1da2a89905399c91eb13abe5"
      },
      {
        "path": "docs/control-plane/INCIDENT_EXTERNAL_REVIEW_BYPASS_20261007.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6c0266f02944a2475ecdd933a698fad81f8d5853599cca9fe61e4d380c8cabd0"
      },
      {
        "path": "docs/control-plane/INCIDENT_TRIAL_IDENTITY_DRIFT_20261007.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c69a13d519db4641086794e7c75cf8f2d41471cf5e7a4b18c1c88600f6555a90"
      },
      {
        "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261030.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "771567629353b2475d5eef6cdcb5664c43c6353c7667bf18697ab745442fc580"
      },
      {
        "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_AUTHORIZATION_PACKAGE_20261031.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b3a21f885dd89435bf35e280dd7fbaa2f89d97da52f1ea5c442d700129d76862"
      },
      {
        "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-30.1.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fd96f191eb004db021faa8bf0b9e74dccc7e97a7d3031be020bb8e94d3cc7c27"
      },
      {
        "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6ff6bf73c45eb32f14677c596f53c0d1390709e6a9919be7258885f3d42014db"
      },
      {
        "path": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.4.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "67ecb2af524fb4934526e57420afbb783dc2b9120d8f2c5b35c0429626c72335"
      },
      {
        "path": "docs/control-plane/ISSUE47_ENGINEERING_AUTONOMY_CONTINUATION_AUTHORIZATION_20261031.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e3c67f4ae21585549f76f1153bcf129b23590d4322e8f7c53f37247e433da3db"
      },
      {
        "path": "docs/control-plane/ISSUE47_ONESHOT_ENGINEERING_DIRECTION_20261030.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "305aa49bbaa71c4f67aa92dcd5033832b1f2a57d02e1200cd9308fe87a8264f8"
      },
      {
        "path": "docs/control-plane/ISSUE47_WEEKEND_ENGINEERING_EXCEPTION_DIRECTION_20261031.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a0ef710faf856b6bbfdc47f4d9f94f480953e7062d1e80af4c3aa1a68ac5fed0"
      },
      {
        "path": "docs/control-plane/LEGACY_ISSUE9_DISPOSITION_20261023.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "83fd2ff2f779ecb6f2cf929ee8b9057fe1385b4be824b9a730e98abff5e2cdcf"
      },
      {
        "path": "docs/control-plane/O2_ADMISSION_EVENT_ID_REPAIR_DIRECTION_20261029.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "47d7742fadab497ef71c74c6e2d09515197e84d936e7bde3b26b2dbad7ce2c1e"
      },
      {
        "path": "docs/control-plane/O2_BOUNDED_TRIAL_AUTHORIZATION_PACKAGE_20261023.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "96da190b158b1e1220469207658914b83ebfd2b1663a7fb231193ce74b387b0e"
      },
      {
        "path": "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.1.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d3a5e541292b8c53e6fe61b7dee8cbf05b8959c38672ea5c836a4c1576a82413"
      },
      {
        "path": "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8434386012c09546b5c3dd17a86c78ef05248d5391699398efc8beea526e7fd9"
      },
      {
        "path": "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.3.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f8cb543fa9bd887ab93887f13a2dc0917d212fb98ff4860938e77d3da918fdf2"
      },
      {
        "path": "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7e32c5000c6fc22d540db9afac3eb22679ca2ad5ae4de415067531485628549e"
      },
      {
        "path": "docs/control-plane/O2_DAY0_ACCELERATION_DIRECTION_20261029.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "cad1184a6361f2ec8f3934b2aba6e12368e6da06acf699363e41e5dd05b81b8f"
      },
      {
        "path": "docs/control-plane/O2_PRELAUNCH_HOTFIX_DIRECTION_20261027.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "19f826bc20163e58a9c2396015a7c2d9bb21cc8dffefe81bd9a5aac9b6e63580"
      },
      {
        "path": "docs/control-plane/O2_PRELAUNCH_HOTFIX_VERIFICATION_20261027.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1928d1ad76dbe5634cbf5ec07bc25d4a6ff0fbf1711d5ef0593fef02b170a130"
      },
      {
        "path": "docs/control-plane/O2_RUNTIME_CONTEXT_RECOVERY_DIRECTION_20261028.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "813727dd3fae9b5bd40f6fcb3caf57de1d6cd5090de23536a091161f18185cca"
      },
      {
        "path": "docs/control-plane/O2_RUNTIME_RECEIPT_PRE_RESERVATION_DIRECTION_20261029.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "383542d059dc116aaeb98e133da6fd0cb6dde5e471b4ff7f221a765cf28f604b"
      },
      {
        "path": "docs/control-plane/O2_S0_S2_LAUNCH_PREPARATION_DIRECTION_20261023.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9c3b2fc53442cba166a137609c9d507faf9b058d152b4df5a1ee6b22f3107056"
      },
      {
        "path": "docs/control-plane/O2_S0_S2_LAUNCH_READINESS_RESULT_20261023.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "11b556ad3c24553989ef68bf814ddd61886121a05368a0059d62fa506f7ab4b0"
      },
      {
        "path": "docs/control-plane/O2_SUCCESSOR_RECOVERY_DIRECTION_20261030.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5e03c2a4fa8ab147c11802816782ed691d5cefeeaab9df97f19a12fe975a2087"
      },
      {
        "path": "docs/control-plane/O2_V3_CARRYOVER_EVIDENCE_20261029.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5a3c3311817f93cad8ee537023f8a5eb801fc550b579111a74431bd3323d663b"
      },
      {
        "path": "docs/control-plane/O2_V3_REAUTHORIZATION_READINESS_DIRECTION_20261029.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c14d3fbf8ddb4d52f2b579f384975ec0fc60a8e0611c500811aa38052683e4d3"
      },
      {
        "path": "docs/control-plane/O2_V4_CARRYOVER_EVIDENCE_20261029.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b7bd6988453b9285d512163c07bb97f9261bd50240cecf3d20a69cf44f5d36d8"
      },
      {
        "path": "docs/control-plane/O2_WORKER_RUNTIME_IMPORT_REPAIR_DIRECTION_20261028.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3e47100e60f55071ff8b53275e8d64def123e6c89e2eb2766c2a2ccf2f40a6ba"
      },
      {
        "path": "docs/control-plane/PR28_ROUND6_CANDIDATE_COMPLETE_AUDIT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "af4cdd845f3c5b9c604999bbf0e9d955cce2edaf0014f3aca6cc23084af9984a"
      },
      {
        "path": "docs/control-plane/PR28_ROUND7_ROUTING_REPAIR.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f5e5734022942192636b8ce58ac7faca30dc048146a853f0a5d04df7ded35c5e"
      },
      {
        "path": "docs/control-plane/PRODUCT_GOAL_BACKLOG.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "13852b5cde594c2e0125768a1d7aa4dd2fb70815c01a12b9e4d806ef495c2bef"
      },
      {
        "path": "docs/control-plane/PUBLIC_READINESS_REMEDIATION_20261005.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c2ef6375b3e20c4caadf96fd663a7fdd78b7e356274627801214e48d718c8b25"
      },
      {
        "path": "docs/control-plane/UBUNTU_AGENT_MODEL_POLICY.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bda1d5f5081113a6b8f436d938b3547b7fa0d7622d1a9d36952b59734644f34b"
      },
      {
        "path": "docs/control-plane/authority-lock.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "40285e2066915893ce226c7e31a44c0f97c164931e7007182b68e6adae9f2960"
      },
      {
        "path": "docs/control-plane/checkpoints/cp0-pre-control-plane-20260922T135255+0800.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c6274ab5db934c91c1e42baa3213fb1591d18917a26d9f7ddbafaa9711527446"
      },
      {
        "path": "docs/control-plane/checkpoints/public-readiness-pre-rewrite-20261005.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6450347a61a671dd7b30cb9f8444b7bde60945794e6cefad9fdf3537a22f8d8f"
      },
      {
        "path": "docs/control-plane/evidence/b-scheme-baseline-audit-20261022.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e5268a3f28bc9125d76fa1249fc38de800993da355e13835b8fa3bf03f16501f"
      },
      {
        "path": "docs/control-plane/evidence/b-scheme-isolated-trial-20261022.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "efc4770cf20de5310c52819dd427b48136678415f61f24aa97a07e4fbeb66e8b"
      },
      {
        "path": "docs/control-plane/handoff-drill-20260922.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e8b9b2384a00d524c0d2d5e2072e9d6a68120ae00e28acac401fc30c66d2a939"
      },
      {
        "path": "docs/obsidian/LEARNER_PROJECTION_CONTRACT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ed4fae7a1b0e0879ecb34d08476e67d3b3b236cadd238862f36d56b9c721d2a7"
      },
      {
        "path": "docs/obsidian/NATIVE_ARCHITECTURE_DECISION.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5c7265aa963bb8d2aa911b8e5cedd9ea66fbc5495c5b37c121709b3b7585e983"
      },
      {
        "path": "docs/obsidian/NATIVE_CAPABILITY_SPIKE.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "42f05f2b08aa77a1efc15bf33b6cbf63c36e0f7a122f0551b04a155521e0c37c"
      },
      {
        "path": "docs/obsidian/PERSONAL_ALPHA_INTEGRATED_TRIAL.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4c375714d8fbfe8148c69937587b30140cd243f2ece58f7d74c0842ddeb87611"
      },
      {
        "path": "docs/requirements/ACCEPTANCE_SCENARIOS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b03e176021201550cf633766089f082c833b0657e8968d026d91e81ec8305c65"
      },
      {
        "path": "docs/requirements/AGENTS.requirements.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c9c610069a997047ccf510c11db45e14add5623989face9c564a753876200a4f"
      },
      {
        "path": "docs/requirements/ARCHITECTURE_AUDIT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "69e52500da03e75e8d032bed4a523f1bc71aa877f67f2000546f0576ee6b5771"
      },
      {
        "path": "docs/requirements/BASELINE_IMPORT.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "58c0602445192c9b11abadc257199bb50a026ae29d6c8bbe2703eaef84a71c0f"
      },
      {
        "path": "docs/requirements/CODEX_INTEGRATION_PROMPT.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "309a0bcc3cf53514b109a57907ca1d3ec1e11af32544c775c782cd71190d0f08"
      },
      {
        "path": "docs/requirements/DECISIONS_AND_CONFLICTS.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ba3b0f8aafbb9359764e635b46717d12cc89b77e6342d442a0f5aa6fc80ae943"
      },
      {
        "path": "docs/requirements/EXAMPLE_TASK_PACKET.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c948afef67ab5a94974025dbfad421ca09e46635a6b107038092dc38f717c8fe"
      },
      {
        "path": "docs/requirements/FAILURE_MATRIX.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e5282b9f1c5593ca9abb3f580e3d6d18aae49c5383a22c1b190d5e2cfc5655be"
      },
      {
        "path": "docs/requirements/FEATURE_DISPOSITION_LEDGER.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "21d31b596af8d689c9b30e5f3c33ea1c394dcdf6952b52e563b4889558ef1905"
      },
      {
        "path": "docs/requirements/MANIFEST.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9a397bb0a1ac90a2c31458aa14fc43e2cfc4b4259213d4f41ed1a10be3fa37b9"
      },
      {
        "path": "docs/requirements/MUTATION_REVIEW.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "df745897543b328e7026d4f84d6d99408d5fbee4f627fb76c962a171653cbb4b"
      },
      {
        "path": "docs/requirements/OBSIDIAN_LEARNER_PROJECTION_NATIVE_SPIKE_DIRECTION_20260923.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "79390360bc9bfff47083b0a5b17257dceec728cf0f2fac92e0bd4ca9ee7c5d30"
      },
      {
        "path": "docs/requirements/OBSIDIAN_NATIVE_CAPABILITY_SPIKE_DIRECTION_20260923.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "277e576d3951cb0dd4b9ed133dcbf0eb552ed4b31dc4fd90c704179dcff39b30"
      },
      {
        "path": "docs/requirements/PERSONAL_ALPHA_DIRECTION_20260922.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "522d9cc3e6d0822e7e38a6d31d1d2c512bae7bc781259195eb1442621871dc09"
      },
      {
        "path": "docs/requirements/PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c573dd8a2704ff61100bb6761bdd712fdc4d404a59bb72c5e42c20ed8a054ddd"
      },
      {
        "path": "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "32a4bfd100952edbf80ec6ae9f8dc31c75c02dab295398554d3bac3cee7d22ab"
      },
      {
        "path": "docs/requirements/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "db8d17eb7204cf43bc022b77124c4c3e95be0802f8f7e6172cb7900604335b7a"
      },
      {
        "path": "docs/requirements/REQUIREMENTS_TRACE.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "580f77178ae612edc00c77544d3d6a9a672b276275c2336c487a7b6ef5d911b2"
      },
      {
        "path": "docs/requirements/SOURCE_INDEX.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5975b4664e82d23f804be20a8b1687e42437d9901e31b141000a9997120ecccf"
      },
      {
        "path": "docs/requirements/TOOL_VALIDATION.txt",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1fa26a170b6bc555248dff25b8f70aa10a4451555138c3a863c825fabdaf6eb2"
      },
      {
        "path": "docs/requirements/TRACEABILITY_MATRIX.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6a64fa2e08d5f2f73aae9aa2e03b9850625092f050e8170672ef611081da4bb4"
      },
      {
        "path": "docs/requirements/USER_DIRECTION_DELTA_20260922.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "75adfd0fadbd8e6835f23c126d867eed0ab94f95a135e9e6c8a89cc71cdf819f"
      },
      {
        "path": "docs/requirements/evidence/baseline-20260920.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2bf1bdfacfde86da2dab2994dd30990e350dd53180fd180ca8901633cac44190"
      },
      {
        "path": "docs/requirements/evidence/codex-review-completion-gate-20261022.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "71545f3674836fe3e422f6b4355f704011b85cdb600f640b94519935eaaa13d8"
      },
      {
        "path": "docs/requirements/evidence/d2-t01-source-library-20261016.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a57bbde99da3d8200cf95b9bfaa6565d2b29a7eb0b5b7d110b70f4b7575a512e"
      },
      {
        "path": "docs/requirements/evidence/loop1-20260920.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "74e4c9405defdd3efd29be2595b20386286fc1ce791442d5185b153a5c7285cf"
      },
      {
        "path": "docs/requirements/evidence/loop2-20260920.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "59f0d467bab6aea9ca2977bd4f0dedf01fe8e818314ce3d4412ac33346a8e3bb"
      },
      {
        "path": "docs/requirements/evidence/loop3-20260920.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1dd35770de35c5ec6c77fc6430a9d5e50ca6f71aa6bc7e6750b4ff77c39b9ea7"
      },
      {
        "path": "docs/requirements/evidence/obsidian-native-v3-20260923.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f90922b030e607c2cc39fda6dc609023448b288064e14f2dcbe76683cddd65c3"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-human-feedback-20260923.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1daa2c4c643f646af1ad9c10d93af0d89481430a05ef5e244db951310b6f1fce"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-pa1-20260922.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "02abc370a5c78c1b996c4963c389972bf17dd920a7e5c6863efcf613da72b26b"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-pa2-20260922.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a1181b55b970f5d792e5119bcf11c135785d89af6f0441c9a2341bb051d3def0"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-pa3-20260922.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e33b14611fbcfa9b10f3244cf142fb96128508f5acba67f2a9b0cf83bd7c846e"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-pa4-20260922.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a5c558aad6b42b2efea563977933662c5ad7ee87d1a3ffe5ec988b5c4306ad1c"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-portability-repair-20261007.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c9260bf20a9421b59671d1a91a19969f5143f5c9e36525dae6a09b07bea2c82c"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-rp-pa-1-20260927.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3380bad936953d541047ab81ef7b84478fd738215c672b4a63eea4cc85d7232b"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-rp-pa-2-20260927.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a84e66cdf10d905443178ba838df5440c8d2b00187409c88dd5d03e65ca6b1b0"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-rp-pa-3-20260927.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9a9f694351b6ab559c02e50fa97b744070cb95cb49166130ae9546cf70e8851f"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-v3-partial-feedback-20260927.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1e2250bcba50c2295b8c2ef93c8af70db3084fa6f862c656962127cf0f89ed38"
      },
      {
        "path": "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d5d72a2a4d70fedc13da3611ab4f48abec1ff56950581d7833a34a475306ba6c"
      },
      {
        "path": "docs/requirements/requirements.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7839bf327748a8d5d35ede5786540deb56f10e632a34a1b52808029718f47d3a"
      },
      {
        "path": "docs/requirements/requirements_guard.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "65f59b23e148cccb8a672d48d3b6c407c6b3ac4a19b7b96c90a8d4a27917a0a4"
      },
      {
        "path": "docs/requirements/scenarios.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "47d9e2e85b921c777c0e31abd046fad4dd577e2addbbe42d2972f7e546be642e"
      },
      {
        "path": "docs/requirements/sources.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1891de3770dd5e1ac44f0af8c47ea83aff6c4e506a76cafa6636e8285f7b0d53"
      },
      {
        "path": "docs/requirements/test_requirements_guard.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3be0b205ffccaa5a142b74a1ebb65aa00ab1f1114b6cfa4e422cfc51cdc7e917"
      },
      {
        "path": "experiments/fixtures/h0-bitepacer-p4-backup-v1/store/raw/bitepacer-p4-backup-micro-source.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1894be5e931ab49dba123d4a57f0ea2dbcd7bfe372faa5f3bd99bff70d385916"
      },
      {
        "path": "experiments/fixtures/h0-bitepacer-p4-backup-v1/store/sources/src_bitepacer_p4_backup_micro.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6fc1df4a7ff16ab7cef1f7e66afd2776d5289039628f1b754b56ebb2fbd1a30f"
      },
      {
        "path": "experiments/manifests/h0-bitepacer-p4-backup-v1.yaml",
        "kind": "file",
        "mode": "0o644",
        "sha256": "62987669e12c57208f4410103cd428688383c77d1eb00abc48873a5f0da303c2"
      },
      {
        "path": "experiments/templates/h0-bitepacer-run-record-v1.yaml",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fd86687c3414ccd81e919da4328eba8e782d83c6d4a326428463708405375889"
      },
      {
        "path": "fixtures/phase0-obsidian/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "06c9a03bdbb35bddc0d2cbdd916675cf8bf299784bce8cead6563036b4dcde67"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_causal_inference.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c510f46708e7ee3278c854d953350f1f2f6a73c986bf44752f4cab23d7d8915a"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_causation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1349555926da61040b70eab8558b42febf68f7afe2907a6dd14d9ff0cab770ec"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_confounder.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ec6a45b4dc630d9b25e8c8c614c98bd0e53f7484975dabe498a371774c30a1d5"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_correlation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2415d144a76341eb92697d12c8ad1b01792e692bd5ad409a1a348082e582ed06"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_counterfactual.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a61323d3e53812a14e09a6c3c657f4d9f9fd4cf9f36ad8242d295ce7e5b33b0f"
      },
      {
        "path": "fixtures/phase0-obsidian/concepts/concept_randomized_controlled_trial.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ba940bad5acbeb61c031ada0348eb7276005dbe8f30c5608c798abc0f32e6cea"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_causal_inference_counterfactual_unresolved.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "474a5254833a1f67819da00cd6f78aa7a6687d7be187052ca15169e74046784a"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_confounder_related_correlation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5a0c000a7ebf84c697cc10fd8cb0af93dbeb2bc08212ba8120cb871f9097cba3"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_correlation_contrasts_causation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f0555aa2dc75eb992255b80c98a04c92170690438f3d5a7975414c8f668416d0"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_event_applied_confounder.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "404c6170b2090bea7fa40ba76667843855250c434efa2a85225a0ae45a03587b"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_event_asked_causation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0da4f29ba841f8b805366d9a17b7117c1d1da884fe616f215d290bf6a785f214"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_event_asked_correlation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "67c9ba065284b1522296ad777ad66d75fc0286537bb33fc64c475106051e173e"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_event_encountered_counterfactual.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "225c5cc663a61deb84d2696c765f80415c9f4b2f1c60628540b8cfd66c3d03b2"
      },
      {
        "path": "fixtures/phase0-obsidian/edges/edge_rct_related_confounder.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c3298c84336d6708a884aa981b0e3b487b79a84e5915ff77167f391a7a006ef6"
      },
      {
        "path": "fixtures/phase0-obsidian/evidence/evidence_apply_confounder.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ac615a2ac7c29e18920d0de1d7afde30893b0718f35acb97eb42c179e90bf6f5"
      },
      {
        "path": "fixtures/phase0-obsidian/evidence/evidence_counterfactual_unresolved.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "65b0f16b3951853f8ae50c6efd65eba78168e97a9c400361d5cddd8bf45be17c"
      },
      {
        "path": "fixtures/phase0-obsidian/evidence/evidence_define_correlation_causation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "83ca5512a1df6111eb9496de52d27282fa711acd8816719960f97127f40a7fb9"
      },
      {
        "path": "fixtures/phase0-obsidian/evidence/evidence_question_correlation_causation.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f22c4fec330bdb5633a889fc431bdf7c81811202aaaa932de062b7a1ea7ad6d9"
      },
      {
        "path": "fixtures/phase0-obsidian/learning-events/event_causality_question.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0c06a0274be6b4b204965c95bf7356bfa796799e77e5fbd8918ca01995578d58"
      },
      {
        "path": "fixtures/phase0-obsidian/raw/synthetic-causality-chat.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9e2a61399ba4d19ca14e9e0332ea8df8d92dade379f047a8afb7533956c5faf6"
      },
      {
        "path": "fixtures/phase0-obsidian/sources/src_synthetic_causality_chat.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "da19bff88f56ccc6036ac7f8d094fc4d485e9bf222046ebb4d9aa400ac070df8"
      },
      {
        "path": "package-lock.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0d386bff67bd52e27ec0e9dc5d19ffebe4c43f9fd29683e0ae753bcb526704cb"
      },
      {
        "path": "package.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "dfc90dcb322487070e9cad73e5a9a7e98efd79d8de51533378d0b1c5779dc17f"
      },
      {
        "path": "requirements-dev.txt",
        "kind": "file",
        "mode": "0o644",
        "sha256": "69075054c6d3bf5e0104bbc5d72895f380f050216a76ee8978dc4fbfd62f95e8"
      },
      {
        "path": "requirements-runtime.lock",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a9db5168a3a79329c2ff51b11c7f546f214bc74e8659a7f7e8366ce3e8bf9791"
      },
      {
        "path": "requirements.txt",
        "kind": "file",
        "mode": "0o644",
        "sha256": "65fe7e9dbb82751c9da89b2e0d4457f87136d4166bbeb109e071ae448cea8a7c"
      },
      {
        "path": "schemas/attempt-feedback/v1/save-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3565f348e290d4c4a9ec841b7cc394cd0243b8d6ed342e1b3b8a6c00fb4331f7"
      },
      {
        "path": "schemas/attempt/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a4c53fb442d7b0a3636779c748cc6628277943d95f510d4300d57806cbb525e6"
      },
      {
        "path": "schemas/attempt/v1/save-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "381c3b6346263ea07b0c7a4dfd276bac597ed55810ef4fe60d7219d4268814b8"
      },
      {
        "path": "schemas/claim-review-overlay/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f5a50b5895c71c7189b7875f405899df21b15df8316b4004f4055dfad8e56f63"
      },
      {
        "path": "schemas/claim-review-overlay/v1/overlay.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "70016794b90631e6869a175d813f0761461df8e41e9da642eab79f50d997b442"
      },
      {
        "path": "schemas/codex-app-engineering-goal/v1/goal-spec.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0d7e35ae9e63a9ab82bd724cd69da74ca59093170779c22d51b871af2cc7fc5b"
      },
      {
        "path": "schemas/due/v1/action-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "05427d658162162522db62e97c8b20806578ad747070fcc0ed11819d4bcd9ffb"
      },
      {
        "path": "schemas/exposure/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a7d257e6a7c05b8a1b15d2cc7cbcadde06e2e7f2d68c757cfaa685ddca26feec"
      },
      {
        "path": "schemas/exposure/v1/save-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "40f2fbd8249de80c2070b1acd6e2147f6e75d148323dc05568ad0c52382fec01"
      },
      {
        "path": "schemas/extraction/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b1c318b71d062841086be76c8de621ed2ee02062572b75247997f3d5c5870c4f"
      },
      {
        "path": "schemas/extraction/v1/definitions.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "affbd9a65c4f8120594f7483df0944a6244b258c85388fb78c6ea43e8b60a719"
      },
      {
        "path": "schemas/extraction/v1/input.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "69a3614c8bbf33e16ff60c6bdb55db7e7890fd1f17f58532f3b02b51ab8de773"
      },
      {
        "path": "schemas/extraction/v1/output.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e9b583ddc00bdd3af8368a63095bb8c484181eea5d7b57178f2f35f971f02623"
      },
      {
        "path": "schemas/formative-test-manifest/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0134f7c26faab0cdebf05b4437da5a606e845a57d1619cffaab399977a3e0cf9"
      },
      {
        "path": "schemas/formative-test-manifest/v1/manifest.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d9b541177a15e3b66ddaaff75ceacfdf32e36300fd9b88e3f4e55dc8631f5747"
      },
      {
        "path": "schemas/formative-test-manifest/v1/run-record.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d2c739d86023c8d9c09f6053311533bea6824144e25cc77bfff812db8e8ab6bf"
      },
      {
        "path": "schemas/graph-read-model/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c256695e05a79606d785a8965c1d0b1b9bc387bf099e03ee4d85e787e68a7831"
      },
      {
        "path": "schemas/graph-read-model/v1/graph-read-model.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7a3d2c1d814d1171a61c78bcddc963fdcaa467727b79519400207842b2b93866"
      },
      {
        "path": "schemas/graph-view-application/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "50361c9ebedaa642ac9a34e234d27d98ef3a6f45a8b4460157caf39f3b1f6214"
      },
      {
        "path": "schemas/graph-view-application/v1/application-result.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0503a495237f5b57f840574da194ba4ffbf77c3f3327197b20af73a2861e2022"
      },
      {
        "path": "schemas/graph-view/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7e325366bcc02946bce7698c9564c333de5d60905b34ac0b42efcf6f984a10c9"
      },
      {
        "path": "schemas/graph-view/v1/plan.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "19915be1b5fbb9c4591a00a16310bbf496c6f78319e49c3e57931bdd6b3ec264"
      },
      {
        "path": "schemas/graph-view/v1/query.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7bb366c8e669b468fbed1905a64bf65bb7b521f9b2596eae2216e4501e2d5380"
      },
      {
        "path": "schemas/guided-map/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "66cb9a662fdf6aac747bf7b55e03637784bd0609a6a484c14a139b718e151d73"
      },
      {
        "path": "schemas/guided-map/v1/guided-map-read-model.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "015983e3d9a0ac61cf349bd8b610111fb4b1ee81e6227166b7984411deb84eeb"
      },
      {
        "path": "schemas/guided-map/v1/guided-map-spec.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2c85ca9edc815d1870d8c4a39bda7cd0e0cfbe8e7938ce1f52e133d6705f6a4b"
      },
      {
        "path": "schemas/guided-review/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f01b27f43d69e992530c3e2cb912e85b9f8e59e31035f3fb729debe1d9e5f33f"
      },
      {
        "path": "schemas/guided-review/v1/record.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ea3954471860774ee3e256d2feb82a2cc64e4b7c77594188ba538cced4ca11f4"
      },
      {
        "path": "schemas/guided-review/v1/request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "46a0a1361f4aa763c5c949d1c8b99d5f76bd935fa1b25d0ca95d33b049754ce1"
      },
      {
        "path": "schemas/import-review/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9c7973c4b2695de3d5832f6f4bad04fb35bc55f207970a2174fae81226706f76"
      },
      {
        "path": "schemas/import-review/v1/preview.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "011f89de9926d1d6c652c5607934192b40e38f339b7e4859ee4ae001a31c0374"
      },
      {
        "path": "schemas/learning-note/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0b03d98460852381ce36416f82bbac14bca62604c512e0996288beb9ac47a1ff"
      },
      {
        "path": "schemas/learning-note/v1/learning-note.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "caa530f6098aae90b71d9e9ffe569a181dfb0f7683eb1247fbfa28129ff25270"
      },
      {
        "path": "schemas/learning-note/v1/save-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "419c5efcb454bacdae1cfa744fc25c6340910b67885d9672ef7d86a059822ec7"
      },
      {
        "path": "schemas/linking-phrase/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a4bdc5b04620675b9bb2393b297caeab1ecc333f749903d8020c07a76fddb639"
      },
      {
        "path": "schemas/linking-phrase/v1/candidate-set.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "269b1e8eb0a7964e7dbd54923542ff11bc56e95ea72d65c69eb671024456136c"
      },
      {
        "path": "schemas/linking-phrase/v1/context.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "843a7f38d9682b29524f33ccef6d177f3fa3a0beeae50934ec76e57549001198"
      },
      {
        "path": "schemas/linking-phrase/v1/decisions.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d10c8fdc3ddc5dd405767a2a354489cca12f3670daf75e21efe4bd610bf0afa2"
      },
      {
        "path": "schemas/linking-phrase/v1/response.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9aa3cea931c2e4617c09067d86c3e1fe63bbd00e43445b98a82e5a2f4008e398"
      },
      {
        "path": "schemas/linking-phrase/v1/reviewed-set.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "96abe0538d55eb2ea3fa7dbe55087294f960dc4b7c492200a005ba1f4d71c17e"
      },
      {
        "path": "schemas/product-goal/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "dfa46fa110fbccb5b8c3cf55a3f06eee863b9ae8149512afe6ec0c9a2458c811"
      },
      {
        "path": "schemas/product-goal/v1/backlog.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5b437359f86e465870c2b78bf30ac6ce5ae667c30f7a544fa483d0dd43eb0ac2"
      },
      {
        "path": "schemas/product-goal/v1/dispatch-envelope.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "237a0db45e5239b3c000dd1713713f867113ff72c8924770db8ed1e93747f362"
      },
      {
        "path": "schemas/product-goal/v1/github-authority-record.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "323c3d2d8c52d420f0583bb6e78d5587c44c92d8fddbe6a3b09fa4cbbc57bd00"
      },
      {
        "path": "schemas/product-goal/v1/goal-spec.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "627dac96f37460395a6b4af41f84d72090affc854b0b041428c1a9fe94b2667c"
      },
      {
        "path": "schemas/product-goal/v1/ledger-event.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "772e3e5c5f6ef8249a5634b853e9b375f580767f6208977960ec818e11236b53"
      },
      {
        "path": "schemas/product-goal/v1/runner-state.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e53e6f63768b482c727800cf950129f3def401cfea461295c4d6af2d8c8b1bb1"
      },
      {
        "path": "schemas/product-goal/v1/worker-result.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "132cc4f3df6d865e95da65b4ff7e4d3f28dde152256d900242a307c879f1b620"
      },
      {
        "path": "schemas/product-review/v1/review-result.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f0b977274a82b291bea0d0aa0b447d2425155cad413da035457ba516abe898b5"
      },
      {
        "path": "schemas/reader/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "346a68127b4986e3382a83b8e7822bcb118eef4d0b4fc6a244bc383e103a9c28"
      },
      {
        "path": "schemas/reader/v1/application-result.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5f54cd34a166cb4cff3e4c402bb8dd29e02d493f8f996a7d93bb7ff01a4d095f"
      },
      {
        "path": "schemas/reader/v1/query.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e5214149de03c97a3f5ac7f0414b72aaf3118408e0abc92f7538814b13a89573"
      },
      {
        "path": "schemas/resume-context/v1/save-request.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "99e4070e5ec96c99cda9358d47bf00dd70fdf6794e3a5e767104c7596b0ae524"
      },
      {
        "path": "schemas/review-assessment/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f6e6a8b902db6bd2a885dd743bd5f6111828599f96388197be7ad44c394c612e"
      },
      {
        "path": "schemas/review-assessment/v1/response.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2b7ab54f64e727979f4079b35c478b722251a60e704d7d87ec5c1d758bebd9bd"
      },
      {
        "path": "schemas/reviewer-context/v1/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "37db44ee3fa8f7dd4937f0be929d132b339fce51824d8d91bd4d64123a0afe5f"
      },
      {
        "path": "schemas/reviewer-context/v1/reviewer-context.schema.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "51a1a303cc4f24586ea5e322ea5cf519b7d88884d0bee01b3679d0059b9e9e1c"
      },
      {
        "path": "scripts/claude_billing_preflight.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6a011d6824e39f6f8b315d391d58ead223ffa2b5a35fc151a02ef2804e3b181d"
      },
      {
        "path": "scripts/claude_review_ingestion.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a1709cf4ad84efd13879c0f5df58c73629428a7aa537fc760788c8c539c320b5"
      },
      {
        "path": "scripts/claude_reviewer_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3c37d9bbac047efe60cbd390936a3376c78dda4567d2c72a00ff9c944798eaec"
      },
      {
        "path": "scripts/codex_control.py",
        "kind": "file",
        "mode": "0o755",
        "sha256": "51cd3778c8c774bb3cdc5f2736b52b9ae89db694c27a618347acb9b171e76716"
      },
      {
        "path": "scripts/codex_jsonl_evidence.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e6eebee348f4be6b532d234566669b3f889134b7dd7499183f2b5c4a016ca844"
      },
      {
        "path": "scripts/codex_orchestrator.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2d33b815c3a84cda289f9b0322f9ee25e387383730bfef37883efec079a65c27"
      },
      {
        "path": "scripts/codex_preflight.sh",
        "kind": "file",
        "mode": "0o755",
        "sha256": "5d15fadc27d127e53aee3186ca8da0b8d571b59cf5b3cadb939b2ad0b8bff192"
      },
      {
        "path": "scripts/codex_verify.sh",
        "kind": "file",
        "mode": "0o755",
        "sha256": "4e10afe9543cf739d98ec1b07d94a3b1ec26dee3b33a1c560746f10ae9cc1c5d"
      },
      {
        "path": "scripts/collaboration_goal_dispatch.py",
        "kind": "file",
        "mode": "0o755",
        "sha256": "7196fada0a44911848a1bb35da54b3b1c87919acf28bb2468b46a75259bd03c6"
      },
      {
        "path": "scripts/collaboration_goal_entrypoint.py",
        "kind": "file",
        "mode": "0o755",
        "sha256": "7e4e4a1a5bc345ca905c965eb6ec0689bd1d91cc690a9420b32b523577daeb07"
      },
      {
        "path": "scripts/collaboration_goal_wakeup.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "516f32be38b75c8a555106a8f0f3594a451100748b2cc5bf00c6eb5cc77d3d04"
      },
      {
        "path": "scripts/cross_issue_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "04c2c05ffeb8725cf6c2592eb0a370ecf67714644d8037dd2bdb46f5297b7d35"
      },
      {
        "path": "scripts/epoch_scope_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "389887a60df9e443850505e4fc804d0b4aba1f0305d9f6e107ab01c9542a4249"
      },
      {
        "path": "scripts/external_review_control.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2b2e2de5b224c4575f7d17a905c0be82a6762ce0abf804f7a6de0d794971fc53"
      },
      {
        "path": "scripts/external_review_handoff.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e13e0290b3d04b55983070f628bb1b4fcb4ca6f0f7aee100c87e853b522dbe91"
      },
      {
        "path": "scripts/github_product_goal_control.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ce040bc0d10f0d2503f578eeddfd216783dfe0cfc65ca1f536d0eea90aba2c2d"
      },
      {
        "path": "scripts/github_product_review_consumer.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "339c3082c481731670c512c625156765fc10a450d11b5b5463e206f4224d5d0e"
      },
      {
        "path": "scripts/goal_continuity.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "471ccee9a12d5b02857c80d0bf556f2bfd1044c4dbab6a883034c76fe0db79e4"
      },
      {
        "path": "scripts/goal_notifications.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "82ba407ef804457e66127d1d48a9d1264dcabbd082a783829bb73118737b2af7"
      },
      {
        "path": "scripts/goal_runner_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "047e34766dd74e18937421756263a8bf0ae77a7d65ee0351c4217e71971fb96c"
      },
      {
        "path": "scripts/import_markdown.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "80a1f796c294b0edc1154fd258ba36501715666d801ad38a6c9f2b8d18506947"
      },
      {
        "path": "scripts/install_collaboration_goal_entrypoint.py",
        "kind": "file",
        "mode": "0o755",
        "sha256": "bdf6c023425217f5edcd74f007786a65cb9f80c289f995c37264b129d57c10a3"
      },
      {
        "path": "scripts/install_runner_python_runtime.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b43181017df11d45cf28c8ae579d27372a69ccbc7aa9a7074301e26fc68ab9f3"
      },
      {
        "path": "scripts/install_ubuntu_worker_runtime.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "23415ec60f91d96ca157025422e6650dd5dc45c55bfb9a35332f67057d358a39"
      },
      {
        "path": "scripts/issue47_engineering_wakeup.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "24c350a8fbd2476f27f9ed5cfd209eefef933a4ee3a508c604b6b80b5a0e003f"
      },
      {
        "path": "scripts/kgnote_alpha.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a07fa572f611cc7138a7e9a72d0fbb3a80f751fe7552cdbef55b66aecafda9c2"
      },
      {
        "path": "scripts/kgnote_obsidian_spike.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "73ad599262ebcf13837cde5ab7530c471e332bdb014fbcbed1586387f5251800"
      },
      {
        "path": "scripts/linux_landlock_exec.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e65b11443b66a511fe2f6bc0f663f6673aac694cd207e01b66fb4894a07fd843"
      },
      {
        "path": "scripts/linux_worker_bootstrap.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "531d7a85fe1aca3c5a8db13a97da5c9cd833286faaf591d363618779db97f35b"
      },
      {
        "path": "scripts/linux_worker_guard.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ca9b4a3a9da6b35dd68be4300eb929fcce23e47093932abd3a9f6d2495426760"
      },
      {
        "path": "scripts/linux_worker_router.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "03177bbb77097a1317b9c0c532a27f3b15d2f8f2f041f951a018103e9149b882"
      },
      {
        "path": "scripts/local_autonomy_runner.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e2158883cbe4a77a238b8df605d2df0ecff513288931d36757f9c28e4fcca6e8"
      },
      {
        "path": "scripts/o2_prepublication_control_tests.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7aa45b31fd6142c160eb53a14811c9a8f1887c4b15cc82864a610554335ad3bd"
      },
      {
        "path": "scripts/o2_successor_recovery.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "338a383aed30eb00bdd223d86c8336e2375739024b6247f4575d9b16d16eb9c6"
      },
      {
        "path": "scripts/prepare_h0.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e59f5bcee360ebb0efa8f9a5a632b1e004373ed7f2e65a19c13df36f7a514b2b"
      },
      {
        "path": "scripts/product_goal_runtime_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9a571ea7320bdb16df3a92f1c74e8e9b8e369f3cbb598918facf3b58c5e6f446"
      },
      {
        "path": "scripts/product_goal_worker_identity.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "05102fb872f85624ceb74d7368905658c17d9c20bc5b435b2ba3bdea836222b7"
      },
      {
        "path": "scripts/product_goal_worker_lane.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "313dc5b4b01fd934f4d8a6e1368295d0daf5f133f1792877503f072027f9ae99"
      },
      {
        "path": "scripts/product_goal_worker_result.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1e1367de33ef02897e3d636faff1c91de807a343aebf88b7098a899404334803"
      },
      {
        "path": "scripts/publish_external_candidate.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b2211bad915d43c71e09d273786bfab922c69b298eac47643471a0f06e161159"
      },
      {
        "path": "scripts/reconcile_o2_attempt_classification.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "678e8c4a49266f0d5cd37f80581115f61b4c669bcb19a2df6cee12992b1a01f4"
      },
      {
        "path": "scripts/replay_issue9_goal_history.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a8c836f9d1416244941a828d36ab23618f6bdf24992c02cb7c541265e23b05e1"
      },
      {
        "path": "scripts/run_product_goal_isolated_trial.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "53fc4d3cdc56b704bc1e1b3cf04c97bba748dba52c9b6eac73da7eb6e7e9c067"
      },
      {
        "path": "scripts/run_tests.sh",
        "kind": "file",
        "mode": "0o755",
        "sha256": "381c67821b7d88af39ae81cc11f8353964a2c83a77794265a7f44f312a6cc98b"
      },
      {
        "path": "scripts/serve_graph_view.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "92597d77d733363c300b78200815148db58e8b4e6c521ce19b6fac3a959dd9e3"
      },
      {
        "path": "scripts/successor_codex_entrypoint.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8ab958c255fc4f976b30c22fe338c0c0452fc086cb0a7ddc8ad808571ee5bcfa"
      },
      {
        "path": "scripts/trusted_candidate_publisher.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f307f808b2cab4bb4c505e78b86c23130aeb55cbc63e1ba4b0fe9a54ce1dd60f"
      },
      {
        "path": "src/kgnote/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8db430100d5efcd996973f456058c273ddec3783790ef1a97913661bc24bd37f"
      },
      {
        "path": "src/kgnote/contracts/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "06468217193100a3ee0821c5394e1d1cf4d34f979f4d2278866bfc22ca6d9087"
      },
      {
        "path": "src/kgnote/contracts/extraction.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "283c7e15f4c2a6da769cb4497de48122e979429206e658442d5703c85e542802"
      },
      {
        "path": "src/kgnote/contracts/graph_read_model.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "136160f247720fc4fa80985d094fe02c5c5ee4c31e4afd9d1244da7fc34d34c9"
      },
      {
        "path": "src/kgnote/contracts/guided_map.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "057291bdf4d422c0004275f468cd6f5997a4f5efd7d3040046ba3ecfde826b9f"
      },
      {
        "path": "src/kgnote/contracts/learning_note.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "90cd6fa8aefe5f7e7b4ca7d62751114bf32b6242b7b08ae2c3dd5a6f35dcc228"
      },
      {
        "path": "src/kgnote/contracts/linking_phrase.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f552997ce87c2084d17ec451b2c1d80cf4385c3d37c49475fb5f78f627b6b083"
      },
      {
        "path": "src/kgnote/contracts/reader.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "828810381e6e0a7035e3bb8161cdd7773ab62d888837e82817200268cb146a02"
      },
      {
        "path": "src/kgnote/experiments/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c6198fdf9ca21741aa2f50037585b362cc1d8cd19536e6b97d4ef28cdef4e4e9"
      },
      {
        "path": "src/kgnote/experiments/manifest.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "88a6bac94984a0c5068ad9e05ccbabce350c881c45cb211b826271adf1ed2803"
      },
      {
        "path": "src/kgnote/extraction/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "95d4d37641092039107345a7de35f494b8098f33d7ca3d278ac5a98949198ff4"
      },
      {
        "path": "src/kgnote/extraction/RUN_ADAPTER.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6bd4dbcf8c4dcbe059815475170433913cc9ac63331f4c33c25433efce5262d3"
      },
      {
        "path": "src/kgnote/extraction/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "81d6293ec2d42abd9366eb01a630a2c89a3f71a38dd08768753c14a8a7f0d3f0"
      },
      {
        "path": "src/kgnote/extraction/gemini_linking_phrase.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b4a838be926fc34f9ee5ca5e7f51417452c5606a23482ba393d2e4ed2e2bf257"
      },
      {
        "path": "src/kgnote/extraction/gemini_transport.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2c615dd3ce93dbd0416507f09b9b2cfd957233552e0ee9593a67256dcc49579a"
      },
      {
        "path": "src/kgnote/extraction/offline_response.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5c22716ac99e6ef4f394eba8db2304c8058acfe9c7ed546174693dd1a676ddb3"
      },
      {
        "path": "src/kgnote/extraction/run_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "30b5083ee031b7fb48d5451eceb35830d69c4f00b54530e664fa9b0c66be6ad0"
      },
      {
        "path": "src/kgnote/ingestion/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3a28ef9ce2eb20ff1d8450ed0e000cd3218032bbe99345c96960e5be798aa267"
      },
      {
        "path": "src/kgnote/ingestion/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b203e2a6e8f49b723ea0fdff5a2247a6b79eec126072d58dc0ae9d5b3737cd37"
      },
      {
        "path": "src/kgnote/ingestion/markdown_source.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f931be9c7962dedc6f6803893a44422950d1e2fbccd4efa0ce311c232bb8fca9"
      },
      {
        "path": "src/kgnote/learning/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f671f07311a94b54c7582f48a0fac139d1268ce5bfc2bc43f50788d40be6f0a0"
      },
      {
        "path": "src/kgnote/learning/catalog.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b8b5fac4e34e299af177734a030465da1f33b4bb2f6b9c1301f1cd7d890ff4f1"
      },
      {
        "path": "src/kgnote/learning/continuity.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9b3aef3238ee8b1b5205b2cf8553f4d0717396881e61ed8e713ba39be914b687"
      },
      {
        "path": "src/kgnote/learning/prior.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bb91ab2bd5a0bcc64fa6975f1d6a45fb6470e4a189916cf5193069acb5eea08b"
      },
      {
        "path": "src/kgnote/learning/source_library.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0381eaf6ea976365d36b099fc9c8dd00ae50605ea86a231ea3130f4f09072c21"
      },
      {
        "path": "src/kgnote/normalization/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b3a76e1fb054c632687b6bfc05e87bc835db4fa83981dfa0122c9c798c4e70cb"
      },
      {
        "path": "src/kgnote/normalization/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7f03bba16e503e36464a17c9782a3abfd972894f1fc8e5bff272ba268c733bc0"
      },
      {
        "path": "src/kgnote/normalization/normalize.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8578509c570a19abdadd69e1f43f130d13689957cc7e184822de107e6e5915e2"
      },
      {
        "path": "src/kgnote/notes/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c72af13755f08d93504c56fbac63a667c1b72586ee9d20b34db9b99bd89aeea0"
      },
      {
        "path": "src/kgnote/notes/store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "660c18eb75245234f26c4a09d6a29524c18ddcde39086ae293d9054f8724cab6"
      },
      {
        "path": "src/kgnote/obsidian_native/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d94070dc4ddeffcc137b7677e7b9d1bff318829eb73e67d54d3398514146e443"
      },
      {
        "path": "src/kgnote/obsidian_native/spike.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1e5720d05500b3432a63d3ea281ba10527d6e90f889e9b20c87d3e6d4bcdcd0e"
      },
      {
        "path": "src/kgnote/obsidian_native/validator.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8412a4923e9366d9b8984aaaa072f3d3855fa62d91691e850a60773ccf916786"
      },
      {
        "path": "src/kgnote/personal_alpha/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "441fd7ba1d18611414c6a79d89864896146dd2e955e195a7efb8582e3cf24028"
      },
      {
        "path": "src/kgnote/personal_alpha/learner_projection.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f8f4d230b4ad6f47c3ab0a4be2cd4c717e44c7f0224d65030263d3dc4baf2f56"
      },
      {
        "path": "src/kgnote/personal_alpha/preview.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a7b7f6421c6cd2e33b325c89c5c44266e1353fd13ff0177d2b2e441ed45687ec"
      },
      {
        "path": "src/kgnote/personal_alpha/workspace.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "385be38b478d3f7ba448b44596554bb3297f9d5aa7f925fa2e22287dc7b25694"
      },
      {
        "path": "src/kgnote/pipeline/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "80a185b4d94b1d6f33275615129bf6e08d93d7594315d1ef9395b338b430419f"
      },
      {
        "path": "src/kgnote/pipeline/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "db97ffeb2eb36c7cca5cecf91dbaff043a28a7478ee480c23863cf14c0760709"
      },
      {
        "path": "src/kgnote/pipeline/import_review.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fa54f7b8ac7f20f9ad9d0193a1f8ab96fd92e160e4596415ef230e5144b4881b"
      },
      {
        "path": "src/kgnote/pipeline/linking_phrase_review.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ba155f4e717ba39fd8469d831cb1605fbb9af222a9d53b9c94d07dd0521ec90c"
      },
      {
        "path": "src/kgnote/pipeline/linking_phrase_run.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "cdc4ad8ec533f6825ee2b2ce5644a6978153597304492dd2245dd843318812ab"
      },
      {
        "path": "src/kgnote/pipeline/live_import.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "42627a6be2f8843b6fe64c962b033987df4721a23a94cc0a6208de668d5d7c64"
      },
      {
        "path": "src/kgnote/pipeline/offline_import.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "63302d7f1fee65123b5b4ca10f615487fd81448c3a04912a0726dae68d5bd119"
      },
      {
        "path": "src/kgnote/planning/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ce2b34ba5c0341528766c6752cb87bb9d52939ebd2fe7e1ff81a13e4159edde4"
      },
      {
        "path": "src/kgnote/planning/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "86b2c7d89fb56a2832e412bf21355250cc7845919eac309e20871480207e933a"
      },
      {
        "path": "src/kgnote/planning/dry_run.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "331604e7b876eb62b37bd9688cc4991e44bc4fdc7e9d1b96cbe7a4a481829595"
      },
      {
        "path": "src/kgnote/reader/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "31d170028bf16102e7640bfd8776f070c4c01fad33db9d8a5cbe02977ecef5df"
      },
      {
        "path": "src/kgnote/reader/application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c59d98956d9948b3237eea72d9adb00d2506379ee220c06aace84c30aeec305b"
      },
      {
        "path": "src/kgnote/review/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9688e0da4cb63ab275df7e463dbbdf55732919cd99ae77dc2f9f9cc201c4a4af"
      },
      {
        "path": "src/kgnote/review/application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "502462e89942af532c4b3d320325d4db5879b08c915a96f599f94e381d82b432"
      },
      {
        "path": "src/kgnote/review/assessment.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "699d0b073f0ca9e4cc3200121cd62ae74a4a02921052daa6ed8566c5f0049137"
      },
      {
        "path": "src/kgnote/review/attempts.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "21cc59d3ed68bf4fed0099c9ae1da2e27b7308fa493f19e2302ad525db5486ad"
      },
      {
        "path": "src/kgnote/review/context.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1a338565710cbab3ee60775ff32b9497b51e6fcbbe2f351a2e9e952d29869f74"
      },
      {
        "path": "src/kgnote/review/exposure.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "30464f5a433b0e51d482bc4c907d9b84bfa4ab4bd1daddf5024570773bd1c8b1"
      },
      {
        "path": "src/kgnote/review/feedback.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0790ffebf7ccab9dc9c5d35de3bbc3f3bc6df1d34cea4e7a83a4638c4637e83a"
      },
      {
        "path": "src/kgnote/review/guided.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "262f3a4842d0ac5222cd57f20a35d659269890fb968d30ac29a714076754cf84"
      },
      {
        "path": "src/kgnote/review/practice.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6fbe85701bce7240709bb08b5265a7b67fbd70ff49e31dc5810b49bd395123fc"
      },
      {
        "path": "src/kgnote/review/scheduling.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c7301ee77ec11805940d8fe43427cd48c5b861a1a9719768eb308923a1e60db6"
      },
      {
        "path": "src/kgnote/review/store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "24f2744445f636e606d6e6ee4e8f60aaf724a19329cbfe755606b1bb01887797"
      },
      {
        "path": "src/kgnote/storage/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1906ef2811192585b0ee442be2c048cf929cfd82d41fa04344549d69c5068799"
      },
      {
        "path": "src/kgnote/storage/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "61ab036f871755455a02dd1c4ef3f810f90c408a9d7df52c3c22f6b112db61cc"
      },
      {
        "path": "src/kgnote/storage/canonical_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3ab3147528f925b3d92411d1d17984e615bd3e47768f7210bcb626db689e2d4e"
      },
      {
        "path": "src/kgnote/visualization/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "220de7f265cac4d660b808030aca72044f8f00775eaaf8976ec7006c0d39a9f2"
      },
      {
        "path": "src/kgnote/visualization/__init__.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2e3d070940d13666571b422cb5494a6c19e6aa60d669bbceba010d7fbbc71f14"
      },
      {
        "path": "src/kgnote/visualization/application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ae0d3415be3629f4490e84a859fb10e1ecf7f54f33a418df6063167b3d2f889e"
      },
      {
        "path": "src/kgnote/visualization/guided_map.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "73dfe2b76ccb41f01250c26895e3f7587ddaf4772f486cb54b8dcabf9fdcd7f8"
      },
      {
        "path": "src/kgnote/visualization/query_plan.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a09618e85bd86c5e2f9fe6be119676161d6153f695d71c3da5584c7a3f6e55a4"
      },
      {
        "path": "src/kgnote/visualization/read_model.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ffbc58f816d875eb388fc6d04b1bc8904bb2c64f8b3c2af20edb5ee204a5f959"
      },
      {
        "path": "tests/control_plane/runtime_admission_fixtures.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4cda460a4c7c0093f88b9b4050cb9891c035c3e93978385c3ca07a9ef1319263"
      },
      {
        "path": "tests/control_plane/test_claude_billing_preflight.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "732233dcf96302415deb227c5f703daa824fa7b567ec7919eabb7ed662c4e023"
      },
      {
        "path": "tests/control_plane/test_claude_review_ingestion.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9e303818f3223bf9d56e13d2e22b85a66a665d0218ea277291ad5c0bb9cd7c05"
      },
      {
        "path": "tests/control_plane/test_claude_reviewer_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "476f086c777bec7bf534913f9d2900869b01e914742b401984f73bce9ab1347c"
      },
      {
        "path": "tests/control_plane/test_claude_reviewer_e2e.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "40b98368254ec02f1fc40195c2c1d0163f8d51858e1b9ea7cc918f03ac354857"
      },
      {
        "path": "tests/control_plane/test_codex_control.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d469502c34235ea2400a7c6ecaabb334b640aa7558538c744a9cbde560da8cab"
      },
      {
        "path": "tests/control_plane/test_codex_orchestrator.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "76d83e610773218b743ed430947328176b385543dd7ead2188e2b3b83cd3e55c"
      },
      {
        "path": "tests/control_plane/test_collaboration_goal_dispatch.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ad188b48ba29bb036beff5e4cbb0a32925b2879edc00341fc319bd2e9de30364"
      },
      {
        "path": "tests/control_plane/test_collaboration_goal_entrypoint.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "42d9894a0e9c4abd84bba61791d685a733f588bb10c5296b9cb5df0ebeca24d2"
      },
      {
        "path": "tests/control_plane/test_collaboration_goal_wakeup.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c33e30a64832a14241ccd3794305adba22fd10eecf5632e431d42a94a57dd854"
      },
      {
        "path": "tests/control_plane/test_cross_issue_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e8ed71c8e7475e7ccee419427b1997eb6fb0c2d8b2ebe2487dcc42482d4126a1"
      },
      {
        "path": "tests/control_plane/test_epoch_scope_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4dbf0b925bd4e2f16fe09a7df90859119e2cd41d36c31fb7eed59102777dd7ea"
      },
      {
        "path": "tests/control_plane/test_exact_review_integration.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "57a78d633073dec85c9308f8dd2e89282ce773bf39d37421e06fcc8295cdfc08"
      },
      {
        "path": "tests/control_plane/test_external_review_control.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c1a571c2c64c8b4d2df3e59afcd41ad24e5f212eea7044c808c6e5fcb4e5b462"
      },
      {
        "path": "tests/control_plane/test_external_review_handoff.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "32b48fa86ca14ee823d557cf56a342b6feef8781bce6265678264aec3402585c"
      },
      {
        "path": "tests/control_plane/test_github_product_goal_control.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "51538c6857e798624bc432362864ff54c1c4ce992d2d0430b0bd894d833a7047"
      },
      {
        "path": "tests/control_plane/test_goal_continuity.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a2e6965418a00bd9fa57ee413af11baecded38d811b5884362ec476a49294df1"
      },
      {
        "path": "tests/control_plane/test_goal_notifications.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "80fa210163bfb0bc9ad10cb621b3c8516ba3581dee51c88f5ac848fcf2d5ab73"
      },
      {
        "path": "tests/control_plane/test_goal_runner_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fa02c4f7af5b91f42ceb1edaa7de269a808ec1b77310fcce25185ab6d518013f"
      },
      {
        "path": "tests/control_plane/test_issue47_engineering_goal_spec.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "33cb1eeec0eef6fbeaf9dfc41153fdcebaffeefa9f2412374fb87c302bea8268"
      },
      {
        "path": "tests/control_plane/test_issue47_engineering_wakeup.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "925748c6ec6e2498dd795c31f99c7cf861b1c31e58350c646000ddaf4782bc76"
      },
      {
        "path": "tests/control_plane/test_issue9_goal_history_replay.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0e6666ef9a87832f8fed3a8221351234d56790951b691e05431ca85eae0f15e6"
      },
      {
        "path": "tests/control_plane/test_linux_landlock_exec.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "207b33cff4de823f293050bd92eba854c6954917a920ce7a3b0c5d77158e2f53"
      },
      {
        "path": "tests/control_plane/test_linux_worker_bootstrap.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "90baea5fc7ee3929ddcf540012d204a466c30f2c2b2fddafc4569f5f17bc24c4"
      },
      {
        "path": "tests/control_plane/test_linux_worker_guard.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3e2101888a48f0a8e2701a5029e7e01e6a4a6a200fc41f36fbd73e273e73acc7"
      },
      {
        "path": "tests/control_plane/test_linux_worker_routing.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "694daa3924fe00ef2b649a1bb8f965be6293b1ea04576d278f004812ce781b65"
      },
      {
        "path": "tests/control_plane/test_local_autonomy_runner.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2056b7638cdb4b7c91a5afd809bba0bb7287cd2cdf84089185bb848185cfd09d"
      },
      {
        "path": "tests/control_plane/test_o2_classification_reconciliation.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "711f73758838af14526ed0a84da59452ed45e12aeace28c2b35e41e308001026"
      },
      {
        "path": "tests/control_plane/test_o2_successor_recovery.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d0589f801728048687e1027088f38df3d4ce950bd0f912c756fe8502a59f8fbe"
      },
      {
        "path": "tests/control_plane/test_o2_v4_day0_readiness.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "81fe00b476b89826c8d163de8cf63eeeeb2e53ce44fda800d68573c69b02619d"
      },
      {
        "path": "tests/control_plane/test_product_goal_backlog.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7f8221f752d7ab5efa9d34cd78926a2bdc7806b19bf5bfecb653f440f3903ef7"
      },
      {
        "path": "tests/control_plane/test_product_goal_dynamic_order.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "15ed5fa1a10043efe545b8ba0cf290a63cda4c434b46c3494baf70894cf6519a"
      },
      {
        "path": "tests/control_plane/test_product_goal_isolated_trial.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "476156018c83f2748e432089d05231016ede21c147e3930fcd9058834d6be839"
      },
      {
        "path": "tests/control_plane/test_product_goal_runtime_admission.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7a5b9d459c882ab7117e46de810444944e3f7bb9ce7be1425241f396768ef529"
      },
      {
        "path": "tests/control_plane/test_product_goal_runtime_wiring.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c96ab2d60a77030621c25e7052a18e58058915adcd4beb43fafdd09bffd7de56"
      },
      {
        "path": "tests/control_plane/test_product_goal_worker_lane.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9aeb00335567e067d84e51344863fe9794b5dbef6d550a762390c94b99d2f12c"
      },
      {
        "path": "tests/control_plane/test_product_goal_worker_result.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b01b85a1db37894d80b4b89b7afc84c491de01777ea3caaa0445dbb19844ab09"
      },
      {
        "path": "tests/control_plane/test_product_review_consumer_schema.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4704331a30a87cd3d682f027efdd02880921c64440b659cea16ca58a3a4ea63f"
      },
      {
        "path": "tests/control_plane/test_publication_receipt_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c50eeb806883609be921f2a0652e71605909570aed8e2fe31a14d4aef39dbd9b"
      },
      {
        "path": "tests/control_plane/test_publish_external_candidate.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "24c604d32a82bb69096eff30133118cbc9ad3aa831b255b9d7d6de9375b33746"
      },
      {
        "path": "tests/control_plane/test_review_completion_gate.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1b045c971e0a47901c72fb2e8fe485bddac46715a9003032c6e9f20a4ba92e57"
      },
      {
        "path": "tests/control_plane/test_runner_python_runtime.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a891896d84852ec837846defdb1a8de8a66a39dfc20ca059df1bcc20badfad7d"
      },
      {
        "path": "tests/control_plane/test_successor_candidate_identity.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e161b0c7fdf2210f466a1a124d3cbfa842ddaaaf8687ec76495370850c10fa28"
      },
      {
        "path": "tests/control_plane/test_successor_codex_entrypoint.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "71c7ab282292a86700c929307ab151c3bb7ab0e409458852246fb7c3ef5b36e1"
      },
      {
        "path": "tests/control_plane/test_trusted_candidate_publisher.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "16502383c64ad8cea07ddb3093ad0154d9e948df7dea6ff70e07b5e164e96d78"
      },
      {
        "path": "tests/control_plane/test_ubuntu_worker_runtime.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3467b3a0b9d23680d40a5650df86331ed827c60a58f47256f2b85e09676c6275"
      },
      {
        "path": "tests/fixtures/control_plane/issue9_pr29_goal_history.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bef716bb1247eced235a7aca8c2f4091f5a46cbebe906765aeae6cb6961142a4"
      },
      {
        "path": "tests/fixtures/control_plane/product_goal_isolated_trial_spec.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "daafc56819c567640e1217d7bcce31a6509651e60250971f1f17bcb7f749b814"
      },
      {
        "path": "tests/fixtures/extraction-run/v1/golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3a0c419bab3c1956ea336f8f4b80068ec8b30b9d2ccff3ebeee462dd16fa730f"
      },
      {
        "path": "tests/fixtures/extraction/v1/invalid/cases.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0bde4ff1181d8d0ff1acffeaef6ba09ada17171d4ab4f9f680f282fdc5b632b7"
      },
      {
        "path": "tests/fixtures/extraction/v1/valid/input.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "39d74c3c701237d5b79d1434e4a0fd191cb571af164581b1d5fe6096ed5677b8"
      },
      {
        "path": "tests/fixtures/extraction/v1/valid/output.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "808884b50eea05361ca6adf26a9cf223bd35ad14c51801a21032d5af39b0345e"
      },
      {
        "path": "tests/fixtures/extraction/v1/valid/raw_response.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a1edb23d8644a9365d86ba7e4c2e4fed9fa7658ce884bab936bb7fe3959a1162"
      },
      {
        "path": "tests/fixtures/graph-read-model/v1/valid.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "79e23cd5f93c486cc78e76906331ea4eb91df24544f1f0a7e5e9abaa3072af07"
      },
      {
        "path": "tests/fixtures/graph-view/v1/plan.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f1dbc75adfa8d7503bb0d9c68b0d100f4e4ebd12a7f2e8f035d7c7494c5c59bf"
      },
      {
        "path": "tests/fixtures/graph-view/v1/query.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2755a810d3d79d1ec76aea6b4c0d5ee6ec53c4e84fd106be4cddbf10e16e5eb9"
      },
      {
        "path": "tests/fixtures/guided-map/v1/bitepacer-golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a1055d5d6108079a93dde02fe82a9f6c7b826a05b38af3f441d0e8258970ef5e"
      },
      {
        "path": "tests/fixtures/guided-map/v1/bitepacer-graph.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fdd421d8bc460ee3280bfa1e57369079571758d81db42876a4997a79dfbfbc78"
      },
      {
        "path": "tests/fixtures/guided-map/v1/bitepacer-spec.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c43e804d6b79ce9ccf27abace72744973519b03fd1ea973fa90036f4f45f2b92"
      },
      {
        "path": "tests/fixtures/learning-note/v1/invalid/cases.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a15763a332ef9630d0e960739ffe499325a52030f9e65d71e888076dfea8cbb5"
      },
      {
        "path": "tests/fixtures/learning-note/v1/valid/note.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ae5c5a888050d631382054f2f0e728ef13ef797983c30b47233420a224a0cddd"
      },
      {
        "path": "tests/fixtures/normalization/v1/golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "77af1e501ca79e6237d6943bf9e7d9d5d4424815d9eae3b043caca6d309d443c"
      },
      {
        "path": "tests/fixtures/personal-alpha/glossary/harmony-glossary.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ac6b860620e30b763ac57b1f7123e108a94628d24c7ae5f4f3c47d08e453c602"
      },
      {
        "path": "tests/fixtures/personal-alpha/golden/network-path-port.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "64e0a9f67e612160d3f31b1c57892e13d67874f50726ee8923d1b1066ff5be5c"
      },
      {
        "path": "tests/fixtures/personal-alpha/golden/network-path-relationships.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f65163b63224f82173bce743f60a209f55a4dd1358a48b97848775fddcf33ae3"
      },
      {
        "path": "tests/fixtures/personal-alpha/golden/network-path-start-here.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2621adf7a3dea0a52b2f1dde08a524a8f02d0ffe9624541d46670ddf58763f85"
      },
      {
        "path": "tests/fixtures/personal-alpha/hierarchical/network-path.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2df7ea0ff998afb4afe369b38d5a3b5830e8f24397091a083e5cf15364078e2a"
      },
      {
        "path": "tests/fixtures/personal-alpha/procedural/seed-starting.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0c8896a0638b1dfcdb2d488dfc86ff3663a6cc3156c066948bd818ac3d5d9ece"
      },
      {
        "path": "tests/fixtures/planning/v1/golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2b765a4a4ad849dd48c9da6ceab6df4a902f7e56bd739672509098ffab39a3ab"
      },
      {
        "path": "tests/fixtures/reader/v1/bitepacer-golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a36e664aed91c19e052d61bc49a3569005a75229cf058811f3d80765bef67bac"
      },
      {
        "path": "tests/fixtures/reader/v1/bitepacer-query.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e65702307ea6bd59ffc62eed0b2a953eb76ebfaa01516e84fbc0cfd2222ebdbe"
      },
      {
        "path": "tests/fixtures/reader/v1/store/concepts/concept_ac75ffef5130f55c93c86161757813ed3ad92aadf3dd5344d742737031de97e2.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "47ed981c99d19046e463716499bfcd8054ddd0b3ec536f5e14e3f5eb00680b9d"
      },
      {
        "path": "tests/fixtures/reader/v1/store/concepts/concept_d18b2812af2ceef6d4d683eb766686b01b608336e89cc608b30c687218d858cf.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "df1221b59de714c4b41cb02d685d8868869c221598f13b6f7200f1b6e75b76cf"
      },
      {
        "path": "tests/fixtures/reader/v1/store/edges/edge_80042c4f448d92b2d8311f064b6189e7259615ff1c0babd38bb817adcf561c4a.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "42e2135362d4d2ccf49a8030bafec606ed1ab9169e0c75cb1005b5683fef8b84"
      },
      {
        "path": "tests/fixtures/reader/v1/store/evidence/evidence_3a0f087ea18e82057fe8900359d67ca3b527f7c1d260e05859b7cb0bfbfb97ce.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4dcc64bef0f012ebd0d5815fd83bf2ecb69876b36c5e19203f0982fc1a26f01f"
      },
      {
        "path": "tests/fixtures/reader/v1/store/evidence/evidence_b1861d12c500f976ca0364f6ec0ac869851ab741a5cc2110cd5714c39d4f3bed.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "af2c68c6e765174421dcec09061567a182d5a1a0a6e26b6531be8236ec0cfd5e"
      },
      {
        "path": "tests/fixtures/reader/v1/store/learning-events/event_ca11d93239de15e6357b7fe8a5b5b5c9f7704940f919ea32a3ec7e163d48f9e7.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d256f2daedbe0826953cf551f8362b5d2966494fb3969868ed26abed42f4ffac"
      },
      {
        "path": "tests/fixtures/reader/v1/store/raw/bitepacer-mini-network-lesson.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bbef6549c2381ee729c355b69151777bbdbda459ca16079055316f52318792db"
      },
      {
        "path": "tests/fixtures/reader/v1/store/sources/src_bitepacer_mini_network_lesson.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6cbebbe7a743f80cea777aef539afddbc9d3cfff14f79aaec34f3b25c7ffd3e1"
      },
      {
        "path": "tests/fixtures/storage/v1/golden.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "317b7e609b0d79872d3f85c7dfac438af4521554499297938233bd9fc8a1c51c"
      },
      {
        "path": "tests/test_attempt_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3efc5e56c6a87d6402ff66b25f5fcd0eca850819d2320dcfa01c990914c6231d"
      },
      {
        "path": "tests/test_canonical_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a34ee35f0d466c504383af4d451a718d92428162bc2ad65c45acf3ec32f7ba25"
      },
      {
        "path": "tests/test_dry_run_planning.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d36209fc4c81a2704d1f655421cfda9af72f4857edc5fc4907d89fd5d4534678"
      },
      {
        "path": "tests/test_durability_scale.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3fe3fecd38342e930c04b25009320987458c38081d66b39c50ed108a37d31482"
      },
      {
        "path": "tests/test_exposure_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "afa767b3dc5f60fc878d4bdf66a5bfd2a871cacea6edc81f7b3a7b4bfedfcf21"
      },
      {
        "path": "tests/test_extraction_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8516ef8d9213dadcd7ec2642a488a59a7eda3e26128a9365a38cb70d9532fa25"
      },
      {
        "path": "tests/test_extraction_run_adapter.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "522244d6f179681b8eb4203a7dd04deffb3860507d657fad2b48f6a56701667e"
      },
      {
        "path": "tests/test_feedback_scheduling.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "931fedf5a98c1e78cdd3e14bfccf582d1f2ef1a6a3e1fd0304c9748335bc8a53"
      },
      {
        "path": "tests/test_formative_manifest.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "76f830a651594000cc18ae66adc78bbaadc92a99f4880da3aa0ef72c4242d930"
      },
      {
        "path": "tests/test_gemini_transport.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9db2b159a88479983b6fd6ae77fa294a122f044122378db46e1541b43b9b5e99"
      },
      {
        "path": "tests/test_github_product_review_consumer.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "43f1a7763ba224fd98e40c0daa556c916adb4cde9d6b67cb2e67929b0373ec18"
      },
      {
        "path": "tests/test_graph_read_model_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "98fd528bf0229658fcff28e61a50165bdfc0ac0535ec199ed8e71f4e26e08db7"
      },
      {
        "path": "tests/test_graph_read_model_projector.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c3f6fe895148bfaccdbc0742cece42bc6d3212b476c1e83f0cc09bfd2acd10e4"
      },
      {
        "path": "tests/test_graph_view_application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a77bc2d44618e6254e871bcd379479908b87fbebe8abd93ce137ab1fe43f7ddc"
      },
      {
        "path": "tests/test_graph_view_planning.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "00a6b972133149d84d2febbca46bb5bebb507f058b2f0bfbbcf379ecbe88c3d4"
      },
      {
        "path": "tests/test_graph_view_server.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e77e09da050c86807d51360afff8461ee45311c4133e6ecb1a90080b6ee58f41"
      },
      {
        "path": "tests/test_guided_map_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "67a9fa5d460da5a6bf78da520909a46901ab1246c147e1466e2037ec3bce96aa"
      },
      {
        "path": "tests/test_guided_map_projector.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "346aa08860975fe53d894f24b318272cd047379451ae86f3b4842bb61993bba6"
      },
      {
        "path": "tests/test_guided_review_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e31db43e9b7b8d16db2923c3e5dd091f31d50695b000796111640af5a46e0651"
      },
      {
        "path": "tests/test_import_markdown_cli.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "eb8aae63a5c23687ca7c5b25871ef2423805d71b43993b3d752ae9382931d0ff"
      },
      {
        "path": "tests/test_import_review_preview.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a369bb8ee749de2418747d0d88b7de8a3b23513c46c27e23f403615d542239d2"
      },
      {
        "path": "tests/test_learning_catalog.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "36a58ee29ce6aaf51bb9a36258dca694d402a82bfcced12ca3f20901638c4985"
      },
      {
        "path": "tests/test_learning_http.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "21e92463dd4f7d7c5c7dd279acf3ebe1a53934c377a6603c50ecab321ffbd5ca"
      },
      {
        "path": "tests/test_learning_note_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c135fbb905b9e3fec1889d83fa6eb616b2d2ef03fc4bd0e7a695bba0bd1b954b"
      },
      {
        "path": "tests/test_learning_note_http.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0c02ed943c7dd31fa0f656a7a3848d838e0519d8422e3c0249761ea14c615a69"
      },
      {
        "path": "tests/test_learning_note_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "540d18b226ca1d360d8bfa0f1576dd0ed69a1531f71adab7c651e88ded2f9308"
      },
      {
        "path": "tests/test_linking_phrase_candidate_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ed0e3f06c9bc23cc245e3010ca69256757ff1de8df896a3a8738414aa1694a10"
      },
      {
        "path": "tests/test_live_import_pipeline.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9fd01ad8b36b2a167bc630aeee126faff54e53afa00701ade14a2efccccf1297"
      },
      {
        "path": "tests/test_markdown_source_importer.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "79fe8539e61935e903af077e9fd146c59c154862875f4407d67c5d7b7570dd07"
      },
      {
        "path": "tests/test_normalization.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0c61d30c96f47cbb8c90663f08ceb7ce63a96edd2a79887b242fe9d40265cdd7"
      },
      {
        "path": "tests/test_obsidian_native_spike.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "db6b042b5e554f20c66a040c595d8293ac78d6cd0811cd4f3fcefac7f284cbf6"
      },
      {
        "path": "tests/test_offline_extraction_response.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "54b8abb53e15aa8e8d2dc9b7a339c3060b853a0edc79537856ccd466c9124745"
      },
      {
        "path": "tests/test_offline_import_pipeline.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7b9a7218a2f302ec311fb4466f740e069fef10af3cec621bb97cac94de491907"
      },
      {
        "path": "tests/test_personal_alpha_analysis.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "098d30cdab90280812130bbebb8f8c8adcc401d95c87ff0907f97a0d2c138d1c"
      },
      {
        "path": "tests/test_personal_alpha_cli.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "750092a5aa453aa8fe0e4b0134a26c209a2efe68d35d8007079ed1ae46a9cafa"
      },
      {
        "path": "tests/test_personal_alpha_presentation.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "34e36cd004ab6894117a597dee3dd693fae9858f9fb71087e8f1f0a04c9bf91b"
      },
      {
        "path": "tests/test_personal_alpha_workspace.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b6557dd914a844260c0b625350fb4ba346f92ecd67f477fcb8181738d10a7b78"
      },
      {
        "path": "tests/test_practice_http.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f08dd5a7fc2e2fbb9743613836e1582e146439fef59617bf5bc53076fecd99f4"
      },
      {
        "path": "tests/test_practice_planner.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "52a4d3bde8124be4b6c531a302fd160dc9dd270c392db1c7821662dd625b40fd"
      },
      {
        "path": "tests/test_prior_encounters.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4a1f51e1b851fcb8fd971fd030a70d9cbf3dad46d47f12128dbf6657143eb592"
      },
      {
        "path": "tests/test_reader_application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4d802e963a10fd7b533beaca5efe73d4bd351935bf0b858b1cdf6e00a7d8db9a"
      },
      {
        "path": "tests/test_reader_contract.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "04687f66c19e7b0fb2bef5c5438e5496f1b59b507e5fa7f215e8cdf3e21466d2"
      },
      {
        "path": "tests/test_resume_context.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "63baa8672ff9098b0f18065b78b06b6254f5ae8fa9dc1d94fd41d41bed078efd"
      },
      {
        "path": "tests/test_review_assessment.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e1c1db9ccadd42985f651e34a6ebf4e0f2f422b0fc241efde0c331e35d8b583d"
      },
      {
        "path": "tests/test_review_store.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "0a6bdbbd7c586d22a856ec1acfab05e418865a385019b6a456d045a4b26cb197"
      },
      {
        "path": "tests/test_reviewer_context.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "79861e7bea693f67846e00396ec89a382bfc24fa1d2f31cb09d45e1059abcb89"
      },
      {
        "path": "tests/test_reviewer_context_application.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ad01973b7a2ab268078a48f62e689b812993cdbac10a03560387f56cca9c5631"
      },
      {
        "path": "tests/test_source_library.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a3c24409ac2ca59fc8013f5a20afbbe9ac4bdc81169253d00204327b4eb8a3d9"
      },
      {
        "path": "tests/test_source_library_http.py",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c8235d2f2cda5b7a744e8214bd645111584cf21919d316cc228dd2576e4d0867"
      },
      {
        "path": "web/README.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8116477f4bc0a173f139b6750f967d9f15a860ffa5c99733df9a29b0b9dff591"
      },
      {
        "path": "web/SECURITY.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b9db4d86873c73518e715828c234db85bc4823f60f4f236eb5e540d0df86647b"
      },
      {
        "path": "web/VISUAL_QA.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1b134f6ab17d88bc7ef20e914a93e6d431b6e49280ef2886be79e90db7b7394c"
      },
      {
        "path": "web/app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "071839d78444a4643be8beb73186328fbf01dfdc4f05eac995b5550c0db71125"
      },
      {
        "path": "web/filters.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "66eeff3f3b7e982389399042d6e521584e604a03a7a3ff7b8d837e3042cdfd0b"
      },
      {
        "path": "web/fixtures/bitepacer-claim-review-overlay.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "26158cff783340e26d1b4c6f51767fe32aadbeaf1a586b1270050e5f3dea9d82"
      },
      {
        "path": "web/fixtures/bitepacer-graph.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "fdd421d8bc460ee3280bfa1e57369079571758d81db42876a4997a79dfbfbc78"
      },
      {
        "path": "web/fixtures/bitepacer-guided-map.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a1055d5d6108079a93dde02fe82a9f6c7b826a05b38af3f441d0e8258970ef5e"
      },
      {
        "path": "web/fixtures/bitepacer-learning-structure.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "04d4fed19587a780e6f4d4c3a1d42b2514f8e823077536c2ad64e47894b32b9b"
      },
      {
        "path": "web/fixtures/bitepacer-mini-network-lesson.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bbef6549c2381ee729c355b69151777bbdbda459ca16079055316f52318792db"
      },
      {
        "path": "web/fixtures/bitepacer-practice-supplement.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "44b86c181446e5fbfba789b3ca0326c7f0feb2841fb2eee8a1d0d9ea8a3ff485"
      },
      {
        "path": "web/fixtures/bitepacer-reading-assist.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "818353f2b9cefbcb2d91c491b2505e3599870743716315bb60c5958e93aebcd4"
      },
      {
        "path": "web/fixtures/bitepacer-soak.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ad29875ea3d23c449b4bffe6968376703bbce2cb8e4f95c58192e0e95492c974"
      },
      {
        "path": "web/fixtures/learning-units.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c9394108ba3ee0ff8a7d0eaada68938066e89bc7b17589b8847c1275d9b05272"
      },
      {
        "path": "web/fixtures/os-learning-structure.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ddcbb2f1cf8a6ea7ad80f5b6745b0ce264172b26c844853ea418a9c515bf2744"
      },
      {
        "path": "web/fixtures/os-overview-claim-review-overlay.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a9ee7cedac06c83b13fdc98bee36b781989591f4effd69e0ca72cbf3d054e089"
      },
      {
        "path": "web/fixtures/os-overview-guided-map.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "81b0945c1f8a36de869201628246de3173c54d98c79bab42aefdd36bb9f32044"
      },
      {
        "path": "web/fixtures/os-overview-review.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "528da29db32b9dd7f767c947da76fca13c1f5dca8ac77758ea62859cab5fe72e"
      },
      {
        "path": "web/fixtures/os-practice-supplement.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a2cf5472056abeff506074a9c99ce4b87017dbb14ceb57ea65333fb4341b9fb3"
      },
      {
        "path": "web/fixtures/os-reading-assist.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ce0e6f021db058f1c526b11e7ce0b69be5389eb59a48f66505b12ebe11e8e5a4"
      },
      {
        "path": "web/fixtures/os-soak.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2caf548f652b17e5b82698f632b5bb9bb5e5472b0805e67ccab21003ac51e0e0"
      },
      {
        "path": "web/fixtures/phase0-graph-view.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "43f008a1d3a0bbae88933c9b1da26250a29fc7b65065250cfac56b9b1c34b040"
      },
      {
        "path": "web/fixtures/pvz-claim-review-overlay.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e30276ce201c2acc09573431c81912a20c5432d4b98cb7f1e9700144023354c3"
      },
      {
        "path": "web/fixtures/pvz-easter-eggs-excerpt.md",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5c076b49b0dc19bf51ab69eb0d5140ce68a3919e034c577d99a3a1559fd6d57f"
      },
      {
        "path": "web/fixtures/pvz-guided-map.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "9df7ed2a9ce0af9b22ae31ce0ae40bee38ab57049ca8ba3c8a9853baa146d44e"
      },
      {
        "path": "web/fixtures/pvz-learning-structure.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "576074e47aa0501457c9d8ffbe0a712713ce383711570aad9df9be0845b31649"
      },
      {
        "path": "web/fixtures/pvz-practice-supplement.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "266c8fa48eeda6bbed69c065511d42910cb3c0abfdb9c1146113ce20ddc3f300"
      },
      {
        "path": "web/fixtures/pvz-reading-assist.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "604fe0ce724f9016d9fb86632f455f8d7467011bef78c5b9aa963ec6b5f89cc4"
      },
      {
        "path": "web/fixtures/pvz-soak.json",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2ec17cdf7ac13531d1280c93cce34350a338c0e3bf90fb1a6f86ed7059604808"
      },
      {
        "path": "web/graph.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "3da08ae41f555b910da0e3b0acacf8df0b8b7074948fb365aa5974257d28be90"
      },
      {
        "path": "web/guided-map-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c421a3a0dcce77ec4ea6c80e4fde86fe4ae647a920b0819666de3e863530dfe8"
      },
      {
        "path": "web/guided-map.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "309ff4fbc12a583411c9555e2f116b269541dc2e53893bbe39112bfeaed658ea"
      },
      {
        "path": "web/guided-map.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7813497f6db8f0d708d7a1b3908964cf64c38b46b9facc1643867d6c6696924f"
      },
      {
        "path": "web/home-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "6f9e5f2d6f791b3736f0436cd01719d1aab70de7c77b518cf2b8f6dd5ea2d49a"
      },
      {
        "path": "web/home.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "74099a3c64083b21f6788e09b99a3003afd2e5c373abaad2719534f09b2cb868"
      },
      {
        "path": "web/import-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8e32b8f054ed002c55af632da91568f90d27c628187b84ed00685fa50a7df9b0"
      },
      {
        "path": "web/import.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "43b28499a29dbbd717e65c794f8fb4b58a191cdb147c719992f5361527a26e52"
      },
      {
        "path": "web/index.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a02ac839bb1fa245419380507bfe85d3b85964e8ee0951571c38489a269a21e9"
      },
      {
        "path": "web/learn-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "667da321e83beb205fea6263be4e1ad7646d8cb0f3567b1f79afaef5409ce48a"
      },
      {
        "path": "web/learn-workspace.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2f637acb20365a8358336850c7fe9607549c603c8edd99a64a80abe1d52d99e7"
      },
      {
        "path": "web/learn.css",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a002d198d8bdc04521ae784c1aef75b1b4fbad3ac1eb71dd3dfddd55874b7521"
      },
      {
        "path": "web/learn.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8fc6b37481b9fcd4d4b25df855dadfa713ea3156e0d0f8d29fad6859ff9b3517"
      },
      {
        "path": "web/learning-note.css",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1c6365b8a3ad116e33b329a069c3d35d3d778b15a99289cdab68e3a392df0e32"
      },
      {
        "path": "web/learning-note.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "035759766fbadc3682c0a9b5914c4587ba86be541dba360b3ffb3e61318d6468"
      },
      {
        "path": "web/learning-note.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a8fc51f1c1d99fa97b9200cfd15be7eb25fc1f7e60147d66797b659b51b417fb"
      },
      {
        "path": "web/learning-workspace.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "492f3e56fc80d15314bca23417c07cd4aa8c9ed798e672faee01dd63fc724c03"
      },
      {
        "path": "web/library-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "e29b5fc23d33f67a8ac0b4eb3618c4ae190555dc1c967e45c14c418cc08f8bd2"
      },
      {
        "path": "web/library.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "55f057eb0619da38b43a04b091636afef0b90901bfb5fdfd3d6f7c2076d63bda"
      },
      {
        "path": "web/panel.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "68cc0bf6fc9775b627bb15196d6d4a5023ca165e03040584e4a8b95e1f55689d"
      },
      {
        "path": "web/practice-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c025fe3074f215ab36f6e4e5ae093e94ff524ce89189ae5bd0d5cf49ca20a15a"
      },
      {
        "path": "web/practice-workspace.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "b7d2c45cdc41e4d69978d36e1e4f056e9ab665940c4aa6418caf473a8a3b32f1"
      },
      {
        "path": "web/practice.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "da479a5a0ed53201811c1c2cda08b035217697a57a55ce6eec51f895eff818d4"
      },
      {
        "path": "web/review-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "5be2aaad7af27b7a427e69a798e8eb56743d0705cca9efe93d112554edf7c9a5"
      },
      {
        "path": "web/review.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "232724c5939909b04a93524edf67b4495d7856463cb160ec2b3e683bcd6a9092"
      },
      {
        "path": "web/soak-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "91d3dc21336749ed8f3d31f53293e9bc875c62a64cc511ae32d6024670d0320f"
      },
      {
        "path": "web/soak-workspace.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "1647fc99cc6ebf08a7fdc652aa80cf910c696fd3381c088b00d43b49b3987791"
      },
      {
        "path": "web/soak.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "7e80ada98b04d7cf925b2d4631db3b573ec0c25e1bba4cacb53fcd6d7235909e"
      },
      {
        "path": "web/source-app.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "cfb88d2a973e91baf50568b0cebaebb6ea398e134d7e2ef7be3daf828a837b31"
      },
      {
        "path": "web/source-library-ui.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "8c8631ed25db4baa28ad14c97ae9103bc2ecf4554e85ecb514c7f0dc899aa765"
      },
      {
        "path": "web/source-reader.css",
        "kind": "file",
        "mode": "0o644",
        "sha256": "a2a6c7322a74a50da8989f4888a81a795b38a44c15e115c150d14146ff5820a2"
      },
      {
        "path": "web/source-reader.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2496252231ed8718b77de8db048677b6a731c56e1ea47108eb35df79ddafe9ce"
      },
      {
        "path": "web/source-reader.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "d165744db38676ebf9ba84b30a7ef6e62f4c35e399d04c90b3ffce25a478039a"
      },
      {
        "path": "web/source.html",
        "kind": "file",
        "mode": "0o644",
        "sha256": "c661c084cc1921283e39ac8064d8f5f66f68bf31e50b3e71e78fa69703eef6ea"
      },
      {
        "path": "web/styles.css",
        "kind": "file",
        "mode": "0o644",
        "sha256": "765131521adea61777da861342294be26749474d93f083676e14211f022fd215"
      },
      {
        "path": "web/tests/continuity.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "dc6b40906e86b2e8d92afd740e891ef26a1fa5874e9b4b548e95c073b518bea9"
      },
      {
        "path": "web/tests/filters.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4ce882fab7447f2c3ad62c3105d5c186e9b068a9271c9ed38d3d8bb9fee61201"
      },
      {
        "path": "web/tests/graph.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "17f777b1bf3b888c9dafc556990b72b0f46e05a52de45c1c5fafc4d8897c71f9"
      },
      {
        "path": "web/tests/guided-map.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "ebd7443d7964c0c8f69d8449b57e28fdd35fd2b04148cf37466987d648e101f7"
      },
      {
        "path": "web/tests/learn-workspace.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "35ffef15e6f5d15049bbbb05114c9e06b25ed974db15e63e61100c53baecb1cc"
      },
      {
        "path": "web/tests/learning-note.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "bc51ecd646f88a937853f14177957eb71e185de51573045ab3832dcaa8f88072"
      },
      {
        "path": "web/tests/os-workspace.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f96b09cfac691f265f00afd9f4e3360c8f6e057f249da7db054d032ae89e93b5"
      },
      {
        "path": "web/tests/panel.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "69f9c94ee3ebb12ef9a8c7b16bca6eea84edf92a30c4106dd437764db89dc339"
      },
      {
        "path": "web/tests/practice-workspace.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "2c0639e1816b3e4bfc46aa6a212ad511849b6b387ee8ba0103cea7b9546b1c35"
      },
      {
        "path": "web/tests/soak-workspace.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "4d9895daaf840b0a42a7297eab36b910b789a9ae32a8c2970b3f18a0e66514ad"
      },
      {
        "path": "web/tests/source-library-ui.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "11a3b7d4391361fbaa90960366011f3f74bc8ead577fa2d4d0ebd15add06c934"
      },
      {
        "path": "web/tests/source-reader.test.js",
        "kind": "file",
        "mode": "0o644",
        "sha256": "f67cf94e69f53ea2fa84a67f2ba67586cba3fb9ccf5648f37075a1f9b0341796"
      }
    ]
  },
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

Review `review-issue47-end-to-end-autonomous-collaboration-004` is `IMPLEMENTING`.
It is bound to `e9955c778d0aa1ae0d2cc839345dbcbca0e4cc5d+worktree:428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716` and fingerprint `428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716`.
Codex must complete deterministic verification before issuing this request.
