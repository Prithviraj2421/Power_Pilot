"""Tests for the domain confidence gate.

A domain label carries the same visual weight at 25% confidence as at 80% -- the
workspace header reads "RETAIL Workspace" either way -- and every downstream
engine builds KPI templates, dashboard layouts and strategic decisions on it as
though it were established. Below the threshold the honest answer is UNKNOWN.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.core.config import Settings, get_settings
from app.intelligence.domain_classifier import DomainClassifier
from app.intelligence.entity_detector import EntityDetector
from app.intelligence.schema.schema_analyzer import SchemaAnalyzer
from app.models.dataset_profile import DatasetProfile


def _profile(df: pd.DataFrame, name: str) -> DatasetProfile:
    profile = SchemaAnalyzer().analyze(df, dataset_name=name)
    EntityDetector().detect(profile, df)
    return profile


@pytest.fixture
def students_df() -> pd.DataFrame:
    """A real-shaped dataset belonging to none of the six supported domains."""
    return pd.DataFrame(
        {
            "student_id": range(1, 61),
            "hours_per_week": [i % 12 + 1 for i in range(60)],
            "tool_used": ["ChatGPT", "Claude", "Copilot", "Gemini"] * 15,
            "satisfaction": [(i % 5) + 1 for i in range(60)],
            "grade_level": ["Freshman", "Sophomore", "Junior", "Senior"] * 15,
        }
    )


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_weak_classification_is_reported_as_unknown(students_df: pd.DataFrame) -> None:
    profile = _profile(students_df, "students_ai_usage.csv")

    DomainClassifier().classify(profile)

    assert profile.detected_domain == DatasetDomain.UNKNOWN
    assert profile.domain_confidence == 0.0


def test_a_rejected_best_guess_is_still_inspectable(students_df: pd.DataFrame) -> None:
    """UNKNOWN must not throw away the ranking -- the guess is useful context."""
    profile = _profile(students_df, "students_ai_usage.csv")

    ranked = DomainClassifier().classify(profile)

    assert ranked, "candidates should still be returned"
    assert profile.candidate_domains, "candidates should still be on the profile"
    assert 0 < ranked[0].confidence < get_settings().min_domain_confidence


def test_featureless_numeric_data_is_unknown() -> None:
    profile = _profile(pd.DataFrame({"a": range(50), "b": range(50)}), "numbers.csv")

    DomainClassifier().classify(profile)

    assert profile.detected_domain == DatasetDomain.UNKNOWN


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("retail.csv", DatasetDomain.RETAIL),
        ("finance.csv", DatasetDomain.FINANCE),
        ("hr.csv", DatasetDomain.HR),
        ("healthcare.csv", DatasetDomain.HEALTHCARE),
    ],
)
def test_genuine_domains_still_classify(
    filename: str, expected: DatasetDomain, datasets_dir
) -> None:
    """The gate must not be so strict that real datasets lose their domain.

    The samples score 0.633-0.800, comfortably clear of the 0.50 threshold.
    """
    profile = _profile(pd.read_csv(datasets_dir / filename), filename)

    DomainClassifier().classify(profile)

    assert profile.detected_domain == expected
    assert profile.domain_confidence >= get_settings().min_domain_confidence


# ---------------------------------------------------------------------------
# Configurability
# ---------------------------------------------------------------------------


def test_threshold_is_configurable(students_df: pd.DataFrame) -> None:
    profile = _profile(students_df, "students_ai_usage.csv")

    # The old 0.20 threshold is what let a 0.325 guess through as fact.
    DomainClassifier(min_confidence=0.20).classify(profile)
    assert profile.detected_domain != DatasetDomain.UNKNOWN

    DomainClassifier(min_confidence=0.50).classify(profile)
    assert profile.detected_domain == DatasetDomain.UNKNOWN


def test_threshold_defaults_to_the_configured_setting() -> None:
    assert Settings().min_domain_confidence == 0.50


def test_a_threshold_above_every_score_makes_everything_unknown(
    datasets_dir,
) -> None:
    profile = _profile(pd.read_csv(datasets_dir / "retail.csv"), "retail.csv")

    DomainClassifier(min_confidence=0.99).classify(profile)

    assert profile.detected_domain == DatasetDomain.UNKNOWN


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_unknown_domain_still_produces_a_full_analysis(
    students_df: pd.DataFrame, pipeline
) -> None:
    """Every engine has a generic fallback, so UNKNOWN degrades rather than fails."""
    result = pipeline.run_pipeline(students_df, dataset_name="students_ai_usage.csv")

    assert result.dataset_profile.detected_domain == DatasetDomain.UNKNOWN
    assert result.quality_report is not None
    assert result.kpi_report is not None and result.kpi_report.primary_kpis
    assert result.dashboard_report is not None and result.dashboard_report.tabs
    assert result.decision_report is not None
    assert result.insight_report is not None
