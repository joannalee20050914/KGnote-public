# KGnote Agent 與開發規範

## 0. Repository control plane

本 repository 的現行 product direction ID 是 `kgnote-obsidian-first-2026-09-22`。`knowledge-graph-first` 描述資料整合骨架；`Obsidian-first` 描述日常產品入口與交付順序。Agent 不得把前者重新解讀為 Graph-first／Web-first UI。

每個 fresh session 依序執行：

1. 閱讀 `docs/control-plane/AUTHORITY.md`，分開 product authority 與 execution authority。
2. 閱讀 root `PLAN.md` 的唯一 active goal、milestone dependency、owned paths、acceptance 與 human gates。
3. 閱讀 root `CODEX_STATUS.md` 的 branch／HEAD、checkpoint、fingerprint、last evidence、next action 與 recovery notes。
4. 執行 `scripts/codex_preflight.sh`。若 authority drift、PLAN/STATUS 不一致、非預期 dirty state 或 consent gate 出現，fail closed。
5. 只執行 PLAN 中唯一 `active` milestone；不得從 superseded roadmap、歷史 AI review 或未完成 checkbox 自行恢復 scope。

一個 PLAN 只表示一個 active goal，可含 ordered／dependency-aware milestones；任何時間最多一個 milestone 為 `active`。Milestone 驗證綠燈後，若下一 milestone dependencies 完成且沒有 human gate，更新 PLAN／STATUS 後自行前進，不要求重新派工。測試失敗先在同一 milestone 內修復；只有跨越產品裁決、資料授權、破壞性 migration、外部付費／外送或明示權限邊界才停止。

`candidate_verified` 只表示目前 fingerprint 的本地 deterministic verification 通過；`release_verified` 需要 PLAN 明定的外部／人工 gate，不得由 Codex 從測試結果自行提升。physical device、Obsidian 實機、真人 learning acceptance 或 live provider 行為一律保留為人工／外部證據。

Control-plane 狀態與 evidence 必須 fingerprint-bound。Session 結束或 milestone 切換前更新 `PLAN.md` 與 `CODEX_STATUS.md`，讓另一 session 不依賴聊天內容即可續接。`output/control-plane/` 可放 ignored run evidence，但 durable handoff 必須存在 tracked PLAN／STATUS／authority 文件中。

### 0.1 Repository-mediated independent review

當 `.ai/REVIEW_PROTOCOL.md` 存在時，它是既有 execution control plane 的 review/orchestration extension，不是產品 authority。fresh session 在 preflight 後還必須讀 `.ai/REVIEW_PROTOCOL.md`、`.ai/REVIEW_REQUEST.md`、`.ai/REVIEW_RESULT.md`、`.ai/DECISIONS.md` 與存在時的 `.ai/ORCHESTRATOR_STATE.json`，並執行 `python3 scripts/codex_control.py --repo . review-validate`。`CODEX_STATUS.md` 的 review state、review ID、candidate identity、unresolved findings、human blockers 與 next action 必須和這些 artifact 一致。

Codex implementer 只能在已批准語意內決定 HOW，不得冒充 `CHATGPT_WORK_REVIEWER`、建立或自批 reviewer PASS、或把 reviewer 意見改寫成產品 authority。獨立 reviewer 必須在與 implementer 分離的 ephemeral context 中，直接重建 repository authority、檢查 exact sealed candidate 並寫 reviewer-owned artifact；它不得以「需要 ChatGPT Work」自我延後。human 仍獨占真正產品／架構裁決。

candidate-complete 時依序：

1. 執行 PLAN 要求的 deterministic verification，確認 fingerprint stable 且 evidence read-back 通過。
2. 用 `review-request` helper 產生／更新 request，綁定 exact HEAD＋worktree fingerprint，archive immutable snapshot。
3. 將 review state 與 `CODEX_STATUS.md` 更新為 `READY_FOR_REVIEW`，保留 `release_verified=false`。
4. 停止 implementation mutation；由 `scripts/codex_orchestrator.py` 將 `READY_FOR_AI_REVIEW` 作為 machine handoff，取得 candidate custody 並自動啟動獨立 reviewer。不得把這一步改成人工輸入「continue」。

若在 reviewer custody 前的 completion audit 發現候選缺口，先執行 `review-invalidate --reason ...`，留下 immutable audit event、分配新 review ID 並回到 `IMPLEMENTING`；不得直接修改已宣告 READY 的 candidate。若 custody 中 candidate bytes 改變，orchestrator 必須拒絕舊 review、留下 stale event、配置新 review ID 並自動回到 repair；fingerprint drift 不是人工續跑點。`CODEX_STATUS.md` 的 canonical JSON 與 human-readable handoff 必須由同一 helper 同步更新，不得出現互相矛盾的 next action。

