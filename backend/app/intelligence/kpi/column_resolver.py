from __future__ import annotations

from typing import Iterable, Optional

from app.common.enums import PhysicalType, SemanticType
from app.common.keyword_match import any_keyword_matches
from app.common.powerbi_names import dax_column, table_name
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile

_NUMERIC = {PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL}
_ID_TOKENS = ("id", "key", "code", "number", "no")


class ColumnResolver:
    """
    Maps a business role ("revenue", "employee id") onto a column the dataset
    actually has, so a KPI formula never references a column that isn't there.

    A KPI whose roles cannot all be resolved should be dropped, not emitted with
    an invented column name -- Power BI rejects the measure either way, and a
    missing KPI is honest where a broken one is not.
    """

    def __init__(self, profile: DatasetProfile) -> None:
        self.table = table_name(profile.dataset_name)
        self._columns = list(profile.columns)

    def ref(self, column: str) -> str:
        return dax_column(self.table, column)

    def measure(
        self, semantic: Optional[SemanticType] = None, keywords: Iterable[str] = ()
    ) -> Optional[str]:
        """A numeric, non-identifier column: by detected entity type first, then by name."""
        candidates = [c for c in self._columns if c.physical_type in _NUMERIC and not c.identifier]
        return self._pick(candidates, semantic, keywords)

    def identifier(
        self, semantic: Optional[SemanticType] = None, keywords: Iterable[str] = ()
    ) -> Optional[str]:
        """A column that names an entity (order, customer, patient...), for DISTINCTCOUNT."""
        candidates = [c for c in self._columns if c.identifier or any_keyword_matches(c.name, _ID_TOKENS)]
        picked = self._pick(candidates, semantic, keywords)
        if picked is not None:
            return picked
        # No explicit ID column: fall back to any column of that entity type (e.g. a customer name).
        return self._pick(self._columns, semantic, keywords) if semantic else None

    @staticmethod
    def _pick(
        candidates: list[ColumnProfile], semantic: Optional[SemanticType], keywords: Iterable[str]
    ) -> Optional[str]:
        # Earlier keywords are the more specific ones, so they win over column order.
        for keyword in keywords:
            for column in candidates:
                if any_keyword_matches(column.name, (keyword,)):
                    return column.name
        if semantic is not None:
            for column in candidates:
                if column.semantic_type == semantic:
                    return column.name
        return None
