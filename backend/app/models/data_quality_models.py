from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class QualityGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ImputationStrategy(str, Enum):
    MEAN = "MEAN"
    MEDIAN = "MEDIAN"
    MODE = "MODE"
    CONSTANT = "CONSTANT"
    FFILL = "FFILL"
    BFILL = "BFILL"
    LEAVE = "LEAVE"


class DuplicateStrategy(str, Enum):
    REMOVE = "REMOVE"
    KEEP_FIRST = "KEEP_FIRST"
    KEEP_LAST = "KEEP_LAST"
    MARK_ONLY = "MARK_ONLY"


class OutlierStrategy(str, Enum):
    FLAG_ONLY = "FLAG_ONLY"
    WINSORIZE = "WINSORIZE"
    CAP = "CAP"
    REMOVE = "REMOVE"


@dataclass(slots=True, frozen=True)
class QualityIssue:
    column: str
    issue_type: str
    description: str
    affected_count: int
    affected_percentage: float
    severity: IssueSeverity
    recommended_treatment: str


@dataclass(slots=True, frozen=True)
class ColumnQualityScore:
    column_name: str
    completeness: float  # 0.0 to 100.0
    consistency: float   # 0.0 to 100.0
    validity: float      # 0.0 to 100.0
    uniqueness: float    # 0.0 to 100.0
    overall_score: float # 0.0 to 100.0


@dataclass(slots=True, frozen=True)
class DatasetQualityReport:
    dataset_name: str
    overall_score: float  # 0.0 to 100.0
    grade: QualityGrade
    grade_explanation: str
    total_issues_count: int
    column_scores: tuple[ColumnQualityScore, ...]
    detected_issues: tuple[QualityIssue, ...]


@dataclass(slots=True, frozen=True)
class AuditTrailEntry:
    column_name: str
    action_type: str
    before_sample: str
    after_sample: str
    rows_affected: int


@dataclass(slots=True, frozen=True)
class PreparationConfig:
    imputation_strategy: ImputationStrategy = ImputationStrategy.MEDIAN
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.REMOVE
    outlier_strategy: OutlierStrategy = OutlierStrategy.CAP
    normalize_categories: bool = True
    convert_dates: bool = True
    parse_numeric_strings: bool = True


@dataclass(slots=True, frozen=True)
class DataPreparationReport:
    dataset_name: str
    original_rows: int
    cleaned_rows: int
    rows_removed: int
    total_actions_count: int
    audit_trail: tuple[AuditTrailEntry, ...]
    summary_notes: tuple[str, ...]
