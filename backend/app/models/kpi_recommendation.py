from dataclasses import dataclass

from app.common.enums import Priority


@dataclass(slots=True, frozen=True)
class KPIRecommendation:
    """
    Represents a KPI recommended by PowerPilot, complete with DAX formula and thresholds.
    """

    name: str
    priority: Priority
    confidence: float
    reason: str
    formula: str | None = None
    target_threshold: str | None = None
    business_impact: str | None = None

    # Set by the KPI engine's verification gate. ``verified`` means every referenced column
    # exists with a usable type, the DAX and pandas compilers agree on the columns, and the
    # value computed on the cleaned dataset is finite. ``computed_value`` is that value.
    computed_value: float | None = None
    verified: bool = False
    verification_note: str = ""