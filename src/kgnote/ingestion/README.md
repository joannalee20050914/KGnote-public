# Local source ingestion

`markdown_source.py` 是 Phase 1 的單檔 Markdown I/O adapter。呼叫者必須明確傳入路徑與
`SourceMetadata`；adapter 不掃描目錄，也不從可變檔名猜 Source identity。

```python
from kgnote.ingestion import SourceMetadata, import_markdown_source

payload = import_markdown_source(
    "/explicit/path/source.md",
    metadata=SourceMetadata(
        source_id="src_example",
        source_kind="document",
        title="Example",
        captured_at=None,
        locator_basis="line_range",
    ),
)
```

檔案以 UTF-8 strict decode，完整內容不做 front-matter parsing、修復或正規化。SHA-256
由可 round-trip 回原始 bytes 的完整 content 計算，完成 payload 在回傳前必須通過
`ExtractionInput` v1 schema。

`MarkdownSourceImportError.code` 是可供測試與 caller 分支處理的安全分類：

- `path_not_found`
- `not_regular_file`
- `unsupported_extension`
- `invalid_utf8`
- `empty_content`
- `read_failed`
- `invalid_source_id`
- `invalid_source_kind`
- `invalid_title`
- `invalid_captured_at`
- `invalid_locator_basis`
- `invalid_extraction_input`

錯誤訊息不包含 source content。此模組只回傳 in-memory payload，不寫 canonical vault，
也不進行 API request、extraction、normalization、stable-ID generation 或 merge。
