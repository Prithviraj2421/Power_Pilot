"""
Unit tests for BusinessProfiler Orchestrator.
"""

import pytest

from app.common.enums import DatasetDomain
from app.intelligence.business_profiler import BusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile


def create_mock_dataset_profile(domain: DatasetDomain, dataset_name: str = "TestDataset") -> DatasetProfile:
    """Helper to create a standard DatasetProfile for tests."""
    return DatasetProfile(
        dataset_name=dataset_name,
        total_rows=1000,
        total_columns=5,
        detected_domain=domain,
        columns=[],
    )


def test_business_profiler_initialization() -> None:
    """Test the facade initializes profilers correctly."""
    orchestrator = BusinessProfiler()
    assert len(orchestrator._profilers) > 0
    assert DatasetDomain.RETAIL in orchestrator._profilers
    assert DatasetDomain.FINANCE in orchestrator._profilers
    assert DatasetDomain.HR in orchestrator._profilers
    assert DatasetDomain.HEALTHCARE in orchestrator._profilers
    assert DatasetDomain.MARKETING in orchestrator._profilers
    assert DatasetDomain.LOGISTICS in orchestrator._profilers


@pytest.mark.parametrize("domain", [
    DatasetDomain.RETAIL,
    DatasetDomain.FINANCE,
    DatasetDomain.HR,
    DatasetDomain.HEALTHCARE,
    DatasetDomain.MARKETING,
    DatasetDomain.LOGISTICS,
    DatasetDomain.UNKNOWN,
])
def test_business_profiler_dispatch(domain: DatasetDomain) -> None:
    """Test facade dispatches to the correct domain profiler based on detected_domain."""
    orchestrator = BusinessProfiler()
    dataset = create_mock_dataset_profile(domain)

    profile = orchestrator.profile(dataset, entities=None)

    assert isinstance(profile, BusinessProfile)
    assert profile.domain == domain


def test_business_profiler_fallback_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test facade falls back safely on error during profiling."""
    orchestrator = BusinessProfiler()
    dataset = create_mock_dataset_profile(DatasetDomain.HEALTHCARE)

    def raising_profile(*args, **kwargs):
        raise Exception("Profiling Error")

    monkeypatch.setattr(orchestrator._profilers[DatasetDomain.HEALTHCARE], "profile", raising_profile)

    profile = orchestrator.profile(dataset, entities=None)

    # Should fall back to the generic UNKNOWN domain fallback profiler
    assert isinstance(profile, BusinessProfile)
    assert profile.domain == DatasetDomain.UNKNOWN
