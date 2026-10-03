"""Reverse-engineer a whole report: prove what can be proven, flag the rest, explain the differences.

"The model proposes, the executor proves": the search and any optional language-model suggestions
only produce candidate formulas. A cell is REPRODUCED only when ``verify()`` (the same compilers
that write the Power BI measures) recomputes the formula on the data and lands on the number the
report shows. Everything else is labelled honestly: AMBIGUOUS (several formulas fit),
NOT_REPRODUCIBLE (none do, with a hint where the rule used by its neighbours gives a different
number) or DERIVED (the report computed it from its own other numbers).
"""

from __future__ import annotations

import math
import time
from typing import Optional

import pandas as pd

from app.intelligence.kpi.ir import Expr, Measure, Op
from app.intelligence.kpi.verification import verify
from app.reverse import consistency
from app.reverse.consistency import Resolution
from app.reverse.describe import describe, shape_of
from app.reverse.diagnostics import diagnose, show_value
from app.reverse.index import DataIndex
from app.reverse.models import (
    AMBIGUOUS,
    DERIVED,
    NOT_REPRODUCIBLE,
    REPRODUCED,
    Alternative,
    CellResult,
    Closest,
    DerivedCheck,
    ParsedReport,
    ReverseReport,
    ReverseSummary,
    TargetCell,
)
from app.reverse.proposer import Proposer
from app.reverse.synthesizer import Candidate, CellSearch, Synthesizer, significant_digits, tolerance_for

DEFAULT_TIME_BUDGET = 90.0  # seconds for a whole report
PROPOSER_LIMIT = 25  # cells we will ask a language model about, per report


