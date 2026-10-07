# KGnote 跨視圖一致性契約 v0

> **現行方向 amendment（2026-09-22；`kgnote-obsidian-first-2026-09-22`）：**本文件的 identity／claim／Evidence／direction 一致性仍是 active contract；`Reader／Map／Graph` 與 segmented-control 描述是 renderer 行為約束，不是要求 Obsidian-first 日常入口複製舊 Web 三視圖 UI。Web-specific 例子保留設計 provenance，現行承載與排序見 root `DEVELOPMENT_PLAIN.md`。

## Recursive Learning Structure 與 Local Graph

Learning Structure 只決定 Reader 的順序、breadcrumb 與 source scope。`parent_id`、nesting、topic、parallel、alternatives、contrast、sequence、problem_solution、mechanism、example 都是 view organization；除非另有 accepted Evidence／Claim，不得轉成 Concept Graph relation。Local Graph 以目前 structure node 的 claim refs 為 scope，並再次套用 ClaimReview gate；不同 renderer 不得補猜缺少的 relation。

> 狀態：Accepted design baseline
> 日期：2026-09-15
> 更新：2026-09-19（固定三層順序撤回；加入派生解說與可選練習邊界）
> 範圍：定義原文閱讀、階層式學習地圖、知識圖譜、派生解說與可選練習如何共用語意、來源與互動焦點；本文件不直接決定最終 UI framework，也不宣稱所有工作區已完成實作。

## 1. 決策摘要

KGnote 保留三種可組合的學習表徵，但不採用必須依序通過的三層學習模式：

```text
                         ┌─ 階層式學習地圖
immutable Source／Evidence ├─ 局部知識圖譜
                         ├─ source-grounded 派生解說
                         └─ 可選練習與回饋
```

這些工具共用 identity、claim、Evidence 與 provenance，不是三份各自生成、各自維護的教材，也不是關卡：

1. **原文閱讀**保留完整語境與作者的自然語言推理，是陌生主題的預設入口。
2. **階層式學習地圖**提供 focus question、章節／流程層級、少量核心 Concept 與可讀關係，按需要協助形成主題輪廓。
3. **知識圖譜**提供局部到跨來源的非線性探索；它不鎖住使用者，也不把開啟圖譜當成已理解。
4. **派生解說**可依使用者的目的或疑問提供摘要、展開、例子與對比；它們是有來源的學習材料，不是原文或使用者表現。
5. **練習**只在使用者選擇時進入；模仿、部分完成、提示填空、無輔助回憶、解釋與應用各自保留活動及支援狀態，不互相冒充。

Knowledge-graph-first 仍是 KGnote 的資料整合原則；它不再被解讀為「初學者第一個畫面必須是完整網狀圖」。

## 2. 名詞與責任邊界

| 名詞 | 在 KGnote 的意思 | 不是什麼 |
| --- | --- | --- |
| 原始來源（Source） | 不可被 KGnote 覆寫的完整教材、對話或文件 | AI 改寫後的乾淨版本 |
| Evidence | 支持某個 claim 的 proposition、來源 ID 與可用時的精確定位 | 裝飾用引文或理解程度分數 |
| Concept | 可跨來源重用的短而穩定概念 | 章節標題、完整句子或一次學習事件 |
| Teaching Proposition | 供學習者閱讀的「主詞 Concept＋關係詞＋受詞 Concept」定向命題 | 每個視圖各自產生的摘要 |
| 學習地圖（Guided Concept Map） | 由 focus question 約束、具有階層與具名關係的導覽視圖 | 只有放射分支、未說明關係的傳統心智圖 |
| 知識圖譜（Exploration Graph） | 從 canonical Concept／Edge 投影出的局部或跨來源網路 | 教材閱讀順序或自動熟練度判斷 |
| 導覽群組（Outline Group） | 原文章節、流程階段或教學分組 | 未經 evidence 支持的 Concept 或 `part_of` 關係 |

使用者介面可稱第二層為「學習地圖」，技術文件使用 `Guided Concept Map`，以免和只有自由聯想的 mind map 混淆。

