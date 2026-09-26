from typing import Optional

import pandas as pd

from app.common.enums import SemanticType
from app.intelligence.relationship.base_relationship_plugin import BaseRelationshipPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class SemanticLinkagePlugin(BaseRelationshipPlugin):
    """
    Detects semantic relationships based on annotated semantic entities (e.g. Customer -> Revenue, Product -> Cost).
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

        entity_cols: dict[str, list[str]] = {}

        if dataset_profile and dataset_profile.columns:
            for col in dataset_profile.columns:
                if hasattr(col, "semantic_type") and col.semantic_type and col.semantic_type != SemanticType.UNKNOWN:
                    stype_str = col.semantic_type.value.upper() if isinstance(col.semantic_type, SemanticType) else str(col.semantic_type).upper()
                    entity_cols.setdefault(stype_str, []).append(col.name)

        if entities:
            for ent in entities:
                stype_str = getattr(ent, "entity_type", getattr(ent, "semantic_type", "")).upper()
                if hasattr(stype_str, "value"):
                    stype_str = stype_str.value.upper()
                entity_cols.setdefault(str(stype_str), []).append(ent.column_name)

        # Semantic association pairs
        association_rules = [
            ("CUSTOMER", "REVENUE", "ONE_TO_MANY", "Customer purchasing generates Revenue."),
            ("PRODUCT", "REVENUE", "ONE_TO_MANY", "Product sales generate Revenue."),
            ("PRODUCT", "QUANTITY", "ONE_TO_MANY", "Product sales track Quantity."),
            ("PRODUCT", "COST", "ONE_TO_MANY", "Product manufacturing drives Cost."),
            ("EMPLOYEE", "COST", "ONE_TO_MANY", "Employee staffing drives Cost/Payroll."),
        ]

        for source_type, target_type, card, desc in association_rules:
            if source_type in entity_cols and target_type in entity_cols:
                for src_col in entity_cols[source_type]:
                    for tgt_col in entity_cols[target_type]:
                        rel = EntityRelationship(
                            source_column=src_col,
                            target_column=tgt_col,
                            relationship_type="SEMANTIC_LINK",
                            cardinality=card,
                            confidence=0.85,
                            reasoning=desc,
                            evidence=(
                                f"Source Entity: {source_type}",
                                f"Target Entity: {target_type}",
                            ),
                        )
                        relationships.append(rel)

        return tuple(relationships)
