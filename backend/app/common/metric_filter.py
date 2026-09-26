"""Name-based identifier detection, shared across the pipeline and exporters.

The Schema Analyzer flags a column as an identifier only when its values are
actually unique, which misses repeating foreign keys: ``customer_id`` appearing 25
distinct times across 60 rows is not unique, so it is profiled as an ordinary
numeric measure. Statistically that is correct and analytically useless -- fitting
a trend line through ``customer_id`` over time produces a real number that means
nothing.

This heuristic complements the structural check by looking at the name, so callers
can exclude keys from anything that treats a column as a business measure.

Lives in ``app.common`` rather than in the Export Center because the intelligence
engines need it too, and intelligence must not depend on export.
"""

from __future__ import annotations


class SmartMetricFilter:
    """
    Utility filtering out technical identifiers (IDs, primary keys, serial numbers)
    so executive reports prioritize high-impact business metrics.
    """

    ID_KEYWORDS = {"id", "uuid", "pk", "key", "number", "serial", "code", "index", "row_num"}

    @classmethod
    def is_identifier_column(cls, col_name: str) -> bool:
        clean = col_name.lower().strip()
        if clean in cls.ID_KEYWORDS:
            return True
        if any(clean.endswith(f"_{kw}") or clean.startswith(f"{kw}_") for kw in ("id", "uuid", "pk", "key", "num")):
            return True
        return False

    @classmethod
    def filter_business_columns(cls, col_names: list[str]) -> list[str]:
        return [c for c in col_names if not cls.is_identifier_column(c)]
