import pandas as pd
import pytest

from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_pipeline_single_column_csv() -> None:
    """
    Test master intelligence pipeline with a single column dataset.
    """
    df = pd.DataFrame({"transaction_id": [101, 102, 103, 104, 105]})
    pipeline = PowerPilotIntelligencePipeline()

    result: MasterIntelligenceResult = pipeline.run_pipeline(df, dataset_name="SingleCol.csv")
    assert isinstance(result, MasterIntelligenceResult)
    assert result.dataset_profile.total_columns == 1
    assert result.dataset_profile.total_rows == 5


def test_pipeline_all_null_column() -> None:
    """
    Test master intelligence pipeline with columns containing all null values.
    """
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "empty_notes": [None, None, None],
            "amount": [10.5, 20.0, 30.5],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()

    result: MasterIntelligenceResult = pipeline.run_pipeline(df, dataset_name="NullCol.csv")
    assert isinstance(result, MasterIntelligenceResult)
    assert result.dataset_profile.total_columns == 3


def test_pipeline_special_character_column_names() -> None:
    """
    Test master intelligence pipeline with special characters in header names.
    """
    df = pd.DataFrame(
        {
            "Gross Revenue ($USD)": [1000, 2000, 3000],
            "Customer % Retention": [0.85, 0.90, 0.95],
            "Date/Time": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()

    result: MasterIntelligenceResult = pipeline.run_pipeline(df, dataset_name="SpecialHeaders.csv")
    assert isinstance(result, MasterIntelligenceResult)
    assert result.dataset_profile.total_columns == 3
    assert len(result.kpi_report.primary_kpis) > 0
