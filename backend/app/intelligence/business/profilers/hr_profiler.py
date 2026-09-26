from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class HRProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the HR domain.
    """

    target_domain = DatasetDomain.HR

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for an HR dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Total Headcount",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Employee entity detected. Measures active workforce size.",
                formula="COUNTDISTINCT('Workforce'[Employee_ID])",
            ),
            KPIRecommendation(
                name="Total Payroll Spend",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Salary/Cost entity detected in workforce records.",
                formula="SUM('Workforce'[Salary])",
            ),
            KPIRecommendation(
                name="Average Salary",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Salary and Employee entities present.",
                formula="AVERAGE('Workforce'[Salary])",
            ),
            KPIRecommendation(
                name="Average Tenure (Years)",
                priority=Priority.MEDIUM,
                confidence=0.85,
                reason="Hire date and Date entities present.",
                formula="AVERAGE('Workforce'[Tenure_Years])",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Department Headcount Share",
                priority=Priority.LOW,
                confidence=0.78,
                reason="Department dimension and Employee entity present.",
                formula="[Total Headcount] / ALL('Workforce'[Department])",
            ),
        )

        dimensions = ("Department", "Job_Level", "Employment_Type", "Hire_Date")
        measures = ("Salary", "Tenure_Years", "Performance_Score", "Employee_ID")

        business_questions = (
            "Which department accounts for the largest salary spend?",
            "What is the average employee tenure by job level?",
            "How does performance score correlate with salary?",
        )

        suggested_charts = (
            {"title": "Headcount by Department", "chart_type": "bar", "x_axis": "Department", "y_axis": "Headcount"},
            {"title": "Salary vs Performance Score", "chart_type": "scatter", "x_axis": "Performance_Score", "y_axis": "Salary"},
            {"title": "Tenure Distribution", "chart_type": "histogram", "x_axis": "Tenure_Years", "y_axis": "Count"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Workforce Overview", "components": ["Total Headcount", "Total Payroll Spend", "Average Salary", "Average Tenure"]},
            {"section": "Department Breakdown", "title": "Departmental Allocation & Compensation", "components": ["Headcount by Department", "Salary vs Performance Score"]},
        )

        suggested_filters = ("Department", "Job_Level", "Employment_Type")
        time_intelligence = ("Headcount Growth YoY", "Tenure Cohort Analysis", "Hire Date Trend")
        recommended_insights = ("Average tenure is highest in Engineering department (4.2 years).")
        data_quality_notes = ("Zero null values in Employee_ID.")

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.HR,
            confidence=0.90,
            business_context="Human capital analytics tracking workforce size, compensation equity, and employee retention.",
            executive_summary="HR dataset with employee roster and compensation signals suitable for workforce analytics.",
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
