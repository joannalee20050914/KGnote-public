# KGnote

KGnote 是 knowledge-graph-first 的互動式學習筆記本。它保留原始教材與 AI 對話作為 evidence，把可重用概念組成可導覽的 knowledge graph，並用可追溯的學習事件而不是虛假精確的熟練百分比，記錄使用者與知識的互動。

目前已完成 contract-first Phase 0 與 Phase 1 extractor pipeline 的 mock 驗證，正在以全離線 synthetic/replay 流程進行 Phase 2 Obsidian 實用性驗證；Gemini Free Tier key 維持停用。

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

## Local setup

Prerequisites: Python 3.11 or newer, Node.js, and npm.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
npm ci
scripts/run_tests.sh
```

Runtime credentials are supplied through environment variables or an ignored local `.env` file. Copy `.env.example` only as a local starting point; the committed example contains placeholders and no credential values. Offline and replay verification does not require a live provider key.

KGnote is under active development. The repository's deterministic checks validate contracts and fixtures, but they do not replace the explicit physical-device and human product-acceptance gates documented in the control plane.
