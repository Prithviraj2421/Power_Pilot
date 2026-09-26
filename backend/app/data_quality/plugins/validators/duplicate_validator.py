import pandas as pd
from app.models.data_quality_models import IssueSeverity, QualityIssue


class DuplicateValidator:
    """
    Detects duplicate rows and primary key collision issues.
    """

    def validate(self, df: pd.DataFrame) -> list[QualityIssue]:
        issues = []
        total_rows = len(df)
        if total_rows <= 1:
            return issues

        # Check full row duplicates
        dup_rows = df.duplicated().sum()
        if dup_rows > 0:
            pct = (dup_rows / total_rows) * 100
            severity = IssueSeverity.HIGH if pct > 10 else IssueSeverity.MEDIUM
            issues.append(
                QualityIssue(
                    column="__FULL_DATASET__",
                    issue_type="DUPLICATE_ROWS",
                    description=f"Dataset contains {dup_rows} identical duplicate rows ({pct:.1f}%).",
                    affected_count=int(dup_rows),
                    affected_percentage=round(pct, 2),
                    severity=severity,
                    recommended_treatment="Remove duplicate rows keeping the first record.",
                )
            )

        # Check column-level ID collisions
        for col in df.columns:
            if "id" in col.lower() or "key" in col.lower() or "code" in col.lower():
                non_null = df[col].dropna()
                dups_in_id = non_null.duplicated().sum()
                if dups_in_id > 0:
                    pct = (dups_in_id / len(non_null)) * 100
                    issues.append(
                        QualityIssue(
                            column=col,
                            issue_type="DUPLICATE_IDENTIFIER",
                            description=f"Identifier column '{col}' has {dups_in_id} duplicate key collisions ({pct:.1f}%).",
                            affected_count=int(dups_in_id),
                            affected_percentage=round(pct, 2),
                            severity=IssueSeverity.CRITICAL,
                            recommended_treatment="Deduplicate primary key values or verify source key generation.",
                        )
                    )

        return issues
