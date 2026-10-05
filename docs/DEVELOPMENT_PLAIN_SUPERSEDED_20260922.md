# KGnote 白話版開發計畫（2026-09-22 前歷史版本）

> **Superseded：**本檔完整保留 2026-09-20 Web-first／Phase 3c roadmap、歷史裁決與驗收記錄，供追溯已完成工程與先前假說。現行排程改見 repository root 的 `DEVELOPMENT_PLAIN.md`。不得以本檔未完成 checkbox 覆蓋 2026-09-22 使用者明示的 Obsidian-first 產品方向。

> 需求 SSOT：本檔只負責排程與保留歷史脈絡。需求原文角色、正反驗收、delivery 與 test/result binding 以 `docs/requirements/requirements.json`、`scenarios.json` 為準；人類可讀追溯見自動生成的 `docs/requirements/REQUIREMENTS_TRACE.md` 與 `TRACEABILITY_MATRIX.md`。
>
> 當前 baseline：`kgnote-reconciliation-2026-09-20-r1`。當前收斂 run 至少完成兩輪 A→B→C→D→E；本輪優先序是 (1) `KG-GOV-01–07` / `SC-35–36` 需求基線，(2) `KG-SOAK-01,04–05` / `SC-02,18` 獨立低壓曝光，(3) `KG-MEM-01` / `SC-03` 精確續學，再依台帳重盤 P0/P1。

> 狀態：Phase 3b 三視圖原型保留為已完成的工程 baseline；2026-09-19 首次真實 H0 發現 note-first 任務不符合 product owner 的使用意圖，當前主線改為 Phase 3c「閱讀、結構化導讀、針對疑問的解說與可選練習」工作區；筆記與 Graph 都是可選工具
> 更新：2026-09-20
> 命名說明：本檔依專案建立需求使用 `PLAIN`，意指「不用專案術語也能檢查」的白話版計畫。

> 2026-09-20 P0 執行裁決：本輪不等待 Phase 3c 各能力軌依序完成，直接交付一條可啟動的 OS 教材垂直流程：`Learn（閱讀／導讀／按需解說與 Evidence）→ 使用者主動開始 Practice → 關係回想或自由解釋 → 提交後才揭露答案／Evidence／回饋 → Retry 形成新 Attempt → reload read-back`。Learn 不要求筆記或輸出；Practice 使用獨立頁面與 state，不沿用三視圖 selection。OS `Interrupt → Driver` 爭議主張以 overlay 封鎖出題而不改 Source；P0 完成以實際 route、持久化、answer-leak regression 與 browser smoke 為準，不以 schema 數量或 Graph 功能替代。

> 2026-09-20 Morning beta checkpoint（歷史 checkpoint，已被 requirements-led convergence 排程 supersede）：P0 已延伸成資料驅動的兩單元 catalog（OS、BitePacer），同一 renderer 提供遞迴 Learning Structure、Reader、按需 Reading Assist 與 scope-local reviewed graph。Practice 現有 relation recall、free explanation、application/prediction、distinction；提交後的 learner self-assessment／dispute correction 以 append-only feedback 保存，不改寫 Attempt。Due Queue 使用可解釋的 1／3／7／21 天 prototype milestones；Due identity 與 Attempt identity 分離，只有 matching scheduled-review Attempt 推進排程，snooze／skip／stop 不建立 Attempt。首頁提供跨單元 continuity，零筆記仍可接續。這是可用性與工程 beta，不宣稱學習效果、mastery 或最佳排程；尤其不代表 `KG-SOAK-01` 或 `KG-MEM-01` 已完成。

### Morning beta 驗收記錄（2026-09-20）

- `home.html → learn.html?unit=... → practice.html?unit=... → review.html` 已以本機 server 實際走通；catalog 由 `web/fixtures/learning-units.json` 驅動，不複製第二套 renderer。
- Learning Structure 是 view-level hierarchy；node 保留 stable ID、parent、order、source anchors、revision、provenance 與 organizing relation，階層不回寫 canonical Edge。
- OS PID 在 L18 提供 `required_depth: define` 的 external Context Gloss 與明示 synthetic prior link；DMA 沒有因同份教材重複出現而自動成為 glossary 項目。
- Disputed `Interrupt → Driver` 仍顯示原文與警示，但從 Practice 與 trusted Local Graph 排除。
- 219 個 Python tests 與 45 個 Web tests 通過；browser smoke 實走兩單元 catalog、OS structure／PID gloss、application Attempt、feedback read-back、Due Queue，並檢查 BitePacer iPad viewport 與 console。
- 已知限制：Context Gloss／prior links 目前是 reviewed fixture，尚無 live AI 或跨來源自動檢索；scheduler 是固定 prototype heuristic；Local Graph 是文字化 scope projection，尚未做更豐富的 touch canvas；長期 7／21 天效果尚未發生。
- 下一個最合理切片：用真實回訪資料驗證 continuity／due recovery，並在不改變內容與練習的前提下比較 baseline 與可選 Local Graph。

### Requirements-led convergence 驗收記錄（2026-09-20）

- Loop 1 (`KG-SOAK-01,04–05`; `SC-02,18`)：獨立 Soak route 與 append-only ExposureEvent；揭露／跳過不建立 Attempt、outcome 或 debt。
- Loop 2 (`KG-MEM-01`; `SC-03`)：精確保存 source scope、遞迴 breadcrumb、selection、未解問題及最近 Attempt／Exposure；重開可回到原位置。
- Loop 3 (`KG-CTX-03`, `KG-SOAK-02–03`, `KG-SRS-03`, `KG-PLAT-06`; `SC-08,10,12,16,17,20,22,24,30,31`)：context-local depth、fixture-specific support progression、non-scoring exposure signal、confusion-first prompt、真實跨單元 event 投影、派生功能獨立降級、併發寫入與 durability regression。
- Architecture／failure／mutation audit 分別記於 `docs/requirements/ARCHITECTURE_AUDIT.md`、`FAILURE_MATRIX.md`、`MUTATION_REVIEW.md`；它們不取代 canonical ledger。
- 最終工程證據：requirements guard 84／37 structural PASS，guard tests 16、Python 238、Web 54、`git diff --check` PASS；Browser Journeys A／B／C 與 server-restart read-back 通過。這些不等於人工學習效果或全部 84 條需求完成。
- 台帳現況：34 `automated_verified`、40 `partial`、10 `not_implemented`；scenario 為 10 `automated_pass`、8 `automated_partial`、19 `not_run`。後兩類不得在回報中冒稱完成。

## 一句話目標

先驗證「一段陌生材料能否讓使用者直接閱讀、取得有來源的結構化導讀，並針對重要內容或不理解處取得摘要、拆解、例子與對比；當使用者選擇練習時，系統能否接住適合的活動、給出具體回饋，並讓之後的學習延續」。閱讀、追問、練習、回看來源與結束 session 可以自由往返；筆記不是開始學習、建題或複習的前置條件。

## 不可變的產品原則

- 長文與原始對話是 evidence，不是要被圖取代的垃圾。
- Source／Evidence 表示「材料說了什麼」，不自動表示該主張已被外部查核、可成為標準答案；原文勘誤另存，不覆寫 source bytes。
- 核心產品產物是可延續的學習脈絡：看過的材料與導讀、提出的問題、對應解說與來源、選擇過的練習、實際回答、暴露的缺口與修正歷史。LearningNote 是其中一種可選、可修訂、可追溯的整理形式，不是啟動學習的門票。
- 閱讀、解說、練習、回饋與回看來源是可往返的活動，不是固定關卡。一次 session 可以只閱讀或追問後結束；不同主題可同時處於不同活動狀態。
- 系統化不等於必須由使用者先自行整理。教材、人工編寫或 AI 可以先提供結構；AI 整理的解說是學習材料，使用者的回答才是該任務上的表現 evidence。沒有改寫 AI 內容不能被判成沒有學習。
- 依任務選擇 outline、流程、對照表、argument map、atomic note、局部 concept graph 或 question set；不得把所有內容強壓成兩個 Concept 加一條短 phrase。
- edge 是導覽索引；完整 claim 必須能表達條件、角色、範圍與例外，proposition/evidence 才是回看時的完整上下文。
- Reader、筆記／Map 與 Graph 共用相同 identity、主張方向、審查狀態與 provenance；一致性不等於三個視圖必須顯示相同集合、相同字長或相同抽象層級。
- 章節階層與教學 grouping 負責閱讀順序，不因出現在地圖中就成為新的 Concept 或知識 Edge。
- 草稿、自我解釋、問題與不確定可以保存，但不因保存就污染 canonical knowledge；AI 結構預設是 proposal。
- 圖可以不完整。不確定的關係允許留白或 `related_to`。
- `related_to` 不足以支持精確因果、依賴、防止或機制推論；精確 learner-facing claim、條件與 review status 必須可查詢。
- 學習重要性由使用者目的作最終決定；AI、教材結構、錯誤頻率與 graph centrality 只能提出理由。每個候選先分為「需要能自行解釋／只需知道去哪裡查／目前不處理」。
- 閉卷 attempt 必須與瀏覽 selection 分離；提交前記錄答案是否可見、提示使用與 client-generated attempt ID，允許「不知道」、錯誤、申覆與後續修訂。
- 學習狀態用可追溯的行為 evidence 表示，不用「理解 73%」。
- 一個 engine 支援多個 space/notebook，且允許跨 space 關係；不為每個學科建新 App。
- Git 可追蹤的 Markdown／YAML store 才是 v0 authoritative data；Obsidian 是人工閱讀／允許範圍內的編輯器與導覽器，Web 是主要工作介面。Source、LearningNote 與 machine-managed Claim／Attempt 的寫入權、revision 與外部修改偵測必須各自明訂；LINE/LIFF 若採用也只是入口。

## 2026-09-19 審查後的產品裁決

`docs/chatgpt_6pro_20260919_review.txt` 是本輪變更的設計輸入，不把其中每個推論自動當成已驗證事實。審查沒有執行完整 repository E2E 或實體 iPad 驗收，所以程式層發現仍須在 Phase 3c-0 逐項重現；但其指出的產品風險已足以改變 roadmap 的驗收中心：

> 從「三個畫面是否忠實顯示同一份知識」改為「使用者是否形成可修訂的理解，以及隔一段時間後能否提取、解釋與應用」。

### 保留、降級與停止假定

| 處置 | 內容 | 後續要求 |
| --- | --- | --- |
| 保留 | immutable Source、Evidence locator、stable Concept identity、Concept Graph／Learning Overlay 分離、append-only history、dry-run／idempotency | 繼續作所有工作區與實驗的共同資料基礎 |
| 補強 | provenance、Teaching Proposition、review persistence | 額外區分來源支持與事實／教學審查；補 attempt identity、答案可見狀態、回饋修訂與重送冪等 |
| 降級為工具 | Reader、Guided Map、Exploration Graph | 由任務工作區按需組合，不再要求使用者理解或依序走完三個 tab |
| 降級為待證偽假說 | `Reader → Map → linking phrase → Graph` 固定路徑、Graph 對 outline 的學習增益 | 必須與內容、時間、練習、回饋相同的非 Graph baseline 比較 |
| 刪除的前提 | Map／Graph 全量集合相等、所有重要內容都能由 Concept／Edge 表示、projector 可直接升級為 `canonical/high`、Graph 必為最後一層 | 改由 view scope、claim review 與任務結果驗證 |
| 暫緩 | 大型 compound graph、3D、複雜動畫、自動 community detection、全圖自動精緻化、全域 mastery、centrality 選重要概念、複雜自適應排程 | 先取得可靠的學習脈絡、問題／解說 provenance、可選 LearningNote、活動類型、Attempt、錯誤與延遲表現資料 |

### 新資訊架構：上層導航是工作，不是表徵

```text
學習工作區
  ├─ 閱讀原文／結構化導讀
  ├─ 針對重要內容或疑問取得摘要／拆解／例子／對比
  ├─ 繼續閱讀／追問／回看來源／收藏解說／先結束
  ├─ 使用者選擇時進入模仿／部分完成／填空／回憶／解釋／應用
  ├─ 取得具體回饋，再回到解說、來源、其他練習或之後再來
  └─ 可選筆記、問題、勘誤與局部關係探索
```

預設入口依當前任務，而非 `beginner / intermediate / expert` 人格標籤：陌生材料預設先提供原文與結構化導讀；使用者可以直接追問、繼續讀、先結束，或主動選擇一個練習。已有印象的內容可以從問題或練習開始；到期複習可以直接進入對應活動；比較兩份材料先用對照解說，需要追蹤多步關係才開 Graph。任何入口都不是理解程度宣稱或下一步鎖。

### 2026-09-19 首次 H0 中止 finding：note-first 不符合使用意圖，不能推出替代流程已有效

真正陌生的 BitePacer P4 backup micro-source 通過前測（`0`），但在普通 Markdown 條件剛開始、尚未產生任何使用者筆記前即由使用者中止。唯一足以由本事件確認的是：使用者不接受「先自行整理筆記」作為陌生材料的預設入口，現有 protocol 與使用意圖不一致。這不表示使用者當時沒有能力整理、不表示自行整理在所有時點無效，也不證明任何替代順序具有較佳學習效果。

因此本 run 記為 `aborted → modify`，不計整理時間、rubric、lookup、無工具回答或任何優劣分數；空白筆記不是失敗資料。原 H0 manifest 保留為 protocol provenance，不事後改寫。後續決策如下：

- 預設入口改為來源閱讀、結構化導讀與針對疑問的解說，不打開空白 note editor 要求產出，也不改成先考試。
- 使用者可以選擇繼續讀、換一種解說、追問、先結束或進入練習；這些是導航選擇，不是必須依序通過的 readiness gate。
- 模仿、部分完成、填空、白紙回想、解釋與應用都是合法活動。有支援的練習不是失敗版本的閉卷測驗；系統應記錄材料／提示是否可見，只在活動本來要求無輔助回憶時隔離答案。
- LearningNote 保留為可選的摘錄、自己的整理、錯誤修正與日後回找工具；未建立筆記也能完成整個學習閉環。
- live AI 尚未有資料邊界與明確同意前，以人工預備的重點／解說驗證流程；日後 AI 可依使用者的目的、重要性或困惑提供摘要、展開、例子與對比，但不得把生成內容當成使用者學會的 evidence。
- 新 baseline 比較使用者實際採用的「閱讀＋AI 解說」方式與 KGnote 支援的同類工作流；兩邊都不強迫先寫筆記或立即練習。

#### 需求澄清：先前混在一起的三件事必須拆開

「陌生資訊變成系統性筆記」描述的是產品要協助保留的結構與脈絡，不等於指定使用者必須先親手整理。先前外部審查把「學習者參與理解建構」過度轉譯為「核心活動是自行產出結構化筆記」，Codex 又把撤掉 note-first 過度轉譯為接近 retrieval-first 的流程；兩個推論都撤回。後續不得要求使用者去適應由 roadmap 自行加入的學習順序。

| 層次 | 真正要保存／觀察的內容 | 是否要求使用者一開始親自產出 | KGnote 的責任 |
| --- | --- | --- | --- |
| 資訊被系統化 | 主題、脈絡、重點、為何重要、解說與來源，之後找得到 | 不要求；教材、人工編寫或 AI／系統可先提供 | 提供結構化導讀與 provenance；不冒充原文或已理解 |
| 使用者形成理解 | 逐漸知道概念在說什麼、如何連接、哪裡仍不懂 | 是學習過程，但不要求立即留下正式筆記或完成固定操作 | 允許閱讀、追問、換例子、對比與回看來源；保存問題與尚待確認處 |
| 使用者輸出可觀察表現 | 模仿、部分完成、填空、回憶、解釋、區辨、作答與應用 | 可稍後、可選擇進入，也不必以整理筆記呈現 | 依活動保存支援／曝光狀態、raw response 與回饋；未進入不算零分 |

這三層共享 Source／Evidence／Concept identity，但不能互相代算：AI 完成系統化不代表使用者已理解；使用者沒有改寫 AI 導讀也不代表沒有學習；閱讀過、覺得熟悉或看懂範例，不自動等於之後能無輔助提取；未選練習更不是錯誤回答。

#### H0 的推論邊界

| 這次事件足以支持 | 這次事件不能支持 |
| --- | --- |
| product owner 明確不接受「先自行整理筆記」作為陌生材料的預設入口 | product owner 當時在認知上沒有能力整理 |
| 現有 note-first 任務與個人產品的使用意圖不一致 | 自行整理筆記在所有學習時點都無效 |
| 個人產品可依明示需求直接修改預設，不必先用實驗取得不寫筆記的許可 | 先閱讀、先解說或任何新順序已被證明最有效 |
| 這個 run 不適合比較預期的可用性或學習成效，應中止且不評分 | 新工作流已通過驗證、Graph 價值已被推翻，或 retrieval 應成為新入口 |

因此要分清楚「現在不想以此活動開始」與「現在做不到」。H0 保留前測、已曝光材料、開始／中止時間與反對理由；不補造 rubric、lookup、unaided response、confidence 或分數。這是需求／protocol finding，不是學習效果 finding。

#### 學習科學只作設計依據，不替 KGnote 背書

