"""The pipeline options a live Power BI model needs: its real table name, and verifying on raw data."""

import pandas as pd
import pytest

from app.common.powerbi_names import dax_references
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


@pytest.fixture(scope="module")
def pipeline() -> PowerPilotIntelligencePipeline:
    return PowerPilotIntelligencePipeline()


def revenue(result) -> object:
    return next(k for k in result.kpi_report.all_kpis if k.name == "Total Sales Revenue")


def test_formulas_name_the_models_real_table_not_a_sanitised_one(pipeline, retail_df: pd.DataFrame) -> None:
    result = pipeline.run_pipeline(retail_df, dataset_name="retail.csv", powerbi_table="Sales Data")

    tables = {t for k in result.kpi_report.all_kpis for t, _ in dax_references(k.formula)}
    assert tables == {"Sales Data"}
    assert "'Sales Data'[sales_amount]" in revenue(result).formula


def test_without_the_option_the_sanitised_file_name_is_used_as_before(pipeline, retail_df: pd.DataFrame) -> None:
    result = pipeline.run_pipeline(retail_df, dataset_name="Sales Data.csv")

    assert "'Sales_Data'[sales_amount]" in revenue(result).formula


def test_verifying_on_the_source_frame_matches_what_the_model_holds(pipeline, retail_df: pd.DataFrame) -> None:
    # A live model contains the raw rows: the sample has a duplicate row and gaps that cleaning removes.
    raw_total = float(retail_df["sales_amount"].sum())

    on_source = pipeline.run_pipeline(retail_df, dataset_name="r.csv", powerbi_table="Sales", verify_on="source")
    on_cleaned = pipeline.run_pipeline(retail_df, dataset_name="r.csv", powerbi_table="Sales", verify_on="cleaned")

    assert revenue(on_source).computed_value == pytest.approx(raw_total)
    assert revenue(on_cleaned).computed_value != pytest.approx(raw_total), "cleaning must change this total"


def test_the_cleaned_frame_is_still_what_the_rest_of_the_analysis_uses(pipeline, retail_df: pd.DataFrame) -> None:
    execution = pipeline.execute(retail_df, dataset_name="r.csv", powerbi_table="Sales", verify_on="source")

    assert len(execution.cleaned_dataframe) == len(retail_df) - 1, "the duplicate row is still removed for analysis"
