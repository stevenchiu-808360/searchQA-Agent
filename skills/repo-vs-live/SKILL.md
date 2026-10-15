---
name: repo-vs-live
description: Use to check whether the live cluster matches the bigdata_elasticsearch repo (search templates, analysis settings, dictionaries, LTR models), or when repo-based reasoning contradicts live behavior.
---

# Repo vs live drift

Run `searchqa repo-sync` first so the repo is current (`main`).

| Item | Repo | Live |
|---|---|---|
| Search template | `es-schema/search_template/<id>.json` (`script.source`) | `searchqa script <id>` |
| Analyzers / filters | `es-schema/index_template/search-product-template.json` | `searchqa settings --analysis` |
| Mapping | same index template (`mappings`) | `searchqa mapping [--field F]` |
| LTR model | `es-schema/ltr/*/*model*.json` | `searchqa ltr --model <name>` |
| LTR feature set | `es-schema/ltr/*/*features*.json` | `searchqa ltr --featureset <name>` |
| Synonym / typo rules | `es-schema/analysis/*.txt` | not readable via API — verify behavior with `searchqa analyze` on a sample rule |

## Steps

1. Fetch both sides. Compare after normalizing whitespace (templates are mustache strings; collapse whitespace before diffing). Write both to temp files under the scratchpad and `diff` them rather than eyeballing.
2. Report: in sync / differs, and the specific differing lines.
3. Use `git -C repos/bigdata_elasticsearch log -- <path>` to show when the repo side last changed.
4. Dictionary rules: pick 1–3 rules from the file (prefer recently added: `git log -p`) and check `analyze` applies them. If not, the ConfigMap or `_reload_search_analyzers` step likely was not run for that env.