`CHANGES_REQUIRED` 時，orchestrator 在五次預設 review/repair budget 內自動把完整 findings 交回 fresh implementer context。Codex 必須保留所有 unresolved findings，只能將已處理項目標成 `FIXED_PENDING_REVIEW`，補 regression evidence、重跑 verification，並以新 candidate／review cycle 請求複審；`VERIFIED` 只能由 reviewer 寫入。五次仍未解決才以 structured evidence 進入 `AUTOMATION_BLOCKED`。`PRODUCT_DECISION_REQUIRED` 時，受影響 scope 立即停止；human 選擇必須先寫入既有適當 authority／decision record 並由 `.ai/DECISIONS.md` 連結，不能只留在對話。

`PASS` 只對 result 中 exact review ID、revision 與 fingerprint 有效。任何 candidate byte drift 都使它 stale。orchestrator archive PASS 後，若下一 work package dependencies 完成且沒有該 package 的 human checkpoint，必須自動前進；不得因 routine test/build failure、review failure、agent/thread 結束或 context rollover 等待 human。PASS 仍須服從 PLAN dependency 與 explicit human checkpoints；尤其不得提升 `PA-HUMAN-1`、`NS-HUMAN-SMOKE`、`release_verified`、physical-device、真人學習或 live-provider 結論。

Orchestrator 的 start／resume／status／stop 介面為 `python3 scripts/codex_orchestrator.py --repo . {start,resume,status,stop}`。durable state 必須包含 active goal、work package、state、current agent、fingerprint、review cycle、blockers、next action、human action required 與 candidate custody。正常 human interruption 只允許 `HUMAN_CHECKPOINT_REQUIRED`、`PRODUCT_DECISION_REQUIRED`、`AUTHORITY_CONFLICT`、`AUTOMATION_BLOCKED`、`BUDGET_EXHAUSTED`、`GOAL_COMPLETE`；operator 明示 `stop` 另以 `STOPPED` 安全停止。

## 1. 產品目標

KGnote 是 knowledge-graph-first 的互動式學習筆記本。它把原始教材與 AI 對話保留為 evidence，將可重用概念整合為可導覽的知識圖，再把可觀察的學習事件疊加到圖上。

核心不是「量化 product owner 懂了幾%」，而是可追溯地回答：

- 哪些概念曾被接觸、提問、解釋、混淆或實際應用？
- 這些判斷由哪一段原始資料或行為 evidence 支持？
- 下次學習應從哪個局部圖與哪個尚未解決的 confusion 接續？

