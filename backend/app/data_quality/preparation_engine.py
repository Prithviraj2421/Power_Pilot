import pandas as pd

from app.data_quality.plugins.cleaners.category_cleaner import CategoryCleaner
from app.data_quality.plugins.cleaners.date_cleaner import DateCleaner
from app.data_quality.plugins.cleaners.duplicate_cleaner import DuplicateCleaner
from app.data_quality.plugins.cleaners.missing_cleaner import MissingValueCleaner
from app.data_quality.plugins.cleaners.numeric_cleaner import NumericCleaner
from app.models.data_quality_models import (
    AuditTrailEntry,
    DataPreparationReport,
    PreparationConfig,
)


class DataPreparationEngine:
    """
    Phase 2 Orchestrator executing data cleaning, standardization, and audit trail generation.
    """

    def prepare(
        self, df: pd.DataFrame, config: PreparationConfig = PreparationConfig(), dataset_name: str = "Dataset.csv"
    ) -> tuple[pd.DataFrame, DataPreparationReport]:
        original_rows = len(df)
        cleaned_df = df.copy()
        all_audit: list[AuditTrailEntry] = []
        summary_notes: list[str] = []

        # 1. Parse Numeric & Currency Strings
        if config.parse_numeric_strings:
            cleaned_df, audit = NumericCleaner().clean(cleaned_df)
            all_audit.extend(audit)

        # 2. Normalize Categories & Casing
        if config.normalize_categories:
            cleaned_df, audit = CategoryCleaner().clean(cleaned_df)
            all_audit.extend(audit)

        # 3. Standardize Dates
        if config.convert_dates:
            cleaned_df, audit = DateCleaner().clean(cleaned_df)
            all_audit.extend(audit)

        # 4. Handle Missing Values
        cleaned_df, audit = MissingValueCleaner().clean(cleaned_df, config.imputation_strategy)
        all_audit.extend(audit)

        # 5. Remove Duplicates
        cleaned_df, audit = DuplicateCleaner().clean(cleaned_df, config.duplicate_strategy)
        all_audit.extend(audit)

        cleaned_rows = len(cleaned_df)
        rows_removed = original_rows - cleaned_rows

        summary_notes.append(f"Original dataset rows: {original_rows}")
        summary_notes.append(f"Cleaned dataset rows: {cleaned_rows} (removed {rows_removed} duplicate/invalid rows)")
        summary_notes.append(f"Total automated preparation actions executed: {len(all_audit)}")

        report = DataPreparationReport(
            dataset_name=dataset_name,
            original_rows=original_rows,
            cleaned_rows=cleaned_rows,
            rows_removed=rows_removed,
            total_actions_count=len(all_audit),
            audit_trail=tuple(all_audit),
            summary_notes=tuple(summary_notes),
        )

        return cleaned_df, report
