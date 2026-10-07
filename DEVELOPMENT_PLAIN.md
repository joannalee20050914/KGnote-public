# KGnote 白話版開發計畫

> 需求 SSOT：需求內容、正反驗收與交付狀態以 `docs/requirements/requirements.json`、`scenarios.json`、`sources.json` 為準。本檔只排現行切片、說明依賴與保留歷史入口，不重寫第二份需求真相。
>
> 現行 baseline：`kgnote-reconciliation-2026-09-27-r8`。Obsidian-first 方向與原始發想再整合見 `docs/requirements/USER_DIRECTION_DELTA_20260922.md`；Personal Alpha 交付裁決、人工試用結果、V3 Golden/native direction 與 integrated-stage direction 分別見 `docs/requirements/PERSONAL_ALPHA_DIRECTION_20260922.md`、`docs/requirements/PERSONAL_ALPHA_HUMAN_FEEDBACK_20260923.md`、`docs/requirements/OBSIDIAN_LEARNER_PROJECTION_NATIVE_SPIKE_DIRECTION_20260923.md`、`docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md`。
>
> 歷史 roadmap：2026-09-22 前的完整 Phase 0–5、Phase 3c 工單與驗收記錄保存在 `docs/DEVELOPMENT_PLAIN_SUPERSEDED_20260922.md`，已標示 superseded；已完成工程事實仍有效，未完成 checkbox 不再自動代表目前優先序。
>
> 更新：2026-09-22。當前產品方向：**Obsidian-first learning layer**。

## 目前裁決

熟悉材料 實際試用確認：現有 Web Learn 頁一次暴露原文、結構、Concept、Claim、Evidence、Local Graph 與續學控制，對簡單內容造成「先學系統才能學材料」的負擔。這是產品方向 finding，不只是 CSS 或版面問題。

因此主線由「擴充獨立 Web 學習工作區」改為：

```text
Obsidian Markdown / LLM Wiki
  ├─ 原文與可修訂文章
  ├─ folders / properties / links / backlinks / aliases
  └─ Canvas 或等價的教材結構圖
        ↓
KGnote Obsidian learning layer
  ├─ 原句便利貼與有限展開
  ├─ 精確續學：問題／回答／混淆／anchor
  ├─ 獨立 Soak：可以只曝光、不作答
  ├─ 分階段練習
  ├─ 問題 → source retrieval → AI escalation
  ├─ 選定來源與真實工作事件回流
  ├─ due queue 與結構圖複習狀態
  └─ 熟悉後才進入 Knowledge Roaming Graph
        ↓
可選 local sidecar
  └─ 只承載 mobile sandbox 不適合的索引、模型 adapter、背景排程或大型圖運算
```

目前 Web prototype 保留為資料契約、失敗安全與 comparison harness；停止把它當日常主要介面，也停止在未驗證前繼續增加 Web panel、route 或圖形控制。

對應需求：`KG-WF-01–03`、`KG-PLAT-08`、`KG-UI-01`、`KG-GOV-07`；驗收：`SC-01`、`SC-38`。

## 目前 active 產品交付：Personal Alpha integrated candidate

最新明示目標把目前交付順序收斂為一條可日常使用的端到端路徑：

```text
明示選定一份 Markdown
  → 一個 documented workflow 做 validation／preview／materialize
  → immutable source snapshot＋穩定 source identity
  → source-grounded 結構、重要 Concept、可支持 relation／Evidence
  → 一篇人類可讀的 Obsidian learning entry note
  → 關閉重開、原樣重跑、失敗回復
```

Personal Alpha 的重點是 Obsidian 中的普通 Markdown learning workspace，而不是先做 plugin 或把 canonical
records 當 UI。輸出要能回答材料主旨、主要主題、重要概念、關係理由、原文位置與待確認事項；內部
ID／schema 只留在可稽核層。實作可重用既有 importer、normalization、store 與 provenance contract，
但 daily workflow 不得要求使用者手寫 extraction response、JSON、Python、fixture、schema 或 ID。

這個裁決調整的是目前交付順序，不撤回 O1–O7 中已保留的產品能力。inline 便利貼、Resume、Soak、
Practice、Due、Knowledge Roaming、第三方 plugin 評估與 mobile 實機仍留在後續；它們不成為這次
Personal Alpha candidate 的前置。live AI/API、正式私人 vault 批次修改、destructive migration 與
第三方 plugin 安裝仍各自需要明示 gate。

對應需求：`KG-ALPHA-01–04`、`KG-ING-01–04`、`KG-PLAT-06,08`、`KG-UI-01`；驗收：`SC-44–47`。

### Personal Alpha 工程進度

