# PowerPilot evaluation harness

A reproducible benchmark, separate from the unit tests. `python -m eval.run` writes one CSV per metric and `summary.md`
into `eval/results/`.

```
python -m eval.datasets.download     # fetch the datasets (needs network); pins licence + sha256 in manifest.lock.json
python -m eval.labels.build_labels   # rewrite eval/labels/*.json from eval/labels/build_labels.py (committed already)
python -m eval.reports.generate      # synthetic legacy reports + truth sidecars (also done inside the run)
python -m eval.run                   # everything deterministic, model-backed systems from the cache
python -m eval.run --llm-mode record # also call the model (ANTHROPIC_API_KEY) and cache every reply in eval/cache/llm.jsonl
```

## What is measured

| metric | file | how |
|---|---|---|
| semantic-type accuracy, F1 on labelled columns, ECE | `semantic_type.csv`, `semantic_columns.csv` | PowerPilot's column types and confidences vs `labels/*.json` |
| domain accuracy and ECE | `domain.csv` | detected domain and confidence vs the domain label |
| KPI validity, value accuracy, recovery of hand-computed KPIs | `kpi.csv`, `kpi_items.csv`, `kpi_truth.csv` | every emitted KPI's DAX is executed by an *independent* evaluator (`tests/kpi/dax_oracle.py`) on the frame the model holds; recovery compares to hand-written pandas on the raw file |
| false-insight rate | `insights.csv` | each column shuffled independently (fixed seed); any CORRELATION or TREND insight on the copy is false by construction |
| copilot grounding | `copilot.csv` | fixed generic question set; an answer's numbers are checked against every fact true of the dataset (plus, for pipeline systems, the numbers in its own fact sheet) |
| reverse-engineering | `reverse.csv`, `reverse_cells.csv` | % of correct cells reproduced with the right formula; planted-mistake precision/recall; hint accuracy |
| wall-clock | `timing.csv` | per dataset, per system |

Systems (`eval/systems.py`): `full`; `no_kpi_verifier` (the verify gate replaced by one that approves everything);
`no_copilot_verifier` (the numeric-claim verifier approves everything); `no_reverse_consistency`; `no_reverse_gate`;
and the baseline `raw_llm` (the model sees the CSV head and the question only). Ablations patch the single checking function
inside a context manager; the product code is untouched.

## Datasets (25)

20 public datasets from the UCI Machine Learning Repository, plus the repository's own four synthetic samples and the
Superstore-shaped golden fixture. The licence of each UCI dataset is read from its own page by `download.py` and stored in
`datasets/manifest.lock.json` next to the sha256 of the file used (all are CC BY 4.0). Files above 20,000 rows are sampled with
a fixed seed, so everyone gets the same rows. Files are not committed (`datasets/raw/` is ignored); the lock lets you check you
have the same ones.

## Labels, and how far to trust them

Columns were labelled by one person (the assistant that wrote this harness) from column names and values, using the written
rules at the top of `labels/build_labels.py`, **before** the pipeline was run on them. They are not a consensus of annotators.
The taxonomy is the product's own (customer, product, revenue, profit, cost, quantity, date, region, employee, identifier,
unknown), so most columns of non-business datasets are `unknown`, and a benchmark on 20 UCI tables says more about how well
PowerPilot *declines* to over-interpret than about how well it reads retail data. Domain labels are judgement calls for several
datasets (`domain_label_confidence: medium` in the label file). The synthetic samples were written alongside the pipeline, so
they are in-distribution; read their results separately.

## Known limits of this run

* **No model-backed result exists yet.** There was no API key when this was built and `eval/cache/llm.jsonl` is empty, so
  `raw_llm`, `powerpilot_llm` and `powerpilot_llm_no_verifier` are reported **not run**, never estimated. `--llm-mode record`
  fills the cache once; reruns are then free.
* `no_kpi_verifier` and `no_reverse_gate` currently change nothing: the KPI plugins only propose KPIs on columns that resolve,
  and on these datasets the reverse search's own numbers always survive `verify()`. Those gates matter against inputs this
  benchmark does not contain (bad columns, formulas the search cannot compute); the ablation says so honestly instead of
  manufacturing a difference.
* Reverse-engineering reports exist only for the 12 datasets that have a text column with 3 to 8 values and enough numeric
  precision; the rest are skipped. Some mistakes cannot be planted meaningfully on some data (the generator records which).
* Copilot "unsupported number" ignores whole numbers up to 10 and accepts any rounding at the precision written.
* Only the shuffled-column test measures false relationship claims; it does not measure missed true ones.
