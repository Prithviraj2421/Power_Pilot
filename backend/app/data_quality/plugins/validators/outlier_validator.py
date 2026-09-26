import numpy as np
import pandas as pd
from app.models.data_quality_models import IssueSeverity, QualityIssue


class OutlierValidator:
    """
    Detects IQR statistical outliers (mild, moderate, extreme) across numeric columns.
    """

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 5:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr <= 0:
                continue

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                pct = (outlier_count / len(series)) * 100
                severity = IssueSeverity.LOW
                if pct > 15:
                    severity = IssueSeverity.HIGH
                elif pct > 5:
                    severity = IssueSeverity.MEDIUM

                issues.append(
                    QualityIssue(
                        column=col,
                        issue_type="NUMERIC_OUTLIERS",
                        description=f"Column '{col}' has {outlier_count} statistical IQR outliers ({pct:.1f}%).",
                        affected_count=int(outlier_count),
                        affected_percentage=round(pct, 2),
                        severity=severity,
                        recommended_treatment="Winsorize, cap to [1.5*IQR bounds], or investigate extreme anomalies.",
                    )
                )

        return issues
