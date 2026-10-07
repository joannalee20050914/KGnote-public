# KGnote 黃金驗收情境

> GENERATED FROM scenarios.json。以下是驗收規格，不是已綁定或已執行的產品測試。

同一情境可以覆蓋多個需求。工程測試與人工閱讀效果的 rubric 要分開；不以資料格式通過代替畫面語意驗收。

## SC-01 · 零筆記也能從閱讀進入任意活動

**Given：** 全新session，無NoteBlock且可無canonical graph。

**When：** 開啟來源、讀導讀、查看解說，再選继续閱讀或輸出。

**Then：** 所有主要路徑均可通行；不要求輸入目標、疑問、筆記或熟悉度。

**以下狀況必須判失敗：** 先完成筆記／任意mandatory input才開正文或Practice。

需求：KG-WF-01, KG-WF-02, KG-WF-03, KG-ING-04

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_learning_http.py", "selector": "LearningHttpTests.test_sc01_zero_note_catalog_read_and_practice_paths_have_no_note_gate"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-02 · 純浸泡與滑走不構成錯誤作答

**Given：** 有一張熟悉情境曝光卡。

**When：** 選輕鬆再看→讀卡→滑走→關閉。

**Then：** 可顯示答案；只留允許的呈現/曝光事件，無incorrect／submitted attempt。

**以下狀況必須判失敗：** 所謂Soak其實只是Practice改名，沒有不作答路徑。

需求：KG-WF-02, KG-SOAK-01, KG-SOAK-05, KG-SOAK-07, KG-PRAC-06

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_learning_http.py", "selector": "LearningHttpTests.test_sc02_sc18_soak_reveal_skip_is_separate_from_attempt_and_due"}, {"path": "tests/test_exposure_store.py", "selector": "ExposureStoreTests.test_sc02_append_only_exposure_is_not_attempt_or_retrieval_result"}, {"path": "web/tests/soak-workspace.test.js", "selector": "SC-02 Soak event carries observation identity without assessment fields"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-03 · 續學回到具體缺口，不重啟整章

**Given：** 曾問branch/worktree，留原問、解說、實際回答與暫緩Git internals。

**When：** 隔日新session選繼續Git。

**Then：** 帶回具体問題／source anchor／已做未做及選項；不需重述背景。

**以下狀況必須判失敗：** 只提供最近文件列表，或斷言用戶已理解前述答案。

需求：KG-WF-03, KG-MEM-01, KG-MEM-07, KG-MEM-08, KG-SOAK-07

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_resume_context.py", "selector": "ResumeContextTests.test_sc03_exact_context_is_append_only_idempotent_and_read_back"}, {"path": "tests/test_learning_http.py", "selector": "LearningHttpTests.test_sc03_exact_resume_context_round_trips_and_enriches_activity"}, {"path": "web/tests/continuity.test.js", "selector": "SC-03 Learn saves exact scope breadcrumb selection and unresolved question"}], "evidence_refs": ["docs/requirements/evidence/loop2-20260920.json"]}。

## SC-04 · 實務處理不被補课吞掉

**Given：** 目的為判斷服务是否可用，測試用唯讀紀錄全正常。

**When：** 使用操作導讀。

**Then：** 指出可停止，深挖是選項；不建構實機restart副作用。

**以下狀況必須判失敗：** 為完成課程繼續建議不必要restart或強制學完整前置。

需求：KG-WF-04

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-05 · DMA已在正文說明時不自動重複

**Given：** 中央閱讀DMA完整段落。

**When：** 左側導航到DMA，不點閱讀求助。

**Then：** 焦點定位正文，無重複字典欄；主動求助才按需顯示不同視角。

**以下狀況必須判失敗：** Summary/Detailed/Source三處相同句且宣稱更深入。

需求：KG-WF-05, KG-STR-05, KG-CTX-06

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "web/tests/learn-workspace.test.js", "selector": "Learning Structure is recursive view navigation while Reading Assist stays explicit"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-06 · 概念與語法可以不同記憶策略

**Given：** 目標為知道如何查監聽服務，不要求默寫全部flags。

**When：** 設查詢語法為lookup，概念解釋為remember。

**Then：** lookup可回找、不進強制due；重要性按用途保存。

**以下狀況必須判失敗：** 兩者因同Concept被強迫共用記憶義務。

需求：KG-WF-06

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-07 · recursive hierarchy定位且保留上下文

**Given：** OS teaching structure有主題/子主題/項目，來源anchor可用。

**When：** 展開CPU執行管理→排程→Round Robin，再返回。

**Then：** 层级与breadcrumb正確，點擊到正文；不強制字典；同資料可大圖展示。

