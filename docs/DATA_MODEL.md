# KGnote 最小資料模型 v0

> **現行方向 amendment（2026-09-22；`kgnote-obsidian-first-2026-09-22`）：**本資料契約保持有效，但舊 `Phase 3c`／`Phase 4` 標籤只保存當時 sequencing provenance，不決定現行交付順序。現行順序見 root `DEVELOPMENT_PLAIN.md`；Obsidian-first 改變 renderer／入口，不把 Concept Graph、Evidence、Attempt 或 Learning Overlay 改成另一套資料真相。

## Morning beta 的 view／learning records

- `LearningStructureNode`：`id`、`title`、`parent_id`、`order`、`source_anchors`、`revision`、provenance、optional organizing relation，以及只供投影的 Concept／Claim refs。它不屬於 canonical Concept Graph。
- `ContextGloss`：綁定 source locator，記錄 `required_depth`、minimum explanation、deferred details 與 source-derived／external provenance。
- `PriorKnowledgeLink`：獨立、可審查的 current gloss → prior unit link；synthetic fixture 必須明示，不能假裝成自然發生的學習歷史。
- `AttemptFeedback`：以 assessment identity 追加 learner outcome、disagreement 與 correction；submitted Attempt bytes 不回寫。
- `DueItem`：由 `(learning_unit_id, review_item_id)` 取得穩定 identity，保存 milestone、due time、actions 與實際 scheduled Attempt refs；不等於 Attempt 或 mastery。

> 狀態：初始 contract，供 Phase 0 fixture 驗證  
> 原則：先保留 evidence 與 provenance，再追求 graph 密度。

## 1. 五種主要 record

### Source

一份不被 KGnote 覆寫的原始材料。

```yaml
schema_version: kgnote.v0.1
id: src_<stable-id>
type: source
source_kind: chatgpt_conversation | notebooklm_export | codex_session | course_material | document | web
title: string
uri_or_path: string
content_sha256: string
captured_at: datetime | null
registered_at: datetime
```

`uri_or_path` 是 canonical store 內部的註冊定位，不是 Web API 參數。Reader v1 只接受
snapshot digest、`source_id` 與可選 `line_range`；`kgnote.reader-application.v1` 在 explicit
store root 內解析登記路徑，驗證 regular non-symlink `raw/*.md`、SHA-256、UTF-8、大小與行界線，
對外只投影 Graph Read Model 共用的 Source label、exact text 與 Evidence／Concept／Edge IDs，
不回傳 `uri_or_path` 或本機 root。

### Concept

可在不同事件與來源中重用的短 noun phrase。

```yaml
schema_version: kgnote.v0.1
id: concept_<stable-id>
type: concept
canonical_name: string
aliases: [string]
spaces: [string]
summary: string
status: active | needs_review | deprecated
evidence_ids: [evidence_<stable-id>]
integration_version: string
integrated_at: datetime
```

`evidence_ids` 支持 canonical name、alias 與 summary 的人工整合判斷；沒有 evidence
支持的摘要不能進 canonical Concept。Concept 不存「product owner 對它懂幾分」。

多語言顯示原則：`canonical_name` 優先採當次教材與學習介面的主要語言；同一概念的
其他語言名稱放入 `aliases`，程式語法、URL、route 等不可翻譯 token 保持原樣。
中英文只要語意與 evidence 足以確認為同一概念，就共用 Concept identity，不因語言不同
自動建立重複節點；無法確認時先保留未解 association，不強制 merge。

### Evidence

支持一個知識或學習 claim 的完整 proposition。

```yaml
schema_version: kgnote.v0.1
id: evidence_<stable-id>
type: evidence
source_id: src_<stable-id>
locator:
  kind: line_range | heading | message | page | timestamp | whole_source
  value: string
proposition: string
observed_at: datetime | null
extractor_version: string
extracted_at: datetime
extraction_confidence: high | medium | low
review_status: unreviewed | accepted | corrected | rejected
```

`extraction_confidence` 只是 extraction claim 的不確定性，不是學習熟練度。

### LearningEvent

在特定情境中發生的一次學習互動。

```yaml
schema_version: kgnote.v0.1
id: event_<stable-id>
type: learning_event
event_type: exposure | question | confusion | explanation | application | assessment
occurred_at: datetime | date | null
context: string
source_ids: [src_<stable-id>]
concept_ids: [concept_<stable-id>]
evidence_ids: [evidence_<stable-id>]
extractor_version: string
extracted_at: datetime
extraction_confidence: high | medium | low
```

