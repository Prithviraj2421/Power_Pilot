"""Guards for the shared sample datasets in tests/datasets/.

These four CSV files were previously committed as 0-byte placeholders, which
made them silently useless. These tests fail loudly if that regresses, and they
pin the domain each sample is expected to classify as so the conftest fixtures
stay trustworthy for every downstream test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

EXPECTED_DOMAINS = {
    "retail_df": DatasetDomain.RETAIL,
    "finance_df": DatasetDomain.FINANCE,
    "hr_df": DatasetDomain.HR,
    "healthcare_df": DatasetDomain.HEALTHCARE,
}

MIN_ROWS = 40
MIN_COLUMNS = 8


@pytest.mark.parametrize("fixture_name", sorted(EXPECTED_DOMAINS))
def test_sample_dataset_is_populated(fixture_name: str, request: pytest.FixtureRequest) -> None:
    """Every sample must carry enough rows for statistics, trends and correlations."""
    df: pd.DataFrame = request.getfixturevalue(fixture_name)

    assert not df.empty, f"{fixture_name} loaded an empty DataFrame"
    assert len(df) >= MIN_ROWS, f"{fixture_name} has {len(df)} rows, expected >= {MIN_ROWS}"
    assert len(df.columns) >= MIN_COLUMNS, (
        f"{fixture_name} has {len(df.columns)} columns, expected >= {MIN_COLUMNS}"
    )


@pytest.mark.parametrize("fixture_name", sorted(EXPECTED_DOMAINS))
def test_sample_dataset_carries_deliberate_dirt(
    fixture_name: str, request: pytest.FixtureRequest
) -> None:
    """Samples intentionally contain missing values and one exact duplicate row.

    A spotless fixture would let the Data Quality Engine score a trivial perfect
    grade and hide regressions in the validator and cleaner plugins.
    """
    df: pd.DataFrame = request.getfixturevalue(fixture_name)

    assert df.isna().sum().sum() > 0, f"{fixture_name} has no missing values to clean"
    assert df.duplicated().sum() >= 1, f"{fixture_name} has no duplicate row to detect"


@pytest.mark.parametrize(("fixture_name", "expected_domain"), sorted(EXPECTED_DOMAINS.items()))
def test_sample_dataset_classifies_to_expected_domain(
    fixture_name: str,
    expected_domain: DatasetDomain,
    request: pytest.FixtureRequest,
    pipeline: PowerPilotIntelligencePipeline,
) -> None:
    """End-to-end check that each sample drives the pipeline to its intended domain."""
    df: pd.DataFrame = request.getfixturevalue(fixture_name)

    result = pipeline.run_pipeline(df, dataset_name=f"{fixture_name}.csv")

    assert result.dataset_profile.detected_domain == expected_domain
    assert result.dataset_profile.domain_confidence > 0.5
    assert result.quality_report is not None
    assert result.quality_report.total_issues_count > 0, (
        "expected the deliberate dirt to surface as quality issues"
    )
    assert result.kpi_report is not None and result.kpi_report.primary_kpis
    assert result.dashboard_report is not None and result.dashboard_report.tabs
    assert result.decision_report is not None and result.decision_report.primary_decisions


def test_csv_upload_fixture_round_trips_through_the_api(client, csv_upload, retail_df) -> None:
    """The conftest upload helper must produce a payload the real endpoint accepts."""
    response = client.post(
        "/api/v1/intelligence/analyze-csv",
        files=csv_upload(retail_df, "retail.csv"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["dataset_name"] == "retail.csv"
    assert body["detected_domain"] == DatasetDomain.RETAIL.value
    assert body["result"]["dataset_profile"] is not None

    # `total_rows` is profiled from the CLEANED frame, not the raw upload, so the
    # one deliberate duplicate row is already gone by the time the profile is built.
    assert body["total_rows"] == len(retail_df.drop_duplicates())
    assert body["total_rows"] == len(retail_df) - 1
