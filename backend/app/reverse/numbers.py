"""Reading the numbers a person sees in a report: "1.2M", "12.5%", "₹1,24,500", "(1,200)".

What matters for proving a formula is not just the value but the **precision the report shows**:
"1.2M" says the true figure lies within 50,000 of 1,200,000, so a formula giving 1,234,567 is a
match while one giving 1,260,000 is not. ``ParsedNumber.tolerance`` carries that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

Unit = Literal["number", "percent", "currency"]

# Suffix -> how much one displayed unit is worth. "Cr" is a crore (Indian grouping); "Lakh"/"Lac" 1e5.
_SUFFIXES = {
    "k": 1e3,
    "m": 1e6,
    "mn": 1e6,
    "mm": 1e6,
    "b": 1e9,
    "bn": 1e9,
    "l": 1e5,
    "lac": 1e5,
    "lakh": 1e5,
    "lakhs": 1e5,
    "cr": 1e7,
    "crore": 1e7,
    "crores": 1e7,
}
_CURRENCY = re.compile(r"[$€£¥₹]|\b(?:rs|inr|usd|eur|gbp)\b\.?", re.IGNORECASE)
_BLANKS = {"", "-", "–", "—", "n/a", "na", "nan", "null", "none", "#n/a", "#div/0!", "#value!", "#ref!"}
_WESTERN = re.compile(r"^\d{1,3}(,\d{3})+$")
_INDIAN = re.compile(r"^\d{1,2}(,\d{2})+,\d{3}$")
_DOT_GROUPS = re.compile(r"^\d{1,3}(\.\d{3}){2,}$")
_SPACE_GROUPS = re.compile(r"^\d{1,3}([   ']\d{3})+$")


@dataclass(frozen=True)
class ParsedNumber:
    """A number as shown: its value, how many decimals were displayed, and in what unit."""

    value: float  # in real units: "12.5%" -> 0.125, "1.2M" -> 1_200_000
    decimals: int  # decimals displayed, in the displayed unit (12.5% -> 1, 1.2M -> 1)
    unit: Unit = "number"
    scale: float = 1.0  # the real size of one displayed unit: 0.01 for %, 1e6 for M, else 1

    @property
    def tolerance(self) -> float:
        """Half a unit in the last place shown, in real units."""
        return 0.5 * 10 ** (-self.decimals) * self.scale


def _mantissa(text: str) -> Optional[tuple[float, int]]:
    """Parse digits with unknown grouping/decimal separators into (value, decimals shown)."""
    text = text.strip()
    if not text or not re.fullmatch(r"[\d.,  ' ]+", text) or not re.search(r"\d", text):
        return None
    decimal = ""
    if "." in text and "," in text:
        decimal = "." if text.rfind(".") > text.rfind(",") else ","
    elif "," in text:
        if _WESTERN.match(text) or _INDIAN.match(text):
            decimal = ""  # 1,234 and 1,24,500 are grouped integers
        elif text.count(",") == 1:
            decimal = ","  # 12,5 -> decimal comma
        else:
            return None
    elif "." in text:
        if _DOT_GROUPS.match(text):
            decimal = ""  # 1.234.567 is a European grouped integer
        elif text.count(".") == 1:
            decimal = "."
        else:
            return None
    elif " " in text or " " in text or " " in text or "'" in text:
        if not _SPACE_GROUPS.match(text):
            return None
    if decimal:
        whole, _, fraction = text.rpartition(decimal)
        if not re.fullmatch(r"\d*", fraction):
            return None
        digits = re.sub(r"\D", "", whole)
        if not digits and not fraction:
            return None
        return float(f"{digits or '0'}.{fraction or '0'}"), len(fraction)
    digits = re.sub(r"\D", "", text)
    return float(digits), 0


def parse_number(text: object) -> Optional[ParsedNumber]:
    """The number a cell shows, or None if it is a label, a blank marker, or not clearly a number."""
    if isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return ParsedNumber(float(text), _decimals_of(float(text)))
    if not isinstance(text, str):
        return None
    shown = text.strip().replace("−", "-")
    if shown.lower() in _BLANKS:
        return None

    negative = False
    if shown.startswith("(") and shown.endswith(")"):
        negative, shown = True, shown[1:-1].strip()
    if shown.endswith("-") and not shown.startswith("-"):
        negative, shown = True, shown[:-1].strip()
    if shown.startswith("-"):
        negative, shown = True, shown[1:].strip()
    elif shown.startswith("+"):
        shown = shown[1:].strip()

    unit: Unit = "number"
    if _CURRENCY.search(shown):
        unit = "currency"
        shown = _CURRENCY.sub("", shown).strip()
    # a sign can also sit between the symbol and the digits: "$-1,200"
    if shown.startswith("-"):
        negative, shown = True, shown[1:].strip()
    elif shown.startswith("(") and shown.endswith(")"):
        negative, shown = True, shown[1:-1].strip()

    scale = 1.0
    if shown.endswith("%"):
        unit, scale, shown = "percent", 0.01, shown[:-1].strip()
    else:
        suffix = re.search(r"\s*([A-Za-z]+)\.?$", shown)
        if suffix and suffix.group(1).lower() in _SUFFIXES:
            scale = _SUFFIXES[suffix.group(1).lower()]
            shown = shown[: suffix.start()].strip()
    if not shown or not shown[0].isdigit() and shown[0] not in ".,":
        return None

    parsed = _mantissa(shown)
    if parsed is None:
        return None
    mantissa, decimals = parsed
    value = mantissa * scale
    return ParsedNumber(-value if negative else value, decimals, unit, scale)


def _decimals_of(value: float) -> int:
    """Decimals needed to write ``value`` exactly (capped), for cells with no number format."""
    if value == int(value) and abs(value) < 1e15:
        return 0
    text = repr(value)
    if "e" in text:
        return 10
    return min(len(text.split(".")[1]), 10)


# --- Excel number formats -----------------------------------------------------------------


@dataclass(frozen=True)
class FormatInfo:
    decimals: int
    unit: Unit
    scale: float
    grouped: bool = field(default=False, compare=False)  # thousands separators shown (only affects drawing)


_QUOTED = re.compile(r'"[^"]*"|\\.')
_BRACKETS = re.compile(r"\[[^\]]*\]")


def interpret_format(number_format: str, value: float) -> FormatInfo:
    """How Excel shows ``value`` under ``number_format``: decimals, % / currency, thousands scaling."""
    if not number_format or number_format.lower() == "general":
        return FormatInfo(_decimals_of(value), "number", 1.0)

    sections = _split_sections(number_format)
    section = sections[1] if value < 0 and len(sections) > 1 else sections[0]
    unit: Unit = "number"
    if re.search(r"\[\$[^\]]*\]|[$€£¥₹]", section):
        unit = "currency"
    cleaned = _BRACKETS.sub("", _QUOTED.sub("", section))
    scale = 1.0
    if "%" in cleaned:
        unit, scale = "percent", 0.01 ** cleaned.count("%")
    if cleaned.lower() == "general":
        return FormatInfo(_decimals_of(value), unit, scale)

    digits = re.sub(r"[^0#?.,]", "", cleaned)
    if "." in digits:
        decimals = len(re.sub(r"[^0#?]", "", digits.split(".", 1)[1]))
        trailing = len(digits.split(".", 1)[1]) - len(digits.split(".", 1)[1].rstrip(","))
    else:
        decimals = 0
        trailing = len(digits) - len(digits.rstrip(","))
    scale *= 1000.0**trailing
    return FormatInfo(decimals, unit, scale, grouped=bool(re.search(r"#,#|0,0", digits)))


def _split_sections(number_format: str) -> list[str]:
    sections, current, quoted = [], [], False
    for char in number_format:
        if char == '"':
            quoted = not quoted
        if char == ";" and not quoted:
            sections.append("".join(current))
            current = []
        else:
            current.append(char)
    sections.append("".join(current))
    return sections


def is_date_format(number_format: str) -> bool:
    """True for formats that show a date or time (so the cell is a label, not a measure)."""
    cleaned = _BRACKETS.sub("", _QUOTED.sub("", number_format or "")).lower()
    return bool(re.search(r"[ydhms]", cleaned)) and not re.search(r"[0#?]", cleaned)


def show(value: float, info: FormatInfo) -> str:
    """The text Excel would show for ``value`` (for the report grid; matching never depends on it)."""
    shown = value / info.scale
    text = f"{abs(shown):{',' if info.grouped else ''}.{info.decimals}f}"
    if info.unit == "percent":
        text += "%"
    elif info.unit == "currency":
        text = "$" + text
    if info.scale in (1e3, 1e6, 1e9) and info.unit != "percent":
        text += {1e3: "K", 1e6: "M", 1e9: "B"}[info.scale]
    return ("-" if shown < 0 else "") + text
