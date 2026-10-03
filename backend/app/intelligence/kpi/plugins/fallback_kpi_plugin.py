from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import Measure, Op, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


def _measure_title(column: str) -> str:
    words = column.replace("_", " ").title()
    return words if words.lower().startswith("total") else f"Total {words}"


class FallbackKPIPlugin(BaseKPIPlugin):
    """
    Fallback KPI plugin for UNKNOWN or unclassified domains.

    Proposes a total for every numeric quantity column (never an ID or a code), or a row
    count when the dataset has none. It states no benchmarks: it knows nothing about the domain.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)

        kpis = [
            KPICandidate(
                name=_measure_title(column),
                priority=Priority.HIGH if index == 0 else Priority.MEDIUM,
                confidence=0.75,
                reason=f"Numeric measure column '{column}' detected.",
                expression=total(column),
                business_impact=f"Measures aggregate sum of {column}.",
            )
            for index, column in enumerate(r.measures())
        ]

        if not kpis:
            kpis.append(
                KPICandidate(
                    name="Total Record Count",
                    priority=Priority.HIGH,
                    confidence=0.90,
                    reason="Dataset row count metric.",
                    expression=Measure(Op.COUNT),
                    business_impact="Measures total dataset row count.",
                )
            )

        return tuple(kpis)
