# ADR-0001: Gemini real-provider extraction transport

- Status: accepted for Issue #9
- Decision date: 2026-09-07
- Documentation access date: 2026-09-07

## Decision

Phase 1 的第一個真實 provider transport 選用 Gemini Developer API `generateContent` 非串流 REST，固定 provider `google-gemini` 與 stable model code `gemini-3.7-flash`。只使用 structured JSON output，不使用 grounding、tools、server-side state、streaming、batch 或自動 retry。

Transport 必須由 caller 明確傳入 API key；不得自行讀取環境變數、檔案或 keychain。它只把已通過 `ExtractionPreview` consent digest 的 envelope 當作唯一 user content 放入單一 request；固定 system safety instruction 與 response schema 是版本化 transport control，不加入其他 source context。它取回唯一 candidate 的原始 JSON text，並將 `responseId` 與 token usage 交給既有 immutable ledger。API HTTP wrapper 不被當成 candidate raw response；ledger 保存的是實際送入 offline validation boundary 的 exact model text bytes。

目前只完成 mocked transport 與 synthetic E2E。沒有進行 live request，也沒有產生 API 費用。

## Why this provider

Gemini 3.7 Flash 的 stable model code 支援 structured outputs，具 1,048,576 input 與 65,536 output token limits。官方 `generateContent` response 提供 `responseId`、`modelVersion` 與 `usageMetadata`，符合 ledger 所需 request identity 與 usage。官方 structured-output API 接受 `responseJsonSchema`，而 KGnote 仍會在本地以完整 schema 與語意規則 fail closed；provider schema 只是第一層約束。

價格頁在決策日列出的 Gemini 3.7 Flash paid standard 價格為每百萬 input tokens USD 0.75、output/thinking tokens USD 3.75（至 2026-12-31），低於比較時的 GPT-5.6 Terra 每百萬 input USD 2、output USD 12。Transport 將單次 output cap 設為 8,192 tokens；若 synthetic fixture 的 provider 計價 input 不超過 10,000 tokens，保守估算單次低於 USD 0.04（0.0075 + 0.03072，未計匯率或稅）。這不是精確報價：本地 byte count 不能可靠換算 provider tokens；live run 前仍須重新核對價格，response usage 才是事後依據。模型完整 context/output limits 下的理論極端值也遠高於此 fixture estimate。

資料邊界是有條件的：只有連到 active billing account 的 Gemini API project 才屬 Paid Service；官方條款稱 paid prompts/responses 不用來改善產品。一般 paid traffic 仍可能為 abuse monitoring 在有限期間記錄 prompt/response；ZDR 需要另行申請核准。KGnote 因此不得把「有 API key」視為符合敏感資料授權，live preview 必須同時確認 project 是 paid、資料已 synthetic 或依明確版本 redacted、且沒有開 grounding。

## Rejected alternatives

### OpenAI Responses API / GPT-5.6 Terra

技術上可行：支援 structured outputs，API business data 預設不拿來訓練，且 Responses API 可在 Zero Data Retention 下強制 `store=false`。未選為第一個 transport，因目前文件價格較高、Phase 4 已預定重新評估 Gemini reviewer，先選 Gemini 可少一個 provider surface。OpenAI 的預設 abuse monitoring 也可能保存 customer content 最多 30 天；ZDR 同樣須資格與核准。

### Google Gen AI Python SDK

官方且成熟，但本切片拒絕引入。官方 troubleshooting 文件說 Python SDK 對 timeout、429 與 5xx 預設可自動 retry；這會讓一次 consent 在 transport 內產生多次 external requests。直接 REST 使用 Python standard library 可明確保證一次呼叫、零新增 runtime dependency，並讓測試檢查 exact method、endpoint、headers、body 與 timeout。

## Failure and security contract

- HTTP 401/403 → `authentication_error`；429 → `rate_limit`；其他 HTTP error → `provider_error`。
- socket/operation timeout → `timeout`；URL/network failure → `transport_error`。
- malformed provider JSON、blocked/no candidate、多 candidate 或非單一 text part → `provider_error`。
- 不重試、不串流、不讀 secrets、不記錄 API key；key 放在 `x-goog-api-key` header，不放 URL。
- provider structured schema 不取代現有 offline schema、local-reference integrity、normalization、dry-run 或 apply approval。

## Official sources

- [Gemini 3.7 Flash model](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash)
- [GenerateContent API reference](https://ai.google.dev/api/generate-content)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- [Gemini zero data retention](https://ai.google.dev/gemini-api/docs/zdr)
- [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini troubleshooting and retry behavior](https://ai.google.dev/gemini-api/docs/troubleshooting)
- [OpenAI model comparison](https://developers.openai.com/api/docs/models/compare)
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- [OpenAI business/API training defaults](https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/)

## Known unknowns and next gate

- 真實 account 的 billing/ZDR/region 狀態無法由 repository 證明。
- 首次 live request 前需建立 exact synthetic/redacted preview，顯示 destination、outbound bytes、SHA-256、redaction version 與當時價格，再取得 fresh digest-bound authorization。
- 首次 live response 要人工檢查 provider payload shape、usage 與 structured-output adherence；若 API schema subset 拒絕目前 schema，不可暗自放寬 local contract。
