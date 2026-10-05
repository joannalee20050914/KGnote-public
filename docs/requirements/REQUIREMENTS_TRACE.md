# KGnote 整合需求與追溯清單

> GENERATED FROM requirements.json — 不要手改此檔以建立第二份真相。

本檔是候選整合基線；來源明示的意圖與本次治理/實作提案分開。所有產品 delivery 初始為 unverified，不表示未實作，也不表示已驗證。

## 原始 27 節處置

| 節 | 處置 | 需求 ID | 解讀與限制 |
|---|---|---|---|
| 01 | mapped | KG-CTX-02 | 按當前目的控制深度；歷史命令只作需求脈絡，不當可執行現行SOP。 |
| 02 | mapped | KG-CTX-08 | 背景自述與推斷區分；下一節修正舊推斷。 |
| 03 | mapped | KG-CTX-08, KG-VAL-03 | 修課名稱不能代替真實先備理解。 |
| 04 | context_only | — | 希望自己理解實務操作；不是要求KGnote具備服務重啟權限。 |
| 05 | mapped | KG-CTX-01 | 術語造成當句阻塞。 |
| 06 | mapped | KG-MEM-04 | 跨層名稱混淆與實際輸出作錨點。 |
| 07 | mapped | KG-CTX-01, KG-CTX-08, KG-CTX-09 | Python/Shell先備需按需補；類比有限度。 |
| 08 | mapped | KG-MEM-01, KG-WF-06 | 需要壓縮重點、分界、知道目前位置。 |
| 09 | context_only | — | 查詢狀態不等於必須修改；歷史dirty output不是本專案狀態。 |
| 10 | mapped | KG-CTX-07, KG-WF-04 | 任務吞噬/三小時名詞鏈的失敗；不硬編80/20。 |
| 11 | mapped | KG-MEM-03 | 看PASS後仍操作且typo；不可合成獨立成功判斷或成功restart。 |
| 12 | context_only | — | 觀察、假說、實際修復動作分開。 |
| 13 | context_only | — | 補充環境時間線；不把已讀當process健康證據。 |
| 14 | context_only | — | 被引用原stderr附件此包未提供；不把AI引用自動當已核實log。 |
| 15 | mapped | KG-CTX-02, KG-CTX-03, KG-CTX-05, KG-CTX-09, KG-WF-04 | AI教學約束提案；保留意圖，數量上限不自動成通則。 |
| 16 | mapped | KG-CTX-01, KG-CTX-07 | 未知詞密度問題；硬熔斷/先備锁来自AI提案須修订。 |
| 17 | context_only | — | 可以補基礎，但非把完整課程當目前任務前置。 |
| 18 | mapped | KG-STR-01 | 目錄式架構要求；八週課綱/畢業規則为AI教案，不全成產品義務。 |
| 19 | mapped | KG-CTX-08, KG-KNOW-08, KG-PRAC-01, KG-PRAC-05, KG-PRAC-08, KG-SOAK-02, KG-SRS-05, KG-STR-01, KG-VAL-02, KG-WF-01, KG-WF-02, KG-WF-04, KG-WF-06 | 直接說明先閱讀AI整理再輸出的自然流程；百分比為自述不是儀表門檻。 |
| 20 | mapped | KG-KNOW-08, KG-MEM-04, KG-PRAC-01, KG-PRAC-03, KG-PRAC-05, KG-PRAC-08, KG-SRS-04, KG-STR-02 | 原OS兩份筆記未隨本次提供；混淆分析是AI當時解讀，不是當前已核對行為。 |
| 21 | mapped | KG-KNOW-08, KG-SOAK-03, KG-SRS-04, KG-STR-02 | 低成本、提示支援、對比與外部記憶提案；固定天數/早考不自動接受。 |
| 22 | context_only | — | 低壓重複與不同context的使用體驗，不把迷因比喻當學術證據。 |
| 23 | mapped | KG-PRAC-06, KG-SOAK-01, KG-SOAK-04, KG-SRS-04 | 使用者明確要無譴責試錯；不保留AI擬造stable熟練度。 |
| 24 | mapped | KG-GOV-01, KG-ING-01, KG-ING-04, KG-MEM-01, KG-MEM-02, KG-MEM-05, KG-MEM-07, KG-MEM-08, KG-PLAT-03, KG-SOAK-07, KG-WF-03 | 精確持久續學是產品缺口；五級scalar之後被§25修正。 |
| 25 | mapped | KG-GRAPH-01, KG-GRAPH-04, KG-ING-01, KG-ING-03, KG-ING-04, KG-KNOW-01, KG-KNOW-02, KG-KNOW-03, KG-MEM-01, KG-MEM-02, KG-MEM-03, KG-MEM-04, KG-MEM-05, KG-MEM-06, KG-MEM-07, KG-PLAT-01, KG-PRAC-03, KG-SOAK-05, KG-SRS-03, KG-WF-03 | 拒絕假量化/人工逐Edge；明確要partial knowledge/learning context。 |
| 26 | mapped | KG-GRAPH-01, KG-GRAPH-03, KG-GRAPH-04, KG-MEM-06, KG-PLAT-03, KG-PRAC-08, KG-SOAK-01, KG-SOAK-02, KG-SOAK-03, KG-SOAK-04, KG-SOAK-05, KG-SOAK-06, KG-SOAK-07, KG-SRS-01, KG-SRS-02, KG-SRS-03, KG-SRS-05, KG-STR-06, KG-WF-02, KG-WF-05 | 不必另開chat、先相似曝光再輸出、保留關係與間隔的直接需求。 |
| 27 | mapped | KG-GRAPH-03, KG-ING-01, KG-ING-02, KG-ING-03, KG-MEM-08, KG-PLAT-01, KG-PLAT-02, KG-PLAT-03, KG-PLAT-04, KG-PLAT-05, KG-SOAK-07, KG-STR-06 | 多學科Web/多端/匯出與低成本互動；具體provider/LINE方案为候選。 |

## workflow

### KG-WF-01 · 陌生材料先閱讀與解說

**必須保留：** 新材料預設可直接讀原文、AI/系統導讀與解說，不要求先交出自己的筆記。

**不得拿來替代：** 以空白編輯器、筆記數量或自我解釋作閱讀前置條件。

**驗收：** zero-note 帳態能讀完整單元、查看解說並自行結束。

**情境：** SC-01。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `U-READ`：Public-safe normalized source U-READ

### KG-WF-02 · 輸出活動由使用者進入

**必須保留：** 可在任意合適時點選擇模仿、提示練習、回憶或解釋，也可返回阅读。

**不得拿來替代：** 強制立即測驗或用60/70/80%熟悉度解鎖。

**驗收：** 不回答檢核也能繼續閱讀；熟悉者可直接進練習。

**情境：** SC-01, SC-02。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B26-U`：Public-safe normalized source B26-U
- `U-READ`：Public-safe normalized source U-READ

### KG-WF-03 · 系統化不等於使用者親自整理

**必須保留：** 系統保存结构、來源與學習脈絡，使用者可選擇編輯但不負責維護全套台帳。

**不得拿來替代：** 把低負擔工具做成每天維護學習表單。

**驗收：** 無手動 NoteBlock 仍可建目標、儲存事件與再次使用。

**情境：** SC-01, SC-03。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B25-U`：Public-safe normalized source B25-U
- `U-READ`：Public-safe normalized source U-READ

