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


class HealthcareKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the HEALTHCARE domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        patient = r.identifier(None, ("patient", "admission", "encounter"))
        stay = r.measure(None, ("length_of_stay", "stay", "los"))
        treatment_cost = r.measure(SemanticType.COST, ("treatment", "charge", "bill", "cost"))

        kpis: list[KPICandidate] = []
        if patient:
            kpis.append(
                KPICandidate(
                    name='Total Patient Admissions',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"Distinct count of '{patient}'.",
                    expression=distinct(patient),
                    business_impact='Measures clinical patient volume.',
                    example_target='Capacity compliance',
                )
            )
        if stay:
            kpis.append(
                KPICandidate(
                    name='Average Length of Stay (ALOS)',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Average of '{stay}'.",
                    expression=average(stay),
                    business_impact='Drives hospital bed turnover efficiency.',
                    example_target='< 4.5 Days',
                )
            )
        if treatment_cost:
            kpis.append(
                KPICandidate(
                    name='Total Treatment Expenditure',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"Sum of '{treatment_cost}'.",
                    expression=total(treatment_cost),
                    business_impact='Measures clinical operating costs.',
                    example_target='Within payer reimbursement limits',
                )
            )

        return tuple(kpis)
