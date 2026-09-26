import pandas as pd
from app.models.data_quality_models import AuditTrailEntry, ImputationStrategy


class MissingValueCleaner:
    """
    Imputes missing values using configured strategy (Mean, Median, Mode, Constant, FFill, BFill).
    """

    def clean(self, df: pd.DataFrame, strategy: ImputationStrategy) -> tuple[pd.DataFrame, list[AuditTrailEntry]]:
        if strategy == ImputationStrategy.LEAVE:
            return df, []

        cleaned_df = df.copy()
        audit_trail = []

        for col in cleaned_df.columns:
            series = cleaned_df[col]
            missing_count = series.isna().sum()
            if missing_count == 0:
                continue

            before_sample = str(series.dropna().iloc[0]) if len(series.dropna()) > 0 else "null"

            if pd.api.types.is_numeric_dtype(series):
                if strategy == ImputationStrategy.MEAN:
                    fill_val = series.mean()
                elif strategy == ImputationStrategy.MEDIAN:
                    fill_val = series.median()
                elif strategy == ImputationStrategy.MODE:
                    fill_val = series.mode()[0] if len(series.mode()) > 0 else 0
                elif strategy == ImputationStrategy.CONSTANT:
                    fill_val = 0
                elif strategy == ImputationStrategy.FFILL:
                    cleaned_df[col] = series.ffill().bfill()
                    fill_val = "ffill"
                else:
                    cleaned_df[col] = series.bfill().ffill()
                    fill_val = "bfill"

                if strategy in (ImputationStrategy.MEAN, ImputationStrategy.MEDIAN, ImputationStrategy.MODE, ImputationStrategy.CONSTANT):
                    cleaned_df[col] = series.fillna(fill_val)

                audit_trail.append(
                    AuditTrailEntry(
                        column_name=col,
                        action_type=f"IMPUTE_MISSING_{strategy.value}",
                        before_sample=f"missing: {missing_count}",
                        after_sample=f"filled with {fill_val}",
                        rows_affected=int(missing_count),
                    )
                )

            elif series.dtype == "object":
                mode_val = series.mode()[0] if len(series.mode()) > 0 else "Unknown"
                cleaned_df[col] = series.fillna(mode_val)
                audit_trail.append(
                    AuditTrailEntry(
                        column_name=col,
                        action_type="IMPUTE_MISSING_MODE",
                        before_sample=f"missing: {missing_count}",
                        after_sample=f"filled with '{mode_val}'",
                        rows_affected=int(missing_count),
                    )
                )

        return cleaned_df, audit_trail
