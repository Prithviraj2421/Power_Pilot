"""The systems under test: the full pipeline, and the same pipeline with one verifier removed at a time.

Ablations are applied by patching the one function that does the checking (never by editing the product), inside a
context manager, so they cannot leak between runs.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional
from unittest import mock

import pandas as pd

from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.verification import Verification
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

# variant name -> what it removes
VARIANTS = {
    "full": "Everything on.",
    "no_kpi_verifier": "KPI verification gate removed: every candidate KPI is emitted as if verified.",
    "no_copilot_verifier": "The copilot's numeric-claim verifier removed: an LLM answer is shown as written.",
    "no_reverse_consistency": "Reverse-engineering without the neighbour-consistency pass.",
    "no_reverse_gate": "Reverse-engineering that trusts the search value instead of recomputing with verify().",
    "raw_llm": "Baseline: the model sees the CSV head and the question, no pipeline.",
}


def _permissive_verify(expr, df: pd.DataFrame, table: str, basis: str = "") -> Verification:
    """What `verify` would be without its checks: compile, try to compute, and call it verified regardless."""
    try:
        dax = DaxCompiler(table).compile(expr)
    except Exception:
        dax = None
    try:
        value = PandasCompiler().evaluate(expr, df)
    except Exception:
        value = None
    return Verification(True, "verification disabled (ablation)", value=value, dax=dax)


@contextmanager
def ablation(variant: str) -> Iterator[None]:
    patches: list[Any] = []
    if variant == "no_kpi_verifier":
        patches.append(mock.patch("app.intelligence.kpi_engine.verify", _permissive_verify))
    elif variant == "no_copilot_verifier":
        from app.intelligence.llm.facts import strip_citations
        from app.intelligence.llm.verifier import CitationResult

        def accept_everything(answer: str, *_args: Any, **_kwargs: Any) -> CitationResult:
            return CitationResult(grounded=True, clean_text=strip_citations(answer))

        patches.append(mock.patch("app.intelligence.llm.llm_copilot.verify_citations", accept_everything))
    elif variant == "no_reverse_consistency":
        patches.append(mock.patch("app.reverse.consistency.resolve", _resolve_without_neighbours))
    elif variant == "no_reverse_gate":
        patches.append(mock.patch("app.reverse.engine.verify", _trusting_verify))
    for patch in patches:
        patch.start()
    try:
        yield
    finally:
        for patch in reversed(patches):
            patch.stop()


def _resolve_without_neighbours(searches):  # noqa: ANN001
    from app.reverse import consistency

    return {s.target.id: consistency.initial(s) for s in searches}


def _trusting_verify(expr, df, table, basis=""):  # noqa: ANN001
    """The search's own number, with no independent recomputation or dtype/DAX checks."""
    try:
        dax = DaxCompiler(table).compile(expr)
        value = PandasCompiler().evaluate(expr, df)
    except Exception:
        return Verification(False, "could not be computed")
    return Verification(value is not None, "unchecked (ablation)", value=value, dax=dax)


@dataclass
class PipelineRun:
    result: Optional[Any]
    cleaned: Optional[pd.DataFrame]
    seconds: float
    error: Optional[str] = None


def run_pipeline(df: pd.DataFrame, name: str, variant: str = "full") -> PipelineRun:
    started = time.perf_counter()
    try:
        with ablation(variant):
            execution = PowerPilotIntelligencePipeline().execute(df.copy(), dataset_name=name)
        return PipelineRun(execution.result, execution.cleaned_dataframe, time.perf_counter() - started)
    except Exception as exc:  # a crash is a result, not a reason to stop the benchmark
        return PipelineRun(None, None, time.perf_counter() - started, f"{type(exc).__name__}: {exc}")
