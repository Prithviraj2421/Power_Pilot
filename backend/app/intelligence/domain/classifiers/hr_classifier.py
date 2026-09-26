from typing import Any

from app.intelligence.domain.base_domain_classifier import BaseDomainClassifier
from app.models.domain_detection_result import DomainDetectionResult
from app.common.enums import DatasetDomain, SemanticType


class HRClassifier(BaseDomainClassifier):
    """
    Domain classifier for the HR (Human Resources) domain.
    Identifies if a dataset belongs to the HR domain based on schema and semantic types.
    """
    
    PRIMARY_ENTITIES = {
        SemanticType.EMPLOYEE,
        SemanticType.DATE
    }
    
    SECONDARY_ENTITIES = {
        SemanticType.COST,
        SemanticType.REGION,
        SemanticType.IDENTIFIER
    }
    
    KEYWORDS = {
        "salary", "department", "hire_date", "performance", "tenure", 
        "position", "manager", "benefit", "payroll", "employee", 
        "staff", "hr", "headcount", "compensation", "leave"
    }

    def classify(self, profile: Any) -> DomainDetectionResult:
        """
        Classify the dataset profile to determine its match with the HR domain.
        
        Args:
            profile: The dataset profile containing columns with semantic types.
            
        Returns:
            DomainDetectionResult: The domain detection result with confidence and reasoning.
        """
        found_entities = set()
        column_names = []
        
        for col in getattr(profile, "columns", []):
            if hasattr(col, "semantic_type") and col.semantic_type:
                found_entities.add(col.semantic_type)
            if hasattr(col, "name") and col.name:
                column_names.append(str(col.name).lower())
                
        # 1. matched_entities: tuple of SemanticTypes found in profile.columns that match primary/secondary
        matched_entities_set = found_entities.intersection(self.PRIMARY_ENTITIES.union(self.SECONDARY_ENTITIES))
        matched_entities = tuple(matched_entities_set)
        
        # 2. missing_entities: tuple of primary expected SemanticTypes not found
        missing_entities_set = self.PRIMARY_ENTITIES - found_entities
        missing_entities = tuple(missing_entities_set)
        
        # 3. evidence: tuple of strings explaining matches
        evidence_list = []
        keyword_matches = sum(1 for name in column_names for kw in self.KEYWORDS if kw in name)
        
        if keyword_matches > 0:
            evidence_list.append(f"Found {keyword_matches} column name(s) matching HR keywords.")
            
        primary_overlap = len(self.PRIMARY_ENTITIES.intersection(found_entities))
        if primary_overlap > 0:
            evidence_list.append(f"Matched {primary_overlap}/{len(self.PRIMARY_ENTITIES)} primary HR entities.")
            
        secondary_overlap = len(self.SECONDARY_ENTITIES.intersection(found_entities))
        if secondary_overlap > 0:
            evidence_list.append(f"Matched {secondary_overlap}/{len(self.SECONDARY_ENTITIES)} secondary HR entities.")
            
        evidence = tuple(evidence_list)
        
        # 5. confidence: score between 0.0 and 1.0
        primary_score = (primary_overlap / len(self.PRIMARY_ENTITIES)) * 0.6 if self.PRIMARY_ENTITIES else 0.0
        secondary_score = (secondary_overlap / len(self.SECONDARY_ENTITIES)) * 0.2 if self.SECONDARY_ENTITIES else 0.0
        keyword_score = min((keyword_matches / 2), 1.0) * 0.2
        
        confidence = round(primary_score + secondary_score + keyword_score, 4)
        
        # 4. reasoning: clear string summarizing why this domain matched or failed to match
        if confidence > 0.6:
            reasoning = "Strong match for HR domain due to significant overlap with HR entities and keywords."
        elif confidence > 0.3:
            reasoning = "Partial match for HR domain based on some HR evidence."
        else:
            reasoning = "Insufficient evidence to classify as HR domain."
            
        return DomainDetectionResult(
            domain=DatasetDomain.HR,
            confidence=confidence,
            matched_entities=matched_entities,
            missing_entities=missing_entities,
            evidence=evidence,
            reasoning=reasoning
        )
