---
name: why-not-found
description: Use when a product does not appear (or appears unexpectedly) in search results for a query (e.g. "搜 X 為什麼沒有商品 Y", "為什麼搜 X 會出現 Y").
---

# Why a product is (not) found

Inputs needed: query text, product id (`IT_NO`, e.g. `DBCRPB-A900GPWR4`). Ask for the id if only a name is given; you can also find candidates with `searchqa search`.

## Steps

1. **Does the doc exist?** `searchqa doc <id> --fields IT_NO,IT_NAME,IS_SHELF,IS_VALID,IS_NC17,PCAT_LEVEL2`
   - `found: false` → not indexed. Point to `search/datafeed/` (Pub/Sub → ES; DELETE messages hard-delete). Stop here.
2. **Is it filtered out?** Read the template's fixed `must_not` / `filter` clauses in `es-schema/search_template/<template>.json` (e.g. `WEIGHT`, shelf/valid flags) and compare with the doc's fields.
3. **Do the tokens match?** Tokenize both sides:
   - query: `searchqa analyze "<query>" --analyzer custom_ik_syn_query` and `--analyzer custom_ik_query`
   - product name: `searchqa analyze "<IT_NAME>" --analyzer custom_ik_index`
   Fuzzy/exact templates use `operator: and` on `BIG_FIELD_NAME(.ik_syn)` — every query token must exist on the index side. Missing token → dictionary issue (use the `dictionary` skill).
4. **Is it just ranked low?** Run the template and look for the id beyond the first page (raise `size`, max ~200):
   `searchqa search search_product_fuzzy --params '<params>' --fields IT_NAME`
   If found deep in results, switch to the `ranking` skill.

## Template params

Templates are written for the search API, which supplies extra params. Minimal working params for `search_product_fuzzy`:

```json
{"query":"<q>","WORD":"<q>","fuzzy":true,"fuzzy_main_term":"<q>","size":40,
 "PCAT_LEVEL2":{},"PCAT_LEVEL3":{},"PCAT_LEVEL4":{},
 "rescore":{"window_size":1,"query":{"rescore_query":{"match_all":{}},"query_weight":1,"rescore_query_weight":0}}}
```

- `PCAT_LEVEL*` must be objects (category → weight); `{}` disables category boosting.
- `rescore` is the second-level rescore supplied by the search API; the no-op above keeps only first-level LTR.
- Always state in the answer that category weights and second-level rescore were not applied, unless the user supplied real params (from search API logs).
- Never pass vector params (`query_vector`, `query_sparse_vector`); hybrid/sparse templates run without vector scores.
- For other templates, list required params with `grep -oE '\{\{[#^]?[A-Za-z_]+' <file>` and read the template before calling.
