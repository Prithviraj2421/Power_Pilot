import re
import pandas as pd
from app.models.data_quality_models import AuditTrailEntry


class NumericCleaner:
    """
    Parses currency strings ($), percentage strings (%), and removes commas from numeric text.
    """

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[AuditTrailEntry]]:
        cleaned_df = df.copy()
        audit_trail = []

        for col in cleaned_df.columns:
            series = cleaned_df[col]
            if pd.api.types.is_string_dtype(series) or series.dtype == "object":
                str_series = series.astype(str).str.strip()

                # Clean currency strings: "$1,250.00" -> 1250.00
                if str_series.str.contains(r"[\$€£₹]", regex=True).any():
                    clean_nums = (
                        str_series.str.replace(r"[\$€£₹\,]", "", regex=True)
                        .str.strip()
                    )
                    parsed_numeric = pd.to_numeric(clean_nums, errors="coerce")
                    if parsed_numeric.notna().sum() > 0:
                        rows_changed = parsed_numeric.notna().sum()
                        cleaned_df[col] = parsed_numeric
                        audit_trail.append(
                            AuditTrailEntry(
                                column_name=col,
                                action_type="PARSE_CURRENCY_TO_FLOAT",
                                before_sample=f"'{str_series.iloc[0]}'",
                                after_sample=f"{parsed_numeric.dropna().iloc[0]}",
                                rows_affected=int(rows_changed),
                            )
                        )
                        continue

                # Clean percentage strings: "85%" -> 0.85
                if str_series.str.contains(r"\%", regex=True).any():
                    clean_pct = str_series.str.replace("%", "", regex=False).str.strip()
                    parsed_pct = pd.to_numeric(clean_pct, errors="coerce") / 100.0
                    if parsed_pct.notna().sum() > 0:
                        rows_changed = parsed_pct.notna().sum()
                        cleaned_df[col] = parsed_pct
                        audit_trail.append(
                            AuditTrailEntry(
                                column_name=col,
                                action_type="PARSE_PERCENTAGE_TO_FLOAT",
                                before_sample=f"'{str_series.iloc[0]}'",
                                after_sample=f"{parsed_pct.dropna().iloc[0]}",
                                rows_affected=int(rows_changed),
                            )
                        )
                        continue

                # Clean numeric strings with commas: "1,000" -> 1000
                if str_series.str.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$").any():
                    clean_commas = str_series.str.replace(",", "", regex=False)
                    parsed_num = pd.to_numeric(clean_commas, errors="coerce")
                    if parsed_num.notna().sum() > 0:
                        rows_changed = parsed_num.notna().sum()
                        cleaned_df[col] = parsed_num
                        audit_trail.append(
                            AuditTrailEntry(
                                column_name=col,
                                action_type="PARSE_COMMAS_TO_NUMERIC",
                                before_sample=f"'{str_series.iloc[0]}'",
                                after_sample=f"{parsed_num.dropna().iloc[0]}",
                                rows_affected=int(rows_changed),
                            )
                        )

        return cleaned_df, audit_trail
