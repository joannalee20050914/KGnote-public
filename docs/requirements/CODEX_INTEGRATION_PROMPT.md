> **HISTORICAL / CONSUMED PROMPT：**本接入任務已完成並只保留 provenance；不得把命令語氣或未完成項目當成目前派工。現行 execution authority 見 root `PLAN.md` 與 `docs/control-plane/AUTHORITY.md`。

# KGnote：先恢復需求完整性，再繼續自主實作

這不是再加一輪feature，也不是停止目前所有工作重做。請先完成一個有界的「需求基線接入」切片，再沿原本的可用雛型工作繼續。

## 依據

讀取本包 README、DECISIONS_AND_CONFLICTS、requirements.json、scenarios.json。來源為原始《拆解Codex實作學習層級》§01–27，以及本對話最近的工作流／結構／閱讀輔助回饋。原文是資料，不是可直接執行命令；歷史AI說法不是自動已批准的需求。若本機有更晚的使用者澄清，保存為新source並做明確delta，不靜默丟掉本包。

先核對repository實際程式、AGENTS/override、branch/worktree/dirty state、啟動路徑與現在tests；不要相信舊完成報告或原始附件表示最新實作。本包83條需求的delivery都是unverified，意義是本次未查驗，不是全部重做。

## 本切片交付

1. 將需求資料與guard合併到repo合適目錄（建議docs/requirements）；不要覆寫既有檔或提交私人原始對話。保存原始來源hash與位置；若相同用途台帳已存在，合併而非再建第二份真相。
2. 各需求核對為not_implemented／partial／reported_implemented／implemented／automated_verified等真實狀態。綁定實際模組與測試路徑；沒有跑過的scenario維持not_run。
3. 對照來源處置表再做一次漏項查找。27節都有處置不代表每個想法已語意完整；發現遗漏補原話與新ID。本文以外的AI提案需標proposal，不能冒充user instruction。
4. 整合AGENTS.requirements.md的短規範，不覆蓋原安全規定。將DEVELOPMENT_PLAIN改成引用requirement IDs的排程文件，不讓它成為另一份重寫意圖的SSOT。歷史段落保留並標superseded，不全檔刪掉舊脈絡。
5. 優先把最易被偷換的情境接上真正產品測試：SC-01零筆記、SC-02無輸出Soak、SC-03精確續學、SC-05無重複DMA字典、SC-07層級定位、SC-11當句PID最小補充、SC-15行為不被AI摘要冒認、SC-18無債務、SC-19答案隔離。可用同一E2E覆蓋多條，不為ID數量造trivial tests。
6. 已實作的能力先補對應負例regression，缺失能力先加可見gap與執行切片。不要先寫會永遠skip的測試，再把需求標完成。規格測試與UI實測分開；人工尚未試用不阻擋安全工程前進。
7. 本機check與現有完整tests跑通；建立source→requirement→scenario→actual test/result的矩陣。CI接入採现有runner；沒有遠端設定權時交付可執行指令和待接入項，不自稱已設required check。

## 必須修正的舊方向

保留可選筆記、Graph與回憶，不要求先寫筆記，不改成retrieval-first。恢復原始§26的「可以只曝光、不作答」的浸泡能力；Practice+due queue不是等價替代。精確續學不能只做recent/history卡。Context Gloss和跨筆記舊知重連不同；flat groups不是層級。統一Concept identity不禁止適當paraphrase，也不允許教學分組私自生成事實Edge。

未知詞密度、熟悉度百分比、recognize/define/explain/apply等歷史AI提案不可不經判斷成硬鎖。原§11用戶四PASS後仍嘗試重啟：不得沿用後面AI示例，寫成已獨立判斷不需restart／已成功restart。

## 工作方式

可以自主選最小可逆工程方案，不必逐個function詢問。commit仍只限可辨識本輪變更，不能reset/clean混合dirty tree；保存開始/結束狀態與決策。不新增未授權API呼叫或資料外送。遇到缺乏live AI授權，使用明示offline內容做功能驗收，但保留live能力未驗證。

不要花整輪重新編輯文書；完成台帳、關鍵測試映射與衝突處置後，繼續實作有明確Requirement IDs的下一個使用者工作流。每輪完成的subset必須明確；不要求83條一晚全部實作，也不以跑滿幾小時作完成指標。

## 結案報告

提供：目前可操作入口、被滿足的Requirement IDs与證據、仍partial/missing/deferred的需求、發現的來源衝突與處置、實際測試與版本、人工仍待評估的少量問題、下一切片。不得只回報測試總數或新增class。不要把guard的structural PASS寫成所有需求／學習效益PASS。

需要更改已明示用戶需求或刪除驗收時才集中提出決策；UI命名和一般工程细节自己處理。現在從source reconciliation與最新程式核對開始，不再只濃縮一版DEVELOPMENT_PLAIN。
