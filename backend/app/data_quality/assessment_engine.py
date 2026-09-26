import pandas as pd

from app.data_quality.plugins.validators.category_validator import CategoryValidator
from app.data_quality.plugins.validators.date_validator import DateValidator
from app.data_quality.plugins.validators.duplicate_validator import DuplicateValidator
from app.data_quality.plugins.validators.missing_validator import MissingValueValidator
from app.data_quality.plugins.validators.outlier_validator import OutlierValidator
from app.data_quality.plugins.validators.type_validator import TypeValidator
from app.models.data_quality_models import (
    ColumnQualityScore,
    DatasetQualityReport,
    QualityGrade,
    QualityIssue,
)


class DataQualityAssessmentEngine:
    """
    Phase 1 Orchestrator running all quality validator plugins and computing Dataset Quality Scores.
    """

    def __init__(self) -> None:
        self.validators = [
            MissingValueValidator(),
            DuplicateValidator(),
            TypeValidator(),
            CategoryValidator(),
            DateValidator(),
            OutlierValidator(),
        ]

    def assess(self, df: pd.DataFrame, dataset_name: str = "Dataset.csv") -> DatasetQualityReport:
        all_issues: list[QualityIssue] = []

        for validator in self.validators:
            try:
                issues = validator.validate(df)
                all_issues.extend(issues)
            except Exception:
                continue

        # Calculate Column Quality Scores
        column_scores: list[ColumnQualityScore] = []
        total_rows = len(df)

        for col in df.columns:
            if total_rows == 0:
                column_scores.append(
                    ColumnQualityScore(
                        column_name=col,
                        completeness=0.0,
                        consistency=0.0,
                        validity=0.0,
                        uniqueness=0.0,
                        overall_score=0.0,
                    )
                )
                continue

            series = df[col]
            missing_count = series.isna().sum()
            completeness = max(0.0, 100.0 - (missing_count / total_rows * 100.0))

            unique_count = series.nunique()
            uniqueness = (unique_count / total_rows * 100.0) if total_rows > 0 else 100.0

            col_issues = [i for i in all_issues if i.column == col]
            validity_penalty = sum(15 for i in col_issues if i.severity.value in ("CRITICAL", "HIGH"))
            validity = max(0.0, 100.0 - validity_penalty)

            consistency_penalty = sum(10 for i in col_issues if i.issue_type in ("CATEGORY_CASE_INCONSISTENCY", "NUMERIC_STORED_AS_TEXT"))
            consistency = max(0.0, 100.0 - consistency_penalty)

            col_overall = (completeness * 0.35) + (consistency * 0.25) + (validity * 0.25) + (uniqueness * 0.15)
            column_scores.append(
                ColumnQualityScore(
                    column_name=col,
                    completeness=round(completeness, 2),
                    consistency=round(consistency, 2),
                    validity=round(validity, 2),
                    uniqueness=round(uniqueness, 2),
                    overall_score=round(col_overall, 2),
                )
            )

        # Calculate Overall Dataset Quality Score
        if column_scores:
            dataset_score = sum(c.overall_score for c in column_scores) / len(column_scores)
        else:
            dataset_score = 100.0

        # Assign Letter Grade
        if dataset_score >= 95.0:
            grade = QualityGrade.A_PLUS
            explanation = "Exceptional data quality. Highly clean, consistent, and standardized dataset."
        elif dataset_score >= 85.0:
            grade = QualityGrade.A
            explanation = "High quality dataset. Minor missing values or minor category case variations detected."
        elif dataset_score >= 70.0:
            grade = QualityGrade.B
            explanation = "Good dataset quality. Requires automated missing value imputation and casing normalization."
        elif dataset_score >= 50.0:
            grade = QualityGrade.C
            explanation = "Fair dataset quality. Moderate missing values, invalid date strings, or outlier anomalies detected."
        elif dataset_score >= 30.0:
            grade = QualityGrade.D
            explanation = "Poor dataset quality. Severe missing values, key collisions, or numeric text formatting issues."
        else:
            grade = QualityGrade.F
            explanation = "Critical quality issues. High null ratios and malformed columns require heavy preparation."

        return DatasetQualityReport(
            dataset_name=dataset_name,
            overall_score=round(dataset_score, 1),
            grade=grade,
            grade_explanation=explanation,
            total_issues_count=len(all_issues),
            column_scores=tuple(column_scores),
            detected_issues=tuple(all_issues),
        )
