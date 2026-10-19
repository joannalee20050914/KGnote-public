# Issue #14／D2-T07 授權能力查核（2026-10-19）

本文件只記錄有界 feasibility spike 的公開官方文件查核，不包含登入、cookie、帳號、私人對話或 live provider 請求。

## 結論

在本切片可驗證的 OpenAI 官方文件中，沒有可供 KGnote 對一般 ChatGPT 訂閱者自動讀取既有對話／memory、或把訂閱當成 KGnote 導師 API 的通用授權路徑。因此 `FD-11` 的自動 subscription handoff 結論為 **unsupported for this bounded spike**。

`Sign in with ChatGPT` 是參與應用程式的身分登入；官方說明明示它不會自行分享 ChatGPT conversations 或 memory。ChatGPT plan 用於其他應用程式也需由 participating app 發起並讓使用者選擇，且不會分享 conversations、memory 或 API key。API 與 ChatGPT subscription 的 billing 亦為獨立系統。

因此本次只保留 provider-neutral、copy-safe 的 manual handoff／人工貼回 delta：不讀 key、不用 cookie、不發送資料、不宣稱已連線或已驗證 live provider。未來若要做 connector，必須另有產品決策、資料授權、官方支援範圍、明確 consent preview 與獨立驗證。

## 官方來源

- [Sign in with ChatGPT](https://help.openai.com/en/articles/20001410-sign-in-with-chatgpt)：身分登入與資料委派是不同權限；不自行分享 conversations 或 memory。
- [Using your ChatGPT plan in other apps and sites](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites)：限 participating app 的使用者選擇；不分享 conversations、memory 或 API key。
- [Managing billing for ChatGPT and the API platform](https://help.openai.com/en/articles/9039756)：ChatGPT 與 API 為分離 billing system。

## 限制

本查核不是所有 provider 的永久相容性宣告，也不是 live authorization 測試；它不能提升 `release_verified`，更不能把 manual fallback 寫成 automatic connector。
