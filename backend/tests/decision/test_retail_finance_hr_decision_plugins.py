import pytest

from app.common.enums import DatasetDomain
from app.intelligence.decision.plugins.finance_decision_plugin import FinanceDecisionPlugin
from app.intelligence.decision.plugins.hr_decision_plugin import HRDecisionPlugin
from app.intelligence.decision.plugins.retail_decision_plugin import RetailDecisionPlugin
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionAction, DecisionReport, ScenarioOption


def test_retail_decision_plugin() -> None:
    plugin = RetailDecisionPlugin()
    profile = DatasetProfile(dataset_name="transactions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.RETAIL)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.primary_decisions) >= 2
    assert len(report.scenario_options) >= 2
    first_action = report.primary_decisions[0]
    assert isinstance(first_action, DecisionAction)
    assert first_action.urgency in ("IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
    assert first_action.confidence >= 0.85


def test_finance_decision_plugin() -> None:
    plugin = FinanceDecisionPlugin()
    profile = DatasetProfile(dataset_name="ledger", total_rows=100, total_columns=5, detected_domain=DatasetDomain.FINANCE)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.FINANCE
    assert len(report.primary_decisions) >= 1
    assert "OPEX" in report.primary_decisions[0].action_title or "Cost" in report.primary_decisions[0].action_title


def test_hr_decision_plugin() -> None:
    plugin = HRDecisionPlugin()
    profile = DatasetProfile(dataset_name="employees", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HR)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.HR
    assert len(report.primary_decisions) >= 1
    assert "Salary" in report.primary_decisions[0].action_title or "Retention" in report.primary_decisions[0].action_title
