from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.common.powerbi_names import dax_table
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.relationship_models import RelationshipReport


def _measure_title(column: str) -> str:
    words = column.replace("_", " ").title()
    return words if words.lower().startswith("total") else f"Total {words}"


class FallbackKPIPlugin(BaseKPIPlugin):
    """
    Fallback KPI recommendation plugin for UNKNOWN or unclassified domains.
    """

    target_domain = DatasetDomain.UNKNOWN

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[KPIRecommendation, ...]:
        r = ColumnResolver(dataset_profile)

        kpis = []
        for cname in r.measures():
            kpis.append(
                KPIRecommendation(
                    name=_measure_title(cname),
                    priority=Priority.HIGH if len(kpis) == 0 else Priority.MEDIUM,
                    confidence=0.75,
                    reason=f"Numeric measure column '{cname}' detected.",
                    formula=f"SUM({r.ref(cname)})",
                    target_threshold="N/A",
                    business_impact=f"Measures aggregate sum of {cname}.",
                )
            )

        if not kpis:
            kpis.append(
                KPIRecommendation(
                    name="Total Record Count",
                    priority=Priority.HIGH,
                    confidence=0.90,
                    reason="Dataset row count metric.",
                    formula=f"COUNTROWS({dax_table(r.table)})",
                    target_threshold="N/A",
                    business_impact="Measures total dataset row count.",
                )
            )

        return tuple(kpis)
