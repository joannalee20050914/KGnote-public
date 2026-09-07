# KGnote 產品契約 v0

> 狀態：Accepted as initial design baseline  
> 日期：2026-08-14  
> 範圍：定義產品目的、邊界、主要使用流程與分層；不選定程式語言、framework 或 graph database。

## 1. 問題

長篇學習對話、課程資料與實作記錄能保留資訊，卻不容易回答：

- 某概念與哪些先備概念、相關概念或真實實作相連？
- 使用者上次具體問了什麼、混淆什麼、在哪裡成功應用？
- 如何不翻找章節或重開長對話，就取得剛好夠的局部上下文？

## 2. 產品定義

KGnote 是「有 evidence 支持的部分個人學習圖」：

1. Concept Graph 表示知識本身的關係。
2. Evidence Store 保留當時完整的 proposition、來源與定位。
3. Learning Overlay 記錄使用者可被觀察的接觸、提問、混淆、解釋與應用。
4. Review State 保留互動時間與回憶結果，不宣稱精確量測大腦。
5. Exposure Engine 在後續階段用局部 graph context 產生低負擔、逐漸減少相似提示的複習互動。

## 3. 主要使用流程

```text
raw source (ChatGPT / NotebookLM / Codex / course material)
  → immutable source record
  → learning-event decontextualization
  → concept / relation / evidence extraction
  → schema validation and normalization
  → dry-run diff and conflict review
  → idempotent graph integration
  → Obsidian or Web neighborhood navigation
  → optional evidence-grounded review
  → new learning evidence (append, never rewrite history)
```

## 4. 產品層與平台定位

| 部分 | 責任 | 初期定位 |
| --- | --- | --- |
| LLM Wiki / exported Markdown | 長期原始來源與人類可讀上下文 | 不覆寫的 input |
| KGnote Markdown/YAML | canonical concept、event、evidence 與 links | v0 source of truth |
| Obsidian | 筆記閱讀、global/local graph 與 v0 驗證 | 不承擔完整 typed-graph UI |
| KGnote Web | typed edges、filters、neighborhood、side panel、review UI | Phase 3 以後主介面 |
| Gemini/reviewer model | evidence-grounded 短回饋與曝光題 | Phase 4；不是 source of truth |
| LINE/LIFF/MINI App | 手機快捷入口 | Phase 5 候選，不綁死核心 |

## 5. 非目標

- 不宣稱重建、掃描或精確量測使用者大腦。
- 不以圖取代原始文章、完整對話或教材。
- 不要求每條 relation 一開始就有完美 ontology label。
- 不以 AI 自信度當成使用者理解程度。
- 不在 v0 重造完整 Obsidian、聊天 App、行動 App 或 graph database infrastructure。
- 不在未授權時將私人學習資料送到外部服務。

## 6. 成功指標（可觀察，不是心智百分比）

v0 有價值的證據是：

- 導入後的 concept 與 evidence 能穩定追回原始 source。
- 使用者可從概念在兩次點選內找到相關混淆或實作記錄。
- 同一資料重跑不會無限產生重複節點。
- 人工檢查能區分 correct relation、soft association、rejected claim 與無 evidence 的 hallucination。
- 使用者在實際學習中願意再次開啟這個圖，且找上下文的成本比翻長文低。

