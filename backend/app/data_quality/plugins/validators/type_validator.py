import re
import pandas as pd
from app.models.data_quality_models import IssueSeverity, QualityIssue


class TypeValidator:
    """
    Detects numbers stored as text, currency symbols ($), percentage strings (%), and mixed data types.
    """

    CURRENCY_PATTERN = re.compile(r"^\s*[\$€£₹]\s*-?\d+(?:\,\d+)*(?:\.\d+)?\s*$")
    PERCENT_PATTERN = re.compile(r"^\s*-?\d+(?:\.\d+)?\%\s*$")
    NUMERIC_STRING_PATTERN = re.compile(r"^\s*-?\d+(?:\,\d+)*(?:\.\d+)?\s*$")

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        total_rows = len(df)
        if total_rows == 0:
            return issues

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            if pd.api.types.is_string_dtype(series) or series.dtype == "object":
                str_series = series.astype(str)

                # Check currency strings
                currency_matches = str_series.str.match(self.CURRENCY_PATTERN).sum()
                if currency_matches > 0:
                    pct = (currency_matches / len(series)) * 100
                    issues.append(
                        QualityIssue(
                            column=col,
                            issue_type="CURRENCY_FORMAT_TEXT",
                            description=f"Column '{col}' contains {currency_matches} currency-formatted text strings.",
                            affected_count=int(currency_matches),
                            affected_percentage=round(pct, 2),
                            severity=IssueSeverity.MEDIUM,
                            recommended_treatment="Parse currency symbols and cast column to FLOAT.",
                        )
                    )

                # Check percentage strings
                percent_matches = str_series.str.match(self.PERCENT_PATTERN).sum()
                if percent_matches > 0:
                    pct = (percent_matches / len(series)) * 100
                    issues.append(
                        QualityIssue(
                            column=col,
                            issue_type="PERCENTAGE_FORMAT_TEXT",
                            description=f"Column '{col}' contains {percent_matches} percentage-formatted text strings.",
                            affected_count=int(percent_matches),
                            affected_percentage=round(pct, 2),
                            severity=IssueSeverity.MEDIUM,
                            recommended_treatment="Parse '%' symbols and divide values by 100 to convert to FLOAT.",
                        )
                    )

                # Check numbers stored as text
                num_matches = str_series.str.match(self.NUMERIC_STRING_PATTERN).sum()
                if num_matches > 0 and currency_matches == 0 and percent_matches == 0:
                    pct = (num_matches / len(series)) * 100
                    if pct > 80:
                        issues.append(
                            QualityIssue(
                                column=col,
                                issue_type="NUMERIC_STORED_AS_TEXT",
                                description=f"Column '{col}' is stored as TEXT but contains {pct:.1f}% numeric values.",
                                affected_count=int(num_matches),
                                affected_percentage=round(pct, 2),
                                severity=IssueSeverity.HIGH,
                                recommended_treatment="Cast column type to INTEGER or FLOAT.",
                            )
                        )

        return issues
