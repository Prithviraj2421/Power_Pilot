import pandas as pd
from app.models.data_quality_models import AuditTrailEntry


class DateCleaner:
    """
    Standardizes date columns to ISO 8601 YYYY-MM-DD strings.
    """

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[AuditTrailEntry]]:
        cleaned_df = df.copy()
        audit_trail = []

        for col in cleaned_df.columns:
            if "date" in col.lower() or "time" in col.lower() or "created" in col.lower() or "dob" in col.lower():
                series = cleaned_df[col].dropna()
                if len(series) == 0:
                    continue

                if pd.api.types.is_string_dtype(series) or series.dtype == "object":
                    parsed = pd.to_datetime(series, errors="coerce")
                    valid_mask = parsed.notna()

                    if valid_mask.sum() > 0:
                        iso_strings = parsed.dt.strftime("%Y-%m-%d")
                        cleaned_df.loc[valid_mask.index[valid_mask], col] = iso_strings[valid_mask]
                        audit_trail.append(
                            AuditTrailEntry(
                                column_name=col,
                                action_type="STANDARDIZE_DATES_ISO8601",
                                before_sample=f"'{series.iloc[0]}'",
                                after_sample=f"'{iso_strings.dropna().iloc[0]}'",
                                rows_affected=int(valid_mask.sum()),
                            )
                        )

        return cleaned_df, audit_trail
