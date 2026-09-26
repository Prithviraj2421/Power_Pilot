"""
Schema Analyzer — the first module in the PowerPilot intelligence pipeline.

Takes a raw DataFrame and produces a complete DatasetProfile containing
structural understanding of every column: physical type, nullability,
uniqueness, identifier status, statistics, and sample values.
"""

import pandas as pd

from app.common.enums import PhysicalType
from app.intelligence.schema.identifier_detector import IdentifierDetector
from app.intelligence.schema.sample_calculator import SampleCalculator
from app.intelligence.schema.statistics_calculator import StatisticsCalculator
from app.intelligence.schema.type_detector import TypeDetector
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile


class SchemaAnalyzer:
    """
    Facade that orchestrates the complete schema analysis pipeline.

    For each column in a DataFrame, the analyzer runs four
    sub-components in order:

      1. **TypeDetector** — determines the physical data type
      2. **StatisticsCalculator** — computes missing/unique counts
      3. **IdentifierDetector** — checks if column is a primary key
      4. **SampleCalculator** — extracts representative values

    The results are assembled into a ``ColumnProfile`` per column,
    and all profiles are collected into a ``DatasetProfile``.
    """

    def __init__(self) -> None:
        """Initialize all sub-components."""
        self._type_detector = TypeDetector()
        self._statistics_calculator = StatisticsCalculator()
        self._identifier_detector = IdentifierDetector()
        self._sample_calculator = SampleCalculator()

    def analyze(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str,
    ) -> DatasetProfile:
        """
        Analyze a DataFrame and produce a complete structural profile.

        Parameters
        ----------
        dataframe : pd.DataFrame
            The dataset to analyze.
        dataset_name : str
            Human-readable name for the dataset (typically the filename).

        Returns
        -------
        DatasetProfile
            A complete structural profile of the dataset, including
            a ColumnProfile for every column.
        """
        columns: list[ColumnProfile] = []

        for column_name in dataframe.columns:
            series = dataframe[column_name]
            profile = self._analyze_column(series, str(column_name))
            columns.append(profile)

        return DatasetProfile(
            dataset_name=dataset_name,
            total_rows=len(dataframe),
            total_columns=len(dataframe.columns),
            columns=columns,
            metadata=self._build_dataset_metadata(dataframe, columns),
        )

    def _analyze_column(
        self,
        series: pd.Series,
        column_name: str,
    ) -> ColumnProfile:
        """
        Run the full analysis pipeline on a single column.

        Parameters
        ----------
        series : pd.Series
            The column data.
        column_name : str
            The column name.

        Returns
        -------
        ColumnProfile
            Complete profile for this column.
        """
        # Step 1: Detect physical type
        type_result = self._type_detector.detect(series)

        # Step 2: Compute statistics
        stats = self._statistics_calculator.calculate(series)

        # Step 3: Detect identifier status
        id_result = self._identifier_detector.detect(series, column_name)

        # Step 4: Extract sample values
        samples = self._sample_calculator.calculate(series)

        return ColumnProfile(
            name=column_name,
            physical_type=type_result.physical_type,
            nullable=stats.nullable,
            unique=stats.is_unique,
            identifier=id_result.is_identifier,
            missing_count=stats.missing_count,
            unique_count=stats.unique_count,
            sample_values=samples,
            confidence=type_result.confidence,
            metadata={
                "type_detection_evidence": list(type_result.evidence),
                "identifier_evidence": list(id_result.evidence),
                "identifier_confidence": id_result.confidence,
            },
        )

    @staticmethod
    def _build_dataset_metadata(
        dataframe: pd.DataFrame,
        columns: list[ColumnProfile],
    ) -> dict:
        """
        Build dataset-level metadata summarizing the analysis.

        Parameters
        ----------
        dataframe : pd.DataFrame
            The original DataFrame.
        columns : list[ColumnProfile]
            Analyzed column profiles.

        Returns
        -------
        dict
            Summary metadata about the dataset.
        """
        type_distribution: dict[str, int] = {}
        identifier_count = 0
        nullable_count = 0

        for col in columns:
            type_name = col.physical_type.value
            type_distribution[type_name] = (
                type_distribution.get(type_name, 0) + 1
            )
            if col.identifier:
                identifier_count += 1
            if col.nullable:
                nullable_count += 1

        return {
            "type_distribution": type_distribution,
            "identifier_columns": identifier_count,
            "nullable_columns": nullable_count,
            "memory_usage_bytes": int(
                dataframe.memory_usage(deep=True).sum()
            ),
        }
