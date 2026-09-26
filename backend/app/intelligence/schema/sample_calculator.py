from typing import Any

import pandas as pd

from app.common.constants import MAX_SAMPLE_VALUES


class SampleCalculator:
    """
    Extracts representative sample values from a dataset column.

    Selects diverse, informative sample values that give a human
    reader a quick understanding of what the column contains.

    Strategy varies by data type:
      - Numeric columns: min, max, median, plus additional unique values.
      - Non-numeric columns: most frequent values.
    """

    def calculate(self, series: pd.Series) -> list[Any]:
        """
        Extract up to MAX_SAMPLE_VALUES representative values.

        Parameters
        ----------
        series : pd.Series
            The column data to sample from.

        Returns
        -------
        list[Any]
            A list of representative sample values.
            Returns an empty list if the column is entirely null.
        """
        non_null = series.dropna()

        if len(non_null) == 0:
            return []

        unique_values = non_null.unique()

        # If fewer unique values than the limit, return all of them
        if len(unique_values) <= MAX_SAMPLE_VALUES:
            return self._to_native_types(unique_values.tolist())

        if pd.api.types.is_numeric_dtype(non_null):
            return self._sample_numeric(non_null, unique_values)

        return self._sample_non_numeric(non_null)

    def _sample_numeric(
        self,
        non_null: pd.Series,
        unique_values: Any,
    ) -> list[Any]:
        """
        Sample numeric columns using statistical landmarks.

        Includes min, max, and median to show the range and center,
        then fills remaining slots with additional unique values.

        Parameters
        ----------
        non_null : pd.Series
            Non-null numeric values.
        unique_values : array-like
            Unique values in the column.

        Returns
        -------
        list[Any]
            Up to MAX_SAMPLE_VALUES representative numeric values.
        """
        samples: list[Any] = []
        seen: set[Any] = set()

        # Statistical landmarks: min, median, max
        landmarks = [
            non_null.min(),
            non_null.median(),
            non_null.max(),
        ]

        for value in landmarks:
            native = self._to_native(value)
            if native not in seen:
                samples.append(native)
                seen.add(native)

        # Fill remaining slots with other unique values
        for value in unique_values:
            if len(samples) >= MAX_SAMPLE_VALUES:
                break
            native = self._to_native(value)
            if native not in seen:
                samples.append(native)
                seen.add(native)

        return samples[:MAX_SAMPLE_VALUES]

    def _sample_non_numeric(
        self,
        non_null: pd.Series,
    ) -> list[Any]:
        """
        Sample non-numeric columns using most frequent values.

        Parameters
        ----------
        non_null : pd.Series
            Non-null values from the column.

        Returns
        -------
        list[Any]
            Up to MAX_SAMPLE_VALUES most frequent values.
        """
        value_counts = non_null.value_counts()
        top_values = value_counts.head(MAX_SAMPLE_VALUES).index.tolist()
        return self._to_native_types(top_values)

    @staticmethod
    def _to_native(value: Any) -> Any:
        """
        Convert a numpy/pandas scalar to a native Python type.

        This prevents serialization issues when the values are
        later converted to JSON or stored in dataclass fields.

        Parameters
        ----------
        value : Any
            A potentially numpy-typed value.

        Returns
        -------
        Any
            The equivalent native Python type.
        """
        if hasattr(value, "item"):
            return value.item()
        return value

    @staticmethod
    def _to_native_types(values: list[Any]) -> list[Any]:
        """
        Convert a list of values to native Python types.

        Parameters
        ----------
        values : list[Any]
            List of potentially numpy-typed values.

        Returns
        -------
        list[Any]
            List with all values converted to native Python types.
        """
        return [
            v.item() if hasattr(v, "item") else v
            for v in values
        ]
