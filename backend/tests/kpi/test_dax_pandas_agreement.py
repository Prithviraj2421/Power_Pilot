"""Property test: the DAX we export and the value we compute must mean the same thing.

Random expressions are compiled to DAX, the DAX *text* is evaluated by an independent mini
evaluator (``dax_oracle``) over plain Python rows, and the result must equal the pandas
compiler's value on the same data. No Power BI needed; seeded, so failures reproduce.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
import pytest

from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.ir import Compare, Difference, Filter, Measure, Op, Ratio

from tests.kpi.dax_oracle import evaluate_dax

NUMERIC = ("price", "qty", "cost")  # have blanks
FILTERABLE_NUMERIC = ("score",)  # no blanks: DAX and pandas differ on blank comparisons, which verification rejects
CATEGORIES = ("North", "South", "East", "West", 'Quote"d')


def make_frame(rng: random.Random, rows: int) -> pd.DataFrame:
    def with_blanks(values: list[float]) -> list:
        return [None if rng.random() < 0.12 else v for v in values]

    return pd.DataFrame(
        {
            "price": with_blanks([round(rng.uniform(1, 500), 2) for _ in range(rows)]),
            "qty": with_blanks([float(rng.randint(1, 20)) for _ in range(rows)]),
            "cost": with_blanks([round(rng.uniform(0, 300), 2) for _ in range(rows)]),
            "score": [round(rng.uniform(-5, 5), 3) for _ in range(rows)],
            "region": [rng.choice(CATEGORIES) for _ in range(rows)],
            "ticket": [f"T{rng.randint(1, max(2, rows // 2))}" if rng.random() > 0.1 else None for _ in range(rows)],
        }
    )


def random_filter(rng: random.Random):
    kind = rng.choice(["eq", "ne", "in", "num"])
    if kind == "eq":
        return Filter("region", Compare.EQ, rng.choice(CATEGORIES))
    if kind == "ne":
        return Filter("region", Compare.NE, rng.choice(CATEGORIES))
    if kind == "in":
        return Filter("region", Compare.IN, tuple(rng.sample(CATEGORIES, rng.randint(1, 3))))
    return Filter(
        "score",
        rng.choice([Compare.GT, Compare.GE, Compare.LT, Compare.LE]),
        round(rng.uniform(-4, 4), 2),
    )


def random_measure(rng: random.Random) -> Measure:
    flt = random_filter(rng) if rng.random() < 0.4 else None
    op = rng.choice([Op.SUM, Op.AVERAGE, Op.MIN, Op.MAX, Op.COUNT, Op.DISTINCT_COUNT])
    if op is Op.COUNT and rng.random() < 0.4:
        return Measure(Op.COUNT, None, flt)
    if op in (Op.COUNT, Op.DISTINCT_COUNT):
        return Measure(op, rng.choice(NUMERIC + ("region", "ticket")), flt)
    return Measure(op, rng.choice(NUMERIC), flt)


def random_expr(rng: random.Random, depth: int = 0):
    roll = rng.random()
    if depth >= 2 or roll < 0.5:
        return random_measure(rng)
    if roll < 0.78:
        return Ratio(random_expr(rng, depth + 1), random_expr(rng, depth + 1), scale=rng.choice([1, 1, 100, 0.5]))
    return Difference(random_expr(rng, depth + 1), random_expr(rng, depth + 1))


def agree(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def rows_of(df: pd.DataFrame) -> list[dict]:
    return [
        {k: (None if pd.isna(v) else (v.item() if isinstance(v, np.generic) else v)) for k, v in row.items()}
        for row in df.to_dict("records")
    ]


@pytest.mark.parametrize("seed", range(8))
def test_compiled_dax_and_pandas_agree_on_random_expressions(seed: int) -> None:
    rng = random.Random(seed)
    compiler, pandas_compiler = DaxCompiler("Sales_Data"), PandasCompiler()
    blanks = values = 0

    for _ in range(60):
        frame = make_frame(rng, rng.choice([1, 2, 5, 40, 200]))
        expr = random_expr(rng)
        dax = compiler.compile(expr)

        expected = pandas_compiler.evaluate(expr, frame)
        actual = evaluate_dax(dax, rows_of(frame))

        assert agree(expected, actual), f"{dax}\n pandas={expected!r} dax-oracle={actual!r}"
        blanks += expected is None
        values += expected is not None

    assert values > 10, "the generator must mostly produce real values, or the test proves little"


def test_the_generator_exercises_blanks_filters_and_every_op() -> None:
    rng = random.Random(123)
    seen_ops, filtered, blank_results = set(), 0, 0
    for _ in range(400):
        expr = random_expr(rng)
        text = DaxCompiler("T").compile(expr)
        seen_ops |= {name for name in ("SUM", "AVERAGE", "MIN", "MAX", "COUNTA", "COUNTROWS", "DISTINCTCOUNT", "DIVIDE") if name in text}
        filtered += "CALCULATE" in text
        blank_results += PandasCompiler().evaluate(expr, make_frame(rng, 5)) is None
    assert len(seen_ops) == 8 and filtered > 20 and blank_results > 5
