"""An in-memory stand-in for a Power BI model, for tests that need no Power BI.

``run_dax`` evaluates the DAX *text* with the independent evaluator in ``tests/kpi/dax_oracle.py`` over the
model's own rows, so "engine value == pandas value" is checked for real rather than assumed.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

from app.common.powerbi_names import dax_references
from app.powerbi_live.connector import MeasureInfo, ModelConnectionError, NewMeasure, TableData, TableInfo
from tests.kpi.dax_oracle import evaluate_dax

_ROW = re.compile(r'^\s*EVALUATE\s+ROW\(\s*"v"\s*,\s*(?P<expr>.*)\)\s*$', re.DOTALL)
_COUNTROWS = re.compile(r"COUNTROWS\('((?:[^']|'')+)'\)")


def rows_of(frame: pd.DataFrame) -> list[dict]:
    return [
        {k: (None if pd.isna(v) else (v.item() if isinstance(v, np.generic) else v)) for k, v in row.items()}
        for row in frame.to_dict("records")
    ]


class FakeConnector:
    def __init__(
        self,
        tables: dict[str, pd.DataFrame],
        measures: Optional[list[MeasureInfo]] = None,
        *,
        engine_scale: float = 1.0,
        engine_blank: bool = False,
        engine_error: Optional[str] = None,
        save_error: Optional[str] = None,
    ) -> None:
        self.tables = tables
        self.measures: list[MeasureInfo] = list(measures or [])
        self.engine_scale = engine_scale
        self.engine_blank = engine_blank
        self.engine_error = engine_error
        self.save_error = save_error
        self.queries: list[str] = []
        self.add_calls: list[list[NewMeasure]] = []

    def list_tables(self) -> list[TableInfo]:
        return [TableInfo(n, len(df.columns), len(df)) for n, df in self.tables.items()]

    def read_table(self, name: str, max_rows: int) -> TableData:
        if name not in self.tables:
            raise ModelConnectionError(f"the model has no table named '{name}'")
        df = self.tables[name]
        return TableData(frame=df.head(max_rows).copy(), rows_total=len(df))

    def list_measures(self) -> list[MeasureInfo]:
        return list(self.measures)

    def run_dax(self, query: str) -> Optional[float]:
        self.queries.append(query)
        if self.engine_error:
            raise ModelConnectionError(self.engine_error)
        match = _ROW.match(query)
        assert match, f"the fake only understands EVALUATE ROW(\"v\", <measure>): {query!r}"
        expr = match.group("expr")
        refs = dax_references(expr)
        table = refs[0][0] if refs else _COUNTROWS.search(expr).group(1).replace("''", "'")
        value = evaluate_dax(expr, rows_of(self.tables[table]))
        if self.engine_blank or value is None:
            return None
        return value * self.engine_scale

    def add_measures(self, measures: list[NewMeasure]) -> None:
        self.add_calls.append(list(measures))
        if self.save_error:
            raise ModelConnectionError(self.save_error)
        taken = {m.name.lower() for m in self.measures}
        for new in measures:
            if new.name.lower() in taken:
                raise ModelConnectionError(f"a measure named '{new.name}' already exists in the model")
        for new in measures:
            self.measures.append(MeasureInfo(new.table, new.name, new.expression, "PowerPilot", new.kpi_id))