- Renkl、Atkinson、Maier 與 Staley（2002）在 worked-example／problem-solving 情境中比較逐步撤去解題步驟與傳統 example-problem pairs；結果支持在其測試條件下由完整範例逐步增加獨立解題，至少改善 near transfer。這使「先有支援，再逐步增加輸出」成為合理候選設計，但不能外推成 KGnote 的 AI 閱讀流程已有效，也不要求每位學習者走同一 fading sequence。來源：[From example study to problem solving](https://doi.org/10.1080/00220970209599510)。
- Bisra 等人（2018）的 meta-analysis 將 self-explanation 定義為學習者產生因果連接或概念關係的推論，納入 64 份研究報告、69 個 effect sizes；這支持把「自己說一次／說明原因」保留為可選學習活動，不支持把正式筆記或 outline 當成唯一生成加工。來源：[Inducing Self-Explanation](https://doi.org/10.1007/s10648-018-9434-x)。
- Roediger 與 Karpicke（2006）的文本實驗中，重讀在 5 分鐘測驗較佳，先前提取則在 2 天／1 週延遲測驗保留較佳，且重讀提高記憶信心。這支持分開觀察「讀起來熟悉」與「之後能提取」，不支持陌生材料必須從測驗開始。來源：[Test-Enhanced Learning](https://doi.org/10.1111/j.1467-9280.2006.01693.x)。
- Agarwal、Nunes 與 Blunt（2021）的課堂研究系統性回顧納入 50 個 experiments、49 個 effect sizes，發現 retrieval practice 在多種教育條件下多有益，但研究範圍與樣本限制仍存在。這支持日後提供經選擇的 retrieval／application 活動，不支持把它變成所有 session 的入口或資格門檻。來源：[Retrieval Practice Consistently Benefits Student Learning](https://doi.org/10.1007/s10648-021-09595-9)。

保留的設計提醒是：熟悉感與可提取表現不可混稱，之後仍應在事先同意的時點觀察解釋、區辨與應用；撤回的是「為了主動學習，所以必須先寫筆記」以及「不先寫筆記，所以應先做 retrieval」兩個產品推論。

#### 原 Phase 3c 主張逐項撤回／替換

| 原主張或驗收 | 處置 | 新約束 |
| --- | --- | --- |
| 核心學習產物是使用者形成的結構化筆記 | 撤回 | 核心是可延續的學習脈絡與之後實際發生的理解／提取／應用 evidence；筆記只是可選產物 |
| Baseline 以可編輯 outline 與自己的解釋為中心 | 替換 | Baseline 以閱讀、結構化導讀、針對疑問的解說與可選練習為中心 |
| 每個主題都要求使用者選擇、組織或修訂 | 撤回配額／關卡 | 支援這些操作，但不以操作次數或交作業作為繼續閱讀、取得解說、建題或複習的條件 |
| 答錯後必須先修訂 NoteBlock 再測 | 撤回 | 可以回看解說、換例子、澄清疑問、選擇修訂筆記、稍後再試或暫停 |
| LearningTarget 必須從使用者筆記產生 | 撤回 | 可直接來自 Source／reviewed Claim、教學重點、使用者問題或可選 LearningNote |
| 第一週優先驗證筆記 editor／note formation | 替換 | 第一週優先驗證：不自行整理筆記也能閱讀、取得解說、按選擇進入活動並在下次續接 |
| 跨視圖一致表示 AI 不可對同一概念換說法 | 明確禁止此誤用 | identity、claim、方向與來源一致；摘要、展開、例子、對比是另存 provenance 的派生解說，不必修改 canonical graph，也不得偷改 claim |

保留而不受此次澄清推翻的工程要求包括：Source／Evidence 追溯、內容勘誤與 teaching-answer gate、瀏覽與練習狀態分離、活動／提示／答案曝光紀錄、錯誤與 confusion 歷史、後續複習、Graph scope／群組語意，以及 write precondition／idempotency／recovery。

#### 下一次 formative test 只先觀察三件事

下一次不重跑「先完成一份筆記」，也不改成「現在先閉卷回答」。選一段 product owner 確實想了解、前測確認陌生的新材料，讓她用閱讀、追問、摘要與解說建立輪廓；只有她選擇活動時才進入，回饋後可返回相應解說／來源。主要觀察：

1. **能否順利學進去：**是否能直接針對不懂處取得合適解說，而非一直被要求填表、改 outline、交筆記或先答題。
2. **能否依意圖在閱讀與活動間切換：**選「我想試著說一次」時真的提供輸入；選「再解釋一次」時停止逼問並換種解說；選「先結束」時不建立零分或假 Attempt。
3. **能否延續學習：**下次能否找到上次來源位置、問題、看過的解說與尚待確認處，不必重建整段上下文。

比較對象是 product owner 實際使用的「閱讀＋AI 解說」方式，不是普通 Markdown／手寫筆記。未進入活動不評分；進入後的實際錯誤連同 activity type、support／exposure state 與 feedback 保存為有意義的學習 evidence。這輪只能驗證流程是否接住使用意圖；學習效果、延遲保持、Graph 增益與不同活動的因果效果仍須各自另測。

## 當前最高優先：Phase 3c 可延續的閱讀、解說與練習工作區

下一個最小可驗收 prototype 不是重做整套三視圖，而是：

```text
明確選定的來源片段＋使用目的
  ↔ 閱讀原文或結構化導讀
  ↔ 依重要內容／疑問查看摘要、拆解、例子或對比
  ↔ 追問、回看來源、收藏解說、可選筆記或先結束
  ↔ 使用者選擇模仿、部分完成、填空、回憶、解釋或應用
  ↔ 取得 Evidence／rubric 支持的回饋，再讀、換例、重試或之後繼續
```

同一份內容提供兩個可公平比較的版本：

- **Baseline：**來源閱讀＋結構化導讀＋按需解說＋可選練習與 Evidence 回饋＋可延續的學習脈絡；筆記可選，練習也不是每次 session 必做。
- **Graph variant：**保留完全相同的內容、解說、輸出活動、回饋與可選筆記，只多提供主題內局部關係及按需跨界展開。

Graph variant 只有在預先指定的關係追蹤、跨來源整合或衝突／條件比較任務中呈現額外收益，才可升回核心路徑；否則維持可選實驗功能。

### 執行方式：Phase 3c-0～3c-8 是能力軌，不是全數串行的 release gate

後續開工使用三種獨立閘門，不等待整個 Phase 3c 全部完成：

| 閘門 | 必須先通過 | 通過後可做 | 不必等待 |
| --- | --- | --- | --- |
| 工程／資料安全閘門 | 受測材料的 claim 可否作答已明確；write precondition、活動／支援／答案曝光與 idempotency 可驗證 | 保存真實 LearningContext、可選 LearningNote 與實際發生的 Attempt | 全部 Graph、7／21 天結果 |
| Formative 可用性閘門 | 無 Graph／無 live AI 也能閱讀、取得人工預備解說、追問或先結束；選擇練習時能進入相符活動並取得回饋；下次可續接問題與解說。不建立筆記、不進入練習仍是合法 session | 立即做陌生材料流程測試；另行驗收可選筆記保存 | Graph variant、所有練習形式、長期效果 |
| 學習效果／Graph 投資閘門 | 有事先寫好的 task manifest、公平版本與對應指標 | 只測該假說並作繼續／修改／停止決定 | H1～H5 全部跑完 |

停止條件只停用受影響的材料或功能。例如 OS 爭議 claim 會阻止它成為標準答案，但不阻止使用已審核的來源測 Reader、解說脈絡或可選筆記保存；Graph 方向誤讀會停止 Graph variant，不停止非 Graph 工作區。

### 下一批可直接交給 Codex 的垂直工單

以下工單已有目的、修改範圍、非目標與結案證據；開工時一次只取一張，不把整個 Epic 當單一工單。

#### 3c-S0：修正 Evidence → 多 Claim 的反向選取

| 項目 | 已決定內容 |
| --- | --- |
| 對應 finding | `selectEvidence()` 用 `.find()` 任意選第一條 Proposition；真正缺口是 Evidence 反向對應多條 Claim，不是 Claim 正向只顯示一筆 Evidence |
| 修改範圍 | `web/learning-workspace.js`、`web/guided-map-app.js`、`web/tests/guided-map.test.js`、`web/tests/os-workspace.test.js` |
| 預期行為 | Evidence 本身可保持焦點；回傳全部 `candidate_edge_ids`。唯一對應可提供直接進入 Claim 的動作，多個對應由使用者選，零對應仍可閱讀合法 Evidence |
| 負向／穩定性 | 不依 propositions 陣列順序選焦點；反轉順序後候選集合與 selection 語意完全相同；unknown Evidence 仍 fail closed |
| 不做 | 不改 layout、ontology、Source bytes、Concept／Edge IDs 或 canonical store |
| 結案證據 | `npm test`；OS `evidence_os_scheduling` 顯示兩個候選；Reader 實際選取；canonical diff 為零 |
| 回退 | 純 read-model／UI 行為修改，無資料 migration；若新 selection 無法 render，feature flag 回舊唯讀 selection，不寫入任何新狀態 |

#### 3c-S1：OS 爭議 Claim 隔離與舊 Guided Map 相容

| 項目 | 已決定內容 |
| --- | --- |
| 對應 finding | 直接把 `review_status` 改成 `needs_revision` 會被舊 schema／JS validator 拒絕；schema 接受 `corrected`，JS 卻只接受 `accepted` |
| 短期策略 | 新增 snapshot-bound、以現有 `edge_id + proposition digest` 定位的獨立 `ClaimReviewOverlay`；不先把新 factual status 塞進舊 Guided Map fixture。分別保存 `source_evidence_review_status: accepted`、`source_support: supported`、`factual_status: needs_revision`、`teaching_answer_status: blocked`；正式 Claim v1 後再 migration preview |
| 修改範圍 | `schemas/claim-review-overlay/v1/`、`web/fixtures/os-overview-claim-review-overlay.json`、`web/guided-map.js`、`web/learning-workspace.js`、OS tests；review UI 顯示警示與理由 |
| 預期行為 | 問題 Source／Evidence 仍可閱讀；受影響 Claim 不得建立 exercise／ReviewItem／due item；未受影響內容仍 ready |
| 相容性 | 修正 JS validator 與既有 schema 的 `accepted | corrected` 差異；宣告需要 overlay 的 learning unit 在 overlay 缺失時只保留 Reader／舊唯讀內容，practice gate fail closed，不得猜 factual status 或宣稱已外部查核 |
| 負向／復原 | malformed／stale overlay fail closed 於 review／practice 功能，但 Reader 仍可用；移除 overlay 即回到舊唯讀 fixture，無 Source mutation |
| 結案證據 | `npm test`、`scripts/run_tests.sh`、OS UI smoke；被隔離 edge 不出現在題目清單，Source hash 不變 |

#### 3c-W0：無 Graph、無 live AI 的閱讀／解說／練習工作區

| 項目 | 已決定內容 |
| --- | --- |
| 使用案例 | 真正陌生的短來源先供閱讀與結構化導讀；使用者可按重點或困惑查看人工預備的摘要／拆解／例子／對比，追問、回原文、先結束，或選擇一個練習 |
| 最薄互動 | `source／導讀 ↔ 解說選項 ↔ 追問／回來源／先結束`；另提供兩個不互相冒充的入口：`再解釋一次` 只回到解說，`我想試著說一次` 才開啟 teach-back 輸入與回饋 |
| 修改範圍 | source Reader、預備 explanation read model、問題／解說／來源的 session context、活動選擇器、teach-back UI 與只有實際提交才建立的最小 Attempt record；沿用 immutable Source／Evidence 與既有安全邊界 |
| 學習脈絡 | 保存目前材料與位置、使用者問題、看過的解說及其 provenance、尚待確認的問題、實際選擇的練習與結果；下次能續接，不要求先產生 LearningNote |
| 筆記角色 | LearningNote route 與 editor 保留為「收藏／補自己的話／之後整理／修正」；無筆記、未練習或只讀後離開都能正常結束 session，不以 note bytes 或操作次數作 completion gate |
| 活動語意 | v0 先實作 `再解釋一次` 與一種 teach-back，不宣稱涵蓋所有模式；後續保留 imitation／partial completion／cloze／free recall／explanation／application 類型。有支援的活動記為正常 guided practice，不標成失敗的 retrieval |
| AI 邊界 | v0 用人工預備、source-grounded 解說；live AI、外送與效果宣稱不在本工單。未來 adapter 必須有目的／困惑範圍、consent、redaction、provenance 與原文回鏈；摘要、展開、例子與對比可以換說法，但不得偷改 canonical claim |
| 表現邊界 | 只有使用者實際進入並提交活動才產生表現紀錄；材料、答案、範例、提示是否可見必須依活動類型保存。teach-back 可以允許參考材料或選擇無輔助，兩者都合法但不可混稱 |
| 正負向驗收 | 選 `再解釋一次` 不出題；選 `先結束` 不建立 Attempt 或零分；選 `我想試著說一次` 真的提供輸入而不是再送摘要；提交後顯示具體缺口並可回到對應解說／來源；reload 能找回問題與尚待確認處 |
| 結案證據 | 一份新陌生 micro-source 的完整 read-back；零 LearningNote、零練習的閱讀 session 合法；有支援與無輔助活動不混標；中途離開不誤記 Attempt；`npm test`、`scripts/run_tests.sh`、Mac／iPad render 與 Source hash 不變 |

#### 3c-B0：可選的無 Graph、無 live AI versioned Markdown LearningNote

| 項目 | 已決定內容 |
| --- | --- |
| 使用案例 | 在空 notebook、零 canonical Concept／Edge／Teaching Proposition 時，使用者主動選擇後才編輯結構化筆記、保存、重開、回來源並留下可選的不確定；不是陌生材料的預設第一步 |
| v1 筆記形狀 | 每個 learning unit 一份 `LearningNote` Markdown document；結構只用 headings／lists／paragraphs。front matter 的 `source_anchors` 只保存 stable anchor ID、Source ID、locator 與 label，作 note-level 回源入口，不綁易變 heading。此次不做 block-level merge／split、拖曳樹、argument-map editor 或五種專用編輯器 |
| 修改範圍 | 新 `schemas/learning-note/v1/`、`src/kgnote/notes/` application／store boundary、`scripts/serve_graph_view.py` 的 bounded notes routes、`web/learning-note.*` 與對應 Python／Web tests |
| 使用者要求 | 用途／問題可沿用或稍後補；系統必須提供 explanation／question／uncertainty 能力，但不強迫每篇、每主題產生固定數量 |
| lookup | notebook-scoped 的確定性文字搜尋：title／headings／body／source-anchor label；回傳 note、heading、snippet 與來源入口，不做 embedding／全庫搜尋平台 |
| AI 邊界 | 使用人工預備 proposal 或完全不用 AI 均可跑通；live model、外送、AI 效果宣稱不在本工單 |
| storage ownership | `notes/` 是人類可讀／可編輯的權威 LearningNote；Source 不可改；ClaimReview／Attempt 等 machine-managed records 只能經 adapter 寫入。外部修改以 bytes digest／ETag 偵測 |
| 寫入安全 | 強 ETag／`If-Match` precondition、atomic write、server-generated new revision、client `save_id` 冪等；stale save 回 conflict 並保留使用者文字，不靜默覆寫 |
| 復原測試 | response 遺失後同 payload 重送讀回同一 revision；同 save ID 不同內容 conflict；write failure 不顯示成功；失敗前版本仍可 read-back |
| render 安全 | v1 禁止 raw HTML 與外部圖片自動載入；Markdown 只 render 明確 allowlist，URL scheme 驗證與 sanitization 另測，CSP 不作唯一防線 |
| iPad 驗收 | 中文輸入法、鍵盤可完成 headings／lists、無 drag 的重排替代操作、保存後 reload、conflict 文字不遺失 |
| 結案證據 | `npm test`、`scripts/run_tests.sh`、versioned fixtures、HTTP 正負向與復原 tests、Mac／iPad render、Source／canonical graph diff 為零 |
| 回退 | feature flag 關閉 notes write routes 後仍可讀 Source／舊三視圖；已成功保存的 Markdown 不刪除，舊版只把未知欄位標為 unsupported |

#### 3c-B1：一個 LearningTarget 的 Attempt／due 垂直閉環

| 項目 | 已決定內容 |
| --- | --- |
| 依賴 | 3c-S1 的 teaching-answer gate；最小 Claim／ReviewItem／Attempt contract；不依賴 Graph、Gemini 或完整 scheduler |
| 修改範圍 | 新 Claim／ReviewItem／Attempt／due schemas 與 `src/kgnote/review/` application boundary、bounded HTTP routes、獨立作答 UI、對應 Python／Web tests |
| 生命週期 | due 只產生待辦資格；使用者開始才建立 Attempt；輸入為 draft；submit／不知道形成結果；cancel 與未開始不是錯誤回答；再試建立新 Attempt |
| 輔助狀態 | 活動類型另存；支援狀態至少區分 `modeled | reference_visible | guided | hinted | unassisted | answer_revealed | unknown_legacy`。題目必需 context 由 ReviewItem 明訂；只有活動本來要求無輔助回憶時，答案／來源可見才算 reveal。只記錄 KGnote 介面可觀測曝光，不宣稱監控其他分頁／紙本 |
| 冪等與衝突 | 同 attempt ID＋同 payload 重送讀回同一結果；同 ID 不同提交 conflict；完整答案揭露後仍可保存回答，但不得標為 unassisted retrieval |
| schedule v1 | 首次有效 submit 時建立 anchor；第 1／3／7／21 天是相對該 anchor 的絕對 milestones，不作累加間隔。每個 Target 保存 `scheduler_timezone`（v1 預設明示 `Asia/Taipei`），`due_at` 存 RFC 3339 UTC、以該時區同一 wall-clock 計算。逾期只顯示最早未完成 milestone，不回填假 Attempt |
| 狀態變化 | snooze 明記新日期與理由；skip 只跳過該 milestone；ReviewItem／Claim revision 變更即 suspend；`remember → lookup` 取消未來 due，歷史保留 |
| 結案證據 | `npm test`、`scripts/run_tests.sh`、injected clock tests、首次 submit→due→start→hint／reveal→submit→revision suspend→resume read-back；無 mastery 分數 |

#### 3c-X0：在任何 Graph variant 前建立 formative test manifest

| 項目 | 已決定內容 |
| --- | --- |
| manifest | Source ID／revision／range、已審核 claims、任務、條件、起始狀態、rubric、主要指標、排除／中止、決策規則 |
| 修改範圍 | `experiments/manifests/` 的 versioned YAML schema／fixture、人工紀錄模板與 read-back validator；不先建通用 analytics 平台 |
| 第一個比較 | 原 note-first H0 已中止且不評分；替代 H0-W 比較 product owner 現有「閱讀＋AI 解說」與 KGnote 無 Graph 的閱讀／導讀／按需解說／可選練習工作區。分開看能否學進去、能否依選擇在解說與練習間切換、能否續接脈絡、操作摩擦與可選筆記價值 |
| rubric | 接受不同組織方式；評分關鍵內容、關係／條件、來源與可回找性，不要求複製 expert fixture 的群組 |
| 指標選擇 | 每個 manifest 只列與假說有關的主要指標；熟悉材料 UI 測試不等 7／21 天。H5 若一起測 retrieval＋feedback＋spacing，結論只適用整套方案 |
| 公平性 | H1 兩組先使用相同箭頭／遮擋修正；材料、額外資訊與回饋相同。BitePacer 熟悉度每次由 pretest 決定，不永久標為低熟悉 |
| Graph 進場 | baseline 已通過 formative gate，且 manifest 已指定一項非 Graph 不易完成的關係任務，才建立 Graph variant |
| 結案證據 | manifest schema／malformed tests、rubric dry-run、一次 H0 N=1 read-back；`scripts/run_tests.sh` 與 `git diff --check` |

每張後續工單沿用：`目的／finding → 相依與已決定邊界 → 修改模組 → 明確不做 → 正向、負向、復原驗收 → 測試命令與實機證據 → 回退方式`。不要求現在把 Phase 3c 全部拆成數百張票。

### Phase 3c-0：重現審查發現與立即安全閘門

這一切片先修「可能教錯」與「把看答案誤算成提取」，完成前不進行任何學習效果比較。

- [ ] 建立 `審查 finding → 程式位置 → 可重現步驟 → 修正狀態 → regression test` 清單；逐項核對 OS 工作區，而不是只照抄外部審查結論。
- [x] 先完成 3c-S0，正確處理 Evidence→多 Claim 反向選取；同時保留 Claim→全部 Evidence 的正向查詢，兩者分別驗收。
- [x] 以 3c-S1 的獨立 overlay 隔離 OS driver／interrupt handler 主張，不直接把 `needs_revision` 寫進舊 Guided Map 欄位；保留原文、原 locator 與「來源確實這樣寫」，另存 factual review、答案封鎖、勘誤依據與審查者。
- [ ] 人工重審 OS 的 10 條 Teaching Propositions 與 supporting Evidence，區分「來源確實這樣說」「主張已查核」「可作教學答案」三種不同狀態；有爭議、證據不足或語意過度壓縮者不得進 ReviewItem。
- [x] 隔離作答 session：區分題目必需 context、使用者主動要求的 hint、非預期 answer leak 與完整 answer reveal；切換離開作答要明確中止或保留 session，不可在已 reveal 後仍標成 `unassisted`。
- [x] 提供「不知道／跳過」並無條件保存原始錯誤回答；不得只保存成功或逐字吻合的回答。
- [x] 依 3c-B1 以 client-generated stable `attempt_id` 加 item revision／idempotency key 去除同一次網路重送；server timestamp 只記時間，不再決定嘗試身分。
- [x] `view_context` 由實際入口與 task context 產生，不固定寫成 `guided_map`；瀏覽 selection 不得重設正在作答的題目或 response。
- [x] 建立 exposure regression matrix，至少覆蓋直接文字、ARIA／隱藏 DOM、Graph label、Reader excerpt、切換視圖、reload、required context、hint、answer reveal 與 stale selection；系統只對本介面可觀測狀態負責。

完成條件：OS 問題主張不再可被排入複習，未受影響的 Source／內容仍可讀；Attempt 能明確區分 activity type 與 modeled／reference-visible／guided／hinted／unassisted／answer-revealed；相同 `attempt_id` 重送只讀回同一筆紀錄。失敗只停止受影響的題目／材料／功能，不自動阻塞已通過安全閘門的閱讀／解說／可選練習工作區或可選筆記。

### Phase 3c-1：修訂 contract、資料模型與向後相容遷移

這是按垂直工單取用的 contract 能力軌，不要求先一次完成所有 record。每張工單只先定義它真正要寫入／讀取的最小 contract、fixture 與 migration preview，不直接批量改 canonical store。

- [ ] 更新 `docs/PRODUCT_CONTRACT.md`：正式採兩個工作迴圈與任務式入口；三視圖改為可選工具；分開驗收「開著工具完成任務」與「關掉工具仍能完成指定表現」；將「Obsidian 是 source of truth」改為各 Markdown／YAML 目錄與 writer ownership／external-edit detection 的精確規則。
- [ ] 更新 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`：共同 identity／claim／provenance 不代表相同 collection；允許經審查的短標籤、全稱與條件展開；Graph／Map 各自驗證 scope。
- [ ] 更新 `docs/DATA_MODEL.md`：明確區分 Source claim、fact／teaching review、canonical knowledge 與 learner draft；禁止 renderer／projector 自行把 confidence 或 edge class 升級。
- [ ] 更新 `docs/REFERENCE_SOURCES.md`：收錄本次審查實際使用的 R1–R29，逐項標明是直接研究學習活動、相鄰 HCI／理論證據或標準；不得用單篇／搜尋摘要替 KGnote 完整流程背書，Pi et al. 2026 未取得足夠方法／結果前不寫效果結論。
- [ ] 建立名詞與 UI label 對照：outline／mind map／concept map／argument map／knowledge graph 各依其實際結構與任務命名，不再用「學習地圖／知識地圖」籠統混稱不同介入活動。
- [ ] 定義 versioned `Claim`：stable `claim_id`＋revision、statement、條件／角色／範圍／例外、Evidence refs、可選 Edge refs 與 review status。Claim 可獨立於二元 Edge；同一 Edge 可有不同條件下的多個 Claim，ReviewItem 一律綁定 `claim_id + revision`，不能只綁 Edge ID。
- [ ] 定義 `ClaimReview／Erratum`：只記「誰在何時、依什麼資料、如何評價哪個 Claim revision」及 correction／外部查核依據；`source_support`、factual review 與 teaching-answer readiness 分開，不把 Claim 內容的條件／角色／範圍只藏在 review record，也不得修改 Source bytes。
- [ ] Claim review v1 狀態固定為：`source_support: supported | unsupported | unknown`、`factual_status: unreviewed | needs_revision | verified | corrected | rejected | insufficient_evidence`、`teaching_answer_status: candidate | ready | blocked | retired`。狀態變更 append 新 review；只有 `verified | corrected` 且有合格 Evidence 可進 `ready`，Claim revision 改變立即轉下游 `blocked`，renderer 不得自行升級。
- [ ] 定義 `TopicLens`：stable ID、revision、learning unit、`topic | source_section | process | comparison` kind、parent、question、multi-membership、role／order、scope、provenance basis／rationale、review status；provenance 至少區分 `source_structure | author_organization | user_organization | ai_proposal`，只有聲稱來源結構時才要求 source Evidence，使用者教學分組保存作者與理由即可；Lens nesting／membership 不生成 `part_of` 或其他 knowledge Edge。
- [ ] 第一版定義 document-level `LearningNote`，不用尚未決定的 block editor：一個 learning unit 一份 versioned Markdown，headings／lists／paragraphs 為結構，source anchors 另存，可沒有 Concept／Edge／Teaching Proposition。`NoteBlock`、atomic-note split／merge 與 graphical argument structure 待 baseline 證明需要後另立 contract。
- [ ] 定義 `LearningTarget`／`ReviewItem`：目標是可觀察表現，不是「背一個節點」；可直接來自 Source／reviewed Claim、教學重點、使用者問題或可選 LearningNote，不要求先有筆記。保存 importance decision／reason／decided_by、claim／Evidence refs、prompt、activity type、rubric、item revision 與允許的回饋狀態。
- [ ] 定義 `Attempt` 狀態機：client ID、review item／revision、`started | draft | submitted | cancelled`、started／submitted time、raw response、confidence、hint events、activity type、`modeled | reference_visible | guided | hinted | unassisted | answer_revealed | unknown_legacy` support／exposure state、feedback revision、outcome、correction、entry task／view；due item 是排程資格，不是 Attempt 或 canonical knowledge。未選練習、只閱讀後結束或中途離開不建立錯誤 Attempt。
- [ ] 定義 Claim 修訂的下游失效：舊 Attempt 永久保留並標明當時判準；受影響的 ReviewItem／due item 立即 suspend，rubric／答案重新確認後才恢復。作答中才發生失效時保留 response，結果標為「無法依舊判準評估」，不得硬判對錯。
- [ ] 將現有 Guided Map Groups 透過 adapter 視為 `TopicLens revision 1`；解除「同一 Concept 只能屬於一個 group」的一般限制，保留特定簡單 renderer 可宣告的版面限制。
- [ ] 提供舊 `ReviewInteraction` → 新 Attempt read adapter；舊資料可讀、不可被偽造為閉卷。無 stable attempt ID 或答案可見狀態者標為 `legacy/unknown`，不拿來估計 retrieval 成效。
- [ ] 新工作區用 feature flag；保留舊三視圖唯讀版作 comparison／rollback。Lens／Graph 派生失敗只停用該功能，已驗證的 Source 與既有 LearningNote 仍可讀。

完成條件：每張已開工工單使用的 record 都有 versioned schema、valid／malformed fixture、provenance、reference integrity、determinism 與 idempotency tests；migration 有 dry-run diff、read-back 與 rollback，不改 Concept IDs，不覆寫舊 review history。未被該垂直切片使用的 record 不作為結案前提。

### Phase 3c-2：Baseline「閱讀、解說與可選練習」工作區

先做不用 Graph 也能完成原始需求的版本，讓 Graph 有真正要打敗的 baseline。

- [ ] Inbox 只接受明確選定的 Source；用途／問題可從 notebook 沿用或稍後補充，只有實驗 protocol 才強制固定。原文 bytes 與來源 hash 不變。
- [ ] 第一個 prototype 使用人工準備、已審核的小材料；學習者可以閱讀／討論未確定主張，但不負責先完成整份教材的專業 fact-check，也不會把未確定內容當唯一正解。
- [ ] Reader 做語意化分段、breadcrumb 與短 excerpt；目前問題與範圍常駐，點 anchor 會實際捲動／聚焦到段落，不只加 highlight class。第一步不顯示空白 note task 或診斷題。
- [ ] 以 3c-W0 提供人工準備、source-grounded 的重點／困惑解說，以及 `繼續閱讀 | 換種解說 | 追問 | 試著說一次 | 先結束`；任一選擇都可再回到來源，不形成固定關卡。
- [ ] 選 `試著說一次` 才進入 teach-back；使用者可選參考材料或無輔助，提交後顯示 rubric 與 Evidence。選擇閱讀、解說、結束或中途離開都不記成錯誤 Attempt。
- [ ] versioned Markdown LearningNote editor 是明確選擇後才進入的可選工具；headings／lists／paragraphs 足以表達 outline、步驟與簡單對照。本期不做 block merge／split、拖曳樹、argument-map editor、atomic-note 系統或五種專用編輯器。
- [ ] live AI 是後續可選 adapter；3c-W0 以人工準備解說完成，3c-B0 可完全零 AI。日後 AI 可卸載摘要／解說／定位，但 AI 產出或「按接受」次數不算使用者表現 evidence。
- [ ] 使用者若選擇記錄，能保存自己的解釋、問題與 uncertainty；不要求每篇／每個主題建立筆記或捏造不確定。也能只閱讀後輸出，或只保存 lookup note、不建立 ReviewItem。
- [ ] 完成 3c-S0 的雙向行為：Claim→全部 Evidence 可取得但預設顯示摘要＋數量、按需展開；Evidence→全部 Claims 不任意單選。可在兩次操作內回到 exact source location。
- [ ] 顯示群組／流程／知識 Edge 的語意類型，明文避免把版面位置、教學順序或共同 membership 誤讀成因果／`part_of`。
- [ ] 由使用者把候選標成 `remember | lookup | defer`；理由可填但不是每次必填。`lookup` 必須可由 notebook-scoped literal search 回到 note heading／snippet／source anchor；importance 不寫入 Concept 永久屬性。
- [ ] 明確驗收四條獨立入口：「只閱讀／解說後結束」「選擇一個有支援或無輔助練習」「可選整理、暫不建題」及「已有脈絡或筆記、直接續接／搜尋／回找」；四者都不需要 Graph extraction 完成。

完成條件：在空 notebook、零 canonical Concept／Edge／Teaching Proposition、零 live AI 的情況下，product owner 能以一份 pretest-confirmed unfamiliar micro-source 閱讀、查看人工解說、追問或正常結束；當她選擇 `試著說一次` 時，系統接住輸入、正確記錄支援狀態並提供可回到 Evidence 的具體回饋。reload 後能找回上次的問題、解說與尚待確認處；全程可不建立 LearningNote，也不要求每次練習。另以明確選擇驗收筆記 headings／lists、保存、重開、搜尋與回來源；canonical graph 不因閱讀、解說、練習或筆記內容改變。BitePacer 若已因反覆使用而熟悉，不再固定充當低熟悉材料。

### Phase 3c-3：LearningTarget、多種支援程度的 Attempt 與有用回饋

- [ ] 可從 Source／reviewed Claim、教學重點、使用者問題或可選筆記建立 LearningTarget，要求「能做什麼」與接受標準；`lookup` 只建立可搜尋入口，不排入間隔複習；`defer` 不製造負擔。
- [ ] 3c-B1 第一個垂直切片只做一種人工 rubric 的解釋或區辨題，但允許明示的 reference-visible 與 unassisted 兩種支援狀態；通過後再分別加入模仿、部分完成、填空、條件／反例、預測與新情境應用。linking-phrase 精確字串只保留給確實需要逐字術語的 target。
- [ ] Reviewer 依 versioned rubric 與 reviewed Evidence 判斷缺少什麼、何時成立、如何修正；保留 `INSUFFICIENT_EVIDENCE`／「標準答案待修訂」，不把字串不同直接判為概念錯誤。
- [ ] 作答前記錄信心；作答後才揭露答案、Evidence 與 correction。短回饋摘要可限制長度，但完整 rubric 差異與 Evidence 必須另可展開。使用者可不同意回饋、指出來源衝突並把失敗送回 LearningNote 修訂。
- [ ] 回饋 revision 與當時的 Evidence snapshot 固定；後續知識修正不覆寫舊 Attempt，而以新回饋／勘誤說明當時判準。
- [ ] Claim／rubric 失效時依 3c-1 suspend 下游題目；作答中失效保留使用者 response 並標成不可依舊判準評估，不丟失或覆寫。
- [ ] 同一 Target 換提示、換案例或要求推論，避免只記住人工 linking phrase；至少一題驗收 transfer，而不是只驗收 recognition。

完成條件：任一題在提交前無答案洩漏；Attempt 可保存錯誤、提示、信心、申覆與修訂；同義但合理回答不因未逐字匹配失敗；有爭議的教材不會被 reviewer 當唯一標準答案。

### Phase 3c-4：最小到期佇列與再次提取

- [ ] 建立可解釋的 due queue：首次有效提交是 `schedule_anchor_at`；第 1／3／7／21 天是相對 anchor 的絕對 milestones，不是每次成功後累加。Target 保存 scheduler timezone（v1 明示 `Asia/Taipei`），`due_at` 存 RFC 3339 UTC；規則、下一日期與理由可見，時鐘可注入測試，不宣稱此組日期最佳。
- [ ] 到期只建立／更新 due eligibility，不建立 Attempt。使用者開始作答才建立 stable Attempt；submit 才形成可評估回答，draft／cancel／不知道各自有明確狀態。
- [ ] 逾期只顯示最早未完成 milestone，不補造一串 Attempt；snooze 記錄新日期與理由，skip 只跳過該 milestone，停止追蹤或 `remember → lookup` 取消未來 due，歷史不刪除。
- [ ] Claim／ReviewItem revision 變更會 suspend 相關 due；rubric 與新答案重新確認後才恢復。一次答錯不自動提高全域複習負擔。
- [ ] 同時支援「已有筆記，今天只複習」的直接入口，不要求重走 Reader／Map／Graph。
- [ ] 失敗可回到對應 LearningNote／Evidence 修訂；使用者明確選擇「再試一次」才建立新 Attempt，形成「錯誤 → 修訂 → 再測」閉環。

完成條件：至少一個 Target 能完成首次作答、產生 due eligibility、到期後由使用者開始新 Attempt、read-back 與規則重算；無開啟 App 不會生成 Attempt，系統不產生 mastery 百分比，也不因時鐘或網路重試建立重複 attempt。

### Phase 3c-5：Topic Lens 與按需局部 Graph variant

Graph 不是第一週或 baseline 的完成前提。只有 3c-W0 通過 Formative gate，且 3c-X0 已指定一項關係任務後，才做低成本 `目前主題＋跨界提示＋概念 ego` variant；大型 compound graph 暫緩。

- [ ] 單元概覽只顯示 Topic Lens 名稱、範圍明確的局部問題、目標與項目數，不預設畫全部 Concept／Edge；單一總問題不能單獨充當 scope control。OS 五個群組改稱教學主題，不稱「五個階段」。
- [ ] Topic Lens v1 明列 `claim_ids`；主題視圖只顯示明確選入且 teaching-ready 的 Claims，不因四個 Concepts 共同出現就自動顯示其間所有 accepted Edges。
- [ ] Concept ego v1 只取與焦點直接相連、reviewed、teaching-ready 且符合 source／relation filter 的 Claims；固定 budget 為最多 8 個鄰居／12 條 Claims，依 Lens membership order 後接 stable Claim ID 排序，不用 centrality 猜重要性，並顯示截斷數量。
- [ ] 跨 Lens Edge 預設顯示去重後的 Claim 數、目的主題與「尚有其他連結」；展開後顯示真實端點、原方向與 Evidence。聚合的「3 條關係」不可偽裝成 canonical Edge。
- [ ] 同一 Concept 可在兩個並列 Lens 各有 visual instance，但 selection 以 stable Concept ID 共用；跨群組計數依 Claim ID 去重。當前 selection 落在新 scope 外要提示，不可靜默切焦點。
- [ ] Filter 若排除目前焦點，v1 拒絕該次更新、保留上一個合法 view 並說明原因；被 filter／budget 隱藏不代表不存在，scope、filter、hidden count 必須可見。
- [ ] `needs_revision／blocked` Claim 預設從教學圖排除並顯示警示數量；使用者主動查看時以警示模式呈現，永不進 exercise。跨主題展開返回後還原原 Lens scope、scroll 與展開項目。
- [ ] 移除 Map／Graph 集合大小必須相等的 validator；只驗證共同出現的 identity／claim／direction／review status／provenance，另外驗證各 view 的 lens revision、scope 與 selection policy。
- [ ] Map 與 Graph 各自由同一 canonical Concept／Claim／Evidence snapshot＋Lens 投影；`projectGraphFromGuidedMap()` 可保留為舊 demo adapter，但不能再拿「Graph 由 Map 複製後兩者相同」當 production 一致性證明。Golden test 要能對共同 source snapshot 的兩個獨立 projector 驗證 shared records。
- [ ] Graph detail 就近顯示所有 supporting Evidence 與條件；不得只顯示 locator＋「切到 Reader」。
- [ ] 先修可讀性 bug：可見群組標題／邊界、箭頭落在節點邊界且不被覆蓋、edge path 避開節點、長 label 斷行／避碰、iPad 不使用固定 850px 桌面縮圖。
- [ ] iPad 採 semantic zoom：主題與目標 → 該主題概念／關係 → 單一 claim 的條件、解釋與 Evidence；一次一個主要工作區，只有比較任務才並列小型圖。
- [ ] 支援兩個無直接 Edge 的主題並列，明示「目前選取資料中沒有直接連線」，不把它教成現實中絕對無關，也不為連通性幻覺 Edge。
- [ ] 第一個 Graph manifest 只驗證單一來源內關係追蹤，不據此宣稱跨來源價值；要測跨來源時另建兩來源 fixture，含共同 Concept 與條件不同的 Claim，Baseline 與 Graph variant 必須看到相同資料。

OS 實機驗收情境固定為：第一屏只顯示「建立保護邊界／回應硬體事件／保存與切換執行現場／平衡排程公平／保護共享狀態」五個教學主題及任務選擇；選「回應硬體事件」後顯示自己的筆記、driver／handler 待釐清項、reviewed 關係與跨主題關係數；要求同時看「中斷／驅動程式」與「鎖／競爭危害」時用兩個有標題的小型區塊並列，而不是塞進無邊界全圖。

完成條件：使用者能指出目前 Lens、scope、隱藏內容與箭頭方向；能區分群組、流程與 knowledge Edge；Graph 在 iPad 無遮擋／不可辨箭頭；同內容 Baseline 與 Graph variant 都能完成相同非 Graph 功能。

### Phase 3c-6：Runtime 解耦、降級與可觀測性

- [ ] 將瀏覽 focus／selection、LearningNote edit session 與 Attempt session 分成不同 state；選另一條 Edge 不得清空或替換未提交回答。
- [ ] 每個 view／attempt 記錄 task、Lens revision、scope、filter、knowledge snapshot、提示與答案可見狀態；先不收集拖曳次數等低價值 telemetry。
- [ ] stale Note／Lens／Graph projector 只停用受影響的派生功能並說明原因；安全的 Source Reader 與已保存筆記繼續可用。
- [ ] 所有 projector 繼承 reviewed input 的 edge class、confidence 與 claim status；不得在 UI adapter 硬編 `canonical/high`。
- [ ] 舊三視圖唯讀路徑與新工作區可由 feature flag 切換；rollback 不刪除新紀錄，未知新 record 對舊版以明確 unsupported 顯示。
- [ ] 所有 LearningNote 寫入使用 server-side revision precondition／強 ETag；stale Mac／iPad editor 回 409／412 類型的明確 conflict，UI 保留未提交文字並提供 reload／手動合併，不做 last-write-wins。
- [ ] 分開驗收「伺服器已保存但 response 遺失」與「保存失敗但 UI 不得顯示成功」；atomic write／backup／read-back failure 必須可復原。
- [ ] 語意化 Markdown 使用 allowlist renderer：raw HTML、危險 URL scheme 與自動外部圖片預設停用；sanitization 有獨立 tests，不能只依 CSP 或 source hash。
- [ ] AI proposal adapter 必須有 exact input／consent／review／ledger；在它完成前，人工 proposal 與無 AI fallback 是正式支援路徑。

完成條件：selection、editing、attempt 三種狀態的交互 regression tests 通過；任一派生視圖故障時仍可讀 Source／LearningNote；並行修改、response loss、write failure、惡意 Markdown 與 AI unavailable 均有明確降級／復原證據。觀測紀錄足以重現當時看見與沒看見的內容，且不包含不必要的私人原文。

### Phase 3c-7：可證偽實驗與三種材料

不把一個同時更換 layout、教材、題目、AI 與排程的「v2」當實驗。每次只改一個假說，內容、總時間、練習、回饋與額外重讀機會盡量相同。

| 假說 | 公平比較 | 可證偽／停止加碼的結果 |
| --- | --- | --- |
| H0-W 核心工作流符合實際使用方式 | product owner 現有「閱讀＋AI 解說」方式 vs KGnote 無 Graph 的閱讀／導讀／按需解說／可選練習工作區；兩組筆記與練習皆可選 | 無法直接針對疑問取得合適解說、選解說卻被逼答題、選練習卻只收到摘要、下次無法續接，或穩定增加操作／切換成本 |
| H1 群組編碼減少主題迷失 | 現行布局 vs 同內容加群組名稱／邊界 | 群組判讀沒改善，或追線錯誤抵銷收益 |
| H2 局部 scope 優於預設全量 | 有群組的全量圖 vs 目前主題＋跨界提示 | 漏看重要關係，或任務完成時間／正確性未改善 |
| H3 Graph 超過非 Graph baseline | 相同的結構化導讀＋搜尋＋Evidence vs 同版加局部 Graph | 關係推理、整合或查核無增益，卻增加時間、錯誤或切換成本 |
| H4 可選的使用者修訂是否有額外價值 | 系統整理的學習脈絡 vs 使用者自願加入少量關鍵選擇／修正 | 控制時間與內容後，回找、理解與延遲表現無改善，或修訂負擔抵銷收益 |
| H5 提取＋回饋＋間隔改善延遲表現 | 重讀 vs 真正提取＋回饋＋間隔 | 只改善當下，7／21 天與新情境未改善 |

每個假說先建立 3c-X0 test manifest，固定 Source revision／range、task、condition、起始狀態、rubric、主要指標、排除／中止與 `continue | modify | stop` 規則；N=1 結果只驅動下一步產品決策。原 note-first H0 manifest 是已中止的 protocol evidence，不重用或改寫；H0-W 另建版本，主要觀察能否直接學進去、能否依使用者選擇在閱讀／解說／練習間切換，以及能否延續學習脈絡。未進入練習不能算零分；進入後的真實回答與支援狀態才是表現 evidence。

材料分工與前測：

- [ ] 原創花園裝置教材彩蛋（高熟悉）只測 UI、群組、定位、方向與錯置發現；高分不宣稱介面促進學習。
- [ ] OS（中熟悉）測結構恢復、driver／handler 區辨、錯誤修正與時間片／context switch 條件；先做子題 pretest，不把過去學過算成介面效果。
- [ ] BitePacer 網路概念只在當次 pretest 顯示低熟悉時測陌生資訊；因它已反覆作 fixture，必要時換尚未接觸的匹配微型材料。記錄先備不足，不把所有失敗歸因 UI。
- [ ] 不用三種不同材料直接推論 prior knowledge 的因果效果；材料長度、術語密度、關係類型、動機與輸入方式至少記錄，正式比較採匹配微型主題／交錯順序。

候選指標包含：找到指定原文的時間與錯誤跳轉、目前主題／scope 判讀、箭頭／群組／位置誤讀、筆記 rubric、無工具解釋／區辨、延遲提取、換案例應用、作答前信心校準、總學習／操作／AI／人工修正時間。每份 manifest 只選與該假說有關的主要指標；熟悉材料 UI／定位不必等 7／21 天。需要延遲測時，部分 matched item 留到延遲日才第一次出現，避免即時測驗替其中一組增加訓練。

每次比較控制或至少記錄：總閱讀／練習時間、額外重讀、提示可見性、題目難度、來源正確性、mapping 熟悉度、輸入方式、條件順序、新奇感，以及 AI 在各條件提供多少解釋；不得讓某一組暗中多一次記憶／回饋機會。

H1 比較的兩組必須使用相同的箭頭端點、遮擋修正與 label 可讀性，只改 grouping encoding。H5 若一次比較「retrieval＋feedback＋spacing」整套方案，結論只到整套方案；若要分辨成分貢獻，另立實驗。筆記 rubric 接受不同組織方式，不以複製 expert fixture／五個既定群組作唯一好答案。

質性訪談固定問：

1. 你剛剛為什麼認為這些概念屬於同一類？
2. 你以為這條線在說什麼？
3. 你現在不知道的是概念本身，還是找不到它在哪裡？
4. 剛才的導讀或解說哪一部分真正幫你建立輪廓，哪一部分沒有切中問題？
5. 沒有 Graph，你會怎麼完成剛剛的任務？
6. 如果你剛才選了練習，它暴露了什麼缺口；如果沒有，什麼讓你選擇繼續讀或先停下？

N=1 只用來找答案洩漏、方向誤讀、焦點遺失、流程阻塞與反覆行為模式；不宣稱普遍長期增益、不把題目數當獨立受試者。若日後宣稱一般學習效益，另依最小有意義效果、變異與設計規劃多人樣本。

### Phase 3c-8：產品決策閘門

產品決策不等待 Phase 3c-0 至 3c-7 全部完成；每一層有足夠證據就作局部決定：

1. **安全閘門：**某材料／功能通過 claim review、write recovery、exposure state 與 idempotency 才可保存真實資料；失敗只隔離受影響項目。
2. **Formative 閘門：**先以 3c-W0 跑 H0-W；若無 Graph baseline 不能在不強迫筆記或練習的前提下完成閱讀／導讀／按需解說／正常結束，不能在使用者選練習時接住相符活動，或下次無法續接，先修工作區，不開始 Graph。3c-B0 的保存／回找／修訂另作可選工具驗收。
3. **Graph 投資閘門：**baseline 已可用且 3c-X0 已指定關係任務，才做 variant。若整合式 Baseline 在內容、時間、練習與回饋相等時表現相同或更好，而 Map／Graph 切換增加導航／對應成本，三層模式維持可選工具。
4. 若局部 Graph 在該任務有可重現增益，保留該任務入口；不得外推所有學習都 Graph-first，也不得把「關係整合有價值」偷換成「必須使用 graph database／node-link 畫面」。
5. 系統提供結構化導讀本身可以有閱讀與 lookup 價值，不要求使用者先自行整理來證明參與。若日後在事先同意的輸出時點只能辨認內容、不能解釋關係條件或換案例應用，只能判定該次可觀察表現尚未達標；不得回推「沒有親手改寫筆記所以沒有學習」。
6. 若出現教材錯誤被強化、非預期答案洩漏或關鍵方向被誤讀，立即停止受影響版本／題目；若局部 Graph 持續增加操作與錯誤，停止增加圖形複雜度。`未顯示增益` 仍須區分樣本不足與已能排除值得付出的效益。

### Phase 3c 整體完成條件

1. 使用者能直接閱讀或取得 source-grounded 導讀與針對疑問的解說，能選擇繼續讀、換解說、追問、先結束或進入練習；選擇會被正確接住，不形成固定關卡。不強迫先產出 Markdown 或每次練習。若主動使用 LearningNote，才驗收自己的結構／解釋與問題／不確定可保存、重開及修訂。
2. 任一 Claim 的全部 Evidence 可取得，預設以摘要／數量避免資訊淹沒；Evidence 的全部 Claims 也可反向取得且不依陣列順序。Source support、fact review 與 teaching-answer readiness 不混用。
3. activity type、required context、model／reference visibility、hint、answer reveal 與非預期 leak 有明確邊界；confidence、raw response、support／exposure state 與 client attempt identity 完整保存。有支援的練習不冒充無輔助提取，系統也不宣稱能觀測外部答案來源。
4. 問題、看過的解說、來源位置、尚待確認處、錯誤、申覆、Evidence 不足、可選 LearningNote 修訂與新的獨立 Attempt 形成可 read-back 的學習脈絡；Claim 修訂會 suspend 舊題而不刪歷史。
5. 至少一個 Target 完成首次與到期再提取；至少一個題目換提示或情境測應用，不只測逐字 phrase。
6. Topic Lens 可重疊、有 revision／scope／provenance；共同 membership 不產生 knowledge Edge，Graph／Map 不要求全量同集合。
7. Baseline 可在零 Concept／Edge／live AI 下獨立使用；若 Graph 通過進場條件，Baseline 與 variant 的內容、練習與回饋等價，且 Graph 去留有預先定義的任務與證偽標準。
8. schema、provenance、migration、malformed input、reference integrity、determinism、conditional write、idempotency、source immutability、exposure、sanitization 與 stale fallback 測試通過；Mac／iPad 的中文輸入、保存、reload、conflict recovery 與實際 render 驗收通過。

### 一週切片順序

若只投入一週，先驗證「幫助系統化陌生資訊」，不假裝一週已證明長期記憶：

1. Day 1–2：完成 3c-W0 的 Source／結構化導讀／人工解說 read model；解說保留類型、來源 anchors、provenance 與「為何重要／回應哪個疑問」。
2. Day 3：完成可往返選擇：繼續閱讀、換種解說、追問、試著說一次、先結束；任何選擇都不建立理解分數或強迫下一關。
3. Day 4：只在選 `試著說一次` 時建立 teach-back input；明示 reference-visible 或 unassisted，保存 raw response 與人工 rubric 回饋，並可回來源／解說。
4. Day 5：保存最小 session context：問題、看過的解說、尚待確認處與最後來源位置；reload 可續接。LearningNote 只作可選收藏／修訂入口。
5. Day 6：完成 3c-S0／S1 中本 fixture 需要的 claim／Evidence 安全閘門；不把整套 Graph 工作提前塞進此切片。
6. Day 7：為 H0-W 建立新 3c-X0 manifest，以另一份真正陌生且使用者想理解的 micro-source 跑 formative test；只觀察能否學進去、能否按選擇切換、能否延續學習，不要求寫筆記、進練習、Graph 或 7／21 天結果。

Graph variant 是條件式後續：只有 Baseline 通過 formative gate，且已選定一項關係任務與公平 rubric，才另開工單；不再固定為 Day 6 必做。

### 審查觀點覆蓋索引

| 審查區段 | 已轉成的實作項目 |
| --- | --- |
| §1 核心四項缺口 | 3c-0、3c-2、3c-3、3c-5 |
| §2 兩個迴圈、可修訂筆記、表徵選擇、重要性 | 新資訊架構、3c-2、3c-3、3c-4 |
| §3 研究證據與限制 | 3c-2／3c-3 的活動設計、3c-7 公平比較與指標 |
| §4 實作診斷與資料品質 | 3c-0、3c-1、3c-5、3c-6 |
| §5 Graph 分區／scope 方案 | 3c-5；短期 visible group，prototype 採 topic scope＋ego，compound graph 暫緩 |
| §6 任務式 IA、OS 示範、iPad progressive disclosure | 新資訊架構、3c-5 |
| §7 contract／TopicLens／NoteBlock／LearningTarget／Attempt／migration | 3c-1、3c-6 |
| §8 可證偽實驗、三種材料、指標、混淆、N=1、停止條件 | 3c-7、3c-8 |
| §9 優先級、最小 prototype、三層模式否證與一週順序 | 3c-0 至 3c-8、整體完成條件、一週切片順序 |

### 第二輪「roadmap → 可執行工單」修訂覆蓋索引

| 後續審查缺口 | 已決定的落點 |
| --- | --- |
| Evidence→多 Claim 被誤譯為 Claim→多 Evidence | 3c-S0；雙向分開驗收、反轉陣列順序 regression |
| `needs_revision` 與舊 schema／JS validator 不相容 | 3c-S1；先用獨立 ClaimReviewOverlay，並修正 accepted／corrected contract drift |
| note-first／retrieval-first 都過度指定唯一主線 | 3c-W0／3c-2；改為可往返的閱讀／導讀／按需解說／可選練習工作區，LearningNote 降為可選工具，原 H0 中止且不評分 |
| NoteBlock 編輯／持久化語意未決 | 3c-B0；v1 選一份 versioned Markdown LearningNote，不做 block editor |
| 零 Concept／Edge 時筆記是否可用 | 3c-B0 與 3c-2 的空 notebook 核心驗收 |
| Claim 與 ClaimReview 邊界、下游題目失效 | 3c-1 versioned Claim＋Review／Erratum＋suspend 傳播 |
| Attempt／提示／揭露／due 語意模糊 | 3c-B1 與 3c-4 的生命週期、exposure state、milestone 規則 |
| 3c-0～3c-8 被誤當完整串行 | 三種獨立閘門；每張工單只取所需 contract |
| 第一週預先承諾 Graph | 一週順序改成 H0-W 工作區 baseline；Graph 需通過 Formative gate＋manifest 才進場 |
| 缺「比現有學習方式有用嗎」 | 3c-X0／3c-7 新增 H0-W，學進去／活動切換／脈絡延續／lookup／可選筆記價值分開驗收 |
| 指標名稱未成可執行 protocol | 3c-X0 manifest：task／condition／rubric／primary metric／exclusion／decision |
| Graph 只定顯示、不定選取政策 | 3c-5 明定 explicit `claim_ids`、8-neighbor／12-claim budget、去重、filter、blocked claim 與返回狀態 |
| 過硬的用途／加工／不確定／Evidence／無答案規則 | 3c-2／3c-3／完成條件改為可選用途、能力而非配額、摘要＋按需展開、四類 exposure |
| 可編輯筆記的 concurrency／recovery／ownership | 3c-B0／3c-6：authoritative Markdown/YAML、ETag precondition、atomic write、response-loss 與 conflict recovery |
| Markdown rendering、AI fallback、iPad 輸入 | 3c-B0／3c-6：allowlist＋sanitization、零 live AI 路徑、中文輸入與無 drag 操作 |

## 已完成：Phase 0 - 用人工 fixture 鎖定資料 contract

這一階段不接 API，也不建前端。要先回答「到底存什麼、不存什麼」。

### 要交付

- [x] 產品邊界與非目標：`docs/PRODUCT_CONTRACT.md`
- [x] 最小資料模型與不變量：`docs/DATA_MODEL.md`
- [x] agent、Git、安全與驗收規範：`AGENTS.md`
- [x] 原始需求、SynthKG 與 BitePacer 參考路徑：`docs/REFERENCE_SOURCES.md`
- [x] 以一小段 synthetic/redacted 學習對話，人工製作 6 個 Concept、1 個 LearningEvent、4 個 Evidence 與 8 個 typed Edge 的 fixture。
- [x] 在 Obsidian 開啟 fixture，人工驗收連結、圖與原文回溯是否真的降低找上下文成本。

### Phase 0 當前驗收條件

1. 同一份 source 能用穩定 ID 被引用。
2. 每個 learning claim 都能追回 evidence，evidence 能追回 source。
3. Concept 和 LearningEvent 沒有被混成同一種節點。
4. 「曾提到」沒有被寫成「已理解」。
5. 使用者能從圖或 concept note 在兩次點選內回到完整 evidence/source。

## 歷史設計基線：已完成但待證偽的三層學習模式

2026-09-15 的 BitePacer 實際使用顯示：只有節點與連線的 Graph 對陌生主題仍缺乏閱讀順序，過度寬泛的 Edge label 也不能幫助 product owner 說清楚節點之間的關係。因此當時建立三視圖原型，並以 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md` 約束它們不分岔。這段保留為已完成工程與歷史決策；2026-09-19 審查後，它不再是當前產品核心或固定順序，後續由 Phase 3c 的 Baseline／Graph variant 比較決定其地位。

| 層次 | 使用者正在做的事 | KGnote 要提供什麼 | 不能偷渡的判斷 |
| --- | --- | --- | --- |
| 1. 原文閱讀（Reader） | 第一次讀懂情境、例子與完整推理 | 不改寫的選定 Source、段落／行號、少量非破壞標註與目前 focus question | 看完不等於記住或理解 |
| 2. 階層式學習地圖（Guided Concept Map） | 看章節／流程骨架，釐清少量核心關係 | 一個 focus question、view-only 導覽群組、固定 Concept label、能讀成句子的 Evidence-backed linking phrase | 群組不等於 Concept；排列不等於 `part_of` 或 prerequisite |
| 3. 知識圖譜（Exploration Graph） | 已有輪廓後做局部、跨章節或跨來源探索 | 同一 Concept identity、同一 Edge 方向／Teaching Proposition、local neighborhood 與可選 cross-link | 開啟或瀏覽 Graph 不等於更熟練 |

當時採用的原型流程是：

```text
讀一小段原文
  → 看回答同一 focus question 的階層學習地圖
  → 補一個關係詞／排列流程／用自己的話解釋一條 Edge
  → 對照同一筆 Teaching Proposition 與原文 Evidence
  → 需要時進入相同焦點的局部知識圖譜
```

三層不是功能鎖。product owner 可以隨時切換 `閱讀｜學習地圖｜探索`；系統只改變預設資訊量，不以點擊數推測先備知識。切換後必須保留相同 Source、focus question、Concept、Edge 與可用時的 Evidence locator。iPad／手機同一時間以一個主要視圖為主，原文 excerpt 就近展開，不要求使用者在三個分離頁面間靠記憶比對。

### 一致性底線

1. 原文 bytes 不改，AI 標註不可冒充原文。
2. 同一 learning unit／locale 的 Concept 名稱固定；英文技術詞作 alias，程式 token 不翻譯。
3. 同一 Edge 的 subject、object、方向與 learner-facing linking phrase 在 Map／Graph 完全一致。
4. 每條教學關係至少有一筆可回到 Source 的 accepted／corrected Evidence；只有 soft association 時不放進預設學習地圖。
5. 三個 renderer 不各自 paraphrase；AI 只在 staging 提 candidate，通過 preview 後由共同 read model 投影。
6. Reader／Map／Graph 任一處都應在兩次操作內看到支持目前概念或關係的原文。

## 已完成：Phase 3b 三層個人可用閉環

本段記錄 2026-09-16 已完成的工程切片。它證明三視圖 identity／provenance 可一致投影與操作，不證明三層模式帶來學習增益，也不證明當時人工 fixture 的主張全部正確：

```text
已選定並人工審核的 BitePacer Source
  → 安全的原文 Reader
  → 一個 focus question 的階層學習地圖
  → 一筆跨視圖一致的關係提取練習
  → 相同焦點的局部 Web Graph
  → append 回答、hint 與評估結果為新的 learning evidence
```

這裡的「可以使用／上線」先定義為 **product owner 可在自己的 Mac 或同一受信任 Wi-Fi 的 iPad，以一篇明確選定的真實 Markdown，在不修改 Python／JSON 的情況下完成閱讀、建立輪廓、解釋一條關係、回看原文與局部探索**。它不是公開網路部署，也不要求多人帳號、雲端同步或 LINE 入口。

### 優先操作順序

1. [x] **接受跨視圖一致性契約**：鎖定原文、Concept identity、Teaching Proposition、Edge 方向、Evidence、焦點同步與 hierarchy／knowledge relation 分界。
2. [x] **決定最小 read-model shape**：Teaching Proposition 與 hierarchy grouping 存在獨立、人工審核的 `kgnote.guided-map-spec.v1`；純投影器以 stable ID 接回同一 Graph Read Model，產生 `kgnote.guided-map-read-model.v1`，不擴充 canonical Edge 或 UI 私有欄位。
3. [x] **安全的原文 Reader**：`kgnote.reader-query.v1` 只接受 snapshot、已註冊 `source_id` 與可選 line range；application boundary 驗證 raw path、symlink、SHA-256、UTF-8、大小與行號後回傳 exact text、Evidence annotation 及相同 Concept／Edge IDs，不接受 caller path。
4. [x] **BitePacer expert-skeleton 學習地圖**：以「一則 LINE 訊息如何抵達 product owner Mac 上的 BitePacer？」為單一 focus question；群組只作導覽，每條核心 Edge 都能讀成中文句子並回到原文。
5. [x] **三視圖焦點同步**：`閱讀｜學習地圖｜探索` 共用 Source／Concept／Edge／Evidence selection；Graph 沿用已完成的 local neighborhood，不另外改寫名稱或 relation。
6. [x] **一個 scaffolded retrieval interaction**：完成補 linking phrase；答後並列 canonical Teaching Proposition 與原文 Evidence，並以獨立 versioned contract 保存 append-only review evidence。
7. [x] **一致性 validator 與 iPad smoke**：自動檢查 identity／label／direction／phrase／evidence／determinism／raw-source immutability；已在 1024×768 iPad responsive viewport 實際走完整條路徑。
8. [x] **完成後回到真實單篇導入入口**：既有 importer、consent-gated Gemini transport、validation、normalization、ledger、dry-run 與獨立 apply approval 已由單一 CLI 串起，不要求 product owner 手工製作 replay JSON；首次真實外送仍需 product owner 針對 exact digest 授權。
9. [x] **人類可判讀的 extraction／apply preview**：完成 versioned Concept 名稱、Edge 方向／relation、Evidence proposition、exact 原文行與 blocking conflict／reject 預覽；另完成獨立、snapshot-bound 的 linking-phrase staging。CLI `phrase-preview` 產生第二次 exact consent digest；`phrase-extract` 只在 digest 完全相符後執行一次 phrase-only Gemini transport，並保存 append-only candidate ledger；`phrase-review` 再以獨立 digest append 人工 accept／correct／reject reviewed set。Fresh Evidence 保持 `unreviewed`，因此即使短語被接受也不會自動成為 Guided Map Teaching Proposition。

既有基礎可以重用：explicit store apply／read-back／viewer、local graph query、Concept detail、一題一答與 append-only review 已有測試。Phase 3b 不重寫這些邊界，只在其前方增加 Reader／Guided Map，在其間增加共用 Teaching Proposition 與 selection state。

### 此主線的完成條件

1. 原始 Markdown byte-for-byte 不變；Reader annotation、Map grouping 與 layout 不回寫原文或冒充 canonical knowledge claim。
2. BitePacer 同一核心 Concept 在三視圖 resolve 到相同 ID／中文 label；相同 Edge 的方向與 linking phrase 一致。
3. Guided Map 每條核心 Edge 可朗讀成合理句子，且由 Reader、Map、Graph 任一處在兩次操作內看到相同 supporting Evidence／原文。
4. product owner 能說出 focus question、重述主要訊息路徑並解釋至少一條關係；只保存 response／hint／outcome／context，不換算理解百分比。
5. iPad 切換三視圖後保留同一焦點，不需同時記住分離畫面才能比對；Graph 預設是該 learning unit 的局部視圖。
6. schema、projection、HTTP 與 UI tests 覆蓋 malformed／stale reference、soft association、跨視圖 drift、determinism、source immutability 與任意 path 拒絕。
7. 關閉重開後 review evidence 仍可追回當時 Teaching Proposition、Source locator 與 view context。
8. Phase 3b 完成只代表人工審核 fixture 的三層 UX 可用；真實 Gemini extraction 仍要另做 exact preview、fresh consent、usage／ledger 與私人資料邊界驗收。

### 當時凍結的項目（歷史記錄）

- 自動 review scheduling、遺忘曲線或熟練度分數。
- hint fading 的多階段完整體驗。
- 語音、LINE/LIFF/MINI App、公開部署、帳號與多人協作。
- 批次掃描全部 LLM Wiki、graph database、reranker、搜尋與版面持久化。
- 自動以停留時間、點擊數或進入 Graph 推測學習階段。
- 純視覺 polish；除非它阻止理解跨視圖對應或完成上述真實操作。

## 已完成：Phase 1 - 可重現的 Markdown extractor MVP

- [x] 定義 versioned extraction input/candidate output JSON Schema、valid fixture 與 malformed-payload contract tests。
- [x] 實作 source importer：只讀一個明確指定的本機 UTF-8 Markdown，產生 validated `ExtractionInput`，不解析 front matter、不掃描目錄或寫入 vault。
- [x] 實作 offline extraction-response boundary：replay 一份 raw JSON、注入 adapter-owned provenance、回傳 accepted/rejected attempt，不接 provider/API 或寫入 response。
- [x] 實作 consent-gated provider-neutral extraction run adapter；回傳經 schema validation，失敗時以 immutable local ledger 保留 raw response 與錯誤狀態。
- [x] 實作 deterministic normalization、stable IDs 與 local-reference integrity。AI 不直接決定覆寫／merge。
- [x] 實作 deterministic dry-run，列出 create/update/unchanged/conflict/reject，不直接改 vault。
- [x] 實作 explicit-root canonical-store adapter、approved idempotent apply 與 read-back audit。
- [x] 用同一 fixture 重跑兩次，證明第二次只會 unchanged、零寫入且不產生重複節點或事件。
- [x] 依官方文件選定第一個真實 provider transport，並以 mocked HTTP 驗證單次 Gemini structured-output request、錯誤映射與 ledger 串接。

### Phase 1 當前不做

- 不批次掃描整個 LLM Wiki。
- 不自動刪除、merge 或 rename 人工 concept notes。
- 不建 Graph RAG、review scheduler 或 chat UI。

## Phase 2 - Obsidian v0 實用性驗證

- [x] 先以 synthetic source + replay response 完成一次全離線 dress rehearsal，產生獨立 disposable Obsidian artifact，並證明重跑零寫入。
- [x] 將一份使用者明確選定的實際學習 Markdown，以人工審閱 replay 全離線導入 repository 外的專用 disposable KGnote vault；原 LLM Wiki 不變。
- [x] 驗收 global graph 與 local neighborhood 可導覽，24 個節點全圖連通且無孤立節點。
- [x] 驗收點 Concept 後可看到 summary，並可由 Evidence／local graph／backlinks 導覽相關概念、learning history 與 source provenance。
- [x] 記錄首批實際使用觀察：無錯誤 merge、orphan 或 provenance 斷裂；長 SHA-ID 標籤有輕度重疊，但目前規模未過密。後續依更多真實樣本再決定是否調整顯示名稱或 schema/prompt。
- [x] Issue #12 已決定 stable ID 繼續作 canonical filename／link target，並以 renderer-owned aliased wiki-link text 改善筆記內導覽；71 個離線測試與三個 disposable Obsidian artifact 視覺驗收均通過。

## Phase 3 - Web Graph Viewer（先不接 AI）

- [x] 定義 versioned canonical snapshot → read-only graph read model contract；stable ID 與顯示 label 分離，Concept Graph／Learning Overlay 分層，Evidence／Source 作 provenance support records。
- [x] 實作純記憶體 deterministic projector；只接受 caller 提供的完整 canonical records，產生 copy-safe graph read model，不讀寫 vault 或接觸 network／clock。
- [x] 定義並實作純記憶體 neighborhood/filter planner；filter-first、方向中立 traversal、1/2/3-hop、snapshot-bound query 與 provenance support selection 均可 deterministic replay。
- [x] 實作 explicit canonical store → projector → planner 的唯讀 application boundary；回傳 versioned、plan-materialized graph JSON，不暴露未選取 provenance 或絕對路徑。
- [x] responsive graph canvas；Mac/iPad 支援大圖，iPhone 預設 local neighborhood。
- [x] 點節點展開 side panel，顯示 source、evidence、history 與 known confusion。
- [x] 1/2/3-hop neighborhood、node/edge type filters 與 space filter。
- [x] 圖是 read model；不讓 UI 直接修改 canonical Markdown。

## 已完成：Phase 3b - 原文／學習地圖／知識圖譜的漸進式介面

Phase 3 已證明 typed graph、local neighborhood、provenance panel 與 responsive canvas 能安全讀取 canonical store；BitePacer 個人試用則證明「技術上能看圖」仍不等於「陌生主題能靠圖建立理解」。Phase 3b 因此完成了跨視圖一致與可讀性 baseline。2026-09-19 後續校正指出：此 baseline 仍缺少針對疑問的解說、可延續的學習脈絡、不同支援程度的可選練習、到期再提取與公平的非 Graph 對照；後續缺口改由 Phase 3c 處理，不在本歷史段落追加新功能。

### 功能邊界

- Reader 負責完整自然語言與 source position；不在瀏覽器重寫原文，也不暴露任意檔案系統路徑。
- Guided Concept Map 負責一個 focus question 的閱讀順序、expert skeleton、核心 Teaching Propositions 與少量 cross-links。
- Exploration Graph 沿用 Phase 3 canonical graph，但從相同 learning unit／focus 開始，再由使用者選擇擴展 hop 或跨來源鄰居。
- 三者共用 Concept identity、learner-facing label、Edge direction、linking phrase、Evidence 與 selection state；詳細 invariants 見 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`。
- chapter／section／流程階段可以存在 map view model，但不因此進 canonical `concepts/` 或 `edges/`。

### 實作順序

1. 先定義 versioned Teaching Proposition 與 Guided Map read-model contract、valid fixture、malformed cases 和 cross-view golden。
2. 加入 explicit-source Reader application boundary；只回傳已註冊 Source 與允許的 locator 範圍，保留安全 header 和 no-store policy。
3. 以人工審核的 BitePacer fixture 建立 expert-skeleton Guided Map，不先接模型自動生成。
4. 建立共享 selection state 與 Reader annotation ↔ Map node／edge ↔ Graph node／edge 的雙向定位。
5. 加入一種 scaffolded retrieval task，重用 Phase 4a append-only review，不同模式不各自建立評分規則。
6. 完成 Mac／iPad 實機與 source-byte read-back，再決定是否擴充 extraction schema／prompt 自動產生 map candidate。

第 1 步已於 2026-09-15 完成：`schemas/guided-map/v1/` 定義 versioned spec 與 renderer read model；BitePacer cross-view golden 鎖定 5 個導覽群組、9 個 Concepts、7 筆 Teaching Propositions 與 5 筆 reviewed Evidence。UI 尚未開始。

第 2 步已於 2026-09-16 完成：`kgnote.reader-application.v1` 可從 explicit canonical store 安全讀取已註冊 Source，BitePacer golden 證明 2,134 bytes／84 行原文與 `L3-L18` excerpt byte-equivalent read-back，並輸出可供後續 selection state 使用的 Evidence／Concept／Edge IDs。HTTP route 與 Reader UI 尚未開始。

第 3 步已於 2026-09-16 完成：`guided-map.html` 直接消費 versioned BitePacer Guided Map read model，呈現單一 focus question、5 個 view-only 階段、9 個固定 Concept 與 7 條可朗讀 Teaching Propositions；每條關係可在一次展開內看到 Evidence proposition、locator 與 exact numbered source lines。此頁仍是人工審核 fixture 的獨立 Guided Map；共享 selection state、Reader UI 與同一焦點的 BitePacer Graph 留給第 4 步。

第 4 步已於 2026-09-16 完成：同一頁加入 `閱讀｜學習地圖｜探索` 三個 tab，並以單一 selection state 保存 Source、focus question、Concept、Edge 與 Evidence IDs。Reader 顯示 84 行 exact source，Map 保留五階段與七條 Teaching Propositions，Graph 使用相同 snapshot 的 9-node／7-edge local learning-unit read model；跨視圖 validator 會在 label、direction、relation、Evidence、Source 或 snapshot 漂移時 fail closed。下一步為一種 scaffolded retrieval interaction。

第 5 步已於 2026-09-16 完成：使用者可選一條 Edge，補上 linking phrase，再並列人工審核的完整 Teaching Proposition、Evidence proposition 與 exact source lines；一致與不一致都只作文字比較，不轉成 mastery。另新增獨立的 `kgnote.guided-review-request.v1`／`kgnote.guided-review-interaction.v1` 契約：瀏覽器只提交 snapshot-bound 身分、回答與 hint 使用，伺服器從 trusted Guided Map 重建題目、canonical proposition 和 Evidence，拒絕 stale context，並以 atomic create 保存 append-only review；不放寬既有 Concept free-recall 契約。

第 6 步已於 2026-09-16 完成第一版驗收：原文 fixture 的 SHA-256 與 84 行 source read-back 由自動測試鎖定；Mac 與 iPad responsive 尺寸均已實際操作三視圖，這次再從 UI 完成「用戶端＿＿＿＿HTTP 請求」、保存、重新載入並由 schema validator 讀回落盤紀錄。第一版已形成 Reader → Guided Map → Graph → retrieval → append-only evidence 的本機閉環；一般化 HTTP Reader／Map catalog 與自動生成仍留在後續，不阻塞個人使用。

### Phase 3b 驗收問題

1. product owner 是否能從 Reader 知道目前在學哪一小段、Map 正在回答哪個問題？
2. Map 的每條核心 Edge 是否能不靠猜位置就讀成一句自然中文？
3. 同一 Concept／Edge 在三視圖是否保持相同名稱、方向、語意與 Evidence？
4. 從任一視圖能否在兩次操作內回到 supporting original text？
5. product owner 能否在關閉原文後重述主要流程，或指出一條仍不理解／不同意的關係？
6. Graph 是否在已有輪廓後提供有用探索，而不是再次造成迷失？

上述問題若未通過，就修正 learning unit、relation 或跨視圖 mapping；不以增加節點、動畫或模型生成量掩蓋問題。

## Phase 4（重排）- Gemini reviewer／RAG 候選

既有 reviewer context 與 append-only review 是可重用的工程基礎，但 2026-09-19 審查後，模型接入不得先於 Phase 3c 的 LearningTarget、活動／支援狀態、Attempt identity、教材審查與人工 rubric baseline。任何自動選題、完整 chat UI、Graph RAG 或閉卷測驗不得阻塞閱讀、針對疑問的解說與 session 脈絡延續。

- [x] 只取 canonical concept note、相關 evidence、1-hop neighborhood 與 previous confusion 作 reviewer context。
- [x] 先由人工選 Concept 完成一題一答與四類自評，不做自動 scheduling。
- [x] append 回答、hint 使用、outcome 與 source context，不自動寫成「已理解」。
- [ ] 對應垂直切片通過安全與人工 rubric baseline 後，才接入 consent-gated Gemini reviewer；輸出 `CORRECT | PARTIAL | INCORRECT | INSUFFICIENT_EVIDENCE` 與最多兩句 correction summary，但結構化 rubric 差異、Evidence refs／revision 必須另可檢視。保留使用者申覆，模型不能自行把來源主張升為正確答案。
- [ ] 是否加入 Graph RAG，須先由 Phase 3c-7 證明跨來源或多步關係任務需要；一般回答先以 reviewed claim／Evidence retrieval 為 baseline。

## Phase 5 - 低摩擦曝光與多端入口

- [ ] Phase 3c-4 先完成單機最小 due queue；Phase 5 只擴充低摩擦 feed／提醒，不另建第二套排程真相。
- [ ] hint fading 依 LearningTarget 與 Attempt history 使用：術語可從提示到自由輸出；機制／應用題優先換 context、條件與案例，不固定為逐字填空序列。
- [ ] 語音輸入、review feed、LINE/LIFF 或 LINE MINI App 在當時再做產品與隱私決策。

## 停車場（不打斷當前主線）

記錄格式：`date | idea/problem | why not now | expected phase`

- 2026-08-14 | Neo4j/專用 graph database | Markdown/YAML 足以驗證 Phase 3c；關係整合價值不等於需要 graph database，引入會增加 migration 與 sync 問題 | Phase 3c-8 證明規模／查詢需求後再評估
- 2026-08-14 | Graph RAG 與 reranker | 先證明 concept/evidence graph 本身可用；否則 RAG 只是放大壞資料 | Phase 4
- 2026-08-14 | 遺忘曲線、最佳化／自適應排程 | Phase 3c-4 只做可解釋 due queue；最佳間隔需真實延遲資料，不能先猜使用者記憶模型 | Phase 5 後重新評估
- 2026-08-14 | LINE/LIFF/LINE MINI App | 它們是入口而非核心，且屆時應重新查證官方產品狀態 | Phase 5
- 2026-08-14 | 批次匯入全部 LLM Wiki | 需先知道使用者真正保留哪些 Note／Target，並從小 fixture 量測 hallucination、relation error、merge conflict 與成本 | Phase 3c-8 後重新評估
- 2026-09-19 | 大型 compound／hierarchical graph | Phase 3c-5 已採低成本 visible group＋topic scope＋ego prototype；compound container、聚合邊與展開動畫的語意／操作成本較高 | Phase 3c-7 證明局部 Graph 有額外價值後再評估
- 2026-09-19 | 自動 community detection／centrality 排重要概念 | 群集與中央性不能替使用者決定用途或學習重要性，也可能把 layout 訊號誤當 ontology | 有跨來源規模與人工標註資料後再研究
- 2026-09-19 | 全域 mastery score／複雜自適應 | 目前缺可靠 LearningTarget、獨立 Attempt、錯誤與延遲表現；先保存可觀察事實 | Phase 3c-7 之後另立 contract

## 驗收記錄

| 日期 | 切片 | 結果 | 證據／限制 |
| --- | --- | --- | --- |
| 2026-09-22 | `KG-VAL-03` 熟悉材料 高熟悉材料 catalog 接入 | implemented；automated tests passed；browser smoke passed；待 product owner 評估熟悉內容的呈現 | 從既有本機 Whisper 逐字稿抽取有界節選，保存原始絕對位置與 SHA-256；使用與 OS／BitePacer 相同的 Learn／Soak／Practice renderer，按設計演變、平台玩法與文化引用投影 4 個閱讀 scope、9 Concepts 與 5 條來源內 Claim。Review 明確只驗證「逐字稿如此描述」，不冒充外部查核；熟悉材料 是熟悉材料的 UI／定位觀察用途，不永久對應能力等級，也不因熟悉或高分宣稱學習效果。需求 guard 84 requirements／37 scenarios structural PASS（不冒充語意或學習效果 PASS）、Python 238、Web 54、`git diff --check` 通過；browser 實走 catalog → Learn 局部 scope／Local Graph → Practice 作答前隔離 → Soak 無作答曝光，未建立 Attempt。 |
| 2026-09-20 | Phase 3c P0 Learn → Practice 可用雛型 | implemented、automated tests passed、browser smoke passed、ready for manual test；尚未由 product owner manual acceptance，也未驗證學習效果 | 新入口 `/learn.html` 以 OS fixture 提供來源名稱、breadcrumb、五個 topic overview、150 行 immutable Source、Concept／Claim 按需解說、Evidence／exact locator 與可選 LearningNote 入口；閱讀不要求任何輸入。獨立 `/practice.html` 不載入 Map／Graph／Reader／canonical answer，使用者主動選關係回想或自由解釋；首次輸入／hint 才建立 Attempt draft，提交後才回傳答案、rubric、Evidence 與具體比較方向，錯誤／「不知道」照樣保存，Retry 產生新 client ID，reload read-back。新增 snapshot-bound ClaimReviewOverlay 封鎖 `Interrupt → Driver` 出題但保留原文警告；修正 Evidence→0/1/N Claims，不依 proposition array order 自選。Attempt v1 使用 atomic write、stable client ID、item revision、raw response、confidence、hint events、support／exposure、outcome、feedback、entry context 與 Source／Claim／Evidence refs；相同 submitted payload 重送 unchanged，不同回答 409 conflict。完整 Python 211 tests、Web 43 tests、HTTP／persistence／malformed／stale／answer-leak regressions通過；browser 實走 Learn→Evidence→自由回答→hint→submit→retry→reload，兩筆 read-back、console 零 error、desktop 與 1024×768 override 無 page-level overflow。人工 feedback 仍是 baseline，非「不知道」自由文字先記 `INSUFFICIENT_EVIDENCE`，尚無人工 outcome 修訂 UI、live reviewer、due queue 或 Graph lens。 |
| 2026-09-20 | note-first／retrieval-first 回饋分析寫入 roadmap | 完成（產品裁決與可執行驗收；功能尚未實作） | 在 H0 finding 下新增三層分界表（資訊系統化／形成理解／可觀察輸出）、H0 能／不能推出的結論、四項學習科學設計依據與外推限制、七項原 Phase 3c 主張撤回／替換表，以及下一次 formative test 的三個主要觀察。明訂先前外部審查與 Codex 都曾加入超出使用者需求的固定活動順序，現已撤回；個人產品可依明示需求修改預設，不用先靠實驗取得「可以不寫筆記」的許可。研究只支持候選活動與需分開觀察熟悉／提取，不證明 KGnote、新順序或 Graph 效果。H0 仍是 `aborted → modify` 且不評分；下一輪比較實際「閱讀＋AI 解說」方式，只驗證能否學進去、按意圖切換與延續脈絡。 |
| 2026-09-19 | note-first／retrieval-first 二分校正 | roadmap 與核心契約已改為可往返的學習工作區；功能尚未實作 | 依使用者補充，撤回「不先寫筆記就改成先進 retrieval」的過度轉譯。Phase 3c 現以閱讀原文／結構化導讀、針對疑問的摘要／拆解／例子／對比、可選練習與可延續學習脈絡為核心；閱讀、追問、練習、回來源及結束可以往返，一次 session 不必練習。新增 3c-W0 工單；LearningTarget 可直接來自 Source／教學重點／使用者問題，不依賴筆記；有支援的模仿／部分完成／填空與無輔助回憶分別記錄，不把前者當失敗的 retrieval。同步修正產品契約與跨視圖契約：派生解說可換說法，但需保留 purpose／kind／source anchors／provenance，不能偷改 canonical claim。此列是需求與計畫校正，不宣稱新流程已完成或具有學習效果。 |
| 2026-09-19 | 真實陌生 BitePacer micro-source H0（note-first protocol） | 中止並決定 `modify`；未進行效果或可用性評分 | 前測在教材未顯示時回答 `0`，符合陌生材料條件；來源 SHA-256 `1894be5e931ab49dba123d4a57f0ea2dbcd7bfe372faa5f3bd99bff70d385916`、upstream commit／hash 與 source-only Reader read-back 均通過，canonical Graph 為 0 nodes／0 links。普通 Markdown 條件開始後，使用者在尚未產生任何筆記前指出 note-first 不符合使用意圖，故 server／頁面立即停止；run record 保存為 `aborted → modify`，rubric、lookup、unaided response、confidence 與分數保持空值，只有預先建立的空白標題檔，不把它視為 learner output。原 manifest 保留不改寫；中止只確認 protocol mismatch，不表示當時沒有能力整理、不表示筆記在所有時點無效，也不證明閱讀優先、提取優先或任何替代流程較有效。下一版 H0-W 必須比較實際使用的「閱讀＋AI 解說」與 KGnote 同類工作區，允許不寫筆記、不進練習並正常結束。中止 record 經 schema＋manifest read-back；完整 Python 199 tests、Web 38 tests、`git diff --check` 通過。 |
| 2026-09-19 | 3c-B0 versioned Markdown LearningNote 最薄垂直切片 | 工程閉環完成；Formative／實體 iPad 驗收 pending | 新增 `kgnote.learning-note.v1`／save command schemas、human-editable `notes/*.md` store、完整 bytes 強 ETag、`If-Match`、server revision、client `save_id` 冪等、process-local concurrent writer serialization、same-directory atomic replace、stale／ID reuse conflict 與 write-failure rollback；HTTP route 由 `--notes-root`／`--enable-note-writes` 明確開啟，關閉 write flag 後仍可讀。`learning-note.html` 可編輯 headings／lists／paragraphs、保存、重開、保留 conflict 草稿、notebook literal search、回到 hash 驗證的 exact Source excerpt；preview 只建立 allowlisted DOM，raw HTML／Markdown image fail closed。零 Concept／Edge／Evidence 的 source-only store 亦可回來源，canonical Phase 0 與 Web fixture diff 為零。Browser 實測 revision 1 → reload/read-back、搜尋、來源 `L3-L13`、窄版單欄無水平 overflow；Python 先修正既有 canonical `L7` 單行 locator 到 Reader `L7-L7` adapter 相容，不改 Evidence bytes。完整 Python 195 tests、Web 34 tests、`git diff --check` 通過；初次 full run 曾抓到 PUT 舊行為 404/405 regression，修正後已完整重跑。本列不宣稱已完成真實陌生材料 H0、Mac/iPad 人工輸入體驗、跨 process／外部 editor 的 OS-level file lock、block editor、AI proposal、LearningTarget 或 Attempt。 |
| 2026-09-19 | Phase 3c roadmap 第二輪可執行性審查 | 完成（規格修訂；功能尚未實作） | 依後續審查修正 Evidence→多 Claim 的 `.find()` 錯譯與 `needs_revision`／舊 validator 相容缺口；選定獨立 ClaimReviewOverlay、document-level LearningNote、versioned Claim、Attempt exposure state、絕對 1／3／7／21-day milestones、三種獨立 gate、H0 與 test manifest。新增 3c-S0／S1／B0／B1／X0 五張可直接開工的垂直工單，含修改模組、非目標、正負向／復原驗收與測試證據；Graph 改為 Baseline 通過 formative gate 後的條件式工作。此列只表示 roadmap 已具備下一批 issue 級決策，不表示 selection、overlay、筆記 writer、Attempt 或實驗已完成。 |
| 2026-09-19 | ChatGPT 6 Pro 審查 → 具體 roadmap 盤點 | 完成（歷史規劃；部分產品假設已於 2026-09-20 撤回） | 完整讀取 `docs/chatgpt_6pro_20260919_review.txt` 的裁決、研究表、程式診斷、Graph scope 方案、資訊架構、資料模型、遷移、實驗與優先順序；當時將 roadmap 驗收中心改為「可修訂理解＋真正閉卷／延遲應用」，新增 Phase 3c-0 至 3c-8、Baseline／Graph variant、公平比較、停止條件與逐節覆蓋索引。保留 Phase 0–3b 已完成事實，但三層模式降為待證偽假說。2026-09-20 已進一步撤回其中「使用者需先形成筆記」及可能導向 retrieval-first 的固定主線；仍保留 Source／Evidence、claim review、exposure、idempotency、Graph scope 等安全要求。此列只記歷史決策，不再代表當前主線。 |
| 2026-09-19 | 外部研究型設計審查資料包 | 完成（尚未送出） | 在 ignored `output/chatgpt-pro6-design-review-2026-09-19/` 建立純文字資料包：5 份核心 design contracts／roadmap／research index、12 份 OS 三視圖實作／schema／fixture／test、1 份當前 UI 與主題分區問題說明，以及一份要求 ChatGPT Pro 主動查找學術證據的完整 prompt。Prompt 以「協助記憶重要概念、把陌生資訊做成系統性筆記」為高於 Graph／三視圖的原始需求，要求先做 zero-based redesign，再判斷現有元件應保留、補強、降級、刪除或根本重構；同時把 accepted contract 當待證偽假說，分開審查理想與程式、核對 citations、比較 visible cluster／group-scoped graph／ego network／compound graph／取消獨立 Graph，並用 熟悉材料／OS／BitePacer 三種熟悉度提出可證偽測試。資料包未含 key、`.env`、私人完整對話或 review 紀錄，亦尚未上傳或產生任何外部寫入；它只準備審查材料，不代表目前已接受 Topic Lens 或其他重構方案。 |
| 2026-09-18 | Phase 3b OS 中間難度複習單元 | 完成（人工審核 fixture） | 將使用者提供、曾修習一學期但已短期未接觸的 OS 摘要完整保留為 150 行／10,571 bytes Source，SHA-256 鎖定；第一張地圖只回答「OS 如何在安全與效率之間管理程式、CPU 與硬體？」，以 5 個 view-only 群組組織 16 Concepts、10 Teaching Propositions 與 8 筆 accepted Evidence。Reader／Map／Graph 由同一 read model 投影，Graph 依群組內關係鏈橫向排列，iPad viewport 檢查為 0 node overlap、0 page/canvas horizontal overflow；從「應用程式 向核心提出 系統呼叫」切到 Reader 時正確標亮 L22-L26。關係提取練習輸入「向核心提出」可比對並 append 保存，read-back 綁定相同 Source／Edge／Evidence，未修改教材或產生理解分數；console 無 error／warning。Web 32 tests、Python 182 tests 全通過。這是用來觀察「舊知複習」UX 的人工內容骨架，不代表已驗證整篇 OS 摘要的技術正確性，也不代表已測得學習效果；BitePacer 保留作陌生內容對照，熟悉內容 fixture 尚待加入。 |
| 2026-09-16 | 真實單篇導入的人類可判讀 preview 與 phrase review CLI | 完成（mock-verified；未真實外送） | `extract`／`apply` 提供 Concept 名稱、Edge 方向／relation、Evidence proposition、locator 與 exact source lines；越界、`CONFLICT`／`REJECT` fail closed。`phrase-preview` 從第一階段 immutable ledger 建立 snapshot-bound phrase-only context 與獨立 consent digest；`phrase-extract` 只在 exact digest 後建立 Gemini transport，固定一 request／零 retry／2,048 output-token cap，模型只能回 `{edge_id, linking_phrase}`。結果以 atomic rename append `manifest.json`、exact raw response 與 pending candidate set，重播逐位元驗證 candidate、零 transport 且不需 key。`phrase-review` 要求每條 Edge 恰有一筆 accept／correct／reject，先輸出完整 reviewed-set digest，批准後以 exclusive create append；不同第二份 review 回 conflict。Fresh Evidence 保留 `unreviewed`，所以人工接受短語仍是 `guided_map_promotion_eligible: false`，不會暗自改 Guided Map。Python 182 tests、Web 29 tests、`git diff --check` 通過；全部 provider 測試使用 mock，未讀真實 key、未連網或產生費用。下一步須在再次確認 Gemini 價格／資料邊界並取得 fresh authorization 後，才以小型 synthetic/redacted source 做 live smoke。 |
| 2026-09-16 | Phase 3b linking-phrase retrieval + append-only review | 完成（本機 fixture） | 單題 `subject ＿＿ object` 練習可在 7 條 reviewed Teaching Propositions 間選擇、顯示 deterministic 首字／字數提示，並比較 normalization 後的輸入；答後並列 canonical sentence、全部 supporting Evidence propositions、locators 與 exact source lines，不輸出 mastery／understood／百分比。新增獨立 versioned Edge-review request／record schema、server-trusted prompt reconstruction、snapshot／learning-unit／Source／Edge stale validation、atomic append 與 idempotent read-back；UI 只有在對照教材後才可保存，編輯回答會使待存結果失效。紀錄寫入 explicit ignored review root，不修改原文、Guided Map、Graph 或 canonical store。Web 29 tests、Python 169 tests 全通過；HTTP 測試涵蓋 configured endpoint、security headers、真實 append 與 stale rejection，未配置時 endpoint 為 404。Browser 實際選「用戶端 → HTTP 請求」、輸入「主動送出」、對照並保存成功；reload 後檔案仍存在，schema read-back 為 valid／`matched_reviewed_phrase`／`hint_used: false`，console 無 error 或 warning。 |
| 2026-09-16 | Phase 3b Reader／Map／Graph 共享焦點 | 完成（人工 fixture） | `guided-map.html` 現提供 `閱讀｜學習地圖｜探索` 三個 ARIA tabs，共用一份 Source／focus question／Concept／Edge／Evidence selection。Reader 逐行呈現 SHA-256 鎖定的 84 行原文與 5 筆 Evidence 標註；Map 使用原有 5 群組／9 Concepts／7 Teaching Propositions；Exploration 使用相同 snapshot 的 BitePacer Graph Read Model，顯示 9 nodes／7 directional edges，edge label 直接取同一 Teaching Proposition linking phrase。選 Map relationship 後，Reader 會標亮相同 Evidence line ranges，Graph 會標亮同一 subject Concept／Edge；Graph 可在第二次操作切回已標亮原文。新增 cross-view validator，snapshot、Concept label／summary／evidence、Edge endpoints／relation／evidence、Evidence proposition／locator、Source label／digest 任一 drift 都 fail closed；unknown selection 亦拒絕。Web 27 tests、Python 163 tests 全通過。Browser 實際以 iPad 1024×768 responsive viewport 驗證 `ngrok 通道 → Flask 路由` 在三視圖保持同一句焦點、Reader 2 Evidence／33 lines、Graph 1 edge／1 subject node，無 page-level horizontal overflow 或 console error／warning。此切片不保存 UI selection 到重開後、不做練習／評分，也尚未把人工 fixture 改成一般化 HTTP Reader／Map endpoint。 |
| 2026-09-16 | Phase 3b BitePacer expert-skeleton Guided Map | 完成（獨立 Guided Map） | 新增零 runtime dependency 的 `guided-map.html`、純 JS fail-closed read-model validator／projector 與 responsive hierarchy renderer。畫面固定回答「一則 LINE 訊息如何抵達 product owner Mac 上的 BitePacer？」，依契約呈現 5 個 view-only 群組、9 個相同 stable-ID／中文 label Concepts、7 條保留 subject／object 方向與 reviewed linking phrase 的 Teaching Propositions；群組沒有進入 Concept 集合。每條關係可一次展開 1–2 筆 accepted Evidence，並以 `Lx-Ly` locator 顯示 exact numbered source lines；Web source fixture SHA-256 與 read model 鎖定的原文 digest 相同。Web 24 tests、Python 163 tests 全通過；Browser 以桌面及 1024×768 iPad responsive viewport 實際驗收，五階段／七關係均載入、概念定義與原文展開可操作、最小 summary 高度 44px、無 page-level horizontal overflow，console 零 error／warning。此切片刻意不把既有 Phase 0 Graph 假裝成 BitePacer Graph；`探索圖` 標示待串接，Reader／Map／Graph selection state 與 HTTP Reader boundary 留給下一項。 |
| 2026-09-16 | Phase 3b explicit-source Reader application boundary | 完成；HTTP／UI pending | 新增 `kgnote.reader-query.v1` 與 `kgnote.reader-application.v1` Draft 2020-12 schemas、safe validator、固定 no-store／CSP／no-referrer／nosniff／frame-denial policy，以及 `load_reader(explicit_root, query)`。Caller 只能傳 snapshot digest、registered Source ID 與可選 `line_range`，不能傳 path；adapter 只解析 Source record 登記的 `raw/*.md`，拒絕 absolute／traversal／非 canonical path、symlink、非 Markdown、missing、超過 2 MiB、hash mismatch、invalid UTF-8、stale snapshot、malformed registered Evidence locator 與越界／反向 locator。BitePacer read-back 為 exact 2,134 bytes／84 行，`L3-L18` excerpt 未改寫，並解析 1 Evidence、1 Concept 與 1 Edge stable ID；只有 accepted／corrected Evidence 可成為 annotation，閱讀不建立 LearningEvent。15 項聚焦測試與完整 163 項 Python regression 通過，原始 fixture bytes 前後不變，無 write／network／process／clock。尚未建立 HTTP route、Markdown renderer、highlight UI 或共享 selection state；Guided Map 已於同日下一切片完成。 |
| 2026-09-15 | Phase 3b Teaching Proposition／Guided Map read model | contract 與 projection 完成；UI pending | 決定 Teaching Proposition 不改寫 canonical Edge、也不放進 renderer 私有欄位，而是存在人工審核、snapshot-bound 的 `kgnote.guided-map-spec.v1`；`kgnote.guided-map-projector.v1` 純記憶體接回 Graph Read Model，輸出 `kgnote.guided-map-read-model.v1`。BitePacer golden 含 5 個 view-only 群組、9 個相同 stable-ID／中文 label Concepts、7 條保留 canonical 方向／relation／Evidence 的中文命題、5 筆 accepted Evidence；stale snapshot、Evidence drift、重複分組、空泛 linking phrase、Learning／soft edge、未審 Evidence、dangling reference 與非 deterministic order 均 fail closed。新增 13 項聚焦測試，完整 Python regression 148 tests 通過。此切片未修改原文、canonical store 或 Web UI；後續 Reader boundary 見 2026-09-16 驗收列。 |
| 2026-09-15 | 三層學習模式與跨視圖一致性契約 | 設計完成；runtime pending | 接受 `原文閱讀 → 階層式學習地圖 → 關係提取練習 → 局部知識圖譜` 為漸進式學習路徑，新增 `docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`，鎖定 immutable source、Concept identity／locale label、Teaching Proposition、Edge 方向、Evidence、不確定性與跨視圖焦點；明訂導覽 grouping 不成為 canonical Concept／Edge，Graph-first 是整合原則而非陌生主題的預設畫面。研究依據包含 concept-map meta-analysis、prior-knowledge × hierarchy/network、multiple-representation、split-attention、scaffold fading 與 retrieval practice；沒有研究直接證明完整三視圖產品組合，故仍視為需由 BitePacer fixture 實機驗證的 evidence-informed hypothesis。本列只代表 contract／開發方向完成，Reader、Guided Map、Teaching Proposition read model、validator 與同步 UI 尚未實作。 |
| 2026-09-15 | 中文 BitePacer 迷你計網個人使用樣本 | 完成（LAN smoke） | 從 2026-08-14 ChatGPT 教學對話選出 client/server → IP/port → loopback → HTTP → Flask route → ngrok tunnel 的小型完整段落，人工審閱建立 9 個中文主顯示 Concept（保留英文技術 alias）、5 段中文 Evidence、1 個 explanation event 與 10 條有來源 edge；dry-run 26 CREATE、apply/read-back 26 canonical records、Web view 10 nodes/10 links。介面學習文字中文化，Evidence 只顯示 proposition 與教材位置，confidence/review status/extractor version 仍保存在 Markdown 而不干擾作答。以 1024×768 iPad viewport 實際驗收本機與 LAN viewer，中文圖與「本機回環位址」複習題可開啟、console 零 error/warning。此樣本用來驗證中文資工學習；英文口語教材應另作跨語言對照，不混入本次驗收。 |
| 2026-09-14 | 個人可用閉環第一版：Web 自由回憶與 append-only review | 完成（本機人工自評） | Concept detail 新增 `Review this concept`；題目與 hint deterministic 來自 bounded reviewer context，作答後顯示當下 Evidence，結果只允許 `CORRECT / PARTIAL / INCORRECT / INSUFFICIENT_EVIDENCE`。保存為 store 內 `reviews/review_<sha256>.md`，含 question、response、hint、snapshot、evidence IDs、時間與 `human-self-assessment.v1` provenance；stale context、malformed input、非 Concept 與 unsafe directory fail closed。此版不呼叫 Gemini、不產生費用、不宣稱 understood；Gemini reviewer 與 correction 留待另建 consent-gated adapter。 |
| 2026-09-08 | Phase 4a reviewer-context application + one-answer assessment contract | 完成（mock-verified） | 新增 explicit canonical store → full graph projection → 人工指定 Concept reviewer context 的 `kgnote.reviewer-context-application.v1` boundary；store/projector/context failures 只回 stable component/code/path，不回顯私人 root 或輸入。新增 `kgnote.review-assessment-prompt.v1` exact prompt，綁定 snapshot、Concept、bounded context、一題、使用者回答、hint boolean、reviewer/prompt version 與 response contract；不含 raw Markdown/path。新增 strict offline response adapter 與 Draft 2020-12 schema，只接受 `CORRECT \| PARTIAL \| INCORRECT \| INSUFFICIENT_EVIDENCE` 加最多 500 字／兩句 correction；extra fields、`UNDERSTOOD`/mastery、第三句、malformed/non-UTF-8 均 fail closed。Phase 0 Correlation read-back 為 3 個 1-hop neighbors、3 links、3 Evidence、1 Source；133 個 Python tests 全通過，包含 determinism、copy safety、immutable result 與封鎖 filesystem write/network/process。此切片以 raw mock responses 驗證，未產生題目、未呼叫 provider、未保存 ReviewInteraction、未建立 Web 作答 UI。 |
| 2026-09-08 | 個人可用閉環：獨立 apply approval → disposable vault → viewer read-back | 完成 | `scripts/import_markdown.py apply` 只從相同 run ID／fingerprint 的 immutable ledger replay accepted candidate，不讀 API key、不發 transport；沒有或錯誤的 apply digest 只回傳最新 dry-run，exact digest 才交給既有 transactional apply/read-back。首次 synthetic integration 為 12 writes（11 canonical + 1 byte-identical raw）、11 canonical records；第二次須依當下 UNCHANGED plan 取得新 digest，批准後為 0 writes。另在 `/private/tmp/kgnote-personal-use-smoke-v1` 建立 repository 外 synthetic artifact，read-only application 回 `ready`、5 nodes／3 links／2 Evidence／1 Source。桌面首驗發現 Web runtime 誤用 checked-in Phase 0 7-node fixture 作 facet catalog，對 5-node store 送出 stale snapshot query，故安全顯示 unavailable；canonical 未變。修正 runtime fresh catalog 後桌面 Mac 1440×1000 重驗 PASS：full 5/3、Concept/Event panel、1/2/3-hop、四組 filters、pan/zoom/reset 與關閉重開均正常，console 零 error/warning，無 mutation/path/raw body/stable-ID 洩漏、overflow 或明顯 label collision。驗收前後皆為 12 files，tree SHA-256 同為 `0b7a60ad35f78cd1b099e3143887f86c28b44f3d41fcf5270cbad63b2839822e`；截圖位於 `/private/tmp/kgnote-personal-use-smoke-*-retest.png`。未使用私人資料、未真實連網或產生費用。 |
| 2026-09-08 | Phase 4a evidence-grounded reviewer context | 完成 | 新增 `kgnote.reviewer-context.v1` schema、contract README 與純記憶體 projector。人工選定 Concept 後只輸出 canonical focus fields、方向中立但保留原方向的 incident 1-hop nodes/links、focus／incident-link Evidence、supporting Sources，以及 explicit `confusion` LearningEvent／`confused_with` link 支持的 previous confusion；question、exposure、explanation、encountered 與 unresolved association 不會被提升為 confusion 或 understood。Phase 0 Correlation read-back 為 3 neighbors／3 links／3 Evidence／1 Source／0 explicit confusion；schema validation、unknown/event focus、malformed model、安全錯誤、determinism、copy safety、input immutability 與禁止 filesystem/network I/O 均通過。Python 125 tests、Web 18 tests 全通過。本切片不含 store adapter、題目生成、reviewer transport、回答或 canonical review write。 |
| 2026-09-08 | 個人可用閉環：真實單篇導入 dry-run 入口 | 完成（mock-verified） | 新增 `kgnote.live-import.v1`，將明確單篇 Markdown 的 exact consent preview → 至多一次 injected provider transport → immutable ledger／offline schema validation → normalization → canonical dry-run 串成同一條邊界，不再要求人工製作 replay JSON；provider reject 會在 normalization/store read 前停止，成功也不自動 apply。新增兩階段 `scripts/import_markdown.py preview\|extract`：digest 不符時不讀 key、不建 transport、不寫 ledger/vault；digest 相符後才從 `GEMINI_API_KEY` 建 Gemini transport，輸出另一個 apply digest。Python 120 tests 通過，包含 provider candidate read-back 為 11 個 CREATE、未批准零 transport/ledger/write、malformed response fail closed、source/input 不變與輸出不洩漏 key/source body。本切片未真實連網、未產生費用、未 apply；CLI 明示目前只有單 request／8,192 output-token 技術上限，尚無可強制的幣值成本上限，故首次 live smoke 前仍須重新查證 provider 價格、billing／retention 邊界並取得 fresh authorization。 |
| 2026-09-08 | 個人可用閉環優先順序 | 規劃完成 | 當前最高優先已改為真實單篇 Markdown → Gemini consent/extraction → dry-run approval → canonical apply/read-back → 個人 vault Web Graph → 人工選 Concept 一題一答 → append review evidence；明確延後 scheduling、完整 hint fading、語音／LINE、公開部署、批次匯入與非阻塞視覺 polish。本列只記錄開發導向，尚未宣稱真實 Gemini 呼叫或 Phase 4 功能已完成。 |
| 2026-08-14 | 專案治理與設計基線 | 完成 | 建立 agent 規範、產品 contract、最小資料模型、分期計畫與來源索引；尚無 executable code，不宣稱 extractor 或 Obsidian flow 已驗證。 |
| 2026-09-07 | Phase 0 data contract 與 synthetic fixture | 完成 | `fixtures/phase0-obsidian/` 共 20 筆 canonical records；read-back 通過 unique ID、reference integrity、edge policy、source SHA-256、locator 與 wiki link 檢查。桌面版 Obsidian 驗收確認 Graph 節點互連、無 unresolved/ghost links，Correlation／Confounder／Counterfactual 三條 Concept → Evidence → Source 路徑皆成功；counterfactual 僅為 unresolved soft association，提問／應用未被宣稱為 understood。截圖保留於 repository 外的 `/tmp/kgnote-obsidian-qa-graph.png` 與 `/tmp/kgnote-obsidian-qa-navigation.png`。 |
| 2026-09-07 | Phase 1 versioned extraction schema contract | 完成 | `scripts/run_tests.sh` 通過 6 個 contract test methods 與 21 個具名 malformed cases；valid input/output、版本 fail-closed、strict fields、RFC 3339 timestamp、local refs、三種 edge policy、provenance 與禁止 proficiency claims 均已驗證，Phase 0 read-back 亦通過。JSON Schema 無法單獨證明跨 record local ref 存在／唯一或 input/output source 相同；目前只對 valid fixture 做 read-back assertion，正式語意驗證留給後續 normalization 切片。 |
| 2026-09-07 | Phase 1 single-file Markdown source importer | 完成 | `scripts/run_tests.sh` 共 14 個 tests 通過；驗證 Phase 0 raw source 可完整 UTF-8 round-trip、SHA-256 對 exact bytes、重跑 deterministic、只讀明確檔案、無 network/vault write，以及 missing/directory/extension/read/UTF-8/empty 與 metadata schema failures 的安全 code/path。Importer 刻意不解析 front matter，Source identity 與 locator basis 仍由 caller 明確提供；batch scan、metadata inference 與 extraction 不在本切片。 |
| 2026-09-07 | Phase 1 offline extraction-response boundary | 完成 | `scripts/run_tests.sh` 共 24 個 tests 通過，其中 21 個具名 rejected-response variants 涵蓋 strict JSON、root/collection、adapter-owned field、candidate schema 與 adapter metadata。Accepted result 注入 Source/version/timestamp，Evidence/Event Source ID 一致；accepted/rejected 皆 deterministic 且保存 exact raw response SHA-256，repr/rejection 不洩漏內容。測試證明無 network/vault write，Phase 0 read-back 通過。跨 collection local-ref 存在／唯一仍留給 normalization；provider API、raw-response persistence 與 retry 尚未實作。 |
| 2026-09-07 | Phase 1 deterministic normalization 與 local-reference integrity | 完成 | `scripts/run_tests.sh` 共 34 個 tests 通過；golden read-back 固定 4 Concepts、2 Evidence、1 LearningEvent、3 Edges 與 10 筆 local-ref mapping。`kgnote.normalize.v1` 驗證 duplicate/dangling/wrong-kind/canonical refs 與 Source mismatch，使用 typed/versioned full SHA-256 stable IDs，且 input/list/local-ref permutation 不改 canonical records；identity collision 明確回 conflict，不自動 merge。AI Concept/Evidence 預設為 `needs_review`／`unreviewed`，不推論 understood/proficiency。此切片純轉換且不讀 existing vault、不寫檔、不連網；existing-note comparison、dry-run 與 apply 留給後續 Issue。 |
| 2026-09-07 | Phase 1 deterministic dry-run planning | 完成 | `scripts/run_tests.sh` 共 44 個 tests 通過；golden preview 涵蓋 CREATE、UNCHANGED、UPDATE、CONFLICT、REJECT。`kgnote.dry-run.v1` 比較 normalized candidates 與 caller-supplied canonical snapshot，fail-closed 驗證 snapshot、typed IDs、schema 與 projected references；只允許 Concept evidence provenance 的純新增 update，保留既有人工 Concept/Evidence review state，移除或其他同 ID 差異均為 conflict。輸入/list 次序不影響結果，result copy-safe，且未讀寫 vault、未 merge/apply、未接網路或模型。Snapshot 目前必須由 caller 提供完整 Source/reference records；filesystem adapter、Markdown render、approval 與 idempotent apply/read-back 留給後續 Issue。 |
| 2026-09-07 | Phase 1 canonical-store adapter、approved apply 與 read-back | 完成 | `scripts/run_tests.sh` 共 52 個 tests 通過；golden integration 在 disposable store 完成 read → normalize → dry-run → exact SHA-256 approval → 9 CREATE／1 UPDATE → read-back，第二輪全為 UNCHANGED 且零寫入。`kgnote.canonical-store.v1` 只讀 explicit root 的五個 canonical directories，Phase 0 人工 fixture 可 read-back 20 筆；拒絕 malformed YAML/front matter、unsafe ID/path、symlink、stale precondition、既存 create target、blocking/forged plan 與錯誤 approval。UPDATE 保留人工 review state 與 Markdown body，建立 recoverable backup；模擬 mid-write 與 read-back mismatch 均 rollback canonical files。未對真實 vault 或 Phase 0 fixture apply；delete/rename/merge、並行 writer、真實資料導入與視覺驗收仍不在本切片。 |
| 2026-09-07 | Phase 1 consent-gated extraction run 與 local ledger | 完成 | `scripts/run_tests.sh` 共 61 個 tests 通過；golden fake-transport flow 完成 deterministic preview → destination/content-bound consent → 單次 transport → offline schema validation → restrictive immutable ledger，exact replay 為零 transport calls。涵蓋 redaction version/source immutability、malformed/schema-invalid/non-UTF-8 response、timeout/auth/rate-limit/provider/transport errors、缺 usage、ledger failure、run-ID conflict、unsafe path/symlink、transport metadata mismatch 與 repr redaction；accepted/rejected/error raw bytes 與 hashes 均留在 explicit local ledger。未選定真實 provider、未讀 secrets、未連網或產生費用；自動 PII 判斷、retry/streaming/batch 與 live smoke test 不在本切片。 |
| 2026-09-07 | Phase 1 Gemini real-provider transport | 完成（mock-verified） | `scripts/run_tests.sh` 共 67 個 tests 通過；ADR 依 2026-09-07 官方文件選定 `google-gemini` / stable `gemini-3.7-flash` 的非串流 REST `generateContent`。Transport 僅接受 caller 注入 key，固定一 request、零 retry、8,192 output-token cap，使用 provider structured JSON schema，保留 exact candidate text、response ID 與實際 usage，並安全映射 auth/rate-limit/timeout/provider/network failures。Synthetic E2E 完成 preview/consent → mocked provider → offline validation → immutable ledger；未讀 env/file/keychain/vault，未真實連網或產生費用。Paid-project、region、retention/ZDR 狀態與真實 schema adherence 尚未 live 驗證；首次 live smoke 仍需顯示 synthetic/redacted exact preview、destination、bytes/digest、最多一 request、成本上限與 ignored local ledger，再取得 fresh authorization。 |
| 2026-09-07 | Phase 2 synthetic offline small-batch dress rehearsal | 完成 | `scripts/run_tests.sh` 共 69 個 tests 通過；explicit synthetic Markdown + replay JSON 完成 import → offline validation → normalization → dry-run → digest approval → canonical apply → read-back。第一次建立 11 筆 canonical records 與 1 份 byte-identical raw source，第二次 11 筆全為 UNCHANGED、零寫入；Phase 0 fixture digest 不變，未讀 key/env、未連網或產生費用。桌面 Obsidian 開啟 repository 外的 `/tmp/kgnote-issue10-obsidian-v2`，確認 1 Source、4 Concepts、2 Evidence、1 LearningEvent、3 typed Edges、1 raw source 共 12 節點形成連通圖；Concept → Evidence → Source → raw、LearningEvent 與 Edge 導覽均成功，類型分離，Counterfactual 保持 `soft_association`／`relation: null`／`confidence: unresolved`，未宣稱 understood，且 broken／ghost／ambiguous links、unresolved links 與重複 basename 均為零。Obsidian 自動建立的 `.obsidian/` 已移除，artifact 恢復 12 檔；截圖位於 repository 外的 `/tmp/kgnote-issue10-graph.png`、`/tmp/kgnote-issue10-concept-evidence-source-raw.png`、`/tmp/kgnote-issue10-learning-event.png`、`/tmp/kgnote-issue10-edge.png`。本切片不是實際私人教材導入。 |
| 2026-09-07 | Phase 2 one-note real-learning offline pilot（Issue #11） | 完成 | 使用者選定的一份 LLM Wiki Markdown 以人工審閱 replay 全離線導入 repository 外的 `/private/tmp/kgnote-issue11-obsidian-v1`；原檔 bytes/SHA-256 不變，未呼叫 provider/API/key。第一次 apply 產生 23 筆 canonical records 與 1 raw source；第二次 preview 23 筆全為 UNCHANGED，canonical/raw/總寫入皆為 0，read-back 仍為 23 筆，vault 仍為 24 檔且 tree SHA-256 前後同為 `685ac9caa9f8a2dd66d0b9ebc68aaf1d74510c4e72c8f8c8bc748a7c38a02f2d`。桌面 Obsidian 驗收確認 7 Concepts、4 Evidence、2 LearningEvents、9 typed Edges、1 Source、1 raw source 共 24 節點為單一連通圖且零 orphan；Concept → Evidence → Source → 660 行 raw conversation 導覽成功，global/local graph、summary、learning history 與 provenance 可回看。Learning state ↔ Knowledge graph 保持 `soft_association`／`relation: null`／`confidence: unresolved`；question 只用 `asked_about`，assistant explanation 只用 `explained`，均未宣稱 product owner understood。broken／ghost／ambiguous／unresolved links 與重複 basename 均為零，未見可疑 merge；限制是長 SHA-ID 在 global graph 有輕度標籤重疊，但 24 節點規模仍可辨識。`.obsidian/` 已移除；截圖位於 `/tmp/kgnote-issue11-graph.png`、`/tmp/kgnote-issue11-local-graph.png`、`/tmp/kgnote-issue11-concept-detail.png`、`/tmp/kgnote-issue11-navigation-raw-top.png`、`/tmp/kgnote-issue11-question-event.png`、`/tmp/kgnote-issue11-explanation-event.png`、`/tmp/kgnote-issue11-soft-association.png`。下一步以另一份小型真實樣本觀察長 ID 標籤、圖密度與 concept merge，再決定顯示名稱或 schema/prompt 調整。 |
| 2026-09-07 | Obsidian display-label decision（Issue #12） | 完成 | 71 個離線測試已通過，並以三個 repository 外 disposable vault 完成桌面 Obsidian 比較。Option 1（stable filename + human heading）與正式 Option 2（stable target + aliased link text）均維持 7 Concepts、4 Evidence、2 LearningEvents、9 Edges、1 Source、1 raw source共 24 節點，全圖連通、零 orphan，且 broken／ghost／ambiguous／unresolved links 均為零；兩者 global/local graph、note tab 與 breadcrumb 都依 filename 顯示完整 stable ID，不採 heading、front matter 或 link alias。Option 2 正文可讀地顯示 `Knowledge graph`、`Learning state`、`Evidence L4-L14`、`Question event` 等短標籤，點擊後仍精確導向 stable-ID note；backlink 來源標題仍用 filename，snippet 保留 target 並顯示 alias，Quick Switcher 可用 front matter alias 搜尋且以 alias 為主文字、stable path 為副文字。Option 3 的 4-note prototype 證實 human-readable filename 能讓 global/local graph、note title、breadcrumb 與 Quick Switcher 全部可讀，但 filename 不再等於 canonical ID，故只作非 canonical 對照、不套用正式 artifact。三方案的 front matter stable ID 與 provenance 未變，Option 1/2 的 LearningEvent／Concept 保持分離，Learning state ↔ Knowledge graph 仍為 `soft_association`／`relation: null`／`confidence: unresolved`。三個 artifact 的 `.obsidian/` 均已移除，正式 Option 2 恢復 24 檔。截圖位於 `/tmp/kgnote-issue12-opt1-*.png`、`/tmp/kgnote-issue12-opt2-*.png` 與 `/tmp/kgnote-issue12-opt3-*.png`。 |
| 2026-09-08 | Phase 3 graph read-model contract（Issue #13） | 完成 | `kgnote.graph-read-model.v1` Draft 2020-12 schema、語意 validator、contract README 與 Phase 0 完整投影 fixture 已建立；7 個 viewer nodes 僅含 6 Concepts 與 1 LearningEvent，8 個 typed links 保留 canonical／learning／soft-association 分層，4 Evidence 與 1 Source 作非 canvas provenance support records。80 個離線測試通過；驗證 stable ID／label 分離、canonical snapshot digest、完整 record read-back、reference integrity、edge endpoint policy、`relation: null` + `confidence: unresolved`、deterministic ordering/facets、read-only validation、malformed input 與安全錯誤。read model 不含 raw Markdown body、絕對路徑、source URI/path、provider response、layout 或 UI clock；本切片不含 filesystem projector adapter、HTTP endpoint、filter execution 或 Web UI。 |
| 2026-09-08 | Phase 3 in-memory deterministic graph projector | 完成 | `kgnote.graph-projector.v1` 將 caller-owned canonical record snapshot 純記憶體投影成 Issue #13 read model；Phase 0 的 20 records 完整產生 7 nodes、8 links、4 Evidence、1 Source 並逐欄符合 golden。投影前沿用 canonical snapshot schema/reference validation，排序 records 與 set-like arrays，導出 facets 與 normalized snapshot digest；顯示 label 會清除 wiki-link 控制字元、截至 64 字、空值 fallback，碰撞時以 stable ID 衍生 token 區分。結果 frozen、每次讀取 model 都是新 JSON copy；malformed／duplicate／dangling snapshot 安全拒絕且不回顯內容。同步修正 read-model event/review enums 與既有 canonical contract 一致；87 個離線測試通過，且測試明確封鎖 filesystem/network 呼叫。此切片仍不含 vault reader 串接、HTTP、layout、filter execution、neighborhood 或 Web UI。 |
| 2026-09-08 | Phase 3 neighborhood/filter planning（Issue #15） | 完成 | 新增 `kgnote.graph-view-query.v1` 與 `kgnote.graph-view-plan.v1` Draft 2020-12 schemas、決策 README、Phase 0 1-hop golden 與純記憶體 planner。決策為 filters 先形成可走訪子圖、hop 導覽方向中立但輸出保留原 link 方向、focus 被 filter 排除時 fail closed、無 focus 選完整 filtered graph；isolated focus／零 links 是合法 plan。Evidence 由 selected nodes/links 收集，Source 再由 Evidence/selected LearningEvent 收集，不成為 canvas nodes。97 個離線測試通過，涵蓋 1/2/3-hop、node/edge/relation/space filters、unknown/excluded focus、stale digest、unavailable/unsorted filters、malformed query、determinism、copy safety、輸入不變與明確封鎖 filesystem/network I/O。尚未實作 canvas、layout、HTTP、search、UI state 或 canonical mutation。 |
| 2026-09-08 | Phase 3 read-only graph view application boundary（Issue #16） | 完成 | 新增 `kgnote.graph-view-application.v1` envelope 與 `load_graph_view(explicit_root, query=None)`，沿用 canonical store reader、projector 與 planner，將完整 snapshot 投影後只 materialize plan 選取的 nodes、links、Evidence、Sources；局部 LearningEvent 的 `concept_ids` 裁切至 selected Concepts，使輸出仍符合完整 read-model reference integrity。未提供 query 時產生 snapshot-bound 全圖 query；stale/malformed query fail closed。store/projector/planner 錯誤只回 stable component/code/contract path，不含 root、絕對路徑或原文。106 個離線測試通過，Phase 0 read-back 為 7 nodes／8 links／4 Evidence／1 Source，並涵蓋局部 provenance、isolated zero-link、dangling store reference、schema refs、determinism、copy safety 與 byte-for-byte 唯讀驗證；測試封鎖 writes、network/model、process/UI 與 clock。HTTP、canvas/layout、search、cache/watcher、authentication 與 canonical mutation 仍未實作。 |
| 2026-09-08 | Phase 3 responsive read-only Web graph canvas（Issue #17） | 完成 | 新增零 runtime dependency 的原生 ES modules + SVG canvas、鎖定 Node toolchain metadata、由 Issue #16 真實結果產生且由 Python read-back 鎖定的 fixture。stable-ID deterministic ellipse layout 呈現 6 Concepts、1 LearningEvent 與 8 typed links；Concept/LearningEvent 形狀分離，canonical/learning/soft-association 顏色與 dash 分離，soft association 保持 `relation: null`／`confidence: unresolved`。Web 6 tests 與 Python 106 tests 通過。實際以 Mac 1440×1000、iPad 1024×768、iPhone 390×844 完成 render 與互動驗收：Mac/iPad 顯示 `Full graph`（7 nodes／8 links），iPhone 顯示以 Confounder 為焦點的 `Local · 1 hop`（4 nodes／4 links）；三種尺寸均無 page-level horizontal overflow 或 node-label overlap。Concept 圓形與 LearningEvent 圓角矩形可辨，canonical／learning／unresolved links 分別為藍色／薄荷綠／琥珀虛線；pointer pan、wheel zoom、`+`／`−`／Reset 均可操作並還原 canvas。stable ID 僅在 native node tooltip 出現，畫面無 Save／Delete／Merge／Rename／Apply、editing、proficiency 或 understood 語意，console 無 error/warning。截圖位於 `/tmp/kgnote-issue17-mac.png`、`/tmp/kgnote-issue17-ipad.png`、`/tmp/kgnote-issue17-iphone.png`。 |
| 2026-09-08 | Phase 3 read-only node detail panel（Issue #18） | 完成 | 新增純記憶體 deterministic detail projector 與 responsive side panel／mobile bottom sheet。Concept 顯示 summary、status、spaces、direct + incident-link Evidence、Source metadata 與 LearningEvent history；LearningEvent 顯示 event type、context、occurred time、Concepts、Evidence 與 Sources。known confusion 僅接受明確 `confusion` event 或 `confused_with` learning edge，question／exposure／encountered／unresolved association 不會被提升成 confusion 或 understood。Evidence 與 Source references 斷裂時 fail closed，固定錯誤碼不回顯輸入；投影 deterministic、copy-safe 且不修改 read model。節點支援 click／Enter／Space，Escape／close 恢復原節點 focus；HTML/JS 不含 mutation controls。Web 13 tests 與 Python 106 tests 通過。實際以 Mac 1440×1000、iPad 1024×768 與 iPhone 390×844 完成視覺、互動、鍵盤與安全驗收：Confounder panel 顯示 summary、active status、causal-inference space、2 Evidence、1 Source、Question event learning history，Known confusion 明確為 `No explicitly evidenced confusion in this view.`；Question event 顯示 question type、context、`Time not recorded`、6 Concepts、4 Evidence 與 1 Source，未呈現 understood 或 confirmed confusion。7 個 graph nodes 皆可 Tab 聚焦；Enter／Space 開啟 panel，Escape／Close 關閉後焦點回到原節點。Mac/iPad side panel 與 full graph 可同時操作，無水平溢位或 node-label overlap；iPhone 顯示 bounded、可捲動 bottom sheet，關閉後 local 1-hop graph 可繼續操作。畫面未出現 stable ID、絕對路徑、raw conversation、mutation controls 或編輯欄位，console 無 error/warning。截圖位於 `/tmp/kgnote-issue18-mac-concept.png`、`/tmp/kgnote-issue18-mac-learning-event.png`、`/tmp/kgnote-issue18-ipad.png`、`/tmp/kgnote-issue18-iphone.png`。 |
| 2026-09-08 | Phase 3 Web hop/facet controls（Issue #19） | 完成 | 新增純 JS deterministic UI-state → `kgnote.graph-view-query.v1` builder，以及只服務 `web/` 靜態檔與 `POST /api/graph-view` 的本機唯讀 adapter；adapter 直接呼叫既有 Issue #16 application boundary，瀏覽器不重寫 traversal，也無法直接取得 canonical fixture Markdown。控制包含 full/focus、1/2/3-hop、node kind、edge class、non-null relation 與 space；同組 OR、跨組 AND，filters-first 與 direction-neutral traversal 仍由 Issue #15 planner 決定。結果只 render materialized nodes/links/Evidence/Sources，切換 view 會關閉 stale detail；empty/rejected 使用安全訊息，desktop reset 為 full graph、iPhone reset 為 deterministic planner-backed 1-hop。Golden HTTP read-back 以 Correlation 1-hop 得到 4 nodes／5 links。第一次視覺驗收發現 LearningEvent-only materialization 將 `concept_ids` 裁為空陣列後與 read-model schema 衝突；已明確定義完整 projector event 仍須有 Concept，而 filter-materialized view 可用空陣列表示相關 Concept 不在本 view，並加入 application/HTTP regression 與安全 validation-error mapping。修正後 Web 18 tests、Python 110 tests 通過。重驗確認 LearningEvent-only 為 `Full filtered graph`、1 node／0 links，Question event panel 可開啟，Concepts 明確顯示 `No concepts in this view.`，4 Evidence 與 1 Source 均保留，無安全錯誤或 request traceback。Mac 1440×1000 回歸維持 full 7/8、Correlation 1-hop 4/5；iPhone 390×844 初始與 Reset 均 deterministic 回到 local 4/4，切至 Correlation 1-hop 為 4/5；fixture Markdown URL 回傳 404。iPad 1024×768 的 Focus、Hops、filter checkbox、Update view、Reset 均為原生 `tabIndex=0` controls，取得焦點時呈現清楚薄荷綠 focus-visible outline；本次 in-app browser 鍵盤注入只設定焦點、未觸發 native select 方向鍵或 Enter／Space 預設動作，依驗收指示記為控制工具限制，query 操作則以直接控制及既有測試確認。三尺寸均無水平溢位；畫面未出現 stable ID、絕對路徑、raw conversation、mutation controls 或編輯功能，browser console 零 error/warning。重驗截圖位於 `/tmp/kgnote-issue19-retest-learning-event-only.png` 與 `/tmp/kgnote-issue19-retest-ipad-keyboard.png`。 |
| 2026-09-08 | Phase 3 end-to-end read-only boundary（Issue #20） | 完成 | 收斂本機 server 為 explicit `web/` regular-file allow-root 與唯一 `POST /api/graph-view` application route；decoded parent traversal、null byte、symlink、directory、canonical/repository/schema/test/Git/env 路徑皆 fail closed，PUT/PATCH/DELETE/OPTIONS/TRACE/CONNECT 回 versioned safe 405。JSON content type、32 KiB 上限、content length、UTF-8/JSON 與 unexpected internal failures均映射固定、不回顯的錯誤 envelope；所有回應加 no-store、CSP、no-referrer、no-sniff、frame denial，並移除 Server/Date identification。Browser rejected query 現會關閉 detail、清空舊 canvas 並標示 `View unavailable`／`Graph unavailable`，不再讓 stale graph 看似成功。新增真實 ephemeral-loopback HTTP E2E matrix，在 write/delete/rename/apply/subprocess/clock 全部 mock-forbidden 下執行 full、1/2/3-hop、四組 filters、LearningEvent-only、stale/unknown/excluded/invalid queries、malformed UTF-8/JSON 與 oversized payload，canonical store 全路徑與 bytes 前後完全一致；另有 static/method/header/internal-error tests。Web 18 tests、Python 114 tests 通過；安全邊界與限制記錄於 `web/SECURITY.md`。實際以 Mac 1440×1000、iPad 1024×768、iPhone 390×844 完成最終 smoke：三尺寸的 pan、wheel/button zoom、canvas Reset、query Reset、Concept panel、LearningEvent-only 1/0 + panel、canonical filtered view 與 isolated 1/0 均正常；Mac/iPad Reset 回 full 7/8，iPhone deterministic 回 local 4/4，無水平溢位、node-label collision、editing、persisted drag/layout、proficiency 或 understood 暗示。rejected Correlation + LearningEvent-kind query 會關閉舊 panel、清空舊 graph 為 0/0，顯示 `View unavailable`／`Graph unavailable` 與固定安全訊息，不回顯 focus ID、query 或路徑；Reset 恢復 full 7/8。五個 repository/canonical/traversal URL 均回安全 404 且 body 不含路徑；PUT/PATCH/DELETE `/api/graph-view` 均回 405。首頁與 API 回應皆含 `Cache-Control: no-store`、CSP、`Referrer-Policy: no-referrer`、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`，且無 Server/Date header。畫面未出現 stable ID、絕對路徑或 raw Markdown；question/exposure/explanation/encountered 未提升為 understood，known confusion 維持 explicit-evidence-only。browser console 零 error/warning，rejected HTTP 僅為預期 Network non-success，4174 server 無 request traceback。已知限制維持 local-only、read-only，無 authentication、search、persistence 或 canonical mutation。截圖位於 `/tmp/kgnote-issue20-mac.png`、`/tmp/kgnote-issue20-ipad.png`、`/tmp/kgnote-issue20-iphone.png`、`/tmp/kgnote-issue20-rejected.png`、`/tmp/kgnote-issue20-recovered.png`。 |
