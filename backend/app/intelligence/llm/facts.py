"""Facts with identities, and the numbers found in text.

A fact is one number the pipeline computed, with an id (`F12`), a key (`kpi.total_sales_revenue.value`), a unit and a label
that says what it *means* ("Total Sales Revenue (KPI value)"). The model is shown facts by id and must cite the id next to every
number it writes; the verifier then checks the number against *that* fact, not against every number anywhere.

`find_numbers` reads the numbers in a piece of text the way a person writes them (`2.30M`, `91.7%`, `$1,200`), with the
precision they were written at. The same function tags numbers in the pipeline's free-text findings and checks the model's answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.reverse.numbers import parse_number

Unit = Literal["count", "number", "percent", "ratio", "currency", "coefficient"]

TAG = re.compile(r"\[(F\d+(?:\s*,\s*F\d+)*)\]")

_NUMBER = re.compile(
    r"""
    (?<![\w.])(?<!\d-)(?<!\d/)
    [-+]?[$£€]?
    (?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?
    (?:\s?(?:%|[KMB](?![A-Za-z])|(?:million|billion|thousand)\b))?
    (?![\w])(?!-\d)(?!/\d)
    """,
    re.VERBOSE,
)
_WORD_SCALE = {"million": "M", "billion": "B", "thousand": "K"}


@dataclass(frozen=True)
class Fact:
    id: str
    key: str
    value: float  # percent facts hold percent units (91.66 means 91.66%); ratio facts hold fractions (0.9166)
    unit: Unit
    label: str

    def to_dict(self) -> dict:
        return {"id": self.id, "key": self.key, "value": self.value, "unit": self.unit, "label": self.label}


@dataclass(frozen=True)
class FactSheet:
    """The text the model reads, and the structured facts behind every id in it."""

    text: str
    facts: dict[str, Fact]


@dataclass(frozen=True)
class Mention:
    """A number as written: where, its value in the units written, what it was decorated with, how precisely."""

    start: int
    end: int
    token: str
    value: float  # percent mentions are in percent units, "2.3M" is 2_300_000
    unit: Literal["number", "percent", "currency"]
    tolerance: float  # half a unit in the last digit written, in the same units as ``value``

    @property
    def decorated(self) -> bool:
        return self.unit != "number" or any(c.isalpha() for c in self.token)


def find_numbers(text: str) -> list[Mention]:
    found = []
    for match in _NUMBER.finditer(text):
        token = match.group(0)
        spelled = re.sub(r"\s?(million|billion|thousand)\b", lambda m: _WORD_SCALE[m.group(1)], token)
        parsed = parse_number(spelled.strip())
        if parsed is None:
            continue
        if parsed.unit == "percent":
            found.append(Mention(match.start(), match.end(), token, parsed.value * 100, "percent", parsed.tolerance * 100))
        else:
            found.append(Mention(match.start(), match.end(), token, parsed.value, "currency" if parsed.unit == "currency" else "number", parsed.tolerance))
    return found


def is_trivial(mention: Mention) -> bool:
    """A bare whole number from 0 to 10 ("3 steps", "top 5") carries no claim worth a citation."""
    return not mention.decorated and float(mention.value).is_integer() and 0 <= mention.value <= 10


def strip_citations(text: str) -> str:
    """The text without its [F12] tags (and the space before each)."""
    return re.sub(r"[ \t]?" + TAG.pattern, "", text)
