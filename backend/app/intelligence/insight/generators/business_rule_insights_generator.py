from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class BusinessRuleInsightsGenerator(BaseInsightGenerator):
    """
    Generates domain-specific business rule insights for Retail, Finance, HR, Healthcare, Marketing, Logistics.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []
        domain = business_profile.domain

        # Domain-aware rule logic
        if domain == DatasetDomain.RETAIL:
            rec = Recommendation(
                action="Optimize product basket recommendations and focus inventory on top revenue categories.",
                target_area="Retail Merchandising & POS",
                expected_impact="Increased Average Order Value (AOV) and customer basket size.",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Retail Basket Concentration & Category Strategy",
                description="Retail transaction analysis highlights revenue driver columns suitable for cross-selling.",
                category="BUSINESS_RULE",
                severity="MEDIUM",
                priority=Priority.HIGH,
                confidence=0.90,
                business_impact="Direct improvement in gross margin and retail sales efficiency.",
                recommendation=rec,
                supporting_evidence=("Domain: Retail", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        elif domain == DatasetDomain.FINANCE:
            rec = Recommendation(
                action="Conduct cost-structure review to improve net operating margins.",
                target_area="Financial Accounting & FP&A",
                expected_impact="Expanded net profit margin and tighter ledger variance control.",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Financial Ledger Margin Optimization",
                description="Financial dataset records indicate potential cost optimization levers in operating expenses.",
                category="BUSINESS_RULE",
                severity="HIGH",
                priority=Priority.HIGH,
                confidence=0.92,
                business_impact="Direct improvement in net EBITDA and earnings quality.",
                recommendation=rec,
                supporting_evidence=("Domain: Finance", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        elif domain == DatasetDomain.HR:
            rec = Recommendation(
                action="Review compensation benchmarks across departments to reduce turnover risk.",
                target_area="Human Resources & Talent Management",
                expected_impact="Lower employee attrition and balanced departmental pay equity.",
                priority=Priority.MEDIUM,
            )
            ins = Insight(
                title="Human Resources Pay Equity & Retention",
                description="HR headcount records provide signals for tenure distribution and salary benchmarks.",
                category="BUSINESS_RULE",
                severity="MEDIUM",
                priority=Priority.MEDIUM,
                confidence=0.88,
                business_impact="Reduced talent recruitment costs and improved staff retention.",
                recommendation=rec,
                supporting_evidence=("Domain: HR", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        elif domain == DatasetDomain.HEALTHCARE:
            rec = Recommendation(
                action="Streamline patient admission protocols to optimize length of stay and bed utilization.",
                target_area="Clinical Operations & Patient Care",
                expected_impact="Reduced treatment cost variances and improved patient turnaround.",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Healthcare Clinical Resource & Care Efficiency",
                description="Healthcare admission metrics indicate opportunities for treatment cost standardization.",
                category="BUSINESS_RULE",
                severity="HIGH",
                priority=Priority.HIGH,
                confidence=0.89,
                business_impact="Lower overall hospital operational costs per admission.",
                recommendation=rec,
                supporting_evidence=("Domain: Healthcare", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        elif domain == DatasetDomain.MARKETING:
            rec = Recommendation(
                action="Reallocate ad spend budget toward top-performing marketing channels.",
                target_area="Digital Marketing & Campaign Analytics",
                expected_impact="Higher Return on Ad Spend (ROAS) and lower Cost Per Acquisition (CPA).",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Marketing Campaign ROAS & Attribution Optimization",
                description="Campaign performance signals indicate variance in conversion rates across ad mediums.",
                category="BUSINESS_RULE",
                severity="MEDIUM",
                priority=Priority.HIGH,
                confidence=0.91,
                business_impact="Maximized lead generation yield per dollar of ad spend.",
                recommendation=rec,
                supporting_evidence=("Domain: Marketing", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        elif domain == DatasetDomain.LOGISTICS:
            rec = Recommendation(
                action="Partner with high-reliability carriers and optimize warehouse dispatch schedules.",
                target_area="Supply Chain & Freight Logistics",
                expected_impact="Reduced shipping delay days and lower freight cost per unit.",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Logistics Carrier On-Time Delivery & Logistics Cost",
                description="Shipment tracking signals indicate freight cost variances and delay spikes across carriers.",
                category="BUSINESS_RULE",
                severity="HIGH",
                priority=Priority.HIGH,
                confidence=0.90,
                business_impact="Improved customer delivery SLA compliance.",
                recommendation=rec,
                supporting_evidence=("Domain: Logistics", f"Confidence: {business_profile.confidence}"),
            )
            insights.append(ins)

        return tuple(insights)
