# KGnote 產品契約 v0

> **現行方向 amendment（2026-09-22；`kgnote-obsidian-first-2026-09-22`）：**本契約的資料、evidence、學習活動與安全邊界仍有效；日常閱讀／編輯／連結／Canvas 入口改為 Obsidian-first。Web 實作保留為 prototype、comparison harness 與資料契約 regression，不再是 Phase 3 以後的預設主介面。若本文後段的舊 phase／介面文字與本 amendment 或 `docs/requirements/USER_DIRECTION_DELTA_20260922.md` 衝突，必須視為 authority drift 並先調和，不得靜默套 precedence。

## Morning beta 補充契約（2026-09-20）

- Learning Structure 是來源導覽的 recursive view record，不是 ontology；membership、nesting 與 organizing relation 不得自動產生 canonical knowledge Edge。
- Reading Assist 預設只顯示原文明確需要的 Context Gloss、先備連結與使用者主動展開的解說。`required_depth` 只能是 `recognize | define | explain | apply`，並必須標示 source-derived 或 external supplement provenance。
- Attempt、AttemptFeedback 與 DueItem 是三種不同 identity。Feedback／correction 只能追加；Due action 不可偽裝成 Attempt；只有由該 DueItem 啟動且完成的 scheduled-review Attempt 可推進 milestone。
- Catalog 與 continuity 不以 LearningNote 是否存在作 gate；零筆記、零 Attempt 仍是合法狀態。
- Local Graph 只能投影目前 structural scope 的 reviewed claims；disputed／blocked claim 要保留警示與 evidence，但不可顯示成可靠 edge。

> 狀態：Active data/product contract, amended for Obsidian-first
> 日期：2026-08-14  
> 更新：2026-09-19（閱讀／解說／可選練習工作區與跨視圖一致性）
> 範圍：定義產品目的、邊界、主要使用流程與分層；不選定程式語言、framework 或 graph database。

## 1. 問題

長篇學習對話、課程資料與實作記錄能保留資訊，卻不容易回答：

- 某概念與哪些先備概念、相關概念或真實實作相連？
- 使用者上次具體問了什麼、混淆什麼、在哪裡成功應用？
- 如何不翻找章節或重開長對話，就取得剛好夠的局部上下文？

## 2. 產品定義

KGnote 是「能保存學習脈絡、並由 evidence 支持的個人閱讀／解說／練習工作區」；knowledge graph 是資料整合骨架與可選探索工具，不是使用者必須先理解或操作的介面：

1. Concept Graph 表示知識本身的關係，是整合骨架，但不要求成為陌生主題的第一個學習畫面。
2. Evidence Store 保留當時完整的 proposition、來源與定位。
3. Learning Overlay 記錄使用者可被觀察的接觸、提問、混淆、解釋與應用。
4. Review State 保留互動時間與回憶結果，不宣稱精確量測大腦。
5. Learning Context 保留目前材料與位置、使用者問題、看過的解說、尚待確認處、可選練習與回饋，讓下次能續接；它不要求先形成正式筆記。
6. Practice Engine 在使用者選擇時提供模仿、部分完成、填空、回憶、解釋或應用活動，並如實保存材料／範例／提示／答案是否可見；有支援的練習不冒充無輔助提取。
7. Learning Views 依任務提供原文閱讀、結構化導讀、階層式學習地圖與知識圖譜探索；共同 identity、claim 與 provenance 不禁止有來源的摘要、展開、例子或對比。

## 3. 主要使用流程

資料導入與使用者學習是兩條邊界。導入 pipeline 可以是線性的、可重放的工程流程：

```text
raw source (ChatGPT / NotebookLM / Codex / course material)
  → immutable source record
  → learning-event decontextualization
  → concept / relation / evidence extraction
  → schema validation and normalization
  → dry-run diff and conflict review
  → idempotent graph integration
  → deterministic read models／source-grounded explanation candidates
```

使用者工作流不是固定 pipeline，也沒有 note-first 或 retrieval-first 關卡：

```text
閱讀原文或系統提供的結構化導讀
  ↔ 針對重要內容／不理解處取得摘要、拆解、例子或對比
  ↔ 繼續閱讀、追問、回看來源、收藏解說或先結束
  ↔ 由使用者選擇模仿、部分完成、填空、回憶、解釋或應用
  ↔ 取得具體回饋，再回到解說、來源、其他活動或之後繼續
```

一次 session 可以只閱讀或追問後結束；不同主題可同時處於不同活動狀態。LearningNote 可在任一處自願加入，但不是學習、建題或複習的前置條件。未進入練習不算零分；只有實際提交的回答才是該任務上的表現 evidence。