## 3. 單一語意骨架

三個視圖必須從同一條可追溯骨架投影：

```text
immutable Source bytes
  └─ Evidence(source_id + locator + proposition)
       ├─ Concept identity + learner-facing label
       └─ directed Edge + one reviewed Teaching Proposition
            ├─ Reader annotation
            ├─ Guided Concept Map projection
            └─ Exploration Graph projection
```

不得讓 reader、map、graph 的 renderer 各自呼叫模型，然後把另一套名稱、關係或 factual claim 偽裝成 canonical projection。AI 可以在 staging 提出 candidate；通過 validation 與人工 preview 後，視圖只讀取同一份已接受資料。

這項限制不禁止針對同一來源建立多筆派生解說。摘要、展開、例子與對比可以依問題換說法，但每筆都必須另存 explanation identity／revision、`summary | elaboration | example | comparison` kind、回應的 purpose／question、source／Evidence anchors、generator／review provenance 與 factual status。派生解說不得覆寫 Source、暗改 canonical claim，或只因被 AI 生成／使用者看過就建立 `understood`／`demonstrated`。

### 3.1 Teaching Proposition 最小投影

第一版不必立刻新增 canonical record type，但所有 learner-facing relation 都必須能投影成下列等價資料：

```yaml
edge_id: edge_<stable-id>
subject_concept_id: concept_<stable-id>
linking_phrase: 將公開請求轉送到
object_concept_id: concept_<stable-id>
display_locale: zh-Hant
evidence_ids: [evidence_<stable-id>]
review_status: accepted
projection_version: string
```

`Edge.relation` 是機器可驗證的類別；`linking_phrase` 是學習者可讀、具有方向的關係詞。兩者不得互相矛盾。`linking_phrase` 的最後儲存位置與 schema migration 需另以小切片決定，但在此之前不得由不同 renderer 臨時改寫。

一筆 Teaching Proposition 必須可以直接讀成一句話：

```text
<subject label> <linking phrase> <object label>
```

例如：

```text
ngrok 通道 將公開請求轉送到 本機連接埠
```

`相關`、`對應`、`maps_to` 等過度寬泛字詞不能單獨充當學習地圖的解釋；如果 evidence 只能支持共同出現，就保留為 soft association，並從預設學習地圖排除。

## 4. 跨視圖不變量

### 4.1 原文不可變

- 原始 Markdown／對話 bytes 不因閱讀介面、標註或地圖生成而改寫。
- Reader 可以加上非破壞性的 highlight、註解與「此段對應」提示，但必須能顯示未改寫原文。
- 每個派生標註、Concept、Edge 與 Teaching Proposition 都要經 Evidence 回到 Source 與 locator。
- Web Reader 只能讀取使用者明確選定、已註冊的 Source；不得把任意本機路徑變成瀏覽器可讀 endpoint。

### 4.2 Concept identity 與名稱一致

- 同一 Concept 在三個視圖使用同一 stable ID。
- 同一 learning unit 與 `display_locale` 中使用同一 learner-facing label；不得在「用戶端」「客戶端」「client」之間隨機切換。
- 第一次出現可以顯示 `用戶端（client；此處為 LINE）`；後續以主要顯示名稱為準，其他語言名稱只作 alias／glossary。
- 程式語法、URL、route、identifier 等不可翻譯 token 保持原樣。
- 顯示名稱的變更必須經同一 normalization／review 路徑，不能只改某一個 renderer。

### 4.3 關係語意與方向一致

- 同一 `edge_id` 在學習地圖與知識圖譜使用相同 subject、object、方向與 learner-facing linking phrase。
- 若原始文字採反向句型，Reader annotation 應指出它對應到哪一筆定向命題；不得因此讓另一個視圖偷偷反轉 Edge。
- 同一命題的主動／被動改寫若會改變閱讀方向，第一版只保留一個主要版本。
- 多語版本可以有不同表面語序，但必須指向相同 subject／object identity、relation semantics 與 Evidence。