`event_type: explanation` 必須在 `context`／Evidence 中保留是教材、AI／系統解說或使用者自己的解釋；它們不可互換。系統或 AI 提供過解說最多能支持「已曝光於該解說」，不能據此建立 `explained`／`demonstrated` learner claim。只有實際保存的使用者輸出才能支持相應的表現紀錄。

### ReviewInteraction

一次曝光、回憶或回饋。下列 v0 shape 是歷史 baseline，不足以承載 2026-09-19 確認的全部活動類型與支援狀態；新寫入由既有 versioned Attempt contract 取代，而不是把所有活動硬塞成 retrieval stage。舊 Phase 3c／4 標籤不再代表現行 roadmap 順序。

```yaml
schema_version: kgnote.v0.1
id: review_<stable-id>
type: review_interaction
concept_ids: [concept_<stable-id>]
occurred_at: datetime
prompt_stage: exposure | fill_blank | changed_context | free_recall | inference
response: string | null
outcome: skipped | unknown | correct | correct_with_hint | partial | incorrect | insufficient_evidence
evidence_ids: [evidence_<stable-id>]
reviewer_version: string
recorded_at: datetime
```

Phase 3c 的新 Attempt 至少要把 `activity_type`（例如 `imitation | partial_completion | cloze | free_recall | explanation | application`）與 `support_state`（例如 `modeled | reference_visible | guided | hinted | unassisted | answer_revealed`）分開。未選練習、取消、只閱讀／追問後結束不建立 `incorrect` 或零分紀錄。LearningTarget 可以直接來自 Source／reviewed Claim、教學重點、使用者問題或可選 LearningNote，不以筆記存在為前置條件。

### 歷史 Phase 3c 所定義的學習脈絡／派生解說邊界

Phase 0 的五種 canonical record 不因產品流程修正而被偷偷擴欄位。歷史 Phase 3c 決定另立 versioned application records，至少涵蓋：

- `DerivedExplanation`：kind（summary／elaboration／example／comparison）、回應的 purpose／question、Source／Evidence anchors、generator／review provenance、revision 與 factual／teaching status。它是學習材料，不是 Source、canonical Claim 或使用者理解 evidence。
- `LearningContext`：目前 Source／locator、使用者問題、看過的 explanation refs、尚待確認處、最後活動與 resume state。它不是正式筆記，也不因存在而宣稱理解。
- `Attempt`：LearningTarget／item revision、activity type、support／exposure state、raw response、feedback 與 idempotent identity。只有實際開始／提交的練習才建立相應狀態。

這些 schema 需隨 3c-W0／3c-B1 垂直切片建立 valid／malformed fixture、provenance、reference integrity、idempotency 與 read-back tests；在此之前不把臨時 UI state 寫入 canonical Concept Graph。

## 2. Relation 分成兩層

### Concept Graph relation

知識如何連結：

```text
is_a
part_of
requires
maps_to
causes
contrasts_with
related_to
```

### Learning Overlay relation

使用者曾與概念發生什麼：

```text
encountered
asked_about
confused_with
explained
applied
demonstrated
```

每條 overlay relation 必須由至少一個 `evidence_id` 支持。`demonstrated` 只能用在 evidence 明確呈現使用者輸出或應用；不能因為 AI 做了解釋就建立。

### Edge shape

```yaml
schema_version: kgnote.v0.1
id: edge_<stable-id>
type: edge
source_id: concept_<id> | event_<id>
relation: string | null
target_id: concept_<id>
edge_class: canonical | learning | soft_association
evidence_ids: [evidence_<stable-id>]
confidence: high | medium | low | unresolved
ruleset_version: string
generated_at: datetime
```

`soft_association` 可以令 `relation: null`；它只表示「這兩個概念在目前 evidence 中靠近」。
v0 是單一 notebook owner 的學習圖，不建立 Actor record。說話者與互動情境保留在
Evidence proposition、Source 原文與 LearningEvent context；若未來出現多人協作需求，再以
獨立 contract 引入 Actor，而不是先留無法解析的 `actor_<id>`。

### Edge endpoint 與 relation 規則

| `edge_class` | source | target | relation | evidence |
| --- | --- | --- | --- | --- |
| `canonical` | Concept | Concept | `is_a \| part_of \| requires \| maps_to \| causes \| contrasts_with \| related_to` | 至少一筆 |
| `learning` | LearningEvent | Concept | `encountered \| asked_about \| confused_with \| explained \| applied \| demonstrated` | 至少一筆 |
| `soft_association` | Concept | Concept | `null` 或 `related_to` | 至少一筆，且只能支持「被同時提及／可能相關」，不能冒充已證實關係 |

其他 source/target/relation 組合一律 validation failure。Edge 只負責 typed relation；
Source 與 Evidence 的導覽使用各 record 的 reference 欄位與 Obsidian link，不另造 edge。

