"""
Unit tests for PowerPilot Operational Profilers.
"""

import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.business.profilers.fallback_profiler import FallbackProfiler
from app.intelligence.business.profilers.healthcare_profiler import HealthcareProfiler
from app.intelligence.business.profilers.logistics_profiler import LogisticsProfiler
from app.intelligence.business.profilers.marketing_profiler import MarketingProfiler
from app.models.business_profile import BusinessProfile
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


def create_mock_dataset_profile(domain: DatasetDomain, dataset_name: str = "TestDataset") -> DatasetProfile:
    """Helper to create a standard DatasetProfile for tests."""
    return DatasetProfile(
        dataset_name=dataset_name,
        total_rows=1000,
        total_columns=5,
        detected_domain=domain,
        columns=[],
    )


def test_healthcare_profiler() -> None:
    """Test HealthcareProfiler generates correct business profile."""
    profiler = HealthcareProfiler()
    dataset = create_mock_dataset_profile(DatasetDomain.HEALTHCARE)
    
    entities = [
        DetectedEntity(column_name="Patient_ID", entity_type="IDENTIFIER", confidence=0.9, reason="ID"),
    ]
    
    profile: BusinessProfile = profiler.profile(dataset, entities)
    
    assert profile.domain == DatasetDomain.HEALTHCARE
    assert len(profile.primary_kpis) == 3
    kpi_names = [kpi.name for kpi in profile.primary_kpis]
    assert "Total Patient Admissions" in kpi_names
    assert "Total Treatment Expenses" in kpi_names
    assert "Average Spend Per Patient" in kpi_names
    assert "Diagnosis_Category" in profile.dimensions
    assert "Treatment_Cost" in profile.measures
    assert len(profile.entities) == 1
    assert profile.entities[0].column_name == "Patient_ID"


def test_marketing_profiler() -> None:
    """Test MarketingProfiler generates correct business profile."""
    profiler = MarketingProfiler()
    dataset = create_mock_dataset_profile(DatasetDomain.MARKETING)
    
    profile: BusinessProfile = profiler.profile(dataset, None)
    
    assert profile.domain == DatasetDomain.MARKETING
    assert len(profile.primary_kpis) == 4
    kpi_names = [kpi.name for kpi in profile.primary_kpis]
    assert "Total Campaign Revenue" in kpi_names
    assert "Total Ad Spend" in kpi_names
    assert "Return on Ad Spend (ROAS)" in kpi_names
    assert "Cost Per Acquisition (CPA)" in kpi_names
    assert "Marketing_Channel" in profile.dimensions
    assert "Ad_Spend" in profile.measures
    assert len(profile.entities) == 0


def test_logistics_profiler() -> None:
    """Test LogisticsProfiler generates correct business profile."""
    profiler = LogisticsProfiler()
    dataset = create_mock_dataset_profile(DatasetDomain.LOGISTICS)
    
    profile: BusinessProfile = profiler.profile(dataset, None)
    
    assert profile.domain == DatasetDomain.LOGISTICS
    assert len(profile.primary_kpis) == 3
    kpi_names = [kpi.name for kpi in profile.primary_kpis]
    assert "Total Shipped Volume" in kpi_names
    assert "Total Freight Spend" in kpi_names
    assert "Average Shipping Delay (Days)" in kpi_names
    assert "Carrier" in profile.dimensions
    assert "Freight_Cost" in profile.measures


def test_fallback_profiler() -> None:
    """Test FallbackProfiler dynamically handles columns."""
    profiler = FallbackProfiler()
    
    col1 = ColumnProfile(
        name="sales_amount", physical_type=PhysicalType.DECIMAL, 
        nullable=False, unique=False, identifier=False, missing_count=0, unique_count=100
    )
    col2 = ColumnProfile(
        name="event_date", physical_type=PhysicalType.DATE,
        nullable=False, unique=False, identifier=False, missing_count=0, unique_count=50
    )
    col3 = ColumnProfile(
        name="category", physical_type=PhysicalType.TEXT,
        nullable=False, unique=False, identifier=False, missing_count=0, unique_count=10
    )
    
    dataset = DatasetProfile(
        dataset_name="UnknownData",
        total_rows=500,
        total_columns=3,
        detected_domain=DatasetDomain.UNKNOWN,
        columns=[col1, col2, col3],
    )
    
    profile: BusinessProfile = profiler.profile(dataset, None)
    
    assert profile.domain == DatasetDomain.UNKNOWN
    assert "sales_amount" in profile.measures
    assert "event_date" in profile.dimensions
    assert "category" in profile.dimensions
    
    assert len(profile.primary_kpis) == 1
    assert profile.primary_kpis[0].name == "Total Sales Amount"
    assert "sales_amount" in profile.primary_kpis[0].formula
