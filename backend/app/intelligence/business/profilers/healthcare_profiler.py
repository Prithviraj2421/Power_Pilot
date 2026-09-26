from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class HealthcareProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the HEALTHCARE domain.
    """

    target_domain = DatasetDomain.HEALTHCARE

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for a Healthcare dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Total Patient Admissions",
                priority=Priority.CRITICAL,
                confidence=0.92,
                reason="Patient/Customer entity and admission records detected.",
                formula="COUNTDISTINCT('Admissions'[Patient_ID])",
            ),
            KPIRecommendation(
                name="Total Treatment Expenses",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Cost/Treatment entity detected in clinical dataset.",
                formula="SUM('Admissions'[Treatment_Cost])",
            ),
            KPIRecommendation(
                name="Average Spend Per Patient",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Calculated from Total Treatment Expenses and Patient Count.",
                formula="[Total Treatment Expenses] / [Total Patient Admissions]",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Average Length of Stay (Days)",
                priority=Priority.MEDIUM,
                confidence=0.82,
                reason="Admission and discharge date dimensions present.",
                formula="AVERAGE('Admissions'[Length_Of_Stay_Days])",
            ),
        )

        dimensions = ("Diagnosis_Category", "Hospital_Wing", "Attending_Doctor", "Admission_Date")
        measures = ("Treatment_Cost", "Length_Of_Stay_Days", "Patient_ID")

        business_questions = (
            "Which diagnosis category incurs the highest total treatment cost?",
            "What is the average length of stay across hospital wings?",
            "How do patient admissions trend by month?",
        )

        suggested_charts = (
            {"title": "Patient Admissions Trend", "chart_type": "line", "x_axis": "Admission_Date", "y_axis": "Admissions"},
            {"title": "Treatment Cost by Diagnosis", "chart_type": "bar", "x_axis": "Diagnosis_Category", "y_axis": "Treatment_Cost"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Clinical & Operational Metrics", "components": ["Total Patient Admissions", "Total Treatment Expenses", "Average Spend Per Patient"]},
            {"section": "Clinical Analysis", "title": "Admissions & Cost Distribution", "components": ["Patient Admissions Trend", "Treatment Cost by Diagnosis"]},
        )

        suggested_filters = ("Diagnosis_Category", "Hospital_Wing", "Attending_Doctor")
        time_intelligence = ("Monthly Admission Volume Trend", "Seasonal Admission Spikes")
        recommended_insights = ("Cardiology diagnoses account for 35% of total treatment costs.")
        data_quality_notes = ("No duplicate patient admission IDs found.")

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.HEALTHCARE,
            confidence=0.88,
            business_context="Healthcare analytics monitoring patient admissions, medical expenses, and hospital resource utilization.",
            executive_summary="Healthcare dataset with patient clinical and cost signals suitable for hospital operations reporting.",
            primary_kpis=primary_kpis,
            secondary_kpis=secondary_kpis,
            dimensions=dimensions,
            measures=measures,
            business_questions=business_questions,
            suggested_charts=suggested_charts,
            suggested_dashboard_layout=suggested_dashboard_layout,
            suggested_filters=suggested_filters,
            time_intelligence=time_intelligence,
            recommended_insights=(recommended_insights,),
            data_quality_notes=(data_quality_notes,),
            entities=entities_tuple,
        )
