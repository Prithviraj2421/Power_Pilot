import pandas as pd
from app.models.data_quality_models import IssueSeverity, QualityIssue


class MissingValueValidator:
    """
    Detects missing values including null, NaN, empty strings, 'N/A', 'NULL', '-'.
    """

    NULL_TOKENS = {"n/a", "null", "none", "nan", "-", "", "undefined", "missing", "unknown"}

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        total_rows = len(df)
        if total_rows == 0:
            return issues

        for col in df.columns:
            series = df[col]
            # Standard null count
            null_mask = series.isna()
            
            # Token null count for string/object columns
            token_mask = pd.Series([False] * total_rows, index=df.index)
            if series.dtype == "object" or isinstance(series.dtype, pd.StringDtype):
                str_series = series.astype(str).str.strip().str.lower()
                token_mask = str_series.isin(self.NULL_TOKENS)

            combined_missing = (null_mask | token_mask).sum()
            if combined_missing > 0:
                pct = (combined_missing / total_rows) * 100
                severity = IssueSeverity.LOW
                if pct > 40:
                    severity = IssueSeverity.CRITICAL
                elif pct > 20:
                    severity = IssueSeverity.HIGH
                elif pct > 5:
                    severity = IssueSeverity.MEDIUM

                issues.append(
                    QualityIssue(
                        column=col,
                        issue_type="MISSING_VALUES",
                        description=f"Column '{col}' has {combined_missing} missing/null values ({pct:.1f}%).",
                        affected_count=int(combined_missing),
                        affected_percentage=round(pct, 2),
                        severity=severity,
                        recommended_treatment="Impute with median/mode or remove null rows if > 50%.",
                    )
                )

        return issues
