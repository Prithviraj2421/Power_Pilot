from dataclasses import dataclass, field
from app.common.enums import SemanticType


@dataclass(slots=True, frozen=True)
class EntityDetectionResult:
    """
    Immutable value object representing the outcome of semantic entity detection
    for a single column.

    Attributes
    ----------
    semantic_type : SemanticType
        The detected semantic entity type.
    confidence : float
        Confidence score between 0.0 and 1.0.
    reason : str
        Summary explanation of why this entity type was detected.
    evidence : tuple[str, ...]
        Detailed human-readable evidence items supporting the score.
    """

    semantic_type: SemanticType
    confidence: float
    reason: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate score invariant."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.confidence}"
            )
