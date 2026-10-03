from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.column_resolver import ColumnResolver
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
        r = ColumnResolver(dataset_profile)
        patient = r.identifier(None, ("patient", "admission", "encounter"))
        stay = r.measure(None, ("length_of_stay", "stay", "los"))
        treatment_cost = r.measure(SemanticType.COST, ("treatment", "charge", "bill", "cost"))

        kpis: list[KPIRecommendation] = []
        if patient:
            kpis.append(
                KPIRecommendation(
                    name='Total Patient Admissions',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"Distinct count of '{patient}'.",
                    formula=f'DISTINCTCOUNT({r.ref(patient)})',
                    target_threshold='Capacity compliance',
                    business_impact='Measures clinical patient volume.',
                )
            )
        if stay:
            kpis.append(
                KPIRecommendation(
                    name='Average Length of Stay (ALOS)',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Average of '{stay}'.",
                    formula=f'AVERAGE({r.ref(stay)})',
                    target_threshold='< 4.5 Days',
                    business_impact='Drives hospital bed turnover efficiency.',
                )
            )
        if treatment_cost:
            kpis.append(
                KPIRecommendation(
                    name='Total Treatment Expenditure',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"Sum of '{treatment_cost}'.",
                    formula=f'SUM({r.ref(treatment_cost)})',
                    target_threshold='Within payer reimbursement limits',
                    business_impact='Measures clinical operating costs.',
                )
            )

        return tuple(kpis)
