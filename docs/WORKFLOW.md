# KGnote 開發工作流

## 1. 單一可驗收切片

每次只選一個能獨立回答「是否完成」的切片，例如：

- 一個 input schema 與 malformed-input 測試。
- 一個 source importer 的 dry-run，不含 apply。
- 一個 idempotent apply 與 read-back audit。
- 一個 Obsidian fixture 的 local graph 驗收。

「extractor + graph UI + Gemini review」不是單一切片。

## 2. 標準循環

```text
read plan/contracts
  → inspect Git/worktree and existing changes
  → state the slice and acceptance criteria
  → implement the smallest vertical path
  → run focused tests
  → run broader regression checks proportional to risk
  → inspect/read back the artifact
  → update plan or parking lot
  → report scope, evidence, limits, next step
```

## 3. Extraction 實驗要記錄的東西

- run ID、source ID、input content hash、schema/extractor/prompt/model version。
- success/reject/error 數、latency、input/output token 與 API error type。
- concept/edge/evidence yield，但 yield 不當成 quality。
- 人工抽樣的 hallucination、relation error、provenance error、over-merge、under-merge。
- retry/cooldown/checkpoint 紀錄；HTTP 429 屬 infrastructure/API stability，不當成 model semantic failure。

## 4. Dry-run / apply

Apply 前的 preview 至少分為：

```text
CREATE      新的 concept/event/evidence
UPDATE      同一 stable ID 的合法更新
UNCHANGED   已存在的等價內容
CONFLICT    需要人工決定的 alias/merge/人工修改衝突
REJECT      schema/evidence/provenance 不合格
```

Apply 後重新讀取 canonical store，比對預期 ID、reference integrity 與數量。不只相信 process exit code 0。

## 5. 測試層次

- Contract tests：schema、enum、版本、stable ID、多餘／缺失欄位。
- Pure unit tests：normalization、deduplication、relation policy、path/locator codec。
- Integration tests：fixture 從 import 到 dry-run/apply/read-back。
- Golden/manual evaluation：固定小樣本的人工 expected concepts/claims，允許以明確流程更新。
- Visual QA：Obsidian/Web 圖的節點、edge、panel、source link 與行動尺寸。

## 6. 遇到新問題

若不阻擋當前切片，寫進 `DEVELOPMENT_PLAIN.md` 停車場後繼續。只有當問題使目前驗收不可能、可能破壞原始 evidence，或需要使用者的重要產品決策時，才停下來處理／詢問。

