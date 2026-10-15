---
name: ranking
description: Use for questions about result order, scores, boosting, or LTR (e.g. "為什麼 A 排在 B 前面", "LTR 用哪些 feature", "某商品分數怎麼算").
---

# Ranking

## Pipeline (read the template to confirm)

1. Base query in the template (`search_product_{exact,fuzzy,hybrid}`), with `function_score` / category boosts from `PCAT_LEVEL2/3/4` params.
2. Rescore stage 1: `sltr` with model `first_level_model` (`es-schema/ltr/first_level_ranking/`), `query_weight: 0` → LTR score replaces base score within `window_size`.
3. Rescore stage 2: `rescore` param from the search API (second-level model, `es-schema/ltr/second_level_ranking/`, e.g. `model_v9`).
4. If `has_sort` is set, rescore is skipped and explicit sort applies.

## Steps

1. Answer structural questions (which features, which model, weights) from the repo: `es-schema/ltr/*/` feature and model JSON.
2. For actual scores, run the template with explain (see `why-not-found` skill for minimal params):
   `searchqa search <template> --params '<params>' --fields IT_NAME --explain`
   Compare the two docs' `explanation` trees; summarize the top contributing parts, not the whole tree.
3. For LTR feature values, add `"has_ltr_log": true` to params and read `fields._ltrlog` via `--raw` (use `filter_path` sparingly; output is large).
4. Check the live model matches the repo: `searchqa ltr --model <name>` (see `repo-vs-live`).

## Caveats to state

- Without real search API params, category weights and second-level rescore are missing; order may differ from production.
- `explain` only covers docs present in the returned hits; no `_explain` API is available.