`relation` 是 machine-readable 類別，不保證單獨顯示時足以教學。Reader、Guided Concept Map
與 Exploration Graph 若要把 Edge 呈現給學習者，必須依
`docs/REPRESENTATION_CONSISTENCY_CONTRACT.md` 共用同一筆方向固定、Evidence-backed 的
Teaching Proposition／linking phrase；不同 renderer 不得各自改寫。同時，原文章節、流程階段
與地圖 grouping 屬於 view-level 導覽結構，不因出現在階層圖中就自動成為 Concept 或 canonical
`part_of` Edge。

Phase 3b v1 的具體落點是 `kgnote.guided-map-spec.v1`：它是獨立、人工審核且綁定 Graph
snapshot 的 view artifact，只 reference canonical IDs 並增加 focus、grouping 與 linking phrase。
純投影器輸出 `kgnote.guided-map-read-model.v1`；兩者 schema 見 `schemas/guided-map/v1/`。

## 3. Stable ID 原則

- Source ID 由 source kind＋穩定外部 ID／canonical path 決定；content hash 用來偵測內容改變，不應每次改動就產生新 source identity。
- Concept ID 由經人工可檢查的 normalized canonical name＋space/namespace 決定。Alias 不直接產生新 Concept。
- Evidence ID 由 source ID＋locator＋normalized proposition＋record `schema_version` 決定。
- Event ID 由 `source_ids` 中的主 source ID＋穩定事件 locator＋`event_type` 決定，不使用每次執行時間作唯一身分；事件 locator 在 v0 可記入 `context`，Phase 1 schema 應將其結構化。
- Edge ID 由 source ID＋relation（包含 null）＋target ID＋edge class＋ruleset version 決定。
- 正規化規則必須 versioned。規則更新時先做 migration preview，不靜默重寫所有 ID。

## 4. 當前允許的 Markdown 映射

```text
KGnote/
├── concepts/
├── learning-events/
├── evidence/
├── edges/
├── sources/
└── reviews/          # Phase 4 前可不存在
```

Markdown front matter 保存 machine-readable fields，正文保持人類可讀。關係使用 Obsidian internal links 方便 v0 graph，但 typed edge 不可只依賴正文中「有 link」來猜測。

## 5. Validation 不變量

1. Canonical store 的所有 reference ID 必須存在且只解析到一筆 record；不接受 pending reference。Phase 1 若需要 pending/unresolved 狀態，只能存在 staging/dry-run output，不得寫入 canonical store。
2. Evidence 必須有 source，locator 不能偽造精確度；只知整份來源時就使用 `whole_source`。
3. Canonical/learning edge 必須有 evidence；沒有足夠 evidence 時改為 soft association 或 reject。
4. 每筆 canonical record 都必須有受支援的 `schema_version`。Unknown enum、空白 concept name、多餘／缺失欄位與不支援的 schema version 明確失敗，不猜預設值。
5. 同一輸入在同一版規則下的 normalized output 必須 deterministic。
6. Apply 必須 idempotent；第二次執行只能是 unchanged 或明確 update，不能產生第二份等價資料。
7. Rejected extraction 保留錯誤類型與 raw model response 的安全本機記錄，但不進入 canonical graph。
8. 派生 record 必須以 Evidence reference 串回 Source，並記錄適用的 extractor／integration／ruleset version 與產生時間。時間與 confidence 描述派生過程，不是原始事件時間或使用者熟練度。

## 6. 從 SynthKG 沿用與修正的地方

| SynthKG 經驗 | KGnote 沿用 | KGnote 修正 |
| --- | --- | --- |
| decontextualization | 將長對話轉成可獲得單獨意義的 learning-event proposition | 不刪掉說話者、時間與學習情境 |
| Pydantic/schema validation | 所有 model output 先驗證才進 graph | schema 必須表達 provenance、review status 與 unresolved relation |
| 短 head/tail + proposition | Concept 保持穩定短語，Evidence 保留完整意義 | 增加 LearningEvent 與 overlay，不只存領域事實 |
| zero/few-shot 實驗與人工評估 | 以 fixture 比較 hallucination、relation error、yield、cost | 不先假設 few-shot 必然較好；先用 KGnote 資料重新量測 |
| Graph RAG 的 proposition retrieval + local subgraph | 未來 review context 使用 evidence 與 1–2 hop neighborhood | v0 先不實作 RAG；不用 generation 掩蓋圖資料問題 |
| API 429 是 pipeline stability 問題 | 記錄 rate-limit 錯誤與可重試狀態 | 必須有 checkpoint/idempotency，不將重試當新 learning event |
