"""
Relationship Engine plugin registry.

Exports all concrete relationship detector plugin classes and the canonical priority registry.
"""

from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.intelligence.relationship.plugins.correlation_link_plugin import CorrelationLinkagePlugin
from app.intelligence.relationship.plugins.foreign_key_plugin import ForeignKeyDetectorPlugin
from app.intelligence.relationship.plugins.hierarchy_plugin import HierarchicalRelationshipPlugin
from app.intelligence.relationship.plugins.primary_key_plugin import PrimaryKeyDetectorPlugin
from app.intelligence.relationship.plugins.semantic_link_plugin import SemanticLinkagePlugin

RELATIONSHIP_ENGINE_REGISTRY: tuple[type[BaseRelationshipPlugin], ...] = (
    PrimaryKeyDetectorPlugin,
    ForeignKeyDetectorPlugin,
    HierarchicalRelationshipPlugin,
    CorrelationLinkagePlugin,
    SemanticLinkagePlugin,
)

__all__ = [
    "BaseRelationshipPlugin",
    "PrimaryKeyDetectorPlugin",
    "ForeignKeyDetectorPlugin",
    "HierarchicalRelationshipPlugin",
    "CorrelationLinkagePlugin",
    "SemanticLinkagePlugin",
    "RELATIONSHIP_ENGINE_REGISTRY",
]
