# PowerPilot as a Power BI Desktop External Tool

PowerPilot adds a button to Power BI Desktop's **External Tools** ribbon. Clicking it opens PowerPilot attached to
the report you have open. It reads the model's tables, runs the analysis, verifies each KPI against **Power BI's own
engine**, and adds only the KPIs that match to your report as measures. Windows only.

```
 Power BI Desktop ──click──▶ launcher.py "%server%" "%database%"
        │                         │  starts one backend per open model (127.0.0.1, random port, random token)
        │                         ▼
        │                    PowerPilot backend  ── serves the built UI at /live
        │                         │
        └── local Analysis ◀──────┘  TOM (structure, write measures) + ADOMD (DAX) through pythonnet
            Services (the model)
```

## Requirements

- Windows with Power BI Desktop installed (the External Tools ribbon is not available in Power BI Report Server's Desktop).
- Python 3.12, with PowerPilot's backend environment: `backend\.venv`.
- `pythonnet`, installed from the optional requirements file (it is not needed for anything else).
- The built frontend: `frontend\dist` (the backend serves it, so no dev server is needed).

## Where the Analysis Services libraries come from

PowerPilot talks to the model with Microsoft's own client libraries. **They ship with Power BI Desktop**, so nothing is
downloaded and they are always the same build as the engine they talk to:

| Library | File in `…\Microsoft Power BI Desktop\bin` | Used for |
| --- | --- | --- |
| Tabular Object Model (TOM) | `Microsoft.PowerBI.Tabular.dll` (+ `Microsoft.PowerBI.Tabular.Json.dll`) | reading tables and measures, adding measures |
| ADOMD.NET | `Microsoft.PowerBI.AdomdClient.dll` | running DAX queries |

`app/powerbi_live/dll_locator.py` looks for a folder containing all three files, in this order:

1. `POWERPILOT_TOM_DLL_DIR`, if set.
2. The install location Desktop's installer records in the registry.
3. `%ProgramFiles%`, `%ProgramFiles(x86)%` and `%LOCALAPPDATA%` under `Microsoft Power BI Desktop\bin`.

If none has them, the error lists every folder tried. To use a different copy, for example the NuGet packages
`Microsoft.AnalysisServices.retail.amd64` and `Microsoft.AnalysisServices.AdomdClient.retail.amd64`, point
`POWERPILOT_TOM_DLL_DIR` at a folder containing the three DLL names above.

## Install

From a normal PowerShell, in the repository root:

```powershell
cd frontend; npm install; npm run build; cd ..
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-powerbi.txt
```

Then **from an administrator PowerShell** (the registration folder is machine-wide):

```powershell
powershell -ExecutionPolicy Bypass -File tools\powerbi-external-tool\install.ps1
```

It checks that the interpreter, the built UI and `pythonnet` exist, fills in the absolute paths Desktop requires, and
writes `PowerPilot.pbitool.json` to
`C:\Program Files (x86)\Common Files\Microsoft Shared\Power BI Desktop\External Tools`. Restart Power BI Desktop.
Use `-TargetDir <folder>` to preview the file without administrator rights. To remove it, run `uninstall.ps1`
(measures already added to a report stay: they are ordinary measures).

## Settings

The launcher sets these for the backend it starts. They are read from the environment (`POWERPILOT_` prefix).

| Variable | Meaning |
| --- | --- |
| `PBI_SERVER`, `PBI_DATABASE` | The open model, from Desktop's `%server%` / `%database%`. Must be `localhost:<port>`. |
| `PBI_TOKEN` | Per-launch secret the UI must send as `X-PowerPilot-Token`. |
| `PBI_MAX_ROWS` | Rows read per table (default 500,000). A larger table is analysed as a sample. |
| `TOM_DLL_DIR` | Folder holding the Analysis Services libraries (see above). |
| `SERVE_FRONTEND` | The built UI directory the backend serves. |
| `PBI_WATCH_INTERVAL_SECONDS`, `PBI_WATCH_FAILURES` | The server stops once the model's port has refused connections this many checks in a row (default every 5 s, 3 times). |

## How long the server lives

One server runs per open model and stops when that model goes away. It watches the model's own port (the Analysis Services engine Desktop started for the report) and stops once it has refused connections three checks in a row. It deliberately does **not** watch the process that launched it: Power BI Desktop starts external tools through a short-lived helper process, so that process exits within seconds of every launch while the report is still open. (An early version watched it and shut down five seconds after launching; `tests/powerbi_live/test_model_watchdog_process.py` is the regression test.)

## What protects your report

- The server listens on `127.0.0.1` only. The model address comes from the launcher, never from a request, and must be loopback.
- Every `/api/v1/powerbi-live/*` call needs the session token. The token travels in the URL **fragment**, which browsers never send to a server.
- The write endpoint takes KPI **ids**, never DAX. The server looks up the verified formula itself.
- A measure is added only after Power BI's engine returns the same value PowerPilot computed (relative tolerance 1e-6).
- Existing measures are never modified or deleted. A name that is already taken is skipped and reported.
- A table read only partly (over the row limit) or changed since the analysis is refused: its value could not be compared like for like.
- Measures are added in one transaction with `SaveChanges()`: all of them, or none.
- KPIs are verified on the rows the model holds (not on a cleaned copy), because that is what the engine computes over.

## Manual test checklist

The automated tests use a fake model, so **this is the only check against a real Power BI engine.** Use any report
with a few tables and at least one numeric column, and note what each step shows.

1. **Install.** Run `install.ps1` as administrator. Expect "Registered PowerPilot" and the file path. Restart Desktop.
2. **Ribbon.** Open a `.pbix`. The **External Tools** ribbon has a blue **PowerPilot** button. *(If it does not: see Troubleshooting.)*
3. **Launch.** Click it. A browser tab opens at `http://127.0.0.1:<port>/live?...`. Expect "Connected to your open model on localhost:<port>" and your tables, with the largest preselected. The address bar must not show `#token=`.
4. **Tables.** Row and column counts match the Data pane. Auto date tables (`LocalDateTable_…`) are not listed.
5. **Analyze.** Click **Analyze selected**. Note the time for your biggest table (record rows and seconds: this is the unmeasured part). Expect KPIs with values, formulas using your real table and column names, and a "Verified" badge.
6. **Compare with Power BI.** For one KPI, make a card in Power BI with the same measure and compare the number with PowerPilot's. They should match.
7. **Check.** Select a KPI and click **Check against Power BI**. Expect "Matches Power BI" with equal values and **nothing added** (confirm in the Data pane).
8. **Add.** Click **Add N to my report**. Expect the success panel listing the measures. In Power BI, the measures appear under a **PowerPilot** display folder in the table's field list, with the right numbers when used in a visual.
9. **Existing measures untouched.** A measure you created beforehand, especially one named like a KPI, is unchanged, and PowerPilot reports it as skipped.
10. **Repeat.** Add the same KPI again: it is skipped as "already added", with no duplicate.
11. **Refused on change.** Analyze, then refresh the data (or load more rows) in Power BI, then try to add. Expect a refusal asking you to analyze again.
12. **Large table.** If you have a table over 500,000 rows: it is marked "sample only", and its KPIs cannot be selected.
13. **Save.** Press Ctrl+S in Power BI, close and reopen the report: the measures are still there. (Without saving they are lost, which is why the reminder is shown.)
14. **Second click.** Click the ribbon button again: the same backend is reused (same port) and the page reopens.
15. **Close the report.** Close the report (or Power BI Desktop). Within about 20 seconds the PowerPilot backend stops by itself (check Task Manager for the `python.exe` that was listening on that port). Reopening the page afterwards shows a message telling you to click the ribbon button again.
16. **Forget data.** Click **Forget this model's data**; the local copy is deleted (`backend\data\datasets`).
17. **Uninstall.** Run `uninstall.ps1` as administrator and restart Desktop: the button is gone.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| No PowerPilot button | Desktop was not restarted; `PowerPilot.pbitool.json` is not in the External Tools folder; the External Tools ribbon is disabled by policy (`EnableExternalTools = 0`). |
| A message box "PowerPilot's interface has not been built" | Run `npm run build` in `frontend\`. |
| "PowerPilot's server did not start" | The message box shows the end of the log; the full log is `%LOCALAPPDATA%\PowerPilot\live\backend-<port>.log`. |
| "Could not find the Analysis Services client libraries" | Desktop is not installed where expected: set `POWERPILOT_TOM_DLL_DIR`. |
| "PowerPilot needs the 'pythonnet' package" | `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-powerbi.txt`. |
| The page says "PowerPilot's background program is not running any more" (or just "Network Error" in an older build) | The server stopped: the report was closed, or the server crashed. Click PowerPilot on the External Tools ribbon again. If it keeps happening, the log in `%LOCALAPPDATA%\PowerPilot\live\backend-<port>.log` says why; a line ending in "is gone; shutting down" means it saw the model's port close. |
| "Power BI Desktop's model is not reachable. Is the report still open?" | The report was closed, or Desktop restarted (a new port is assigned each time): click the ribbon button again. |
| "This PowerPilot session has expired" (401) | The page was opened without the launcher's token: use the ribbon button. |
| Analyze is slow on a large table | Rows are read through pythonnet; lower `POWERPILOT_PBI_MAX_ROWS` or analyze fewer tables. |

## Known limits

- One table at a time: no KPIs that span tables or follow relationships.
- Not tested with DirectQuery or composite models, or with row-level security roles. Import-mode models are the intended case.
- Add-only: PowerPilot has no "undo". Measures it adds carry the annotation `PowerPilot_KpiId` and live in the `PowerPilot` display folder, so they are easy to find and delete in Power BI.
- A copy of the rows PowerPilot reads is stored in the local data directory until you use **Forget this model's data**.
