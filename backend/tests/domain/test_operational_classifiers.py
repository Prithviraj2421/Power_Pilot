import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.domain.classifiers.healthcare_classifier import HealthcareClassifier
from app.intelligence.domain.classifiers.logistics_classifier import LogisticsClassifier
from app.intelligence.domain.classifiers.marketing_classifier import MarketingClassifier
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile


def create_column(name: str, semantic_type: SemanticType = SemanticType.UNKNOWN) -> ColumnProfile:
    """Helper to construct ColumnProfile objects for domain classification tests."""
    return ColumnProfile(
        name=name,
        physical_type=PhysicalType.TEXT,
        nullable=False,
        unique=False,
        identifier=False,
        missing_count=0,
        unique_count=10,
        semantic_type=semantic_type,
    )


def test_healthcare_classifier_matches():
    """Test HealthcareClassifier with healthcare-oriented dataset profile."""
    classifier = HealthcareClassifier()

    columns = [
        create_column("patient_id", SemanticType.CUSTOMER),
        create_column("admission_date", SemanticType.DATE),
        create_column("treatment_cost", SemanticType.COST),
        create_column("doctor", SemanticType.EMPLOYEE),
        create_column("diagnosis", SemanticType.UNKNOWN),
        create_column("prescription", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="patient_records.csv",
        total_rows=300,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.HEALTHCARE
    assert result.confidence >= 0.5
    assert len(result.evidence) > 0


def test_marketing_classifier_matches():
    """Test MarketingClassifier with marketing-oriented dataset profile."""
    classifier = MarketingClassifier()

    columns = [
        create_column("lead_id", SemanticType.CUSTOMER),
        create_column("campaign_name", SemanticType.UNKNOWN),
        create_column("ad_spend", SemanticType.COST),
        create_column("conversions", SemanticType.REVENUE),
        create_column("click_date", SemanticType.DATE),
        create_column("ctr", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="campaign_performance.csv",
        total_rows=500,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.MARKETING
    assert result.confidence >= 0.5
    assert len(result.evidence) > 0


def test_logistics_classifier_matches():
    """Test LogisticsClassifier with logistics-oriented dataset profile."""
    classifier = LogisticsClassifier()

    columns = [
        create_column("shipment_id", SemanticType.IDENTIFIER),
        create_column("item_sku", SemanticType.PRODUCT),
        create_column("quantity_shipped", SemanticType.QUANTITY),
        create_column("destination_city", SemanticType.REGION),
        create_column("delivery_date", SemanticType.DATE),
        create_column("carrier", SemanticType.UNKNOWN),
        create_column("tracking_no", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="freight_logistics.csv",
        total_rows=400,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.LOGISTICS
    assert result.confidence >= 0.6
    assert len(result.evidence) > 0
