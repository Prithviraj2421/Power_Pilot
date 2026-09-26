from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class IdentifierResult:
    """
    Result of identifier detection for a single column.

    Captures whether a column appears to be a primary key or unique
    identifier, along with the confidence level and reasoning.

    Attributes
    ----------
    is_identifier : bool
        Whether the column is detected as an identifier.

    confidence : float
        Confidence score between 0.0 and 1.0.

    evidence : tuple[str, ...]
        Human-readable reasons explaining the decision.
    """

    is_identifier: bool
    confidence: float
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate invariants after construction."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
