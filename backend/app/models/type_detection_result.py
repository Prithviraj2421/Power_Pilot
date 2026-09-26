from dataclasses import dataclass, field
from app.common.enums import PhysicalType


@dataclass(slots=True, frozen=True)
class TypeDetectionResult:
    """
    Immutable result produced by a type detector plugin.

    Each detector returns this value object when it successfully
    recognizes a column's physical type. The confidence score and
    evidence trail make the detection explainable and auditable.

    Attributes
    ----------
    physical_type : PhysicalType
        The detected physical type of the column.

    confidence : float
        Confidence score between 0.0 (no confidence) and 1.0 (certain).

    evidence : tuple[str, ...]
        Human-readable reasons explaining why this type was chosen.
        Uses a tuple (not list) to preserve immutability of the frozen dataclass.
    """

    physical_type: PhysicalType
    confidence: float
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate invariants after construction."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
