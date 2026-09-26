from typing import Optional

import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import StatisticalSummary
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class StatisticsPlugin(BaseDataIntelligencePlugin):
    """
    Computes numeric column statistics and column distribution counts.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> StatisticalSummary:
        total_rows = len(df)

        date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        column_summaries = {}
        for col in num_cols:
            series = df[col].dropna()
            if series.empty:
                continue

            stats = {
                "mean": float(series.mean()),
                "std": float(series.std()) if len(series) > 1 else 0.0,
                "min": float(series.min()),
                "25%": float(series.quantile(0.25)),
                "50%": float(series.median()),
                "75%": float(series.quantile(0.75)),
                "max": float(series.max()),
                "skewness": float(series.skew()) if len(series) > 2 else 0.0,
            }
            column_summaries[str(col)] = stats

        evidence = (
            f"Evaluated {total_rows} rows across {len(num_cols)} numeric, {len(cat_cols)} categorical, and {len(date_cols)} date columns.",
        )

        return StatisticalSummary(
            total_rows=total_rows,
            numeric_columns_count=len(num_cols),
            categorical_columns_count=len(cat_cols),
            date_columns_count=len(date_cols),
            column_summaries=column_summaries,
            evidence=evidence,
        )
