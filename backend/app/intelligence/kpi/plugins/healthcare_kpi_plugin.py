from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.relationship_models import RelationshipReport


class HealthcareKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the HEALTHCARE domain.
    """

    target_domain = DatasetDomain.HEALTHCARE

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[KPIRecommendation, ...]:
        tbl = dataset_profile.dataset_name

        kpis = [
            KPIRecommendation(
                name="Total Patient Admissions",
                priority=Priority.CRITICAL,
                confidence=0.94,
                reason="Distinct count of patient admission records.",
                formula=f"DISTINCTCOUNT('{tbl}'[Patient_ID])",
                target_threshold="Capacity compliance",
                business_impact="Measures clinical patient volume.",
            ),
            KPIRecommendation(
                name="Average Length of Stay (ALOS)",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Average inpatient days per admission.",
                formula=f"AVERAGE('{tbl}'[Length_Of_Stay_Days])",
                target_threshold="< 4.5 Days",
                business_impact="Drives hospital bed turnover efficiency.",
            ),
            KPIRecommendation(
                name="Total Treatment Expenditure",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Sum of patient medical treatment costs.",
                formula=f"SUM('{tbl}'[Treatment_Cost])",
                target_threshold="Within payer reimbursement limits",
                business_impact="Measures clinical operating costs.",
            ),
        ]

        return tuple(kpis)
