"""From a grid of cells to the numbers that need explaining, each with the words that describe it.

A "grid" is whatever a file reader produced (a worksheet, a CSV, a PDF table). Here we find the
tables in it, the header rows above and the label columns to the left, and for every number
collect ``row_labels`` and ``col_labels`` (the nearest non-numeric cells left and above, with
merged or blank cells carried over). Numbers the report computed itself (a ``=SUM`` cell, or a
"Total" row or column) are marked derived rather than treated as facts about the data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.reverse import formulas
from app.reverse.models import CellKind, DerivedInfo, LayoutCell, SheetLayout, TargetCell
from app.reverse.numbers import ParsedNumber

_TOTAL = re.compile(r"\b(grand\s*total|sub\s*-?\s*total|total|sum)\b", re.IGNORECASE)
_AVERAGE = re.compile(r"\b(average|avg|mean)\b", re.IGNORECASE)
_GRAND = re.compile(r"grand\s*total", re.IGNORECASE)
_AGGREGATE = re.compile(r"\b(all|overall|grand\s*total|sub\s*-?\s*total|total|sum|average|avg|mean)\b", re.IGNORECASE)
_GENERIC_SHEET = re.compile(r"^(sheet|page|table)\s*\d*$", re.IGNORECASE)


@dataclass
class Cell:
    row: int  # 0-based
    col: int
    text: str = ""  # what the report shows ("" when empty)
    number: Optional[ParsedNumber] = None
    formula: Optional[str] = None  # "=SUM(B2:B5)" for spreadsheet formula cells
    full_precision: bool = False


@dataclass
class Grid:
    name: str
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)
    merges: list[tuple[int, int, int, int]] = field(default_factory=list)  # r1, c1, r2, c2 (0-based, inclusive)

    @property
    def rows(self) -> int:
        return max((r for r, _ in self.cells), default=-1) + 1

    @property
    def cols(self) -> int:
        return max((c for _, c in self.cells), default=-1) + 1

    def add(self, cell: Cell) -> None:
        if cell.text or cell.number is not None:
            self.cells[(cell.row, cell.col)] = cell

    def text(self, row: int, col: int) -> str:
        """Visible text at a position, reading through merged ranges to their top-left cell."""
        cell = self.cells.get((row, col))
        if cell and cell.text:
            return _label_text(cell)
        for r1, c1, r2, c2 in self.merges:
            if r1 <= row <= r2 and c1 <= col <= c2:
                origin = self.cells.get((r1, c1))
                return _label_text(origin) if origin else ""
        return ""

    def merged_origin(self, row: int, col: int) -> Optional[tuple[int, int, int, int]]:
        for merge in self.merges:
            r1, c1, r2, c2 = merge
            if r1 <= row <= r2 and c1 <= col <= c2:
                return merge
        return None


def ref_of(row: int, col: int) -> str:
    return f"{formulas.column_letters(col + 1)}{row + 1}"


def _is_year(cell: Cell) -> bool:
    """A 4-digit whole number that reads as a year (a header like 2024, not a quantity)."""
    number = cell.number
    return bool(
        number
        and number.unit == "number"
        and number.decimals == 0
        and number.scale == 1.0
        and 1900 <= number.value <= 2100
        and re.fullmatch(r"\d{4}", cell.text.replace(",", "").strip() or "")
    )


def _label_text(cell: Cell) -> str:
    if cell.number is not None and _is_year(cell):
        return str(int(cell.number.value))
    return cell.text.strip()


def _bands(grid: Grid) -> list[list[int]]:
    """Runs of consecutive non-empty rows (tables are separated by blank rows)."""
    rows = sorted({r for r, _ in grid.cells})
    bands: list[list[int]] = []
    for r in rows:
        if bands and r == bands[-1][-1] + 1:
            bands[-1].append(r)
        else:
            bands.append([r])
    return bands


def extract(grid: Grid) -> tuple[list[TargetCell], SheetLayout]:
    """The report's numbers with their labels, and the layout to draw them back."""
    kinds: dict[tuple[int, int], CellKind] = {}
    target_ids: dict[tuple[int, int], str] = {}
    targets: list[TargetCell] = []
    pending_context: list[str] = []

    for number, band in enumerate(_bands(grid)):
        built = _read_band(grid, band, list(pending_context), kinds, target_ids, number)
        if built is None:  # text only: a title or caption for the table that follows
            for r in band:
                texts = [grid.text(r, c) for c in range(grid.cols) if grid.text(r, c)]
                pending_context.extend(texts)
                for c in range(grid.cols):
                    if (r, c) in grid.cells:
                        kinds[(r, c)] = "title"
            continue
        targets.extend(built)
        pending_context = []

    cells = tuple(
        LayoutCell(
            ref=ref_of(r, c),
            row=r,
            col=c,
            text=cell.text,
            kind=kinds.get((r, c), "other"),
            target_id=target_ids.get((r, c)),
        )
        for (r, c), cell in sorted(grid.cells.items())
    )
    return targets, SheetLayout(grid.name, grid.rows, grid.cols, cells)


