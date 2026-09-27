"""Regression test for a real classification bug.

A synthetic weather-station dataset -- reading id, timestamp, station code,
temperature, humidity, pressure, wind speed, battery -- nothing about people --
classified as HR at 0.667 confidence, with a wider margin over the runner-up
than the genuine hr.csv sample scores over its own runner-up.

Traced to app/intelligence/entity/detectors/employee_detector.py matching the
keyword "emp" as a raw substring: `"emp" in "temperature_c"` is True in plain
Python (t-EMP-erature), so the Entity Detector tagged the temperature column
EMPLOYEE, which gave the HR domain classifier a "primary entity found" hit it
should never have had. See app/common/keyword_match.py, which sixteen entity
detectors and domain classifiers now use instead of raw `in`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.common.enums import DatasetDomain, SemanticType
from app.intelligence.entity_detector import EntityDetector
from app.intelligence.schema.schema_analyzer import SchemaAnalyzer
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


@pytest.fixture
def sensor_df() -> pd.DataFrame:
    """The exact dataset shape that triggered the original bug report."""
    return pd.DataFrame(
        {
            "reading_id": range(1, 401),
            "recorded_at": pd.date_range("2024-06-01", periods=400, freq="1h").astype(str),
            "station_code": ["ALPHA", "BRAVO", "CHARLIE", "DELTA"] * 100,
            "temperature_c": [20.0 + (i % 15) for i in range(400)],
            "humidity_pct": [50.0 + (i % 40) for i in range(400)],
            "pressure_hpa": [1013.0 + (i % 9) for i in range(400)],
            "wind_speed_kmh": [10.0 + (i % 20) for i in range(400)],
            "battery_pct": [90.0 - (i % 80) for i in range(400)],
        }
    )


def test_temperature_column_is_not_tagged_as_employee(sensor_df: pd.DataFrame) -> None:
    profile = SchemaAnalyzer().analyze(sensor_df, dataset_name="sensors.csv")
    EntityDetector().detect(profile, sensor_df)

    temperature_column = next(col for col in profile.columns if col.name == "temperature_c")
    assert temperature_column.semantic_type != SemanticType.EMPLOYEE


def test_no_sensor_column_is_tagged_as_employee(sensor_df: pd.DataFrame) -> None:
    """None of these columns describe a person; none should match EMPLOYEE."""
    profile = SchemaAnalyzer().analyze(sensor_df, dataset_name="sensors.csv")
    EntityDetector().detect(profile, sensor_df)

    employee_columns = [
        col.name for col in profile.columns if col.semantic_type == SemanticType.EMPLOYEE
    ]
    assert employee_columns == []


def test_sensor_dataset_no_longer_classifies_as_hr(
    sensor_df: pd.DataFrame, pipeline: PowerPilotIntelligencePipeline
) -> None:
    """End-to-end: the full pipeline must not label this dataset HR."""
    result = pipeline.run_pipeline(sensor_df, dataset_name="sensors.csv")

    assert result.dataset_profile.detected_domain != DatasetDomain.HR
    # No business domain fits this dataset, so the honest label is UNKNOWN --
    # not merely "not HR", but specifically not a false-confident guess either.
    assert result.dataset_profile.detected_domain == DatasetDomain.UNKNOWN
    assert result.dataset_profile.domain_confidence == 0.0


def test_genuine_hr_dataset_is_unaffected(datasets_dir, pipeline) -> None:
    """The fix must not weaken real HR detection -- only reject false positives."""
    df = pd.read_csv(datasets_dir / "hr.csv")

    result = pipeline.run_pipeline(df, dataset_name="hr.csv")

    assert result.dataset_profile.detected_domain == DatasetDomain.HR
    assert result.dataset_profile.domain_confidence >= 0.5