- **PA-1 deterministic preview：已通過。** 單一 explicit Markdown 可產生零寫入、無 external call 的人類可讀 preview；三種不同 Markdown shape、精確 locator、heading／knowledge Edge 分界、explicit relation 與 unresolved association 均有 targeted tests。完整 verifier evidence：`output/control-plane/verification-20260922T150751+0800.json`。
- **PA-2 transactional workspace：已通過。** 生成普通 Markdown 的 Start Here、Structure、Concepts、Relationships、Evidence、immutable Source 與 user-owned My Notes；同輸入 unchanged、source update 保留 unmanaged files、generated-file local edit fail closed，且 injected update／new-workspace failure 可 rollback。完整 verifier evidence：`output/control-plane/verification-20260922T152330+0800.json`。
- **PA-3 single daily command：已通過。** `python3 scripts/kgnote_alpha.py SOURCE --vault VAULT --space personal` 在同一命令內列出 preview、transactional apply、read-back、entry path 與 actionable error；README 與 `docs/WORKFLOW.md` 已記錄唯一日常路徑。完整 verifier evidence：`output/control-plane/verification-20260922T153030+0800.json`。
- **PA-4 three-source candidate：已通過。** 同一 documented command 已依序處理 hierarchical networking、heading-free music glossary 與 procedural gardening 三份來源；首跑均 applied/read-back pass，原樣重跑均 unchanged，且 source bytes、provenance、record identity、link reopen 與 rollback 均有 automated evidence。完整 verifier evidence：`output/control-plane/verification-20260922T153953+0800.json`；可檢查 workspace 位於 `output/personal-alpha/pa4-vault`，durable run evidence 位於 `docs/requirements/evidence/personal-alpha-pa4-20260922.json`。目前只升為 `candidate_verified`；product owner 的 Obsidian usability acceptance 仍是 PA-HUMAN-1。
- **PA-HUMAN-1 初次人工試用：未通過，待修復後重測。** Source／Evidence／relation tracing 與工程安全證據保留；但 `Start Here` 偏系統索引、短教材被過度拆頁，且 candidate／review／provenance 等系統資訊與真正學習文本以近似層級呈現。這是 learner-facing projection regression，不是 Canvas 格式缺口。人工證據：`docs/requirements/evidence/personal-alpha-human-feedback-20260923.json`。
- **Native capability spike 歷史 checkpoint：曾在 NS-0 後中止。** 官方 capability matrix 與 reuse inventory 保留於 `docs/obsidian/NATIVE_CAPABILITY_SPIKE.md`；當時 Canvas artifact、validator、tests 與三來源 spike vault 尚未開始，直到下列 V3 learner-facing automated gate 通過後才恢復。
- **V3 learner-facing projection remediation：automated gate 已通過。** 三份手寫 Golden fixtures 固定 Start Here、Port 與 Relationships 的呈現層級；舊 renderer 先產生 5/6 RED，之後加入 pure learner projection、human-readable collision-safe filenames、collapsed Evidence/debug、user-owned Continue Here 與三來源 generated-byte read-back。26 個 Personal Alpha targeted tests 與完整 repository verifier 通過；repaired artifact evidence 為 `docs/requirements/evidence/personal-alpha-v3-projection-20260923.json`。這不提升 PA-HUMAN-1。
- **Native capability spike：automated technical spike 已完成。** 三份 repaired Markdown workspace 均生成 deterministic JSON Canvas 並 semantic read-back；hierarchical fixture 有 file-backed H1/H2/H3、directed labeled/colored edges，glossary 不捏造 hierarchy，procedural 只表達順序而不升格因果。技術決策為 `native_sufficient_for_next_reading_slice`，見 `docs/obsidian/NATIVE_ARCHITECTURE_DECISION.md`。Obsidian desktop/mobile、hover/touch 與 learner usability 仍待 product owner smoke。
- **Integrated stage RP-PA-1：獨立 reviewer PASS。** Native command 明示輸出的 `Workspace` 才是應在 Obsidian 開啟的 exact vault root；validator 以同一 root 解析所有 Canvas file node。Start Here 在既有 Golden sections 後提供 secondary optional Canvas 入口，並只在 disposable generated vault 加入 vault-local Reading-view CSS snippet，使 lesson 先於 properties 顯示而不刪 provenance。PASS 只綁定該 sealed candidate；不提升任何 human gate。
- **Integrated stage RP-PA-2：獨立 reviewer PASS。** `Continue Here` 說明手動 close/reopen 流程，要求 exact note heading/block link 與 note/section/next/question；獨立 read-back 拒絕空 starter、欄位不一致與 stale anchor。Evidence 將 exact line bytes 與可點擊 navigation 分開：唯一 heading 可開 enclosing section，否則明示 document-only。same-input 與 source-update regression 逐 byte 保留 My Notes、Continue Here 與 unmanaged files。PASS 只綁定該 sealed candidate；不提升任何 human gate。
- **Integrated stage RP-PA-3：candidate implementation complete，待 orchestrator deterministic validation／獨立 review。** 同一 documented native preparation command 已對 hierarchical、heading-free glossary 與 procedural 三份 fixture 走完整 read-back，涵蓋 Start Here、source、concepts、source-supported structure／relationships、on-demand Evidence、manual continuation、optional Canvas、same-input rerun 與 source-update user-byte preservation。整合測試修正 native digest 誤納 learner-owned Markdown 的缺口。集中試用 exact handoff 為 `docs/obsidian/PERSONAL_ALPHA_INTEGRATED_TRIAL.md`；`PA-HUMAN-1`、`NS-HUMAN-SMOKE` 與 `release_verified=false` 仍未提升。
- **2026-10-07 concentrated-trial portability repair：fresh external review pending。** Human-handoff read-back 發現舊 command 把 worktree 絕對路徑雜湊進 source identity，repository migration 後同一 source 會產生不同 workspace suffix。正式 handoff 現在明示 stable external source key，保留 content hash 偵測 byte drift，並以跨兩個實際 worktree source path 的相同 workspace ID／digest read-back 與 regression tests 固定此 invariant；durable evidence 為 `docs/requirements/evidence/personal-alpha-portability-repair-20261007.json`。舊 external PASS 因而視為 stale；新 exact candidate 完成 internal／external re-review 前不得進 PA-HUMAN-1 或 NS-HUMAN-SMOKE。

## 一句話目標

使用者打開一篇普通 Obsidian Markdown 就能直接閱讀；遇到不懂的詞可在原句展開一句便利貼，能精確回到上次未釐清的位置，也能選擇只看熟悉例子、不必作答的 Soak；需要時才從同一位置進入練習、來源定位、提問與複習。只有對概念已有足夠且可說明的熟悉證據時，才把同一 Concept identity 放進知識漫遊圖。

## 從最初發想保留的產品循環

Obsidian-first 改變主要介面與進場順序，不撤回最初 KGnote 要解決的問題：學習脈絡不能只存在某一段 AI conversation，也不能要求使用者手工維護一張假精確的進度表。

```text
教材／AI 對話／真實工作事件
  → 保留 Source 與原始定位
  → 提出 Concept／relation／confusion／learning event 候選
  → 連回文章、舊例子與局部結構
  → 閱讀／精確續學／Soak／Practice／提問
  → 保存可觀察 evidence 與下一個未解問題
  → Due、教材結構圖與 Knowledge Roaming 投影
```

