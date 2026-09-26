import pytest
import pandas as pd

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity_detector import EntityDetector
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


def create_column(
    name: str,
    physical_type: PhysicalType,
    identifier: bool = False,
) -> ColumnProfile:
    """Helper to create a ColumnProfile for testing."""
    return ColumnProfile(
        name=name,
        physical_type=physical_type,
        nullable=False,
        unique=False,
        identifier=identifier,
        missing_count=0,
        unique_count=10,
    )


def test_entity_detector_orchestrator():
    """
    Test that EntityDetector main facade correctly orchestrates multiple detectors.
    Constructs a DatasetProfile with multiple ColumnProfile objects, runs EntityDetector().detect(profile, df),
    and asserts DetectedEntity objects are returned and column.semantic_type is enriched.
    """
    # Arrange
    orchestrator = EntityDetector()

    customer_id_col = create_column("customer_id", PhysicalType.TEXT, identifier=True)
    order_date_col = create_column("order_date", PhysicalType.DATETIME)
    sales_amount_col = create_column("sales_amount", PhysicalType.FLOAT)
    qty_col = create_column("qty", PhysicalType.INTEGER)
    product_sku_col = create_column("product_sku", PhysicalType.TEXT)

    columns = [
        customer_id_col,
        order_date_col,
        sales_amount_col,
        qty_col,
        product_sku_col,
    ]

    profile = DatasetProfile(
        dataset_name="test_dataset.csv",
        total_rows=2,
        total_columns=len(columns),
        columns=columns,
    )

    df = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "order_date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        "sales_amount": [100.5, 200.0],
        "qty": [1, 2],
        "product_sku": ["SKU-1", "SKU-2"],
    })

    # Act
    detected_entities = orchestrator.detect(profile, df)

    # Assert
    assert isinstance(detected_entities, list)
    assert all(isinstance(entity, DetectedEntity) for entity in detected_entities)

    entities_by_col = {entity.column_name: entity for entity in detected_entities}

    # Validate specific entities were detected
    assert "customer_id" in entities_by_col
    assert customer_id_col.semantic_type in (SemanticType.CUSTOMER, SemanticType.IDENTIFIER)

    assert "order_date" in entities_by_col
    assert entities_by_col["order_date"].entity_type == SemanticType.DATE.value
    assert order_date_col.semantic_type == SemanticType.DATE

    assert "product_sku" in entities_by_col
    assert entities_by_col["product_sku"].entity_type == SemanticType.PRODUCT.value
    assert product_sku_col.semantic_type == SemanticType.PRODUCT