### KG-WF-04 · 操作任務與理解深挖可分開

**必須保留：** 使用者要完成當前實務問題時，保留最短安全操作路徑；理解教學可以另開且返回原任務。

**不得拿來替代：** 把當前服務檢查變成先修完Git或計網。

**驗收：** 所有檢查正常時可結束；待學內容不阻擋任務完成。

**情境：** SC-04。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B10-U`：Public-safe normalized source B10-U
- `B15-A`：Public-safe normalized source B15-A
- `B19-U`：Public-safe normalized source B19-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-WF-05 · 低負擔而非短文一律優先

**必須保留：** 允许完整長文；減少的是找上下文、無關展開與重複操作，而非一律把文字截短。

**不得拿來替代：** 以使用者偏好低負擔為由只給卡片或隱藏完整原文。

**驗收：** 可持續閱讀完整來源，輔助資訊預設按需展开。

**情境：** SC-05。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-WF-06 · 目標與記憶重要性可分用途

**必須保留：** 依使用者用途選需內化、可查閱、暫不處理；概念推理與精確語法記憶可分開。

**不得拿來替代：** 所有concept自動入SRS或graph中央性決定重要性。

**驗收：** 把精確指令設為lookup後仍可搜尋、不產生強制複習。

**情境：** SC-06。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B08-U`：Public-safe normalized source B08-U
- `B19-U`：Public-safe normalized source B19-U
- `B19-A`：Public-safe normalized source B19-A
- `R-PRODUCT`：Public-safe normalized source R-PRODUCT

### KG-ALPHA-01 · 單一日常 Markdown 導入工作流

**必須保留：** 使用者明示選定一份 Markdown 後，以一個有文件的命令或同等簡單入口完成 preview 與安全 materialization；正常使用不需手改 JSON、Python、fixture、schema、ID 或逐一呼叫 pipeline internals。

**不得拿來替代：** 把既有多階段開發者 CLI、手寫 extraction response 或請 Codex 告知下一條命令當成 daily-use workflow。

**驗收：** 從空的允許目的地開始，單一入口產生可開啟的 workspace 並回報 entry note、來源 digest、操作摘要與明確錯誤；使用者不編輯內部格式。

**情境：** SC-44。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `U-PERSONAL-ALPHA`：Public-safe normalized source U-PERSONAL-ALPHA

### KG-ALPHA-05 · Obsidian Personal Alpha integrated reopenable learning flow

**必須保留：** 使用者不依賴 Codex 對話或修改 Python／JSON，即可從 Start Here 進入教材、閱讀原文與概念解釋、區分並查看來源支持的教材階層與概念關係、按需核對具誠實定位精度的 Evidence、保留自己的筆記／未解問題／明示續讀位置，關閉後重新開啟並從 Start Here 經 Continue Here 回到記錄位置；Markdown 獨立可用，Canvas 只作可選增益。

**不得拿來替代：** 以空白 Continue Here 模板、最近開檔、JSON／Markdown read-back、未開啟的 Canvas、聊天中的下一步指示、Web UI 或完整 plugin 冒充整合產品流程；也不得為圖面捏造階層、因果或外部知識。

**驗收：** 同一 documented generation/preparation workflow 產生真正可作為 Obsidian vault 開啟的 disposable workspace；entry 可發現 Canvas 與手動續讀入口，source/heading/block locator 能力與限制如實呈現，user-owned notes/continuation 在 regeneration 後 byte-preserved，關閉重開的整段導航由實際產物 read-back 驗證，最後集中交付真人試用。

**情境：** SC-48。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `U-PERSONAL-ALPHA`：Public-safe normalized source U-PERSONAL-ALPHA
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3
- `U-PERSONAL-ALPHA-INTEGRATED-STAGE`：Public-safe normalized source U-PERSONAL-ALPHA-INTEGRATED-STAGE


## structure

### KG-STR-01 · 可遞迴架構與目前位置

**必須保留：** 結構可表達主題、子主題、局部項目，並顯示當前位置。

**不得拿來替代：** 平面group加顏色或卡片即聲稱完成hierarchy。

**驗收：** 測試至少主題→子主題→項目三層；此深度是測試設計不是認知定律。

**情境：** SC-07。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B18-U`：Public-safe normalized source B18-U
- `B19-U`：Public-safe normalized source B19-U
- `U-STRUCT`：Public-safe normalized source U-STRUCT

### KG-STR-02 · 組織關係必須可辨

**必須保留：** 同層比較、替代方案、時序、問題／解法與例子可區分，不將所有線看成相同語意。

**不得拿來替代：** 位置接近就自動判為對立、相似或因果。

**驗收：** 同一比較組可說明比較維度；未確定關係明示未定。

**情境：** SC-08。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B20-A`：Public-safe normalized source B20-A
- `B21-A`：Public-safe normalized source B21-A
- `U-STRUCT`：Public-safe normalized source U-STRUCT

### KG-STR-03 · 導覽結構與事實斷言分開

**必須保留：** 父子容器與membership不自動成為canonical Edge；若顯示因果／解決等事實仍須有支持。

**不得拿來替代：** 把claim放在view metadata就免除查核。

**驗收：** 重排／多重membership後canonical graph不變；無支持的problem-solution不出為事實。

**情境：** SC-08, SC-09。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `U-STRUCT`：Public-safe normalized source U-STRUCT

### KG-STR-04 · 結構範圍忠於資料

**必須保留：** 區分來源原章節與重組教學lens；未涵蓋主題只可標延伸，不假装教材有教。

**不得拿來替代：** 為漂亮完整OS樹捏造未教的memory-management內容。

**驗收：** 圖上可辨重組依據、來源範圍與未涵蓋項目。

**情境：** SC-07, SC-09。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `R-READING`：Public-safe normalized source R-READING
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3

### KG-STR-05 · 左側以導覽為主

**必須保留：** 點結構項目定位正文、更新breadcrumb；多個anchor可選且保持返回位置。

**不得拿來替代：** 每點樹节点就強制打開重複小辭典。

**驗收：** 點排程子題直接到相關段落；返回維持原閱讀位置。

**情境：** SC-07, SC-05。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `U-STRUCT`：Public-safe normalized source U-STRUCT
- `U-RECALL`：Public-safe normalized source U-RECALL
- `R-READING`：Public-safe normalized source R-READING

### KG-STR-06 · 來源座標與概念回找並存

**必須保留：** 閱讀當下可按段落定位；跨筆記尋找舊知可從概念／問題進入，不必記章節號。

**不得拿來替代：** 把原始不想手找Ch11誤解成永遠不能跳來源段落。

**驗收：** 從概念能找到舊例子，再一鍵看來源；左樹仍可定位当前正文。

**情境：** SC-10。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `B27-A`：Public-safe normalized source B27-A
- `U-STRUCT`：Public-safe normalized source U-STRUCT
- `U-RECALL`：Public-safe normalized source U-RECALL

### KG-STR-07 · 窄側欄與大圖共用結構

**必須保留：** 側欄可折疊；需要全局時可展開大架構，兩者共享同一revision與selection。

**不得拿來替代：** 另維護一份mind map名稱或強塞横向巨圖进窄欄。

