# Deterministic normalization v1

`kgnote.normalize.v1` 將一個 validated `ExtractionCandidateResult` 純轉換成 canonical
record candidates 與 local-ref → canonical-ID map。它不讀現有 vault、不 merge、不 apply。

## Text rules

- Unicode NFC。
- 去除頭尾空白並將內部連續 whitespace collapse 成一個空格。
- Concept identity 使用 case-folded canonical name；輸出保留 normalized display case。
- Alias 以 case-insensitive key 去重並穩定排序；與 canonical name 相同者移除。
- Space 作為 identity namespace，NFC/whitespace/case-fold 後去重排序。
- 不做 stemming、翻譯、synonym/fuzzy matching 或 ontology inference。

## Stable IDs

每個 ID 都是 typed/versioned identity payload 的 canonical JSON（sorted keys、explicit
null、UTF-8）完整 SHA-256，加上 `concept_`、`evidence_`、`event_`、`edge_` prefix。
Local ref 與 list position 不進 identity。

- Concept：case-folded name、sorted spaces、normalization ruleset。
- Evidence：Source、normalized locator/proposition、canonical schema version。
- LearningEvent：Source、normalized locator、event type、canonical schema version。
- Edge：resolved source/target canonical IDs、relation（含 null）、class、ruleset。

同一 batch 有兩個 local refs 產生相同 typed ID 時回 `identity_conflict`，不靜默 merge。

## Output policy

AI Concept 一律先是 `needs_review`；Evidence 一律先是 `unreviewed`。CandidateResult 的
`generated_at` 被重用為 deterministic extraction/integration timestamp，不讀 system clock。
結果物件內部保存 canonical JSON，property 每次回傳新物件，避免 caller 改寫驗收結果。

這層只驗 local-reference integrity 與 deterministic mapping；existing-note comparison、alias
merge、CREATE/UPDATE/UNCHANGED/CONFLICT、Markdown render 與 vault apply 均屬後續切片。
