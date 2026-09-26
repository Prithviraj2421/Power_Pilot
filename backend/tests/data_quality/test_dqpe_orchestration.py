import pandas as pd
import pytest

from app.data_quality.dqpe_facade import DataQualityPreparationEngine
from app.models.data_quality_models import QualityGrade
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_dqpe_facade_assessment_and_preparation() -> None:
    df = pd.DataFrame(
        {
            "customer_id": [1, 1, 2, 3],
            "revenue": ["$1,000.00", "$1,000.00", "$2,500.00", None],
            "signup_date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    dqpe = DataQualityPreparationEngine()

    quality_report = dqpe.assess_quality(df, dataset_name="RawData.csv")
    assert quality_report.dataset_name == "RawData.csv"
    assert quality_report.grade in (QualityGrade.A, QualityGrade.B, QualityGrade.C, QualityGrade.D)
    assert len(quality_report.detected_issues) > 0

    cleaned_df, prep_report = dqpe.prepare_data(df, dataset_name="RawData.csv")
    assert len(cleaned_df) == 3
    assert prep_report.rows_removed == 1
    assert prep_report.total_actions_count > 0


def test_pipeline_integration_with_dqpe_stage1() -> None:
    df = pd.DataFrame(
        {
            "order_id": [101, 102, 103],
            "sales": ["$150.00", "$250.00", "$350.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="IntegratedTest.csv")

    assert result.quality_report is not None
    assert result.preparation_report is not None
    assert result.dataset_profile.total_columns == 3
    assert result.dataset_profile.columns[1].physical_type.value.lower() in ("float", "decimal", "integer")
