# Issue #46 — Pikambler 原文直接閱讀 Product Goal：O2 隔離與接單能力核對

Status: **IMMUTABLE PRODUCT GOAL PROPOSAL / NOT AUTHORIZED / NOT DISPATCHABLE**。
GitHub Issue: https://github.com/joannalee20050914/KGnote-public/issues/46
同一 #47 工程入口證據: https://github.com/joannalee20050914/KGnote-public/issues/47#issuecomment-6539550102

## 固定 Product Goal

- Goal ID: `GOAL-KGNOTE-PIKAMBLER-SOURCE-LESSON-CANARY`
- Goal version: `2026-10-31.1-isolated-canary-proposal`
- Canonical JSON SHA-256: `5e19072c3ea7b27e66e70a01f40bdc5d85d354017a7366cef510e3c96c69429e`
- Spec: `docs/control-plane/ISSUE46_PIKAMBLER_SOURCE_LESSON_GOAL_SPEC_v2026-10-31.1.json`
- 規格基準：GitHub main `bb23b319243a8bcb183ddf1cd2ce955043e3808e`，對應現行 Obsidian-first `PRODUCT_CONTRACT.md`、`DEVELOPMENT_PLAIN.md`、`requirements.json`、`FEATURE_DISPOSITION_LEDGER.md` 與 Issue #46。
- **只處理一篇明確選定的私有 Pikambler Markdown，不掃描整個 LLM Wiki。** 原始來源身分、版本與 bytes 不變；Obsidian 開啟原文正文，新增疑問／補充以不同筆記紀錄連回原段落。原文可以是文章或保留角色的學習對話；不自動將 AI 說明冒充實際學習行為。
- 只做一個 Obsidian 入口與一次私人來源的實測；概念圖譜、完整內嵌便利貼、外部 AI 自動改寫教材、大量資料遷移都不屬本 Goal。
- 本版 **沒有 Product Goal Owner APPROVE comment**；此文件和 Draft PR 不構成模型／產品派工授權。

## O2 依賴處理：獨立、可回退的隔離試行；不是 O2 successor

1. 現有 O2 v4 正式 Goal 為 `ACTIVE`，Runner 已停派。此狀態不等於 O2 `CLOSED`、也不轉移 O2 4/5 Codex 歷史額度。既有 backlog `previous_must_be_closed=true` 規則持續有效。
2. 本提案 **不加入 `PRODUCT_GOAL_BACKLOG.json` 的繼任序列**，因此不得把 #46 當成 O2 已 CLOSED 的下一個排程。只有另行 exact Owner 批准的 bounded isolated canary 才能在 O2 未完成時單獨試行。
3. 啟動前需由 Mac no-model admission 產生 `ISSUE46-O2-EXCLUSIVE-ISOLATED-TRIAL-RECEIPT`：舊 Runner unloaded、O2 formal state/ledger/cursor/quota/archive byte-for-byte unchanged；新 Product Goal 使用獨立 repo checkout/worktree/state/ledger/PR/review identity，並共用全域 writer lock，一次只有一個 model-bearing writer。若無法驗證則 **WAITING_O2_ISOLATION**；不得使用舊 O2 runner 或重設歷史。
4. 隔離試行 PASS 也不結案 O2、不授權永久 B-scheme，不自動選取 O3 等 successor。若通用接單引擎無法支援這種 isolated scope，停在 `BLOCKED_INTAKE_UNSUPPORTED`，不以改寫 backlog 或關閉 O2 繞過。

## Product Goal intake 實際支援狀態：目前未通過

