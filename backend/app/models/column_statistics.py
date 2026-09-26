from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ColumnStatistics:
    """
    Statistical summary for a single dataset column.

    Produced by the StatisticsCalculator and consumed by the
    SchemaAnalyzer to populate ColumnProfile fields.

    Attributes
    ----------
    missing_count : int
        Number of null / NaN values in the column.

    unique_count : int
        Number of distinct non-null values.

    total_count : int
        Total number of rows in the column (including nulls).

    nullable : bool
        True if the column contains at least one null value.

    is_unique : bool
        True if all non-null values are unique.
    """

    missing_count: int
    unique_count: int
    total_count: int
    nullable: bool
    is_unique: bool