**驗收：** 改一個結構項目後兩種視圖對應一致且無全頁溢位。

**情境：** SC-07, SC-27。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-STRUCT`：Public-safe normalized source U-STRUCT
- `R-READING`：Public-safe normalized source R-READING

### KG-STR-08 · 教材結構圖與知識漫遊圖分開

**必須保留：** 起始可見的領域tree表達主題／文章與typed組織關係，edge可查完整說明、節點回Markdown；熟悉後的Knowledge Roaming另用Concept graph，不混成同一畫面或語意。

**不得拿來替代：** 用平面卡片冒充tree、把Canvas membership生成canonical Edge，或從一開始顯示整個漫遊圖。

**驗收：** 三層tree、至少兩種typed組織edge、edge詳述與note anchor導覽可用；漫遊投影為另一個有資格條件的view。

**情境：** SC-39, SC-43。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3
- `O-OBS-CANVAS`：Obsidian Help：Canvas


## context

### KG-CTX-01 · 詞彙與句子都可發起閱讀協助

**必須保留：** 可選取文本或標記不懂處，連同句子／段落與當前問題形成求助context。

**不得拿來替代：** 只允許canonical keyword列表內的詞被提問。

**驗收：** PID或任意非canonical片語可發起求助並保存原位置。

**情境：** SC-11。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B05-U`：Public-safe normalized source B05-U
- `B07-U`：Public-safe normalized source B07-U
- `B16-A`：Public-safe normalized source B16-A
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-CTX-02 · 先補足當句最低必要概念

**必須保留：** 解說回答此處術語的角色以及如何幫助理解當句，深度依目的與語境。

**不得拿來替代：** 預設列完整詞典、指令、內部機制。

**驗收：** overview的PID提示可使人理解識別用途，不自動展開操作手冊。

**情境：** SC-11。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B01-U`：Public-safe normalized source B01-U
- `B15-A`：Public-safe normalized source B15-A
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-CTX-03 · 深度是context建議而非能力分數

**必須保留：** 保存當前理解目標、必要內容與暫缓範圍；若使用depth enum須版本化且可覆盖。

**不得拿來替代：** 固定PID=define或把四級標籤當通用認知階梯。

**驗收：** 同概念在overview與troubleshooting產生不同範圍且不改Concept。

**情境：** SC-12。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B15-A`：Public-safe normalized source B15-A
- `U-GLOSS`：Public-safe normalized source U-GLOSS
- `R-READING`：Public-safe normalized source R-READING

### KG-CTX-04 · 補充來源與原文分明

**必須保留：** 原文未定義時可用外部/預製補充，但標示來源與不確定；不可偽稱原文有說。

**不得拿來替代：** 虛構Evidence或把模型常識貼成來源摘錄。

**驗收：** 外部PID提示與Source定位分列；補充被移除時原文仍可读。

**情境：** SC-11, SC-21。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `R-READING`：Public-safe normalized source R-READING

### KG-CTX-05 · 範圍提醒不是鎖功能

**必須保留：** 指出哪些延伸非當前必需，使用者仍可主动深入或存為稍後問題。

**不得拿來替代：** 不懂前置就禁止閱讀，或禁止好奇心。

**驗收：** 選擇深入可展開；返回時仍在原句且不產生補課債。

**情境：** SC-12。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B15-A`：Public-safe normalized source B15-A
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-CTX-06 · 避免同篇三次重複解釋

**必須保留：** 未主動求助時不因keyword被選取而重複正文；主動求助可改用例子／對比。

**不得拿來替代：** Summary、Detailed、Evidence實際同一句卻宣稱更詳細。

**驗收：** 讀DMA原段預設無重複字典；點不懂才出不同角度或誠實回指原段。

**情境：** SC-05。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `U-RECALL`：Public-safe normalized source U-RECALL
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-CTX-07 · 未知詞密度可觸發支援而非強制重開

**必須保留：** 多處不懂時提供較簡模型、最小先備橋接或暫停選項；保留任務。

**不得拿來替代：** 硬編3詞熔斷、80/20或因多問就鎖課。

**驗收：** 多個不懂標記不一次噴多篇lecture，也不强制返回第一章。

**情境：** SC-13。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B10-U`：Public-safe normalized source B10-U
- `B16-U`：Public-safe normalized source B16-U
- `B16-A`：Public-safe normalized source B16-A

### KG-CTX-08 · 先備背景可修正

**必須保留：** 課名、過往使用與當前理解分開；以使用者澄清為準，必要時選擇快速複習或新知。

**不得拿來替代：** 修過ASP.NET就視為懂Web；固定使用者能力／低吞吐人格。

**驗收：** 修課紀錄與自述衝突時不直接跳過基礎，且可回退解說。

**情境：** SC-14。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B02-U`：Public-safe normalized source B02-U
- `B03-U`：Public-safe normalized source B03-U
- `B07-U`：Public-safe normalized source B07-U
- `B19-U`：Public-safe normalized source B19-U

### KG-CTX-09 · 類比有邊界且不加入新負擔

**必須保留：** 可用已確認的C++等經驗連結新知，並保留類比適用範圍。

**不得拿來替代：** 用使用者同樣不懂的東西解釋未知，或把類比當同一事實。

**驗收：** 求助稿能分開真實關係與比喻；無先備證據不強行套用。

**情境：** SC-13。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B07-U`：Public-safe normalized source B07-U
- `B15-A`：Public-safe normalized source B15-A

### KG-CTX-10 · 原句便利貼與inline最低必要解說

**必須保留：** 反白目前不懂且尚無完整文章的詞，可保存一句context-local解釋並於原句inline展開／收合；annotation有anchor、revision與provenance，不自動成為Concept。

**不得拿來替代：** 每個陌生詞都另開note／Concept，或AI解釋無preview覆寫source或可編輯文章。

**驗收：** 建立、修改、取消、收合、展開、重開與stale anchor均可預期；source snapshot不變，正式寫入另有diff／revision。

**情境：** SC-40。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST


## memory

### KG-MEM-01 · 精確續學而非最近開過清單

**必須保留：** 能回復上次問題、最後解說、使用者實際回答、未釐清處、閱讀anchor與暫緩支線。

**不得拿來替代：** 只顯示last_seen或最後一張教材卡就宣稱記住上次學到哪。

**驗收：** 新的session續Git时接回branch/worktree具体疑問，而非重教Git定义。

**情境：** SC-03。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B08-U`：Public-safe normalized source B08-U
- `B24-U`：Public-safe normalized source B24-U
- `B25-U`：Public-safe normalized source B25-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-MEM-02 · 舊知重連必須有真實歷史

**必須保留：** 以concept/明確reference查到之前來源、問題和例子；無歷史則明示沒有可用紀錄。

**不得拿來替代：** 概念存在於庫即寫你以前學過；用語意相似當同一概念。

**驗收：** 兩來源同概念可跳舊段落；同名異義或只有AI提到不虛構學習史。

**情境：** SC-10, SC-14。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B25-U`：Public-safe normalized source B25-U
- `U-RECALL`：Public-safe normalized source U-RECALL

### KG-MEM-03 · 區分誰說誰做與知識主張

**必須保留：** 保存user/assistant/tool attribution；從AI摘要生成的行為claim須回查原始user/tool證據。

