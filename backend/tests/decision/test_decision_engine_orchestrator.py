import pytest

from app.common.enums import DatasetDomain
from app.intelligence.decision_engine import DecisionEngine
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionReport


def test_decision_engine_orchestrator() -> None:
    engine = DecisionEngine()

    profile = DatasetProfile(dataset_name="pos_transactions", total_rows=500, total_columns=6, detected_domain=DatasetDomain.RETAIL)

    report = engine.decide(profile)

    assert isinstance(report, DecisionReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.primary_decisions) >= 2
    assert len(report.scenario_options) >= 2
    assert len(report.executive_decision_summary) > 0
