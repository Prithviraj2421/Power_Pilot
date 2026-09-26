import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.domain.classifiers.finance_classifier import FinanceClassifier
from app.intelligence.domain.classifiers.hr_classifier import HRClassifier
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile


def create_column(name: str, semantic_type: SemanticType) -> ColumnProfile:
    """Helper to construct ColumnProfile objects for domain classification tests."""
    return ColumnProfile(
        name=name,
        physical_type=PhysicalType.FLOAT if semantic_type in (SemanticType.REVENUE, SemanticType.PROFIT, SemanticType.COST) else PhysicalType.TEXT,
        nullable=False,
        unique=False,
        identifier=False,
        missing_count=0,
        unique_count=10,
        semantic_type=semantic_type,
    )


def test_finance_classifier_matches():
    """Test FinanceClassifier with finance-oriented dataset profile."""
    classifier = FinanceClassifier()

    columns = [
        create_column("revenue", SemanticType.REVENUE),
        create_column("net_profit", SemanticType.PROFIT),
        create_column("cogs", SemanticType.COST),
        create_column("trans_date", SemanticType.DATE),
        create_column("ledger_id", SemanticType.IDENTIFIER),
        create_column("balance", SemanticType.UNKNOWN),
        create_column("tax", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="financial_ledger.csv",
        total_rows=200,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.FINANCE
    assert result.confidence >= 0.7
    assert SemanticType.REVENUE in result.matched_entities
    assert SemanticType.PROFIT in result.matched_entities
    assert len(result.evidence) > 0
    assert len(result.reasoning) > 0


def test_hr_classifier_matches():
    """Test HRClassifier with HR-oriented dataset profile."""
    classifier = HRClassifier()

    columns = [
        create_column("employee_id", SemanticType.EMPLOYEE),
        create_column("hire_date", SemanticType.DATE),
        create_column("salary", SemanticType.COST),
        create_column("department", SemanticType.UNKNOWN),
        create_column("position", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="employee_directory.csv",
        total_rows=150,
        total_columns=len(columns),
        columns=columns,
    )

    result = classifier.classify(profile)

    assert result.domain == DatasetDomain.HR
    assert result.confidence >= 0.6
    assert SemanticType.EMPLOYEE in result.matched_entities
    assert len(result.evidence) > 0
    assert len(result.reasoning) > 0