這個循環有幾條不可省略的產品意圖：

- **實作軌與理解軌並行。** 真實任務可先安全完成；學習支線保存後再接，不因陌生詞很多就讓三分鐘操作變成三小時前置課程。
- **系統保存脈絡。** 使用者正常閱讀、提問、跳過、回答與操作即可留下資料，不必每天填 Learning State、寫心得或逐條審核 ontology。
- **先熟悉再輸出。** 完全顯示答案的再曝光、選項／填空、提示回想與無提示輸出是不同活動；不把它們壓成一個 Quiz。
- **零譴責、無債務。** 答錯、說不知道、滑走、暫停數日或今天零活動都不產生罰分、連續天數壓力或必須清空的欠卡。
- **圖保存結構，不宣稱複製大腦。** 只保存來源、關係候選、問題、混淆、回答與應用等 evidence；不生成全域熟練百分比。
- **一個 engine，多個 Space。** CS、BitePacer、音樂、繪圖、裁縫等可有不同入口與視圖，但共享資料契約；可信的跨領域 Concept／association 可連結，同名異義不強併。

對應需求：`KG-WF-04–06`、`KG-MEM-01,04,07–09`、`KG-SOAK-01,04,07`、`KG-ING-02–04`、`KG-KNOW-02,07`、`KG-PLAT-01`；驗收：`SC-02–04`、`SC-16`、`SC-18`、`SC-26`、`SC-31`、`SC-37`。

## 不可變的共通邏輯

以下是舊工程中仍成立、且不因 Obsidian-first 而重做的契約：

- Source／Evidence 可追溯；AI 摘要、便利貼或後續文章修訂不冒充原始 snapshot。
- Source support、外部事實審查、teaching-answer readiness 分開。
- Concept Graph 與 Learning Overlay 分開；閱讀、曝光或 AI 提及不等於理解。
- 同一 Concept 使用 stable identity 與 aliases；mention、便利貼、題目、due、圖上節點不是新的同義 Concept。
- 章節、資料夾、Canvas group 與 tree parent 是導航結構，不自動成為 canonical knowledge Edge。
- 不確定的關係可保存為 `related_to`／unresolved association；不要求使用者先替每條線命名，也不把候選關係冒充精確事實。
- Attempt、Exposure、Due 與 history 分開；只閱讀、揭露、跳過、snooze 或離開不建立錯誤回答。
- 題目提交前答案隔離；提示、參考原文、答案揭露與無輔助回答分別保存。
- Soak 可以顯示答案且不要求提交；只有 Practice 的無輔助作答模式需要答案隔離。
- 暫停、跳過與 overdue 不形成懲罰性 debt；回來時可以直接選一則內容，不必先清空 backlog。
- 精確續學保存最後問題、實際回答、未釐清處、anchor 與暫緩支線；recent/history 卡不能替代。
- 不使用全域 mastery 百分比。UI 顯示可理解的行為／複習狀態及其依據。
- 寫入需 version、precondition、idempotency 與 recovery；不靜默覆寫使用者 Markdown。
- 外部模型、embedding 或資料外送需明確 adapter、資料邊界、授權與 provenance；無 live AI 時仍有可用路徑。

對應需求：`KG-MEM-01,05–09`、`KG-KNOW-01–07,09`、`KG-PRAC-02–07`、`KG-SOAK-01,04–05,07`、`KG-SRS-01–03`、`KG-PLAT-05–07`。

## 產品責任邊界

| 能力 | 優先承載 | KGnote 是否另做 | 驗收重點 |
| --- | --- | --- | --- |
| Markdown 閱讀、編輯、folders、properties | Obsidian 原生 | 否 | 不複製第二套 editor／file tree |
| Wikilinks、aliases、backlinks、heading／block link、hover preview | Obsidian 原生 | 只保存 stable identity／anchor 對應 | 點詞或圖節點能回文章與位置 |
| 手工大綱與可攜圖檔 | Obsidian Canvas／開放 JSON Canvas | 先做 adapter 或 generator，不先重造 canvas | Mac／iPad 可開，節點仍連 Markdown |
| 自動 tree layout、typed edge 詳述、review color overlay | 先評估現有跨平台外掛；不足才做 KGnote plugin | 是，僅補差距 | 同一結構 revision，不維護兩份名稱與線 |
| 原句便利貼與一鍵 inline 展開 | KGnote Obsidian plugin | 是 | 原文不被靜默改寫；收合／展開不跳頁 |
| 精確續學 context | KGnote plugin＋既有 resume domain layer | 是 | 回到最後問題、回答、混淆與文章 anchor，不只顯示 recent |
| Soak／低負擔再曝光 | KGnote plugin＋既有 Exposure domain layer | 是 | 可看答案、滑走、零作答；不建立錯誤 Attempt 或 debt |
| 分階段題目、Attempt、Due、confusion | KGnote plugin＋既有 domain layer | 是 | 支援程度與 evidence 可追溯 |
| source retrieval、問題路由與 AI 解說 | KGnote plugin；必要時 optional sidecar | 是 | 先找來源、再升級 AI；輸出可申覆 |
| 選定對話／工作事件匯入 | 既有 Markdown workflow＋KGnote importer | 是，但限明示選定來源 | 保留 speaker／tool／action attribution；只生成候選 |
| 多 Space 與跨領域連結 | Obsidian folders／properties＋KGnote identity layer | 是，資料驅動 | 不為每個學科另造 App；同名異義不強併 |
| 大型索引、embedding、背景工作或重型圖運算 | optional local sidecar | 只有需求被證明時 | sidecar 故障不妨礙 Markdown 閱讀 |
| 一般閱讀入口 | Obsidian note | 不再以 Web dashboard 取代 | 使用者不必學 KGnote 術語 |

平台依據只說明可重用能力，不證明學習效果：Obsidian 原生支援 note／heading／block links 與 hover preview、Canvas directed connections／labels／colors，以及可收合 callouts。自訂 plugin 若要跨 iPad／iPhone，核心路徑不得依賴 mobile 不提供的 Node.js／Electron API。

