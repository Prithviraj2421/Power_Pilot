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
5. BusinessProfiler: measure/dimension taxonomy and executive briefing
6. DataIntelligenceEngine: trends, correlations, outliers, business-rule anomalies
7. InsightEngine: ranked insights and executive summary
8. RelationshipEngine: keys, hierarchies, semantic links
9. KPIEngine: recommended KPIs with DAX formulas
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

## Other layers
- `datasets/`: SQLite + CSV store in `backend/data/` is the source of truth; the result cache is performance only.
  Upload with `POST /api/v1/datasets`, then address everything by dataset id.
- `export_center/` (xlsx/pdf/docx/html), `services/powerbi_export_service.py` with `common/powerbi_names.py`
  (one table-name and DAX-escaping rule for measures, model and M script), `intelligence/llm/` (fact sheet + numeric
  verifier; any failure falls back to the rules copilot).

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
   resolved, omit the KPI or widget. Never invent a column.
2. Every number shown to a user must trace to a computation on their data: no made-up benchmarks, placeholder chart
   series, or LLM-written figures.
3. Keep plugins small (one concern) and register them in their package `__init__` registry.
4. Every bug fix ships a regression test, and you confirm it fails on the old code first.
5. pandas 3: string columns have dtype `str`, not `object`. Use `pd.api.types.is_string_dtype`.
6. Dates can be day-first (DD/MM/YYYY): use `common/date_parse.parse_dates_robust`, not bare `pd.to_datetime`.
7. Match keywords in column names with `common/keyword_match` (whole token), never substring `in`.
8. Never `rm -rf` anything under `backend/data/`: it is the live dataset registry.
9. Ask before pushing to GitHub.
