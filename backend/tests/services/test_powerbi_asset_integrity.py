"""Integrity checks for the generated Power BI assets.

The assets used to look right and be unusable: DAX measures referenced columns the
dataset does not have (`Sales_Amount`, `Gross_Revenue`...), used `'file.csv'` as the
table name while the model called it `file`, and the .bim contained a property
Microsoft's own parser rejects. These tests check every reference in every asset
against the model they would be loaded into.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.common.powerbi_names import powerbi_table_name
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.relationship_models import EntityRelationship, RelationshipReport
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline
from app.services.powerbi_export_service import PowerBIExportService

_REF = re.compile(r"'((?:[^']|'')+)'\[((?:[^\]]|\]\])+)\]")
_DATA_TYPES = {"int64", "double", "string", "dateTime", "boolean"}


def dax_references(expression: str) -> list[tuple[str, str]]:
    return [(t.replace("''", "'"), c.replace("]]", "]")) for t, c in _REF.findall(expression)]


def messy_superstore() -> tuple[pd.DataFrame, str]:
    """Column and file names with spaces, hyphens and brackets -- all legal in a real export."""
    df = pd.DataFrame(
        {
            "Order ID": [f"CA-{i:04d}" for i in range(60)],
            "Customer ID": [f"C{i % 12:03d}" for i in range(60)],
            "Order Date": pd.date_range("2024-01-01", periods=60).strftime("%d/%m/%Y"),
            "Sub-Category": ["Chairs", "Tables", "Phones"] * 20,
            "Region": ["East", "West", "North", "South"] * 15,
            "Quantity": [(i % 5) + 1 for i in range(60)],
            "Sales": [round(20 + (i * 7.3) % 400, 2) for i in range(60)],
            "Profit": [round(-10 + (i * 3.1) % 90, 2) for i in range(60)],
        }
    )
    return df, "Sample - Superstore.csv"


@pytest.fixture(scope="module")
def runs() -> list[tuple[str, pd.DataFrame, object]]:
    pipeline = PowerPilotIntelligencePipeline()
    datasets = Path(__file__).parents[1] / "datasets"

    cases = [(f"{n}.csv", pd.read_csv(datasets / f"{n}.csv")) for n in ("retail", "finance", "hr", "healthcare")]
    df, name = messy_superstore()
    cases.append((name, df))
    return [(name, df, pipeline.run_pipeline(df, dataset_name=name)) for name, df in cases]


def test_every_kpi_formula_references_a_real_table_and_column(runs) -> None:
    for name, df, result in runs:
        assert result.kpi_report.all_kpis, f"{name} produced no KPIs"
        for kpi in result.kpi_report.all_kpis:
            refs = dax_references(kpi.formula)
            assert refs, f"{name}: '{kpi.formula}' references no column"
            for table, column in refs:
                assert table == powerbi_table_name(name), f"{name}: formula uses table '{table}'"
                assert column in df.columns, f"{name}: '{column}' is not a column ({kpi.formula})"


def test_bim_is_structurally_consistent_with_its_own_measures(runs) -> None:
    for name, df, result in runs:
        bim = PowerBIExportService.generate_tabular_model_bim(
            result.dataset_profile, result.kpi_report, result.relationship_report
        )
        model = bim["model"]
        assert len(model["tables"]) == 1
        table = model["tables"][0]
        assert table["name"] == powerbi_table_name(name)
        assert [c["name"] for c in table["columns"]] == list(df.columns)
        assert {c["dataType"] for c in table["columns"]} <= _DATA_TYPES
        assert sum(1 for c in table["columns"] if c.get("isKey")) <= 1

        assert model["relationships"] == [], "a single table cannot be related to itself"
        assert len(table["partitions"]) == 1, f"{name}: without a partition the table has no data"
        assert table["partitions"][0]["source"]["type"] == "m"

        columns = {c["name"] for c in table["columns"]}
        for measure in table["measures"]:
            for ref_table, ref_column in dax_references(measure["expression"]):
                assert ref_table == table["name"]
                assert ref_column in columns


def test_dax_script_measures_resolve_against_the_dataset(runs) -> None:
    for name, df, result in runs:
        script = PowerBIExportService.generate_dax_script(result.kpi_report, name)
        defined = [line for line in script.splitlines() if " = " in line and not line.startswith("//")]
        assert len(defined) == len(result.kpi_report.all_kpis)
        for line in defined:
            for table, column in dax_references(line):
                assert table == powerbi_table_name(name)
                assert column in df.columns


def test_power_query_script_has_no_machine_specific_path_and_reads_quoted_csv(runs) -> None:
    for name, df, result in runs:
        m = PowerBIExportService.generate_power_query_m(result.dataset_profile)
        assert "C:\\Users" not in m, "a real user's folder must never be baked into the script"
        assert "FilePath" in m
        assert "QuoteStyle.Csv" in m, "QuoteStyle.None splits any quoted field containing a comma"
        for column in df.columns:
            assert f'"{column}"' in m, f"{name}: column '{column}' is not typed in the M script"


def _profile(*cols: tuple) -> DatasetProfile:
    columns = [
        ColumnProfile(
            name=n, physical_type=t, nullable=False, unique=u, identifier=ident,
            missing_count=missing, unique_count=10,
        )
        for n, t, ident, u, missing in cols
    ]
    return DatasetProfile(dataset_name="t.csv", total_rows=10, total_columns=len(columns), columns=columns)


def test_m_script_types_decimals_as_numbers_not_integers() -> None:
    profile = _profile(("amount", PhysicalType.DECIMAL, False, False, 0))
    assert '{"amount", type number}' in PowerBIExportService.generate_power_query_m(profile)


def test_m_script_does_not_round_integer_columns_that_cleaning_filled() -> None:
    # Gaps are imputed with a median, which can be x.5; Int64 would silently round it.
    profile = _profile(
        ("complete", PhysicalType.INTEGER, False, False, 0),
        ("had_gaps", PhysicalType.INTEGER, False, False, 3),
    )
    m = PowerBIExportService.generate_power_query_m(profile)
    assert '{"complete", Int64.Type}' in m
    assert '{"had_gaps", type number}' in m


def test_m_script_escapes_quotes_in_column_names() -> None:
    profile = _profile(('the "best" column', PhysicalType.TEXT, False, False, 0))
    m = PowerBIExportService.generate_power_query_m(profile)
    assert '{"the ""best"" column", type text}' in m


def test_m_script_honours_a_supplied_file_path() -> None:
    profile = _profile(("a", PhysicalType.TEXT, False, False, 0))
    m = PowerBIExportService.generate_power_query_m(profile, file_path="D:\\data\\mine.csv")
    assert 'FilePath = "D:\\data\\mine.csv"' in m


def test_bim_marks_only_one_unique_identifier_as_key() -> None:
    profile = _profile(
        ("order_id", PhysicalType.INTEGER, True, True, 0),
        ("customer_id", PhysicalType.INTEGER, True, True, 0),
        ("region_code", PhysicalType.INTEGER, True, False, 0),
    )
    columns = PowerBIExportService.generate_tabular_model_bim(profile)["model"]["tables"][0]["columns"]
    assert [c["name"] for c in columns if c.get("isKey")] == ["order_id"]


def test_bim_keeps_detected_relationships_as_a_note_not_as_self_joins() -> None:
    profile = _profile(
        ("order_id", PhysicalType.INTEGER, True, True, 0),
        ("customer_id", PhysicalType.INTEGER, True, False, 0),
    )
    report = RelationshipReport(
        all_relationships=(
            EntityRelationship("order_id", "customer_id", "FOREIGN_KEY", "ONE_TO_MANY", 0.9, "r"),
        ),
        domain=DatasetDomain.RETAIL,
    )
    model = PowerBIExportService.generate_tabular_model_bim(profile, relationship_report=report)["model"]

    assert model["relationships"] == []
    note = model["annotations"][0]
    assert note["name"] == "PowerPilot_DetectedRelationships"
    assert "order_id -> customer_id" in note["value"]


def test_m_script_blanks_cells_that_fail_the_type_cast() -> None:
    # e.g. a "total_sqft" column that is 96% numeric with a few ranges like "2100-2850".
    profile = _profile(
        ("label", PhysicalType.TEXT, False, False, 0),
        ("total_sqft", PhysicalType.FLOAT, False, False, 0),
    )
    m = PowerBIExportService.generate_power_query_m(profile)

    assert '#"Replaced Errors" = Table.ReplaceErrorValues(#"Changed Type", {{"total_sqft", null}})' in m
    assert '"label", null' not in m, "text columns cannot fail a cast, so they are left alone"
    assert m.rstrip().endswith('#"Replaced Errors"')


def test_m_script_for_an_all_text_dataset_has_no_error_step() -> None:
    profile = _profile(("a", PhysicalType.TEXT, False, False, 0))
    m = PowerBIExportService.generate_power_query_m(profile)

    assert "Replaced Errors" not in m
    assert m.rstrip().endswith('#"Changed Type"')


def test_dax_script_shows_each_verified_value_readably_and_lists_rejections(runs) -> None:
    from dataclasses import replace

    name, df, result = next(r for r in runs if r[0] == "retail.csv")
    revenue = next(k for k in result.kpi_report.all_kpis if k.name == "Total Sales Revenue")
    rejected = replace(revenue, name="Average Basket", verified=False, computed_value=None,
                       verification_note="column 'basket' is not in the dataset")
    report = replace(result.kpi_report, rejected_kpis=(rejected,))

    script = PowerBIExportService.generate_dax_script(report, name)

    assert f"// Verified value: {revenue.computed_value:,.0f}" in script
    assert "e+" not in script
    assert "// Rejected KPIs" in script and "//   - Average Basket: column 'basket' is not in the dataset" in script
    assert "Average_Basket =" not in script, "a rejected KPI must never be exported as a measure"

    bim = PowerBIExportService.generate_tabular_model_bim(result.dataset_profile, report)
    note = next(a for a in bim["model"]["annotations"] if a["name"] == "PowerPilot_RejectedKPIs")
    assert "Average Basket" in note["value"]
    assert all(m["name"] != "Average_Basket" for m in bim["model"]["tables"][0]["measures"])
