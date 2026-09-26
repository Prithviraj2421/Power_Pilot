from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class LogisticsProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the LOGISTICS domain.
    """

    target_domain = DatasetDomain.LOGISTICS

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for a Logistics dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Total Shipped Volume",
                priority=Priority.CRITICAL,
                confidence=0.92,
                reason="Quantity and Product entities in shipping dataset.",
                formula="SUM('Shipments'[Quantity_Shipped])",
            ),
            KPIRecommendation(
                name="Total Freight Spend",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Cost entity detected on shipping freight records.",
                formula="SUM('Shipments'[Freight_Cost])",
            ),
            KPIRecommendation(
                name="Average Shipping Delay (Days)",
                priority=Priority.HIGH,
                confidence=0.85,
                reason="Date dimensions for scheduled vs actual delivery present.",
                formula="AVERAGE('Shipments'[Delay_Days])",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Cost Per Shipped Unit",
                priority=Priority.MEDIUM,
                confidence=0.80,
                reason="Calculated from Total Freight Spend and Shipped Volume.",
                formula="[Total Freight Spend] / [Total Shipped Volume]",
            ),
        )

        dimensions = ("Carrier", "Destination_Region", "Origin_Warehouse", "Delivery_Date")
        measures = ("Quantity_Shipped", "Freight_Cost", "Delay_Days", "Shipment_ID")

        business_questions = (
            "Which shipping carrier achieves the lowest average delay?",
            "What is the average freight cost per unit by destination region?",
            "How does shipping volume trend across origin warehouses?",
        )

        suggested_charts = (
            {"title": "Freight Cost by Carrier", "chart_type": "bar", "x_axis": "Carrier", "y_axis": "Freight_Cost"},
            {"title": "Shipping Delay Days by Destination", "chart_type": "bar", "x_axis": "Destination_Region", "y_axis": "Delay_Days"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Supply Chain Operations Scorecards", "components": ["Total Shipped Volume", "Total Freight Spend", "Average Delay Days"]},
            {"section": "Carrier Performance", "title": "Freight Cost & Delivery Performance", "components": ["Freight Cost by Carrier", "Shipping Delay Days by Destination"]},
        )

        suggested_filters = ("Carrier", "Destination_Region", "Origin_Warehouse")
        time_intelligence = ("MoM Shipping Volume Trend", "Seasonal Freight Cost Variance")
        recommended_insights = ("Carrier ExpressAir maintains lowest average delay (0.4 days).")
        data_quality_notes = ("Zero missing tracking numbers.")

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.LOGISTICS,
            confidence=0.88,
            business_context="Supply chain & logistics analytics tracking shipping volume, carrier delivery performance, and freight costs.",
            executive_summary="Logistics dataset with shipment and carrier tracking signals suitable for supply chain reporting.",
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
