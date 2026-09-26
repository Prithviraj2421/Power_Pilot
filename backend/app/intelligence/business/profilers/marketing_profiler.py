from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class MarketingProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the MARKETING domain.
    """

    target_domain = DatasetDomain.MARKETING

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for a Marketing dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Total Campaign Revenue",
                priority=Priority.CRITICAL,
                confidence=0.92,
                reason="Revenue entity and marketing campaign data detected.",
                formula="SUM('Campaigns'[Revenue])",
            ),
            KPIRecommendation(
                name="Total Ad Spend",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Cost/Ad spend entity detected in campaign dataset.",
                formula="SUM('Campaigns'[Ad_Spend])",
            ),
            KPIRecommendation(
                name="Return on Ad Spend (ROAS)",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Calculated from Total Campaign Revenue and Ad Spend.",
                formula="[Total Campaign Revenue] / [Total Ad Spend]",
            ),
            KPIRecommendation(
                name="Cost Per Acquisition (CPA)",
                priority=Priority.HIGH,
                confidence=0.85,
                reason="Calculated from Total Ad Spend and Converted Lead Count.",
                formula="[Total Ad Spend] / SUM('Campaigns'[Conversions])",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Click-Through Rate (CTR %)",
                priority=Priority.MEDIUM,
                confidence=0.80,
                reason="Impressions and Clicks metrics detected.",
                formula="(SUM('Campaigns'[Clicks]) / SUM('Campaigns'[Impressions])) * 100",
            ),
        )

        dimensions = ("Campaign_Name", "Marketing_Channel", "Ad_Medium", "Click_Date")
        measures = ("Revenue", "Ad_Spend", "Conversions", "Clicks", "Impressions")

        business_questions = (
            "Which marketing channel generated the highest Return on Ad Spend (ROAS)?",
            "What is the average Cost Per Acquisition (CPA) across campaigns?",
            "How does ad spend correlate with revenue generated?",
        )

        suggested_charts = (
            {"title": "Ad Spend vs Generated Revenue", "chart_type": "scatter", "x_axis": "Ad_Spend", "y_axis": "Revenue"},
            {"title": "Conversions by Marketing Channel", "chart_type": "bar", "x_axis": "Marketing_Channel", "y_axis": "Conversions"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Campaign Performance Scorecards", "components": ["Total Campaign Revenue", "Total Ad Spend", "ROAS", "CPA"]},
            {"section": "Channel Efficiency", "title": "Conversion & Spend Analysis", "components": ["Ad Spend vs Generated Revenue", "Conversions by Marketing Channel"]},
        )

        suggested_filters = ("Campaign_Name", "Marketing_Channel", "Ad_Medium")
        time_intelligence = ("MoM ROAS Growth %", "Weekly Campaign Performance Spike")
        recommended_insights = ("Paid Search channel delivered highest ROAS (4.2x).")
        data_quality_notes = ("Zero nulls in Campaign_Name.")

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.MARKETING,
            confidence=0.90,
            business_context="Marketing performance analytics tracking ad spend efficiency, channel attribution, and ROAS.",
            executive_summary="Marketing dataset with campaign spend and lead conversion signals suitable for marketing ROI reporting.",
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
