import pytest

from app.common.enums import DatasetDomain, PhysicalType, SemanticType
from app.intelligence.relationship.plugins.correlation_link_plugin import CorrelationLinkagePlugin
from app.intelligence.relationship.plugins.semantic_link_plugin import SemanticLinkagePlugin
from app.models.column_profile import ColumnProfile
from app.models.data_intelligence_models import (
    CorrelationResult,
    DataIntelligenceReport,
    QualityReport,
    StatisticalSummary,
)
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


def make_col(name: str, ptype: PhysicalType, stype: SemanticType = SemanticType.UNKNOWN) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        physical_type=ptype,
        nullable=False,
        unique=False,
        identifier=False,
        missing_count=0,
        unique_count=10,
        semantic_type=stype,
    )


def test_correlation_link_plugin() -> None:
    plugin = CorrelationLinkagePlugin()

    profile = DatasetProfile(dataset_name="sales.csv", total_rows=100, total_columns=2)
    correlations = (
        CorrelationResult(column_a="units", column_b="revenue", coefficient=0.92, correlation_type="strong_positive", confidence=0.9, reasoning="Strong correlation", p_value=0.0001, q_value=0.0001, effect_size=abs(0.9), n=60, survived_fdr=True),
    )
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=100.0, completeness_score=100.0, uniqueness_score=100.0, validity_score=100.0, total_issues=0),
        statistical_summary=StatisticalSummary(total_rows=100, numeric_columns_count=2, categorical_columns_count=0, date_columns_count=0),
        correlations=correlations,
        domain=DatasetDomain.RETAIL,
    )

    results = plugin.analyze(profile, intelligence_report=intel_report)
    assert isinstance(results, tuple)
    assert len(results) == 1
    rel = results[0]
    assert isinstance(rel, EntityRelationship)
    assert rel.relationship_type == "CORRELATION_LINK"
    assert rel.source_column == "units"
    assert rel.target_column == "revenue"


def test_semantic_link_plugin() -> None:
    plugin = SemanticLinkagePlugin()

    cols = [
        make_col("customer_id", PhysicalType.INTEGER, stype=SemanticType.CUSTOMER),
        make_col("total_revenue", PhysicalType.FLOAT, stype=SemanticType.REVENUE),
    ]
    profile = DatasetProfile(dataset_name="sales.csv", total_rows=100, total_columns=2, columns=cols)
    entities = [
        DetectedEntity(column_name="customer_id", entity_type="CUSTOMER", confidence=0.95, reason="Customer entity"),
        DetectedEntity(column_name="total_revenue", entity_type="REVENUE", confidence=0.90, reason="Revenue entity"),
    ]

    results = plugin.analyze(profile, entities=entities)
    assert isinstance(results, tuple)
    assert len(results) >= 1
    rel = results[0]
    assert isinstance(rel, EntityRelationship)
    assert rel.relationship_type == "SEMANTIC_LINK"
    assert rel.source_column == "customer_id"
    assert rel.target_column == "total_revenue"
