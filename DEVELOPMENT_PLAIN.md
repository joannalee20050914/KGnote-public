# KGnote 白話版開發計畫

> 狀態：Phase 2 離線實用性驗證已完成，進入 Phase 3 read-only Web Graph Viewer
> 更新：2026-09-08
> 命名說明：本檔依專案建立需求使用 `PLAIN`，意指「不用專案術語也能檢查」的白話版計畫。

## 一句話目標

先驗證「把一段學習對話變成有來源、可點回原文、可用 Obsidian 圖導覽的概念筆記」是否真的有用，再開發 Web UI、Gemini 複習、語音或 LINE 入口。

## 不可變的產品原則

- 長文與原始對話是 evidence，不是要被圖取代的垃圾。
- edge 是導覽索引，proposition/evidence 才是回看時的完整上下文。
- 圖可以不完整。不確定的關係允許留白或 `related_to`。
- 學習狀態用可追溯的行為 evidence 表示，不用「理解 73%」。
- 一個 engine 支援多個 space/notebook，且允許跨 space 關係；不為每個學科建新 App。
- Responsive Web 是未來主介面；Obsidian 是 source of truth 與 v0 導覽器；LINE/LIFF 若採用也只是入口，不是核心架構。

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

## 當前主線：Phase 1 - 可重現的 Markdown extractor MVP

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

## Phase 4 - Gemini RAG 複習切片

- [ ] 只取 canonical concept note、相關 evidence、1-hop neighborhood 與 previous confusion 作 reviewer context。
- [ ] 先做一題一答；只輸出 `CORRECT | PARTIAL | INCORRECT | INSUFFICIENT_EVIDENCE` 與最多兩句 correction。
- [ ] 紀錄回答、hint 使用與 source context，不自動寫成「已理解」。
- [ ] 先人工選 concept，不做自動 scheduling。

## Phase 5 - 低摩擦曝光與多端入口

- [ ] 以可觀察事件建立 review scheduling，先用簡單、可解釋規則。
- [ ] hint fading：原句曝光 → 填空 → 換 context → 自由輸出 → 推理。
- [ ] 語音輸入、review feed、LINE/LIFF 或 LINE MINI App 在當時再做產品與隱私決策。

## 停車場（不打斷當前主線）

記錄格式：`date | idea/problem | why not now | expected phase`

- 2026-08-14 | Neo4j/專用 graph database | v0 用 Markdown/YAML 就能驗證價值，現在引入會同時增加 migration 與 sync 問題 | Phase 3 後重新評估
- 2026-08-14 | Graph RAG 與 reranker | 先證明 concept/evidence graph 本身可用；否則 RAG 只是放大壞資料 | Phase 4
- 2026-08-14 | 遺忘曲線、自動 due date | 需要真實互動資料才能設計，不先猜使用者記憶模型 | Phase 5
- 2026-08-14 | LINE/LIFF/LINE MINI App | 它們是入口而非核心，且屆時應重新查證官方產品狀態 | Phase 5
- 2026-08-14 | 批次匯入全部 LLM Wiki | 需先從小 fixture 量測 hallucination、relation error、merge conflict 與成本 | Phase 2

## 驗收記錄

