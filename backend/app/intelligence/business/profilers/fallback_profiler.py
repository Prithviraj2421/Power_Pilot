from typing import Optional

from app.common.enums import DatasetDomain, PhysicalType, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class FallbackProfiler(BaseBusinessProfiler):
    """
    Fallback Business Profiler plugin for UNKNOWN or unmapped domains.
    """

    target_domain = DatasetDomain.UNKNOWN

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate general BI business profile for an unclassified dataset.
        """
        dimensions = []
        measures = []
        date_cols = []

        for col in dataset_profile.columns:
            if col.physical_type in (PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL):
                measures.append(col.name)
            elif col.physical_type in (PhysicalType.DATE, PhysicalType.DATETIME):
                date_cols.append(col.name)
                dimensions.append(col.name)
            else:
                dimensions.append(col.name)

        primary_kpis = []
        for measure in measures[:3]:
            primary_kpis.append(
                KPIRecommendation(
                    name=f"Total {measure.replace('_', ' ').title()}",
                    priority=Priority.HIGH,
                    confidence=0.70,
                    reason=f"Numeric measure column '{measure}' detected in dataset.",
                    formula=f"SUM('{dataset_profile.dataset_name}'[{measure}])",
                )
            )

        if not primary_kpis:
            primary_kpis.append(
                KPIRecommendation(
                    name="Total Record Count",
                    priority=Priority.HIGH,
                    confidence=0.90,
                    reason="Dataset row count metric.",
                    formula=f"COUNTROWS('{dataset_profile.dataset_name}')",
                )
            )

        business_questions = (
            "What is the overall distribution of numeric metrics across key dimensions?",
            "Are there temporal trends or seasonality patterns in the data?",
        )

        suggested_charts = (
            {"title": "Metric Distribution Overview", "chart_type": "bar", "x_axis": dimensions[0] if dimensions else "Index", "y_axis": measures[0] if measures else "Count"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "General Dataset Overview", "components": [kpi.name for kpi in primary_kpis]},
            {"section": "Analysis", "title": "Exploratory BI Breakdown", "components": ["Metric Distribution Overview"]},
        )

        suggested_filters = tuple(dimensions[:3])
        time_intelligence = (f"Temporal Analysis on {date_cols[0]}" if date_cols else "N/A - No temporal columns detected",)
        recommended_insights = (f"Dataset contains {dataset_profile.total_rows} rows and {dataset_profile.total_columns} columns.",)
        data_quality_notes = (f"Nullable columns count: {sum(1 for c in dataset_profile.columns if c.nullable)}",)

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.UNKNOWN,
            confidence=0.50,
            business_context="Exploratory BI analytics for unclassified dataset.",
            executive_summary=f"General dataset '{dataset_profile.dataset_name}' with {len(measures)} measures and {len(dimensions)} dimensions.",
            primary_kpis=tuple(primary_kpis),
            secondary_kpis=(),
            dimensions=tuple(dimensions),
            measures=tuple(measures),
            business_questions=business_questions,
            suggested_charts=suggested_charts,
            suggested_dashboard_layout=suggested_dashboard_layout,
            suggested_filters=suggested_filters,
            time_intelligence=time_intelligence,
            recommended_insights=recommended_insights,
            data_quality_notes=data_quality_notes,
            entities=entities_tuple,
        )
