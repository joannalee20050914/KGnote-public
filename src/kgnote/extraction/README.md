# Offline extraction response boundary

`offline_response.py` 將一份不可信任的 raw JSON response replay 成 immutable
`ExtractionAttempt`。它不呼叫 provider、不讀 `.env`、不寫 response/log/vault。

呼叫者提供已驗證的 `ExtractionInput`、`extractor_version` 與 `generated_at`。Response 只能
提供 `concepts`、`evidence`、`learning_events`、`edges` 四個 candidate collections；
schema version、Source identity、extractor version、timestamp，以及 Evidence/LearningEvent
的 Source ID 都由 adapter 注入。

Accepted attempt 內部以 canonical JSON 保存 validated CandidateResult，property 每次回傳
新物件，避免 caller 修改已記錄結果。Accepted/rejected attempt 都保存 exact raw response
與其 UTF-8 SHA-256；`repr` 與 rejection summary 不顯示 raw content。

Parser 拒絕 invalid JSON、duplicate object keys 與非標準 `NaN/Infinity`。不可信 response
錯誤回傳 rejected attempt；無效的 trusted `ExtractionInput` 則沿用 contract exception。

這一層不檢查跨 collection local ref 是否存在／唯一，也不做 normalization、stable ID、
deduplication 或 merge。

## Selected real-provider transport

`GeminiExtractionTransport` is the single Issue #9 provider wrapper. It targets
`google-gemini` / `gemini-3.7-flash` through one non-streaming `generateContent`
REST request, requires an explicitly injected API key, and never retries. The caller
must still build and approve the exact `ExtractionPreview`; constructing a transport
does not authorize an external send. See `docs/ADR-0001-GEMINI-EXTRACTION-TRANSPORT.md`
for the selection, privacy boundary, and live-test gate.
