import pytest

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.relationship.plugins.foreign_key_plugin import ForeignKeyDetectorPlugin
from app.intelligence.relationship.plugins.hierarchy_plugin import HierarchicalRelationshipPlugin
from app.intelligence.relationship.plugins.primary_key_plugin import PrimaryKeyDetectorPlugin
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.relationship_models import EntityRelationship


def make_col(name: str, ptype: PhysicalType, nullable: bool = True, unique: bool = False, identifier: bool = False) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        physical_type=ptype,
        nullable=nullable,
        unique=unique,
        identifier=identifier,
        missing_count=0 if not nullable else 5,
        unique_count=100 if unique else 10,
    )


def test_primary_key_plugin() -> None:
    plugin = PrimaryKeyDetectorPlugin()

    cols = [
        make_col("order_id", PhysicalType.INTEGER, nullable=False, unique=True, identifier=True),
        make_col("customer_name", PhysicalType.TEXT, nullable=True, unique=False),
    ]
    profile = DatasetProfile(dataset_name="orders.csv", total_rows=100, total_columns=2, columns=cols)

    results = plugin.analyze(profile)
    assert isinstance(results, tuple)
    assert len(results) == 1
    rel = results[0]
    assert isinstance(rel, EntityRelationship)
    assert rel.relationship_type == "PRIMARY_KEY"
    assert rel.source_column == "order_id"
    assert rel.confidence >= 0.9


def test_foreign_key_plugin() -> None:
    plugin = ForeignKeyDetectorPlugin()

    cols = [
        make_col("order_id", PhysicalType.INTEGER, nullable=False, unique=True, identifier=True),
        make_col("customer_id", PhysicalType.INTEGER, nullable=False, unique=False),
    ]
    profile = DatasetProfile(dataset_name="orders.csv", total_rows=100, total_columns=2, columns=cols)

    results = plugin.analyze(profile)
    assert isinstance(results, tuple)
    assert len(results) == 1
    rel = results[0]
    assert isinstance(rel, EntityRelationship)
    assert rel.relationship_type == "FOREIGN_KEY"
    assert rel.source_column == "customer_id"
    assert rel.cardinality == "MANY_TO_ONE"


def test_hierarchy_plugin() -> None:
    plugin = HierarchicalRelationshipPlugin()

    cols = [
        make_col("Category", PhysicalType.TEXT),
        make_col("Subcategory", PhysicalType.TEXT),
    ]
    profile = DatasetProfile(dataset_name="products.csv", total_rows=50, total_columns=2, columns=cols)

    results = plugin.analyze(profile)
    assert isinstance(results, tuple)
    assert len(results) == 1
    rel = results[0]
    assert isinstance(rel, EntityRelationship)
    assert rel.relationship_type == "PARENT_CHILD"
    assert rel.source_column == "Category"
    assert rel.target_column == "Subcategory"
