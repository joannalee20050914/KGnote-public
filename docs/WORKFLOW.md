# KGnote 工作流

## Personal Alpha：日常使用只跑這一條

前提：準備一份你明示選定的 UTF-8 Markdown，並選一個已存在的 Obsidian vault（第一次測試建議用 disposable vault）。在 repository root 執行：

```bash
python3 scripts/kgnote_alpha.py \
  "/absolute/path/to/learning-source.md" \
  --vault "/absolute/path/to/Obsidian Vault" \
  --space personal
```

這一個命令會在本機完成 validation、列出人類可讀 preview、transactional materialization 與 read-back。
它不呼叫 external API、不讀 API key、不掃整個 vault，也不修改 `.obsidian`。正常使用不需手改 JSON、
Python、fixture、schema、ID，或依序執行 importer internals。

成功後，終端最後會印出唯一的 `Entry note` 絕對路徑。回到 Obsidian 打開該 `Start Here.md`，即可依序查看：

- 材料主旨與 immutable source；
- Markdown heading 結構；
- 重要 Concept candidates；
- 有原句支持的 relation candidates 與 unresolved associations；
- Evidence 與待確認事項。`Lx-Ly` 精確指向保存 source 的 bytes；若有唯一 enclosing heading，link
  會開啟該 section，否則會明示只開整份文件，不宣稱可直接跳到某一行；
- `My Notes.md` 與 `Continue Here.md`，兩者都是使用者可自由編輯且更新時會逐 byte 保留的檔案。

要留下可重開的手動續讀位置，在停止前開啟 `Continue Here.md`：

1. 在 `Resume link` 放入 workspace 內某篇 note 的 exact heading 或 block wikilink，例如
   `[[Concepts/Port#Related concepts|Resume at my recorded position]]`。
2. 讓 `Current note` 與 `Current section` 分別等於 link 的 note path 與 heading/block anchor。
3. 填寫 `Next` 和 `Question to revisit`；即使目前沒有問題，也要明示記錄，而不是留空。
4. 重開 vault 後從 `Start Here` 的 `Continue` 進入 `Continue Here`，再點 `Resume link`。

空白 starter、最近開過的檔案或檔案時間都不是 continuation。KGnote 不從 recency、click 或停留時間
推測進度。工程端的 continuation read-back 只驗證已填欄位與 heading/block target 能解析，不宣稱使用者
真的完成閱讀。

同一 source path 原樣重跑同一命令會回報 `Status: unchanged`，不建立第二套等價 records。來源內容更新時可
重跑；KGnote 只替換未被修改的 generated files，逐 byte 保留 `My Notes.md`、`Continue Here.md` 與其他 unmanaged files。若直接修改
generated note，workflow 會以 `managed_file_conflict` fail closed，不會覆寫；先把個人內容移到
`My Notes.md` 或另一個 user-owned note 再重跑。

只想看計畫而不寫入時，加：

```bash
--preview-only
```

目前 deterministic extractor 只使用 headings、wikilinks、emphasis、inline code、definition labels 與
明示 relation phrases。所有派生知識保持 `unreviewed`；缺少明確 relation 時只保留 unresolved
association，不為完整外觀補猜。工程 read-back 通過不等於 product owner 已接受實際 Obsidian usability。

## Integrated trial preparation：Markdown + optional Canvas

需要準備可直接在 Obsidian 開啟的 review candidate 時，使用同一份明示選定的來源，並把 `--vault`
指向一個已存在的 **disposable parent directory**：

```bash
python3 scripts/kgnote_obsidian_spike.py \
  "/absolute/path/to/learning-source.md" \
  --vault "/absolute/path/to/disposable-parent" \
  --space personal
```

命令輸出的 `Obsidian vault root`（與 `Workspace` 相同）才是要用 Obsidian 的 **Open folder as
vault** 開啟的根目錄；不要把 `--vault` 的 parent directory 當成 vault。`Learning
Structure.canvas` 的所有 file node、`Start Here.md` 的 wikilink，以及 read-back validator 都以這個
完全相同的根目錄解析。

`Start Here.md` 保留既有 lesson-first sections 和順序，並在其後提供 `Optional Canvas`。Canvas 只是
次要結構導覽；不開 Canvas 時，普通 Markdown 仍包含完整的來源、概念、關係、Evidence、筆記與續讀入口。

