import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.domain.classifiers.retail_classifier import RetailClassifier
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile


def create_column(name: str, semantic_type: SemanticType) -> ColumnProfile:
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


def test_retail_classifier_with_retail_dataset() -> None:
    """Test that RetailClassifier identifies a retail dataset with high confidence."""
    classifier = RetailClassifier()

    columns = [
        create_column("customer_id", SemanticType.CUSTOMER),
        create_column("sku", SemanticType.PRODUCT),
        create_column("sales_amount", SemanticType.REVENUE),
        create_column("qty", SemanticType.QUANTITY),
    ]

    profile = DatasetProfile(
        dataset_name="retail_sales.csv",
        total_rows=100,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.RETAIL
    assert result.confidence >= 0.6
    assert SemanticType.CUSTOMER in result.matched_entities
    assert SemanticType.PRODUCT in result.matched_entities
    assert SemanticType.REVENUE in result.matched_entities
    assert SemanticType.QUANTITY in result.matched_entities
    assert len(result.evidence) > 0
    assert len(result.reasoning) > 0


def test_retail_classifier_with_non_retail_dataset() -> None:
    """Test that RetailClassifier returns low confidence for non-retail data."""
    classifier = RetailClassifier()

    columns = [
        create_column("employee_id", SemanticType.EMPLOYEE),
        create_column("hire_date", SemanticType.DATE),
        create_column("department", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="hr_roster.csv",
        total_rows=50,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.RETAIL
    assert result.confidence <= 0.3
    assert SemanticType.PRODUCT in result.missing_entities
    assert SemanticType.REVENUE in result.missing_entities
