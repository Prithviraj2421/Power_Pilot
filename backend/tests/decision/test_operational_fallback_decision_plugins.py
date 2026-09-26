import pytest

from app.common.enums import DatasetDomain
from app.intelligence.decision.plugins.fallback_decision_plugin import FallbackDecisionPlugin
from app.intelligence.decision.plugins.healthcare_decision_plugin import HealthcareDecisionPlugin
from app.intelligence.decision.plugins.logistics_decision_plugin import LogisticsDecisionPlugin
from app.intelligence.decision.plugins.marketing_decision_plugin import MarketingDecisionPlugin
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionReport


def test_healthcare_decision_plugin() -> None:
    plugin = HealthcareDecisionPlugin()
    profile = DatasetProfile(dataset_name="admissions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HEALTHCARE)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.HEALTHCARE
    assert len(report.primary_decisions) >= 1


def test_marketing_decision_plugin() -> None:
    plugin = MarketingDecisionPlugin()
    profile = DatasetProfile(dataset_name="campaigns", total_rows=100, total_columns=5, detected_domain=DatasetDomain.MARKETING)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.MARKETING
    assert len(report.primary_decisions) >= 1
    assert "ROAS" in report.primary_decisions[0].action_title or "Ad Spend" in report.primary_decisions[0].action_title


def test_logistics_decision_plugin() -> None:
    plugin = LogisticsDecisionPlugin()
    profile = DatasetProfile(dataset_name="shipments", total_rows=100, total_columns=5, detected_domain=DatasetDomain.LOGISTICS)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.LOGISTICS
    assert len(report.primary_decisions) >= 1


def test_fallback_decision_plugin() -> None:
    plugin = FallbackDecisionPlugin()
    profile = DatasetProfile(dataset_name="custom_data", total_rows=100, total_columns=2, detected_domain=DatasetDomain.UNKNOWN)

    report = plugin.decide(profile)
    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.UNKNOWN
    assert len(report.primary_decisions) >= 1
