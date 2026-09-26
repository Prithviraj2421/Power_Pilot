from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class RetailProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the RETAIL domain.
    """

    target_domain = DatasetDomain.RETAIL

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for a Retail dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Total Revenue",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Revenue entity detected on transaction column. Classified as Retail domain. Date dimension available.",
                formula="SUM('Sales'[Revenue])",
            ),
            KPIRecommendation(
                name="Average Order Value (AOV)",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Order ID and Revenue detected. AOV is a standard retail metric.",
                formula="SUM('Sales'[Revenue]) / COUNTDISTINCT('Sales'[Order_ID])",
            ),
            KPIRecommendation(
                name="Total Units Sold",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Quantity entity detected. Measures total merchandise volume.",
                formula="SUM('Sales'[Quantity])",
            ),
            KPIRecommendation(
                name="Active Customer Count",
                priority=Priority.MEDIUM,
                confidence=0.85,
                reason="Customer entity detected. Measures unique purchasing customers.",
                formula="COUNTDISTINCT('Sales'[Customer_ID])",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Revenue Per Customer",
                priority=Priority.MEDIUM,
                confidence=0.80,
                reason="Customer and Revenue entities present.",
                formula="[Total Revenue] / [Active Customer Count]",
            ),
            KPIRecommendation(
                name="Average Basket Size",
                priority=Priority.LOW,
                confidence=0.75,
                reason="Quantity and Order entities present.",
                formula="[Total Units Sold] / COUNTDISTINCT('Sales'[Order_ID])",
            ),
        )

        dimensions = ("Product_Category", "Store_Region", "Customer_Segment", "Order_Date")
        measures = ("Revenue", "Quantity", "Unit_Price", "Discount_Amount")

        business_questions = (
            "Which product categories generate 80% of total revenue?",
            "What is the average basket size across different store regions?",
            "How does monthly sales volume trend YoY?",
            "Which customer segment has the highest Average Order Value?",
        )

        suggested_charts = (
            {"title": "Monthly Revenue Trend", "chart_type": "line", "x_axis": "Order_Date", "y_axis": "Revenue"},
            {"title": "Revenue by Product Category", "chart_type": "bar", "x_axis": "Product_Category", "y_axis": "Revenue"},
            {"title": "Sales Volume vs Quantity", "chart_type": "scatter", "x_axis": "Quantity", "y_axis": "Revenue"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Executive Summary & Key KPIs", "components": ["Total Revenue", "AOV", "Units Sold", "Active Customers"]},
            {"section": "Sales Performance", "title": "Revenue & Category Trends", "components": ["Monthly Revenue Trend", "Revenue by Product Category"]},
            {"section": "Customer Insights", "title": "Customer Segmentation & Basket Size", "components": ["Revenue Per Customer", "Sales Volume vs Quantity"]},
        )

        suggested_filters = ("Order_Date", "Product_Category", "Store_Region")
        time_intelligence = ("YoY Revenue Growth %", "MoM Sales Volume Change %", "Quarter-to-Date (QTD) Sales")
        recommended_insights = (
            "Top 20% of products account for majority of sales volume.",
            "Seasonal revenue peak observed in Q4.",
        )
        data_quality_notes = ("No critical missing values in primary key columns.",)

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.RETAIL,
            confidence=0.95,
            business_context="Retail transactional analytics focusing on sales performance, category mix, and customer purchasing behavior.",
            executive_summary="Retail dataset with strong revenue and product category signals suitable for executive sales reporting.",
            primary_kpis=primary_kpis,
            secondary_kpis=secondary_kpis,
            dimensions=dimensions,
            measures=measures,
            business_questions=business_questions,
            suggested_charts=suggested_charts,
            suggested_dashboard_layout=suggested_dashboard_layout,
            suggested_filters=suggested_filters,
            time_intelligence=time_intelligence,
            recommended_insights=recommended_insights,
            data_quality_notes=data_quality_notes,
            entities=entities_tuple,
        )
