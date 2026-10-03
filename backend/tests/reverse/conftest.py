from __future__ import annotations

import pandas as pd
import pytest

from app.reverse.index import DataIndex
from app.reverse.models import TargetCell
from app.reverse.synthesizer import Synthesizer

from tests.reverse import legacy_reports as lr


def target(
    value: float,
    rows=(),
    cols=(),
    *,
    decimals: int = 2,
    unit: str = "number",
    scale: float = 1.0,
    ctx=(),
    axis=(),
    shown: str = "",
    ident: str = "S!B2",
    block: int = 0,
    derived=None,
) -> TargetCell:
    return TargetCell(
        id=ident,
        sheet=ident.split("!")[0],
        cell_ref=ident.split("!")[1],
        value=value,
        shown_text=shown or f"{value:,.{decimals}f}",
        decimals_shown=decimals,
        unit=unit,  # type: ignore[arg-type]
        scale=scale,
        row_labels=tuple(rows),
        col_labels=tuple(cols),
        context_labels=tuple(ctx),
        row_axis_names=tuple(axis),
        block=block,
        derived=derived,
    )


@pytest.fixture(scope="session")
def golden_df() -> pd.DataFrame:
    return lr.golden()


@pytest.fixture(scope="session")
def golden_index(golden_df) -> DataIndex:
    return DataIndex(golden_df)


@pytest.fixture(scope="session")
def golden_synth(golden_index) -> Synthesizer:
    return Synthesizer(golden_index)
