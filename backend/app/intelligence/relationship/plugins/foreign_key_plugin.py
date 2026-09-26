from typing import Optional

import pandas as pd

from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class ForeignKeyDetectorPlugin(BaseRelationshipPlugin):
    """
    Detects candidate Foreign Keys referencing entity identifiers (e.g. customer_id, product_id, department_id).
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
            # Foreign keys usually have duplicates (unique=False) and referential naming
            col_lower = col.name.lower()

            if not col.unique and any(col_lower.endswith(suffix) for suffix in ["_id", "_key", "_code", "_pk", "_uuid"]):
                target_entity = col_lower.split("_")[0].title()
                rel = EntityRelationship(
                    source_column=col.name,
                    target_column=f"{target_entity}.id",
                    relationship_type="FOREIGN_KEY",
                    cardinality="MANY_TO_ONE",
                    confidence=0.90,
                    reasoning=f"Column '{col.name}' exhibits foreign key naming pattern referencing entity '{target_entity}'.",
                    evidence=(
                        f"Column Name: {col.name}",
                        f"Unique: {col.unique}",
                        f"Inferred Target: {target_entity}",
                    ),
                )
                relationships.append(rel)

        return tuple(relationships)
