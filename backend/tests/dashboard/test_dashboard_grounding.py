"""Every column a dashboard names must exist in the dataset it was built for.

The domain plugins used to hardcode canonical names (`Store_ID`, `Order_Date`,
`Ledger_Account`...), so a real file's dashboard advertised filters and chart
axes that were not in the data, and a chart whose column was missing was silently
drawn from some other numeric column.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

_GRAINS = {"Year", "Quarter", "Month"}


def _dataset(name: str) -> pd.DataFrame:
    return pd.read_csv(Path(__file__).parents[1] / "datasets" / f"{name}.csv")


def _sensors() -> pd.DataFrame:
    """No business domain at all: a unit-less IoT feed with an ID and a postal-style code."""
    return pd.DataFrame(
        {
            "reading_id": range(1, 61),
            "site_code": [10000 + (i % 4) for i in range(60)],
            "station": ["north", "south", "east", "west"] * 15,
            "recorded_at": pd.date_range("2024-01-01", periods=60).strftime("%Y-%m-%d"),
            "temperature_c": [15 + (i % 9) * 0.7 for i in range(60)],
            "humidity_pct": [40 + (i % 11) * 1.3 for i in range(60)],
        }
    )


def _messy_superstore() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Order ID": [f"CA-{i:04d}" for i in range(60)],
            "Customer ID": [f"C{i % 12:03d}" for i in range(60)],
            "Order Date": pd.date_range("2024-01-01", periods=60).strftime("%d/%m/%Y"),
            "Sub-Category": ["Chairs", "Tables", "Phones"] * 20,
            "Region": ["East", "West", "North", "South"] * 15,
            "Quantity": [(i % 5) + 1 for i in range(60)],
            "Sales": [round(20 + (i * 7.3) % 400, 2) for i in range(60)],
        }
    )


@pytest.fixture(scope="module")
def runs() -> list[tuple[str, pd.DataFrame, object]]:
    pipeline = PowerPilotIntelligencePipeline()
    cases = [(f"{n}.csv", _dataset(n)) for n in ("retail", "finance", "hr", "healthcare")]
    cases += [("Sample - Superstore.csv", _messy_superstore()), ("sensors.csv", _sensors())]
    return [(name, df, pipeline.run_pipeline(df, dataset_name=name)) for name, df in cases]


def test_every_widget_column_exists_in_the_dataset(runs) -> None:
    for name, df, result in runs:
        for tab in result.dashboard_report.tabs:
            for widget in tab.widgets:
                for column in (widget.metric_column, widget.dimension_column):
                    assert column is None or column in df.columns, (
                        f"{name}: widget '{widget.title}' uses '{column}', which is not a column"
                    )


def test_filters_and_time_dimensions_are_real_columns(runs) -> None:
    for name, df, result in runs:
        report = result.dashboard_report
        for column in report.global_filters:
            assert column in df.columns, f"{name}: filter '{column}' is not a column"
        time_dims = list(report.time_intelligence_dimensions)
        if time_dims:
            assert time_dims[0] in df.columns, f"{name}: time dimension '{time_dims[0]}'"
            assert set(time_dims[1:]) <= _GRAINS


def test_every_dashboard_has_content_and_no_empty_tabs(runs) -> None:
    for name, _, result in runs:
        report = result.dashboard_report
        assert report.tabs, f"{name}: dashboard has no tabs"
        assert all(tab.widgets for tab in report.tabs), f"{name}: a tab has no widgets"


def test_kpi_cards_mirror_the_kpi_report(runs) -> None:
    for name, _, result in runs:
        cards = [w.title for w in result.dashboard_report.tabs[0].widgets if w.widget_type == "KPI_CARD"]
        expected = [k.name for k in result.kpi_report.primary_kpis][:4]
        assert cards == expected, f"{name}: dashboard cards disagree with the KPI tab"


def test_widgets_never_overlap_on_the_grid(runs) -> None:
    for name, _, result in runs:
        for tab in result.dashboard_report.tabs:
            cells = set()
            for w in tab.widgets:
                assert 1 <= w.grid_col and w.grid_col - 1 + w.grid_width <= 12, f"{name}: '{w.title}' overflows"
                for col in range(w.grid_col, w.grid_col + w.grid_width):
                    assert (w.grid_row, col) not in cells, f"{name}: '{w.title}' overlaps another widget"
                    cells.add((w.grid_row, col))


def test_retail_sample_gets_its_real_chart_axes(runs) -> None:
    result = next(r for n, _, r in runs if n == "retail.csv")
    charts = {w.widget_id: w for t in result.dashboard_report.tabs for w in t.widgets}

    assert charts["w_trend_rev"].metric_column == "sales_amount"
    assert charts["w_trend_rev"].dimension_column == "order_date"
    assert charts["w_cat_breakdown"].dimension_column == "category"
    assert "Store_ID" not in result.dashboard_report.global_filters


def test_unclassified_dataset_does_not_chart_ids_or_codes(runs) -> None:
    result = next(r for n, _, r in runs if n == "sensors.csv")
    charted = {w.metric_column for t in result.dashboard_report.tabs for w in t.widgets if w.widget_type != "KPI_CARD"}

    assert charted, "a dataset with real measures should still get a chart"
    assert charted.isdisjoint({"reading_id", "site_code"}), "summing an ID or a code is meaningless"
    assert charted <= {"temperature_c", "humidity_pct"}


def test_no_chart_is_repeated_across_a_dashboard(runs) -> None:
    # A mislabelled entity (Category tagged as a product) once produced the same
    # "Sales by Category" chart on both tabs; tables legitimately mirror a bar chart.
    for name, _, result in runs:
        seen = set()
        for tab in result.dashboard_report.tabs:
            for w in tab.widgets:
                if w.widget_type in ("KPI_CARD", "TABLE"):
                    continue
                key = (w.metric_column, w.dimension_column)
                assert key not in seen, f"{name}: '{w.title}' appears twice"
                seen.add(key)


def test_a_product_chart_needs_a_product_column(make_profile) -> None:
    from app.common.enums import DatasetDomain, PhysicalType
    from app.intelligence.dashboard.plugins.retail_dashboard_plugin import RetailDashboardPlugin

    profile = make_profile(
        "orders.csv", DatasetDomain.RETAIL,
        ("Category", PhysicalType.TEXT), ("Sales", PhysicalType.FLOAT),
    )
    titles = [w.widget_id for t in RetailDashboardPlugin().recommend(profile).tabs for w in t.widgets]

    assert "w_top_products" not in titles and "w_prod_table" not in titles