**不得拿來替代：** 把AI解釋過或示範過當成使用者能獨立解釋/操作。

**驗收：** 四PASS後仍嘗試restart的原紀錄不得被寫成已獨立判斷不需restart。

**情境：** SC-15。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B11-U`：Public-safe normalized source B11-U
- `B25-A`：Public-safe normalized source B25-A
- `R-DATA`：Public-safe normalized source R-DATA

### KG-MEM-04 · 混淆紀錄保留具體配對與當時情境

**必須保留：** 可保存實際表達的混淆、原回答、反饋及後續修正；不是只剩錯誤次數。

**不得拿來替代：** 遇到兩個詞就推測confused_with。

**驗收：** branch/worktree confusion可回原句；後續釐清不抹去歷史。

**情境：** SC-16。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B06-U`：Public-safe normalized source B06-U
- `B20-U`：Public-safe normalized source B20-U
- `B20-A`：Public-safe normalized source B20-A
- `B25-U`：Public-safe normalized source B25-U

### KG-MEM-05 · 無證據不等於未學過

**必須保留：** 沒有學習紀錄時標未有紀錄／unknown，允許使用者說明既有背景。

**不得拿來替代：** 資料庫缺一筆就斷言UNSEEN或沒學過。

**驗收：** 新建unit不自动斷言所有概念陌生。

**情境：** SC-14。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B24-A`：Public-safe normalized source B24-A
- `B25-U`：Public-safe normalized source B25-U
- `R-DATA`：Public-safe normalized source R-DATA

### KG-MEM-06 · 保持可觀察事件而非全域熟練度

**必須保留：** 保存見過、提問、提示、回答、應用與時間，必要摘要附來源與條件。

**不得拿來替代：** 自動紅綠燈／mastery百分比或看過就升級理解。

**驗收：** 打開十次頁面不會生成理解事件；作答成果只對該任務。

**情境：** SC-14, SC-15。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B26-U`：Public-safe normalized source B26-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-MEM-07 · 不用學習者維護狀態表

**必須保留：** 正常閱讀、提問與作答可自動留可追溯紀錄；推定的觀察可更正而不要求逐項管理。

**不得拿來替代：** 每日强制自評數十concept或寫心得才保存進度。

**驗收：** 結束session無表單也保留問題與anchor；錯記可修正。

**情境：** SC-03。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B25-U`：Public-safe normalized source B25-U
- `B24-A`：Public-safe normalized source B24-A
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-MEM-08 · 可攜續學context供不同導師使用

**必須保留：** 能輸出有來源的局部續學包，不必每次重貼全部對話；不綁唯一AI。

**不得拿來替代：** 只做漂亮history页面卻沒有可供續教的context。

**驗收：** export包包含當前問題、實際證據與未知處，無全域能力臆測。

**情境：** SC-03。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B27-U`：Public-safe normalized source B27-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-MEM-09 · 操作時間線不虛構修復因果

**必須保留：** 學習紀錄區分唯讀查驗、實際變更操作、觀察到的恢復、使用者提出的原因與後續證據；因果未證實時保留為假說。

**不得拿來替代：** 把查詢命令、時間上相鄰的對話或AI摘要寫成成功修復動作。

**驗收：** 服務自行恢復的案例可重建查驗、未成功restart、網路恢復假說與證據，不冒稱由使用者修好。

**情境：** SC-37。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `B12-U`：Public-safe normalized source B12-U
- `B13-U`：Public-safe normalized source B13-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION


## soak

### KG-SOAK-01 · 不需作答的再曝光是獨立能力

**必須保留：** 提供能直接看熟悉概念／例子、可略過且无需提交答案的浸泡入口。

**不得拿來替代：** 把Start Practice或due題目清單改名Soak就算完成。

**驗收：** 啟動浸泡能看卡→滑走→結束；不建立答錯Attempt。

**情境：** SC-02。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `B23-U`：Public-safe normalized source B23-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-SOAK-02 · 逐步降低外觀與提示依賴

**必須保留：** 同一目標可先用熟悉context，再換提示、措辭或情境；用户可保留／增加提示。

**不得拿來替代：** 每次重複同一標準答案或一開始就自由回憶。

**驗收：** 至少兩種cue變體與可回到熟悉例子的路徑。

**情境：** SC-17。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B26-U`：Public-safe normalized source B26-U

### KG-SOAK-03 · 提示量與題型不綁成固定升級階梯

**必須保留：** 相似度、提示支援、輸出要求與間隔分別記錄並可選。

**不得拿來替代：** 答對一次自動升級、七級逐關解鎖或固定一天升一級。

**驗收：** 可用新例子加提示，也可在熟悉例子做無提示回想。

**情境：** SC-17。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B21-A`：Public-safe normalized source B21-A
- `B26-U`：Public-safe normalized source B26-U
- `U-READ`：Public-safe normalized source U-READ

### KG-SOAK-04 · 低壓、無債務、可無限期暫停

**必須保留：** 允許跳過、答錯、今天零活動、暫停追蹤；不懲罰或強制補完積欠。

**不得拿來替代：** 紅色欠卡、連續天數懲罰、答錯强制長篇檢討。

**驗收：** 跳過數日後仍能自主看一則，不先清空due backlog。

**情境：** SC-18。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `B23-U`：Public-safe normalized source B23-U
- `B26-U`：Public-safe normalized source B26-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-SOAK-05 · 曝光不是提取成功

**必須保留：** 可記已呈現／曝光等可觀測狀態，但不得推斷真的看懂；Soak顯示答案是合法設計。

**不得拿來替代：** 所有曝光都用answer-leak gate攔掉或算成功回憶。

**驗收：** 同一卡曝光可顯示答案；Practice無輔助模式才隔離；兩者紀錄不同。

**情境：** SC-02, SC-19。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B26-U`：Public-safe normalized source B26-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-SOAK-06 · 局部關係與舊例子不被碎片化

**必須保留：** 可複習概念、具體關係或小組概念，保留主題/舊例子來源。

**不得拿來替代：** 僅有互不相連的一詞一答案卡。

**驗收：** 小型關係練習可顯示必要context，但不洩漏待提取關係。

**情境：** SC-17。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `B26-A`：Public-safe normalized source B26-A

### KG-SOAK-07 · 複習不必先開全新聊天重建背景

**必須保留：** 短時互動直接取得既有材料與局部歷史，真正新問題才開新的教學支線。

**不得拿來替代：** 每日複習先要求描述過去學了什麼。

**驗收：** 從浸泡入口可直接看既有例子；不要求空白chat起手。

**情境：** SC-02, SC-03。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B26-U`：Public-safe normalized source B26-U
- `B27-U`：Public-safe normalized source B27-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION


## practice

### KG-PRAC-01 · 多種輸出形式與條件

**必須保留：** 保留模仿、填空、選擇／區辨、白紙回想、自己說一次與應用；分批交付不偷換成單一填詞。

**不得拿來替代：** 把三種相同字串填空算三種活動。

**驗收：** 題目目錄明示目前可用／未實作活動，能保存自由解釋。

