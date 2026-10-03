from __future__ import annotations

from app.common.powerbi_names import dax_column, dax_table
from app.intelligence.kpi.ir import Compare, DatePart, Difference, Expr, Filter, Measure, Op, Ratio, Scalar

_FUNCTIONS = {
    Op.SUM: "SUM",
    Op.AVERAGE: "AVERAGE",
    Op.MIN: "MIN",
    Op.MAX: "MAX",
    Op.COUNT: "COUNTA",
    Op.DISTINCT_COUNT: "DISTINCTCOUNT",
}
_DATE_FUNCTIONS = {DatePart.YEAR: "YEAR", DatePart.QUARTER: "QUARTER", DatePart.MONTH: "MONTH"}
_OPERATORS = {
    Compare.EQ: "=",
    Compare.NE: "<>",
    Compare.GT: ">",
    Compare.GE: ">=",
    Compare.LT: "<",
    Compare.LE: "<=",
}


def literal(value: Scalar) -> str:
    """A DAX literal. Booleans are checked first because ``True`` is an ``int`` in Python."""
    if isinstance(value, bool):
        return "TRUE()" if value else "FALSE()"
    if isinstance(value, (int, float)):
        return repr(value)
    return '"' + value.replace('"', '""') + '"'


class DaxCompiler:
    """Compiles KPI expressions to DAX measure bodies for one Power BI table."""

    def __init__(self, table: str) -> None:
        self.table = table

    def ref(self, column: str) -> str:
        return dax_column(self.table, column)

    def compile(self, expr: Expr) -> str:
        if isinstance(expr, Measure):
            if expr.group:
                raise ValueError("a grouped measure is a table, not a measure; use compile_query")
            return self._measure(expr)
        if isinstance(expr, Ratio):
            text = f"DIVIDE({self.compile(expr.numerator)}, {self.compile(expr.denominator)})"
            return text if expr.scale == 1 else f"{text} * {expr.scale:g}"
        left = self.compile(expr.minuend)
        right = self.compile(expr.subtrahend)
        if isinstance(expr.subtrahend, Difference):
            right = f"({right})"
        return f"{left} - {right}"

    def compile_query(self, measure: Measure, name: str = "Value") -> str:
        """A grouped measure as a DAX query (what a visual would run), not a measure body."""
        if not measure.group:
            raise ValueError("compile_query needs a grouped measure")
        label = name.replace('"', '""')
        return f'SUMMARIZECOLUMNS({self.ref(measure.group)}, "{label}", {self._measure(measure)})'

    def _measure(self, measure: Measure) -> str:
        if measure.op is Op.COUNT and measure.column is None:
            body = f"COUNTROWS({dax_table(self.table)})"
        else:
            body = f"{_FUNCTIONS[measure.op]}({self.ref(measure.column)})"
        if not measure.filters:
            return body
        return f"CALCULATE({body}, {', '.join(self._filter(f) for f in measure.filters)})"

    def _filter(self, flt: Filter) -> str:
        column = self.ref(flt.column)
        if flt.part is not None:
            column = f"{_DATE_FUNCTIONS[flt.part]}({column})"
        if flt.compare is Compare.IN:
            return f"{column} IN {{{', '.join(literal(v) for v in flt.value)}}}"
        return f"{column} {_OPERATORS[flt.compare]} {literal(flt.value)}"
