"""
Healthcare Domain Classifier Plugin.
"""

from typing import Set, Any, List

from app.intelligence.domain.base_domain_classifier import BaseDomainClassifier
from app.models.domain_detection_result import DomainDetectionResult
from app.common.enums import DatasetDomain, SemanticType
from app.common.keyword_match import contains_keyword


class HealthcareClassifier(BaseDomainClassifier):
    """
    Domain Classifier for detecting Healthcare datasets.
    """

    @property
    def domain(self) -> DatasetDomain:
        """The target dataset domain."""
        return DatasetDomain.HEALTHCARE

    @property
    def primary_entities(self) -> Set[SemanticType]:
        """Primary semantic types expected in healthcare datasets."""
        return {
            SemanticType.CUSTOMER,
            SemanticType.DATE,
            SemanticType.COST,
        }

    @property
    def secondary_entities(self) -> Set[SemanticType]:
        """Secondary semantic types common in healthcare datasets."""
        return {
            SemanticType.EMPLOYEE,
            SemanticType.REGION,
            SemanticType.IDENTIFIER,
        }

    @property
    def keywords(self) -> Set[str]:
        """Keywords commonly found in healthcare dataset column names."""
        return {
            "patient", "doctor", "diagnosis", "hospital", "medical",
            "treatment", "prescription", "claim", "dosage", "admission",
            "clinic", "ehr", "health", "physician", "provider"
        }

    def classify(self, profile: Any) -> DomainDetectionResult:
        """
        Analyzes a dataset profile and evaluates if it belongs to the Healthcare domain.

        Args:
            profile: The dataset profile containing column metadata.

        Returns:
            DomainDetectionResult: The classification outcome with confidence and evidence.
        """
        matched_entities_set: Set[SemanticType] = set()
        matched_keywords: Set[str] = set()
        
        if hasattr(profile, "columns") and profile.columns:
            for col in profile.columns:
                if hasattr(col, "semantic_type") and col.semantic_type:
                    matched_entities_set.add(col.semantic_type)
                
                if hasattr(col, "name") and col.name:
                    col_name = str(col.name).lower()
                    for kw in self.keywords:
                        if contains_keyword(col_name, kw):
                            matched_keywords.add(kw)

        found_primary = self.primary_entities.intersection(matched_entities_set)
        found_secondary = self.secondary_entities.intersection(matched_entities_set)
        
        missing_entities = self.primary_entities - found_primary
        matched_entities = found_primary.union(found_secondary)
        
        primary_ratio = len(found_primary) / len(self.primary_entities) if self.primary_entities else 0.0
        secondary_ratio = len(found_secondary) / len(self.secondary_entities) if self.secondary_entities else 0.0
        keyword_score = min(1.0, len(matched_keywords) / 3.0)

        confidence = (primary_ratio * 0.5) + (secondary_ratio * 0.2) + (keyword_score * 0.3)
        confidence = round(float(confidence), 4)

        evidence: List[str] = []
        if found_primary:
            evidence.append(f"Found {len(found_primary)} out of {len(self.primary_entities)} primary expected entities.")
        if found_secondary:
            evidence.append(f"Found {len(found_secondary)} out of {len(self.secondary_entities)} secondary expected entities.")
        if matched_keywords:
            evidence.append(f"Matched {len(matched_keywords)} relevant column name keywords (e.g., {', '.join(list(matched_keywords)[:3])}).")

        reasoning = (
            f"Dataset yields a {confidence:.4f} confidence score for HEALTHCARE domain based on "
            f"{primary_ratio * 100:.1f}% primary entity overlap and {len(matched_keywords)} keyword matches."
        )

        return DomainDetectionResult(
            domain=self.domain,
            confidence=confidence,
            matched_entities=tuple(matched_entities),
            missing_entities=tuple(missing_entities),
            evidence=tuple(evidence),
            reasoning=reasoning
        )
