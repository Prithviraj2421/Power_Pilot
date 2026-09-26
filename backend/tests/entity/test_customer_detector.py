import pytest
import pandas as pd
from typing import Any

from app.models.column_profile import ColumnProfile
from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.detectors.customer_detector import CustomerDetector


@pytest.fixture
def detector() -> CustomerDetector:
    """Provides a CustomerDetector instance for testing."""
    return CustomerDetector()


def create_column(name: str, physical_type: PhysicalType, sample_values: list[Any] = None) -> ColumnProfile:
    """Helper to create a ColumnProfile with default values for required fields."""
    return ColumnProfile(
        name=name,
        physical_type=physical_type,
        nullable=True,
        unique=False,
        identifier=False,
        missing_count=0,
        unique_count=0,
        sample_values=sample_values or []
    )


def test_customer_detector_customer_id(detector: CustomerDetector) -> None:
    """Test CustomerDetector with 'customer_id' column."""
    col = create_column("customer_id", PhysicalType.TEXT, ["cust_001", "cust_002"])
    result = detector.detect(col)
    
    assert result is not None
    assert result.semantic_type == SemanticType.CUSTOMER
    assert result.confidence == 0.6  # 0.4 for keyword + 0.2 for text type
    assert any("contains customer keywords" in ev for ev in result.evidence)
    assert any("categorical/text" in ev for ev in result.evidence)


def test_customer_detector_client_name(detector: CustomerDetector) -> None:
    """Test CustomerDetector with 'client_name' column."""
    col = create_column("client_name", PhysicalType.TEXT, ["Acme Corp", "Globex"])
    result = detector.detect(col)
    
    assert result is not None
    assert result.semantic_type == SemanticType.CUSTOMER
    assert result.confidence == 0.6
    assert any("contains customer keywords" in ev for ev in result.evidence)


def test_customer_detector_email(detector: CustomerDetector) -> None:
    """Test CustomerDetector with 'email' column containing valid emails."""
    col = create_column("email", PhysicalType.TEXT, ["user@example.com", "admin@test.com"])
    result = detector.detect(col)
    
    assert result is not None
    assert result.semantic_type == SemanticType.CUSTOMER
    # 0.4 keyword + 0.2 text type + 0.4 email/phone match
    assert result.confidence == 1.0
    assert any("emails or phone numbers" in ev for ev in result.evidence)


def test_customer_detector_phone(detector: CustomerDetector) -> None:
    """Test CustomerDetector with 'phone' column containing valid phone numbers."""
    col = create_column("phone", PhysicalType.TEXT, ["+1-555-0123", "(555) 123-4567"])
    result = detector.detect(col)
    
    assert result is not None
    assert result.semantic_type == SemanticType.CUSTOMER
    assert result.confidence == 1.0
    assert any("emails or phone numbers" in ev for ev in result.evidence)


def test_customer_detector_account_number(detector: CustomerDetector) -> None:
    """Test CustomerDetector with 'account_number' column (may not match full keyword)."""
    col = create_column("account_number", PhysicalType.TEXT, ["Acc 1", "Acc 2"])
    result = detector.detect(col)
    
    # Since 'account_number' doesn't contain 'account_name', it might not match keyword
    assert result is None


def test_customer_detector_random_col(detector: CustomerDetector) -> None:
    """Test CustomerDetector with a non-matching 'random_col'."""
    col = create_column("random_col", PhysicalType.TEXT, ["val1", "val2"])
    result = detector.detect(col)
    
    assert result is None
