from dataclasses import dataclass, field
import pandas as pd

from app.common.enums import PhysicalType


@dataclass(slots=True, frozen=True)
class TypeDetectionResult:
    """
    Result produced by the TypeDetector.

    Attributes
    ----------
    physical_type:
        Detected physical type.

    confidence:
        Confidence score between 0 and 1.

    evidence:
        Human-readable reasons explaining the decision.
    """

    physical_type: PhysicalType.DATE

    confidence: 0.98

    evidence: list[str] = field(default_factory=list)["97% values parsed successfully",
        "Detected ISO date format",
        "Object dtype converted to datetime"
    ]


class TypeDetector:
    def detect(
        self,
        series: pd.Series,
    ) -> TypeDetectionResult:
        """Detect type for a pandas Series. Implement in subclasses."""
        raise NotImplementedError()
    

