"""Grounding guarantees for the Copilot engine.

The engine has no generative model, so its whole value is that it cannot invent a
figure. These tests pin that property: real signals are cited with real numbers,
and when the analysis supports nothing the answer says so rather than filling the
gap with plausible-sounding text.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from app.intelligence.copilot_engine import CopilotEngine, CopilotResponse
from app.models.data_intelligence_models import BusinessAnomaly, CorrelationResult, TrendResult
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

# Strings the engine used to fabricate when it had no real evidence. None of them
# may ever appear in an answer again.
FABRICATED_STRINGS = (
    "High variance detected in transaction volume",
    "Operational expenses exceeded baseline target thresholds",
    "margin compression across key dimensions",
    "Renegotiate vendor terms",
    "Optimize marketing acquisition channels",
    "Region, Store_ID, Product_Category",
    "Total Sales, Net Profit, Profit Margin",
    "Immediate inventory re-allocation and pricing adjustments",
    "Immediate action required for high-risk segments",
    "Execute immediate margin recovery plan",
)


@pytest.fixture
def engine() -> CopilotEngine:
    return CopilotEngine()


@pytest.fixture
def minimal_result() -> MasterIntelligenceResult:
    """A dataset with no business measures, no dates and no dimensions to speak of.

    This is the case that used to trigger every fabricated fallback.
    """
    df = pd.DataFrame({"reading_a": [1.0, 2.0, 3.0], "reading_b": [4.0, 5.0, 6.0]})
    return PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="Sensors.csv")


# ---------------------------------------------------------------------------
# No fabrication, ever
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Why did profit decrease?",
        "Show sales by region.",
        "What should management do?",
        "Which KPIs are failing benchmarks?",
        "How is the data quality?",
        "Give me a summary.",
    ],
)
def test_no_answer_contains_fabricated_text(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult, question: str
) -> None:
    response = engine.ask(question, minimal_result)
    haystack = " ".join(
        (response.answer, *response.evidence, *response.recommended_actions)
    )

    for fabricated in FABRICATED_STRINGS:
        assert fabricated not in haystack, (
            f"answer to {question!r} contains fabricated text: {fabricated!r}"
        )


def test_evidence_only_ever_references_real_columns(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult
) -> None:
    """Invented column names were the most dangerous fabrication: they look real."""
    response = engine.ask("Show sales by region.", minimal_result)
    real_columns = {col.name for col in minimal_result.dataset_profile.columns}

    for item in response.evidence:
        assert item.startswith("Dimension: ")
        assert item.removeprefix("Dimension: ") in real_columns


# ---------------------------------------------------------------------------
# Honest "I don't know"
# ---------------------------------------------------------------------------


def test_admits_when_no_decline_signal_exists(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("Why did profit decrease?", minimal_result)

    assert response.intent == "WHY_DECREASE"
    assert response.evidence == (), "no decline signal means no evidence may be cited"
    assert "cannot attribute a decrease" in response.answer


def test_admits_when_no_kpis_were_recommended(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("What are my KPIs?", minimal_result)

    assert response.intent == "KPI_PERFORMANCE"
    if not minimal_result.kpi_report or not minimal_result.kpi_report.primary_kpis:
        assert "No KPIs were recommended" in response.answer
        assert response.evidence == ()


def test_admits_when_no_decisions_were_produced(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("What should management do?", minimal_result)

    assert response.intent == "MANAGEMENT_ACTION"
    if not minimal_result.decision_report or not minimal_result.decision_report.primary_decisions:
        assert "no strategic actions" in response.answer
        assert response.recommended_actions == ()


def test_fallback_answers_point_at_what_is_available(
    engine: CopilotEngine, minimal_result: MasterIntelligenceResult
) -> None:
    """An honest refusal should still be useful."""
    response = engine.ask("Why did profit decrease?", minimal_result)
    assert "I can speak to" in response.answer


# ---------------------------------------------------------------------------
# Real signals are cited correctly
# ---------------------------------------------------------------------------


def test_business_anomalies_are_read_with_their_real_fields(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    """Regression: the engine read ``anomaly.description``, which does not exist.

    Any dataset that produced a business anomaly raised AttributeError. It only
    went unnoticed because the sample datasets produce none.
    """
    anomaly = BusinessAnomaly(
        anomaly_title="Margin collapse",
        severity="CRITICAL",
        affected_entity="Electronics",
        metric_name="profit",
        observed_value=1.0,
        expected_value=10.0,
        deviation_pct=-90.0,
        confidence=0.92,
        reasoning="Profit fell 90% below the expected baseline.",
    )
    intelligence = dataclasses.replace(
        retail_result.data_intelligence_report, business_anomalies=(anomaly,)
    )
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    response = engine.ask("Why did profit decrease?", result)

    assert response.evidence, "a present anomaly must be cited"
    assert "Margin collapse" in response.evidence[0]
    assert "Electronics" in response.evidence[0]
    assert "-90.0%" in response.evidence[0]


def test_declining_trends_are_cited_with_real_numbers(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    trend = TrendResult(
        time_column="order_date",
        metric_column="profit",
        direction="decreasing",
        slope=-12.5,
        growth_rate_pct=-18.4,
        confidence=0.88,
        reasoning="Sustained negative slope across the period.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    response = engine.ask("Why did revenue drop?", result)
    cited = " ".join(response.evidence)

    assert "profit is decreasing over order_date" in cited
    assert "-18.4%" in cited


def test_increasing_trends_are_not_cited_as_a_cause_of_decline(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    trend = TrendResult(
        time_column="order_date",
        metric_column="profit",
        direction="increasing",
        slope=9.0,
        growth_rate_pct=22.0,
        confidence=0.9,
        reasoning="Sustained positive slope.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    response = engine.ask("Why did profit decrease?", result)
    assert "increasing" not in " ".join(response.evidence)


def test_only_negative_correlations_are_cited_for_a_decline(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    correlations = (
        CorrelationResult(
            column_a="discount",
            column_b="profit",
            coefficient=-0.81,
            correlation_type="strong_negative",
            confidence=0.9,
            reasoning="Higher discounts track lower profit.",
        ),
        CorrelationResult(
            column_a="quantity",
            column_b="sales_amount",
            coefficient=0.93,
            correlation_type="strong_positive",
            confidence=0.95,
            reasoning="More units, more revenue.",
        ),
    )
    intelligence = dataclasses.replace(
        retail_result.data_intelligence_report, correlations=correlations, trends=()
    )
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)

    assert "discount and profit" in cited
    assert "quantity and sales_amount" not in cited


def test_kpi_answer_cites_real_dax_formulas(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("Show me the DAX measures", retail_result)

    assert response.intent == "KPI_PERFORMANCE"
    real_names = {kpi.name for kpi in retail_result.kpi_report.primary_kpis}
    for item in response.evidence:
        assert item.split(":")[0] in real_names


def test_quality_answer_reports_the_real_grade_and_cleaning_delta(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("How is the data quality?", retail_result)
    quality = retail_result.quality_report
    preparation = retail_result.preparation_report

    assert response.intent == "DATA_QUALITY"
    assert f"{quality.overall_score:.1f}%" in response.answer
    assert str(quality.total_issues_count) in response.answer
    assert f"{preparation.original_rows} rows to {preparation.cleaned_rows}" in response.answer


def test_breakdown_lists_the_datasets_actual_dimensions(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("Show sales by region.", retail_result)

    assert response.intent == "DIMENSIONAL_BREAKDOWN"
    assert "category" in response.answer.lower() or "region" in response.answer.lower()


# ---------------------------------------------------------------------------
# Intent routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("How is the data quality?", "DATA_QUALITY"),
        ("Are there missing values?", "DATA_QUALITY"),
        ("Why did profit decrease?", "WHY_DECREASE"),
        ("Show sales by region.", "DIMENSIONAL_BREAKDOWN"),
        ("What should management do?", "MANAGEMENT_ACTION"),
        ("Which KPIs are failing benchmarks?", "KPI_PERFORMANCE"),
        ("Tell me about this file.", "GENERAL_QA"),
    ],
)
def test_questions_route_to_the_expected_intent(
    engine: CopilotEngine,
    retail_result: MasterIntelligenceResult,
    question: str,
    expected_intent: str,
) -> None:
    assert engine.ask(question, retail_result).intent == expected_intent


def test_short_keywords_do_not_match_inside_longer_words(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    """'do' must not match inside 'domain', which used to force MANAGEMENT_ACTION."""
    assert engine.ask("What is the domain?", retail_result).intent == "GENERAL_QA"


def test_every_response_is_the_documented_shape(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    response = engine.ask("Give me an executive briefing.", retail_result)

    assert isinstance(response, CopilotResponse)
    assert isinstance(response.answer, str) and response.answer.strip()
    assert isinstance(response.evidence, tuple)
    assert isinstance(response.recommended_actions, tuple)
    assert isinstance(response.suggested_followups, tuple)
    assert response.suggested_followups, "every answer should offer a way forward"


def test_answers_always_name_the_dataset(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    for question in ("Why did profit decrease?", "What are my KPIs?", "Summarize this."):
        assert "retail.csv" in engine.ask(question, retail_result).answer


# ---------------------------------------------------------------------------
# Identifier and contradictory-figure filtering
# ---------------------------------------------------------------------------


def test_identifier_columns_are_never_cited_as_business_trends(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    """A trend fitted through customer_id is valid arithmetic and meaningless."""
    identifier = next(
        col.name for col in retail_result.dataset_profile.columns if col.identifier
    )
    trend = TrendResult(
        time_column="order_date",
        metric_column=identifier,
        direction="decreasing",
        slope=-1.2,
        growth_rate_pct=-8.0,
        confidence=0.85,
        reasoning="Negative slope.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)
    assert identifier not in cited


def test_growth_rate_is_dropped_when_it_contradicts_the_slope(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    """The plugin derives direction from the slope but growth from endpoints only.

    When they disagree the answer must not claim "decreasing (+17.6%)".
    """
    trend = TrendResult(
        time_column="order_date",
        metric_column="profit",
        direction="decreasing",
        slope=-4.0,
        growth_rate_pct=17.6,
        confidence=0.85,
        reasoning="Negative slope but a higher final value than first.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)

    assert "profit is decreasing over order_date" in cited
    assert "+17.6" not in cited, "a positive growth figure must not accompany a decline"


def test_agreeing_growth_rate_is_still_reported(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    trend = TrendResult(
        time_column="order_date",
        metric_column="profit",
        direction="decreasing",
        slope=-4.0,
        growth_rate_pct=-31.2,
        confidence=0.85,
        reasoning="Negative slope and negative endpoint delta.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)
    assert "-31.2% first to last" in cited


def test_identifier_correlations_are_not_cited(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    identifier = next(
        col.name for col in retail_result.dataset_profile.columns if col.identifier
    )
    correlation = CorrelationResult(
        column_a=identifier,
        column_b="profit",
        coefficient=-0.77,
        correlation_type="strong_negative",
        confidence=0.9,
        reasoning="Spurious.",
    )
    intelligence = dataclasses.replace(
        retail_result.data_intelligence_report, correlations=(correlation,), trends=()
    )
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)
    assert identifier not in cited


def test_repeating_foreign_keys_are_excluded_even_when_not_flagged_unique(
    engine: CopilotEngine, retail_result: MasterIntelligenceResult
) -> None:
    """customer_id repeats across rows, so the Schema Analyzer does not flag it.

    The name heuristic must still keep it out of business-trend evidence.
    """
    profile_flag = next(
        col.identifier for col in retail_result.dataset_profile.columns if col.name == "customer_id"
    )
    assert profile_flag is False, "fixture assumption: customer_id is not structurally unique"

    trend = TrendResult(
        time_column="order_date",
        metric_column="customer_id",
        direction="decreasing",
        slope=-0.4,
        growth_rate_pct=-12.0,
        confidence=0.85,
        reasoning="Negative slope.",
    )
    intelligence = dataclasses.replace(retail_result.data_intelligence_report, trends=(trend,))
    result = dataclasses.replace(retail_result, data_intelligence_report=intelligence)

    cited = " ".join(engine.ask("Why did profit decrease?", result).evidence)
    assert "customer_id" not in cited
