from typing import Optional

import numpy as np
import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import TrendResult
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class TrendsPlugin(BaseDataIntelligencePlugin):
    """
    Identifies temporal columns and numeric measure columns, computes overall slope
    and growth rate percentage over time.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[TrendResult, ...]:
        df_copy = df.copy()
        date_cols = df_copy.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        if not date_cols:
            for col in df_copy.select_dtypes(include=["object"]).columns:
                try:
                    parsed = pd.to_datetime(df_copy[col], errors="coerce")
                    if parsed.notna().sum() / len(df_copy) > 0.8:
                        df_copy[col] = parsed
                        date_cols.append(col)
                except Exception:
                    continue

        if not date_cols:
            return ()

        num_cols = df_copy.select_dtypes(include=["number"]).columns.tolist()
        if not num_cols:
            return ()

        results = []
        for d_col in date_cols:
            for n_col in num_cols:
                temp_df = df_copy[[d_col, n_col]].dropna()
                if len(temp_df) < 2:
                    continue

                temp_df = temp_df.sort_values(by=d_col)

                x = np.arange(len(temp_df))
                y = temp_df[n_col].values

                if len(x) > 1:
                    slope, _ = np.polyfit(x, y, 1)
                    start_val = y[0]
                    end_val = y[-1]
                    growth_rate_pct = float(((end_val - start_val) / abs(start_val)) * 100 if start_val != 0 else 0.0)

                    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
                    confidence = 0.85
                    reasoning = f"Slope is {slope:.4f} and overall growth is {growth_rate_pct:.2f}%."

                    results.append(
                        TrendResult(
                            time_column=str(d_col),
                            metric_column=str(n_col),
                            direction=direction,
                            slope=round(float(slope), 4),
                            growth_rate_pct=round(growth_rate_pct, 2),
                            confidence=confidence,
                            reasoning=reasoning,
                        )
                    )

        return tuple(results)
