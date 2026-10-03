"""Naming and escaping rules shared by every Power BI artifact we generate.

The KPI engine writes DAX formulas, the exporter writes the .bim model and the
Power Query script. If each derived the table name on its own they drifted
apart (`'orders.csv'[Sales]` in a measure, table `orders` in the model), and
none of the measures resolved.
"""

from __future__ import annotations

import re

_EXTENSION = re.compile(r"\.(csv|tsv|txt|xlsx|xlsm|xls)$", re.IGNORECASE)
_UNSAFE = re.compile(r"[^A-Za-z0-9_]+")


def powerbi_table_name(dataset_name: str) -> str:
    """The Power BI table name for an uploaded file: no extension, no punctuation."""
    stem = _EXTENSION.sub("", dataset_name.strip())
    cleaned = _UNSAFE.sub("_", stem).strip("_")
    return cleaned or "Dataset"


def dax_table(table: str) -> str:
    """A table reference, quoted so it is valid whatever the name contains."""
    return "'" + table.replace("'", "''") + "'"


def dax_column(table: str, column: str) -> str:
    """A fully qualified column reference. A literal `]` in a name is doubled."""
    return f"{dax_table(table)}[{column.replace(']', ']]')}]"


def m_string(value: str) -> str:
    """A Power Query text literal. Quotes are doubled; backslashes are literal in M."""
    return '"' + value.replace('"', '""') + '"'


_DAX_REFERENCE = re.compile(r"'((?:[^']|'')+)'\[((?:[^\]]|\]\])+)\]")


def dax_references(expression: str) -> list[tuple[str, str]]:
    """Every (table, column) a DAX expression refers to, with escapes undone."""
    return [(t.replace("''", "'"), c.replace("]]", "]")) for t, c in _DAX_REFERENCE.findall(expression)]
