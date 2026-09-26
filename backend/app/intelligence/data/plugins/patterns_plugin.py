from typing import Optional

import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import PatternReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class PatternsPlugin(BaseDataIntelligencePlugin):
    """
    Data intelligence plugin for analyzing patterns such as Pareto 80/20 distributions,
    high cardinality clustering, and seasonality.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[PatternReport, ...]:
        reports = []

        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        numeric_cols = df.select_dtypes(include=["number"]).columns

        for cat_col in categorical_cols:
            unique_count = df[cat_col].nunique()
            if unique_count > 0 and unique_count < len(df) * 0.5:
                if unique_count > 50:
                    reports.append(
                        PatternReport(
                            pattern_type="High Cardinality",
                            description=f"Column '{cat_col}' has high cardinality ({unique_count} unique values).",
                            affected_columns=(str(cat_col),),
                            confidence=0.8,
                            reasoning="High number of distinct categories may require clustering or dimensional reduction.",
                        )
                    )

                for num_col in numeric_cols:
                    if (df[num_col] >= 0).all():
                        agg = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
                        total = agg.sum()
                        if total > 0:
                            top_20_pct_count = max(1, int(len(agg) * 0.2))
                            top_20_sum = agg.head(top_20_pct_count).sum()
                            pct_ratio = float(top_20_sum / total)
                            if pct_ratio >= 0.70:
                                reports.append(
                                    PatternReport(
                                        pattern_type="Pareto Distribution",
                                        description=f"Top 20% of '{cat_col}' accounts for {pct_ratio * 100:.1f}% of '{num_col}'.",
                                        affected_columns=(str(cat_col), str(num_col)),
                                        confidence=0.9,
                                        reasoning="A classic 80/20 rule is observed, indicating high concentration.",
                                    )
                                )

        datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns
        if len(datetime_cols) > 0 and len(numeric_cols) > 0:
            for dt_col in datetime_cols:
                reports.append(
                    PatternReport(
                        pattern_type="Potential Seasonality",
                        description=f"Time series data detected in '{dt_col}'.",
                        affected_columns=(str(dt_col),),
                        confidence=0.6,
                        reasoning="Presence of datetime columns suggests potential seasonal patterns that could be explored further.",
                    )
                )

        return tuple(reports)