### 4.4 階層與知識關係分離

- 章節、流程階段與教學分組只負責閱讀順序和版面 grouping。
- `Outline Group contains Concept` 不自動產生 `Concept part_of Concept`。
- 原文標題只有在它本身是可跨來源重用、且有 Evidence 支持的短概念時，才可另外成為 Concept。
- 教學地圖可以把既有 Concept 排入階層；該 layout 不得被回寫成新的 canonical knowledge claim。

### 4.5 範圍與粒度一致

- 一張學習地圖只回答一個明確 focus question。
- Reader 預設開啟支持該 focus question 的連續原文範圍；Map 與 Graph 預設只顯示同一範圍需要的 Concept／Edge。
- Map 可以省略例子與細節，但不能加入原文和 accepted Evidence 都未支持的新因果、先備或流程關係。
- Graph 可以增加經支持的 cross-link 或跨來源鄰居，但原來的核心命題仍保持相同名稱、方向與視覺識別。
- 節點數與 cross-link 數由 fixture 可讀性測試決定，不把任意「神奇數字」宣稱為普遍認知定律。

### 4.6 Evidence 與不確定性一致

- Guided Map 預設只使用 `accepted`／`corrected` Evidence 支持的命題。
- `unreviewed`、`low confidence`、`related_to` 或 soft association 必須保持可辨識的不確定狀態；不得在較簡化的視圖中變得更肯定。
- 如果某條關係沒有足以支持可讀 linking phrase 的 Evidence，Map 應省略或標為「待釐清」，不能補猜。
- Internal metadata（extractor version、confidence code、stable ID）預設不與學習敘述混排，但要能在 provenance／debug view 查到。

### 4.7 焦點與互動狀態一致

- 切換 Reader／Map／Graph 時保留目前的 Source、focus question、Concept 與可用時的 Evidence locator。
- 點原文標註會聚焦相同 Concept／Edge；點 Map／Graph 節點或邊會就近顯示其原文 Evidence。
- 同一 Concept 在三個視圖使用同一名稱、基礎顏色與 icon 語意；layout 可以不同。
- 在新視圖不存在的額外鄰居不得把焦點靜默換成另一個 Concept。
- URL／重新整理後是否保存 view state 是實作決策，但不得把 stale selection 顯示成仍與目前 snapshot 相符。

### 4.8 學習階段不是熟練度宣稱

- Reader、Map、Graph 是不同任務的工具，不是 `beginner / intermediate / expert` 人格標籤。
- 可以依使用者明確選擇的「我還陌生／已有輪廓／想自由探索」推薦起始視圖，但不由點擊數自動宣稱已理解。
- 所有視圖都保持可進入；progressive disclosure 是降低預設負擔，不是鎖功能。
- 從 Map 進入 Graph 或完成一次題目只新增 observable LearningEvent／ReviewInteraction，不產生熟練度百分比。

## 5. 三種視圖各自允許做什麼

| 視圖 | 核心任務 | 可以改變 | 不可改變 |
| --- | --- | --- | --- |
| Reader | 讀懂語境、例子與完整推理 | 字級、段落導覽、非破壞 highlight、就近顯示對應命題 | 原文 bytes、Concept identity、Evidence locator |
| Guided Map | 建立一個 focus question 的宏觀結構 | 排序、階層 grouping、折疊細節、只選核心 accepted propositions | Concept 名稱、Edge 方向、linking phrase、Evidence 支持 |
| Exploration Graph | 局部或跨來源發散探索 | hop、filter、layout、增加有 Evidence 的鄰居與 cross-link | 已顯示核心命題的語意、方向、不確定性與 provenance |

不同視圖的價值來自資訊量、排列方式和探索自由度不同；一致性不等於三個畫面長得一樣。

## 6. 降低跨表徵認知負荷的 UI 約束