def _first_data_row(grid: Grid, band: list[int]) -> Optional[int]:
    for r in band:
        for c in range(grid.cols):
            cell = grid.cells.get((r, c))
            if cell and cell.number is not None and not _is_year(cell):
                return r
    return None


def _read_band(
    grid: Grid,
    band: list[int],
    context: list[str],
    kinds: dict[tuple[int, int], CellKind],
    target_ids: dict[tuple[int, int], str],
    block: int = 0,
) -> Optional[list[TargetCell]]:
    first = _first_data_row(grid, band)
    if first is None:
        # all numbers are year-like (or there are none): a table of years has nothing to explain
        return None
    cols = sorted({c for r in band for c in range(grid.cols) if (r, c) in grid.cells})
    left, right = cols[0], cols[-1]
    data_rows = [r for r in band if r >= first]
    above = [r for r in band if r < first]

    # Titles: leading rows holding a single cell, left-aligned or spanning the whole table.
    titles: list[int] = []
    for r in above:
        own = [c for c in range(left, right + 1) if (r, c) in grid.cells]
        merge = grid.merged_origin(r, own[0]) if len(own) == 1 else None
        spans_all = merge is not None and merge[1] <= left and merge[3] >= right
        if len(own) == 1 and (merge is None or spans_all) and (own[0] == left or spans_all):
            titles.append(r)
            context.append(grid.text(r, own[0]))
            kinds[(r, own[0])] = "title"
        else:
            break
    header_rows = above[len(titles):]

    label_cols, index_cols = _label_columns(grid, data_rows, left, right)
    data_cols = [c for c in range(left, right + 1) if c not in label_cols and c not in index_cols]

    col_labels = _column_labels(grid, header_rows, data_cols, left)
    row_labels = _row_labels(grid, data_rows, label_cols)
    axis_names = tuple(
        t for t in (_header_above(grid, header_rows, c) for c in label_cols) if t
    )
    for r in header_rows:
        for c in range(left, right + 1):
            if (r, c) in grid.cells:
                kinds[(r, c)] = "header"
    for c in label_cols:
        for r in data_rows:
            if (r, c) in grid.cells:
                kinds[(r, c)] = "label"

    sheet_context = _sheet_context(grid.name)
    if sheet_context:
        context = [*context, sheet_context]

    total_rows = {r: _total_kind(row_labels[r]) for r in data_rows}
    total_cols = {c: _total_kind(col_labels.get(c, ())) for c in data_cols}
    # a typed "All Regions" row is a summary too: it is never one of the parts a Total adds up
    summary_rows = {r for r in data_rows if _is_summary(row_labels[r])}
    summary_cols = {c for c in data_cols if _is_summary(col_labels.get(c, ()))}
    targets: list[TargetCell] = []
    for r in data_rows:
        for c in data_cols:
            cell = grid.cells.get((r, c))
            if cell is None or cell.number is None:
                continue
            ident = f"{grid.name}!{ref_of(r, c)}"
            derived = _derived_info(grid, cell, r, c, data_rows, data_cols, total_rows, total_cols, summary_rows, summary_cols)
            targets.append(
                TargetCell(
                    id=ident,
                    sheet=grid.name,
                    cell_ref=ref_of(r, c),
                    value=cell.number.value,
                    shown_text=cell.text,
                    decimals_shown=cell.number.decimals,
                    unit=cell.number.unit,
                    scale=cell.number.scale,
                    row_labels=tuple(row_labels[r]),
                    col_labels=tuple(col_labels.get(c, ())),
                    context_labels=tuple(context),
                    row_axis_names=axis_names,
                    full_precision=cell.full_precision,
                    derived=derived,
                    block=block,
                )
            )
            kinds[(r, c)] = "derived" if derived else "value"
            target_ids[(r, c)] = ident
    return targets


def _sheet_context(name: str) -> str:
    return "" if _GENERIC_SHEET.match(name.strip()) else name.strip()


def _label_columns(grid: Grid, data_rows: list[int], left: int, right: int) -> tuple[list[int], set[int]]:
    """Leading columns that hold labels (text or years), and columns that merely number the rows."""
    labels: list[int] = []
    index: set[int] = set()
    for c in range(left, right + 1):
        cells = [grid.cells[(r, c)] for r in data_rows if (r, c) in grid.cells]
        if not cells:
            continue
        numbers = [x for x in cells if x.number is not None]
        texts = [x for x in cells if x.number is None and x.text.strip()]
        values = [x.number.value for x in numbers]
        is_sequence = (
            len(numbers) == len(data_rows) >= 3
            and not texts
            and values[0] in (0, 1)
            and values == [values[0] + i for i in range(len(values))]
        )
        if is_sequence:
            index.add(c)  # 1, 2, 3, ... numbering the rows: not data, not a label
            continue
        all_years = bool(numbers) and not texts and all(_is_year(x) for x in numbers)
        if len(numbers) / len(cells) < 0.5 or all_years:
            labels.append(c)
            continue
        break  # the first column of numbers: everything from here on is data
    return labels, index


