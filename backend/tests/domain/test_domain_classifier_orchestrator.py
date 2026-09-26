import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.domain_classifier import DomainClassifier
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.domain_detection_result import DomainDetectionResult


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


def test_domain_classifier_orchestrator_retail():
    """Test DomainClassifier orchestrator correctly ranks RETAIL as top candidate."""
    orchestrator = DomainClassifier()

    columns = [
        create_column("customer_id", SemanticType.CUSTOMER),
        create_column("sku", SemanticType.PRODUCT),
        create_column("sales_amount", SemanticType.REVENUE),
        create_column("qty", SemanticType.QUANTITY),
        create_column("store_location", SemanticType.REGION),
    ]

    profile = DatasetProfile(
        dataset_name="pos_transactions.csv",
        total_rows=1000,
        total_columns=len(columns),
        columns=columns,
    )

    candidates = orchestrator.classify(profile)

    assert isinstance(candidates, list)
    assert len(candidates) == 6
    assert all(isinstance(c, DomainDetectionResult) for c in candidates)

    # First candidate should be Retail
    top_candidate = candidates[0]
    assert top_candidate.domain == DatasetDomain.RETAIL
    assert top_candidate.confidence >= 0.5

    # DatasetProfile enrichment
    assert profile.detected_domain == DatasetDomain.RETAIL
    assert profile.domain_confidence == top_candidate.confidence
    assert len(profile.candidate_domains) == 6


def test_domain_classifier_orchestrator_finance():
    """Test DomainClassifier orchestrator correctly ranks FINANCE as top candidate."""
    orchestrator = DomainClassifier()

    columns = [
        create_column("gross_revenue", SemanticType.REVENUE),
        create_column("net_profit", SemanticType.PROFIT),
        create_column("cogs", SemanticType.COST),
        create_column("posting_date", SemanticType.DATE),
        create_column("ledger_account", SemanticType.IDENTIFIER),
        create_column("balance", SemanticType.UNKNOWN),
    ]

    profile = DatasetProfile(
        dataset_name="general_ledger.csv",
        total_rows=500,
        total_columns=len(columns),
        columns=columns,
    )

    candidates = orchestrator.classify(profile)

    assert candidates[0].domain == DatasetDomain.FINANCE
    assert profile.detected_domain == DatasetDomain.FINANCE


def test_domain_classifier_orchestrator_empty():
    """Test DomainClassifier orchestrator handles empty profiles gracefully."""
    orchestrator = DomainClassifier()

    profile = DatasetProfile(
        dataset_name="empty.csv",
        total_rows=0,
        total_columns=0,
        columns=[],
    )

    candidates = orchestrator.classify(profile)

    assert len(candidates) == 6
    assert profile.detected_domain == DatasetDomain.UNKNOWN
    assert profile.domain_confidence == 0.0
