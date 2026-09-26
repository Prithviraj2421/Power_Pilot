from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain
from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import BusinessAnomaly
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class BusinessAnomaliesPlugin(BaseDataIntelligencePlugin):
    """
    Data intelligence plugin for detecting domain-aware business rule anomalies.
    Supported domains: Retail, Finance, HR, Healthcare, Marketing, Logistics.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[BusinessAnomaly, ...]:
        anomalies = []
        domain_enum = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)

        col_map = {str(c).lower(): c for c in df.columns}

        # 1. RETAIL ANOMALIES
        if domain_enum == DatasetDomain.RETAIL or any(k in col_map for k in ["sales", "revenue", "price"]):
            for price_col_name in ["price", "sales", "revenue", "unit_price"]:
                if price_col_name in col_map:
                    real_col = col_map[price_col_name]
                    if pd.api.types.is_numeric_dtype(df[real_col]):
                        negatives = df[df[real_col] < 0]
                        if not negatives.empty:
                            count = len(negatives)
                            min_val = float(negatives[real_col].min())
                            anomalies.append(
                                BusinessAnomaly(
                                    anomaly_title="Negative Pricing or Revenue Detected",
                                    severity="HIGH",
                                    affected_entity="Product / Transaction",
                                    metric_name=str(real_col),
                                    observed_value=min_val,
                                    expected_value=0.0,
                                    deviation_pct=100.0,
                                    confidence=0.95,
                                    reasoning=f"Found {count} negative revenue/price entries (min: {min_val:.2f}) which violate retail non-negativity rules.",
                                    evidence=(f"{count} negative rows in '{real_col}'",),
                                )
                            )

        # 2. FINANCE ANOMALIES
        if domain_enum == DatasetDomain.FINANCE or any(k in col_map for k in ["operating_cost", "cogs", "expense"]):
            for cost_col_name in ["operating_cost", "cogs", "expense", "unit_cost"]:
                if cost_col_name in col_map:
                    real_col = col_map[cost_col_name]
                    if pd.api.types.is_numeric_dtype(df[real_col]):
                        negatives = df[df[real_col] < 0]
                        if not negatives.empty:
                            count = len(negatives)
                            min_val = float(negatives[real_col].min())
                            anomalies.append(
                                BusinessAnomaly(
                                    anomaly_title="Negative Operating Cost / Expense",
                                    severity="HIGH",
                                    affected_entity="Ledger Account",
                                    metric_name=str(real_col),
                                    observed_value=min_val,
                                    expected_value=0.0,
                                    deviation_pct=100.0,
                                    confidence=0.95,
                                    reasoning=f"Found {count} negative cost entries (min: {min_val:.2f}) in financial ledger.",
                                    evidence=(f"{count} negative cost rows in '{real_col}'",),
                                )
                            )

        # 3. HR ANOMALIES
        if domain_enum == DatasetDomain.HR or any(k in col_map for k in ["salary", "tenure"]):
            if "salary" in col_map:
                real_col = col_map["salary"]
                if pd.api.types.is_numeric_dtype(df[real_col]):
                    negatives = df[df[real_col] <= 0]
                    if not negatives.empty:
                        count = len(negatives)
                        anomalies.append(
                            BusinessAnomaly(
                                anomaly_title="Non-Positive Employee Salary",
                                severity="CRITICAL",
                                affected_entity="Employee",
                                metric_name=str(real_col),
                                observed_value=float(negatives[real_col].min()),
                                expected_value=30000.0,
                                deviation_pct=100.0,
                                confidence=0.95,
                                reasoning=f"Found {count} employee salary records <= 0.",
                                evidence=(f"{count} non-positive salary records",),
                            )
                        )

        # 4. HEALTHCARE ANOMALIES
        if domain_enum == DatasetDomain.HEALTHCARE or any(k in col_map for k in ["length_of_stay", "stay_days"]):
            for stay_col in ["length_of_stay", "length_of_stay_days", "stay_days"]:
                if stay_col in col_map:
                    real_col = col_map[stay_col]
                    if pd.api.types.is_numeric_dtype(df[real_col]):
                        invalid_stay = df[df[real_col] <= 0]
                        if not invalid_stay.empty:
                            count = len(invalid_stay)
                            anomalies.append(
                                BusinessAnomaly(
                                    anomaly_title="Invalid Hospital Length of Stay",
                                    severity="HIGH",
                                    affected_entity="Patient Admission",
                                    metric_name=str(real_col),
                                    observed_value=float(invalid_stay[real_col].min()),
                                    expected_value=1.0,
                                    deviation_pct=100.0,
                                    confidence=0.90,
                                    reasoning=f"Found {count} patient admission records with length of stay <= 0 days.",
                                    evidence=(f"{count} invalid length of stay records",),
                                )
                            )

        # 5. MARKETING ANOMALIES
        if domain_enum == DatasetDomain.MARKETING or any(k in col_map for k in ["ctr", "roas"]):
            if "roas" in col_map:
                real_col = col_map["roas"]
                if pd.api.types.is_numeric_dtype(df[real_col]):
                    negatives = df[df[real_col] < 0]
                    if not negatives.empty:
                        anomalies.append(
                            BusinessAnomaly(
                                anomaly_title="Negative Return on Ad Spend (ROAS)",
                                severity="HIGH",
                                affected_entity="Campaign",
                                metric_name=str(real_col),
                                observed_value=float(negatives[real_col].min()),
                                expected_value=1.0,
                                deviation_pct=100.0,
                                confidence=0.90,
                                reasoning="ROAS cannot be negative.",
                                evidence=(f"{len(negatives)} negative ROAS entries",),
                            )
                        )

        # 6. LOGISTICS ANOMALIES
        if domain_enum == DatasetDomain.LOGISTICS or any(k in col_map for k in ["delay_days", "shipping_delay"]):
            for delay_col in ["delay_days", "shipping_delay"]:
                if delay_col in col_map:
                    real_col = col_map[delay_col]
                    if pd.api.types.is_numeric_dtype(df[real_col]):
                        extreme_delays = df[df[real_col] > 30]
                        if not extreme_delays.empty:
                            anomalies.append(
                                BusinessAnomaly(
                                    anomaly_title="Extreme Shipping Delay Detected",
                                    severity="HIGH",
                                    affected_entity="Shipment",
                                    metric_name=str(real_col),
                                    observed_value=float(extreme_delays[real_col].max()),
                                    expected_value=3.0,
                                    deviation_pct=900.0,
                                    confidence=0.85,
                                    reasoning=f"Found {len(extreme_delays)} shipments with delays exceeding 30 days.",
                                    evidence=(f"{len(extreme_delays)} extreme delay shipments",),
                                )
                            )

        return tuple(anomalies)