原文、導讀、派生解說、學習地圖與知識圖譜的 identity、claim、方向、Evidence 與互動焦點必須符合 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`。一致性不要求所有表面文字 byte-for-byte 相同：摘要、展開、例子與對比可以依問題換說法，但必須明示其類型、目的、來源 anchors 與 provenance，不得偷偷改變 canonical claim。

## 4. 產品層與平台定位

| 部分 | 責任 | 初期定位 |
| --- | --- | --- |
| LLM Wiki / exported Markdown | 長期原始來源與人類可讀上下文 | 不覆寫的 input |
| KGnote Markdown/YAML | canonical concept、event、evidence 與 links | v0 source of truth |
| Obsidian | 日常 Markdown 閱讀／編輯、links／backlinks、Canvas／結構導航與 KGnote learning-layer 入口 | 現行主要產品表面；不因 Obsidian-first 而弱化 typed data／evidence contract |
| KGnote Web | 已完成的 Reader／Practice／Map／graph 工程與資料契約 regression | prototype／comparison harness；除安全修復或 comparison test 外停止 Web-only workflow 擴張 |
| Gemini/reviewer model | 經同意後提供 source-grounded 摘要／拆解／例子／對比與短回饋 | Phase 4；不是 source of truth，模型產出不是使用者理解 evidence |
| LINE/LIFF/MINI App | 手機快捷入口 | Phase 5 候選，不綁死核心 |

## 5. 學習活動與可選表徵

最上層導航以工作為單位：閱讀／導讀、問與解說、練習／回饋、學習脈絡回顧，以及可選筆記。Reader、Map、Graph 是可被這些工作按需使用的表徵工具，不是必須依序通過的三層課程。

| 視圖 | 主要作用 | 核心限制 |
| --- | --- | --- |
| 原文閱讀 | 讀懂完整語境、例子與推理 | 顯示 immutable source；標註不得冒充原文 |
| 階層式學習地圖 | 以 focus question、導覽群組與具名關係建立輪廓 | 群組不自動成為 Concept；每條核心 Edge 要能讀成有 Evidence 的命題 |
| 知識圖譜探索 | 在已有輪廓後查看 local neighborhood、cross-link 與跨來源關係 | 保留相同 Concept identity、Edge 方向、不確定性與 provenance |

三個視圖不是內容的三個 source of truth。Source 保留原文，canonical store 保留可重用知識與 evidence，view model 只決定當下如何選取、排序與呈現。系統可另外保存 source-grounded 的派生解說；它們是帶 provenance 的學習材料，不是原文，也不必為每個換說法都修改 canonical graph。

## 6. 非目標

- 不宣稱重建、掃描或精確量測使用者大腦。
- 不以圖取代原始文章、完整對話或教材。
- 不要求每條 relation 一開始就有完美 ontology label。
- 不以三份獨立 AI 摘要分別驅動 Reader、Map 與 Graph。
- 不因章節階層或版面 grouping 自動新增 canonical Concept／Edge。
- 不以 AI 自信度當成使用者理解程度。
- 不要求使用者先自行整理筆記、修改 AI 導讀或完成練習，才可繼續閱讀、取得解說、建題或日後複習。
- 不把有範例／材料／提示可見的練習標成無輔助回憶，也不把未進入練習記成錯誤。
- 不在 v0 重造完整 Obsidian、聊天 App、行動 App 或 graph database infrastructure。
- 不在未授權時將私人學習資料送到外部服務。

## 7. 成功指標（可觀察，不是心智百分比）

v0 有價值的證據是：

- 導入後的 concept 與 evidence 能穩定追回原始 source。
- 使用者可從概念在兩次點選內找到相關混淆或實作記錄。
- 同一資料重跑不會無限產生重複節點。
- 人工檢查能區分 correct relation、soft association、rejected claim 與無 evidence 的 hallucination。
- 使用者可以朗讀／解釋核心 Edge，而不必由線的位置猜關係；同一 Edge 在 Map 與 Graph 的名稱、方向與語意一致。
- 使用者從 Reader、Map 或 Graph 任一處，可在兩次操作內看見支持目前 Concept／Edge 的原文，切換視圖後仍保留同一焦點。
- 使用者在實際學習中願意再次開啟這個圖，且找上下文的成本比翻長文低。
- 使用者能直接針對不理解處取得有來源的解說，而不必先填表、改 outline 或交出筆記。
- 使用者選擇繼續讀、換解說、先結束或進入練習時，系統執行相符動作；選擇解說不突然考試，選擇練習不只回傳另一份摘要。
- 下次回來能找回上次的來源位置、問題、看過的解說與尚待確認處，不必重建整段上下文。
- 若進入練習，活動類型、材料／提示可見性、raw response 與回饋可 read-back；若未進入，不產生零分或假 Attempt。
