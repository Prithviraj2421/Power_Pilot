import numpy as np
import pandas as pd
import pytest

from app.intelligence.data.plugins.correlation_plugin import CorrelationPlugin
from app.intelligence.data.plugins.outliers_plugin import OutliersPlugin
from app.intelligence.data.plugins.trends_plugin import TrendsPlugin
from app.models.data_intelligence_models import CorrelationResult, OutlierReport, TrendResult
from app.models.dataset_profile import DatasetProfile


def test_correlation_plugin() -> None:
    """Test CorrelationPlugin with strongly correlated columns."""
    plugin = CorrelationPlugin()

    # Create dataset where column_b is exactly 2 * column_a
    df = pd.DataFrame({
        "units": [10, 20, 30, 40, 50, 60, 70, 80],
        "revenue": [20, 40, 60, 80, 100, 120, 140, 160],
        "random_val": [5, 2, 8, 1, 9, 3, 7, 4],
    })

    dataset_profile = DatasetProfile(dataset_name="sales.csv", total_rows=8, total_columns=3)
    results = plugin.analyze(df, dataset_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    top_corr = results[0]
    assert isinstance(top_corr, CorrelationResult)
    assert top_corr.coefficient >= 0.99
    assert top_corr.confidence >= 0.8
    assert len(top_corr.reasoning) > 0


def test_trends_plugin() -> None:
    """Test TrendsPlugin with time-series data."""
    plugin = TrendsPlugin()

    df = pd.DataFrame({
        "order_date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]),
        "sales": [100.0, 120.0, 140.0, 160.0, 180.0],
    })

    dataset_profile = DatasetProfile(dataset_name="sales.csv", total_rows=5, total_columns=2)
    results = plugin.analyze(df, dataset_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    trend = results[0]
    assert isinstance(trend, TrendResult)
    assert trend.direction in ("increasing", "upward")
    assert trend.confidence >= 0.7


def test_outliers_plugin() -> None:
    """Test OutliersPlugin with a dataset containing extreme values."""
    plugin = OutliersPlugin()

    # Add extreme outliers
    values = [10.0, 12.0, 11.0, 13.0, 12.0, 11.0, 10.0, 12.0, 500.0, -300.0]
    df = pd.DataFrame({"price": values})

    dataset_profile = DatasetProfile(dataset_name="prices.csv", total_rows=len(values), total_columns=1)
    results = plugin.analyze(df, dataset_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    outlier_rep = results[0]
    assert isinstance(outlier_rep, OutlierReport)
    assert outlier_rep.outlier_count >= 1
    assert outlier_rep.column_name == "price"
    assert outlier_rep.method_used == "IQR"
