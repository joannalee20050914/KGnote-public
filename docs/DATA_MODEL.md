# KGnote 最小資料模型 v0

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
支持的摘要不能進 canonical Concept。Concept 不存「learner 對它懂幾分」。

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

### ReviewInteraction

一次曝光、回憶或回饋；Phase 4 以後才實作。

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
