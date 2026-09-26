import pandas as pd

from app.models.identifier_result import IdentifierResult
from app.common.constants import IDENTIFIER_THRESHOLD


class IdentifierDetector:
    """
    Detects whether a dataset column serves as a primary key
    or unique identifier.

    Combines three independent heuristics — column name patterns,
    value uniqueness, and sequential integer detection — to produce
    a weighted confidence score with explainable evidence.

    Each heuristic contributes a fraction of the overall confidence:
      - Name pattern match: up to 0.40
      - Uniqueness ratio:   up to 0.40
      - Sequential pattern: up to 0.20
    """

    # ── Heuristic Weights ──────────────────────────────────────
    _NAME_WEIGHT: float = 0.40
    _UNIQUENESS_WEIGHT: float = 0.40
    _SEQUENTIAL_WEIGHT: float = 0.20

    # ── Confidence threshold for positive identification ───────
    _POSITIVE_THRESHOLD: float = 0.50

    # ── Name patterns that suggest an identifier column ────────
    _ID_PATTERNS: tuple[str, ...] = (
        "_id", "id_", "_key", "_code", "_no", "_num",
        "_pk", "_number", "_index",
    )
    _ID_EXACT_MATCHES: frozenset[str] = frozenset({
        "id", "key", "pk", "code", "index", "no", "number",
    })

    def detect(
        self,
        series: pd.Series,
        column_name: str,
    ) -> IdentifierResult:
        """
        Analyze a column to determine if it is an identifier.

        Parameters
        ----------
        series : pd.Series
            The column data to analyze.
        column_name : str
            The name of the column (used for name-pattern heuristic).

        Returns
        -------
        IdentifierResult
            Contains is_identifier flag, confidence score, and
            human-readable evidence explaining the decision.
        """
        evidence: list[str] = []
        non_null = series.dropna()

        if len(non_null) == 0:
            return IdentifierResult(
                is_identifier=False,
                confidence=0.0,
                evidence=("Column is entirely null",),
            )

        # ── Heuristic 1: Column name pattern ───────────────────
        name_score = self._score_name_pattern(column_name, evidence)

        # ── Heuristic 2: Value uniqueness ──────────────────────
        uniqueness_score = self._score_uniqueness(non_null, evidence)

        # ── Heuristic 3: Sequential integer pattern ────────────
        sequential_score = self._score_sequential(non_null, evidence)

        # ── Weighted combination ───────────────────────────────
        confidence = (
            name_score * self._NAME_WEIGHT
            + uniqueness_score * self._UNIQUENESS_WEIGHT
            + sequential_score * self._SEQUENTIAL_WEIGHT
        )
        confidence = round(min(confidence, 1.0), 4)

        is_identifier = confidence >= self._POSITIVE_THRESHOLD

        evidence.append(
            f"Weighted confidence: {confidence:.2f} "
            f"(name={name_score:.2f}×{self._NAME_WEIGHT}, "
            f"uniqueness={uniqueness_score:.2f}×{self._UNIQUENESS_WEIGHT}, "
            f"sequential={sequential_score:.2f}×{self._SEQUENTIAL_WEIGHT})"
        )

        return IdentifierResult(
            is_identifier=is_identifier,
            confidence=confidence,
            evidence=tuple(evidence),
        )

    def _score_name_pattern(
        self,
        column_name: str,
        evidence: list[str],
    ) -> float:
        """
        Score based on whether the column name matches known
        identifier naming conventions.

        Returns
        -------
        float
            1.0 if name matches, 0.0 otherwise.
        """
        normalized = column_name.strip().lower()

        if normalized in self._ID_EXACT_MATCHES:
            evidence.append(
                f"Column name '{column_name}' exactly matches "
                f"identifier pattern '{normalized}'"
            )
            return 1.0

        for pattern in self._ID_PATTERNS:
            if pattern in normalized:
                evidence.append(
                    f"Column name '{column_name}' contains "
                    f"identifier pattern '{pattern}'"
                )
                return 1.0

        evidence.append(
            f"Column name '{column_name}' does not match "
            f"any known identifier patterns"
        )
        return 0.0

    def _score_uniqueness(
        self,
        non_null: pd.Series,
        evidence: list[str],
    ) -> float:
        """
        Score based on the ratio of unique values to total values.

        Uses IDENTIFIER_THRESHOLD from constants as the minimum
        uniqueness ratio for a positive signal.

        Returns
        -------
        float
            Normalized uniqueness score (0.0 to 1.0).
        """
        unique_count = non_null.nunique()
        total_count = len(non_null)
        uniqueness_ratio = unique_count / total_count

        evidence.append(
            f"Uniqueness ratio: {unique_count}/{total_count} "
            f"= {uniqueness_ratio:.2%}"
        )

        if uniqueness_ratio >= IDENTIFIER_THRESHOLD:
            return min(uniqueness_ratio, 1.0)

        return 0.0

    def _score_sequential(
        self,
        non_null: pd.Series,
        evidence: list[str],
    ) -> float:
        """
        Score based on whether the column contains sequential integers.

        Checks for monotonically increasing integer values, which is
        a strong indicator of a surrogate key or auto-increment ID.

        Returns
        -------
        float
            1.0 if sequential integers detected, 0.0 otherwise.
        """
        if not pd.api.types.is_numeric_dtype(non_null):
            return 0.0

        try:
            as_int = non_null.astype(int)
        except (ValueError, TypeError):
            return 0.0

        # Check if values equal their integer cast (no fractional parts)
        if not (non_null == as_int).all():
            return 0.0

        if as_int.is_monotonic_increasing and len(as_int) > 1:
            evidence.append("Values are monotonically increasing integers")
            return 1.0

        return 0.0
