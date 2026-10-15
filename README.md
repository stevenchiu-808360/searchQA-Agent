# searchQA agent

用對話的方式回答搜尋相關問題（相關性、排序、斷詞、同義詞、schema）。

這個資料夾沒有獨立的 agent 程式。在這裡啟動 Claude Code 或 Codex，它就會讀取本資料夾的規則與 skills，以 [bigdata_elasticsearch](https://github.com/PChome24h/bigdata_elasticsearch) 為主要依據，必要時再以**唯讀**方式查詢線上 Elasticsearch 驗證。

## 使用方式

### 啟動

**Claude Code**

```bash
cd ~/Desktop/work/tools/"searchQA agent"
claude
```

或在 VS Code「開啟資料夾」選 `searchQA agent`，再開啟 Claude Code 面板。

**Codex**

```bash
cd ~/Desktop/work/tools/"searchQA agent"
codex
```

> ⚠️ 一定要從這個資料夾啟動 session。從其他資料夾啟動（例如 bigdata_elasticsearch），規則、skills 與權限設定都不會套用。

### 提問範例

直接用中文問：

- 「搜『禮卷』為什麼沒出現 DBCRPB-A900GPWR4？」
- 「『即享卷』會被 typo 修正嗎？」
- 「為什麼 A 排在 B 前面？」
- 「LTR 第一階段用了哪些 feature？」
- 「stage 的 search_product_fuzzy 跟 repo 一樣嗎？」

預設查 **stage**；要查其他環境請在問題中說明（例如「查 prod」）。

### 回答格式

```
結論：...
證據：
- [repo] <檔案路徑>: <相關片段>
- [ES:stage] <指令>: <相關輸出>
建議：...
```

`[repo]` 表示依設定檔推論，`[ES:<env>]` 表示已用線上叢集驗證。

## 初次設定

```bash
cd ~/Desktop/work/tools/"searchQA agent"

# 1. Python 環境（需要 Python 3.14）
python3.14 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 2. ES 連線設定
cp .env.example .env
# 編輯 .env，填入各環境的 username / password

# 3. 拉取 bigdata_elasticsearch（需要 GitHub SSH 權限）
.venv/bin/searchqa repo-sync

# 4. 確認可以運作
.venv/bin/pytest
.venv/bin/searchqa analyze 禮卷 --analyzer custom_ik_syn_query
```

## 運作方式

### 啟動時自動載入的內容

| 檔案 | 作用 |
|---|---|
| `CLAUDE.md` → `AGENTS.md` | 角色、安全規則、工作流程、回答格式（`CLAUDE.md` 只是轉接檔，規則以 `AGENTS.md` 為準） |
| `skills/`（Claude 透過 `.claude/skills` symlink 讀取） | 依問題類型自動觸發的除錯流程 |
| `.claude/settings.json` | 允許執行 `searchqa` 不需確認；禁止 `curl` / `wget` / `kubectl` / `gcloud` / `ssh` 與讀取 `.env` |

### Skills

| Skill | 何時使用 |
|---|---|
| `why-not-found` | 某商品搜不到，或不該出現卻出現 |
| `ranking` | 排序、分數、LTR feature |
| `dictionary` | 斷詞、同義詞、typo、停用詞、IK 詞典 |
| `repo-vs-live` | 比對線上 template / settings / LTR 模型與 repo 是否一致 |

### 工作流程

1. 先讀 `repos/bigdata_elasticsearch/`（`main` 分支）的設定推論答案。
2. 以下情況才查 ES：需要實際資料（doc 欄位、分數、排序）、設定無法確定結果（例如 IK 實際斷詞），或懷疑 repo 與線上不一致。
3. repo 只 checkout `es-schema/` 與 `search/`；`plugins/`、`infra/`、`tools/` 不在 QA 範圍內。

## 安全設計：只能 GET

agent 只能透過 `searchqa` CLI 存取 ES，CLI 有四層保護：

| 層 | 做法 |
|---|---|
| 1. HTTP client | method 寫死為 `GET`，沒有任何可指定 method 的公開介面；request 不帶 body，參數放在 `?source=` |
| 2. Endpoint 白名單 | 只允許 `_analyze`、`_search(/template)`、`_render/template`、`_doc`、`_mapping`、`_settings`、`_alias`、`_scripts`、`_ltr`、`_cat/indices`、`_cat/aliases` |
| 3. Agent 權限 | `.claude/settings.json` 禁止 `curl` 等網路工具；`AGENTS.md` 規定只能用 `searchqa` |
| 4. 測試 | `tests/test_client.py` 檢查只發 GET、不帶 body、白名單外的路徑一律擋下 |

> 白名單是必要的：ES 有些 GET 會產生副作用（`_refresh`、`_flush`、`_reload_search_analyzers`），只限制 GET 並不夠。

> 🔐 建議 `.env` 使用 ES **唯讀帳號**（cluster `monitor`、index `read` + `view_index_metadata`），讓 ES 本身也擋住寫入。

## 已知限制

- **不支援向量檢索**：不產生 `query_vector` / `query_sparse_vector`。跑 hybrid / sparse template 時會省略向量參數，回答中會註明。
- **沒有 `_explain` API**：完整 query 會超過 ES URL 長度上限（4KB）。改用 `search --explain`，只能解釋有出現在結果中的 doc。
- **Template 參數是近似值**：線上搜尋 API 會帶入類別權重（`PCAT_LEVEL*`）與第二階段 `rescore`，agent 自行組的參數沒有這些，排序可能與線上不同。若能提供 log 中的真實參數，結果會較準確。
- 不支援 scroll、PIT、async search。

## CLI

agent 會自行使用，也可以手動執行：

```bash
.venv/bin/searchqa <command> [--env dev|stage|prod] [--pretty]
.venv/bin/searchqa <command> -h
```

| 指令 | 用途 |
|---|---|
| `repo-sync` | clone 或更新 bigdata_elasticsearch |
| `analyze <text> --analyzer A \| --field F [--explain]` | 斷詞 |
| `render <template_id> --params JSON` | 展開 search template |
| `search <template_id> --params JSON [--fields F,..] [--explain] [--raw]` | 執行 search template |
| `script <template_id>` | 取得線上的 template |
| `doc <id> [--fields F,..]` | 取得 doc（找不到時回傳 `found: false`） |
| `mapping [--field F]` / `settings [--analysis]` | mapping / settings |
| `ltr --model M \| --featureset F` | LTR 模型 / feature set |

`--index` 預設為 `product_alias`。

## 專案結構

```
.
├── README.md
├── AGENTS.md / CLAUDE.md
├── .env.example            # 複製為 .env 並填入帳密（.env 不進 git）
├── pyproject.toml
├── .claude/
│   ├── settings.json
│   └── skills -> ../skills
├── skills/<name>/SKILL.md
├── repos/                  # bigdata_elasticsearch clone（不進 git）
├── src/searchqa/
│   ├── __main__.py         # CLI 入口
│   ├── config.py           # 讀取 .env、環境選擇
│   ├── client.py           # GET-only client + 白名單
│   └── commands/           # 各子指令
└── tests/
```

## 開發

- 規則、skills 有變動時，改 `AGENTS.md` 與 `skills/`，不要改 `CLAUDE.md`。
- 新增 ES endpoint 必須同時更新 `client.py` 的 `ENDPOINT_ALLOWLIST` 與 `tests/test_client.py`。
- 新增子指令：在 `src/searchqa/commands/` 繼承 `BaseCommand`，並加入 `__main__.py` 的 `COMMANDS`。
- 測試：`.venv/bin/pytest`
- Lint / format：`.venv/bin/ruff check . && .venv/bin/ruff format .`
