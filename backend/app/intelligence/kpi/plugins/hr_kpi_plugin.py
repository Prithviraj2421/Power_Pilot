from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import average, distinct, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


class HRKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the HR domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        employee = r.identifier(SemanticType.EMPLOYEE, ("employee", "emp", "staff"))
        salary = r.measure(None, ("salary", "wage", "compensation", "pay"))
        tenure = r.measure(None, ("tenure", "service", "experience", "years"))

        kpis: list[KPICandidate] = []
        if employee:
            kpis.append(
                KPICandidate(
                    name='Total Active Headcount',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"Distinct count of '{employee}'.",
                    expression=distinct(employee),
                    business_impact='Measures total human capital workforce capacity.',
                    example_target='Stable org capacity',
                )
            )
        if salary:
            kpis.append(
                KPICandidate(
                    name='Total Payroll Expenditure',
                    priority=Priority.HIGH,
                    confidence=0.92,
                    reason=f"Sum of '{salary}'.",
                    expression=total(salary),
                    business_impact='Measures primary HR operating cost driver.',
                    example_target='Within annual HR budget',
                )
            )
        if tenure:
            kpis.append(
                KPICandidate(
                    name='Average Employee Tenure (Years)',
                    priority=Priority.MEDIUM,
                    confidence=0.86,
                    reason=f"Average of '{tenure}'.",
                    expression=average(tenure),
                    business_impact='Indicates organizational workforce stability.',
                    example_target='> 3.5 Years',
                )
            )

        return tuple(kpis)
