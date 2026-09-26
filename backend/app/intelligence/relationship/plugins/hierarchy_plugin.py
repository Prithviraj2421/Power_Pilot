from typing import Optional

import pandas as pd

from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class HierarchicalRelationshipPlugin(BaseRelationshipPlugin):
    """
    Detects Parent-Child dimensional hierarchies (e.g. Category -> Subcategory, Country -> City).
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

        col_names = [col.name for col in dataset_profile.columns]
        col_lower_map = {col.name.lower(): col.name for col in dataset_profile.columns}

        # Hierarchy pairs
        hierarchy_patterns = [
            ("category", "subcategory"),
            ("category", "product_name"),
            ("department", "team"),
            ("country", "state"),
            ("country", "city"),
            ("state", "city"),
            ("region", "country"),
            ("year", "quarter"),
            ("year", "month"),
        ]

        for parent_key, child_key in hierarchy_patterns:
            if parent_key in col_lower_map and child_key in col_lower_map:
                parent_col = col_lower_map[parent_key]
                child_col = col_lower_map[child_key]

                rel = EntityRelationship(
                    source_column=parent_col,
                    target_column=child_col,
                    relationship_type="PARENT_CHILD",
                    cardinality="ONE_TO_MANY",
                    confidence=0.88,
                    reasoning=f"Parent-Child dimensional hierarchy detected between '{parent_col}' and '{child_col}'.",
                    evidence=(
                        f"Parent Column: {parent_col}",
                        f"Child Column: {child_col}",
                    ),
                )
                relationships.append(rel)

        return tuple(relationships)
