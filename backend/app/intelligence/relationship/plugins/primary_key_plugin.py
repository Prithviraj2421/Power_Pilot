from typing import Optional

import pandas as pd

from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class PrimaryKeyDetectorPlugin(BaseRelationshipPlugin):
    """
    Detects candidate Primary Keys based on 100% uniqueness, non-nullability, and identifier naming heuristics.
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

        for col in dataset_profile.columns:
            if not col.unique or col.nullable:
                continue

            col_lower = col.name.lower()
            is_id_name = any(k in col_lower for k in ["id", "uuid", "pk", "key", "code"]) or col.identifier

            if is_id_name:
                confidence = 0.95 if col.identifier else 0.85
                rel = EntityRelationship(
                    source_column=col.name,
                    target_column=col.name,
                    relationship_type="PRIMARY_KEY",
                    cardinality="ONE_TO_ONE",
                    confidence=confidence,
                    reasoning=f"Column '{col.name}' has 100% uniqueness, zero nulls, and identifier naming heuristics.",
                    evidence=(
                        f"Unique: {col.unique}",
                        f"Nullable: {col.nullable}",
                        f"Identifier Flag: {col.identifier}",
                        f"Physical Type: {col.physical_type.value}",
                    ),
                )
                relationships.append(rel)

        return tuple(relationships)
