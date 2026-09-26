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