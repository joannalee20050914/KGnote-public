# BitePacer P4：備份檔「存在」為什麼還不等於「可恢復」？

> Material ID: `h0-bitepacer-p4-backup-v1`
> Grounded in BitePacer commit `3679c9be4fbd518e7677f62e7f9c277fb579018e`,
> `p4_sqlite_backup.py` SHA-256 `d08982e517338e4bd0d37c834f1cb4623d852be95ad213e3fa6c943f28d92472`.
> 這份教材描述該版本程式的行為，不主張它是所有 SQLite 系統的最佳備份方法。

## A. 建立備份：copy 完成後，程式還要證明什麼？

`create_online_backup()` 不把「產生了一個檔案」直接當成功。它先拒絕把備份放在 live database
相同目錄，也拒絕覆寫相同時間戳的 backup 或 manifest。實際複製使用 SQLite connection 的
`backup()`，而不是在資料庫可能仍開啟時直接複製檔案 bytes。

複製完成後，`verify_backup()` 以 read-only SQLite connection 檢查三類訊號：

1. `PRAGMA integrity_check` 必須回傳 `ok`；
2. migration ledger 必須至少有一筆，並保存最新 `migration_id`；
3. 七張 P4 core tables 都必須能查詢，並保存各自 row count。

驗證成功後才計算 backup file 的 SHA-256，並把建立時間、live source path、backup path、
SHA-256、最新 migration、table counts 與 integrity result 寫入 manifest。若 backup API 或
驗證階段失敗，未通過的 destination 會被移除；程式不會留下它並宣稱成功。

## B. 之後再驗 manifest：不是重讀 JSON 就算驗證

`verify_backup_manifest()` 先解析 manifest，再對 manifest 指向的 backup 重新執行
`verify_backup()`。它把「現在實際讀到的」結果和 manifest 當時記錄的三項內容逐一比較：

- file SHA-256；
- latest migration；
- core table row counts。

任一項不同就 fail closed。SHA-256 回答的是 backup bytes 是否仍與 manifest 綁定；
SQLite integrity、migration 與可查詢的 table counts 則回答檔案是否仍具有程式預期的資料庫
結構與最低內容輪廓。這些檢查重疊但不相同，因此不能只保留其中一項就宣稱等價。

## C. Restore：為什麼寫到新檔，而不是直接蓋回 live database？

`restore_to_new_file()` 拒絕覆寫既有 destination。它先驗證 backup，再用 read-only source
connection 將內容寫到新的 SQLite file；寫完後對新檔再次執行 `verify_backup()`，並比較 restore
前後的 core table counts。若 counts 不同，就刪除失敗的新檔並回報錯誤。

這條路徑刻意是 non-destructive verification：它證明「能產生一份通過既定檢查的新資料庫」，
但不會自動替換目前 live database。注意，程式沒有要求 restored file 的 SHA-256 必須等於 backup
file；它比較的是兩邊都可通過的 SQLite 檢查及 table counts。SQLite 的邏輯 backup 不應被簡化成
「兩個檔案 bytes 必須完全相同」。

## 一個要能自行回答的問題

如果同事說：「backup 檔案存在，而且 SHA-256 沒變，所以一定能安全恢復」，你會如何用這份
程式的三個階段反駁或補充？請區分 create-time verification、later manifest verification，及
restore-to-new-file verification 各自增加了什麼 evidence，並指出它們仍沒有自動做的事。