1. iPad／手機同一時間只安排一個主要視圖，不將完整 Reader、Map、Graph 同時塞在一個畫面。
2. Source excerpt／Evidence 以鄰近 panel、drawer 或底部 sheet 顯示，避免切到另一頁後靠工作記憶拼接。
3. 同一 renderer 若提供三視圖切換，可使用一致的 control（歷史 Web 例：`閱讀｜學習地圖｜探索`）並持續顯示目前 focus question；Obsidian-first 介面不被要求複製此 control。
4. 第一次接觸陌生主題時預設 Reader／結構化導讀；同一位置提供繼續讀、換種解說、追問、可選練習與先結束，不把 Map、Graph、筆記或測驗設成必經下一步。Graph 預設為相同 learning unit 的 local view，不先展示全庫網路。
5. Map 的每條可見 Edge 都要能朗讀成自然句子；Canvas 上放不下時，點選後仍須立即顯示完整命題，不能只留下代碼。
6. 新增跨來源節點時，以視覺層級區分「本段核心」與「延伸探索」，不能讓延伸鄰居改寫主要閱讀路徑。
7. 顯示 alias、定義或 Evidence 時採 progressive disclosure；同一概念不要同時堆疊多組近義名稱。

## 7. 閱讀、解說與練習的可往返互動

三種視圖主要處理理解、組織與探索；長期保留可以在之後由提取、解釋或應用活動觀察，但不因此把測驗設成陌生材料入口。第一版採可往返工作流：

```text
閱讀原文或結構化導讀
  ↔ 取得針對疑問的摘要／拆解／例子／對比
  ↔ 繼續閱讀／追問／回看來源／收藏／先結束
  ↔ 使用者選擇模仿／部分完成／填空／回憶／解釋／應用
  ↔ 查看具體回饋與 Evidence，再回到任一活動或之後繼續
```

- 初次使用不要求從空白畫布建立整張圖、正式筆記或立即作答；一次 session 可以只閱讀／追問後結束。
- 系統可建議一小題，但只有使用者選擇後才進入。選 `再解釋一次` 必須回到解說，不能偷偷改成測驗；選 `試著說一次` 必須提供真正的輸入活動，不能只送另一份摘要。
- 模仿與 reference-visible practice 是正常的有支援活動，不是失敗版本的 free recall。後續可以在事先同意的活動中逐步減少骨架與提示，但每次都保留 Concept identity、Evidence、activity type 與支援／曝光狀態。
- 回答結果只記錄實際 response、activity type、材料／提示／答案可見狀態、outcome 與 context；不把看過地圖或 AI 解說等同於 understood，也不把未作答記成零分。
- LearningTarget 可直接來自 Source／reviewed Claim、教學重點或使用者問題；不要求先有 LearningNote。答錯後可以回看解說、換例子、澄清問題、選擇修訂筆記或之後再試，不強迫先改 NoteBlock。

## 8. 產生與審核流程

```text
明確選定 Source
  → 只讀匯入與 Source identity
  → outline／focus question candidate
  → Concept／Evidence／Edge candidate
  → learner-facing Teaching Proposition candidate
  → schema + semantic + cross-view consistency validation
  → 人類 preview（名稱、方向、linking phrase、原文定位）
  → 經批准後 apply
  → 三個 deterministic read model／view
```

規則：

- AI candidate 不能直接成為 learner-facing truth。
- Preview 必須把完整命題讀成一句話，並並列 supporting source excerpt；只顯示 `maps_to` 等內部 enum 不算可判讀 preview。
- 同一 candidate 只能正規化一次；三個 renderer 不再個別 paraphrase。
- 修正 Concept 名稱或 Edge 方向時要產生明確 diff，並重新驗證所有引用它的視圖。
- 如果只有一個視圖能成功投影，整個 learning unit 不得標為三視圖 ready。

### 8.1 Linking phrase candidate staging boundary