**情境：** SC-20。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B20-U`：Public-safe normalized source B20-U
- `U-READ`：Public-safe normalized source U-READ

### KG-PRAC-02 · 無輔助作答隔離答案

**必須保留：** 無輔助模式在提交或主動揭露前不把答案放在可見UI、隱藏DOM或ARIA。

**不得拿來替代：** 只用CSS遮住或selection bar暴露答案。

**驗收：** 跨route、reload、stale selection仍無意外答案；主動提示另記錄。

**情境：** SC-19。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE
- `U-READ`：Public-safe normalized source U-READ

### KG-PRAC-03 · 原回答與追加式回饋

**必須保留：** 保存raw response、題目/rubric revision、提示、回饋與更正，重試另筆。

**不得拿來替代：** 只保留成功或最後一次的改寫回答。

**驗收：** 錯→部分→再次回答的三種資訊都能read-back。

**情境：** SC-20。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B20-U`：Public-safe normalized source B20-U
- `B25-U`：Public-safe normalized source B25-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-PRAC-04 · 未評估與證據不足分離

**必須保留：** 尚未有評估者時用unassessed；已評估但材料不足才用insufficient evidence；保留評估來源。

**不得拿來替代：** 所有自由回答先當INSUFFICIENT_EVIDENCE或incorrect。

**驗收：** 提交自由答案先显示待自評；對照rubric後另追加self assessment。

**情境：** SC-20。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-PRAC-05 · 語意判準不等於逐字一致

**必須保留：** 依角色、條件、因果與重要區辨回饋；只有需精確記術語的目標才做字串判分。

**不得拿來替代：** 合理同義答案因措辭不同一律錯。

**驗收：** 同義正確答案與錯誤相似詞均有案例；評分限制可見。

**情境：** SC-20。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B20-U`：Public-safe normalized source B20-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-PRAC-06 · 不懂、跳過、取消與失敗分開

**必須保留：** 未進入、草稿離開、滑過、不知道、有提示與錯誤各自記錄。

**不得拿來替代：** 用空值統一當零分／incorrect。

**驗收：** 只看題目不產生已提交結果；不知道可直接提交且保存。

**情境：** SC-02, SC-19。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B23-U`：Public-safe normalized source B23-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-PRAC-07 · Attempt身分與寫入冪等

**必須保留：** 穩定client attempt ID；同提交重送回相同結果，不同payload同ID回conflict，retry新ID。

**不得拿來替代：** 用server timestamp作attempt唯一身分或覆寫已交回答。

**驗收：** 模擬寫成功response遺失、重送與不同payload皆可驗證。

**情境：** SC-22。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE
- `R-RELIABILITY`：Public-safe normalized source R-RELIABILITY

### KG-PRAC-08 · 能回饋具體缺口並接回解說

**必須保留：** 答後可看rubric、來源、缺少條件與短修正，再回相關解說；不必先重寫筆記。

**不得拿來替代：** 只說不一致或答錯後強制寫反省。

**驗收：** 選部分正確可指出哪一條待補，回原段不丟attempt。

**情境：** SC-20。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B20-U`：Public-safe normalized source B20-U
- `B26-U`：Public-safe normalized source B26-U
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-PRAC-09 · 由有選項辨認逐步到無提示回想

**必須保留：** 新Target先可用原文挖空＋選項或選擇／區辨，再依可說明evidence或使用者選擇進入提示與無提示回想；後期問法貼近原文，遠距transfer另標目的。

**不得拿來替代：** 陌生內容第一題只給自由回想、把choice冒充unassisted，或以大幅換句增加無關記憶負擔。

**驗收：** 同Target可建立choice/cloze與recall兩類item並分別保存support、prompt revision、answer visibility與Attempt。

**情境：** SC-41。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST


## review

### KG-SRS-01 · 到期資格與學習事件分開

**必須保留：** 時間安排只產生可選待複習項；開始活動與提交各有明確生命週期。

**不得拿來替代：** 到期本身或snooze自動建立Attempt。

**驗收：** 推進注入時鐘有due但無attempt；活動開始才按contract建立。

**情境：** SC-23。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-SRS-02 · 可解釋簡單排程非最佳遺忘曲線

**必須保留：** 定義每段間隔的起算點、延期／停止規則及下一次原因，支持clock測試。

**不得拿來替代：** 把1/3/7/21寫成對所有人的最佳公式。

**驗收：** schedule計算可重放；user能看懂下一次日期如何得來。

**情境：** SC-23。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `B26-A`：Public-safe normalized source B26-A
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT

### KG-SRS-03 · 自然接觸與真正提取採不同處理

**必須保留：** 自然曝光可減少近期重複推送；只有有實際回答證據才記提取，排程影響可追溯。

**不得拿來替代：** Codex log提到POST就抵銷一個記憶評量。

**驗收：** 只展示與自主正確解釋各有測試；不因曝光直接延長提取成功級別。

**情境：** SC-24。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B26-A`：Public-safe normalized source B26-A
- `B25-U`：Public-safe normalized source B25-U
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-SRS-04 · 反覆混淆可提議對比不強制加量

**必須保留：** 可推薦先前明確混淆的成對區辨，保留user opt-out與低負擔。

**不得拿來替代：** 一次答錯全庫加量或無窮追問。

**驗收：** 錯認port/localhost後可選短對比，也可滑走。

**情境：** SC-16, SC-18。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B20-U`：Public-safe normalized source B20-U
- `B21-A`：Public-safe normalized source B21-A
- `B23-U`：Public-safe normalized source B23-U

### KG-SRS-05 · 換情境應用與延遲回憶分別驗收

**必須保留：** 題目與評量區分熟悉例子的回答、延遲提取與新案例應用。

**不得拿來替代：** 一次答對就宣稱長期記得且能transfer。

**驗收：** 至少一組匹配新案例與一個延遲測試計畫；未等到時間不報結果。

**情境：** SC-25。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B26-U`：Public-safe normalized source B26-U
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT

### KG-SRS-06 · Due清單與教材結構圖共用複習狀態

**必須保留：** 任務清單與教材結構圖顏色投影同一Target／Due／Attempt history；顏色表示可解釋階段並有文字替代，七天規則標為使用者選定方案而非最佳曲線。

**不得拿來替代：** 圖與清單各算一套狀態、只靠顏色、snooze／閱讀建立Attempt，或固定天數被宣稱個人最佳遺忘曲線。

**驗收：** 同Target在queue與圖上狀態一致、可重放；點節點進review並回原結構位置，圖例與下一日期理由可見。

**情境：** SC-43。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST


## knowledge

### KG-KNOW-01 · Concept／Evidence／行為分層

**必須保留：** 可重用concept identity、完整主張provenance與學習互動各有邊界。

**不得拿來替代：** 把一次事件或完整長句都變成Concept。

**驗收：** 同概念跨來源共用identity，事件不改概念的領域定義。

