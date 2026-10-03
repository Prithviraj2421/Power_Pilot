"""A minimal DAX evaluator for the subset the KPI compiler emits.

It exists so tests can check that the DAX *string* we export means the same thing as the
value we computed with pandas, without needing Power BI. It is deliberately independent of
``PandasCompiler``: it parses the DAX text and evaluates it over plain Python rows.

BLANK is ``None``. Rules follow DAX: aggregates ignore blanks, DISTINCTCOUNT counts BLANK as a
value, an aggregate over no rows is BLANK, DIVIDE is BLANK on a zero or blank denominator (or a
blank numerator), subtraction treats one BLANK operand as 0, and multiplication by BLANK is BLANK.
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

_TOKEN = re.compile(
    r"""\s*(?:
        (?P<ref>'(?:[^']|'')+'\[(?:[^\]]|\]\])+\])
      | (?P<table>'(?:[^']|'')+')
      | (?P<string>"(?:[^"]|"")*")
      | (?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
      | (?P<name>[A-Za-z_][A-Za-z_0-9]*)
      | (?P<op><>|<=|>=|=|<|>|-|\*|\(|\)|,|\{|\})
    )""",
    re.VERBOSE,
)
_REF = re.compile(r"'(?:[^']|'')+'\[((?:[^\]]|\]\])+)\]")


def _tokens(text: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if not match or match.end() == pos:
            raise ValueError(f"cannot tokenize DAX at {text[pos:pos + 20]!r}")
        pos = match.end()
        kind = match.lastgroup
        out.append((kind, match.group(kind)))
    return out


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokens(text)
        self.pos = 0

    def peek(self) -> tuple[str, str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("end", "")

    def take(self) -> tuple[str, str]:
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, value: str) -> None:
        if self.take()[1] != value:
            raise ValueError(f"expected {value!r}")

    def parse(self) -> Any:
        node = self.argument()
        if self.peek()[0] != "end":
            raise ValueError("trailing tokens")
        return node

    def argument(self) -> Any:
        left = self.additive()
        kind, value = self.peek()
        if value in ("=", "<>", "<", "<=", ">", ">="):
            self.take()
            return ("cmp", value, left, self.additive())
        if kind == "name" and value == "IN":
            self.take()
            self.expect("{")
            items = [self.additive()]
            while self.peek()[1] == ",":
                self.take()
                items.append(self.additive())
            self.expect("}")
            return ("in", left, items)
        return left

    def additive(self) -> Any:
        node = self.multiplicative()
        while self.peek()[1] == "-":
            self.take()
            node = ("sub", node, self.multiplicative())
        return node

    def multiplicative(self) -> Any:
        node = self.primary()
        while self.peek()[1] == "*":
            self.take()
            node = ("mul", node, self.primary())
        return node

    def primary(self) -> Any:
        kind, value = self.take()
        if kind == "number":
            return ("num", float(value))
        if kind == "string":
            return ("str", value[1:-1].replace('""', '"'))
        if kind == "ref":
            return ("ref", _REF.fullmatch(value).group(1).replace("]]", "]"))
        if kind == "table":
            return ("table", value[1:-1])
        if value == "(":
            node = self.additive()
            self.expect(")")
            return node
        if value == "-":
            return ("neg", self.primary())
        if kind == "name":
            if self.peek()[1] == "(":
                self.take()
                args = []
                if self.peek()[1] != ")":
                    args.append(self.argument())
                    while self.peek()[1] == ",":
                        self.take()
                        args.append(self.argument())
                self.expect(")")
                return ("call", value.upper(), args)
        raise ValueError(f"unexpected token {value!r}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isnan(value)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _column(node: Any, rows: list[dict]) -> list[Any]:
    assert node[0] == "ref", f"expected a column reference, got {node[0]}"
    return [row[node[1]] for row in rows]


def _evaluate(node: Any, rows: list[dict]) -> Optional[float]:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "neg":
        inner = _evaluate(node[1], rows)
        return None if inner is None else -inner
    if kind == "sub":
        left, right = _evaluate(node[1], rows), _evaluate(node[2], rows)
        if left is None and right is None:
            return None
        return (left or 0.0) - (right or 0.0)
    if kind == "mul":
        left, right = _evaluate(node[1], rows), _evaluate(node[2], rows)
        return None if left is None or right is None else left * right
    assert kind == "call", f"cannot evaluate {kind}"
    name, args = node[1], node[2]
    if name == "DIVIDE":
        numerator, denominator = _evaluate(args[0], rows), _evaluate(args[1], rows)
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator
    if name == "CALCULATE":
        return _evaluate(args[0], [row for row in rows if _passes(args[1], row)])
    if not rows:
        return None
    if name == "COUNTROWS":
        return float(len(rows))
    values = _column(args[0], rows)
    if name == "COUNTA":
        return float(sum(not _blank(v) for v in values))
    if name == "DISTINCTCOUNT":
        return float(len({None if _blank(v) else v for v in values}))
    numbers = [float(v) for v in values if _is_number(v)]
    if not numbers:
        return None
    return {"SUM": sum, "AVERAGE": lambda xs: sum(xs) / len(xs), "MIN": min, "MAX": max}[name](numbers)


def _literal(node: Any) -> Any:
    if node[0] in ("num", "str"):
        return node[1]
    if node[0] == "neg":
        return -_literal(node[1])
    assert node[0] == "call" and node[1] in ("TRUE", "FALSE")
    return node[1] == "TRUE"


def _passes(node: Any, row: dict) -> bool:
    if node[0] == "in":
        cell = row[node[1][1]]
        return not _blank(cell) and cell in [_literal(item) for item in node[2]]
    assert node[0] == "cmp"
    cell, wanted = row[node[2][1]], _literal(node[3])
    if _blank(cell):
        return False
    if node[1] == "=":
        return cell == wanted
    if node[1] == "<>":
        return cell != wanted
    if not _is_number(cell):
        return False
    return {"<": cell < wanted, "<=": cell <= wanted, ">": cell > wanted, ">=": cell >= wanted}[node[1]]


def evaluate_dax(dax: str, rows: list[dict]) -> Optional[float]:
    """Evaluate a compiled measure body over ``rows`` (a list of column->value dicts)."""
    return _evaluate(_Parser(dax).parse(), rows)
