from dataclasses import dataclass, field

from app.common.enums import DatasetDomain
from app.models.kpi_recommendation import KPIRecommendation


@dataclass(slots=True, frozen=True)
class KPIReport:
    """
    Unified immutable report detailing all primary and secondary KPI recommendations for a dataset.
    """

    primary_kpis: tuple[KPIRecommendation, ...] = field(default_factory=tuple)
    secondary_kpis: tuple[KPIRecommendation, ...] = field(default_factory=tuple)
    all_kpis: tuple[KPIRecommendation, ...] = field(default_factory=tuple)
    domain: DatasetDomain = DatasetDomain.UNKNOWN
    total_kpis_recommended: int = 0
