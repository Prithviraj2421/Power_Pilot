from typing import Optional

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.intelligence.stats.significance import apply_fdr, correlation_p_values, reportable, testable_columns
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import CorrelationResult
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class CorrelationPlugin(BaseDataIntelligencePlugin):
    """
    Tests every pair of numeric (non-key) columns for correlation.

    ``test_all`` returns every pair tested, with its p-value, effect size and n, but not yet corrected for the number of
    tests: the engine pools these with the trend tests and corrects once across all of them. ``analyze`` is the stand-alone
    form: it corrects within its own family and returns only the pairs that survive and are large enough to matter.
    """

    def test_all(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[CorrelationResult, ...]:
        numeric = [c for c in df.select_dtypes(include=["number"]).columns if df[c].nunique() > 1]
        cols = testable_columns(numeric, dataset_profile)
        if len(cols) < 2:
            return ()

        data = df[cols]
        present = data.notna().to_numpy(dtype=float)
        counts = present.T @ present  # points available for each pair
        pearson = data.corr(method="pearson").to_numpy()
        spearman = data.rank().corr(method="pearson").to_numpy()  # rank correlation, ranks taken once per column
        p_pearson = correlation_p_values(pearson, counts)
        p_spearman = correlation_p_values(spearman, counts)

        results = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = pearson[i, j]
                if np.isnan(r):
                    continue
                n = int(counts[i, j])
                both = [v for v in (p_pearson[i, j], p_spearman[i, j]) if not np.isnan(v)]
                # The larger p-value of the two tests: a pair must be convincing under Pearson AND under ranks.
                p = float(max(both)) if both else None
                size = abs(float(r))
                kind = ("strong_" if size >= 0.5 else "moderate_") + ("positive" if r > 0 else "negative")
                results.append(
                    CorrelationResult(
                        column_a=str(cols[i]),
                        column_b=str(cols[j]),
                        coefficient=round(float(r), 4),
                        correlation_type=kind,
                        confidence=round(min(1.0, size), 4),
                        reasoning=f"Pearson correlation between '{cols[i]}' and '{cols[j]}' is {r:.2f} (n = {n}).",
                        p_value=p,
                        effect_size=size,
                        n=n,
                    )
                )
        return tuple(results)

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[CorrelationResult, ...]:
        settings = get_settings()
        corrected = apply_fdr(self.test_all(df, dataset_profile, business_profile, entities), settings.insight_fdr_q)
        kept = [c for c in corrected if reportable(c, settings.insight_min_effect_size)]
        return tuple(sorted(kept, key=lambda c: -(c.effect_size or 0)))