對應需求：`KG-PLAT-01–03,05–08`、`KG-STR-06,08`；驗收：`SC-38–39`。

## 日常介面只顯示一件主要工作

普通狀態只是一篇 Obsidian 文章。KGnote 不常駐顯示 Claim／Evidence／Lens／Attempt 等內部術語；這些留在稽核、衝突與進階檢查層。

### 閱讀狀態

- 頁面主體是文章。
- 已存在的 Wiki link 照常使用；hover preview 與 backlinks 不另做一套。
- 陌生詞只用低干擾 highlight／便利貼標記。
- 使用者選取文字後，最多先看到一組短動作：`解釋一句 | 提問 | 稍後`。
- 不自動打開 Graph、Evidence panel、Practice、note editor 或全套 metadata。

### 需要時才展開

- 點文章標題／breadcrumb：看教材結構。
- 點「繼續上次」：回到最後問題、實際回答、未釐清處與精確 anchor。
- 點便利貼：在原句 inline 展開一句話。
- 點「浸泡一下」：看一則已知材料或舊例子，可直接滑走，不必作答。
- 點「練一下」：進入單一題目，而不是新的 dashboard。
- 點「為什麼」：先顯示最接近來源段落；需要時再看 AI 解說與 provenance。
- 點「關係漫遊」：只有 eligible Concept 才進入 Knowledge Roaming Graph。

完成條件：第一次打開 note 的使用者只靠 Obsidian 既有閱讀模型即可開始；未使用 KGnote 功能時沒有額外學習成本。內部 record 名稱不是完成任務的必要知識。

對應需求：`KG-UI-01`、`KG-WF-01–05`、`KG-CTX-01–07`；驗收：`SC-38`、`SC-40`。

## 兩種圖的明確分工

### A. 教材結構圖：從一開始可見

用途是回答「這個領域有哪些文章／主題，我現在在哪裡？」

- 以 tree 為預設閱讀模型：領域 → 主題 → 子主題 → Markdown 文章／anchor。
- Edge 是組織關係，可標 `子概念／平行／對立／替代／時序／問題—解法／例子`。
- 只有來源或人工判斷足以支持時才使用精確 relation；暫時只知道「相關」時可保留無方向／unresolved association，不阻塞閱讀。
- 短 label 常駐；hover、focus 或 touch 展開更完整的關係描述。
- 點節點打開 LLM Wiki article 或指定 heading／block。
- 結構 node 可引用 Concept，但 tree parent／membership 本身不生成 canonical Edge。
- 第一個 spike 優先測原生 Canvas／JSON Canvas；若自動 tree、hover detail 或 review overlay 不足，再做最小 plugin renderer。

### B. Knowledge Roaming Graph：熟悉後才可進入

用途是回答「在我已能順暢聯想的認知範圍內，還能如何跨文章探索？」

- 不作陌生教材首頁，也不拿全庫圖代替學習結構。
- 只有 `roam_eligible` Concept 出現在預設漫遊圖；閱讀次數或 Concept record 存在不足以取得資格。
- eligibility 使用可說明的行為 evidence 與使用者 override；初版不設假精密分數。
- 探索到尚未 eligible 的外部概念時，只顯示邊界／問題入口，不把整片未知圖展開造成負荷。
- 原有 local neighborhood、typed relation、Evidence 與 scope planner 可重用，但 renderer 必須在 Obsidian-first formative gate 後才接回主線。
- 漫遊可跨 Space 顯示可信的聯想與共同 Concept，但預設仍以局部 neighborhood 呈現，不載入全庫宇宙圖。

兩張圖可引用同一 Concept identity，但不要求顯示相同集合；教材結構圖的「子主題」不等於知識漫遊圖的 `part_of`。

對應需求：`KG-STR-01–04,07–08`、`KG-GRAPH-01–05`、`KG-KNOW-06`；驗收：`SC-07–08`、`SC-29`、`SC-39`、`SC-43`。

## 便利貼：原句中的最低必要解說

便利貼處理「目前不懂，但尚未值得另建完整文章或複習 Concept」的認知盲區。

```text
收合：所有程序的起點皆源於共同祖先 PID 1。

展開：所有程序的起點皆源於共同祖先
      PID 1（Process ID 是核心用來唯一識別執行中 Process 的整數值）。
```

首版資料必須包含：annotation ID、文章 revision、精確 anchor、選取文字、最小解釋、來源／產生方式、revision、是否被使用者接受。它是 annotation，不自動成為 Concept；之後有更多內容、連結或複習價值時，才提供明示 promotion preview。

首版行為：

1. 使用者反白文字，選 `建立便利貼`。
2. 先顯示一句可編輯解釋 proposal；可接受、修改或取消。
3. 接受後在閱讀 view 可 inline 展開／收合，不覆寫 source snapshot。
4. 若文章本身是可修訂 LLM Wiki note，`寫入文章` 是另一個明示動作：產生新 revision／diff，保留原 anchor 與 proposal provenance。
5. 同詞在另一句不自動重複展開；可引用同一 Concept／gloss，但 context explanation 可不同。

完成條件：不離開原句即可重讀解釋；收合後文章仍像普通 Markdown；取消不留垃圾節點；stale anchor 不猜位置或覆寫文字。

對應需求：`KG-CTX-01–06,10`、`KG-KNOW-01,06,09`、`KG-PLAT-06`；驗收：`SC-11–12`、`SC-40`。

## 浸泡：可以只曝光，不必作答

Soak 是獨立活動，不是把 Practice 題目改名。它處理「現在只想再看一眼，慢慢熟悉味道」的情境：答案、舊例子與必要關係可以直接顯示，使用者不必先回想或提交。

```text
今天再碰一下：Port

你曾在 127.0.0.1:5050 看過它。
5050 是 port，用來區分同一台 host 上的不同 network service。

[再看一個相似例子]  [練一下]  [滑走]  [暫停]
```

首版行為：