**情境：** SC-15, SC-26。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B25-A`：Public-safe normalized source B25-A
- `R-DATA`：Public-safe normalized source R-DATA

### KG-KNOW-02 · 允許模糊關聯而不逼命名

**必須保留：** 可存有來源的聯想、待釐清關係；不要求用戶填完整ontology。

**不得拿來替代：** 保存創意之前先強制選精確relation。

**驗收：** 創意類比可保存為soft association並回原話，不自動成為事實Edge。

**情境：** SC-26。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-KNOW-03 · Source忠實不等於教學答案正確

**必須保留：** 分開source support、fact review、teaching readiness；原文錯誤以erratum保存。

**不得拿來替代：** accepted source就自動當review標準答案。

**驗收：** 有爭議主張仍可讀且有警告，但無法出標準答案題。

**情境：** SC-21。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `B25-A`：Public-safe normalized source B25-A

### KG-KNOW-04 · 主張修訂傳播到下游

**必須保留：** 已排入的ReviewItem遇到依據撤回應阻擋或重新審核；歷史attempt保持舊判準。

**不得拿來替代：** 只加警告卻繼續讓舊錯題到期出現。

**驗收：** claim改待修訂後既有due item blocked；過去回答仍可查。

**情境：** SC-21。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `R-PRACTICE`：Public-safe normalized source R-PRACTICE

### KG-KNOW-05 · 多對多Evidence選取不依順序

**必須保留：** 一Evidence支持多Claim時保留自身焦點與候選；零Claim仍可閱讀。

**不得拿來替代：** find第一條作唯一真實對應。

**驗收：** 反轉propositions陣列時候選集合／selection語意不變。

**情境：** SC-28。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA

### KG-KNOW-06 · 語意一致不等於逐字與全集一致

**必須保留：** 共享identity、claim方向、來源及審查狀態；允許contextual paraphrase和不同selection policy。

**不得拿來替代：** 所有視圖全量等集合或所有解說必須同句。

**驗收：** 短解說與展開解說同源不同細節；兩視圖局部集合可不同。

**情境：** SC-12, SC-29。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `U-GLOSS`：Public-safe normalized source U-GLOSS

### KG-KNOW-07 · 完整關係可含條件與多角色

**必須保留：** generic Edge僅為索引；完整claim可帶條件、範圍、角色與例外。

**不得拿來替代：** related_to就支持causal inference；短linking phrase取代機制。

**驗收：** 有條件句的條件不因轉圖消失，不明關係不可推論為因果。

**情境：** SC-08, SC-29。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-DATA`：Public-safe normalized source R-DATA
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-KNOW-08 · 歷史AI分析不是心理診斷或行為證據

**必須保留：** 保留使用者感受，不採納舊AI對智力、吞吐或能力的推斷作固定profile。

**不得拿來替代：** 把AI安慰／推論寫成學習障礙或已學會的事實。

**驗收：** 續學包只引可觀察紀錄與自述，無診斷與能力百分比。

**情境：** SC-14, SC-15。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `B20-A`：Public-safe normalized source B20-A
- `B21-A`：Public-safe normalized source B21-A
- `R-DATA`：Public-safe normalized source R-DATA

### KG-KNOW-09 · 同一Concept identity貫穿文章到漫遊

**必須保留：** 文章mention、便利貼、ReviewItem、Due、教材結構appearance與Knowledge Roaming node引用同一stable Concept identity／aliases；各階段record不重複定義Concept。

**不得拿來替代：** 每個UI或每次問答依顯示文字新建同義節點，或為去重強併同名異義詞。

**驗收：** alias變更不分裂history；從任一階段可回同一Concept與source anchors；無Concept ref的純context便利貼仍合法。

**情境：** SC-39, SC-40, SC-41, SC-42, SC-43。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST


## graph

### KG-GRAPH-01 · Graph保留為關係回找與探索工具

**必須保留：** 使用者需要時可從concept找局部關係與過去context；不將Graph全面刪除或強制首頁。

**不得拿來替代：** Graph optional被當成永遠不做；或每次都先看全圖。

**驗收：** 閱讀路徑可完全不用圖；查關係時仍有graph或等價可驗證入口。

**情境：** SC-29。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B26-U`：Public-safe normalized source B26-U
- `U-STRUCT`：Public-safe normalized source U-STRUCT
- `R-PRODUCT`：Public-safe normalized source R-PRODUCT

### KG-GRAPH-02 · 範圍、群組與跨界連線可見

**必須保留：** 按目前topic/概念與task選子圖，顯示scope、群組與被隱藏範圍。

**不得拿來替代：** 無任務地平鋪整單元節點。

**驗收：** 中斷/driver與lock/race不無邊界混合；無資料連線不推論現實無關。

**情境：** SC-29。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-STRUCT`：Public-safe normalized source U-STRUCT
- `R-DATA`：Public-safe normalized source R-DATA

### KG-GRAPH-03 · 局部展開有方向與Evidence

**必須保留：** hop/budget展開保留方向、跨主題context與就近Evidence。

**不得拿來替代：** 為連通性補線或箭頭被节点遮住。

**驗收：** 方向可判讀；show more與hidden count可驗證；圖故障Reader正常。

**情境：** SC-29, SC-30。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B26-U`：Public-safe normalized source B26-U
- `B27-A`：Public-safe normalized source B27-A
- `R-DATA`：Public-safe normalized source R-DATA

### KG-GRAPH-04 · 顯示學習痕跡不等於能力視覺化

**必須保留：** 可區分領域關係與明確學習／混淆事件，圖例說明來源。

**不得拿來替代：** 實線/綠色默示已理解或不分soft與fact。

**驗收：** 只曝光的節點不被標成已掌握，confusion有原始證據。

**情境：** SC-14, SC-16。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B26-A`：Public-safe normalized source B26-A

### KG-GRAPH-05 · Knowledge Roaming只投影可說明為熟悉的Concept

**必須保留：** Knowledge Roaming用於認知範圍內聯想；預設只投影有可說明行為evidence或使用者override的roam-eligible Concept，遇到未知邊界提供提問而非展開整片陌生網路。

**不得拿來替代：** Concept存在、AI提及、閱讀次數或單次選擇題正確就自動等同熟悉／可漫遊。

**驗收：** eligibility理由、override、撤回與stale規則可查；未eligible節點不進預設漫遊但其Source仍可讀。

**情境：** SC-39, SC-43。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST


## ingestion

### KG-ING-01 · 保留原始來源與精確定位

**必須保留：** 原始對話/文本不可覆寫，派生內容連回source revision與locator。

**不得拿來替代：** 乾淨摘要替代原始對話或虛構細行號。

**驗收：** hash/read-back檢查及unknown locator合法降級。

**情境：** SC-21, SC-28。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B25-U`：Public-safe normalized source B25-U
- `B27-U`：Public-safe normalized source B27-U
- `R-DATA`：Public-safe normalized source R-DATA

### KG-ING-02 · 匯出／單篇匯入是獨立長期能力

**必須保留：** 支援低摩擦的選定材料進入學習庫；具體browser exporter可分期，不等於批量掃描。

**不得拿來替代：** 永久只能開兩份手寫fixture卻稱已完成個人資料導入。

**驗收：** 來源匯入驗收與renderer fixture驗收分列。

**情境：** SC-31。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B27-U`：Public-safe normalized source B27-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-ING-03 · 自動抽取只形成有來源候選

**必須保留：** 從對話候選概念、疑問與行為，保留speaker/review；允許automation但不替用戶造理解。

**不得拿來替代：** 把AI對話所有coding詞都算使用者學過。

**驗收：** AI-only statement與user回答在抽取fixture得到不同事件。

