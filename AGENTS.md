# KGnote Agent 與開發規範

## 1. 產品目標

KGnote 是 knowledge-graph-first 的互動式學習筆記本。它把原始教材與 AI 對話保留為 evidence，將可重用概念整合為可導覽的知識圖，再把可觀察的學習事件疊加到圖上。

核心不是「量化 learner 懂了幾%」，而是可追溯地回答：

- 哪些概念曾被接觸、提問、解釋、混淆或實際應用？
- 這些判斷由哪一段原始資料或行為 evidence 支持？
- 下次學習應從哪個局部圖與哪個尚未解決的 confusion 接續？

產品契約見 `docs/PRODUCT_CONTRACT.md`，分期與當前主線見 `DEVELOPMENT_PLAIN.md`，資料模型見 `docs/DATA_MODEL.md`，外部參考來源見 `docs/REFERENCE_SOURCES.md`。

## 2. 開工前必做

1. 閱讀 `DEVELOPMENT_PLAIN.md` 的「當前主線」、驗收條件與「停車場」。
2. 執行 `git status --short --branch` 與 `git worktree list --porcelain`；不猜測 branch、worktree 或 runtime 身分。
3. 先盤點已有檔案、契約與未提交修改。不覆寫、stash、commit、搬移或刪除使用者／其他 agent 的變更。
4. 先說明本次要完成的單一可驗收切片，不因順手而擴張範圍。

## 3. 資料與知識契約

- 原始來源是 immutable evidence。不覆寫、「清理」或把 AI 摘要假裝成原文。
- 每個派生資料必須保留 provenance：來源 ID／路徑、可用時的原文定位、extractor 版本、產生時間與 confidence。
- 短而穩定的 noun phrase 才能成為 Concept；完整語意放在 Evidence proposition，不把整句事件當節點。
- Concept Graph（知識如何連結）與 Learning Overlay（使用者曾發生什麼）必須分離。
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
5. 更新 `DEVELOPMENT_PLAIN.md` 的驗收記錄或將新問題放入停車場。
6. 回報修改範圍、測試結果、已知限制與一個最合理的下一步。

## 6. Git 與協作

- `main` 是唯一可稱為 main 的 ref。使用真實 branch 名稱回報工作位置。
- 一個 branch 只承載一個可命名主題。多 agent 並行時，每個任務使用不同 branch 與 worktree，並先界定可修改檔案。
- commit 保持單一目的。未獲使用者明確同意，不自行 commit、push、merge 或開 PR。
- 不把大型原始匯出、API response、中間 graph、HTML render 或日誌順手放入 repository root。先放 ignored output 目錄，再決定哪些是可重現 fixture 或正式 artifact。

## 7. 學習型協作的教學約束

當使用者希望理解操作時，採「操作軌／理解軌」雙軌：

- 先說本次操作要解決的問題、輸出要看哪裡，以及結果 A/B 各代表什麼。
- 新名詞一次只補足當前操作需要的最小模型；能查的 flag、PID 或路徑不要當背誦。
- 明確區分「現在必須理解」、「認得用途即可」與「暫時當黑箱」。
- 不讓教學支線延誤原始修復／實作目標；完成操作閉環後再整理概念。
- session 結束只摘要 2–4 個真正學會的分界，並另列曾看過但不用背的細節。

