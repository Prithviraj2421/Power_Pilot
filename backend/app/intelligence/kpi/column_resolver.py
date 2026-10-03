from __future__ import annotations

from typing import Iterable, Optional

from app.common.enums import PhysicalType, SemanticType
from app.common.keyword_match import any_keyword_matches
from app.common.powerbi_names import dax_column, powerbi_table_name
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity

_NUMERIC = {PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL}
_ID_TOKENS = ("id", "key", "code", "number", "no")
_TEXTUAL = {PhysicalType.CATEGORICAL, PhysicalType.TEXT}
_DATES = {PhysicalType.DATE, PhysicalType.DATETIME}

# Numeric columns that are labels, not quantities: summing or charting them means nothing.
LABEL_TOKENS = ("id", "key", "code", "zip", "postal", "pin", "phone", "index")

# Set on a profile when it describes a table that already exists in an open Power BI model.
POWERBI_TABLE_KEY = "powerbi_table"


def table_for(profile: DatasetProfile) -> str:
    """The Power BI table KPI formulas must name.

    A table read from a live model keeps its real name, which may contain spaces that
    ``powerbi_table_name`` would rewrite, so the formulas would no longer resolve there.
    Everything else (an uploaded file) gets the sanitised file-name stem.
    """
    return profile.metadata.get(POWERBI_TABLE_KEY) or powerbi_table_name(profile.dataset_name)


class ColumnResolver:
    """
    Maps a business role ("revenue", "employee id") onto a column the dataset
    actually has, so a KPI formula never references a column that isn't there.

    A KPI whose roles cannot all be resolved should be dropped, not emitted with
    an invented column name -- Power BI rejects the measure either way, and a
    missing KPI is honest where a broken one is not.
    """

    def __init__(self, profile: DatasetProfile, entities: Optional[list[DetectedEntity]] = None) -> None:
        self.table = table_for(profile)
        self._columns = list(profile.columns)
        # The detector's verdicts, which win over whatever is stamped on the column profile.
        self._entity_of = {e.column_name: e.entity_type for e in entities or []}

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

    def measures(self) -> list[str]:
        """Every numeric column that is a quantity rather than a label, in column order."""
        return [
            c.name
            for c in self._columns
            if c.physical_type in _NUMERIC and not c.identifier and not any_keyword_matches(c.name, LABEL_TOKENS)
        ]

    def dimension(
        self, semantic: Optional[SemanticType] = None, keywords: Iterable[str] = ()
    ) -> Optional[str]:
        """A column to group by. Descriptive text columns win over identifiers (names beat IDs)."""
        textual = [c for c in self._columns if c.physical_type in _TEXTUAL]
        descriptive = [c for c in textual if not c.identifier]
        return self._pick(descriptive, semantic, keywords) or self._pick(textual, semantic, keywords)

    def dimensions(self) -> list[str]:
        """Every descriptive text/category column, in column order."""
        return [c.name for c in self._columns if c.physical_type in _TEXTUAL and not c.identifier]

    def date(self, keywords: Iterable[str] = ()) -> Optional[str]:
        """A date column: a typed one, preferring a name match, else one the entity detector tagged."""
        dated = [c for c in self._columns if c.physical_type in _DATES]
        return self._pick(dated, SemanticType.DATE, keywords) or (dated[0].name if dated else None)

    def _pick(
        self, candidates: list[ColumnProfile], semantic: Optional[SemanticType], keywords: Iterable[str]
    ) -> Optional[str]:
        # Earlier keywords are the more specific ones, so they win over column order.
        for keyword in keywords:
            for column in candidates:
                if any_keyword_matches(column.name, (keyword,)):
                    return column.name
        if semantic is not None:
            for column in candidates:
                if self._entity_of.get(column.name, column.semantic_type) == semantic:
                    return column.name
        return None