**情境：** SC-15, SC-31。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B27-U`：Public-safe normalized source B27-U
- `R-DATA`：Public-safe normalized source R-DATA
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-ING-04 · 使用者不用逐條審核所有機器紀錄

**必須保留：** 讓安全的來源保存、閱讀與未審候選可先行；事實promote／標準答案才過適當審查。

**不得拿來替代：** 以安全為由要求初學者先驗完整ontology才能閱讀。

**驗收：** 候選待審不阻擋raw Reader，且不進可考集合。

**情境：** SC-01, SC-21。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B25-U`：Public-safe normalized source B25-U
- `B24-A`：Public-safe normalized source B24-A
- `U-READ`：Public-safe normalized source U-READ
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION


## platform

### KG-PLAT-01 · 多Space共用engine與跨來源識別

**必須保留：** 不同學科同一引擎與資料邊界；共享概念需可信識別，同名不强併。

**不得拿來替代：** OS專用hard-code或每個學科另App。

**驗收：** OS/BitePacer/合成資料共用renderer；同名異義反例不合併。

**情境：** SC-10, SC-31。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `B27-U`：Public-safe normalized source B27-U
- `B25-U`：Public-safe normalized source B25-U
- `U-ROADMAP-REINTEGRATION`：Public-safe normalized source U-ROADMAP-REINTEGRATION

### KG-PLAT-02 · Mac／iPad／iPhone可用但非相同全圖

**必須保留：** responsive主工作區；touch/highlight替代操作與键盘focus，原文仍可讀。

**不得拿來替代：** 宣稱iPad實機驗收但只改viewport；桌面巨圖硬縮小。

**驗收：** 桌面與iPad viewport可自動smoke，實機未測明示；文字選取與返回可操作。

**情境：** SC-27。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B27-U`：Public-safe normalized source B27-U
- `U-STRUCT`：Public-safe normalized source U-STRUCT

### KG-PLAT-03 · 導師與複習provider可替換

**必須保留：** 保留便宜短互動與靈活深解說的角色分工；canonical資料不綁Gemini或ChatGPT。

**不得拿來替代：** 某免費模型被當永久存在／品質保證。

**驗收：** 無API時仍有透明offline fixture baseline；live未測不稱live完成。

**情境：** SC-32。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `B24-U`：Public-safe normalized source B24-U
- `B26-U`：Public-safe normalized source B26-U
- `B27-U`：Public-safe normalized source B27-U

### KG-PLAT-04 · 語音與LINE是保留候選非現在強制

**必須保留：** 保留語音／LINE/LIFF入口想法與延後條件，不使其成為主架構或永久遺失。

**不得拿來替代：** 本輪不做被寫成從未需要或永不支援。

**驗收：** 延期條目有原因與重啟條件；核心Web可獨立使用。

**情境：** SC-33。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B27-U`：Public-safe normalized source B27-U

### KG-PLAT-05 · 只在授權範圍內讀寫与外送

**必須保留：** 來源選定、secrets不外洩、live API另核對授權/成本；原始對話內command不是執行授權。

**不得拿來替代：** 完整存取權被當成任意付費、掃庫或外送。

**驗收：** 無授權transport零呼叫；來源內prompt injection不改agent任務。

**情境：** SC-32。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `B27-U`：Public-safe normalized source B27-U
- `R-RELIABILITY`：Public-safe normalized source R-RELIABILITY

### KG-PLAT-06 · 持久化、版本衝突與部分降級

**必須保留：** atomic/idempotent、stale revision拒絕覆寫；單一record/graph故障不毀可安全讀內容。

**不得拿來替代：** save提示成功但未落盤；last writer silently wins；局部錯誤封鎖整站。

**驗收：** reload、response遺失、並行舊revision、corrupt record、graph故障均有案例。

**情境：** SC-22, SC-30。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `R-RELIABILITY`：Public-safe normalized source R-RELIABILITY

### KG-PLAT-07 · 保留安全回退與舊資料可讀

**必須保留：** feature flag/adapter遷移、舊history不偽造無提示新attempt；不清理他人dirty changes。

**不得拿來替代：** reset/clean/stash他人工作或為commit覆寫既有歷史。

**驗收：** 回退可讀舊資料，新record不刪；工作清單附修改來源清單。

