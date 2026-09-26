from typing import Optional

import pandas as pd

from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class CorrelationLinkagePlugin(BaseRelationshipPlugin):
    """
    Detects statistical correlation linkages between measure columns.
    """

    def analyze(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[EntityRelationship, ...]:
        relationships = []

        if intelligence_report and intelligence_report.correlations:
            for corr in intelligence_report.correlations:
                if abs(corr.coefficient) >= 0.6:
                    rel = EntityRelationship(
                        source_column=corr.column_a,
                        target_column=corr.column_b,
                        relationship_type="CORRELATION_LINK",
                        cardinality="MANY_TO_MANY",
                        confidence=corr.confidence,
                        reasoning=f"Strong statistical correlation (r={corr.coefficient:.2f}) links '{corr.column_a}' and '{corr.column_b}'.",
                        evidence=(
                            f"Pearson r: {corr.coefficient:.4f}",
                            f"Type: {corr.correlation_type}",
                        ),
                    )
                    relationships.append(rel)

        return tuple(relationships)
