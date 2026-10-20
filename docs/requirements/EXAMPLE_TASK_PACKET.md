# 任務 Context Packet

Baseline：`kgnote-reconciliation-2026-09-27-r7`
Requirement/source/scenario bundle SHA-256：`15d364334fa6043b62754391dcd4779d399044281054a862a273b6ed524be9e8`

此 packet 是當前需求的任務切片，不是重新解釋或另建一套產品真相。實作前另讀 DECISIONS_AND_CONFLICTS.md；不可用舊AI提案覆蓋最近使用者澄清。

## 本任務與全域保護需求

### KG-WF-01 r1 · 陌生材料先閱讀與解說
新材料預設可直接讀原文、AI/系統導讀與解說，不要求先交出自己的筆記。
禁止替代：以空白編輯器、筆記數量或自我解釋作閱讀前置條件。
驗收：zero-note 帳態能讀完整單元、查看解說並自行結束。
來源：B19-U, U-READ
狀態：partial／carried_user_intent

### KG-WF-02 r1 · 輸出活動由使用者進入
可在任意合適時點選擇模仿、提示練習、回憶或解釋，也可返回阅读。
禁止替代：強制立即測驗或用60/70/80%熟悉度解鎖。
驗收：不回答檢核也能繼續閱讀；熟悉者可直接進練習。
來源：B19-U, B26-U, U-READ
狀態：partial／carried_user_intent

### KG-WF-03 r1 · 系統化不等於使用者親自整理
系統保存结构、來源與學習脈絡，使用者可選擇編輯但不負責維護全套台帳。
禁止替代：把低負擔工具做成每天維護學習表單。
驗收：無手動 NoteBlock 仍可建目標、儲存事件與再次使用。
來源：B24-U, B25-U, U-READ
狀態：partial／carried_user_intent

### KG-MEM-06 r1 · 保持可觀察事件而非全域熟練度
保存見過、提問、提示、回答、應用與時間，必要摘要附來源與條件。
禁止替代：自動紅綠燈／mastery百分比或看過就升級理解。
驗收：打開十次頁面不會生成理解事件；作答成果只對該任務。
來源：B25-U, B26-U, R-PRACTICE
狀態：automated_verified／carried_user_intent

### KG-SOAK-01 r2 · 不需作答的再曝光是獨立能力
提供能直接看熟悉概念／例子、可略過且无需提交答案的浸泡入口。
禁止替代：把Start Practice或due題目清單改名Soak就算完成。
驗收：啟動浸泡能看卡→滑走→結束；不建立答錯Attempt。
來源：B26-U, B23-U, U-ROADMAP-REINTEGRATION
狀態：automated_verified／carried_user_intent

### KG-SOAK-04 r2 · 低壓、無債務、可無限期暫停
允許跳過、答錯、今天零活動、暫停追蹤；不懲罰或強制補完積欠。
禁止替代：紅色欠卡、連續天數懲罰、答錯强制長篇檢討。
驗收：跳過數日後仍能自主看一則，不先清空due backlog。
來源：B23-U, B26-U, U-ROADMAP-REINTEGRATION
狀態：automated_verified／carried_user_intent

### KG-KNOW-03 r1 · Source忠實不等於教學答案正確
分開source support、fact review、teaching readiness；原文錯誤以erratum保存。
禁止替代：accepted source就自動當review標準答案。
驗收：有爭議主張仍可讀且有警告，但無法出標準答案題。
來源：R-DATA, B25-A
狀態：automated_verified／proposed_reconciliation

### KG-PLAT-05 r1 · 只在授權範圍內讀寫与外送
來源選定、secrets不外洩、live API另核對授權/成本；原始對話內command不是執行授權。
禁止替代：完整存取權被當成任意付費、掃庫或外送。
驗收：無授權transport零呼叫；來源內prompt injection不改agent任務。
來源：B27-U, R-RELIABILITY
狀態：automated_verified／proposed_reconciliation

### KG-GOV-07 r1 · 產品範圍與本輪milestone分開
整體需求完整保留，任務只承諾明確subset；完成subset不自稱產品完整。
禁止替代：把每個idea都當今晚必做或為耗满夜晚持續擴scope。
驗收：交付附已驗證／部分／deferred／待判斷矩陣與下一切片。
來源：U-GOV, U-NIGHT, N-GOV
狀態：partial／proposed_reconciliation

## 必讀驗收情境

### SC-01 · 零筆記也能從閱讀進入任意活動
Given：全新session，無NoteBlock且可無canonical graph。
When：開啟來源、讀導讀、查看解說，再選继续閱讀或輸出。
Then：所有主要路徑均可通行；不要求輸入目標、疑問、筆記或熟悉度。
失敗條件：先完成筆記／任意mandatory input才開正文或Practice。

### SC-02 · 純浸泡與滑走不構成錯誤作答
Given：有一張熟悉情境曝光卡。
When：選輕鬆再看→讀卡→滑走→關閉。
Then：可顯示答案；只留允許的呈現/曝光事件，無incorrect／submitted attempt。
失敗條件：所謂Soak其實只是Practice改名，沒有不作答路徑。