| 日期 | 切片 | 結果 | 證據／限制 |
| --- | --- | --- | --- |
| 2026-08-14 | 專案治理與設計基線 | 完成 | 建立 agent 規範、產品 contract、最小資料模型、分期計畫與來源索引；尚無 executable code，不宣稱 extractor 或 Obsidian flow 已驗證。 |
| 2026-09-07 | Phase 0 data contract 與 synthetic fixture | 完成 | `fixtures/phase0-obsidian/` 共 20 筆 canonical records；read-back 通過 unique ID、reference integrity、edge policy、source SHA-256、locator 與 wiki link 檢查。桌面版 Obsidian 驗收確認 Graph 節點互連、無 unresolved/ghost links，Correlation／Confounder／Counterfactual 三條 Concept → Evidence → Source 路徑皆成功；counterfactual 僅為 unresolved soft association，提問／應用未被宣稱為 understood。截圖保留於 repository 外的 `<local-validation-artifact>` 與 `<local-validation-artifact>`。 |
| 2026-09-07 | Phase 1 versioned extraction schema contract | 完成 | `scripts/run_tests.sh` 通過 6 個 contract test methods 與 21 個具名 malformed cases；valid input/output、版本 fail-closed、strict fields、RFC 3339 timestamp、local refs、三種 edge policy、provenance 與禁止 proficiency claims 均已驗證，Phase 0 read-back 亦通過。JSON Schema 無法單獨證明跨 record local ref 存在／唯一或 input/output source 相同；目前只對 valid fixture 做 read-back assertion，正式語意驗證留給後續 normalization 切片。 |
| 2026-09-07 | Phase 1 single-file Markdown source importer | 完成 | `scripts/run_tests.sh` 共 14 個 tests 通過；驗證 Phase 0 raw source 可完整 UTF-8 round-trip、SHA-256 對 exact bytes、重跑 deterministic、只讀明確檔案、無 network/vault write，以及 missing/directory/extension/read/UTF-8/empty 與 metadata schema failures 的安全 code/path。Importer 刻意不解析 front matter，Source identity 與 locator basis 仍由 caller 明確提供；batch scan、metadata inference 與 extraction 不在本切片。 |
| 2026-09-07 | Phase 1 offline extraction-response boundary | 完成 | `scripts/run_tests.sh` 共 24 個 tests 通過，其中 21 個具名 rejected-response variants 涵蓋 strict JSON、root/collection、adapter-owned field、candidate schema 與 adapter metadata。Accepted result 注入 Source/version/timestamp，Evidence/Event Source ID 一致；accepted/rejected 皆 deterministic 且保存 exact raw response SHA-256，repr/rejection 不洩漏內容。測試證明無 network/vault write，Phase 0 read-back 通過。跨 collection local-ref 存在／唯一仍留給 normalization；provider API、raw-response persistence 與 retry 尚未實作。 |
| 2026-09-07 | Phase 1 deterministic normalization 與 local-reference integrity | 完成 | `scripts/run_tests.sh` 共 34 個 tests 通過；golden read-back 固定 4 Concepts、2 Evidence、1 LearningEvent、3 Edges 與 10 筆 local-ref mapping。`kgnote.normalize.v1` 驗證 duplicate/dangling/wrong-kind/canonical refs 與 Source mismatch，使用 typed/versioned full SHA-256 stable IDs，且 input/list/local-ref permutation 不改 canonical records；identity collision 明確回 conflict，不自動 merge。AI Concept/Evidence 預設為 `needs_review`／`unreviewed`，不推論 understood/proficiency。此切片純轉換且不讀 existing vault、不寫檔、不連網；existing-note comparison、dry-run 與 apply 留給後續 Issue。 |
| 2026-09-07 | Phase 1 deterministic dry-run planning | 完成 | `scripts/run_tests.sh` 共 44 個 tests 通過；golden preview 涵蓋 CREATE、UNCHANGED、UPDATE、CONFLICT、REJECT。`kgnote.dry-run.v1` 比較 normalized candidates 與 caller-supplied canonical snapshot，fail-closed 驗證 snapshot、typed IDs、schema 與 projected references；只允許 Concept evidence provenance 的純新增 update，保留既有人工 Concept/Evidence review state，移除或其他同 ID 差異均為 conflict。輸入/list 次序不影響結果，result copy-safe，且未讀寫 vault、未 merge/apply、未接網路或模型。Snapshot 目前必須由 caller 提供完整 Source/reference records；filesystem adapter、Markdown render、approval 與 idempotent apply/read-back 留給後續 Issue。 |
| 2026-09-07 | Phase 1 canonical-store adapter、approved apply 與 read-back | 完成 | `scripts/run_tests.sh` 共 52 個 tests 通過；golden integration 在 disposable store 完成 read → normalize → dry-run → exact SHA-256 approval → 9 CREATE／1 UPDATE → read-back，第二輪全為 UNCHANGED 且零寫入。`kgnote.canonical-store.v1` 只讀 explicit root 的五個 canonical directories，Phase 0 人工 fixture 可 read-back 20 筆；拒絕 malformed YAML/front matter、unsafe ID/path、symlink、stale precondition、既存 create target、blocking/forged plan 與錯誤 approval。UPDATE 保留人工 review state 與 Markdown body，建立 recoverable backup；模擬 mid-write 與 read-back mismatch 均 rollback canonical files。未對真實 vault 或 Phase 0 fixture apply；delete/rename/merge、並行 writer、真實資料導入與視覺驗收仍不在本切片。 |
| 2026-09-07 | Phase 1 consent-gated extraction run 與 local ledger | 完成 | `scripts/run_tests.sh` 共 61 個 tests 通過；golden fake-transport flow 完成 deterministic preview → destination/content-bound consent → 單次 transport → offline schema validation → restrictive immutable ledger，exact replay 為零 transport calls。涵蓋 redaction version/source immutability、malformed/schema-invalid/non-UTF-8 response、timeout/auth/rate-limit/provider/transport errors、缺 usage、ledger failure、run-ID conflict、unsafe path/symlink、transport metadata mismatch 與 repr redaction；accepted/rejected/error raw bytes 與 hashes 均留在 explicit local ledger。未選定真實 provider、未讀 secrets、未連網或產生費用；自動 PII 判斷、retry/streaming/batch 與 live smoke test 不在本切片。 |
| 2026-09-07 | Phase 1 Gemini real-provider transport | 完成（mock-verified） | `scripts/run_tests.sh` 共 67 個 tests 通過；ADR 依 2026-09-07 官方文件選定 `google-gemini` / stable `gemini-3.7-flash` 的非串流 REST `generateContent`。Transport 僅接受 caller 注入 key，固定一 request、零 retry、8,192 output-token cap，使用 provider structured JSON schema，保留 exact candidate text、response ID 與實際 usage，並安全映射 auth/rate-limit/timeout/provider/network failures。Synthetic E2E 完成 preview/consent → mocked provider → offline validation → immutable ledger；未讀 env/file/keychain/vault，未真實連網或產生費用。Paid-project、region、retention/ZDR 狀態與真實 schema adherence 尚未 live 驗證；首次 live smoke 仍需顯示 synthetic/redacted exact preview、destination、bytes/digest、最多一 request、成本上限與 ignored local ledger，再取得 fresh authorization。 |
| 2026-09-07 | Phase 2 synthetic offline small-batch dress rehearsal | 完成 | `scripts/run_tests.sh` 共 69 個 tests 通過；explicit synthetic Markdown + replay JSON 完成 import → offline validation → normalization → dry-run → digest approval → canonical apply → read-back。第一次建立 11 筆 canonical records 與 1 份 byte-identical raw source，第二次 11 筆全為 UNCHANGED、零寫入；Phase 0 fixture digest 不變，未讀 key/env、未連網或產生費用。桌面 Obsidian 開啟 repository 外的 `<local-validation-artifact>`，確認 1 Source、4 Concepts、2 Evidence、1 LearningEvent、3 typed Edges、1 raw source 共 12 節點形成連通圖；Concept → Evidence → Source → raw、LearningEvent 與 Edge 導覽均成功，類型分離，Counterfactual 保持 `soft_association`／`relation: null`／`confidence: unresolved`，未宣稱 understood，且 broken／ghost／ambiguous links、unresolved links 與重複 basename 均為零。Obsidian 自動建立的 `.obsidian/` 已移除，artifact 恢復 12 檔；截圖位於 repository 外的 `<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`。本切片不是實際私人教材導入。 |
| 2026-09-07 | Phase 2 one-note real-learning offline pilot（Issue #11） | 完成 | 使用者選定的一份 LLM Wiki Markdown 以人工審閱 replay 全離線導入 repository 外的 `<external-workspace>`；原檔 bytes/SHA-256 不變，未呼叫 provider/API/key。第一次 apply 產生 23 筆 canonical records 與 1 raw source；第二次 preview 23 筆全為 UNCHANGED，canonical/raw/總寫入皆為 0，read-back 仍為 23 筆，vault 仍為 24 檔且 tree SHA-256 前後同為 `685ac9caa9f8a2dd66d0b9ebc68aaf1d74510c4e72c8f8c8bc748a7c38a02f2d`。桌面 Obsidian 驗收確認 7 Concepts、4 Evidence、2 LearningEvents、9 typed Edges、1 Source、1 raw source 共 24 節點為單一連通圖且零 orphan；Concept → Evidence → Source → 660 行 raw conversation 導覽成功，global/local graph、summary、learning history 與 provenance 可回看。Learning state ↔ Knowledge graph 保持 `soft_association`／`relation: null`／`confidence: unresolved`；question 只用 `asked_about`，assistant explanation 只用 `explained`，均未宣稱 learner understood。broken／ghost／ambiguous／unresolved links 與重複 basename 均為零，未見可疑 merge；限制是長 SHA-ID 在 global graph 有輕度標籤重疊，但 24 節點規模仍可辨識。`.obsidian/` 已移除；截圖位於 `<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`。下一步以另一份小型真實樣本觀察長 ID 標籤、圖密度與 concept merge，再決定顯示名稱或 schema/prompt 調整。 |
| 2026-09-07 | Obsidian display-label decision（Issue #12） | 完成 | 71 個離線測試已通過，並以三個 repository 外 disposable vault 完成桌面 Obsidian 比較。Option 1（stable filename + human heading）與正式 Option 2（stable target + aliased link text）均維持 7 Concepts、4 Evidence、2 LearningEvents、9 Edges、1 Source、1 raw source共 24 節點，全圖連通、零 orphan，且 broken／ghost／ambiguous／unresolved links 均為零；兩者 global/local graph、note tab 與 breadcrumb 都依 filename 顯示完整 stable ID，不採 heading、front matter 或 link alias。Option 2 正文可讀地顯示 `Knowledge graph`、`Learning state`、`Evidence L4-L14`、`Question event` 等短標籤，點擊後仍精確導向 stable-ID note；backlink 來源標題仍用 filename，snippet 保留 target 並顯示 alias，Quick Switcher 可用 front matter alias 搜尋且以 alias 為主文字、stable path 為副文字。Option 3 的 4-note prototype 證實 human-readable filename 能讓 global/local graph、note title、breadcrumb 與 Quick Switcher 全部可讀，但 filename 不再等於 canonical ID，故只作非 canonical 對照、不套用正式 artifact。三方案的 front matter stable ID 與 provenance 未變，Option 1/2 的 LearningEvent／Concept 保持分離，Learning state ↔ Knowledge graph 仍為 `soft_association`／`relation: null`／`confidence: unresolved`。三個 artifact 的 `.obsidian/` 均已移除，正式 Option 2 恢復 24 檔。截圖位於 `<local-validation-artifact>`、`<local-validation-artifact>` 與 `<local-validation-artifact>`。 |
| 2026-09-08 | Phase 3 graph read-model contract（Issue #13） | 完成 | `kgnote.graph-read-model.v1` Draft 2020-12 schema、語意 validator、contract README 與 Phase 0 完整投影 fixture 已建立；7 個 viewer nodes 僅含 6 Concepts 與 1 LearningEvent，8 個 typed links 保留 canonical／learning／soft-association 分層，4 Evidence 與 1 Source 作非 canvas provenance support records。80 個離線測試通過；驗證 stable ID／label 分離、canonical snapshot digest、完整 record read-back、reference integrity、edge endpoint policy、`relation: null` + `confidence: unresolved`、deterministic ordering/facets、read-only validation、malformed input 與安全錯誤。read model 不含 raw Markdown body、絕對路徑、source URI/path、provider response、layout 或 UI clock；本切片不含 filesystem projector adapter、HTTP endpoint、filter execution 或 Web UI。 |
| 2026-09-08 | Phase 3 in-memory deterministic graph projector | 完成 | `kgnote.graph-projector.v1` 將 caller-owned canonical record snapshot 純記憶體投影成 Issue #13 read model；Phase 0 的 20 records 完整產生 7 nodes、8 links、4 Evidence、1 Source 並逐欄符合 golden。投影前沿用 canonical snapshot schema/reference validation，排序 records 與 set-like arrays，導出 facets 與 normalized snapshot digest；顯示 label 會清除 wiki-link 控制字元、截至 64 字、空值 fallback，碰撞時以 stable ID 衍生 token 區分。結果 frozen、每次讀取 model 都是新 JSON copy；malformed／duplicate／dangling snapshot 安全拒絕且不回顯內容。同步修正 read-model event/review enums 與既有 canonical contract 一致；87 個離線測試通過，且測試明確封鎖 filesystem/network 呼叫。此切片仍不含 vault reader 串接、HTTP、layout、filter execution、neighborhood 或 Web UI。 |
| 2026-09-08 | Phase 3 neighborhood/filter planning（Issue #15） | 完成 | 新增 `kgnote.graph-view-query.v1` 與 `kgnote.graph-view-plan.v1` Draft 2020-12 schemas、決策 README、Phase 0 1-hop golden 與純記憶體 planner。決策為 filters 先形成可走訪子圖、hop 導覽方向中立但輸出保留原 link 方向、focus 被 filter 排除時 fail closed、無 focus 選完整 filtered graph；isolated focus／零 links 是合法 plan。Evidence 由 selected nodes/links 收集，Source 再由 Evidence/selected LearningEvent 收集，不成為 canvas nodes。97 個離線測試通過，涵蓋 1/2/3-hop、node/edge/relation/space filters、unknown/excluded focus、stale digest、unavailable/unsorted filters、malformed query、determinism、copy safety、輸入不變與明確封鎖 filesystem/network I/O。尚未實作 canvas、layout、HTTP、search、UI state 或 canonical mutation。 |
| 2026-09-08 | Phase 3 read-only graph view application boundary（Issue #16） | 完成 | 新增 `kgnote.graph-view-application.v1` envelope 與 `load_graph_view(explicit_root, query=None)`，沿用 canonical store reader、projector 與 planner，將完整 snapshot 投影後只 materialize plan 選取的 nodes、links、Evidence、Sources；局部 LearningEvent 的 `concept_ids` 裁切至 selected Concepts，使輸出仍符合完整 read-model reference integrity。未提供 query 時產生 snapshot-bound 全圖 query；stale/malformed query fail closed。store/projector/planner 錯誤只回 stable component/code/contract path，不含 root、絕對路徑或原文。106 個離線測試通過，Phase 0 read-back 為 7 nodes／8 links／4 Evidence／1 Source，並涵蓋局部 provenance、isolated zero-link、dangling store reference、schema refs、determinism、copy safety 與 byte-for-byte 唯讀驗證；測試封鎖 writes、network/model、process/UI 與 clock。HTTP、canvas/layout、search、cache/watcher、authentication 與 canonical mutation 仍未實作。 |
| 2026-09-08 | Phase 3 responsive read-only Web graph canvas（Issue #17） | 完成 | 新增零 runtime dependency 的原生 ES modules + SVG canvas、鎖定 Node toolchain metadata、由 Issue #16 真實結果產生且由 Python read-back 鎖定的 fixture。stable-ID deterministic ellipse layout 呈現 6 Concepts、1 LearningEvent 與 8 typed links；Concept/LearningEvent 形狀分離，canonical/learning/soft-association 顏色與 dash 分離，soft association 保持 `relation: null`／`confidence: unresolved`。Web 6 tests 與 Python 106 tests 通過。實際以 Mac 1440×1000、iPad 1024×768、iPhone 390×844 完成 render 與互動驗收：Mac/iPad 顯示 `Full graph`（7 nodes／8 links），iPhone 顯示以 Confounder 為焦點的 `Local · 1 hop`（4 nodes／4 links）；三種尺寸均無 page-level horizontal overflow 或 node-label overlap。Concept 圓形與 LearningEvent 圓角矩形可辨，canonical／learning／unresolved links 分別為藍色／薄荷綠／琥珀虛線；pointer pan、wheel zoom、`+`／`−`／Reset 均可操作並還原 canvas。stable ID 僅在 native node tooltip 出現，畫面無 Save／Delete／Merge／Rename／Apply、editing、proficiency 或 understood 語意，console 無 error/warning。截圖位於 `<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`。 |
| 2026-09-08 | Phase 3 read-only node detail panel（Issue #18） | 完成 | 新增純記憶體 deterministic detail projector 與 responsive side panel／mobile bottom sheet。Concept 顯示 summary、status、spaces、direct + incident-link Evidence、Source metadata 與 LearningEvent history；LearningEvent 顯示 event type、context、occurred time、Concepts、Evidence 與 Sources。known confusion 僅接受明確 `confusion` event 或 `confused_with` learning edge，question／exposure／encountered／unresolved association 不會被提升成 confusion 或 understood。Evidence 與 Source references 斷裂時 fail closed，固定錯誤碼不回顯輸入；投影 deterministic、copy-safe 且不修改 read model。節點支援 click／Enter／Space，Escape／close 恢復原節點 focus；HTML/JS 不含 mutation controls。Web 13 tests 與 Python 106 tests 通過。實際以 Mac 1440×1000、iPad 1024×768 與 iPhone 390×844 完成視覺、互動、鍵盤與安全驗收：Confounder panel 顯示 summary、active status、causal-inference space、2 Evidence、1 Source、Question event learning history，Known confusion 明確為 `No explicitly evidenced confusion in this view.`；Question event 顯示 question type、context、`Time not recorded`、6 Concepts、4 Evidence 與 1 Source，未呈現 understood 或 confirmed confusion。7 個 graph nodes 皆可 Tab 聚焦；Enter／Space 開啟 panel，Escape／Close 關閉後焦點回到原節點。Mac/iPad side panel 與 full graph 可同時操作，無水平溢位或 node-label overlap；iPhone 顯示 bounded、可捲動 bottom sheet，關閉後 local 1-hop graph 可繼續操作。畫面未出現 stable ID、絕對路徑、raw conversation、mutation controls 或編輯欄位，console 無 error/warning。截圖位於 `<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`。 |
| 2026-09-08 | Phase 3 Web hop/facet controls（Issue #19） | 完成 | 新增純 JS deterministic UI-state → `kgnote.graph-view-query.v1` builder，以及只服務 `web/` 靜態檔與 `POST /api/graph-view` 的本機唯讀 adapter；adapter 直接呼叫既有 Issue #16 application boundary，瀏覽器不重寫 traversal，也無法直接取得 canonical fixture Markdown。控制包含 full/focus、1/2/3-hop、node kind、edge class、non-null relation 與 space；同組 OR、跨組 AND，filters-first 與 direction-neutral traversal 仍由 Issue #15 planner 決定。結果只 render materialized nodes/links/Evidence/Sources，切換 view 會關閉 stale detail；empty/rejected 使用安全訊息，desktop reset 為 full graph、iPhone reset 為 deterministic planner-backed 1-hop。Golden HTTP read-back 以 Correlation 1-hop 得到 4 nodes／5 links。第一次視覺驗收發現 LearningEvent-only materialization 將 `concept_ids` 裁為空陣列後與 read-model schema 衝突；已明確定義完整 projector event 仍須有 Concept，而 filter-materialized view 可用空陣列表示相關 Concept 不在本 view，並加入 application/HTTP regression 與安全 validation-error mapping。修正後 Web 18 tests、Python 110 tests 通過。重驗確認 LearningEvent-only 為 `Full filtered graph`、1 node／0 links，Question event panel 可開啟，Concepts 明確顯示 `No concepts in this view.`，4 Evidence 與 1 Source 均保留，無安全錯誤或 request traceback。Mac 1440×1000 回歸維持 full 7/8、Correlation 1-hop 4/5；iPhone 390×844 初始與 Reset 均 deterministic 回到 local 4/4，切至 Correlation 1-hop 為 4/5；fixture Markdown URL 回傳 404。iPad 1024×768 的 Focus、Hops、filter checkbox、Update view、Reset 均為原生 `tabIndex=0` controls，取得焦點時呈現清楚薄荷綠 focus-visible outline；本次 in-app browser 鍵盤注入只設定焦點、未觸發 native select 方向鍵或 Enter／Space 預設動作，依驗收指示記為控制工具限制，query 操作則以直接控制及既有測試確認。三尺寸均無水平溢位；畫面未出現 stable ID、絕對路徑、raw conversation、mutation controls 或編輯功能，browser console 零 error/warning。重驗截圖位於 `<local-validation-artifact>` 與 `<local-validation-artifact>`。 |
| 2026-09-08 | Phase 3 end-to-end read-only boundary（Issue #20） | 完成 | 收斂本機 server 為 explicit `web/` regular-file allow-root 與唯一 `POST /api/graph-view` application route；decoded parent traversal、null byte、symlink、directory、canonical/repository/schema/test/Git/env 路徑皆 fail closed，PUT/PATCH/DELETE/OPTIONS/TRACE/CONNECT 回 versioned safe 405。JSON content type、32 KiB 上限、content length、UTF-8/JSON 與 unexpected internal failures均映射固定、不回顯的錯誤 envelope；所有回應加 no-store、CSP、no-referrer、no-sniff、frame denial，並移除 Server/Date identification。Browser rejected query 現會關閉 detail、清空舊 canvas 並標示 `View unavailable`／`Graph unavailable`，不再讓 stale graph 看似成功。新增真實 ephemeral-loopback HTTP E2E matrix，在 write/delete/rename/apply/subprocess/clock 全部 mock-forbidden 下執行 full、1/2/3-hop、四組 filters、LearningEvent-only、stale/unknown/excluded/invalid queries、malformed UTF-8/JSON 與 oversized payload，canonical store 全路徑與 bytes 前後完全一致；另有 static/method/header/internal-error tests。Web 18 tests、Python 114 tests 通過；安全邊界與限制記錄於 `web/SECURITY.md`。實際以 Mac 1440×1000、iPad 1024×768、iPhone 390×844 完成最終 smoke：三尺寸的 pan、wheel/button zoom、canvas Reset、query Reset、Concept panel、LearningEvent-only 1/0 + panel、canonical filtered view 與 isolated 1/0 均正常；Mac/iPad Reset 回 full 7/8，iPhone deterministic 回 local 4/4，無水平溢位、node-label collision、editing、persisted drag/layout、proficiency 或 understood 暗示。rejected Correlation + LearningEvent-kind query 會關閉舊 panel、清空舊 graph 為 0/0，顯示 `View unavailable`／`Graph unavailable` 與固定安全訊息，不回顯 focus ID、query 或路徑；Reset 恢復 full 7/8。五個 repository/canonical/traversal URL 均回安全 404 且 body 不含路徑；PUT/PATCH/DELETE `/api/graph-view` 均回 405。首頁與 API 回應皆含 `Cache-Control: no-store`、CSP、`Referrer-Policy: no-referrer`、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`，且無 Server/Date header。畫面未出現 stable ID、絕對路徑或 raw Markdown；question/exposure/explanation/encountered 未提升為 understood，known confusion 維持 explicit-evidence-only。browser console 零 error/warning，rejected HTTP 僅為預期 Network non-success，4174 server 無 request traceback。已知限制維持 local-only、read-only，無 authentication、search、persistence 或 canonical mutation。截圖位於 `<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`、`<local-validation-artifact>`。 |
