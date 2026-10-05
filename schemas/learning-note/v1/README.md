# LearningNote v1

一個 learning unit 對應一份人類可讀、可直接編輯的 Markdown 筆記。front matter
保存 identity、server-generated revision、來源入口與最近一次冪等 save token；正文只使用
headings、lists 與 paragraphs。

- `notes/` 是 LearningNote 的 authoritative store，不是 canonical Concept Graph 的一部分。
- 強 ETag 是完整 Markdown bytes 的 SHA-256；更新必須帶目前 ETag，首次建立使用 `If-Match: *`。
- `save_id` 只代表同一個 save command。最近一次 command 可在 response 遺失後安全重送；相同 ID 配不同內容一律 conflict。
- `source_anchors` 是 note-level 回源入口，不宣稱與易變 heading 一一綁定。
- v1 不接受 raw HTML 或 Markdown image syntax；Web renderer 只建立 allowlisted DOM nodes，不用 `innerHTML`。
