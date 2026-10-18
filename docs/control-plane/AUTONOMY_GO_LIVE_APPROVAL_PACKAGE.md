# KGnote Autonomous Development Go-Live：擁有人一次性核准事項

狀態：`PROPOSED_NOT_ACTIVE`。本文件不增加任何既有額度，也不解除 Issue #8 的 17/17 internal review、2/2 external Work review 或 `AUTOMATION_BLOCKED`。

## 核准後唯一啟用範圍

- 啟用既有 `com.kgnote.local-autonomy-runner`，每 30 秒最多執行一次 bounded wake；只有 Asia/Taipei 09:00–18:30 會嘗試工作。
- Runner 只呼叫既有 `codex_orchestrator.py resume --max-steps 1`。外部審查等待時只做一次非模型讀取；沒有新結果不啟動模型。
- 每個工作包必須有 `.ai/work-package-envelope.json`，並由既有 Orchestrator 在 verification／seal 前，依完整 reconciliation receipt、exact goal/work-package、active milestone scope、剩餘 internal/external review budget、當前 fingerprint 與 writer lock，原子地從 `RECONCILING` 轉為 `APPROVED`。Runner 還會要求該 transition receipt；手動只改 status 不構成授權。
- 單一 writer lock、terminal states、人工 gate、受保護寫入與既有 GitHub exact-candidate checks 全部保留。

## 建議第一個真實 canary 工作包

- Issue：#8，只處理既有 `finding-r-004`（HTML comment／引用語境的虛假 speaker attribution）及必要 regression tests。
- Local repair attempts：最多 3 次。
- Internal independent reviews：最多 3 輪，新額度另列；不得重寫或清除歷史 17/17。
- External Work reviews：最多 2 輪，新額度另列；不得重寫或清除歷史 2/2。
- 無進展停止：連續 2 輪沒有縮小 blocking findings，或同一 finding 連續 2 輪以相同最小反例重現。
- Usage：保存 role、開始／結束時間、duration、工作包、review cycle、exit code、result、transcript path，以及平台實際提供的 token 數。訂閱剩餘額度與 reset time 沒有可靠來源時維持 `unknown`。

## 不包含的權限

- 不允許修改或合併 PR #1、PR #22、`main`，不允許 force push 或略過 branch protection。
- 不允許付費 API、新資料外送、刪除 immutable evidence、覆寫人工筆記或提升 `PA-HUMAN-1`、`NS-HUMAN-SMOKE`、`release_verified`。
- Push、建立新 PR、merge 及任何平台要求的人工批准仍須各自符合既有權威；本核准不會把它們變成無條件允許。
- GitHub Projects 可使用現有 `project` scope 做最小狀態同步與 read-back；若 API 或欄位權限拒絕，改以 Issue／PR receipt 保持可見並 fail closed，不擴權。

## 啟用、停止與回復

核准後先將 example 複製為正式 envelope，填入 exact authority URL 與上述額度，執行 read-back，再 bootstrap LaunchAgent。正式 canary 只在所有 preflight 與 envelope checks 通過後開始。

立即停止：

```bash
launchctl bootout gui/501 /Users/joanna/Library/LaunchAgents/com.kgnote.local-autonomy-runner.plist
```

停止後保留 envelope、Orchestrator state、review history、GitHub receipts 與 runner log；不 reset、clean 或刪除 checkpoint。回復只需保持 LaunchAgent 未載入，並將 envelope 狀態設為非 `APPROVED`。排程喚醒不得解除任何 terminal state。

## 擁有人核准需要明示的單一決定

是否核准上述第一個 canary 工作包（3 次 local repairs、3 輪新 internal reviews、2 輪新 external Work reviews、09:00–18:30、兩輪無進展即停止），以及允許在 exact read-back 後載入既有 LaunchAgent。未取得明示核准前，本方案維持 `PROPOSED_NOT_ACTIVE`。