產品 authority 分界見 `docs/control-plane/AUTHORITY.md`；產品契約見 `docs/PRODUCT_CONTRACT.md`，分期與當前主線見 `DEVELOPMENT_PLAIN.md`，資料模型見 `docs/DATA_MODEL.md`，原文／學習地圖／知識圖譜的一致性見 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`，外部參考來源見 `docs/REFERENCE_SOURCES.md`。

## 2. 開工前必做

1. 閱讀 `docs/requirements/README.md`、`docs/requirements/DECISIONS_AND_CONFLICTS.md`，再讀 `DEVELOPMENT_PLAIN.md` 的當前排程、驗收條件與停車場；roadmap 只引用 requirement IDs，不取代台帳。
2. 執行 `git status --short --branch` 與 `git worktree list --porcelain`；不猜測 branch、worktree 或 runtime 身分。
3. 先盤點已有檔案、契約與未提交修改。不覆寫、stash、commit、搬移或刪除使用者／其他 agent 的變更。
4. 先說明本次要完成的單一可驗收切片，不因順手而擴張範圍。
5. 不自動執行 `git stash`、`git reset`、`git clean`、force checkout 或刪除 residual。若 dirty state 不符合 PLAN／STATUS，保留現場並 fail closed。

### 2.1 需求連續性

- `docs/requirements/requirements.json` 是需求與 delivery 狀態的唯一 machine-readable 主台帳；`scenarios.json` 是驗收規格主資料，其他 trace／matrix Markdown 由 guard 生成。
- 非 trivial 任務要列出 Requirement IDs、baseline ID/hash、禁止替代、scenario、implementation/test binding 與實際 run evidence；壓縮 context 後由 task packet 與本地進度檔恢復。
- 閱讀／解說優先且輸出自願；Soak、Practice、Context Gloss、Prior Knowledge、exact continuation 不得以相近功能互相替代。
- 新來源先標示 speaker、位置/hash 與 delta；AI 歷史提案仍是 proposal，不能冒充 user instruction。需求刪除、弱化、永久延期或 optional→mandatory 必須留下 before/after、理由、影響與批准來源。
- 執行 `python3 docs/requirements/requirements_guard.py check --repo .`；structural PASS、schema PASS 或路徑存在都不等於產品／人工／學習效益 PASS。

## 3. 資料與知識契約

- 原始來源是 immutable evidence。不覆寫、「清理」或把 AI 摘要假裝成原文。
- 每個派生資料必須保留 provenance：來源 ID／路徑、可用時的原文定位、extractor 版本、產生時間與 confidence。
- 短而穩定的 noun phrase 才能成為 Concept；完整語意放在 Evidence proposition，不把整句事件當節點。
- Concept Graph（知識如何連結）與 Learning Overlay（使用者曾發生什麼）必須分離。
- Reader、Guided Concept Map 與 Exploration Graph 只能投影同一份 Concept identity、Edge 方向、Teaching Proposition 與 Evidence；不同 renderer 不得各自改寫語意。
- 章節、流程階段與教學 grouping 是 view-level 導覽結構，不能因版面階層自動成為 Concept 或 canonical Edge。
- `encountered` 不等於 `understood`；AI 或 Codex 曾提到某概念，不能單據此宣稱使用者已理解。
- 不確定關係可使用 `related_to` 或未解 association；不為了「圖看起來完整」而幻覺精確 relation。
- confusion 是有價值的歷史 evidence，之後澄清時不應刪除；應以新 evidence 表示後續變化。
- 不使用虛假精密的熟練度百分比。Review state 只記行為事實，例如 `last_seen`、`correct_with_hint`、`confused_with` 與 exposure count。
- v0 的 source of truth 是人類可讀、Git 可追蹤的 Markdown/YAML。不在未經設計決策前引入 Neo4j 或其他 graph database。

## 4. 分層與安全邊界

- ingestion、extraction、normalization/integration、storage、visualization、review 是不同邊界；不寫成一個難以重放的大腳本。
- 純轉換邏輯不得直接發送 API 請求、修改 vault 或開啟 UI。外部 I/O 經明確 adapter 進入。
- 擷取與 merge 必須可重放。同一 source/extractor version 重跑不得產生無界重複節點或事件。
- 任何會覆寫人工筆記、批量 merge／rename concept、刪除 evidence、發送外部資料或產生付費 API 消耗的操作，都要先顯示 dry-run/preview，再取得使用者明確授權。
- 密鑰只放本機 ignored `.env`。版控只放 `.env.example`，且不得把外部參考專案中的 `.env` 搬入本專案。
- 教材、對話可含個人或敏感資訊。導入外部模型前必須有明確的資料邊界、redaction 策略與使用者授權。

## 5. 一個開發切片的完成條件

1. 實作符合已接受的 contract，不將未決定項目暗自寫死。
2. 有與風險相稱的自動測試；資料轉換至少要測 schema validation、provenance、idempotency 與 malformed input。
3. 使用一小組 fixture 做 read-back，驗證輸出不只是「程式沒有拋錯」。
4. 若會產生人類可視成品，必須實際打開或 render 驗收，不只驗證檔案存在。
5. 產品切片更新 `DEVELOPMENT_PLAIN.md` 的驗收記錄或將新問題放入停車場；純 control-plane 切片只更新 PLAN／STATUS／verification evidence，不改產品 roadmap。
6. 回報修改範圍、測試結果、已知限制與一個最合理的下一步。
7. 更新相關 requirement delivery、scenario run binding 與 source→requirement→scenario→actual test/result matrix；未執行維持 `not_run`。

## 6. Git 與協作

- `main` 是唯一可稱為 main 的 ref。使用真實 branch 名稱回報工作位置。
- 一個 branch 只承載一個可命名主題。多 agent 並行時，每個任務使用不同 branch 與 worktree，並先界定可修改檔案。
- commit 保持單一目的。未獲使用者明確同意，不自行 commit、push、merge 或開 PR。
- checkpoint 或其他明確授權的 commit 仍須使用 path-explicit staging，驗證 staged path/blob set，且不得把授權擴張成後續自動 commit。
- 不把大型原始匯出、API response、中間 graph、HTML render 或日誌順手放入 repository root。先放 ignored output 目錄，再決定哪些是可重現 fixture 或正式 artifact。

## 7. 學習型協作的教學約束

當使用者希望理解操作時，採「操作軌／理解軌」雙軌：

- 先說本次操作要解決的問題、輸出要看哪裡，以及結果 A/B 各代表什麼。
- 新名詞一次只補足當前操作需要的最小模型；能查的 flag、PID 或路徑不要當背誦。
- 明確區分「現在必須理解」、「認得用途即可」與「暫時當黑箱」。
- 不讓教學支線延誤原始修復／實作目標；完成操作閉環後再整理概念。
- session 結束只摘要 2–4 個真正學會的分界，並另列曾看過但不用背的細節。
