# Prove-It Migration

You have an old report (an Excel file, a CSV, or a PDF with tables) whose numbers nobody can explain, and the data behind it.
PowerPilot finds the formula behind **every** number, **proves** each one by recomputing it on your data, and flags the numbers
it cannot reproduce. Those are often real mistakes in the old report. What is proven can be added to your Power BI report as
measures.

## What you get

For every number in the report, one of four results:

| Result | Meaning |
|---|---|
| **Reproduced** (green) | A formula built from the report's own labels and your data's columns gives exactly this number, at the precision the report shows. Shown with the formula in plain words, its DAX, the recomputed value, and how strong the evidence is. |
| **Several formulas fit** (amber) | More than one different formula gives this number and nothing in the report or its neighbours tells them apart (for example `Customer ID` and `Customer Name` both give 12). All are listed. Nothing is added to Power BI for these. |
| **Not reproduced** (red) | No formula does. If the other numbers under the same heading follow one rule, that rule's value is shown as the *closest*, plus a plain-English hint: two digits swapped, one order left out, a whole region missing, a units slip, off by one. |
| **Calculated in the report** (grey) | A `=SUM(...)` cell or a "Total" row or column. It is checked against its own parts, and against the data: a total that adds up but disagrees with the data tells you a number it sums is wrong. |

"Not reproduced" is not "wrong": the old report may have used data you no longer have. It is a list of numbers worth a look.

## How to use it

**With an uploaded dataset:** upload your data in PowerPilot as usual, open the **Prove-It Migration** tab, choose the old report,
click **Find the formulas**. Click any number for its story. Download the proven measures as `.dax` or `.bim`.

**Inside Power BI Desktop:** open your report, click PowerPilot on the External Tools ribbon (see `powerbi-external-tool.md`), find
the **Prove-It Migration** section, pick the table that holds the data behind the old report, choose the old report and run it.
Then **Check against Power BI** (Power BI's own engine recomputes every number; nothing is written) and
**Add proven measures to Power BI**. Save the report (Ctrl+S) to keep them.

Supported reports: `.xlsx` / `.xlsm` (the numbers are read at the precision the cell shows), `.csv`, and PDFs whose tables are real
text (a scan or a picture of a table cannot be read). Numbers are understood as people write them: `1.2M`, `12.5%`,
`₹1,24,500`, `(1,200)`, `1.234,56`.

## What makes it trustworthy

* **The model proposes, the executor proves.** The search (and the optional language model) only *propose* formulas. A number is
  Reproduced only when the same compilers that write the Power BI measures recompute the formula on the raw data and land on the
  number the report shows. A hint is never a match.
* **Precision, not wishful rounding.** A report that shows `1.2M` is matched within half of the last digit shown (±50,000), not
  within a loose percentage.
* **Small numbers are honest.** `12` customers fits several columns by chance, so those cells come back as *several formulas fit*
  unless the report's wording or its neighbours settle it (Customer ID explaining all three segments while Customer Name explains
  two of them).
* **Raw data first.** A number that only matches the *cleaned* data is marked as such and is never offered as a measure: the
  model holds the raw rows, so Power BI's engine would disagree.
* **No data leaves the machine for the language model.** If an Anthropic key is configured, the model sees only column names, the
  labels around one number, and its unit. Its suggestions are parsed through a whitelist and proven like any other.

## What is written to your report

Only numbers proven on the raw data. Numbers that follow one rule collapse into **one measure** (`Total Sales`), because a visual
supplies the region and year: the filters that vary from number to number are dropped, the ones that never change are kept. The
measure itself and **each** of the numbers it reproduces are run through Power BI's engine first. Measures go in the display folder
`PowerPilot\Migrated`.

It is add-only, like KPIs: a measure whose name exists is left untouched, a table that changed since the analysis (or was only read
as a sample) is refused, and the server accepts measure ids, never DAX from the browser.

## Where the code is

`backend/app/reverse/`: `numbers.py` (reading shown numbers), `report_reader.py` + `grid.py` + `formulas.py` (xlsx/csv/pdf into
labelled numbers), `hypotheses.py` (what labels say), `index.py` + `synthesizer.py` (the search), `consistency.py` (neighbours),
`diagnostics.py` (hints), `proposer.py` (optional model), `engine.py` (the whole report), `migration.py` (measures),
`service.py` (store + orchestration). The IR gained date-part filters (`YEAR/QUARTER/MONTH`) and several filters per measure.

Endpoints: `POST /api/v1/datasets/{id}/reverse-engineer`, `GET /api/v1/reverse/{id}[/dax|/bim]`,
`POST /api/v1/powerbi-live/reverse-engineer`, `POST /api/v1/powerbi-live/reverse-engineer/apply`.

Tests: `backend/tests/reverse/` generates a legacy report from the golden Superstore data with known formulas and three planted
mistakes (`legacy_reports.py`), as `.xlsx`, `.csv` and `.pdf`.

## Limits worth knowing

* Dates stored as text depend on Power BI's locale for `YEAR()`; the engine check refuses any measure Power BI computes differently.
* PDF extraction is best effort; tables without clear structure can be misread.
* Very large tables are bounded by a search time budget (90 s by default, `POWERPILOT_REVERSE_TIME_BUDGET_SECONDS`); if it runs out
  the summary says so.
* A small number can honestly stay ambiguous. That is the tool refusing to guess.
