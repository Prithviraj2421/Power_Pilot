from dataclasses import dataclass, field
from typing import Optional

from app.common.enums import DatasetDomain


@dataclass(slots=True, frozen=True)
class EntityRelationship:
    """
    Immutable representation of a structural, statistical, or semantic relationship.
    """

    source_column: str
    target_column: str
    relationship_type: str  # 'PRIMARY_KEY', 'FOREIGN_KEY', 'PARENT_CHILD', 'CORRELATION_LINK', 'SEMANTIC_LINK'
    cardinality: str  # 'ONE_TO_ONE', 'ONE_TO_MANY', 'MANY_TO_MANY'
    confidence: float
    reasoning: str
    evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class RelationshipReport:
    """
    Unified immutable report detailing all identified relationships across a dataset.
    """

    primary_keys: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    foreign_keys: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    hierarchies: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    correlations: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    semantic_links: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    all_relationships: tuple[EntityRelationship, ...] = field(default_factory=tuple)
    domain: DatasetDomain = DatasetDomain.UNKNOWN
