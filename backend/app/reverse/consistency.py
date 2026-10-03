"""Neighbours settle what a single number cannot.

"12" customers fits Customer ID, Customer Name and Product ID alike. But in a column of three such
numbers, Customer ID explains all three and Customer Name only two: the author used Customer ID.
Likewise, when every other number in a column follows one rule and one number does not, that number
is where a mistake is likely, and the rule says what it *should* have been.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from app.intelligence.kpi.compilers import PandasCompiler
from app.intelligence.kpi.ir import Difference, Expr, Filter, Measure, Ratio
from app.reverse.describe import describe, filters_of
from app.reverse.synthesizer import AMBIGUITY_MARGIN, Candidate, CellSearch, Synthesizer

COLUMN_WEIGHT = 3  # numbers under one heading are the strongest evidence of a shared rule
ROW_WEIGHT = 3
TABLE_WEIGHT = 1
MIN_PATTERN_SIZE = 4  # a group must be at least this big before deviating from it is called out
PATTERN_SHARE = 0.75


@dataclass
class Resolution:
    search: CellSearch
    chosen: Optional[Candidate] = None
    alternatives: list[Candidate] = field(default_factory=list)  # other shapes that also fit
    ambiguous: bool = False
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    support: int = 0  # neighbouring numbers explained by the chosen shape


@dataclass
class Expectation:
    """What the formula used by the neighbours gives for this cell."""

    expr: Expr
    value: Optional[float]
    source: str  # "the other 3 numbers in its column"
    shape: str


Key = tuple


def groups(searches: list[CellSearch]) -> tuple[dict[Key, list[str]], dict[Key, list[str]], dict[Key, list[str]]]:
    columns: dict[Key, list[str]] = defaultdict(list)
    rows: dict[Key, list[str]] = defaultdict(list)
    tables: dict[Key, list[str]] = defaultdict(list)
    for s in searches:
        t = s.target
        columns[(t.sheet, t.block, t.col_labels)].append(t.id)
        rows[(t.sheet, t.block, t.row_labels)].append(t.id)
        tables[(t.sheet, t.block)].append(t.id)
    return columns, rows, tables


def initial(search: CellSearch) -> Resolution:
    """The best shape if one stands clear of the rest; otherwise the cell is ambiguous."""
    resolution = Resolution(search)
    if not search.candidates:
        return resolution
    best = search.candidates[0]
    close = [c for c in search.candidates if c.score >= best.score - AMBIGUITY_MARGIN]
    resolution.chosen = best
    if len(close) == 1:
        if len(search.candidates) > 1:
            resolution.reasons.append(
                f"{len(search.candidates) - 1} other formula(s) also give this number, but the words in the report point at this one"
            )
    else:
        resolution.ambiguous = True
    resolution.alternatives = [c for c in search.candidates if c is not best and (not resolution.ambiguous or c in close)]
    return resolution


def resolve(searches: list[CellSearch]) -> dict[str, Resolution]:
    """Resolve every cell with numbers alone, then let neighbours settle the ambiguous ones."""
    resolutions = {s.target.id: initial(s) for s in searches}
    shapes = {s.target.id: {c.shape for c in s.candidates} for s in searches}
    columns, rows, tables = groups(searches)

    for _ in range(3):
        changed = False
        for ident, resolution in resolutions.items():
            if not resolution.ambiguous:
                continue
            target = resolution.search.target
            contenders = [resolution.chosen, *resolution.alternatives]
            tally: dict[str, tuple[int, int, int]] = {}
            for candidate in contenders:
                tally[candidate.shape] = (
                    _explained(columns[(target.sheet, target.block, target.col_labels)], ident, candidate.shape, shapes),
                    _explained(rows[(target.sheet, target.block, target.row_labels)], ident, candidate.shape, shapes),
                    _explained(tables[(target.sheet, target.block)], ident, candidate.shape, shapes),
                )

            def weight(shape: str) -> int:
                c, r, t = tally[shape]
                return COLUMN_WEIGHT * c + ROW_WEIGHT * r + TABLE_WEIGHT * t

            ranked = sorted(contenders, key=lambda c: (-weight(c.shape), -c.score))
            top, rest = ranked[0], ranked[1:]
            if weight(top.shape) > 0 and all(weight(top.shape) > weight(o.shape) for o in rest):
                c, r, t = tally[top.shape]
                where = []
                if c:
                    where.append(f"{c} other number(s) under the same heading")
                if r:
                    where.append(f"{r} other number(s) in the same row")
                if not where:
                    where.append(f"{t} other number(s) in the table")
                resolution.chosen = top
                resolution.alternatives = [o for o in contenders if o is not top and weight(o.shape) == weight(top.shape)]
                resolution.ambiguous = False
                resolution.support = c + r + t
                resolution.reasons.append("the same formula also explains " + " and ".join(where))
                dropped = [o for o in rest]
                if dropped:
                    resolution.reasons.append(
                        "other formulas that gave this number fail on its neighbours: " + "; ".join(describe(o.expr) for o in dropped[:3])
                    )
                changed = True
        if not changed:
            break

    _note_pattern_breaks(resolutions, columns)
    for ident, resolution in resolutions.items():
        if resolution.chosen is not None and not resolution.support:
            resolution.support = _support_of(resolution, resolutions, columns, rows)
    return resolutions


def _explained(group: list[str], me: str, shape: str, shapes: dict[str, set[str]]) -> int:
    return sum(1 for other in group if other != me and shape in shapes[other])


def _support_of(resolution, resolutions, columns, rows) -> int:
    t = resolution.search.target
    peers = {*columns[(t.sheet, t.block, t.col_labels)], *rows[(t.sheet, t.block, t.row_labels)]} - {t.id}
    return sum(1 for p in peers if resolutions[p].chosen is not None and resolutions[p].chosen.shape == resolution.chosen.shape)


def _note_pattern_breaks(resolutions: dict[str, Resolution], columns: dict[Key, list[str]]) -> None:
    for group in columns.values():
        solved = [resolutions[i] for i in group if resolutions[i].chosen is not None and not resolutions[i].ambiguous]
        if len(group) < MIN_PATTERN_SIZE or len(solved) < MIN_PATTERN_SIZE:
            continue
        counts = Counter(r.chosen.shape for r in solved)
        shape, count = counts.most_common(1)[0]
        if count / len(solved) < PATTERN_SHARE:
            continue
        example = next(r.chosen for r in solved if r.chosen.shape == shape)
        for r in solved:
            if r.chosen.shape != shape and shape not in {c.shape for c in r.search.candidates}:
                r.notes.append(
                    f"Its neighbours under the same heading all use '{describe(example.expr)}' (with their own filters); "
                    "this number fits a different formula, which is worth checking."
                )


# --- what the pattern says a missing number should have been ------------------------------


def pattern_for(
    target_id: str,
    searches: dict[str, CellSearch],
    resolutions: dict[str, Resolution],
    columns: dict[Key, list[str]],
    rows: dict[Key, list[str]],
    tables: dict[Key, list[str]],
) -> Optional[tuple[Candidate, list[Candidate], str]]:
    """The formula shape followed by most of this cell's neighbours: (template, peers using it, where from)."""
    t = searches[target_id].target
    for group, place in (
        (columns[(t.sheet, t.block, t.col_labels)], "under the same heading"),
        (rows[(t.sheet, t.block, t.row_labels)], "in the same row"),
        (tables[(t.sheet, t.block)], "in the table"),
    ):
        peers = [
            resolutions[i]
            for i in group
            if i != target_id and i in resolutions and resolutions[i].chosen and not resolutions[i].ambiguous
        ]
        if len(peers) < 2:
            continue
        counts = Counter(r.chosen.shape for r in peers)
        shape, count = counts.most_common(1)[0]
        if count >= 2 and count / len(peers) >= 0.6:
            users = [r.chosen for r in peers if r.chosen.shape == shape]
            return users[0], users, f"the {count} other number(s) {place}"
    return None


