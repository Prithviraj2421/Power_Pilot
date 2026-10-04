from typing import Optional

import numpy as np
import pandas as pd

from app.common.date_parse import parse_dates_robust
from app.core.config import get_settings
from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.intelligence.stats.significance import apply_fdr, reportable, testable_columns, trend_test
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import TrendResult
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class TrendsPlugin(BaseDataIntelligencePlugin):
    """
    Tests every numeric (non-key) metric against every date column for a trend over time.

    ``test_all`` returns every trend tested with its p-value (regression slope, or Mann-Kendall for few points), effect size
    and n, uncorrected: the engine pools them with the correlation tests and corrects once. ``analyze`` is the stand-alone
    form: it corrects within its own family and returns only trends that survive and are large enough to matter.
    """

    def test_all(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[TrendResult, ...]:
        df_copy = df.copy()
        date_cols = df_copy.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        if not date_cols:
            for col in df_copy.select_dtypes(include=["object", "string"]).columns:
                try:
                    parsed = parse_dates_robust(df_copy[col])
                    if parsed.notna().sum() / len(df_copy) > 0.8:
                        df_copy[col] = parsed
                        date_cols.append(col)
                except Exception:
                    continue

        if not date_cols:
            return ()

        num_cols = testable_columns(df_copy.select_dtypes(include=["number"]).columns.tolist(), dataset_profile)
        if not num_cols:
            return ()

        results = []
        for d_col in date_cols:
            for n_col in num_cols:
                temp_df = df_copy[[d_col, n_col]].dropna()
                if len(temp_df) < 2:
                    continue

                temp_df = temp_df.sort_values(by=d_col, kind="stable")

                x = np.arange(len(temp_df))
                y = temp_df[n_col].values.astype(float)

                slope, intercept = np.polyfit(x, y, 1)
                # Growth is read off the fitted line, not the raw first/last
                # observations: a single noisy endpoint can otherwise flip the
                # sign relative to the slope-derived direction below.
                fitted_start = intercept
                fitted_end = slope * x[-1] + intercept
                growth_rate_pct = float(
                    ((fitted_end - fitted_start) / abs(fitted_start)) * 100 if fitted_start != 0 else 0.0
                )

                _, p_value, effect, method = trend_test(y)
                direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
                reasoning = f"Slope is {slope:.4f} and overall growth is {growth_rate_pct:.2f}% (n = {len(y)}, {method})."

                results.append(
                    TrendResult(
                        time_column=str(d_col),
                        metric_column=str(n_col),
                        direction=direction,
                        slope=round(float(slope), 4),
                        growth_rate_pct=round(growth_rate_pct, 2),
                        confidence=0.85,
                        reasoning=reasoning,
                        p_value=None if np.isnan(p_value) else float(p_value),
                        effect_size=effect,
                        n=len(y),
                        test_method=method,
                    )
                )

        return tuple(results)

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[TrendResult, ...]:
        settings = get_settings()
        corrected = apply_fdr(self.test_all(df, dataset_profile, business_profile, entities), settings.insight_fdr_q)
        kept = [t for t in corrected if reportable(t, settings.insight_min_effect_size)]
        return tuple(sorted(kept, key=lambda t: -(t.effect_size or 0)))
