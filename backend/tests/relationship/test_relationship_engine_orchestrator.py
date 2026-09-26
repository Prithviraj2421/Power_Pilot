import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.relationship_engine import RelationshipEngine
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship, RelationshipReport


def make_col(name: str, ptype: PhysicalType, nullable: bool = False, unique: bool = False, identifier: bool = False, stype: SemanticType = SemanticType.UNKNOWN) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        physical_type=ptype,
        nullable=nullable,
        unique=unique,
        identifier=identifier,
        missing_count=0 if not nullable else 5,
        unique_count=100 if unique else 10,
        semantic_type=stype,
    )


def test_relationship_engine_orchestrator() -> None:
    engine = RelationshipEngine()

    cols = [
        make_col("order_id", PhysicalType.INTEGER, nullable=False, unique=True, identifier=True),
        make_col("customer_id", PhysicalType.INTEGER, nullable=False, unique=False, stype=SemanticType.CUSTOMER),
        make_col("Category", PhysicalType.TEXT),
        make_col("Subcategory", PhysicalType.TEXT),
        make_col("revenue", PhysicalType.FLOAT, stype=SemanticType.REVENUE),
    ]
    profile = DatasetProfile(dataset_name="orders.csv", total_rows=100, total_columns=5, columns=cols, detected_domain=DatasetDomain.RETAIL)

    entities = [
        DetectedEntity(column_name="customer_id", entity_type="CUSTOMER", confidence=0.95, reason="Customer ID"),
        DetectedEntity(column_name="revenue", entity_type="REVENUE", confidence=0.90, reason="Sales Revenue"),
    ]

    report = engine.analyze(profile, entities=entities)

    assert isinstance(report, RelationshipReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.primary_keys) == 1
    assert report.primary_keys[0].source_column == "order_id"
    assert len(report.foreign_keys) == 1
    assert report.foreign_keys[0].source_column == "customer_id"
    assert len(report.hierarchies) == 1
    assert report.hierarchies[0].source_column == "Category"
    assert len(report.semantic_links) >= 1
    assert len(report.all_relationships) >= 4