def _key(flt: Filter) -> tuple:
    return (flt.column, flt.part)


def instantiate(synth: Synthesizer, target, template: Expr, peers: list[Expr]) -> Expr:
    """The template formula with this cell's own labels in place of the template cell's.

    A filter the cell's labels do not mention is kept when every peer agrees on its value (a year the
    title states once) and dropped when peers disagree (a Total row has no single region).
    """
    own: dict[tuple, Filter] = {}
    for slot in synth.reader.hints_for(target).slots:
        for option in slot.options:
            for flt in option.filters:
                own.setdefault(_key(flt), flt)
    seen: dict[tuple, set[str]] = defaultdict(set)
    for peer in peers:
        for flt in filters_of(peer):
            seen[_key(flt)].add(repr(flt.value))

    def rebuild_filters(filters: tuple[Filter, ...]) -> tuple[Filter, ...]:
        out = []
        for flt in filters:
            k = _key(flt)
            if k in own:
                out.append(own[k])
            elif len(seen[k]) <= 1:
                out.append(flt)
        return tuple(out)

    def rebuild(node: Expr) -> Expr:
        if isinstance(node, Measure):
            return Measure(node.op, node.column, rebuild_filters(node.filters), node.group)
        if isinstance(node, Ratio):
            return Ratio(rebuild(node.numerator), rebuild(node.denominator), node.scale)
        return Difference(rebuild(node.minuend), rebuild(node.subtrahend))

    return rebuild(template)


def expectation_for(
    target_id: str,
    synth: Synthesizer,
    df: pd.DataFrame,
    searches: dict[str, CellSearch],
    resolutions: dict[str, Resolution],
    group_sets: tuple[dict[Key, list[str]], dict[Key, list[str]], dict[Key, list[str]]],
) -> Optional[Expectation]:
    found = pattern_for(target_id, searches, resolutions, *group_sets)
    if found is None:
        return None
    template, users, source = found
    target = searches[target_id].target
    expr = instantiate(synth, target, template.expr, [u.expr for u in users])
    try:
        value = PandasCompiler().evaluate(expr, df)
    except Exception:  # a formula that cannot be computed here gives no expectation
        return None
    return Expectation(expr, value, source, template.shape)
