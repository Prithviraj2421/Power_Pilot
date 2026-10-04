# PowerPilot benchmark results

25 datasets. Every rate is the mean of per-dataset rates unless stated.

## Semantic types and domain

Column accuracy counts `unknown` as a class; F1 is over the columns that mean something. Domain ECE uses 5 bins because there are only a few dozen datasets.

| system | datasets | column accuracy | F1 (labelled columns) | column ECE | domain accuracy | domain ECE (5 bins) |
|---|---|---|---|---|---|---|
| full | 25 | 39.9% | 33.3% | 0.340 | 28.0% | 0.100 |
| raw_llm | not run |  |  |  |  |  |

## KPIs

Validity and value accuracy are checked by an independent DAX evaluator. Recovery compares against hand-written pandas on the raw file.

| system | datasets | validity (refs exist and executes) | value accuracy | hand-computed KPIs recovered |
|---|---|---|---|---|
| full | 25 | 99.0% | 99.0% | 22.3% |
| no_kpi_verifier | 25 | 99.0% | 99.0% | 22.3% |
| raw_llm | not run |  |  |  |

## Insights on shuffled-column (null) data

A claim is a CORRELATION or TREND insight. On a shuffled copy every such claim is false by construction.

| datasets | mean relationship claims, real data | mean claims, null data | share of datasets with any false claim |
|---|---|---|---|
| 25 | 84.160 | 0.000 | 0.0% |

## Copilot grounding

Questions per system are `answered of asked`; those without a cached model reply are not run. Pooled over questions.

| system | questions answered | answers with an unsupported number | answers that are correct | answers stating a number |
|---|---|---|---|---|
| powerpilot_rules | 165 of 165 | 0.0% | 12.1% | 100.0% |
| powerpilot_llm | 0 of 165 | n/a | n/a | n/a |
| powerpilot_llm_no_verifier | 0 of 165 | n/a | n/a | n/a |
| raw_llm | 0 of 165 | n/a | n/a | n/a |

## Reverse-engineering legacy reports

Pooled over cells. A planted mistake is detected when its cell is reported NOT_REPRODUCIBLE.

| system | reports | correct cells reproduced with the right formula | reproduced (any formula) | planted-mistake precision | planted-mistake recall | hints naming the right problem |
|---|---|---|---|---|---|---|
| full | 24 | 87.1% | 89.7% | 95.2% | 96.8% | 93.3% |
| no_reverse_consistency | 24 | 76.1% | 78.7% | 95.2% | 96.8% | 93.3% |
| no_reverse_gate | 24 | 87.1% | 89.7% | 95.2% | 96.8% | 93.3% |

## Wall-clock seconds

| system | runs | mean | median | max |
|---|---|---|---|---|
| pipeline:full | 25 | 1.43 | 0.66 | 11.40 |
| pipeline:no_kpi_verifier | 25 | 1.30 | 0.40 | 10.96 |
| reverse:full | 24 | 0.29 | 0.10 | 1.95 |
| reverse:no_reverse_consistency | 24 | 0.30 | 0.12 | 2.18 |
| reverse:no_reverse_gate | 24 | 0.26 | 0.08 | 1.84 |