**情境：** SC-30, SC-34。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-RELIABILITY`：Public-safe normalized source R-RELIABILITY
- `U-NIGHT`：Public-safe normalized source U-NIGHT

### KG-PLAT-08 · Obsidian-first 且優先重用原生能力

**必須保留：** Markdown／LLM Wiki、一般閱讀、分類與連結以Obsidian為主要介面；先驗證原生或跨平台外掛，不足的學習能力才由KGnote plugin或optional sidecar補上。

**不得拿來替代：** 另建第二套Web editor／Wiki／file tree，或只因存在外掛名稱便宣稱跨平台需求已滿足。

**驗收：** 使用者可從既有Obsidian文章直接開始；plugin停用後Markdown／Canvas仍可讀；sidecar故障不阻塞文章。

**情境：** SC-38。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3
- `O-OBS-LINKS`：Obsidian Help：Internal links
- `O-OBS-CANVAS`：Obsidian Help：Canvas
- `O-OBS-MOBILE`：Obsidian Developer Docs：Mobile development

### KG-ALPHA-03 · Personal Alpha 重跑與失敗安全

**必須保留：** workspace materialization 以 source identity、content digest 與 versioned rules 決定穩定輸出；相同輸入重跑不複製 canonical knowledge 或破壞人工內容，衝突與中斷 fail closed／rollback 並於成功後 read-back。

**不得拿來替代：** 以每次執行時間產生新 ID、先刪目的地再重建、靜默覆寫人工檔案，或錯誤後留下半套可被誤認為成功的 state。

**驗收：** 相同輸入第二次為 unchanged；注入寫入失敗後目的地回到先前一致狀態；source bytes、manifest、entry note 與 references read-back 相符。

**情境：** SC-46。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `U-PERSONAL-ALPHA`：Public-safe normalized source U-PERSONAL-ALPHA
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3


## validation

### KG-VAL-01 · 工程通過與學習有效分開

**必須保留：** 區分implementation、unit/integration、browser、manual UX與learning-effectiveness證據。

**不得拿來替代：** 測試數量當學習增益或AI代使用者簽認。

**驗收：** 自動smoke僅標engineering verified；未測手動與延遲保留未驗證。

**情境：** SC-25, SC-35。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT
- `U-GOV`：Public-safe normalized source U-GOV

### KG-VAL-02 · 比較原有學法而非強制筆記baseline

**必須保留：** 比較閱讀+AI解說現行方式與KGnote；Graph條件同內容時間。

**不得拿來替代：** 用使用者已拒絕的先寫筆記任務當唯一本位。

**驗收：** protocol包含可拒絕與中止原因，空白筆記不記理解零分。

**情境：** SC-25。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `B19-U`：Public-safe normalized source B19-U
- `U-READ`：Public-safe normalized source U-READ
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT

### KG-VAL-03 · 熟悉度由任務當下判斷

**必須保留：** 熟悉材料/OS/BitePacer是材料用途設計，不永久對應高/中/低能力。

**不得拿來替代：** 不同教材分數差當先備知識因果；N=1泛化。

**驗收：** 反覆BitePacer接觸會更新前測紀錄；matched task與限制可見。

**情境：** SC-25。**依據類別：** source_based。**採納標記：** proposed_reconciliation。**交付：** not_implemented。

**來源：**
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT
- `B03-U`：Public-safe normalized source B03-U

### KG-ALPHA-04 · 三種來源的 Personal Alpha 工程驗證

**必須保留：** candidate verification 至少使用三份內容與結構 materially different 的 Markdown，逐份驗證來源、結構、provenance、重開 read-back 與無人工內部格式介入，並通過完整 repository verifier。

**不得拿來替代：** 以三份近乎相同 fixture、只檢查檔案存在、單一路徑 smoke 或 automated pass 冒充真人 Obsidian usability acceptance。

**驗收：** 三份 fixture 各有可說明差異與端到端 run evidence；full verifier 綠燈後狀態只升為 candidate_verified，真人 usability 仍是外部 gate。

**情境：** SC-47。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `U-PERSONAL-ALPHA`：Public-safe normalized source U-PERSONAL-ALPHA
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3


## governance

### KG-GOV-01 · 不可再以摘要取代需求來源

**必須保留：** 每項需求連到speaker、來源位置與理由；roadmap只能排程與引用。

**不得拿來替代：** 再寫一份更長DEVELOPMENT_PLAIN作唯一真相。

**驗收：** 需求→原話→正反驗收→implementation evidence可雙向查。

**情境：** SC-35。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** automated_verified。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `B24-U`：Public-safe normalized source B24-U

### KG-GOV-02 · 保留被延後與被取代的條目

**必須保留：** 需求有stable ID、revision、active/deferred/superseded處置與理由，不直接刪除。

**不得拿來替代：** optional/deferred等於遺忘；新總結抹去舊需求。

**驗收：** 刪ID、弱化must或改defer須顯示delta與決策。

**情境：** SC-33, SC-36。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `N-GOV`：Public-safe normalized source N-GOV

### KG-GOV-03 · 區分用戶意圖、AI提案與研究假說

**必須保留：** 來源角色與adoption分開；本次合併不把所有AI說法默認批准。

**不得拿來替代：** 原對話中AI的硬熔斷、學力推論或UI方案自動成contract。

**驗收：** 提案有proposal狀態；真正衝突單列而不強行拼接。

**情境：** SC-36。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `R-EXPERIMENT`：Public-safe normalized source R-EXPERIMENT
- `N-GOV`：Public-safe normalized source N-GOV

### KG-GOV-04 · 單一主台帳與機械可檢查映射

**必須保留：** 以一份machine-readable ledger產生人類視圖；scenario/test/evidence有ID映射。

**不得拿來替代：** 多份手改真相或填path就算測試通過。

**驗收：** checker檢查dangling/duplicate/未映射與過度宣稱，生成視圖可重建。

**情境：** SC-35。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** automated_verified。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `N-GOV`：Public-safe normalized source N-GOV
- `O-TRACE`：NASA SWE-052：Bidirectional Traceability（Handbook Ver C）

### KG-GOV-05 · 每次任務使用可重建context packet

**必須保留：** 任務載入相關需求、禁止替代、scenario、當前revision/未決項，session恢復可重建。

**不得拿來替代：** 只說已讀過或要求每次憑聊天記憶補上下文。

**驗收：** 新session僅靠packet仍能說出此切片不該做什麼。

**情境：** SC-35。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `N-GOV`：Public-safe normalized source N-GOV
- `O-AGENTS`：OpenAI：AGENTS.md
- `O-PLANS`：OpenAI Cookbook：Using PLANS.md for multi-hour problem solving（2025-10-07，已封存）

### KG-GOV-06 · 讓漏項在使用者驗收前暴露

**必須保留：** 定義負例測試、變更影響清單、CI gate与獨立對照；保護需求/測試不被同次弱化。

**不得拿來替代：** 實作+測試同時改低標準後自稱全綠。

**驗收：** 移除無輸出Soak、重複DMA辭典、強制寫筆記等mutant須被對應測試抓到。

**情境：** SC-35, SC-36。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `N-GOV`：Public-safe normalized source N-GOV
- `O-CI`：GitHub：About protected branches

### KG-GOV-07 · 產品範圍與本輪milestone分開

**必須保留：** 整體需求完整保留，任務只承諾明確subset；完成subset不自稱產品完整。

**不得拿來替代：** 把每個idea都當今晚必做或為耗满夜晚持續擴scope。

**驗收：** 交付附已驗證／部分／deferred／待判斷矩陣與下一切片。

**情境：** SC-33, SC-35。**依據類別：** proposed_safeguard。**採納標記：** proposed_reconciliation。**交付：** partial。

**來源：**
- `U-GOV`：Public-safe normalized source U-GOV
- `U-NIGHT`：Public-safe normalized source U-NIGHT
- `N-GOV`：Public-safe normalized source N-GOV


## ui

### KG-UI-01 · 學習介面不暴露不必要的系統複雜度

**必須保留：** 日常入口只呈現當前主要工作；Source／Evidence／Claim／Lens／Attempt等內部模型按需或只在稽核層顯示，使用者不需先學系統才能讀文章。

**不得拿來替代：** 把所有可追溯資料同時做成常駐面板，或以更多說明文字補償複雜工作流。

**驗收：** 普通文章開啟時即能閱讀；未主動使用KGnote功能時沒有額外輸入、dashboard或術語門檻。

**情境：** SC-38。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST
- `U-PA-HUMAN-FEEDBACK`：Public-safe normalized source U-PA-HUMAN-FEEDBACK
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3

### KG-ALPHA-02 · coherent Obsidian learning workspace

**必須保留：** 每份新來源產生一個人類可讀的學習入口，優先使用普通 Markdown／wikilink／heading anchor／properties，清楚呈現材料概要、主要結構、重要概念、可支持的關係、來源 Evidence 與待確認事項。

**不得拿來替代：** 把使用者丟進 canonical record 目錄、平面全圖、內部 enum 清單，或只複製原文而不提供可導航的學習結構。

**驗收：** 僅從 entry note 與原生連結即可回答材料主旨、主題、重要概念、關係理由、原文位置與不確定事項；派生 note 不冒充 immutable source。

**情境：** SC-45。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** partial。

**來源：**
- `U-PERSONAL-ALPHA`：Public-safe normalized source U-PERSONAL-ALPHA
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST
- `U-PA-HUMAN-FEEDBACK`：Public-safe normalized source U-PA-HUMAN-FEEDBACK
- `U-OBSIDIAN-LEARNER-PROJECTION-V3`：Public-safe normalized source U-OBSIDIAN-LEARNER-PROJECTION-V3


## teaching

### KG-AI-01 · 提問先檢索來源再按複雜度升級AI

**必須保留：** 閱讀／測驗問題先檢索目前文章與直接連結來源；來源不足、跨層或跨概念比較才升級AI，並建議當前最低必要深度、偏題／稍後探索與是否值得擴充文章。

**不得拿來替代：** 所有問題一律外送、AI判斷不可申覆，或生成內容直接成為source／canonical fact。

**驗收：** source可回答時零live transport且回exact anchor；AI升級有理由、scope、限制與provenance，擴充需preview／accept。

**情境：** SC-42。**依據類別：** user_explicit。**採納標記：** carried_user_intent。**交付：** not_implemented。

**來源：**
- `U-OBS-FIRST`：Public-safe normalized source U-OBS-FIRST
