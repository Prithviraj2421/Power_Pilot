import pandas as pd
from app.models.data_quality_models import AuditTrailEntry, DuplicateStrategy


class DuplicateCleaner:
    """
    Handles row deduplication according to DuplicateStrategy.
    """

    def clean(self, df: pd.DataFrame, strategy: DuplicateStrategy) -> tuple[pd.DataFrame, list[AuditTrailEntry]]:
        if strategy == DuplicateStrategy.MARK_ONLY:
            return df, []

        total_dups = df.duplicated().sum()
        if total_dups == 0:
            return df, []

        keep_opt = "first" if strategy in (DuplicateStrategy.REMOVE, DuplicateStrategy.KEEP_FIRST) else "last"
        cleaned_df = df.drop_duplicates(keep=keep_opt)

        audit = [
            AuditTrailEntry(
                column_name="__FULL_DATASET__",
                action_type=f"DEDUPLICATE_ROWS_{strategy.value}",
                before_sample=f"total rows: {len(df)}",
                after_sample=f"cleaned rows: {len(cleaned_df)}",
                rows_affected=int(total_dups),
            )
        ]

        return cleaned_df, audit