review vault 內的 `.obsidian/appearance.json` 只啟用同 vault 的
`.obsidian/snippets/kgnote-reading.css`。它在 Reading view 隱藏 properties 區塊，讓教材先出現；
frontmatter/provenance bytes 仍保存在 note 中，Source 與 audit links 也不受影響。這些檔案只寫入
disposable generated workspace，不修改任何正式／私人 vault 或 Obsidian 全域設定。

終端的 `Read-back: passed` 只代表靜態工程檢查：Canvas file paths 確實由列出的 vault root 解析、
heading anchors 存在、Start Here 可找到 Canvas、Reading-view snippet 已放入並啟用。它不代表實際
Obsidian desktop/mobile 已開啟、CSS 已由 app 套用、互動可用或真人已接受；`NS-HUMAN-SMOKE` 與
`PA-HUMAN-1` 仍須後續集中試用。

這是整合 candidate 的單一 generation／preparation entry；不需要先跑 `kgnote_alpha.py`，也不需要手改
Python 或 JSON。準備完成後，exact vault／entry／Canvas paths、三個集中試用 scenario、known limitations、
engineering／native／human evidence 分界與 prior-candidate recovery 都固定記在
[`docs/obsidian/PERSONAL_ALPHA_INTEGRATED_TRIAL.md`](obsidian/PERSONAL_ALPHA_INTEGRATED_TRIAL.md)。

`My Notes.md` 與 `Continue Here.md` 是 learner-owned Markdown，所以試用時可以正常編輯；native integrity
digest 只綁定 generator-owned lesson/source Markdown。相同輸入或 source update 重跑仍會逐 byte 保留
這兩個檔案及其他 unmanaged learner files，而 generated lesson 的 drift 仍會 fail closed。

## Repository 開發工作流

## 1. 單一可驗收切片

每次只選一個能獨立回答「是否完成」的切片，例如：

- 一個 input schema 與 malformed-input 測試。
- 一個 source importer 的 dry-run，不含 apply。
- 一個 idempotent apply 與 read-back audit。
- 一個 Obsidian fixture 的 local graph 驗收。

「extractor + graph UI + Gemini review」不是單一切片。

## 2. 標準循環

```text
read plan/contracts
  → inspect Git/worktree and existing changes
  → state the slice and acceptance criteria
  → implement the smallest vertical path
  → run focused tests
  → run broader regression checks proportional to risk
  → inspect/read back the artifact
  → update plan or parking lot
  → report scope, evidence, limits, next step
```

## 3. Extraction 實驗要記錄的東西

- run ID、source ID、input content hash、schema/extractor/prompt/model version。
- success/reject/error 數、latency、input/output token 與 API error type。
- concept/edge/evidence yield，但 yield 不當成 quality。
- 人工抽樣的 hallucination、relation error、provenance error、over-merge、under-merge。
- retry/cooldown/checkpoint 紀錄；HTTP 429 屬 infrastructure/API stability，不當成 model semantic failure。

## 4. Dry-run / apply

Apply 前的 preview 至少分為：

```text
CREATE      新的 concept/event/evidence
UPDATE      同一 stable ID 的合法更新
UNCHANGED   已存在的等價內容
CONFLICT    需要人工決定的 alias/merge/人工修改衝突
REJECT      schema/evidence/provenance 不合格
```

Apply 後重新讀取 canonical store，比對預期 ID、reference integrity 與數量。不只相信 process exit code 0。

## 5. 測試層次

- Contract tests：schema、enum、版本、stable ID、多餘／缺失欄位。
- Pure unit tests：normalization、deduplication、relation policy、path/locator codec。
- Integration tests：fixture 從 import 到 dry-run/apply/read-back。
- Golden/manual evaluation：固定小樣本的人工 expected concepts/claims，允許以明確流程更新。
- Visual QA：Obsidian/Web 圖的節點、edge、panel、source link 與行動尺寸。

## 6. 遇到新問題

若不阻擋當前切片，寫進 `DEVELOPMENT_PLAIN.md` 停車場後繼續。只有當問題使目前驗收不可能、可能破壞原始 evidence，或需要使用者的重要產品決策時，才停下來處理／詢問。
