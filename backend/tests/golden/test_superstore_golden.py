"""Golden test: a Superstore export must yield DAX that only references its own columns.

Superstore is the dataset people actually try first, and it is awkward on purpose:
spaces and hyphens in column names (`Order ID`, `Sub-Category`), day-first dates
(`19/03/2024`), a numeric postal code that must never be summed, and a file name
with spaces. Before the KPI plugins resolved real columns they emitted
`SUM('x.csv'[Sales_Amount])` -- a table and a column that do not exist -- so every
exported measure failed in Power BI. This runs the full pipeline and checks every
asset a user can download against the dataset it came from.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.common.powerbi_names import dax_references, table_name
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline
from app.services.powerbi_export_service import PowerBIExportService

DATASET_NAME = "Sample - Superstore.csv"
TABLE = table_name(DATASET_NAME)

# The measures this dataset should produce. Pinned exactly: a change here is a
# deliberate change to KPI selection and should be reviewed as one.
EXPECTED_FORMULAS = {
    "Total Sales Revenue": f"SUM('{TABLE}'[Sales])",
    "Average Order Value (AOV)": f"DIVIDE(SUM('{TABLE}'[Sales]), DISTINCTCOUNT('{TABLE}'[Order ID]))",
    "Total Units Sold": f"SUM('{TABLE}'[Quantity])",
    "Active Customer Count": f"DISTINCTCOUNT('{TABLE}'[Customer ID])",
}


@pytest.fixture(scope="module")
def dataset() -> pd.DataFrame:
    return pd.read_csv(Path(__file__).with_name("superstore.csv"))


@pytest.fixture(scope="module")
def result(dataset: pd.DataFrame):
    return PowerPilotIntelligencePipeline().run_pipeline(dataset, dataset_name=DATASET_NAME)


def assert_references_resolve(expression: str, where: str, dataset: pd.DataFrame) -> None:
    references = dax_references(expression)
    assert references, f"{where}: no table/column reference found in {expression!r}"
    for table, column in references:
        assert table == TABLE, f"{where}: refers to table {table!r}, the model's table is {TABLE!r}"
        assert column in dataset.columns, f"{where}: refers to column {column!r}, which the dataset does not have"


def test_the_fixture_is_the_awkward_superstore_shape(dataset: pd.DataFrame) -> None:
    assert {"Order ID", "Sub-Category", "Postal Code"} <= set(dataset.columns)
    assert dataset["Order Date"].str.slice(0, 2).astype(int).max() > 12, "dates must be day-first"
    assert dataset["Order ID"].duplicated().any(), "orders must span several rows"


def test_every_kpi_formula_references_existing_columns(result, dataset: pd.DataFrame) -> None:
    kpis = result.kpi_report.all_kpis
    assert kpis, "no KPIs produced: this test would otherwise pass vacuously"
    for kpi in kpis:
        assert_references_resolve(kpi.formula, f"KPI '{kpi.name}'", dataset)


def test_every_measure_in_the_dax_script_references_existing_columns(result, dataset: pd.DataFrame) -> None:
    script = PowerBIExportService.generate_dax_script(result.kpi_report, DATASET_NAME)
    measures = [line for line in script.splitlines() if line and not line.startswith("//")]
    assert len(measures) == len(result.kpi_report.all_kpis)
    for line in measures:
        assert_references_resolve(line.split(" = ", 1)[1], f"DAX script line {line!r}", dataset)


def test_every_measure_in_the_bim_references_existing_columns(result, dataset: pd.DataFrame) -> None:
    bim = PowerBIExportService.generate_tabular_model_bim(
        result.dataset_profile, result.kpi_report, result.relationship_report
    )
    table = bim["model"]["tables"][0]
    assert table["name"] == TABLE
    assert table["measures"], "the model has no measures"
    for measure in table["measures"]:
        assert_references_resolve(measure["expression"], f"BIM measure '{measure['name']}'", dataset)


def test_superstore_gets_exactly_the_expected_measures(result) -> None:
    produced = {kpi.name: kpi.formula for kpi in result.kpi_report.all_kpis}
    assert produced == EXPECTED_FORMULAS


def test_postal_code_and_row_id_are_never_summed(result) -> None:
    for kpi in result.kpi_report.all_kpis:
        assert "Postal Code" not in kpi.formula and "Row ID" not in kpi.formula
