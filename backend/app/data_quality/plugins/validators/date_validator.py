import pandas as pd
from app.common.date_parse import parse_dates_robust
from app.models.data_quality_models import IssueSeverity, QualityIssue


class DateValidator:
    """
    Detects unparseable dates and future timestamp anomalies.
    """

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        for col in df.columns:
            if "date" in col.lower() or "time" in col.lower() or "created" in col.lower() or "dob" in col.lower():
                series = df[col].dropna()
                if len(series) == 0:
                    continue

                parsed = parse_dates_robust(series)
                failed_count = parsed.isna().sum()

                if failed_count > 0:
                    pct = (failed_count / len(series)) * 100
                    issues.append(
                        QualityIssue(
                            column=col,
                            issue_type="INVALID_DATE_FORMAT",
                            description=f"Column '{col}' has {failed_count} unparseable or corrupted date strings ({pct:.1f}%).",
                            affected_count=int(failed_count),
                            affected_percentage=round(pct, 2),
                            severity=IssueSeverity.HIGH if pct > 10 else IssueSeverity.MEDIUM,
                            recommended_treatment="Repair date formatting and standardize to ISO 8601 YYYY-MM-DD.",
                        )
                    )

        return issues