- 可從文章、Due、教材結構圖或「繼續上次」進入一則 Soak，但不強迫每天開啟。
- 可複習單一 Concept、真實 Edge 或小型 neighborhood；內容保留原主題與舊例子，不拆成孤立字卡。
- `看過／揭露／滑走／不知道／停止` 只建立 Exposure；不建立錯誤 Attempt，不宣稱成功 retrieval。
- 同一 Target 可由幾乎原句與完整答案開始，日後提供較少提示、不同措辭或新情境；相似度、提示量、輸出要求與間隔分別記錄，不固定自動升級。
- 使用者可一直保留熟悉例子、退回完整答案，或主動切到 Practice；系統不能因答對一次鎖掉提示。
- 沒有 live AI 時仍能從 reviewed Source／Evidence 產生 deterministic offline Soak；模型只負責可審核的變體，不決定使用者能力。

完成條件：啟動後可只看一則→滑走→結束；數日未使用後可直接回來看一則，不先清空 backlog；Soak 顯示答案不會污染同一 Target 的無輔助 Practice；Exposure history 與 Attempt history 可分別讀回。

對應需求：`KG-SOAK-01–07`、`KG-SRS-03`、`KG-MEM-02,04`；驗收：`SC-02–03`、`SC-17–19`、`SC-24`。

## 練習：先辨認，再逐步回想

Practice 是使用者選擇進入的輸出活動。它不是單一 relation fill-in，也不以自由回答作陌生內容的第一個預設活動；Soak 看過答案不自動等於已完成 Practice。

| 支援階段 | 首選活動 | 題目原則 | 可觀察紀錄 |
| --- | --- | --- | --- |
| 1. 再辨認 | 原文挖空＋選項 | 保留原句與上下文，只挖一個必要詞／短關係 | selected option、原文是否可見 |
| 2. 有線索辨認 | 選擇／區辨 | distractor 來自真實易混淆點，不造無意義陷阱 | option、hint、confusion |
| 3. 有提示回想 | 首字／概念提示／局部句框 | 問法貼近原始文章，不同措辭有教學理由才使用 | prompt revision、hint events |
| 4. 無提示回想 | 填空／短答／自己的話 | 只在先前支援或使用者主動選擇後進入 | raw response、answer visibility |
| 5. 理解驗收 | 比較／解釋／應用 | 針對機制與概念才換情境；不拿新奇 wording 增加無關負荷 | rubric、Evidence、申覆 |

階段不是人格、永久能力標籤或必須逐關解鎖的課程。使用者可保留提示、退回上一階段、直接挑戰、回答不知道或跳過。自動建議只根據可追溯事件，不用 mastery 百分比。

完成條件：同一 Target 至少能以有選項 cloze 與無提示 recall 呈現；兩者共享 Source／Claim identity但建立不同 ReviewItem／Attempt context。初次錯誤不被描述為「應該硬想出來」。

對應需求：`KG-WF-02`、`KG-PRAC-01–09`、`KG-SOAK-02–03,05`；驗收：`SC-17`、`SC-19–20`、`SC-41`。

## 提問：source retrieval 優先，AI 按需要升級

問題入口存在於閱讀與練習，不另開一個與文章斷裂的 chat product。

```text
使用者問題＋選取文字＋當前段落
  ↓
1. 搜尋目前文章、直接連結文章與 reviewed Evidence
  ├─ 足以回答：回傳最接近段落、anchor 與短說明
  └─ 不足：分類問題
       ├─ 當句術語 → 有界便利貼
       ├─ 跨段／跨文章比較 → 較強 AI 解說
       ├─ 深度合理且有助本質理解 → 建議擴充
       └─ 目前偏題或過深 → 保存為稍後探索，不阻塞正文
```

AI 選擇取決於任務複雜度與資料邊界，不把 Codex／ChatGPT／Gemini 名稱寫進 canonical record。每個回答保存 input scope、retrieved anchors、provider／model（若有）、output、confidence／限制與使用者處置。

「逐漸擴充 LLM Wiki」採 proposal → preview → accept 的流程：

- 原始 source snapshot 永遠保留。
- AI 解說先是 learning expansion，不是 source 或 fact。
- 使用者接受後，可新增連結 note、補入現有可編輯文章的新 revision，或只保留問題歷史。
- 同一概念先 resolve stable identity／alias；不得因每次問答建立新節點。

完成條件：原文足以回答的問題不呼叫外部模型；跨概念問題能明示為何升級；偏題建議可被覆寫；任何 AI 內容都不會無 preview 寫進 Markdown。

對應需求：`KG-AI-01`、`KG-CTX-01–05`、`KG-KNOW-02–04,09`、`KG-PLAT-03,05`；驗收：`SC-32`、`SC-42`。

## 選定來源與真實工作事件回流

KGnote 不只從整理好的教材學習，也要保留真實實作中「概念第一次落地」的 context；但這不等於掃描整個 vault、把所有 coding 名詞都算成使用者學過。

```text
使用者明示選定的 ChatGPT／Codex 對話、Markdown 或操作紀錄
  → immutable Source snapshot＋speaker／tool attribution
  → 提出 Concept／question／confusion／action／outcome 候選
  → 自動保存安全的未審 learning event
  → 只有事實 Edge、標準答案或正式文章修訂需要適當 review／preview
```

實作軌與理解軌必須分開又能互相引用：安全完成真實任務不必等所有名詞學完；當下不展開的問題保存為 continuation branch，之後能回到原 command、log、文章或對話。唯讀查驗、實際變更、觀察到恢復、使用者提出的因果假說與後續證據要分開，不能把時間上相鄰的對話冒認成成功修復動作。

完成條件：選定單篇來源可匯入並保留 hash／locator；AI-only 敘述不產生「使用者理解」事件；四個 PASS、未成功 restart 與後續網路恢復可依原時間線讀回；未審候選不阻擋閱讀，也不進入可考集合。

對應需求：`KG-WF-04`、`KG-MEM-03–04,07–09`、`KG-ING-01–04`、`KG-PLAT-05`；驗收：`SC-03`、`SC-15–16`、`SC-21`、`SC-28`、`SC-31–32`、`SC-37`。

