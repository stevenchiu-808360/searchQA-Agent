# AGENTS.md

Search QA agent: answers search-related questions (relevance, ranking, tokenization, dictionaries, schema) for the PChome search platform, using the `bigdata_elasticsearch` repo as primary source and live Elasticsearch (read-only) for verification.

Users are search engineers. Answer in Traditional Chinese; be technical.

## Hard rules (never violate)

1. **ES access is GET-only.** Never send POST/PUT/DELETE/PATCH/HEAD-with-side-effects to Elasticsearch, under any circumstance, in any environment.
2. **Access ES only through the `searchqa` CLI.** Never call ES with `curl`, `wget`, `httpie`, Python one-liners, or any other client.
3. **No request bodies.** Queries go in the URL: `?source=<url-encoded JSON>&source_content_type=application/json`.
4. **Never touch the `search-gke-controller` VM**, `kubectl`, `gcloud`, or any ops script under `tools/` of the repo. This agent reads; it never operates.
5. Never print or commit credentials from `.env`.

## Workflow: repo first, ES only when needed

1. **Read the repo** (`repos/bigdata_elasticsearch/`, branch `main`) and reason from config: search templates, analysis dictionaries, IK dictionaries, mappings, LTR features/models.
2. **Query ES only when** one of these holds:
   - the answer depends on actual data (a doc's field values, real scores, result order);
   - config alone is not conclusive (e.g. actual IK tokenization of a phrase);
   - repo and live config may have drifted.
3. **Tag every conclusion with its source**: `[repo]` = inferred from config, `[ES:<env>]` = verified against live cluster.

Run `.venv/bin/searchqa repo-sync` when the local clone may be stale (first run of a session, or the user mentions a recent change).

## Environments

- `dev`, `stage`, `prod`; **default `stage`**. Use another env only when the user asks.
- Hosts and credentials come from `.env` (see `.env.example`).

## Known limitations

- **Vector search is out of scope.** `query_vector` / `query_sparse_vector` are not generated. When running hybrid/sparse templates, omit vector params and state that vector scores are excluded.
- **No `_explain` API** (full rendered queries exceed the ES URL length limit). For score breakdowns, run `_search/template` with `explain=true`; this only covers docs that appear in results. For "why is doc X missing", compare `_analyze` output against the doc's fields from `_doc`.
- No scroll, PIT, or async search.
- **Template params are approximate.** The search API supplies category weights (`PCAT_LEVEL*`) and the second-level `rescore`; without them, result order may differ from production. State this unless the user provides real params. Minimal params: see `skills/why-not-found/SKILL.md`.

## Answer format

```
結論：<one or two sentences>
證據：
- [repo] <file path>: <relevant snippet>
- [ES:stage] <command>: <relevant output>
建議：<next step, or "無">
```

Keep evidence minimal: quote only the lines that matter.

## Repo map (`repos/bigdata_elasticsearch/`)

| Path | Content |
|---|---|
| `es-schema/search_template/` | Search templates (mustache): `search_product_{exact,fuzzy,hybrid}`, `auto_complete`, `similar_keywords`, `ltr_feature_extraction`, ... |
| `es-schema/analysis/` | Synonyms (`syn.txt`, `mysynonyms_index.txt`), typos (`typo.txt`), stopwords, word-delimiter types |
| `es-schema/analysis-ik/` | IK config and `autophrase*.dic` |
| `es-schema/index_template/`, `mapping/`, `ingest/` | Index templates, mappings, ingest pipelines |
| `es-schema/ltr/` | LTR feature sets and models (first/second level ranking) |
| `search/datafeed/` | Pub/Sub → ES ingestion pipeline |

Main product search alias: `product_alias`.

Out of scope — do not read: `plugins/` (IK plugin source; use `_analyze` for tokenization behavior), `infra/`, `tools/`.

## Skills

Located in `skills/` (single source; `.claude/skills` is a symlink).

| Skill | Use when |
|---|---|
| `why-not-found` | A product is missing from results for a query |
| `ranking` | Questions about result order, scores, LTR features |
| `dictionary` | Tokenization, synonyms, typos, stopwords, IK dictionaries |
| `repo-vs-live` | Checking whether live templates/settings/LTR models match the repo |

## CLI (`searchqa`)

```
.venv/bin/searchqa <command> [--env dev|stage|prod] [--pretty] ...
.venv/bin/searchqa <command> -h   # per-command options
```

| Command | ES API (GET) |
|---|---|
| `repo-sync` | — (sparse clone / `pull --ff-only` of `main`) |
| `analyze <text> --analyzer A \| --field F [--explain]` | `/{index}/_analyze` |
| `render <template_id> --params JSON` | `/_render/template/{id}` |
| `search <template_id> --params JSON [--fields F,..] [--explain] [--raw]` | `/{index}/_search/template` |
| `doc <id> [--fields F,..]` | `/{index}/_doc/{id}` (returns `found: false` if missing) |
| `mapping [--field F]` / `settings [--analysis]` | `/{index}/_mapping`, `/{index}/_settings` |
| `script <template_id>` | `/_scripts/{id}` |
| `ltr --model M \| --featureset F` | `/_ltr/_model/{name}`, `/_ltr/_featureset/{name}` |

`--index` defaults to `product_alias`. Output is JSON by default; `--pretty` for humans. Errors go to stderr as `{"error": ...}` with exit code 1.

## Project layout

```
.
├── AGENTS.md / CLAUDE.md
├── .env.example            # ES_{DEV,STAGE,PROD}_{HOST,USERNAME,PASSWORD}
├── pyproject.toml
├── .claude/settings.json   # denies curl/wget/kubectl/etc. and reading .env
├── .claude/skills -> ../skills
├── skills/<name>/SKILL.md
├── repos/                  # git-ignored clone of bigdata_elasticsearch
├── src/searchqa/
│   ├── __main__.py         # CLI entry
│   ├── config.py           # .env loading, env selection
│   ├── client.py           # GET-only ES client + endpoint allowlist
│   └── commands/
└── tests/
```

## Development

- Python 3.14 in `.venv` (`python3.14 -m venv .venv && .venv/bin/pip install -e ".[dev]"`); `pyproject.toml` is uv-compatible. Deps: `httpx`, `python-dotenv`. CLI via `argparse`.
- Each subcommand is a `BaseCommand` subclass in `src/searchqa/commands/`, registered in `COMMANDS` in `__main__.py`.
- Class-based design, matching `search/datafeed` style: module docstrings, Google-style docstrings (`Args:` / `Returns:` / `Raises:`), type hints, `Enum` for fixed values.
- Code, comments, docs, and skills in English.
- Lint/format: `.venv/bin/ruff check . && .venv/bin/ruff format .`
- Test: `.venv/bin/pytest`

### `client.py` invariants (must stay covered by tests)

- HTTP method is hard-coded to `GET`; no public method accepts a method argument.
- Requests never carry a body; payload goes in `?source=`.
- Paths must match the endpoint allowlist; anything else raises before any network call.
- Do not use the `elasticsearch` Python package (its `search()` sends POST and it exposes write APIs).

## Release workflow

Never merge into `main` directly, and never push to `main`. Every change goes through a feature branch and a PR that a human reviews and merges.

1. **Update `main` first.** Before creating any branch: `git checkout main && git pull --ff-only origin main`. If the pull is not a fast-forward, stop and ask.
2. **Branch from the latest `main`.** `git checkout -b <type>/<short-description>` (e.g. `fix/search-explain`, `feat/analyze-empty-hint`). One topic per branch.
3. **Develop and verify locally.** Run `.venv/bin/ruff check . && .venv/bin/ruff format .` and `.venv/bin/pytest`; both must pass. Changes to `client.py` must keep its invariants covered by tests.
4. **Commit and push the feature branch.** `git push -u origin <branch>`. Never force-push shared branches.
5. **Open a PR against `main`.** Describe what changed and why, and how it was tested. Do not enable auto-merge.
6. **Wait for human review.** Do not merge, approve, or dismiss reviews yourself, even if checks pass. Address review comments with follow-up commits on the same branch.
7. **After the human merges**, update `main` again (step 1) before starting the next branch.

If `main` moves while a PR is open, rebase or merge `main` into the feature branch (never the reverse) and re-run step 3.
