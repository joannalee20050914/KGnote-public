# Extraction contract v1

這裡的 JSON Schema 是 extraction boundary 的 language-neutral source of truth，採
JSON Schema Draft 2020-12：

- `ExtractionInput`：未來 importer 交給 extraction adapter 的 immutable source context。
- `ExtractionCandidateResult`：adapter 包裝的候選結果，尚未進入 normalization/integration。

## 版本

Input 與 output 分別使用 `kgnote.extraction-input.v1` 與
`kgnote.extraction-output.v1`。未知版本 fail closed，不 fallback 到 latest。任何改變可接受
payload shape 的修改都要建立新版 schema。

這些版本不同於 canonical Markdown 的 `kgnote.v0.1`：extraction contract 可以演進而不
靜默改寫 canonical store；兩者只在後續 normalization/integration adapter 明確銜接。

## 欄位所有權

`schema_version`、`source_id`、`extractor_version`、`generated_at` 由 adapter envelope
負責，不應信任模型自行填寫。Concept、Evidence、LearningEvent 與 Edge 內容是待驗證的
candidate。測試直接組裝完整 envelope，並不代表已實作 adapter。

Candidate 只使用 payload-local refs：`c_*`、`ev_*`、`le_*`、`ed_*`。它不能產生
canonical `concept_*`、`evidence_*`、`event_*` 或 `edge_*` ID，也不能決定 alias merge、
deduplication 或 stable ID。

## Schema 能力邊界

Schema 可驗證欄位、enum、格式、local-ref 類型與 edge endpoint/relation family。它不能只靠
JSON Schema 證明 local ref 確實存在、全域唯一，或 output `source_id` 與 input 相同；測試會
對 valid fixture 做 read-back assertion，正式語意驗證留給後續 normalization 切片。

## 執行測試

從 clean checkout 安裝隔離依賴並執行：

```sh
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt && scripts/run_tests.sh
```

安裝 dependency 可能需要 PyPI；`scripts/run_tests.sh` 與 test suite 本身不使用網路、不寫入
canonical fixture/vault。
