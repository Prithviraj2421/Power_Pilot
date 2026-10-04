import pandas as pd
import pytest

from app.intelligence.copilot_engine import CopilotEngine, CopilotResponse
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_copilot_engine_why_decrease() -> None:
    """A real, steady decline (with noise) is a finding the copilot can cite."""
    import numpy as np

    rng = np.random.default_rng(7)
    days = pd.date_range("2024-01-01", periods=40)
    df = pd.DataFrame(
        {
            "customer_id": range(1, 41),
            "sales_amount": 400.0 - 8.0 * np.arange(40) + rng.normal(0, 10, 40),
            "order_date": days.strftime("%Y-%m-%d"),
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="Test.csv")

    copilot = CopilotEngine()
    resp: CopilotResponse = copilot.ask("Why did profit decrease?", result)

    assert isinstance(resp, CopilotResponse)
    assert resp.intent == "WHY_DECREASE"
    assert "decrease" in resp.answer or "drop" in resp.answer or "Test.csv" in resp.answer
    assert len(resp.evidence) > 0
    assert len(resp.suggested_followups) > 0


def test_copilot_engine_management_actions() -> None:
    df = pd.DataFrame(
        {
            "employee_id": [1, 2, 3],
            "salary": [50000, 60000, 70000],
            "hire_date": ["2020-01-01", "2021-01-01", "2022-01-01"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="HR.csv")

    copilot = CopilotEngine()
    resp: CopilotResponse = copilot.ask("What should management do?", result)

    assert isinstance(resp, CopilotResponse)
    assert resp.intent == "MANAGEMENT_ACTION"
    assert len(resp.recommended_actions) > 0


def test_copilot_engine_general_qa() -> None:
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="General.csv")

    copilot = CopilotEngine()
    resp: CopilotResponse = copilot.ask("Give me an executive summary", result)

    assert isinstance(resp, CopilotResponse)
    assert resp.intent == "GENERAL_QA"
    assert "General.csv" in resp.answer


def test_copilot_engine_does_not_cite_a_wiggle_as_a_trend() -> None:
    """Five unrelated numbers going up and down are not a trend, so there is no trend evidence to cite."""
    df = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "sales_amount": [100.0, 150.0, 200.0, 80.0, 50.0],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        }
    )
    result = PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="Test.csv")

    assert result.data_intelligence_report.trends == ()
    assert result.data_intelligence_report.tests_run >= 1
