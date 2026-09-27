"""Numeric claim verification for generated answers.

Telling a model "do not invent figures" is a request, not a guarantee. This
module checks the request was honoured: every number in a generated answer must
trace back to a number in the grounding facts or in the question itself.

That turns "grounded" from a prompt instruction into something the server
actually enforces -- an answer containing an unsupported figure is caught before
a user reads it and treats it as analysis.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# Matches 1,234.56 / 91.7% / $1,200 / -5.2 / .75, with optional currency and
# percent decoration. Grouped so the numeric core can be normalized separately.
_NUMBER_PATTERN = re.compile(
    r"""
    (?<![\w.])                 # not mid-identifier (skips col_2, v1.2)
    [-+]?                      # sign
    [$£€]?                     # currency
    (?:
        \d{1,3}(?:,\d{3})+     # grouped thousands
        |
        \d+                    # plain integer part
        |
        (?=\.\d)               # or a bare .5
    )
    (?:\.\d+)?                 # decimals
    %?                         # percent
    (?![\w])                   # not mid-identifier
    """,
    re.VERBOSE,
)

# Numbers a reader would never mistake for analysis. Ordinals and list positions
# ("the 3 steps below", "first of 2") would otherwise produce constant false
# positives without carrying any factual claim.
_TRIVIAL_VALUES = frozenset(float(n) for n in range(0, 11))

# Relative tolerance for matching a stated figure to a fact. Covers a model
# writing 91.7 for a stored 91.66, or 1.2M for 1,234,567.
_RELATIVE_TOLERANCE = 0.01


@dataclass(slots=True, frozen=True)
class VerificationResult:
    """Outcome of checking an answer's numbers against its grounding facts."""

    grounded: bool
    unsupported_values: tuple[str, ...] = field(default_factory=tuple)
    checked_count: int = 0

    @property
    def summary(self) -> str:
        if self.grounded:
            return f"All {self.checked_count} numeric claim(s) trace to the analysis."
        return (
            f"{len(self.unsupported_values)} of {self.checked_count} numeric claim(s) "
            f"could not be traced to the analysis: {', '.join(self.unsupported_values)}"
        )


def _normalize(token: str) -> float | None:
    """Turn a matched token into a comparable float, or None if it is not one."""
    cleaned = token.strip().rstrip("%").lstrip("$£€").replace(",", "")
    if cleaned in ("", "-", "+", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_numbers(text: str) -> list[tuple[str, float]]:
    """Every numeric token in ``text``, as (original token, numeric value)."""
    found: list[tuple[str, float]] = []
    for match in _NUMBER_PATTERN.finditer(text):
        token = match.group(0)
        value = _normalize(token)
        if value is not None:
            found.append((token, value))
    return found


def _matches_any(value: float, allowed: list[float]) -> bool:
    for candidate in allowed:
        if math.isclose(value, candidate, rel_tol=_RELATIVE_TOLERANCE, abs_tol=1e-9):
            return True
        # A model often rounds a stored 91.66 to 91.7, or reports 1.2 for 1.23
        # million. Compare at the precision the answer was written to.
        if value != 0 and candidate != 0:
            decimals = len(str(value).split(".")[-1]) if "." in str(value) else 0
            if decimals and round(candidate, decimals) == value:
                return True
    return False


def verify_numeric_claims(answer: str, *grounding_texts: str) -> VerificationResult:
    """Check that every non-trivial number in ``answer`` appears in the grounding.

    ``grounding_texts`` should include the serialized facts given to the model and
    the user's own question -- a number the user supplied is fair to repeat back.
    """
    allowed = [value for text in grounding_texts for _token, value in extract_numbers(text)]

    unsupported: list[str] = []
    checked = 0

    for token, value in extract_numbers(answer):
        if value in _TRIVIAL_VALUES and float(value).is_integer():
            continue
        checked += 1
        if not _matches_any(value, allowed):
            unsupported.append(token)

    # Preserve order while removing duplicates, so a repeated figure is reported once.
    seen: set[str] = set()
    deduped = [t for t in unsupported if not (t in seen or seen.add(t))]

    return VerificationResult(
        grounded=not deduped,
        unsupported_values=tuple(deduped),
        checked_count=checked,
    )