- `PR #50` 的 #47 Engineering No-Paste **PASS** 只證明**固定** Issue #47 Owner comment `6539158585` 能被已安裝 Mac LaunchAgent 收取、去重和回寫。
- 已合併 `scripts/issue47_engineering_wakeup.py` 的 `INTAKE_COMMENT_ID = 6539158585`、`INTAKE_MARKER_NAME = KGNOTE-ISSUE47-PRECANARY-NO-PASTE-ENGINEERING-SMOKE-20261031`，與固定 #47/v4 `ENGINEERING` action binding 不會自動發現 #46 新 Product Goal；收件成功 **≠** 已可 Product Goal dispatch。
- 另須交付一個**既有唯一 LaunchAgent 內**的 generic Product Goal admission／intake：只接受 allowlisted repo/Issue、真實 Owner 身分、immutable Goal version/digest/permissions、獨立資料邊界、有效工作時間、總額度與單 writer lock；寫入 durable receipt、去重；拒絕未授權／O2 衝突／重複／來源越權；依既有 Runner WorkOrder／Ubuntu adapter 啟動，不要新增第二個 Runner。
- 需實機證明：在 #46 正式 exact approval 後，新的 GitHub comment 被本機讀取；先回寫 `ACCEPTED_FOR_EXACT_GOAL`，然後由 Mac 產生獨立 work order／ledger reservation，Codex/Claude 真正啟動並回寫 PR/review/repair。這不是當前已經通過的 #47 固定留言測試。
- **目前沒有該功能的實機驗收證據**。不能在 approval 之前、或支援尚未存在時，宣稱 #46 正在實作。

## 私人來源與資料外送邊界

- 私人 LLM Wiki 原文與使用者筆記只在本機讀取。先比對單篇來源是否已在 KGnote 中，既有 source ID/revision 優先；不進行全庫掃描、內容改寫或重複匯入。
- 不在公開 GitHub Issue/PR/checkpoint/Claude reviewer 中暴露原始對話、私人路徑、原始內容摘錄或憑證。工程測試可用 synthetic conversation fixture。沒有用戶獨立授權不得把私有文章送到遠端模型。
- 若目前沒有一篇已由使用者明確指定的私有 Pikambler 來源，記錄 `WAITING_PRIVATE_SOURCE_SELECTION`，提供本機來源選擇流程；不要自行猜檔案、公開檔名或用測試 fixture 冒充真實資料。

## 實際完成和停止規則

- 使用者能在 Mac Obsidian 讀完整原文、在某段留下自己的問題、關閉重開仍看到同段及註記；相同匯入重跑不複製、不能改原文，原文更新後 stale anchor 明示。
- 只用同一 Product Goal: Codex ≤6 launches、Ubuntu Claude ≤6 launches、每個合法工作窗口各 ≤2、單 writer、300s spacing、3600s backoff、既有 subscription 登入，絕不動 #47 工程 14/18 或 O2 4/5 額度。已用用量、UNKNOWN reservation 不可重置。
- Provider 狀態不足／user acceptance／獨立複審失敗：保存 checkpoint，正常修復由 Agent 自行做；真正 Goal 硬上限或未知人類產品決定才詢問 Owner。
- 完成前不能改 Product Goal backlog、不能替 Owner ACCEPT 或 MERGE、不能提升 PA-HUMAN-1／NS-HUMAN-SMOKE、不能宣稱 permanent go-live。

## 未滿足的前置依賴（全部需有實際 receipt）

- `ISSUE47-EXACT-REVIEWED-LAUNCHER-AND-UNIQUE-WRITER-RECEIPT` — **MISSING / NOT VERIFIED**
- `ISSUE47-NEW-PRODUCT-GOAL-GENERIC-INTAKE-PASS` — **MISSING / NOT VERIFIED**
- `ISSUE46-O2-EXCLUSIVE-ISOLATED-TRIAL-RECEIPT` — **MISSING / NOT VERIFIED**
- `ISSUE46-EXACT-PRIVATE-SOURCE-SELECTION-RECEIPT` — **MISSING / NOT VERIFIED**

下一步：先在 #47 既有接線工作範圍內修復 generic Product Goal intake，並完成獨立、安全、零模型負向測試；由具備本機權限的 Executor 驗證私人單篇來源 selection 和 O2 隔離。待規格、review/receipt、資料邊界均固定後，才能由 GitHub Owner 對本 Goal 版本發出一次 exact Product Goal APPROVE。**不要因使用者說要建立 Goal，就自行貼 APPROVE。**