**以下狀況必須判失敗：** flat buckets被標成hierarchy，或動畫存在但定位不到原段。

需求：KG-STR-01, KG-STR-04, KG-STR-05, KG-STR-07

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "web/tests/learn-workspace.test.js", "selector": "Learning Structure is recursive view navigation while Reading Assist stays explicit"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_hierarchical_canvas_is_deterministic_three_level_and_typed"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json", "docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-08 · 組織語意不偷渡領域事實

**Given：** 一組排程方案與一組待釐清關係。

**When：** 顯示比較／替代／problem-solution標示。

**Then：** 區分編輯者比較意圖與已支持的事實關係；可追溯依據。

**以下狀況必須判失敗：** 同層被推成互斥，或把資料標view-only就免審查。

需求：KG-STR-02, KG-STR-03, KG-KNOW-07

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "web/tests/learn-workspace.test.js", "selector": "SC-08 structural semantics remain typed view data and do not become canonical propositions"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_hierarchical_canvas_is_deterministic_three_level_and_typed"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_procedural_canvas_expresses_order_without_canonical_causality"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json", "docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-09 · 重排與重疊membership不修改ontology

**Given：** CPU在兩個不同Lens且資料中無part_of Edge。

**When：** 重排、折疊、切Lens。

**Then：** Concept ID不變，canonical digest不變，来源未涵蓋內容有明示。

**以下狀況必須判失敗：** 自動生成part_of或添加未教的虛構章節。

