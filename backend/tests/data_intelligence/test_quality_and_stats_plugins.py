import pandas as pd
import pytest

from app.intelligence.data.plugins.quality_plugin import DataQualityPlugin
from app.intelligence.data.plugins.statistics_plugin import StatisticsPlugin
from app.models.data_intelligence_models import QualityReport, StatisticalSummary
from app.models.dataset_profile import DatasetProfile


def test_data_quality_plugin() -> None:
    """Test DataQualityPlugin with nulls, duplicates, and valid rows."""
    plugin = DataQualityPlugin()

    df = pd.DataFrame({
        "id": [1, 2, 3, 3, None],
        "name": ["Alice", "Bob", "Charlie", "Charlie", "Eve"],
        "age": [25.0, 30.0, 35.0, 35.0, None],
    })

    dataset_profile = DatasetProfile(dataset_name="test.csv", total_rows=5, total_columns=3)
    report: QualityReport = plugin.analyze(df, dataset_profile)

    assert isinstance(report, QualityReport)
    assert 0.0 <= report.completeness_score <= 100.0
    assert 0.0 <= report.uniqueness_score <= 100.0
    assert 0.0 <= report.validity_score <= 100.0
    assert report.total_issues > 0
    assert len(report.evidence) > 0


def test_statistics_plugin() -> None:
    """Test StatisticsPlugin with numeric, text, and date columns."""
    plugin = StatisticsPlugin()

    df = pd.DataFrame({
        "numeric_col": [10.0, 20.0, 30.0, 40.0, 50.0],
        "text_col": ["A", "B", "C", "D", "E"],
        "date_col": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]),
    })

    dataset_profile = DatasetProfile(dataset_name="test.csv", total_rows=5, total_columns=3)
    summary: StatisticalSummary = plugin.analyze(df, dataset_profile)

    assert isinstance(summary, StatisticalSummary)
    assert summary.total_rows == 5
    assert summary.numeric_columns_count == 1
    assert summary.categorical_columns_count == 1
    assert summary.date_columns_count == 1
    assert "numeric_col" in summary.column_summaries

    stats = summary.column_summaries["numeric_col"]
    assert stats["mean"] == 30.0
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
