import pandas as pd
from app.models.data_quality_models import IssueSeverity, QualityIssue


class CategoryValidator:
    """
    Detects casing inconsistencies and whitespace variations in categorical columns (e.g. 'Mumbai', 'mumbai', 'MUMBAI ').
    """

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            if pd.api.types.is_string_dtype(series) or series.dtype == "object":
                str_series = series.astype(str)
                raw_unique_count = str_series.nunique()
                cleaned_unique_count = str_series.str.strip().str.lower().nunique()

                if raw_unique_count > cleaned_unique_count:
                    diff = raw_unique_count - cleaned_unique_count
                    pct = (diff / raw_unique_count) * 100
                    issues.append(
                        QualityIssue(
                            column=col,
                            issue_type="CATEGORY_CASE_INCONSISTENCY",
                            description=f"Column '{col}' has {diff} category variations due to letter casing or whitespace (e.g. 'Mumbai' vs 'mumbai').",
                            affected_count=int(diff),
                            affected_percentage=round(pct, 2),
                            severity=IssueSeverity.MEDIUM,
                            recommended_treatment="Normalize category casing and trim surrounding whitespace.",
                        )
                    )

        return issues
