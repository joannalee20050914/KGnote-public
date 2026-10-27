# O2 首次派工 Control Plane Hotfix 驗證契約

本文件記錄 `CODEX-APP-GOAL-O2-PRELAUNCH-HOTFIX-20261027` 的封存前驗證範圍。它不修改、取代或重新授權 O2 Product Goal；正式 O2 state、ledger、Owner APPROVE、模型額度、試行日期與 Work Item DAG 均不屬於本次候選修改。

## 修復邊界

1. Mac Runner 在 clean detached deployment 中，只能從固定 `codex/o2-reading-experience` 遠端 seed 建立首次候選；候選以真實 branch clone 計算 fingerprint，並由 append-only ledger state patch 保存。
2. Ubuntu bootstrap 必須在任何模型 process 前建立或重用自己的真實、private、clean Git checkout；錯 repository、branch、HEAD、owner、mode、symlink、Git common directory 或 dirty bytes 一律 fail closed。
3. O2 Claude review lane 必須以正式 `build_claude_schema_projection()` 產生三項 Schema Admission，並經真實 `WorkOrder.from_dict()` 與 command/schema preflight；不得回退 Legacy schema。
4. Mac Runner Python runtime 必須由 clean detached deployment、完整 pinned lock 與 pip install report 新建；不得複製舊 venv。安裝與 read-back 必須驗證 interpreter、package versions/sources、imports、`sys.executable`、`sys.path`、deployment commit/tree、owner/mode 與 rollback 指示。

## 2026-10-28 09:00 隔離首次派工矩陣

| 要求 | 綁定證據 |
|---|---|
| detached deployment、state 無 candidate、既有 Owner APPROVE | `RunnerTests.test_o2_first_window_runner_binds_seed_bootstraps_checkout_and_reserves_once` |
| `WI-O2-A-IMPLEMENT` ACTION_READY、首次 seed identity、sealed order SHA-256 | 同上；另由 `ProductGoalDynamicOrderTest.test_detached_first_seed_binding_is_remote_verified_ledgered_and_restart_safe` 驗證 ledger crash/restart replay |
| Ubuntu checkout 在模型前完成、第二次重用、dirty 不覆寫 | `LinuxWorkerBootstrapTest.test_product_checkout_is_cloned_once_reused_and_dirty_bytes_fail_closed` |
| 錯 common directory／identity／stage／digest／path fail closed | `LinuxWorkerBootstrapTest.test_product_checkout_rejects_linked_worktree_common_directory` 與 `LinuxWorkerRoutingTest.test_o2_product_goal_identity_rejects_cross_goal_stage_digest_event_and_path` |
| 首次 Codex `--pull-request 0` | `RunnerTests.test_o2_first_window_runner_binds_seed_bootstraps_checkout_and_reserves_once` 解析真正 sealed nested command |
| Worker result、Router checkpoint、Consumer/state successor | `ProductGoalRuntimeWiringTest.test_dynamic_order_to_real_router_checkpoint_result_state_and_next_work` |
| verification 與 publisher substitute | `ProductGoalWorkerLaneTest.test_verify_and_publish_require_exact_candidate_and_github_readback` |
| Reviewer 三項 Schema Admission 與 Claude-facing projection | `ProductGoalWorkerLaneTest.test_real_claude_schema_gets_deterministic_review_identity`；不 mock `WorkOrder.from_dict()` |
| Schema mismatch 在 executor/model 前拒絕 | `ProductGoalWorkerLaneTest.test_review_schema_projection_mismatch_fails_before_executor` |
| Review result ingestion／PASS、CHANGES_REQUIRED、429 與缺 verdict | `ProductGoalWorkerResultTest.test_claude_pass_changes_required_429_and_missing_verdict` |
| 相同 attempt 不建立第二 reservation 或重派 | `RunnerTests.test_o2_first_window_runner_binds_seed_bootstraps_checkout_and_reserves_once`、`GoalRunnerAdapterTests.test_durable_reservation_forces_reconciliation_before_redispatch` |
| 環境錯誤先 checkpoint 結算才可 retry | `RunnerTests.test_product_goal_runner_releases_reconciled_failure_then_retries_through_admission` 與 Router bootstrap/restart 負向測試 |
| 10/27 不派工、10/28 09:00 開窗、18:00 關窗、11/10 hard stop | `ProductGoalRuntimeWiringTest.test_o2_trial_schedule_boundaries_gate_planning_from_runner_clock`、`test_o2_dynamic_order_and_reservation_recheck_schedule_boundaries`、`test_o2_hard_stop_allows_existing_dispatch_evidence_reconciliation_only` |
| pinned runtime、imports、retired prefix、clean detached identity | `RunnerPythonRuntimeTest`；正式安裝收據只在 merge 後 deployment 產生 |

以上為 controlled no-model evidence；它不代表真實 Codex/Claude 產品輸出、五日試行、Obsidian 實機或真人學習驗收。正式 Hotfix 合併仍必須先取得同一 PR／HEAD／fingerprint 的 Ubuntu Claude PASS 與 Consumer 接受紀錄。
