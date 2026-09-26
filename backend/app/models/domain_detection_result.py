from dataclasses import dataclass, field

from app.common.enums import DatasetDomain, SemanticType


@dataclass(slots=True, frozen=True)
class DomainDetectionResult:
    """
    Immutable value object representing the outcome of domain classification
    by a domain plugin classifier.

    Attributes
    ----------
    domain : DatasetDomain
        The candidate dataset domain evaluated by this classifier.
    confidence : float
        Confidence score between 0.0 and 1.0.
    matched_entities : tuple[SemanticType, ...]
        Tuple of semantic entity types present in the dataset that support this domain.
    missing_entities : tuple[SemanticType, ...]
        Tuple of expected primary semantic entity types that were absent.
    evidence : tuple[str, ...]
        Detailed human-readable evidence strings explaining the score calculation.
    reasoning : str
        High-level summary explanation of why this domain matched or failed to match.
    """

    domain: DatasetDomain
    confidence: float
    matched_entities: tuple[SemanticType, ...] = field(default_factory=tuple)
    missing_entities: tuple[SemanticType, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)
    reasoning: str = ""

    def __post_init__(self) -> None:
        """Validate confidence score invariant."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.confidence}"
            )
