from typing import Optional

import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import CorrelationResult
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class CorrelationPlugin(BaseDataIntelligencePlugin):
    """
    Computes Pearson correlation matrix for numeric columns and flags pairs with |r| >= 0.5.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[CorrelationResult, ...]:
        num_cols = df.select_dtypes(include=["number"]).columns
        if len(num_cols) < 2:
            return ()

        corr_matrix = df[num_cols].corr(method="pearson")

        results = []
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                col_a = num_cols[i]
                col_b = num_cols[j]
                coef = corr_matrix.loc[col_a, col_b]

                if pd.isna(coef):
                    continue

                abs_coef = float(abs(coef))
                if abs_coef >= 0.5:
                    corr_type = "strong_positive" if coef > 0 else "strong_negative"
                    conf_score = round(min(1.0, abs_coef), 4)
                    reasoning = f"Pearson correlation between '{col_a}' and '{col_b}' is {coef:.2f}."

                    results.append(
                        CorrelationResult(
                            column_a=str(col_a),
                            column_b=str(col_b),
                            coefficient=round(float(coef), 4),
                            correlation_type=corr_type,
                            confidence=conf_score,
                            reasoning=reasoning,
                        )
                    )

        return tuple(results)
