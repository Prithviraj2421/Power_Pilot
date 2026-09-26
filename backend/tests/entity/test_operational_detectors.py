import pytest
from typing import Any

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.detectors.date_detector import DateDetector
from app.intelligence.entity.detectors.employee_detector import EmployeeDetector
from app.intelligence.entity.detectors.identifier_detector import IdentifierDetector
from app.intelligence.entity.detectors.product_detector import ProductDetector
from app.intelligence.entity.detectors.region_detector import RegionDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


def create_column(
    name: str,
    physical_type: PhysicalType,
    identifier: bool = False,
    sample_values: list[Any] = None,
) -> ColumnProfile:
    """Helper to create a ColumnProfile for testing."""
    return ColumnProfile(
        name=name,
        physical_type=physical_type,
        nullable=True,
        unique=False,
        identifier=identifier,
        missing_count=0,
        unique_count=0,
        sample_values=sample_values or [],
    )


def test_product_detector_matches():
    """Test ProductDetector correctly identifies product-related columns."""
    detector = ProductDetector()

    for name in ["product_name", "sku", "item_category"]:
        col = create_column(name=name, physical_type=PhysicalType.TEXT)
        result = detector.detect(col)
        assert isinstance(result, EntityDetectionResult), f"Failed for {name}"
        assert result.semantic_type == SemanticType.PRODUCT


def test_product_detector_ignores_non_matching():
    """Test ProductDetector ignores non-product columns."""
    detector = ProductDetector()
    col = create_column(name="customer_id", physical_type=PhysicalType.TEXT)
    assert detector.detect(col) is None


def test_date_detector_matches():
    """Test DateDetector correctly identifies date-related columns."""
    detector = DateDetector()

    for name in ["order_date", "created_at"]:
        col = create_column(name=name, physical_type=PhysicalType.DATETIME)
        result = detector.detect(col)
        assert isinstance(result, EntityDetectionResult), f"Failed for {name}"
        assert result.semantic_type == SemanticType.DATE


def test_date_detector_ignores_non_matching():
    """Test DateDetector ignores non-date columns."""
    detector = DateDetector()
    col = create_column(name="price", physical_type=PhysicalType.FLOAT)
    assert detector.detect(col) is None


def test_region_detector_matches():
    """Test RegionDetector correctly identifies region-related columns."""
    detector = RegionDetector()

    for name in ["state", "country", "zip_code"]:
        col = create_column(name=name, physical_type=PhysicalType.TEXT)
        result = detector.detect(col)
        assert isinstance(result, EntityDetectionResult), f"Failed for {name}"
        assert result.semantic_type == SemanticType.REGION


def test_employee_detector_matches():
    """Test EmployeeDetector correctly identifies employee-related columns."""
    detector = EmployeeDetector()

    for name in ["employee_name", "staff_id", "sales_rep"]:
        col = create_column(name=name, physical_type=PhysicalType.TEXT)
        result = detector.detect(col)
        assert isinstance(result, EntityDetectionResult), f"Failed for {name}"
        assert result.semantic_type == SemanticType.EMPLOYEE


def test_identifier_detector_matches():
    """Test IdentifierDetector correctly identifies identifier columns."""
    detector = IdentifierDetector()

    # Matching by property
    col1 = create_column(name="some_id", physical_type=PhysicalType.TEXT, identifier=True)
    result1 = detector.detect(col1)
    assert isinstance(result1, EntityDetectionResult)
    assert result1.semantic_type == SemanticType.IDENTIFIER

    # Matching by name
    for name in ["uuid", "pk"]:
        col = create_column(name=name, physical_type=PhysicalType.TEXT, identifier=False)
        result = detector.detect(col)
        assert isinstance(result, EntityDetectionResult), f"Failed for {name}"
        assert result.semantic_type == SemanticType.IDENTIFIER
