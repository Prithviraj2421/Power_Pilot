"""Numeric claim verification for generated answers.

Telling a model "do not invent figures" is a request, not a guarantee. This module checks the
request was honoured, at two levels:

``verify_citations`` (what the copilot uses). Every number in an answer must be followed by the id
of a fact in the fact sheet, and must match *that fact* at the precision it was written, in a unit
that fact can have, in a sentence that is about what the fact means. So "Revenue is 9,994 [F1]"
fails when F1 is the row count (the sentence says revenue, the fact says rows), and "$9,994 [F1]"
fails on unit alone. An answer that passes comes back with its [F12] tags stripped and a list of
citations (span, fact id, label, value) so the page can show where each figure came from.

``verify_numeric_claims`` (the older, weaker check). Every number only has to appear *somewhere*
in the grounding text. Kept for callers that have no fact ids.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Mapping, Optional

from app.intelligence.llm.facts import TAG, Fact, Mention, find_numbers, is_trivial, strip_citations

# --- the older check: a number only has to exist somewhere ---------------------------------------------

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


# --- the citation check ------------------------------------------------------------------------------

MISSING, UNKNOWN_FACT, WRONG_VALUE, WRONG_UNIT, WRONG_MEANING = (
    "missing_citation", "unknown_fact", "value_mismatch", "unit_mismatch", "meaning_mismatch",
)
_SENTENCE_END = re.compile(r"[.!?;\n](?=\s|$)")
_WORDS_BEFORE, _WORDS_AFTER = 8, 4
_STOP = frozenset(
    "the and are was were with from that this has have had for which over across about around per into than then its their "
    "there here but not you your our can will would should could may might also more most less very just only each every "
    "all any some such these those when what where who how why been being does did done out off".split()
)


@dataclass(frozen=True)
class Citation:
    """One cited figure: where it is in the displayed text, and the fact behind it."""

    start: int  # offsets into ``CitationResult.clean_text``
    end: int
    text: str
    fact_id: str
    label: str
    value: float
    unit: str

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "text": self.text, "fact_id": self.fact_id,
                "label": self.label, "value": self.value, "unit": self.unit}


@dataclass(frozen=True)
class Problem:
    token: str
    kind: str
    detail: str


@dataclass(frozen=True)
class CitationResult:
    grounded: bool
    problems: tuple[Problem, ...] = ()
    citations: tuple[Citation, ...] = ()
    clean_text: str = ""
    checked_count: int = 0

    @property
    def unsupported_values(self) -> tuple[str, ...]:
        seen: list[str] = []
        for p in self.problems:
            if p.token not in seen:
                seen.append(p.token)
        return tuple(seen)

    @property
    def summary(self) -> str:
        if self.grounded:
            return f"All {self.checked_count} numeric claim(s) cite a fact with the same value, unit and meaning."
        return (
            f"{len(self.problems)} of {self.checked_count} numeric claim(s) failed citation checks: "
            + "; ".join(f"{p.token} ({p.detail})" for p in self.problems)
        )


def _stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    return word[:-1] if word.endswith("s") and not word.endswith("ss") and len(word) > 3 else word


def _words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP]


def _label_words(fact: Fact) -> set[str]:
    return set(_words(f"{fact.label} {fact.key.replace('.', ' ').replace('_', ' ')}"))


def _in_mention_units(fact: Fact, mention: Mention) -> float:
    """The fact's value expressed the way the answer wrote it (a ratio of 0.917 is 91.7 when written as a percent)."""
    return fact.value * 100 if fact.unit == "ratio" and mention.unit == "percent" else fact.value


def _value_matches(fact: Fact, mention: Mention) -> bool:
    return abs(_in_mention_units(fact, mention) - mention.value) <= mention.tolerance + 1e-9 * max(1.0, abs(mention.value))


def _unit_ok(fact: Fact, mention: Mention) -> bool:
    if mention.unit == "percent":
        return fact.unit in ("percent", "ratio")
    if mention.unit == "currency":
        return fact.unit in ("currency", "number")
    return True


def _clause_words(clean: str, start: int, end: int) -> list[str]:
    """The words around a number in its own sentence: a few before and a few after."""
    boundaries = [m.end() for m in _SENTENCE_END.finditer(clean) if m.end() <= start]
    sentence_start = boundaries[-1] if boundaries else 0
    after = next((m.start() for m in _SENTENCE_END.finditer(clean) if m.start() >= end), len(clean))
    before_words = _words(clean[sentence_start:start])[-_WORDS_BEFORE:]
    after_words = _words(clean[end:after])[:_WORDS_AFTER]
    return before_words + after_words


def verify_citations(answer: str, facts: Mapping[str, Fact], question: str = "") -> CitationResult:
    """Check every number in ``answer`` against the fact it cites. See the module docstring."""
    tags = list(TAG.finditer(answer))
    removed: list[tuple[int, int]] = []  # spans dropped from the displayed text: a tag and the space before it
    for tag in tags:
        start = tag.start() - 1 if tag.start() > 0 and answer[tag.start() - 1] in " \t" else tag.start()
        removed.append((start, tag.end()))
    clean = strip_citations(answer)

    def shift(index: int) -> int:
        return index - sum(e - s for s, e in removed if e <= index)

    asked = find_numbers(question)
    vocabulary = {w for fact in facts.values() for w in _label_words(fact)}
    problems: list[Problem] = []
    citations: list[Citation] = []
    checked = 0

    for mention in find_numbers(answer):
        if is_trivial(mention):
            continue
        if any(abs(a.value - mention.value) <= max(a.tolerance, 1e-9) for a in asked if a.unit == mention.unit):
            continue  # the user's own number, repeated back
        checked += 1
        tag = next((t for t in tags if 0 <= t.start() - mention.end <= 2 and not answer[mention.end : t.start()].strip()), None)
        if tag is None:
            problems.append(Problem(mention.token, MISSING, "no fact id follows the number"))
            continue
        ids = [i.strip() for i in tag.group(1).split(",")]
        unknown = [i for i in ids if i not in facts]
        if unknown:
            problems.append(Problem(mention.token, UNKNOWN_FACT, f"{', '.join(unknown)} is not a fact in the analysis"))
            continue
        cited = [facts[i] for i in ids]
        matching = [f for f in cited if _value_matches(f, mention)]
        if not matching:
            nearest = ", ".join(f"{f.id}={f.value:g}" for f in cited)
            problems.append(Problem(mention.token, WRONG_VALUE, f"does not match the cited fact ({nearest})"))
            continue
        compatible = [f for f in matching if _unit_ok(f, mention)]
        if not compatible:
            fact = matching[0]
            problems.append(Problem(mention.token, WRONG_UNIT, f"written as {mention.unit} but {fact.id} is a {fact.unit}"))
            continue
        start, end = shift(mention.start), shift(mention.end)
        window = set(_clause_words(clean, start, end))
        fact = next((f for f in compatible if window & _label_words(f)), None)
        if fact is None and window & vocabulary:
            fact = compatible[0]
            problems.append(Problem(mention.token, WRONG_MEANING, f"the sentence is about something other than {fact.label!r}"))
            continue
        fact = fact or compatible[0]
        citations.append(Citation(start, end, clean[start:end], fact.id, fact.label, fact.value, fact.unit))

    return CitationResult(not problems, tuple(problems), tuple(citations), clean, checked)