class ReverseEngine:
    def __init__(
        self,
        raw: pd.DataFrame,
        table: str,
        *,
        cleaned: Optional[pd.DataFrame] = None,
        proposer: Optional[Proposer] = None,
        time_budget: float = DEFAULT_TIME_BUDGET,
        max_filter_sets: int = 300,
        basis_label: str = "raw table",
    ) -> None:
        self.raw = raw
        self.cleaned = cleaned
        self.table = table
        self.proposer = proposer
        self.time_budget = time_budget
        self.max_filter_sets = max_filter_sets
        self.basis_label = basis_label

    # --- the whole report -----------------------------------------------------------

    def run(self, parsed: ParsedReport, filename: str, report_id: str) -> ReverseReport:
        started = time.monotonic()
        deadline = started + self.time_budget
        by_id = {t.id: t for t in parsed.targets}
        results: dict[str, CellResult] = {}
        pending: list[TargetCell] = []  # numbers that have to come from the data
        derived: list[TargetCell] = []

        for target in parsed.targets:
            if target.derived is None:
                pending.append(target)
                continue
            check = self._check_derived(target, by_id)
            if check.consistent or target.derived.kind == "formula":
                results[target.id] = self._derived_result(target, check)
                derived.append(target)
            else:
                # a typed "Total" that is not the sum of its parts: let the data try to explain it
                pending.append(target)
                results[target.id] = CellResult(target, NOT_REPRODUCIBLE, notes=[check.explanation])

        index = DataIndex(self.raw)
        synth = Synthesizer(index, max_filter_sets=self.max_filter_sets)
        searches = {t.id: synth.search(t, deadline) for t in pending}
        resolutions = consistency.resolve(list(searches.values()))
        groups = consistency.groups(list(searches.values()))
        exhausted = any(s.exhausted for s in searches.values())

        for ident, resolution in resolutions.items():
            result = self._prove(resolution, self.raw, "raw")
            result.notes = [*results[ident].notes, *result.notes] if ident in results else result.notes
            results[ident] = result

        if self.cleaned is not None and not self.cleaned.equals(self.raw):
            self._try_cleaned(pending, results, deadline)

        for target in pending:
            if results[target.id].status == NOT_REPRODUCIBLE:
                self._explain_miss(results[target.id], searches[target.id], synth, index, searches, resolutions, groups)
        self._ask_proposer(results)
        for target in derived:
            self._data_check(results[target.id], synth, index, searches, resolutions, groups)
        for ident, search in searches.items():
            if search.exhausted and results[ident].status != REPRODUCED:
                results[ident].notes.append("The time budget ran out before every formula could be tried for this number.")

        ordered = [results[t.id] for t in parsed.targets]
        summary = self._summarise(ordered, time.monotonic() - started, exhausted)
        return ReverseReport(
            report_id=report_id,
            filename=filename,
            table=self.table,
            results=ordered,
            layout=parsed.layout,
            warnings=parsed.warnings,
            summary=summary,
            rows_analysed=len(self.raw),
        )

    # --- derived cells --------------------------------------------------------------

    @staticmethod
    def _check_derived(target: TargetCell, by_id: dict[str, TargetCell]) -> DerivedCheck:
        info = target.derived
        if info.op is None:
            return DerivedCheck(True, None, f"A spreadsheet formula ({info.formula}) over other cells of this report; it was not recomputed.")
        sources = [by_id[s] for s in info.sources if s in by_id]
        if len(sources) != len(info.sources) or not sources:
            return DerivedCheck(True, None, "Computed from cells outside the numbers read here; it was not recomputed.")
        values = [s.value for s in sources]
        expected = {
            "sum": sum(values),
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }[info.op]
        slack = target.tolerance + sum(s.tolerance for s in sources) / (len(sources) if info.op == "average" else 1)
        consistent = abs(target.value - expected) <= slack + 1e-9 * max(1.0, abs(expected))
        n = len(sources)
        verb = {"sum": "Adding up", "average": "Averaging", "min": "Taking the smallest of", "max": "Taking the largest of"}[info.op]
        text = f"{verb} the {n} number{'s' if n != 1 else ''} it totals gives {show_value(expected, target)}"
        if consistent:
            return DerivedCheck(True, expected, f"{text}, which matches.")
        return DerivedCheck(
            False,
            expected,
            f"{text}, but this cell shows {show_value(target.value, target)}: it is not what its own parts give.",
        )

    @staticmethod
    def _derived_result(target: TargetCell, check: DerivedCheck) -> CellResult:
        info = target.derived
        names = {"sum": "Sum", "average": "Average", "min": "Smallest", "max": "Largest"}
        formula = (
            f"{names[info.op]} of the {len(info.sources)} number{'s' if len(info.sources) != 1 else ''} it totals"
            if info.op
            else f"Spreadsheet formula {info.formula}"
        )
        result = CellResult(target, DERIVED, formula=formula, recomputed=check.expected, derived_check=check)
        result.reasons.append("The report computed this number from its own other numbers, so there is no data formula to find.")
        result.notes.append(check.explanation)
        if not check.consistent:
            result.hint = check.explanation
        return result

    def _data_check(self, result: CellResult, synth, index: DataIndex, searches, resolutions, groups) -> None:
        """A total that adds up can still disagree with the data (a number it sums is wrong, or a row is missing)."""
        target = result.target
        own = {**searches, target.id: CellSearch(target, synth.reader.hints_for(target))}
        expectation = consistency.expectation_for(target.id, synth, self.raw, own, resolutions, groups)
        if expectation is None or expectation.value is None or not math.isfinite(expectation.value):
            return
        check = result.derived_check
        check.data_value = expectation.value
        check.matches_data = abs(target.value - expectation.value) <= tolerance_for(target)
        if check.matches_data:
            result.notes.append("It also matches what the data gives for the same rule, so the total is right.")
        else:
            result.hint = diagnose(target, expectation.value, expectation.expr, index)
            result.notes.append(f"It adds up from the numbers shown, but it does not match the data: {result.hint}")

    # --- proving --------------------------------------------------------------------

    def _prove(self, resolution: Resolution, df: pd.DataFrame, basis: str) -> CellResult:
        target = resolution.search.target
        result = CellResult(target, NOT_REPRODUCIBLE, basis=None)
        contenders = [c for c in [resolution.chosen, *resolution.alternatives] if c is not None]
        proven: list[tuple[Candidate, float, str]] = []
        rejected: list[str] = []
        tol = tolerance_for(target)
        for candidate in contenders:
            outcome = verify(candidate.expr, df, self.table, basis=self.basis_label if basis == "raw" else "cleaned dataset")
            if not outcome.verified:
                rejected.append(f"'{describe(candidate.expr)}' was rejected: {outcome.note}")
                continue
            if abs(outcome.value - target.value) > tol:
                rejected.append(f"'{describe(candidate.expr)}' did not reproduce the number when recomputed ({outcome.value:g})")
                continue
            proven.append((candidate, outcome.value, outcome.dax))
        result.notes.extend(rejected)
        if not proven:
            return result

        # The first proven candidate is the chosen one if it is still among them; else the best that survived.
        chosen_candidate, value, dax = proven[0]
        still_ambiguous = resolution.ambiguous and len(proven) > 1
        result.status = AMBIGUOUS if still_ambiguous else REPRODUCED
        result.basis = basis
        result.expr = chosen_candidate.expr
        result.formula = describe(chosen_candidate.expr)
        result.dax = dax
        result.recomputed = value
        result.exact = abs(value - target.value) <= 1e-6 * max(1.0, abs(target.value))
        result.shape = chosen_candidate.shape
        result.reasons.extend(resolution.reasons)
        result.reasons.extend(chosen_candidate.reasons)
        others = proven[1:] if still_ambiguous else [p for p in proven[1:] if p[0] in resolution.alternatives]
        result.alternatives = [Alternative(describe(c.expr), d, v, c.expr) for c, v, d in others]
        if still_ambiguous:
            result.reasons.append(
                f"{len(proven)} different formulas give this number and nothing in the report or its neighbours separates them"
            )
        else:
            result.evidence = self._evidence(resolution, chosen_candidate, len(resolution.search.candidates))
            result.reasons.insert(0, self._basis_reason(target, chosen_candidate, len(resolution.search.candidates)))
        if basis == "cleaned":
            result.notes.append(
                "This only matches the cleaned data, not the raw table. The old report probably used cleaned figures; it cannot be added to Power BI as is."
            )
        return result

    @staticmethod
    def _basis_reason(target: TargetCell, candidate: Candidate, total: int) -> str:
        digits = significant_digits(target)
        used = f"using the filters {', '.join(candidate.used)}" if candidate.used else "without filters"
        return f"{total} formula(s) fit the {digits}-digit number; this one, {used}, matches what the report shows"

    @staticmethod
    def _evidence(resolution: Resolution, candidate: Candidate, total: int) -> str:
        target = resolution.search.target
        digits = significant_digits(target)
        points = 3 if digits >= 5 else 2 if digits >= 3 else 0
        measure = _first(candidate.expr)
        if measure is not None and measure.column and resolution.search.hints.column_affinity(measure.column) > 0:
            points += 1
        if resolution.support >= 2:
            points += 1
        if total == 1:
            points += 1
        return "strong" if points >= 4 else "moderate" if points >= 2 else "weak"

    @staticmethod
    def _carry_notes(previous: Optional[CellResult], current: CellResult) -> None:
        if previous is not None:
            current.notes = [*previous.notes, *current.notes]

    def _try_cleaned(self, pending: list[TargetCell], results: dict[str, CellResult], deadline: float) -> None:
        unmatched = [t for t in pending if results[t.id].status == NOT_REPRODUCIBLE]
        if not unmatched:
            return
        index = DataIndex(self.cleaned)
        synth = Synthesizer(index, max_filter_sets=self.max_filter_sets)
        searches = [synth.search(t, deadline) for t in unmatched]
        resolutions = consistency.resolve(searches)
        for ident, resolution in resolutions.items():
            if resolution.chosen is None:
                continue
            attempt = self._prove(resolution, self.cleaned, "cleaned")
            if attempt.status in (REPRODUCED, AMBIGUOUS):
                attempt.notes = [*results[ident].notes, *attempt.notes]
                results[ident] = attempt

    # --- what the miss looks like ---------------------------------------------------

    def _explain_miss(self, result: CellResult, search: CellSearch, synth: Synthesizer, index: DataIndex, searches, resolutions, groups) -> None:
        target = result.target
        expectation = consistency.expectation_for(target.id, synth, self.raw, searches, resolutions, groups)
        if expectation is not None and expectation.value is not None and math.isfinite(expectation.value):
            difference = target.value - expectation.value
            result.closest = Closest(
                expectation.value,
                describe(expectation.expr),
                difference,
                difference / expectation.value if expectation.value else None,
                expectation.expr,
            )
            result.hint = diagnose(target, expectation.value, expectation.expr, index)
            result.reasons.append(
                f"No formula reproduces this number. The formula used by {expectation.source} is shown as the closest."
            )
            return
        guess = self._label_guess(search, index)
        if guess is not None:
            expr, value = guess
            difference = target.value - value
            result.closest = Closest(value, describe(expr), difference, difference / value if value else None, expr)
            result.hint = diagnose(target, value, expr, index)
            result.reasons.append(
                "No formula reproduces this number. The closest reading of its labels is shown, but nothing else in the report follows the same rule."
            )
        else:
            result.reasons.append("No formula built from its labels and the data's columns reproduces this number.")

    @staticmethod
    def _label_guess(search: CellSearch, index: DataIndex) -> Optional[tuple[Expr, float]]:
        hints = search.hints
        filters = []
        for slot in hints.slots:
            best = max(slot.options, key=lambda o: o.affinity)
            filters.extend(f for f in best.filters if f not in filters)
        from app.reverse.describe import canonical_filters

        scope = canonical_filters(tuple(filters))
        values = index.values(scope)
        best_at, best_key = None, (0.0, 0)
        for i, measure in enumerate(index.base_measures):
            if not measure.column or math.isnan(values[i]):
                continue
            key = (hints.column_affinity(measure.column), 1 if measure.op in hints.ops else 0)
            if key[0] > 0 and key > best_key:
                best_at, best_key = i, key
        if best_at is None:
            return None
        measure = index.base_measures[best_at]
        return Measure(measure.op, measure.column, scope), float(values[best_at])

    # --- the optional language model ------------------------------------------------

    def _ask_proposer(self, results: dict[str, CellResult]) -> None:
        if self.proposer is None:
            return
        asked = 0
        for ident, result in results.items():
            if result.status != NOT_REPRODUCIBLE:
                continue
            if asked >= PROPOSER_LIMIT:
                break
            asked += 1
            try:
                proposals = self.proposer.propose(self.table, self.raw, result.target)
            except Exception as exc:  # a model that fails must never break the report
                result.notes.append(f"The language-model suggestion step failed: {exc}")
                continue
            tol = tolerance_for(result.target)
            for expr in proposals:
                outcome = verify(expr, self.raw, self.table, basis=self.basis_label)
                if outcome.verified and abs(outcome.value - result.target.value) <= tol:
                    result.status = REPRODUCED
                    result.basis = "raw"
                    result.expr = expr
                    result.formula = describe(expr)
                    result.dax = outcome.dax
                    result.recomputed = outcome.value
                    result.exact = abs(outcome.value - result.target.value) <= 1e-6 * max(1.0, abs(result.target.value))
                    result.shape = shape_of(expr)
                    result.proposed_by = "language model"
                    result.evidence = "weak"
                    result.reasons.insert(0, "A language model suggested this formula; PowerPilot recomputed it on the data and it matches.")
                    result.closest = None
                    result.hint = None
                    break

    # --- summary --------------------------------------------------------------------

    @staticmethod
    def _summarise(results: list[CellResult], seconds: float, exhausted: bool) -> ReverseSummary:
        count = lambda status: sum(1 for r in results if r.status == status)  # noqa: E731
        reproduced, ambiguous, missed, derived = count(REPRODUCED), count(AMBIGUOUS), count(NOT_REPRODUCIBLE), count(DERIVED)
        from_data = reproduced + ambiguous + missed
        suspected = sum(1 for r in results if r.status == NOT_REPRODUCIBLE and r.closest is not None) + sum(
            1
            for r in results
            if r.status == DERIVED
            and r.derived_check is not None
            and (not r.derived_check.consistent or r.derived_check.matches_data is False)
        )
        return ReverseSummary(
            cells=len(results),
            reproduced=reproduced,
            ambiguous=ambiguous,
            not_reproducible=missed,
            derived=derived,
            percent_reproduced=round(100.0 * reproduced / from_data, 1) if from_data else 0.0,
            suspected_errors=suspected,
            seconds=round(seconds, 2),
            budget_exhausted=exhausted,
        )


def _first(expr: Expr) -> Optional[Measure]:
    from app.reverse.describe import first_measure

    return first_measure(expr)
