---
name: dictionary
description: Use for questions about how a query or product name is tokenized, synonyms, typo correction, stopwords, or IK dictionaries (e.g. "禮卷怎麼斷詞", "X 有沒有同義詞", "為什麼 A 會被當成 B").
---

# Dictionary / tokenization

## Analyzer chain (live `product_alias`, verify with `searchqa settings --analysis` if unsure)

| Analyzer | Tokenizer | Filters | Used as |
|---|---|---|---|
| `custom_ik_index` | `ik_max_word` | multiplexer(`word_delimiter_graph_ik`, `lowercase`+`synonyms_index`), lowercase, flatten_graph, unique | index analyzer of most text fields |
| `custom_ik_query` | `ik_smart` | lowercase, `stopwords_ik`, `word_delimiter_graph_ik_query` | search analyzer of most text fields |
| `custom_ik_syn_query` | `ik_smart` | lowercase, `synonyms_typo_query`, `synonyms_query` | `*.ik_syn` subfields, `IT_ATTR`, `IT_CORE_TAG` |
| `custom_syn_query` | `keyword` | lowercase, asciifolding, `synonyms_typo_query`, `synonyms_query` | `*.syn` subfields |
| `custom_2gram_index` / `_query` | `standard` | lowercase, word_delimiter_graph, shingle_2gram, `stopwords_v1` | 2-gram fields |

## Filter → repo file (`repos/bigdata_elasticsearch/es-schema/`)

| Filter | File | Format | Reload |
|---|---|---|---|
| `synonyms_typo_query` | `analysis/typo.txt` | `wrong => right` | `_reload_search_analyzers` |
| `synonyms_query` | `analysis/syn.txt` | `a,b,c` (equivalent) | `_reload_search_analyzers` |
| `synonyms_index` | `analysis/mysynonyms_index.txt` | index-time; needs reindex | reindex |
| `stopwords_ik` | `analysis/stopword.dic` | one per line | — |
| `stopwords_v1` | `analysis/stopwords_v1.txt` | one per line | — |
| IK tokenizer words | `analysis-ik/autophrase*.dic` (+ base dicts baked into image) | one per line | rolling restart |

## Steps

1. `grep -n` the term in the files above. Report exact lines. Note typo rules apply before synonyms.
2. If the question is about actual token output, or IK base dictionaries matter (they are not in the repo), run:
   `searchqa analyze "<text>" --analyzer <name>` (add `--explain` to see each filter's output).
   Compare query-side (`custom_ik_syn_query`, `custom_ik_query`) and index-side (`custom_ik_index`) when the question is about matching.
3. If repo and live output disagree (e.g. a rule in `syn.txt` has no effect), the dictionary may not have been deployed/reloaded — say so and suggest the `repo-vs-live` skill.
