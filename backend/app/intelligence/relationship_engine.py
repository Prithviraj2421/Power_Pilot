from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain
from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.intelligence.relationship.plugins import (
    CorrelationLinkagePlugin,
    ForeignKeyDetectorPlugin,
    HierarchicalRelationshipPlugin,
    PrimaryKeyDetectorPlugin,
    SemanticLinkagePlugin,
)
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship, RelationshipReport


class RelationshipEngine:
    """
    Facade orchestrating structural, statistical, and semantic relationship discovery.

    Executes all registered Relationship Engine plugins and synthesizes a unified RelationshipReport.
    """

    def __init__(self) -> None:
        """Initialize all individual relationship detector plugins."""
        self._pk_plugin = PrimaryKeyDetectorPlugin()
        self._fk_plugin = ForeignKeyDetectorPlugin()
        self._hierarchy_plugin = HierarchicalRelationshipPlugin()
        self._correlation_plugin = CorrelationLinkagePlugin()
        self._semantic_plugin = SemanticLinkagePlugin()

    def analyze(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> RelationshipReport:
        """
        Discover relationships across dataset columns.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : Optional[BusinessProfile]
            The executive business profile.
        intelligence_report : Optional[DataIntelligenceReport]
            The data intelligence report.
        entities : Optional[list[DetectedEntity]]
            List of detected semantic entities.
        df : Optional[pd.DataFrame]
            Optional raw dataset DataFrame.

        Returns
        -------
        RelationshipReport
            Unified, explainable relationship report.
        """
        pks = self._run_plugin(self._pk_plugin, dataset_profile, business_profile, intelligence_report, entities, df)
        fks = self._run_plugin(self._fk_plugin, dataset_profile, business_profile, intelligence_report, entities, df)
        hierarchies = self._run_plugin(self._hierarchy_plugin, dataset_profile, business_profile, intelligence_report, entities, df)
        correlations = self._run_plugin(self._correlation_plugin, dataset_profile, business_profile, intelligence_report, entities, df)
        semantics = self._run_plugin(self._semantic_plugin, dataset_profile, business_profile, intelligence_report, entities, df)

        all_rels: list[EntityRelationship] = []
        for group in (pks, fks, hierarchies, correlations, semantics):
            if isinstance(group, (list, tuple)):
                for item in group:
                    if isinstance(item, EntityRelationship):
                        all_rels.append(item)

        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)

        return RelationshipReport(
            primary_keys=tuple(pks) if isinstance(pks, tuple) else (),
            foreign_keys=tuple(fks) if isinstance(fks, tuple) else (),
            hierarchies=tuple(hierarchies) if isinstance(hierarchies, tuple) else (),
            correlations=tuple(correlations) if isinstance(correlations, tuple) else (),
            semantic_links=tuple(semantics) if isinstance(semantics, tuple) else (),
            all_relationships=tuple(all_rels),
            domain=domain,
        )

    def _run_plugin(
        self,
        plugin: BaseRelationshipPlugin,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile],
        intelligence_report: Optional[DataIntelligenceReport],
        entities: Optional[list[DetectedEntity]],
        df: Optional[pd.DataFrame],
    ):
        """Safely execute plugin with exception boundary."""
        try:
            return plugin.analyze(dataset_profile, business_profile, intelligence_report, entities, df)
        except Exception:
            return ()
