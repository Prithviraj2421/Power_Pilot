from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import pandas as pd

DISPLAY_FOLDER = "PowerPilot"
KPI_ANNOTATION = "PowerPilot_KpiId"


class ModelConnectionError(Exception):
    """The open model could not be reached or queried. The message is safe to show a user."""


@dataclass(frozen=True)
class TableInfo:
    name: str
    column_count: int
    row_count: int


@dataclass(frozen=True)
class TableData:
    """Rows read from one table. ``rows_total`` is what the model holds, ``frame`` what was read."""

    frame: pd.DataFrame
    rows_total: int

    @property
    def sampled(self) -> bool:
        return len(self.frame) < self.rows_total


@dataclass(frozen=True)
class MeasureInfo:
    table: str
    name: str
    expression: str
    display_folder: str = ""
    kpi_id: Optional[str] = None  # set only on measures PowerPilot wrote


@dataclass(frozen=True)
class NewMeasure:
    table: str
    name: str
    expression: str
    description: str
    kpi_id: str


class ModelConnector(Protocol):
    """A connection to the model open in Power BI Desktop.

    Implementations connect per call rather than holding a connection: Desktop closes the model's
    port when the report closes, so a held connection would only ever go stale.
    """

    def list_tables(self) -> list[TableInfo]:
        """Tables worth analysing: not hidden date tables, not measure-only tables."""
        ...

    def read_table(self, name: str, max_rows: int) -> TableData:
        """The table's rows (the first ``max_rows`` when it is larger), one column per data column."""
        ...

    def list_measures(self) -> list[MeasureInfo]:
        """Every measure in the model, whoever created it."""
        ...

    def run_dax(self, query: str) -> Optional[float]:
        """Run a DAX query returning a single value; ``None`` is BLANK."""
        ...

    def add_measures(self, measures: list[NewMeasure]) -> None:
        """Create the measures in one transaction, or none of them.

        Only ever adds. Raises ``ModelConnectionError`` rather than replace a measure that exists.
        """
        ...