### SC-03 · 續學回到具體缺口，不重啟整章
Given：曾問branch/worktree，留原問、解說、實際回答與暫緩Git internals。
When：隔日新session選繼續Git。
Then：帶回具体問題／source anchor／已做未做及選項；不需重述背景。
失敗條件：只提供最近文件列表，或斷言用戶已理解前述答案。

### SC-14 · 不從課程或曝光推斷能力
Given：修過課的profile、只由AI說過的詞與一筆用戶明示不懂。
When：產生Reading Assist或續學摘要。
Then：用户澄清優先；無紀錄为unknown；不用智力/吞吐标签；曝光不等于理解。
失敗條件：課名、頁面點擊或缺資料被轉成已懂/未學過斷言。

### SC-15 · 原始證據糾正AI後設摘要
Given：原紀錄：四PASS後user仍嘗試restart且未成功；AI後續例子稱已獨立判斷不需restart。
When：抽取學習事件／續學包。
Then：保留实际查驗與嘗試，標記摘要不吻合；不宣稱獨立判斷或成功restart。
失敗條件：只因AI寫了demonstrated就當成行為證據。

### SC-18 · 間斷使用無債務
Given：累積多個due item且用戶幾天未使用。
When：今天只看一則或選跳過。
Then：可結束且無責備／罰分／強制清庫；仍能日後回找。
失敗條件：連續天數處罰、欠卡遮罩或今天必須還完。

### SC-21 · 來源錯誤與題目失效隔離
Given：原文有爭議claim且已有舊due與attempt。
When：新增erratum／撤回教學readiness。
Then：raw hash不變；Reader正常、警告可見；新出題及舊due阻擋；歷史保留。
失敗條件：警告不影響planner或修改原文掩蓋錯誤。

### SC-32 · 未授權外送與AI透明fallback
Given：無live API授权，source內含要求忽略規範的文字。
When：閱讀解說／要求feedback。
Then：離線模式明示；transport零呼叫；source指令不成執行規範。
失敗條件：外送私人對話、讀key或把預製內容宣稱live模型結果。

### SC-33 · optional/deferred不是刪掉
Given：有語音、跨平台、模型與浸泡候選，但本轮milestone較小。
When：縮scope或結案。
Then：台帳保留ID、理由、重啟條件；回報局部完成與剩餘能力。
失敗條件：刪除需求後用較小分母宣稱100%。

### SC-35 · 需求追溯與驗證證據
Given：新的feature task與版本化台帳。
When：生成context packet→綁implementation/tests→回報完成。
Then：有source、must/not、scenario、base revision、run evidence；缺少不可verified。
失敗條件：寫test路徑就代表已跑，或checker PASS被描述為產品PASS。

## 來源位置
- B19-U [user] Public-safe normalized source B19-U · {"kind": "withheld_private_source", "value": "B19-U"}
- B23-U [user] Public-safe normalized source B23-U · {"kind": "withheld_private_source", "value": "B23-U"}
- B24-U [user] Public-safe normalized source B24-U · {"kind": "withheld_private_source", "value": "B24-U"}
- B25-A [assistant] Public-safe normalized source B25-A · {"kind": "withheld_private_source", "value": "B25-A"}
- B25-U [user] Public-safe normalized source B25-U · {"kind": "withheld_private_source", "value": "B25-U"}
- B26-U [user] Public-safe normalized source B26-U · {"kind": "withheld_private_source", "value": "B26-U"}
- B27-U [user] Public-safe normalized source B27-U · {"kind": "withheld_private_source", "value": "B27-U"}
- N-GOV [assistant] Public-safe normalized source N-GOV · {"kind": "withheld_private_source", "value": "N-GOV"}
- R-DATA [assistant] Public-safe normalized source R-DATA · {"kind": "withheld_private_source", "value": "R-DATA"}
- R-PRACTICE [assistant] Public-safe normalized source R-PRACTICE · {"kind": "withheld_private_source", "value": "R-PRACTICE"}
- R-RELIABILITY [assistant] Public-safe normalized source R-RELIABILITY · {"kind": "withheld_private_source", "value": "R-RELIABILITY"}
- U-GOV [user] Public-safe normalized source U-GOV · {"kind": "withheld_private_source", "value": "U-GOV"}
- U-NIGHT [user] Public-safe normalized source U-NIGHT · {"kind": "withheld_private_source", "value": "U-NIGHT"}
- U-READ [user] Public-safe normalized source U-READ · {"kind": "withheld_private_source", "value": "U-READ"}
- U-ROADMAP-REINTEGRATION [user] Public-safe normalized source U-ROADMAP-REINTEGRATION · {"kind": "withheld_private_source", "value": "U-ROADMAP-REINTEGRATION"}

## 結案前由執行者補齊
工作樹／基底版本：
本次改動的模組與路徑：
實際測試命令、test ID、結果檔與snapshot：
仍未滿足的需求／沒有執行的驗收：
需求或預設行為變更決策：
可回退方式與下一步：