## 記憶複習：清單與結構圖是同一份狀態的兩種投影

- Due Queue 回答「今天可複習什麼」。
- 教材結構圖顏色回答「整個領域哪些位置正在熟悉、已到期或有未解疑問」。
- 兩者引用同一 Target／Due／Attempt history；Canvas 或圖 renderer 不另算一套狀態。
- 顏色只表達可說明狀態，例如 `未排程／正在熟悉／今日到期／已完成本輪／有疑惑／roam eligible`，不表示掌握百分比。
- 七天排程先當使用者選定的簡單方案；起算點、milestone、snooze、skip、停止與 timezone 必須可見、可重放。若沿用 1／3／7／21 prototype，必須明示它不是「已量測的個人遺忘曲線」。
- 自然閱讀或工作中再次遇到 Concept 可減少近期重複推送，但只記 Exposure；只有實際作答 evidence 才能記成功 retrieval。
- overdue 是「有東西可回來看」，不是欠債。跳過數日、今天零活動或暫停整個 Space 都不產生罰分、連續天數損失或強制補完。
- 點著色節點直接進入對應文章 anchor 或 ReviewItem；完成後回到同一結構位置。

完成條件：任務清單與圖上節點不會對同一 Target 顯示矛盾狀態；snooze 不建立 Attempt；只閱讀不讓節點假裝通過 recall；顏色有文字／圖例替代，不只靠色覺。

對應需求：`KG-SRS-01–06`、`KG-STR-08`、`KG-PLAT-02`；驗收：`SC-18`、`SC-23–24`、`SC-43`。

## 跨階段資料連接

一個概念只維護一個 stable identity：

```text
Concept process-id
  aliases: PID, Process ID, 程序識別碼
  mentions: article + anchor
  annotations: 便利貼
  learning_events: 問題 / 混淆 / 實作 / 回答
  exposures: Soak / 自然再次遇見
  review_items: cloze / choice / recall
  due_state: schedule projection
  resume_contexts: 最後問題 / 回答 / 未解支線
  structure_appearances: tree / Canvas nodes
  roaming_node: eligible 後的 KG projection
```

`mention`、`annotation`、`learning event`、`exposure`、`review item`、`due`、`resume context`、`structure appearance` 與 `roaming node` 是不同 record；它們引用 Concept，不重新定義 Concept。若文字同名但語意不同，先保留 unresolved，不強併。若便利貼只有當句用途，也可沒有 Concept ref。

完成條件：重新命名 alias 不產生第二份學習歷史；從題目、便利貼、due 或圖節點都能回到同一文章與 Concept；刪除 view projection 不刪 Source、Attempt 或 canonical identity。

對應需求：`KG-KNOW-01,05–07,09`、`KG-PLAT-01,06–07`；驗收：`SC-05`、`SC-15`、`SC-26`、`SC-39–43`。

## 精確續學：接回問題，不是只開最近文件

Resume 是一個可攜的局部 context，不是 history 頁或「最近看過」卡。每個可續學 checkpoint 至少包含：

- Space／unit／Source revision 與文章 heading／block anchor。
- 當時目標與最後一個具體問題。
- 使用者實際回答、使用過的提示、最後解說與尚未釐清處。
- confusion pair、暫緩支線與下一個安全動作。
- 相關 Concept／Evidence refs，以及哪些事情尚無紀錄或不能推定。

使用者可從文章、教材結構圖或全域 command 選 `繼續上次`，直接回到該位置；不同 AI／導師可取得同一份有來源的局部續學包，不必重貼整段對話。正常離開時自動保存，不要求填表；系統誤記時可更正，但不抹去原 event。

完成條件：Git 學習能接回 branch／worktree 的具體疑問而不是重教 Git 定義；無歷史時明示「沒有可用紀錄」；recent item 不得冒充 continuation；從一台裝置保存後，另一端至少能讀回相同 Markdown／sidecar context，未實機驗證時不得宣稱完整跨裝置通過。

對應需求：`KG-MEM-01–02,04–05,07–08`、`KG-WF-03`、`KG-PLAT-02,06–07`；驗收：`SC-03`、`SC-10`、`SC-14`、`SC-22`、`SC-27`、`SC-30`。

## 多 Space：一個引擎，不為每個學科另造 App

Space 是導航與權限邊界，不是另一套資料模型。Computer Science、BitePacer、音樂、繪圖、裁縫等可有自己的教材樹、Due 視圖與預設 scope；共享 Concept 只有在 identity／來源足夠時才跨 Space 引用。跨領域的 creative analogy 可保存為 association＋Evidence，不必為了進圖發明冗長的 canonical relation。

完成條件：renderer、Soak、Practice、Resume 與 Due 不 hard-code OS／熟悉材料；至少使用兩種不同領域 fixture 驗證同一流程；同名異義反例不被合併；暫停某個 Space 不影響其他 Space，也不產生債務。

對應需求：`KG-PLAT-01`、`KG-KNOW-01–02,05,07`、`KG-SOAK-04,06`；驗收：`SC-10`、`SC-18`、`SC-26`、`SC-31`。

## 現行交付階段

### O0：停止擴張並保存可重用工程

狀態：本 roadmap 已完成；程式處置尚待下一切片。

- [x] 現有 Web Learn UI 記為 usability finding，不用更多 panel 修補掩蓋。
- [x] 舊 DEVELOPMENT_PLAIN 完整移入歷史檔並標 superseded。
- [ ] 為現有 Web routes 加上 `prototype / comparison harness` 定位，不刪除資料或測試。
- [ ] 列出可重用 domain modules：Source／Evidence、catalog、Attempt、Exposure、Due、resume、Claim review、graph planner。
- [ ] 停止新增 Web-only learning workflow，除非是安全修復或 comparison test。

### O1：Obsidian 能力盤點與最小技術 spike

目標：先證明哪些能力不必重造。