需求：KG-STR-03, KG-STR-04

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_hierarchical_canvas_is_deterministic_three_level_and_typed"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_augmentation_adds_only_discoverability_markdown_and_reruns_byte_identically"}], "evidence_refs": ["docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-10 · 跨來源舊知與同名異義

**Given：** 兩來源共享同concept，一筆是已發生的user接觸；另有同名異義詞。

**When：** 在新文highlight該詞。

**Then：** 顯示真實舊例子與來源；可返回新文；歧義保持待選。

**以下狀況必須判失敗：** 只有庫内存在就寫你以前學會，或同名強行merge。

需求：KG-STR-06, KG-MEM-02, KG-PLAT-01

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_prior_encounters.py", "selector": "PriorEncounterTests.test_sc10_shared_concept_requires_real_other_unit_history"}, {"path": "web/tests/learn-workspace.test.js", "selector": "SC-10 prior encounter rendering is event-backed and not inferred from Concept existence"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-11 · PID當句最低補充與非canonical術語

**Given：** overview原句有PID但無充分定義；已準備可信外補，term尚可無Concept ID。

**When：** highlight PID並求解。

**Then：** 出現当前所需短解說、對當句角色、來源与可深入；可保存問題；不强制建node。

**以下狀況必須判失敗：** 沒canonical concept就無法求助，或預設展開ps/namespace指令教學。

需求：KG-CTX-01, KG-CTX-02, KG-CTX-04

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "web/tests/learn-workspace.test.js", "selector": "Learning Structure is recursive view navigation while Reading Assist stays explicit"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-12 · context深度可變，深入可返回

**Given：** 同詞在overview與診斷文本中，兩者目的不同。

**When：** 分別求助，並從overview主動深入。

**Then：** 範圍按context不同且可自主深入；返回保留原位置，Concept不被写固定depth。

**以下狀況必須判失敗：** 四级label鎖住好奇心或補充反过来誤改原文。

需求：KG-CTX-03, KG-CTX-05, KG-KNOW-06

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "web/tests/learn-workspace.test.js", "selector": "SC-12 the same concept gets context-local depth without becoming a concept mastery label"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-13 · 多個不懂不演變成名詞雪崩

**Given：** 一段含多個使用者標记不懂的必要概念。

**When：** 請求協助繼續理解。

**Then：** 提供最小橋接或較易版本選項，停車其餘疑問，保留原任務。

**以下狀況必須判失敗：** 一次講完五篇百科或硬编码三詞锁課。

需求：KG-CTX-07, KG-CTX-09

驗證方法：rubric_and_manual；狀態：not_run；test binding：未綁定。

## SC-14 · 不從課程或曝光推斷能力

**Given：** 修過課的profile、只由AI說過的詞與一筆用戶明示不懂。

**When：** 產生Reading Assist或續學摘要。

**Then：** 用户澄清優先；無紀錄为unknown；不用智力/吞吐标签；曝光不等于理解。

**以下狀況必須判失敗：** 課名、頁面點擊或缺資料被轉成已懂/未學過斷言。

需求：KG-CTX-08, KG-MEM-02, KG-MEM-05, KG-MEM-06, KG-KNOW-08, KG-GRAPH-04

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-15 · 原始證據糾正AI後設摘要

**Given：** 原紀錄：四PASS後user仍嘗試restart且未成功；AI後續例子稱已獨立判斷不需restart。

**When：** 抽取學習事件／續學包。

**Then：** 保留实际查驗與嘗試，標記摘要不吻合；不宣稱獨立判斷或成功restart。

**以下狀況必須判失敗：** 只因AI寫了demonstrated就當成行為證據。

需求：KG-MEM-03, KG-MEM-06, KG-KNOW-01, KG-KNOW-08, KG-ING-03

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-16 · 具體混淆與後續更正

**Given：** user明說label像Git版本；後續有澄清或新的正確回答。

**When：** 查看history或短對比練習。

**Then：** 原混淆、日期、配對、修正可回查；推薦不帶強制增加負擔。

**以下狀況必須判失敗：** 只存最後綠燈或把共同出現的詞推成混淆。

需求：KG-MEM-04, KG-SRS-04, KG-GRAPH-04

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_reviewer_context.py", "selector": "ReviewerContextTest.test_confusion_first_prompt_offers_distinction_and_does_not_erase_history"}, {"path": "tests/test_review_store.py", "selector": "ReviewStoreTest.test_prompt_is_grounded_and_append_is_readable_and_idempotent"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-17 · 熟悉外型、提示、活動可各自變動

**Given：** 同target有熟悉句、不同措辭、另一安全例子。

**When：** 先曝光，再選強提示填空，再返回曝光或自由解釋。

**Then：** 可雙向切換；保存variant/context/support，不改Knowledge identity。

**以下狀況必須判失敗：** 固定逐關解鎖，或毫無變化重複同句。

需求：KG-SOAK-02, KG-SOAK-03, KG-SOAK-06

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "web/tests/soak-workspace.test.js", "selector": "SC-17 support fading is a deterministic representation progression, not one permanent prompt"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-18 · 間斷使用無債務

**Given：** 累積多個due item且用戶幾天未使用。

**When：** 今天只看一則或選跳過。

**Then：** 可結束且無責備／罰分／強制清庫；仍能日後回找。

**以下狀況必須判失敗：** 連續天數處罰、欠卡遮罩或今天必須還完。

需求：KG-SOAK-04, KG-SRS-04

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_learning_http.py", "selector": "LearningHttpTests.test_sc02_sc18_soak_reveal_skip_is_separate_from_attempt_and_due"}, {"path": "web/tests/soak-workspace.test.js", "selector": "SC-18 Soak page states no debt and never submits an Attempt"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-19 · 獨立Attempt與合法支援模式

**Given：** Learn曾顯示答案，之後明確選無輔助Practice。

**When：** 載入、reload、切焦點、用hint、提交或取消。

**Then：** 無意外UI/ARIA/hidden DOM答案；主動揭露另記；prompt不受瀏覽替換；取消非錯。

**以下狀況必須判失敗：** 把曾看過教材視為作弊，或正常活動答案曝光仍標unassisted。

需求：KG-SOAK-05, KG-PRAC-02, KG-PRAC-06

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "web/tests/practice-workspace.test.js", "selector": "isolated Practice document contains no hidden Reader, graph, selection summary, answer, or source excerpt"}, {"path": "tests/test_practice_http.py", "selector": "PracticeHttpTests.test_safe_items_submit_reveal_retry_semantics_and_reload_readback"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json"]}。

## SC-20 · 自由解釋、有用回饋与追加保存

**Given：** reviewed rubric與同義正確／部分／錯誤回答樣例。

**When：** 提交→對照→自評→更正→重試。

**Then：** 未評估是unassessed；有來源的feedback另追加；原回答保留；新Attempt。

**以下狀況必須判失敗：** 任意回答一律insufficient或exact-match錯誤；只保留最後一次。

需求：KG-PRAC-01, KG-PRAC-03, KG-PRAC-04, KG-PRAC-05, KG-PRAC-08

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_attempt_store.py", "selector": "AttemptStoreTests.test_retry_requires_and_preserves_a_new_attempt_identity"}, {"path": "web/tests/practice-workspace.test.js", "selector": "Attempt starts with stable client identity and records hints, raw response, exposure, and refs"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-21 · 來源錯誤與題目失效隔離

**Given：** 原文有爭議claim且已有舊due與attempt。

**When：** 新增erratum／撤回教學readiness。

**Then：** raw hash不變；Reader正常、警告可見；新出題及舊due阻擋；歷史保留。

**以下狀況必須判失敗：** 警告不影響planner或修改原文掩蓋錯誤。

需求：KG-CTX-04, KG-KNOW-03, KG-KNOW-04, KG-ING-01, KG-ING-04

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-22 · 持久化重送與衝突

**Given：** 已建立attempt／note草稿。

**When：** 模擬寫入成功回應丟失、同ID重送、同ID改回答與stale revision。

**Then：** 不重複提交、不靜默覆寫；明確保存狀態與可復原文字。

**以下狀況必須判失敗：** server timestamp創新ID、錯誤卻顯示保存成功。

需求：KG-PRAC-07, KG-PLAT-06

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_attempt_store.py", "selector": "AttemptStoreTests.test_concurrent_first_write_preserves_one_submitted_payload"}, {"path": "tests/test_learning_note_store.py", "selector": "LearningNoteStoreTests.test_concurrent_writers_with_one_etag_produce_one_save_and_one_conflict"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-23 · due與attempt不同、排程可重放

**Given：** 固定target/revision與注入clock。

**When：** 到期、snooze、skip、啟動活動、提交。

**Then：** 到期/延期不建立attempt；間隔起算清楚，可重播相同next due。

**以下狀況必須判失敗：** 到期自造學習紀錄或算法不能解釋時間基準。

需求：KG-SRS-01, KG-SRS-02

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-24 · 自然曝光不冒充retrieval

**Given：** 一份log只含POST；另一筆是user在新情境正確解釋POST。

**When：** 套用去重／排程政策。

**Then：** 前者只能記來源出現/曝光；後者可形成特定task的回答證據；兩種影響可查。

**以下狀況必須判失敗：** 兩者都直接當correct recall而取消必要檢核。

需求：KG-SRS-03

驗證方法：automated_and_manual；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_exposure_store.py", "selector": "ExposureStoreTests.test_natural_exposure_kinds_remain_typed_without_correctness"}, {"path": "tests/test_feedback_scheduling.py", "selector": "FeedbackSchedulingTests.test_sc24_natural_exposure_is_visible_to_scheduler_without_advancing_or_scoring_due"}], "evidence_refs": ["docs/requirements/evidence/loop1-20260920.json", "docs/requirements/evidence/loop3-20260920.json"]}。

## SC-25 · 實驗與完成狀態的界線

**Given：** UI可用，只有N=1/自動smoke；無7/21天資料。

**When：** 輸出完成報告與comparison protocol。

**Then：** 列測試類型、內容/時間/順序，baseline為實際偏好；未驗證效果不推論。

**以下狀況必須判失敗：** 宣稱全部學習有效或以不交筆記算理解0分。

需求：KG-SRS-05, KG-VAL-01, KG-VAL-02, KG-VAL-03

驗證方法：review_and_manual；狀態：not_run；test binding：未綁定。

## SC-26 · 模糊聯想可保存而不污染facts

**Given：** 創意類比有原話但沒有精確ontology relation。

**When：** 保存、回找、查看Knowledge Graph。

**Then：** 可保存soft link／association，原話可查；不強迫標fact或label。

**以下狀況必須判失敗：** 必須填精確relation才能保存或renderer自動canonical/high。

需求：KG-KNOW-01, KG-KNOW-02

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-27 · 多端閱讀與可存取操作

**Given：** 同單元於桌面／1024×768與窄屏。

**When：** 讀、展開hierarchy、選詞求助、關閉panel、開始Practice。

**Then：** 主要文字可讀、focus返回、無全頁横向溢位；實體device未測有標記。

**以下狀況必須判失敗：** 以viewport測試冒充真iPad；小字樹遮住正文。

需求：KG-STR-07, KG-PLAT-02

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-28 · Evidence多向解析

**Given：** 一Evidence對0/1/2個Claim的fixtures。

**When：** 選Evidence，並反轉claim列表順序。

**Then：** Evidence可作焦點，多個候選完整且不因排序換選取。

**以下狀況必須判失敗：** find取第一項或沒有claim就拒讀Evidence。

需求：KG-KNOW-05, KG-ING-01

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-29 · 有範圍的Graph而非全量複本

**Given：** OS多topic與跨topic Edge，含一爭議關係。

**When：** 開目前Lens／concept ego並按需展開。

**Then：** 群組、scope、方向、hidden count與爭議皆可辨；圖與Reader不必等集合。

**以下狀況必須判失敗：** 無邊界全量圖或為连通捏造Edge。

需求：KG-KNOW-06, KG-KNOW-07, KG-GRAPH-01, KG-GRAPH-02, KG-GRAPH-03

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-30 · 故障、回退與資料保留

**Given：** 既有來源/筆記/attempt與單個損毀派生圖。

**When：** 關閉feature flag、restart server或故障view。

**Then：** 來源與安全紀錄仍可讀；新舊history不刪；未知格式說明而非亂讀。

**以下狀況必須判失敗：** Graph錯誤拖垮全Reader或回退刪新紀錄。

需求：KG-GRAPH-03, KG-PLAT-06, KG-PLAT-07

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_learning_catalog.py", "selector": "LearningCatalogTests.test_structure_and_context_gloss_projection_failures_do_not_block_source_reader"}, {"path": "tests/test_durability_scale.py", "selector": "DurabilityScaleTests.test_large_append_only_history_round_trips_without_identity_loss"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_injected_native_write_failure_rolls_back_and_rerun_recovers"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json", "docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-31 · 資料驅動多單元與輸入邊界

**Given：** OS、BitePacer與第三份安全小資料。

**When：** 用同一renderer載入，再模擬選定單篇來源匯入。

**Then：** 無OS硬碼；來源schema/身份一致；fixture支援與live導入分開驗收。

**以下狀況必須判失敗：** 複製三份JS或假稱支持任意材料。

需求：KG-ING-02, KG-ING-03, KG-PLAT-01

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_learning_catalog.py", "selector": "LearningCatalogTests.test_three_units_load_with_structure_assist_and_three_or_more_activity_types"}, {"path": "web/tests/learn-workspace.test.js", "selector": "SC-31 a third synthetic unit uses the same workspace renderer without unit-name branches"}], "evidence_refs": ["docs/requirements/evidence/loop3-20260920.json"]}。

## SC-32 · 未授權外送與AI透明fallback

**Given：** 無live API授权，source內含要求忽略規範的文字。

**When：** 閱讀解說／要求feedback。

**Then：** 離線模式明示；transport零呼叫；source指令不成執行規範。

**以下狀況必須判失敗：** 外送私人對話、讀key或把預製內容宣稱live模型結果。

需求：KG-PLAT-03, KG-PLAT-05

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-33 · optional/deferred不是刪掉

**Given：** 有語音、跨平台、模型與浸泡候選，但本轮milestone較小。

**When：** 縮scope或結案。

**Then：** 台帳保留ID、理由、重啟條件；回報局部完成與剩餘能力。

**以下狀況必須判失敗：** 刪除需求後用較小分母宣稱100%。

需求：KG-PLAT-04, KG-GOV-02, KG-GOV-07

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-34 · dirty tree與資料擁有權

**Given：** repo已有混合未提交變更與他人檔案。

**When：** 規劃/實作可逆切片。

**Then：** 先記錄起點，只改任務檔，commit只含可辨識變更，無reset/clean。

**以下狀況必須判失敗：** 為使working tree乾淨而清除／混合提交。

需求：KG-PLAT-07

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-35 · 需求追溯與驗證證據

**Given：** 新的feature task與版本化台帳。

**When：** 生成context packet→綁implementation/tests→回報完成。

**Then：** 有source、must/not、scenario、base revision、run evidence；缺少不可verified。

**以下狀況必須判失敗：** 寫test路徑就代表已跑，或checker PASS被描述為產品PASS。

需求：KG-VAL-01, KG-GOV-01, KG-GOV-04, KG-GOV-05, KG-GOV-06, KG-GOV-07

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-36 · 衝突與弱化變更不可靜默

**Given：** baseline含Soak不作答與Notes optional。

**When：** 候選patch刪掉Soak、將optional改must或把驗收刪掉。

**Then：** delta可見，保留舊ID並提供明確decision；AI不能自行捏造user批准。

**以下狀況必須判失敗：** 同一agent降規格+改測試後以全綠結案。

需求：KG-GOV-02, KG-GOV-03, KG-GOV-06

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-37 · 查驗、操作、恢復與原因不被混寫

**Given：** 紀錄包含唯讀PASS查驗、拼字錯誤而未執行的restart、稍後服務可用，以及使用者提出網路恢復假說。

**When：** 建立學習事件或精確續學時間線。

**Then：** 分列觀察、未成功操作、恢復狀態、假說與後續依據；不宣稱查詢或使用者成功restart造成恢復。

**以下狀況必須判失敗：** AI後設摘要或時間相鄰被當成成功修復的行為與因果證據。

需求：KG-MEM-09

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-38 · Obsidian-first 普通文章入口不要求學系統

**Given：** LLM Wiki已有一篇可讀Markdown，KGnote plugin可啟用或停用。

**When：** 使用者從Obsidian打開文章並開始閱讀，尚未主動選取KGnote功能。

**Then：** 主體仍是普通文章、links／backlinks／preview可沿用；不先顯示dashboard、內部record術語或要求任何輸入，plugin停用後Markdown仍可讀。

**以下狀況必須判失敗：** 必須先理解Claim／Evidence／Lens／Attempt、切換多欄頁或離開Obsidian才能開始讀原文。

需求：KG-PLAT-08, KG-UI-01

驗證方法：automated_and_manual；狀態：manual_fail；test binding：{"test_refs": [{"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_materialize_reopen_links_source_bytes_and_idempotent_rerun"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "PersonalAlphaPresentationTests.test_start_here_is_a_learning_entry_not_a_debug_dashboard"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "PersonalAlphaPresentationTests.test_evidence_is_reachable_but_not_a_mandatory_learning_path_step"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-human-feedback-20260923.json", "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json"]}。

## SC-39 · 教材結構圖與熟悉後的知識漫遊圖不混用

**Given：** 同一領域有tree-like文章結構、typed組織關係與部分尚未熟悉Concept。

**When：** 使用者從結構圖定位文章，之後開啟Knowledge Roaming。

**Then：** 結構圖從一開始可見、edge詳述可查且節點回Markdown anchor；漫遊圖只投影eligible Concept並沿用相同identity。

**以下狀況必須判失敗：** 把tree membership寫成canonical knowledge Edge，或因文章／Concept曾出現就把全部未知節點放入漫遊圖。

需求：KG-STR-08, KG-GRAPH-05, KG-KNOW-09

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_hierarchical_canvas_is_deterministic_three_level_and_typed"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_semantic_validator_reads_back_all_three_shapes"}], "evidence_refs": ["docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-40 · 原句便利貼可收合展開且不靜默改原文

**Given：** 使用者在一篇versioned Markdown中反白目前不懂、尚無獨立文章的詞。

**When：** 建立一句最低必要解釋並在閱讀時展開、收合、關閉重開，或取消／遇到stale anchor。

**Then：** 解釋留在原句context、可編輯並有provenance；source snapshot不變，正式寫入可編輯文章必須另有preview與新revision。

**以下狀況必須判失敗：** 每個便利貼都自動建Concept、取消仍留垃圾節點、stale anchor猜位置，或AI解釋無preview覆寫文章。

需求：KG-CTX-10, KG-KNOW-09

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-41 · 練習由有選項cloze逐步撤除支援

**Given：** 一個新Target有reviewed原文span，使用者對具體詞彙尚不熟。

**When：** 先做原文挖空＋選項，再依可說明的事件或主動選擇進入提示與無提示回想。

**Then：** 各活動共享Target／Source identity但分別記錄support、prompt revision、答案可見與Attempt；後期問法貼近原文，退階／保留提示／不知道均合法。

**以下狀況必須判失敗：** 一開始只給自由回想、把選項題冒充無提示提取，或為測驗刻意換成無關的陌生問法。

需求：KG-PRAC-09, KG-KNOW-09

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-42 · 問題先找來源再升級AI且擴充可審核

**Given：** 閱讀或練習中提出一個可能由原文回答、也可能需要跨概念比較的問題。

**When：** 系統先檢索目前文章與直接連結來源，再判斷最低必要深度與是否升級AI。

**Then：** 原文足夠時回最接近anchor且不呼叫live模型；不足時明示升級理由、限制與provenance，擴充只有preview接受後才成為文章新revision或linked note。

**以下狀況必須判失敗：** 所有問題一律外送、AI自行判定並覆寫原文、偏題判斷不可申覆，或每次回答建立重複Concept。

需求：KG-AI-01, KG-KNOW-09

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-43 · 複習清單與結構圖狀態一致且漫遊有門檻

**Given：** 同一Target有可重放的排程、自然曝光、提示與無提示Attempt，並出現在教材結構圖。

**When：** 查看今日清單、結構圖顏色並決定是否進入Knowledge Roaming。

**Then：** 兩種投影顯示相同可解釋狀態；顏色有文字替代；七天規則標為使用者選定方案；漫遊資格依行為evidence與override而非曝光或假百分比。

**以下狀況必須判失敗：** 清單與圖矛盾、snooze建立Attempt、只閱讀就標成已回想／可漫遊，或把固定天數宣稱個人最佳遺忘曲線。

需求：KG-STR-08, KG-SRS-06, KG-GRAPH-05, KG-KNOW-09

驗證方法：automated_and_manual；狀態：not_run；test binding：未綁定。

## SC-44 · 單一命令從選定 Markdown 建立 workspace

**Given：** 使用者有一份明示選定、UTF-8 且非空的 Markdown 與一個空白或既有的 allowlisted 目的地。

**When：** 依文件執行唯一 daily-use workflow，不編輯 JSON、Python、fixture、schema、ID，也不逐一呼叫 pipeline internals。

**Then：** 命令先做完整 validation／preview，再一次安全 materialize 並回報可開啟的 entry note、來源 digest、created／updated／unchanged 摘要與下一步；失敗訊息可操作且不聲稱成功。

**以下狀況必須判失敗：** 需要手寫 extraction response、複製生成 ID、詢問 Codex 下一條命令，或錯誤只留下 stack trace／半完成成功訊息。

需求：KG-ALPHA-01

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_personal_alpha_analysis.py", "selector": "PersonalAlphaAnalysisTests.test_hierarchical_preview_is_deterministic_zero_write_and_source_grounded"}, {"path": "tests/test_personal_alpha_analysis.py", "selector": "PersonalAlphaAnalysisTests.test_malformed_sources_fail_with_actionable_codes_and_no_destination"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_one_command_materializes_reports_entry_and_reruns_unchanged"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_same_daily_command_handles_three_distinct_sources_and_reopens_cleanly"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_input_and_managed_file_errors_are_actionable_without_traceback"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-pa1-20260922.json", "docs/requirements/evidence/personal-alpha-pa3-20260922.json", "docs/requirements/evidence/personal-alpha-pa4-20260922.json", "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json"]}。

## SC-45 · Obsidian entry note 回答學習與 provenance 問題

**Given：** 一份含標題層級、概念敘述、關係線索與部分不確定內容的新 Markdown 已完成 materialization。

**When：** 使用者在 Obsidian 從生成的 entry note 閱讀並沿普通 wikilink／heading anchor 導覽。

**Then：** 可找到材料概要、主要主題、重要概念、可支持的關係、每項來源 Evidence 與待確認清單；immutable source 可逐 byte 回讀，內部 record 不成為必經入口。

**以下狀況必須判失敗：** 只能看到 canonical 檔名／enum／平面圖、關係沒有來源理由、派生摘要冒充原文，或 plugin／Web UI 不在時內容不可讀。

需求：KG-ALPHA-02

驗證方法：automated_and_manual；狀態：manual_fail；test binding：{"test_refs": [{"path": "tests/test_personal_alpha_analysis.py", "selector": "PersonalAlphaAnalysisTests.test_three_materially_different_markdown_shapes_share_one_contract"}, {"path": "tests/test_personal_alpha_analysis.py", "selector": "PersonalAlphaAnalysisTests.test_every_concept_and_relation_resolves_to_exact_source_evidence"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_materialize_reopen_links_source_bytes_and_idempotent_rerun"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_all_three_markdown_shapes_materialize_and_reopen_without_source_links_leaking"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_same_daily_command_handles_three_distinct_sources_and_reopens_cleanly"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "PersonalAlphaPresentationTests.test_start_here_is_a_learning_entry_not_a_debug_dashboard"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "PersonalAlphaPresentationTests.test_port_teaches_source_scoped_meaning_before_audit_details"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "PersonalAlphaPresentationTests.test_relationships_lead_with_readable_propositions_and_plain_uncertainty"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-pa1-20260922.json", "docs/requirements/evidence/personal-alpha-pa2-20260922.json", "docs/requirements/evidence/personal-alpha-pa4-20260922.json", "docs/requirements/evidence/personal-alpha-human-feedback-20260923.json", "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json"]}。

## SC-46 · Personal Alpha 冪等重跑與交易式失敗回復

**Given：** 同一來源已成功 materialize，且測試可在 commit 前後的指定寫入點注入中斷或 I/O 失敗。

**When：** 先原樣重跑，再執行一個注入失敗的更新／建立流程並重新開啟 workspace。

**Then：** 原樣重跑不新增等價 Concept／Evidence／relation 或覆寫人工內容；失敗後仍只有先前完整版本或完全沒有新 workspace，下一次合法重跑可恢復。

**以下狀況必須判失敗：** 出現重複 canonical identity、部分新舊檔混合、人工檔案被靜默改寫、暫存檔被誤當正式內容，或需要 reset／手工 JSON 修復。

需求：KG-ALPHA-03

驗證方法：automated；狀態：automated_pass；test binding：{"test_refs": [{"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_materialize_reopen_links_source_bytes_and_idempotent_rerun"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_source_update_preserves_user_notes_and_removes_no_unmanaged_files"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_new_readable_concept_path_never_overwrites_user_owned_file"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_local_edit_to_generated_file_fails_closed_without_overwrite"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_injected_update_failure_rolls_back_to_previous_complete_workspace"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_injected_new_workspace_failure_leaves_no_partial_target"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_same_daily_command_handles_three_distinct_sources_and_reopens_cleanly"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-pa2-20260922.json", "docs/requirements/evidence/personal-alpha-pa4-20260922.json", "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json"]}。

## SC-47 · 三種 materially different 來源的 candidate verification

**Given：** 至少三份在領域、篇章形狀或關係表達上有明確差異的 Markdown fixture。

**When：** 每份都只經同一 documented daily-use workflow 建立、關閉後 read-back、原樣重跑，並執行完整 repository verification。

**Then：** 三份均保存 source bytes/provenance、產生 coherent Obsidian workspace、無重複 canonical record 且 verifier 綠燈；狀態只標 candidate_verified。

**以下狀況必須判失敗：** fixture 只是換名字的複本、任一來源需手改內部格式、只檢查檔案存在、full verifier 未綠，或把 automated evidence 寫成 product owner 已接受 usability。

需求：KG-ALPHA-04

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_personal_alpha_analysis.py", "selector": "PersonalAlphaAnalysisTests.test_three_materially_different_markdown_shapes_share_one_contract"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_all_three_markdown_shapes_materialize_and_reopen_without_source_links_leaking"}, {"path": "tests/test_personal_alpha_cli.py", "selector": "PersonalAlphaCliTests.test_same_daily_command_handles_three_distinct_sources_and_reopens_cleanly"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_injected_update_failure_rolls_back_to_previous_complete_workspace"}, {"path": "tests/test_personal_alpha_presentation.py", "selector": "LearnerProjectionTests.test_three_source_shapes_keep_distinct_navigation_semantics"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_semantic_validator_reads_back_all_three_shapes"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_manual_continuation_requires_complete_exact_heading_or_block_target"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_evidence_states_heading_jump_and_document_only_line_limit_honestly"}, {"path": "tests/test_personal_alpha_workspace.py", "selector": "PersonalAlphaWorkspaceTests.test_source_update_preserves_user_notes_and_removes_no_unmanaged_files"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-pa1-20260922.json", "docs/requirements/evidence/personal-alpha-pa2-20260922.json", "docs/requirements/evidence/personal-alpha-pa3-20260922.json", "docs/requirements/evidence/personal-alpha-pa4-20260922.json", "docs/requirements/evidence/personal-alpha-v3-projection-20260923.json", "docs/requirements/evidence/obsidian-native-v3-20260923.json"]}。

## SC-48 · Obsidian Personal Alpha 從進入教材到手動續讀重開的整合流程

**Given：** 一份已授權 fixture 經 documented daily workflow 產生 disposable local Obsidian workspace，且使用者未依賴 Codex 對話、未編輯 Python／JSON，也未安裝第三方 plugin。

**When：** 使用者以真正 vault root 開啟工作區，從 Start Here 閱讀 source/concepts/structure/relationships，按需核對 Evidence，留下 My Notes 與手動 Continue Here 的 note/section/next/question，關閉後重新開啟並沿入口返回記錄位置，選擇性開啟 Canvas。

**Then：** Markdown 本身完成連續可導航學習流程；Canvas 路徑以 vault root 解析並只提供可選增益；Reading view 第一眼是教材；Evidence 明示實際 locator 精度；regeneration 保留 user-owned bytes；工程、原生操作與尚待真人驗收的證據分層記錄。

**以下狀況必須判失敗：** validator 只在子目錄通過但真實 vault root 路徑錯誤、Start Here 找不到 Canvas/Continue Here、Canvas 成為必經、frontmatter 干擾主要閱讀、空模板或 recent file 被當成續讀完成、Evidence document link 被宣稱為精準段落定位、user-owned bytes 被覆寫，或 automated/read-back 結果提升任何 human gate。

需求：KG-ALPHA-05

驗證方法：automated_and_manual；狀態：automated_partial；test binding：{"test_refs": [{"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_augmentation_adds_only_discoverability_markdown_and_reruns_byte_identically"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_documented_native_command_reports_exact_vault_root_and_reruns_unchanged"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_semantic_validator_reads_back_all_three_shapes"}, {"path": "tests/test_obsidian_native_spike.py", "selector": "ObsidianNativeArtifactTests.test_integrated_trial_flow_reads_back_and_preserves_all_three_shapes"}], "evidence_refs": ["docs/requirements/evidence/personal-alpha-v3-partial-feedback-20260927.json", "docs/requirements/evidence/personal-alpha-rp-pa-1-20260927.json", "docs/requirements/evidence/personal-alpha-rp-pa-2-20260927.json", "docs/requirements/evidence/personal-alpha-rp-pa-3-20260927.json"]}。
