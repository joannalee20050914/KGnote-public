# 2026-09-22 使用者產品方向修正：Obsidian-first learning layer

狀態：使用者明示方向，待逐切片工程驗收。來源是 2026-09-22 本 Codex task 中、在實際使用 熟悉材料 Web prototype 後提出的回饋；本檔是決策化整理，不是完整私人對話逐字匯出。

## 觸發 finding

目前 Web Learn UI 同時顯示原文、結構、Concept、Claim、Evidence、Local Graph 與續學控制，對簡單材料造成額外操作與理解負擔。產品若要求使用者先學會 KGnote 的內部模型，便偏離「學習新事物」的目的。

## 已明示的方向

1. **Obsidian-first。** Markdown／LLM Wiki、分類、內部連結、backlinks 與文章閱讀優先留在 Obsidian；只有 Obsidian 原生或跨平台外掛無法合理完成的能力，才另建 KGnote 介面或 sidecar。
2. **原始文字先出現。** 日常入口是一篇普通可讀的 Markdown 文章，不是 KGnote dashboard、Graph 或一組內部資料模型面板。
3. **兩種圖分開。** 教材結構圖是領域最上層的樹狀導航，可從一開始查看；知識漫遊圖用於熟悉後的聯想探索，不得因曾曝光就提前納入節點。
4. **教材結構圖要有真正的圖。** 結構像 tree，Edge 可表達子概念、平行、對立等組織關係；hover／選取可看完整關係，點節點可回 LLM Wiki 文章。
5. **便利貼是局部認知支援。** 反白目前不懂、但不值得另建完整文章的詞，在原句位置保存一句最低必要解釋；可一鍵於閱讀畫面展開為括號註解，再收合回原文。
6. **練習逐步撤除支援。** 初期先有原文挖空＋選項或選擇題，再到提示回想與空白回想；自由回想不再是陌生內容的第一個預設活動。後期題目盡量貼近原文表述，不為測驗刻意大幅改寫問題。
7. **問題先找來源，再視需要用 AI。** 原文能釐清的問題先檢索並定位最接近段落；跨層次、遠距概念比較或來源不足時才使用較強 AI。AI 也要判斷當前最小必要深度、是否偏題，以及問題是否值得擴充正式文章。
8. **互動可累積回 LLM Wiki，但不得靜默改原文。** 有價值的解說、比較與問題可經明示接受後形成文章新 revision 或連結筆記；來源 snapshot、AI proposal、使用者接受與正式內容必須可區分。
9. **複習不只是一列任務。** 到期清單保留；教材結構圖同時以顏色顯示可解釋的複習階段，讓使用者先看整體結構再進入知識點。七天規則先作使用者選定的排程，不宣稱普遍最佳遺忘曲線。
10. **一份 Concept identity 貫穿各階段。** 文章 mention、便利貼、題目、due、教材結構圖與知識漫遊節點引用同一概念；不得因不同 UI 各建一個同義節點。
11. **語意與操作要簡單。** 日常畫面不要求理解 Source／Evidence／Claim／Lens／Attempt 等內部術語；這些可留在資料與稽核層，只在處理衝突、來源或進階檢查時展開。

## 後續明示裁決：將最初發想補回現行 roadmap

使用者在檢核原始《拆解Codex實作學習層級》與現行 `DEVELOPMENT_PLAIN.md` 後明示：保留上述合理且必要的 Obsidian-first 修正；其餘最初發想應整合回現行 roadmap，而不是只留在 requirements 台帳或歷史文件。具體處置：

1. **Soak 獨立交付。** 可以完整顯示答案、舊例子與局部關係，只曝光、不作答、直接滑走或暫停；不建立錯誤 Attempt，也不以 Practice／Due Queue 代替。
2. **精確續學進入主線。** 保存最後問題、使用者實際回答、未釐清處、confusion、文章 anchor 與暫緩支線；recent/history 不足以替代。
3. **真實工作事件可回流。** 明示選定的對話、Markdown 或操作紀錄可形成有 speaker／tool／action attribution 的 learning-event 候選；不掃整庫、不把 AI 說過冒認為使用者理解。
4. **模糊關係不增加人工負擔。** 關係可暫存為 related／unresolved；使用者不必逐線命名或審完整 ontology 才能繼續學。
5. **無債務是產品行為。** 答錯、不知道、跳過、數日不使用、今天零活動或暫停 Space，不產生罰分、欠卡壓力或強制補完。
6. **多 Space 使用同一 engine。** 不同學科可有自己的導航與 scope；可信 Concept 可跨 Space 重連，同名異義不強併，不為每個主題另造 App。
7. **實作軌與理解軌並行。** 真實任務可先安全完成，當下不展開的學習支線可保存後精確續接，不因陌生詞密度把短操作變成長篇前置課。

這些不是新增第二份 requirement；分別引用既有 `KG-SOAK-*`、`KG-MEM-*`、`KG-ING-*`、`KG-KNOW-*`、`KG-WF-04` 與 `KG-PLAT-01`。本次改的是 roadmap 的可見排程與能力邊界。

## 私人來源版本邊界

本方向曾與兩個格式不同、但屬同一來源 lineage 的私人匯出版本核對。公開 repository 不保留其名稱、hash、行號、逐字摘錄或本機位置。B01–B27 等 stable source-role IDs 只維持需求追溯；公開的規範內容以 requirements、scenarios 與本決策記錄為準。原始定位與 byte identity 僅保存在經驗證的離線復原備份，不會在公開 history 中重新錨定。

## 不能由本次方向偷渡的結論

- Obsidian-first 不代表刪除 KG、Evidence、Attempt、Due 或既有 Web 工程；它改變的是主要承載介面與進場順序。
- 教材結構圖從一開始可見，不代表知識漫遊圖也可從一開始顯示全部節點。
- 「熟悉後可漫遊」不等於建立全域 mastery 百分比，也不允許用閱讀次數單獨判定熟悉。
- 七天複習是可解釋的產品排程選擇，不是個人記憶曲線已被量測。
- AI 判斷深度與價值是可申覆的建議；AI 不得自行把補充升格為原文或 canonical fact。
- 使用社群外掛前仍需驗證維護狀態、資料格式、Mac／iPad／iPhone 支援與離線／外送邊界；「有外掛」不等於已滿足需求。

## 待確認但不阻塞第一切片

- 便利貼按鈕的用語與展開動畫。
- 熟悉後進入知識漫遊的具體行為門檻與手動 override。
- 七天內的精確 milestone；在決定前不稱為科學最佳曲線。
- 教材結構圖首版使用原生 Canvas、現有社群外掛或最小 KGnote plugin renderer；先以可逆 spike 比較，不先綁死。

## Obsidian 官方能力依據（只支持平台邊界，不支持學習效果）

- Internal links／heading／block links／hover preview：https://obsidian.md/help/links
- Canvas、directed connection、label、color、JSON Canvas：https://obsidian.md/help/plugins/canvas
- Graph View 的 notes／links、group color、arrow 與 local depth：https://obsidian.md/help/plugins/graph
- Foldable callouts：https://obsidian.md/help/callouts
- Plugin editor API：https://docs.obsidian.md/Plugins/Editor/Editor
- Mobile plugin constraints：https://docs.obsidian.md/Plugins/Getting%20started/Mobile%20development
