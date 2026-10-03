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


class HRKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the HR domain.
    """

    target_domain = DatasetDomain.HR

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
        employee = r.identifier(SemanticType.EMPLOYEE, ("employee", "emp", "staff"))
        salary = r.measure(None, ("salary", "wage", "compensation", "pay"))
        tenure = r.measure(None, ("tenure", "service", "experience", "years"))

        kpis: list[KPIRecommendation] = []
        if employee:
            kpis.append(
                KPIRecommendation(
                    name='Total Active Headcount',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"Distinct count of '{employee}'.",
                    formula=f'DISTINCTCOUNT({r.ref(employee)})',
                    target_threshold='Stable org capacity',
                    business_impact='Measures total human capital workforce capacity.',
                )
            )
        if salary:
            kpis.append(
                KPIRecommendation(
                    name='Total Payroll Expenditure',
                    priority=Priority.HIGH,
                    confidence=0.92,
                    reason=f"Sum of '{salary}'.",
                    formula=f'SUM({r.ref(salary)})',
                    target_threshold='Within annual HR budget',
                    business_impact='Measures primary HR operating cost driver.',
                )
            )
        if tenure:
            kpis.append(
                KPIRecommendation(
                    name='Average Employee Tenure (Years)',
                    priority=Priority.MEDIUM,
                    confidence=0.86,
                    reason=f"Average of '{tenure}'.",
                    formula=f'AVERAGE({r.ref(tenure)})',
                    target_threshold='> 3.5 Years',
                    business_impact='Indicates organizational workforce stability.',
                )
            )

        return tuple(kpis)