- [ ] 先在 Mac disposable vault 驗證 Markdown links／aliases／backlinks／hover preview、heading／block anchor、Canvas directed labeled edge 與資料 read-back。
- [ ] 盤點現有社群外掛，但不得只因名稱相符就採用；記錄更新狀態、資料格式、mobile 支援、network／telemetry、可匯出與失敗回退。
- [ ] 只有原生能力／現有外掛不足時，才建 disposable、mobile-compatible plugin skeleton；不連 live AI、不掃整個 vault、不修改正式 LLM Wiki。
- [ ] 以 iPad／iPhone 約束做相容性 gate 與 read-back；桌面 spike 可先完成，但未實機操作不得宣稱 mobile UX 通過。
- [ ] 定義 vault allowlist、writer ownership、sidecar boundary 與可攜資料格式。

通過後才決定：原生 Canvas＋小外掛、既有社群外掛 adapter，或自建最小 tree renderer。不得在 spike 前宣稱必須做獨立 App。

### O2：最小 Obsidian-first 閱讀切片

只交付一條可人工試用的路徑：

```text
打開一篇既有 Markdown
  → 看普通文章
  → 從領域 tree／Canvas 點回本文
  → 反白一個陌生詞建立一句便利貼
  → 在原句展開／收合
  → 關閉重開仍可讀回
```

非目標：Practice、Due、Knowledge Roaming、RAG、live AI、批次匯入、公開部署。

完成條件：來源 snapshot 不變；若選擇正式寫入可編輯文章，必須有 preview／new revision；Mac 可完成完整流程，iPad／iPhone 的資料與核心操作相容性另列實際結果，不用 viewport 冒充實機；拔掉 plugin 後 Markdown 與 Canvas 仍可讀。

### O3：Obsidian-first 精確續學

- [ ] 把既有 resume domain layer 投影到 Obsidian note／heading／block anchor，不只顯示最近開過的 unit。
- [ ] 保存最後問題、使用者實際回答、提示、最後解說、未釐清處、confusion 與暫緩支線。
- [ ] 從文章、教材結構圖與全域 command 都能 `繼續上次`，並在完成／暫停後回到原 scope。
- [ ] 正常離開自動保存；無歷史明示無紀錄；stale anchor 不猜位置；可匯出 provider-neutral 的局部續學包。
- [ ] 以 branch／worktree fixture 驗證不會只重教 Git 定義；沿用 SC-03 的既有 domain evidence，但 Obsidian UI 另做人工 smoke。

### O4：獨立 Soak／浸泡閉環

- [ ] 從一個 reviewed Source／Evidence 顯示完整答案與舊例子，不要求輸入。
- [ ] 支援 `再看相似例子／練一下／不知道／滑走／暫停`；除主動轉 Practice 外只建立 Exposure。
- [ ] 單一 Concept、真實 Edge 與小型 neighborhood 都可成為 Soak target，保留原主題與來源。
- [ ] 相似度、提示量、輸出要求與間隔分開；使用者可一直保留提示，不答對一次就強制升級。
- [ ] 數日停用、overdue backlog、offline fixture、reload 與 Soak→Practice 答案隔離皆有負例驗收。

### O5：分階段單題 Practice 閉環

- [ ] 由一個 reviewed Source span 建立原文 cloze＋選項。
- [ ] 同一 Target 可在使用者主動選擇或可說明 evidence 後切到提示／無提示回想。
- [ ] Practice 直接出現在文章 context 或小型 modal；提交後回原 anchor。
- [ ] 保存 activity type、support、raw response、hint／answer reveal、confusion 與 retry；沿用既有 Attempt safety。
- [ ] 問法貼近原文；任何較遠 transfer 題另標目的與階段。

### O6：問題路由、文章擴充與選定事件回流

- [ ] 先做 literal／heading／linked-note retrieval，不先上 embedding。
- [ ] 原文能回答時只回 anchor；不足時才進 AI adapter。
- [ ] 對便利貼、跨概念比較、偏題／稍後探索建立不同處置。
- [ ] learning expansion 經 preview 後才能成為 LLM Wiki 新 revision／linked note。
- [ ] 支援明示選定的單篇 Markdown／對話／操作紀錄匯入；保存 hash、locator、speaker／tool 與 action attribution。
- [ ] extraction 只形成 Concept／question／confusion／learning-event 候選；AI-only 內容不生成使用者理解，未審候選不進可考集合。
- [ ] 操作時間線區分唯讀查驗、實際變更、觀察結果與因果假說；實作可先完成，理解支線保存後再接。
- [ ] live provider 前重新核對授權、資料外送、成本、retention 與 mobile／sidecar 路徑。

### O7：複習地圖、Knowledge Roaming 與多 Space

- [ ] Due Queue 與教材結構圖共用同一 schedule projection。
- [ ] 節點顏色＋文字狀態、圖例、click-to-Soak／review 與返回位置。
- [ ] 自然 Exposure 可抑制近期重複推送但不算 recall；暫停、跳過、overdue 與零活動不產生 debt 或懲罰。
- [ ] 定義 roam eligibility 的行為證據、使用者 override、撤回與 stale 規則；不使用全域 mastery %。
- [ ] 只投影 eligible Concepts；未知邊界提供提問，不展開整個陌生網路。
- [ ] 支援 unresolved／soft association 與 Evidence，不要求使用者逐線命名；view grouping 不升格成 canonical Edge。
- [ ] 同一 engine 支援至少兩個不同領域 Space 與可信跨 Space identity；同名異義不強併，暫停一個 Space 不影響其他 Space。
- [ ] 以 熟悉材料 做熟悉材料的 UI／定位測試，以 OS／真正陌生材料與至少一個非 CS fixture 分別測結構恢復、初學與 generic architecture；材料不永久等同能力級別。

## 下一個單一切片

目前唯一 active 工程切片是 **RP-PA-3 integrated candidate**：由 orchestrator 對 exact repository
fingerprint 執行 deterministic validation 與獨立 review。若 reviewer 要求修改，仍只在 RP-PA-3 內修復
並保留 finding IDs；不得先開始新產品能力。

