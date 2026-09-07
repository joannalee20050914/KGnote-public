# KGnote

KGnote 是 knowledge-graph-first 的互動式學習筆記本。它保留原始教材與 AI 對話作為 evidence，把可重用概念組成可導覽的 knowledge graph，並用可追溯的學習事件而不是虛假精確的熟練百分比，記錄使用者與知識的互動。

目前專案處於 contract-first 的 Phase 0，尚未有產品程式碼。

## 閱讀順序

1. [`docs/PRODUCT_CONTRACT.md`](docs/PRODUCT_CONTRACT.md) - 產品做什麼與不做什麼
2. [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) - Concept、Evidence、LearningEvent 與 relation 契約
3. [`DEVELOPMENT_PLAIN.md`](DEVELOPMENT_PLAIN.md) - 當前主線、分期、驗收與停車場
4. [`AGENTS.md`](AGENTS.md) - Codex/agent 與 repository 工作規範
5. [`docs/REFERENCE_SOURCES.md`](docs/REFERENCE_SOURCES.md) - 需求、SynthKG 與 BitePacer 來源索引

## 預期演進

```text
Markdown exports
      ↓
versioned extraction + validation
      ↓
Concept Graph + Evidence + Learning Overlay
      ↓
Obsidian v0
      ↓
Web graph viewer
      ↓
RAG review and low-friction exposure
```

這是階段順序，不是授權一次實作全部功能。

