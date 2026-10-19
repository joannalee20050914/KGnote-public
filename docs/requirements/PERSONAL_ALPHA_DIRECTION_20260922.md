# 2026-09-22 使用者產品目標：Obsidian-first Personal Alpha

狀態：使用者明示產品與執行目標；工程驗收中。產品方向 ID 維持 `kgnote-obsidian-first-2026-09-22`。

來源：2026-09-22 Codex task 的 `/goal` 附件
`local-source-withheld`，
SHA-256 `81a2edc29963f3c0982072b1806401b496093c6b5cd5a198315a4cf7bdf983e0`，162 行。
本檔是決策化整理，不複製私人學習來源內容。

## 目標

把 KGnote 帶到可供 product owner 日常使用的 Obsidian-first Personal Alpha。使用者明示選定一份新的
Markdown 學習來源後，只需執行一個有文件的工作流，就能得到可在 Obsidian 直接閱讀、搜尋、
連結、關閉後重開的學習 workspace；不需手改 JSON、Python、fixture、schema、ID 或內部 record。

每份 workspace 至少要讓使用者實際回答：

- 這份材料在談什麼？
- 主要主題或章節是什麼？
- 哪些概念重要、彼此如何關聯？
- 概念或關係為何出現、支持原文在哪裡？
- 哪些內容仍不確定或需要人工確認？

原始來源 bytes 必須作 immutable evidence 保存；派生的結構、說明、Concept、relation 與 Evidence
保留 provenance。輸出優先使用普通 Markdown、wikilink、heading/block anchor、properties 與其他
Obsidian 原生能力，不為這個目標另建 Web 閱讀器、Wiki、file tree 或大型圖 UI。

## Personal Alpha 工程邊界

1. **單一日常入口。** 一個明顯、有文件的命令或同等簡單入口，負責 preview、建立／更新與最終摘要；錯誤訊息指出可採取的下一步。
2. **人類可讀輸出。** coherent learning entry point 先呈現來源摘要、結構、重要概念、關係、Evidence links 與待確認事項；不把使用者丟進 canonical record 資料夾或平面全圖。
3. **安全重跑。** 同一來源與同一版規則重跑不重複 canonical knowledge、不破壞人工筆記；輸入變更或目的地衝突必須 fail closed 或走明示 update preview。
4. **失敗安全。** interrupted／failed write 不留下半套 canonical 或 workspace state；apply 後做 read-back。
5. **泛用性。** 最終工程驗證使用至少三份內容與結構 materially different 的 Markdown，且全程不需手改 JSON／Python。
6. **證據分級。** automated candidate verification 不冒充真人 Obsidian usability acceptance；真人 gate 要另記錄 product owner 的閱讀與續用觀察。

## 與既有方向的關係

這個目標不撤回 `U-OBS-FIRST` 或 `U-ROADMAP-REINTEGRATION`，而是明示調整目前交付順序：

- 先完成「選定 Markdown → 可用 Obsidian learning workspace」的端到端 Personal Alpha；
- inline 便利貼、Resume、Soak、Practice、Due 與 Knowledge Roaming 保留在整體 roadmap，但不是此 Alpha 的完成前置；
- 原生 Canvas 或 plugin 只有在 coherent Markdown workspace 無法滿足此目標時才加入；
- 現有 Web prototype 只保留 regression／comparison 用途；
- live AI/API、第三方 plugin、正式私人 vault 批次修改與 destructive migration 都沒有在此授權。

## 驗證與停止點

工程 candidate 必須證明三種來源、source bytes/provenance、冪等重跑、無重複 canonical record、
失敗回復、Obsidian artifact read-back、單一工作流文件與完整 repository verification。之後停在真人
Obsidian usability gate，提供精確命令、建議先測來源、觀察清單與已通過的自動證據；只有真人回饋
可以提升 usability／release acceptance。
