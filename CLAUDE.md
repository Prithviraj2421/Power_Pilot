# PowerPilot

CSV in, out comes a verified Power BI model (`.bim` / `.dax` / `.m`), executive insights, and a grounded copilot.
Backend: Python 3.12 / FastAPI / pandas. Frontend: React 19 / TypeScript / Vite. Repo: Prithviraj2421/Power_Pilot.

## Pipeline
`backend/app/pipeline/intelligence_pipeline.py` -> `PowerPilotIntelligencePipeline.execute()` runs 11 engines, then
assembles the result (the docstring says "12 stages"; the 12th is the assembly). Later stages see only the cleaned frame.
1. DQPE: assess quality, then clean (`app/data_quality/`)
2. SchemaAnalyzer: physical type per column
3. EntityDetector: semantic types (revenue, customer, date...) written onto each column profile
4. DomainClassifier: retail/finance/hr/healthcare/marketing/logistics, else `unknown` below `min_domain_confidence`
5. KPIEngine: IR -> DAX + pandas, verified against the data; unverified KPIs go to `rejected_kpis` (runs before 6 so
   everything downstream only ever sees verified KPIs)
6. BusinessProfiler: measure/dimension taxonomy and briefing (its KPI lists are replaced by the verified ones)
7. DataIntelligenceEngine: trends, correlations, outliers, business-rule anomalies
8. InsightEngine: ranked insights and executive summary
9. RelationshipEngine: keys, hierarchies, semantic links
10. DashboardEngine: tabs and widgets
11. DecisionEngine: recommended actions
12. Assemble `MasterIntelligenceResult` (plus the cleaned DataFrame, used by exports)

## Engine pattern (`backend/app/intelligence/`)
- Each engine is a facade `<name>_engine.py` + an ABC `<area>/base_*.py` + small plugins + a tuple registry.
- The registry is `*_REGISTRY` in the plugin package `__init__.py` (e.g. `KPI_RECOMMENDATION_REGISTRY`). Adding a plugin
  means one new file and one tuple entry; the facade instantiates from the registry, so nothing else is wired.
- KPI, dashboard and decision engines pick a plugin by `target_domain`, use a `Fallback*` plugin for `unknown`, and fall
  back again when the domain plugin yields nothing. Entity, insight, data-intelligence and relationship engines run
  every registered plugin.
- Column resolution is shared: `intelligence/kpi/column_resolver.py`, `intelligence/dashboard/builder.py`.
- KPIs: plugins return `KPICandidate`s holding an IR expression (`kpi/ir.py`), never a formula string. `kpi_engine.py`
  compiles it with `kpi/compilers/` (DAX and pandas, which must agree), `kpi/verification.py` gates it, and
  `kpi/baseline.py` derives the benchmark from the data. Optional DAX-engine check: `POWERPILOT_DAX_ENGINE_CHECK`.

## Other layers
- `datasets/`: SQLite + CSV store in `backend/data/` is the source of truth; the result cache is performance only.
  Upload with `POST /api/v1/datasets`, then address everything by dataset id.
- `powerbi_live/` + `routes/powerbi_live_route.py` + `tools/powerbi-external-tool/`: PowerPilot as a Power BI Desktop External
  Tool (see `docs/powerbi-external-tool.md`). `ModelConnector` is the seam: `TomAdomdConnector` (pythonnet, Desktop's own DLLs,
  Windows only, imported lazily) in production, `tests/powerbi_live/fake_connector.py` in CI. KPIs there are verified on the model's
  raw rows and written back only if Power BI's engine returns the same value.
- `reverse/` + `routes/reverse_route.py` (+ live endpoints in `powerbi_live_route.py`): Prove-It Migration, reverse-engineering a
  legacy xlsx/csv/pdf report into proven formulas (see `docs/prove-it-migration.md`). The search only *proposes*; `verify()` proves.
  Hints (`diagnostics.py`) never become matches. Proven cells become measures via `migration.py`, written by the same engine-checked
  `LiveModelService` writer as KPIs. The IR has date-part filters (`DatePart`) and `Measure.filters` (a tuple).
- `export_center/` (xlsx/pdf/docx/html), `services/powerbi_export_service.py` with `common/powerbi_names.py`
  (one table-name and DAX-escaping rule for measures, model and M script), `intelligence/llm/` (fact sheet with a
  stable id and meaning per number + citation verifier: every number the model writes must carry its fact id and match that fact's
  value, unit and meaning; the tags are stripped and returned as `citations`; any failure falls back to the rules copilot).

## Run
```
cd backend && .venv/Scripts/python.exe -m pytest                                # pytest.ini sets pythonpath/testpaths
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
cd frontend && npm run test      # also: npm run lint, npm run build (runs tsc -b), npm run dev (:3000, proxies /api)
cd frontend && npx tsc -b --noEmit    # not plain `tsc --noEmit`: root tsconfig has files: [], so that checks nothing
```
CI (`.github/workflows/ci.yml`): backend on Python 3.12 and 3.13, frontend, and `npm audit` at high severity.

## Rules
1. Never hardcode column names. Resolve roles through detected entities / `ColumnResolver`; if a role cannot be
   resolved, omit the KPI or widget. Never invent a column. Build KPIs as IR, never as DAX/format strings.
2. Every number shown to a user must trace to a computation on their data: no made-up benchmarks, placeholder chart
   series, or LLM-written figures. A KPI is shown or exported only if `verified`; a target is data-derived or labelled
   "Example target".
3. Keep plugins small (one concern) and register them in their package `__init__` registry.
4. Every bug fix ships a regression test, and you confirm it fails on the old code first.
5. pandas 3: string columns have dtype `str`, not `object`. Use `pd.api.types.is_string_dtype`.
6. Dates can be day-first (DD/MM/YYYY): use `common/date_parse.parse_dates_robust`, not bare `pd.to_datetime`.
7. Match keywords in column names with `common/keyword_match` (whole token), never substring `in`.
8. Never `rm -rf` anything under `backend/data/`: it is the live dataset registry.
9. Ask before pushing to GitHub.
10. Anything that writes into a user's Power BI model must be add-only, token-guarded, and take KPI ids, never client DAX.
11. A formula is only ever believed after `verify()` recomputes it; models and heuristics propose, hints explain, neither decides.
