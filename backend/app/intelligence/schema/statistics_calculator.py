import pandas as pd

from app.models.column_statistics import ColumnStatistics


class StatisticsCalculator:
    """
    Computes summary statistics for a single dataset column.

    Produces a ColumnStatistics value object containing counts
    and boolean flags that feed into the ColumnProfile.
    """

    def calculate(self, series: pd.Series) -> ColumnStatistics:
        """
        Compute statistics for a pandas Series.

        Parameters
        ----------
        series : pd.Series
            The column data to analyze.

        Returns
        -------
        ColumnStatistics
            Immutable statistics including missing count, unique count,
            nullable flag, and uniqueness flag.
        """
        total_count = len(series)
        missing_count = int(series.isna().sum())
        non_null_count = total_count - missing_count

        if non_null_count == 0:
            return ColumnStatistics(
                missing_count=missing_count,
                unique_count=0,
                total_count=total_count,
                nullable=True,
                is_unique=False,
            )

        unique_count = int(series.nunique(dropna=True))

        return ColumnStatistics(
            missing_count=missing_count,
            unique_count=unique_count,
            total_count=total_count,
            nullable=missing_count > 0,
            is_unique=unique_count == non_null_count,
        )
