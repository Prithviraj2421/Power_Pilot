"""A small evaluator for the spreadsheet formulas people use in legacy reports.

Files written by other tools (openpyxl, exporters) carry formulas but no cached results, so a
``=SUM(B2:B5)`` total would otherwise have no value to explain. This covers cell references,
ranges, + - * / ^, percent literals and SUM / AVERAGE / MIN / MAX / COUNT / ROUND / ABS. Anything
else (other sheets, IF, lookups, ...) is "not understood": ``references`` and ``evaluate`` return
None rather than guess.
"""

from __future__ import annotations

import re
from typing import Callable, Optional, Union

_TOKEN = re.compile(
    r"""\s*(?:
        (?P<range>\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+)
      | (?P<ref>\$?[A-Z]{1,3}\$?\d+)(?![\w(!])
      | (?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
      | (?P<func>[A-Z][A-Z0-9.]*)(?=\()
      | (?P<op>[-+*/^%(),])
    )""",
    re.VERBOSE,
)
_REF = re.compile(r"\$?([A-Z]{1,3})\$?(\d+)")
Value = Union[float, list]


def column_number(letters: str) -> int:
    number = 0
    for char in letters:
        number = number * 26 + ord(char) - 64
    return number


def column_letters(number: int) -> str:
    letters = ""
    while number:
        number, rest = divmod(number - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def split_ref(ref: str) -> tuple[int, int]:
    """'B3' -> (row 3, column 2), both 1-based."""
    match = _REF.fullmatch(ref)
    return int(match.group(2)), column_number(match.group(1))


def expand_range(text: str) -> list[str]:
    first, last = (split_ref(part) for part in text.split(":"))
    rows = range(min(first[0], last[0]), max(first[0], last[0]) + 1)
    cols = range(min(first[1], last[1]), max(first[1], last[1]) + 1)
    return [f"{column_letters(c)}{r}" for r in rows for c in cols]


class _Unsupported(Exception):
    pass


def _tokens(formula: str) -> list[tuple[str, str]]:
    text = formula.strip()
    if text.startswith("="):
        text = text[1:]
    if "!" in text or '"' in text or "[" in text:
        raise _Unsupported
    out, pos = [], 0
    while pos < len(text):
        match = _TOKEN.match(text.upper(), pos)
        if not match or match.end() == pos:
            if not text[pos:].strip():
                break
            raise _Unsupported
        pos = match.end()
        out.append((match.lastgroup, match.group(match.lastgroup)))
    return out


class _Parser:
    def __init__(self, formula: str, lookup: Callable[[str], Optional[float]]) -> None:
        self.tokens = _tokens(formula)
        self.pos = 0
        self.lookup = lookup
        self.refs: list[str] = []

    def peek(self) -> tuple[str, str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("end", "")

    def take(self) -> tuple[str, str]:
        token = self.peek()
        self.pos += 1
        return token

    def parse(self) -> float:
        value = self.expression()
        if self.peek()[0] != "end":
            raise _Unsupported
        return _scalar(value)

    def expression(self) -> Value:
        value = self.term()
        while self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            right = self.term()
            value = _scalar(value) + _scalar(right) if op == "+" else _scalar(value) - _scalar(right)
        return value

    def term(self) -> Value:
        value = self.factor()
        while self.peek()[1] in ("*", "/"):
            op = self.take()[1]
            right = _scalar(self.factor())
            if op == "/":
                if right == 0:
                    raise _Unsupported  # #DIV/0!
                value = _scalar(value) / right
            else:
                value = _scalar(value) * right
        return value

    def factor(self) -> Value:
        if self.peek()[1] in ("-", "+"):
            sign = -1.0 if self.take()[1] == "-" else 1.0
            return sign * _scalar(self.factor())
        base = self.atom()
        if self.peek()[1] == "^":
            self.take()
            return _scalar(base) ** _scalar(self.factor())
        return base

    def atom(self) -> Value:
        kind, text = self.take()
        if kind == "number":
            value = float(text)
            while self.peek()[1] == "%":
                self.take()
                value /= 100
            return value
        if kind == "ref":
            self.refs.append(text.replace("$", ""))
            return self.lookup(text.replace("$", "")) or 0.0
        if kind == "range":
            cells = expand_range(text.replace("$", ""))
            self.refs.extend(cells)
            return [v for v in (self.lookup(c) for c in cells) if v is not None]
        if text == "(":
            value = self.expression()
            if self.take()[1] != ")":
                raise _Unsupported
            return value
        if kind == "func":
            self.take()  # the "("
            args: list[Value] = []
            if self.peek()[1] != ")":
                args.append(self.expression())
                while self.peek()[1] == ",":
                    self.take()
                    args.append(self.expression())
            if self.take()[1] != ")":
                raise _Unsupported
            return _call(text, args)
        raise _Unsupported


def _scalar(value: Value) -> float:
    if isinstance(value, list):
        if len(value) != 1:
            raise _Unsupported
        return value[0]
    return value


def _flatten(args: list[Value]) -> list[float]:
    flat: list[float] = []
    for arg in args:
        flat.extend(arg if isinstance(arg, list) else [arg])
    return flat


def _call(name: str, args: list[Value]) -> float:
    if name == "SUM":
        return float(sum(_flatten(args)))
    if name in ("AVERAGE", "MIN", "MAX"):
        numbers = _flatten(args)
        if not numbers:
            raise _Unsupported
        return {"AVERAGE": lambda xs: sum(xs) / len(xs), "MIN": min, "MAX": max}[name](numbers)
    if name == "COUNT":
        return float(len(_flatten(args)))
    if name == "ABS" and len(args) == 1:
        return abs(_scalar(args[0]))
    if name == "ROUND" and len(args) == 2:
        return float(round(_scalar(args[0]) + 0.0, int(_scalar(args[1]))))
    raise _Unsupported


def references(formula: str) -> Optional[list[str]]:
    """Every cell a same-sheet formula reads (ranges expanded), or None if it is not understood."""
    try:
        parser = _Parser(formula, lambda _ref: None)
        parser.parse()
    except (_Unsupported, ZeroDivisionError, OverflowError):
        return None
    return list(dict.fromkeys(parser.refs))


def evaluate(formula: str, lookup: Callable[[str], Optional[float]]) -> Optional[float]:
    """The formula's value, reading cells through ``lookup`` (None for blank); None if not understood."""
    try:
        return _Parser(formula, lookup).parse()
    except (_Unsupported, ZeroDivisionError, OverflowError):
        return None


_SIMPLE = re.compile(r"^=?\s*(SUM|AVERAGE|MIN|MAX)\((.*)\)\s*$", re.IGNORECASE)


def aggregate_of(formula: str) -> Optional[str]:
    """'sum' | 'average' | 'min' | 'max' when the whole formula is one such aggregate (or a + chain)."""
    match = _SIMPLE.match(formula.strip())
    if match and match.group(2).count("(") == 0:
        return {"SUM": "sum", "AVERAGE": "average", "MIN": "min", "MAX": "max"}[match.group(1).upper()]
    body = formula.strip().lstrip("=")
    if re.fullmatch(r"\$?[A-Za-z]{1,3}\$?\d+(\s*\+\s*\$?[A-Za-z]{1,3}\$?\d+)+", body):
        return "sum"
    return None