Learner-facing linking phrase 不加入既有 `kgnote.extraction-output.v1`，也不成為 canonical
Edge 欄位。獨立的 `kgnote.linking-phrase-context.v1` 只提供 snapshot-bound canonical Edge、
固定方向與 source-grounded Evidence；首次擷取的 Evidence 可以是 `unreviewed`，但只能支援
`pending` candidate。不受信任的模型回應只能包含 `edge_id` 與短語。
Adapter 會拒絕 missing／duplicate／extra Edge、generic phrase 與額外欄位，並從 trusted
context 重建端點、relation、Evidence IDs 與 locators。產物
`kgnote.linking-phrase-candidate-set.v1` 的狀態固定為 `pending`，且以 context／raw-response
SHA-256 與 provider／model／prompt version 保留 provenance。後續人工可 accept／correct／reject，
決策以另一份 append-only reviewed set 保存；只有短語被 accept/correct，且全部 supporting
Evidence 也已 accepted/corrected，才具備進入 Guided Map spec 的 promotion 資格。

## 9. 自動驗證條件

正式實作後至少要有以下 contract tests：

1. 三視圖中的相同 Concept resolve 到同一 stable ID 與同一 locale label。
2. 同一 `display_locale` 中，相同 `edge_id` 的 subject、object、方向與 linking phrase byte-for-byte 相同。
3. 每筆 Teaching Proposition 至少有一筆存在且可回到 Source 的 Evidence。
4. Guided Map 不接受沒有 Evidence 的 relation，預設也不接受 soft association 冒充解釋。
5. Outline Group 不會被 projector 自動輸出成 Concept 或 canonical Edge。
6. 切換視圖的 focus state resolve 到目前 snapshot；unknown／stale reference fail closed。
7. 相同 input、projection version 與 locale 產生 deterministic output。
8. Reader annotation 不修改 raw source bytes，且不能讀取未註冊的任意檔案。
9. 中英文 alias 不產生第二個等價 Concept；無法確認語意相同時不強制 merge。
10. 不同 renderer 不包含各自獨立、未標示 provenance 的 AI factual claim／relation generation path；合法派生解說必須是可辨識、versioned、source-grounded 的 explanation artifact，而不是 renderer 私有文字。
11. 同一派生解說可回到其 purpose／question 與 Source／Evidence anchors；摘要、展開、例子或對比不得修改 canonical claim 的方向、條件或不確定性。
12. 練習紀錄保存 activity type 與支援／曝光狀態；未選練習、取消或只讀後結束不建立 incorrect Attempt。

## 10. 人工與實機驗收條件

對每個小型真實 fixture，至少檢查：

1. 使用者能指出這張 Map 正在回答哪一個問題。
2. 每條核心 Edge 都能直接朗讀成合理句子；若不能，先修 relation，不靠使用者猜。
3. 從 Reader、Map 或 Graph 任一處，在兩次操作內能看到支持該 Concept／Edge 的原文。
4. 在三視圖切換後仍停在相同 Concept／Evidence，且名稱與方向沒有改變。
5. iPad 上不需同時記住兩個分離畫面的內容才能理解關係。
6. 若本次驗收由使用者選擇練習，系統能依該活動的支援狀態接住輸入並保存行為 evidence；若只閱讀／追問後結束，不把未作答記為失敗或零分。
7. 使用者可標記「這條關係看不懂／不同意」，而不是被迫在錯誤圖上繼續探索。
8. 關閉重開後能找回上次的 Source 位置、問題、看過的派生解說與尚待確認處，不必重建整段脈絡。

## 11. BitePacer 首個驗收單元

第一個三視圖 fixture 沿用已選定的 BitePacer 迷你計網教材，focus question 為：

> 一則 LINE 訊息如何抵達 product owner Mac 上的 BitePacer？

Guided Map 的導覽群組先固定為：

1. 誰在溝通：用戶端、伺服器。
2. 如何找到位置：IP 位址、連接埠、本機回環位址。
3. 如何交換資料：HTTP 請求、HTTP 回應。
4. 程式如何處理：Flask 路由。
5. 外部如何進入：ngrok 通道。

這些群組是教學順序，不直接成為 Concept Graph nodes。核心 Teaching Propositions 必須由現有原文重新人工審核；不能沿用只有 `related_to` 或過度寬泛 label 的顯示結果。