def _header_above(grid: Grid, header_rows: list[int], col: int) -> str:
    for r in reversed(header_rows):
        text = grid.text(r, col)
        if text:
            return text
    return ""


def _column_labels(grid: Grid, header_rows: list[int], data_cols: list[int], left: int) -> dict[int, tuple[str, ...]]:
    out: dict[int, list[str]] = {c: [] for c in data_cols}
    for index, r in enumerate(header_rows):
        # Without real merged ranges (CSV, PDF), a super-header such as "2024" covers the blank cells to its right.
        spreads = not grid.merges and index < len(header_rows) - 1
        carried = ""
        for c in data_cols:
            cell = grid.cells.get((r, c))
            text = _label_text(cell) if cell else grid.text(r, c)
            if text:
                carried = text
            elif spreads:
                text = carried
            if text and (not out[c] or out[c][-1] != text):
                out[c].append(text)
    return {c: tuple(v) for c, v in out.items()}


def _row_labels(grid: Grid, data_rows: list[int], label_cols: list[int]) -> dict[int, list[str]]:
    """Labels per row. A blank cell in an outer label column repeats the group above (pivot-style)."""
    current: dict[int, str] = {}
    out: dict[int, list[str]] = {}
    last = label_cols[-1] if label_cols else None
    for r in data_rows:
        for c in label_cols:
            cell = grid.cells.get((r, c))
            text = _label_text(cell) if cell else grid.text(r, c)
            if text:
                current[c] = text
                for deeper in label_cols:
                    if deeper > c:
                        current.pop(deeper, None)  # a new group: inner labels start again
            elif c == last:
                current.pop(c, None)
        out[r] = [current[c] for c in label_cols if c in current]
    return out


def _is_summary(labels) -> bool:
    deepest = [label for label in labels if label]
    return bool(deepest) and bool(_AGGREGATE.search(deepest[-1]))


def _total_kind(labels) -> Optional[str]:
    """'total' | 'grand' | 'average' when the deepest label says the row/column is a computed figure."""
    for label in reversed(list(labels)):
        if _GRAND.search(label):
            return "grand"
        if _TOTAL.search(label):
            return "total"
        if _AVERAGE.search(label):
            return "average"
        break
    return None


def _derived_info(
    grid: Grid,
    cell: Cell,
    row: int,
    col: int,
    data_rows: list[int],
    data_cols: list[int],
    total_rows: dict[int, Optional[str]],
    total_cols: dict[int, Optional[str]],
    summary_rows: set[int],
    summary_cols: set[int],
) -> Optional[DerivedInfo]:
    if cell.formula:
        refs = formulas.references(cell.formula)
        if refs is not None:  # reads only this sheet: the report computed it itself
            sources = tuple(f"{grid.name}!{ref}" for ref in refs)
            return DerivedInfo("formula", sources, formulas.aggregate_of(cell.formula), cell.formula)
        return None

    def numeric(r: int, c: int) -> bool:
        other = grid.cells.get((r, c))
        return bool(other and other.number is not None)

    kind = total_rows.get(row)
    if kind:
        rows = [r for r in data_rows if r < row and numeric(r, col) and r not in summary_rows]
        if kind != "grand":  # stop at the previous subtotal
            previous = [r for r in data_rows if r < row and total_rows.get(r)]
            if previous:
                rows = [r for r in rows if r > previous[-1]]
        else:
            rows = [r for r in rows if not total_rows.get(r)]
        if len(rows) >= 2:
            op = "average" if kind == "average" else "sum"
            return DerivedInfo("total_label", tuple(f"{grid.name}!{ref_of(r, col)}" for r in rows), op)
    kind = total_cols.get(col)
    if kind:
        cols = [c for c in data_cols if c < col and numeric(row, c) and c not in summary_cols]
        if kind != "grand":
            previous = [c for c in data_cols if c < col and total_cols.get(c)]
            if previous:
                cols = [c for c in cols if c > previous[-1]]
        else:
            cols = [c for c in cols if not total_cols.get(c)]
        if len(cols) >= 2:
            op = "average" if kind == "average" else "sum"
            return DerivedInfo("total_label", tuple(f"{grid.name}!{ref_of(row, c)}" for c in cols), op)
    return None
