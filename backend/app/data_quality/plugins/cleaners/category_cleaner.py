import pandas as pd
from app.models.data_quality_models import AuditTrailEntry


class CategoryCleaner:
    """
    Normalizes string casing and trims whitespace for text/categorical columns.
    """

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[AuditTrailEntry]]:
        cleaned_df = df.copy()
        audit_trail = []

        for col in cleaned_df.columns:
            series = cleaned_df[col]
            if pd.api.types.is_string_dtype(series) or series.dtype == "object":
                str_series = series.astype(str)
                trimmed = str_series.str.strip().str.title()
                
                changed_mask = str_series != trimmed
                changed_count = changed_mask.sum()

                if changed_count > 0:
                    cleaned_df[col] = trimmed
                    audit_trail.append(
                        AuditTrailEntry(
                            column_name=col,
                            action_type="NORMALIZE_CATEGORIES",
                            before_sample=f"e.g. '{str_series.iloc[0]}'",
                            after_sample=f"e.g. '{trimmed.iloc[0]}'",
                            rows_affected=int(changed_count),
                        )
                    )

        return cleaned_df, audit_trail