RP-PA-3 通過後，下一個 coherent checkpoint 是 product owner 對
`docs/obsidian/PERSONAL_ALPHA_INTEGRATED_TRIAL.md` 所列 exact candidate 的一次集中試用：

1. 從 Start Here 讀 source、concepts、source-supported structure／relationships，按需開 Evidence。
2. 在 My Notes 與 Continue Here 留下 learner-owned bytes，關閉重開後回到 exact heading/block。
3. Markdown 路徑先獨立完成，再選擇性檢查 Canvas 與 vault-local Reading view。

同一操作可提供兩類 evidence，但 `PA-HUMAN-1` 與 `NS-HUMAN-SMOKE` 必須各自判定。自動 read-back、
reviewer PASS 或 Canvas JSON 正確都不得替代真人／native 結果，也不得把 `release_verified` 提升為 true。

## 驗收層級

| 層級 | 可以宣稱 | 不可宣稱 |
| --- | --- | --- |
| Structural guard | ID、source、scenario、binding 結構完整 | UI 已簡單、語意完整或學習有效 |
| Automated tests | contract、持久化、失敗安全行為通過 | product owner 覺得好用 |
| Browser／Obsidian smoke | 指定流程可操作、render 與 read-back 正常 | 熟悉度或長期記憶改善 |
| product owner formative acceptance | 此版本符合實際使用意圖、摩擦可接受 | 普遍學習效果 |
| 延遲／應用觀察 | 指定材料與條件下的行為結果 | 跨人群或所有知識類型的因果結論 |

## 暫停／延後

- 繼續美化目前 Web Learn 多欄頁面。
- Web-only note editor、第二套 Wiki、第二套 file tree。
- Graph database、Neo4j、Graph RAG、全庫 embedding。
- 全庫自動掃描與自動批次修改正式 LLM Wiki；O6 的明示單篇匯入不在此列。
- 全域 mastery %、自動 community detection、centrality 決定重要性。
- 3D Graph、大型 compound graph、公開部署、auth／multi-user、LINE／LIFF、語音。
- 在沒有 Obsidian mobile spike 前決定 desktop-only plugin 或獨立 App。

這些項目保留於需求台帳或歷史 roadmap；延後不等於刪除。

## 可重用的既有成果

| 既有成果 | 新主線用途 | 處置 |
| --- | --- | --- |
| Markdown importer、source hash、Evidence locator | Obsidian note／anchor 註冊與來源查核 | 保留 |
| Concept stable IDs、aliases、Claim review | 跨文章／便利貼／題目／圖的 identity | 保留 |
| Attempt、Exposure、Due、feedback、resume | plugin domain layer | 保留，換 UI adapter |
| exact continuation／Soak regression | O3／O4 的 domain baseline | 既有測試證明舊能力，不冒充 Obsidian UI 已接入 |
| graph read model、planner、local neighborhood | O5 Knowledge Roaming engine | 保留，暫不作首頁 |
| Guided Map structure fixtures | tree／Canvas adapter 輸入候選 | 重新命名為教材結構，不當知識 Edge |
| Web Learn／Practice／Soak／Review | regression、comparison、資料 API prototype | 凍結擴張，不刪除 |
| versioned LearningNote Web editor | writer safety 與 recovery reference | 不與 Obsidian editor 競爭 |
| 熟悉材料／OS／BitePacer fixtures | 熟悉 UI、中熟悉恢復、陌生流程候選 | 保留用途，不標能力人格 |

## 決策與歷史索引

- 2026-09-22 使用者方向修正：`docs/requirements/USER_DIRECTION_DELTA_20260922.md`。
- 2026-09-22 Obsidian-first Personal Alpha 目標：`docs/requirements/PERSONAL_ALPHA_DIRECTION_20260922.md`。
- 2026-09-22 原始發想再整合裁決：保留 Obsidian-first 必要修正，將精確續學、獨立 Soak、真實事件回流、soft association、無債務與多 Space 補回本 roadmap；同一 delta 文件保存此後續澄清。
- 2026-09-20 requirements baseline、trace 與 scenario：`docs/requirements/`。
- 2026-09-22 前完整 roadmap／工單／驗收表：`docs/DEVELOPMENT_PLAIN_SUPERSEDED_20260922.md`。
- 產品契約：`docs/PRODUCT_CONTRACT.md`；資料模型：`docs/DATA_MODEL.md`；表示一致性：`docs/REPRESENTATION_CONSISTENCY_CONTRACT.md`。
- 本次只更新需求／roadmap；程式仍是已存在的 Web prototype，不可把文件方向寫成 implemented。

## 本次 roadmap 再整合完成條件

- [x] 保留 Obsidian-first、文本優先、兩種圖分工與簡化 UI，不恢復 Graph-first Web 首頁。
- [x] 精確續學、Soak、Practice、事件回流、複習／漫遊與多 Space 各有清楚交付位置，不以彼此替代。
- [x] Soak 明示可顯示答案、零作答、零債務，並與 Practice Attempt／答案隔離分開。
- [x] 原始對話 iCloud export 以新 hash／位置登記，不覆寫舊附件 hash 或靜默重設行號。
- [x] requirements guard／自身 tests／生成 trace／`git diff --check` 通過。
- [x] 回報明確區分：roadmap 已補齊，產品尚未按新順序接入 Obsidian，人工試用仍待 O1／O2。

文件驗證結果（2026-09-22）：baseline `kgnote-reconciliation-2026-09-22-r3`；requirements guard 為 `structural_traceability_pass`（93 requirements／43 scenarios），guard 自身 16 tests 通過，四份衍生 trace views 已重新生成，`git diff --check` 通過。`U-ROADMAP-REINTEGRATION` 已連到 14 個既有 Requirement IDs；iCloud export hash 已再次讀回相符。這些結果只證明 roadmap 與追溯結構，**不代表 O1–O7 已接入 Obsidian，也不代表 UI 或學習效果已通過人工驗收**。