## 12. 研究依據與證據限制

- Novak 與 Cañas 將 concept map 定義為具有 linking words、階層、focus question 與 cross-links 的知識表示；也主張讓概念連回外部資源。 <https://cmap.ihmc.us/docs/theory-of-concept-maps>
- Davies 區分 mind map 的自由聯想與 concept map 的具名概念關係，並指出工具應依學習目的選擇。 <https://doi.org/10.1007/s10734-010-9387-6>
- Nesbit 與 Adesope 對 55 項研究、5,818 名學習者的 meta-analysis 顯示 concept／knowledge maps 與知識保留改善相關，但效果依使用方式與對照條件而異。 <https://doi.org/10.3102/00346543076003413>
- Amadieu、Tricot 與 Mariné 的互動文件實驗顯示，低先備知識者在階層結構下有較佳自由回憶且較少迷失；高先備知識者較能應付網狀結構，但網路並未普遍保證額外學習增益。 <https://doi.org/10.1016/j.chb.2008.12.017>
- Ainsworth 的 DeFT framework 指出 multiple representations 是否有效，取決於設計、功能與學習者必須完成的跨表徵任務；不是表徵越多越好。 <https://doi.org/10.1016/j.learninstruc.2006.03.001>
- Schnotz 與 Bannert 顯示 task-appropriate graphics 可幫助心智模型，task-inappropriate graphics 也可能干擾。 <https://doi.org/10.1016/S0959-4752(02)00017-8>
- Chandler 與 Sweller 的 split-attention experiments 支持把必須共同理解的文字與圖就近整合。 <https://doi.org/10.1111/j.2044-8279.1992.tb01017.x>
- Chang、Sung 與 Chen 的研究中，map correction 改善了文本理解與摘要，scaffold fading 促進摘要；這支持 KGnote 先測試 expert skeleton 與逐步撤除提示，而不是先假定空白生成最適合初學者。 <https://doi.org/10.1080/00220970209602054>
- Karpicke 與 Blunt 的實驗顯示 retrieval practice 對科學文本的 meaningful learning 可優於只做 concept mapping，因此 KGnote 不把被動看圖當成記憶完成。 <https://doi.org/10.1126/science.1199327>

目前沒有一項研究直接驗證 KGnote 這個完整的「原文＋Guided Concept Map＋Knowledge Graph」產品組合。此契約是由多條相鄰證據形成的 evidence-informed design hypothesis；是否適合 product owner，仍以小型真實教材、可觀察行為與反覆實機使用驗收，不宣稱已有普遍因果證明。

## 13. v1 儲存與投影決定

Teaching Proposition 與 hierarchy grouping 存在獨立、人工審核的
`kgnote.guided-map-spec.v1`，而不是擴充 canonical Edge，也不是由各 renderer 現場產生。
Spec 綁定一個 `kgnote.graph-read-model.v1` snapshot，只保存 focus question、locale、群組、
Concept／Edge／Evidence references 與 linking phrase；`kgnote.guided-map-projector.v1` 再解析
同一份 Concept label、Edge source／target／relation 與 Evidence，輸出
`kgnote.guided-map-read-model.v1`。詳細 schema 與 ownership boundary 見
`schemas/guided-map/v1/README.md`。

這個 v1 決定避免改動 canonical schema，同時讓 linking phrase 可 version control、人工審核與
測試。Graph snapshot、Edge Evidence 或 reference 一旦漂移就 fail closed，不能由 UI 猜測修補。

## 14. 明確延後的決定

- 自動產生 outline／focus question 的 provider、prompt 與成本界線。
- 如何依使用者明確自評推薦起始視圖，以及是否保存該 preference。
- 跨多篇教材的 learning unit merge、map version history 與協作編輯。
- 語言學習教材是否需要 sentence pattern／pronunciation 等專用 view；不得先塞進資工概念 fixture。

這些項目必須在各自實作切片中先做 contract／preview，不能由 UI 程式暗自寫死。
