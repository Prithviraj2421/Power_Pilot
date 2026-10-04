"""Run the benchmark and write one CSV per metric plus a summary table.

    python -m eval.run                                  # every dataset, every deterministic system
    python -m eval.run --datasets golden_superstore uci_hcv --variants full
    python -m eval.run --llm-mode record                # also call the model (needs ANTHROPIC_API_KEY) and cache replies
    python -m eval.run --llm-mode off                   # never touch a model, not even the cache

Model-backed systems (the raw-LLM baseline, the LLM copilot with and without its verifier) run from the response cache
eval/cache/llm.jsonl. A request that is not cached is **not run** and reported as such: it is never filled in.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from typing import Any, Callable, Optional

import pandas as pd

from app.core.config import Settings
from app.intelligence.llm.llm_copilot import LlmCopilotService
from eval import raw_llm
from eval.common import RESULTS, Dataset, dataset_ids, load, mean
from eval.llm import CacheMiss, CachedLLM, ModelUnavailable
from eval.metrics import copilot as copilot_metric
from eval.metrics import insights as insight_metric
from eval.metrics import kpi as kpi_metric
from eval.metrics import reverse as reverse_metric
from eval.metrics import semantic as semantic_metric
from eval.reports.generate import reports_for
from eval.systems import VARIANTS, ablation, run_pipeline

PIPELINE_VARIANTS = ("full", "no_kpi_verifier")
REVERSE_VARIANTS = ("full", "no_reverse_consistency", "no_reverse_gate")
COPILOT_SYSTEMS = ("powerpilot_rules", "powerpilot_llm", "powerpilot_llm_no_verifier", "raw_llm")
NOT_RUN = "not_run"


class Tables:
    """Rows collected per metric, written as one CSV each."""

    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}

    def add(self, metric: str, **row: Any) -> None:
        self.rows.setdefault(metric, []).append(row)

    def frame(self, metric: str) -> pd.DataFrame:
        return pd.DataFrame(self.rows.get(metric, []))

    def write(self, out) -> None:
        out.mkdir(parents=True, exist_ok=True)
        for metric, rows in self.rows.items():
            pd.DataFrame(rows).to_csv(out / f"{metric}.csv", index=False)


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


# --- one dataset ------------------------------------------------------------------------------------


def run_dataset(ds: Dataset, variants: set[str], llm: CachedLLM, tables: Tables) -> None:
    runs = {}
    for variant in PIPELINE_VARIANTS:
        needed = variant == "full" or variant in variants
        if needed:
            runs[variant] = run_pipeline(ds.frame, ds.name, variant)
            tables.add("timing", dataset=ds.id, system=f"pipeline:{variant}", rows=len(ds.frame), columns=len(ds.frame.columns),
                       seconds=round(runs[variant].seconds, 3), error=runs[variant].error or "")
    full = runs["full"]
    if full.error:
        log(f"  pipeline failed on {ds.id}: {full.error}")
        return

    # semantic types, domain, calibration
    cols = semantic_metric.column_rows(ds, full.result)
    for row in cols:
        tables.add("semantic_columns", system="full", **row)
    tables.add("semantic_type", system="full", dataset=ds.id, **semantic_metric.score_columns(cols))
    tables.add("domain", system="full", **semantic_metric.domain_row(ds, full.result))

    # KPIs
    for variant, run in runs.items():
        if run.error:
            continue
        rows, scores = kpi_metric.kpi_rows(ds, run)
        truth = scores.pop("_truth")
        for row in rows:
            tables.add("kpi_items", system=variant, **row)
        for row in truth:
            tables.add("kpi_truth", system=variant, **row)
        tables.add("kpi", system=variant, dataset=ds.id, **scores)

    # insights on the data and on a column-shuffled copy
    real = insight_metric.claim_count(full.result)
    null_run = run_pipeline(insight_metric.shuffle_columns(ds.frame, 20240601), f"null_{ds.name}")
    null = insight_metric.claim_count(null_run.result) if null_run.result else {"claims": None, "correlation": None, "trend": None, "insights": None}
    tables.add("insights", system="full", dataset=ds.id, real_claims=real["claims"], null_claims=null["claims"],
               null_correlation=null["correlation"], null_trend=null["trend"], null_insights=null["insights"],
               false_insight_dataset=bool(null["claims"]) if null["claims"] is not None else None)

    # copilot
    run_copilot(ds, full, llm, tables, variants)

    # raw-LLM baseline for classification and KPIs
    run_raw_llm(ds, llm, tables)

    # reverse engineering
    for variant in REVERSE_VARIANTS:
        if variant != "full" and variant not in variants:
            continue
        for spec, content, filename in reports_for(ds):
            try:
                with ablation(variant):
                    rows, summary = reverse_metric.run_report(ds, spec, content, filename)
            except Exception as exc:
                log(f"  reverse failed on {filename} ({variant}): {type(exc).__name__}: {exc}")
                continue
            for row in rows:
                tables.add("reverse_cells", system=variant, **row)
            tables.add("reverse", system=variant, **summary)
            tables.add("timing", dataset=ds.id, system=f"reverse:{variant}", rows=len(ds.frame), columns=len(ds.frame.columns),
                       seconds=round(summary["seconds"], 3), error="")


def run_copilot(ds: Dataset, full: Any, llm: CachedLLM, tables: Tables, variants: set[str]) -> None:
    data_facts = copilot_metric.fact_universe(ds)
    pipeline_facts = data_facts + copilot_metric.pipeline_facts(full.result)
    asked = copilot_metric.questions(ds)
    settings = Settings(anthropic_api_key="eval-cache")  # a non-empty key makes the service try the (cached) client
    service = LlmCopilotService(settings=settings, client=llm) if llm.mode != "off" else None
    from app.intelligence.copilot_engine import CopilotEngine

    def rules(q: str) -> tuple[str, str]:
        return CopilotEngine().ask(q, full.result).answer, "rules"

    def powerpilot_llm(q: str) -> tuple[str, str]:
        missed = llm.misses
        response = service.ask(q, full.result)
        if llm.misses > missed:  # the model could not be asked (nothing cached), so the rules engine answered instead
            raise CacheMiss("no cached model answer")
        return response.answer, response.source  # source is "rules" when the verifier rejected the model's answer

    def powerpilot_llm_free(q: str) -> tuple[str, str]:
        with ablation("no_copilot_verifier"):
            return powerpilot_llm(q)

    def baseline(q: str) -> tuple[str, str]:
        return raw_llm.answer(llm, ds, q), "llm"

    systems: dict[str, Callable[[str], tuple[str, str]]] = {"powerpilot_rules": rules}
    if service is not None:
        systems |= {"powerpilot_llm": powerpilot_llm, "powerpilot_llm_no_verifier": powerpilot_llm_free, "raw_llm": baseline}
    for system, ask in systems.items():
        for question in asked:
            try:
                answer, source = ask(question.text)
            except (CacheMiss, ModelUnavailable):
                tables.add("copilot", system=system, dataset=ds.id, question=question.text, status=NOT_RUN)
                continue
            row = copilot_metric.grade(ds, question, answer, data_facts if system == "raw_llm" else pipeline_facts)
            tables.add("copilot", system=system, status="ok", source=source, **{k: v for k, v in row.items() if k != "dataset"}, dataset=ds.id)


def run_raw_llm(ds: Dataset, llm: CachedLLM, tables: Tables) -> None:
    if llm.mode == "off":
        return
    try:
        guess = raw_llm.classify(llm, ds)
    except (CacheMiss, ModelUnavailable):
        tables.add("semantic_type", system="raw_llm", dataset=ds.id, status=NOT_RUN)
        tables.add("domain", system="raw_llm", dataset=ds.id, status=NOT_RUN)
        tables.add("kpi", system="raw_llm", dataset=ds.id, status=NOT_RUN)
        return
    predicted = guess.get("columns", {}) if isinstance(guess, dict) else {}
    rows = []
    for name, truth in ds.columns.items():
        entry = predicted.get(name) or {}
        rows.append({"dataset": ds.id, "column": name, "truth": truth, "predicted": str(entry.get("type", "missing")).lower(),
                     "confidence": float(entry.get("confidence", 0) or 0)})
    for row in rows:
        tables.add("semantic_columns", system="raw_llm", **row)
    tables.add("semantic_type", system="raw_llm", dataset=ds.id, **semantic_metric.score_columns(rows))
    domain = str(guess.get("domain", "missing")).lower() if isinstance(guess, dict) else "missing"
    tables.add("domain", system="raw_llm", dataset=ds.id, truth=ds.domain, predicted=domain,
               confidence=float(guess.get("domain_confidence", 0) or 0) if isinstance(guess, dict) else 0.0, correct=domain == ds.domain,
               label_confidence=ds.domain_label_confidence)
    try:
        stated = raw_llm.kpis(llm, ds)
    except (CacheMiss, ModelUnavailable):
        tables.add("kpi", system="raw_llm", dataset=ds.id, status=NOT_RUN)
        return
    from eval.common import close

    values = [float(k["value"]) for k in stated if isinstance(k, dict) and isinstance(k.get("value"), (int, float))]
    covered = sum(any(close(v, t["value"], 1e-2) for v in values) for t in ds.kpis)
    wrong = sum(not any(close(v, t["value"], 1e-2) for t in ds.kpis) for v in values)
    tables.add("kpi", system="raw_llm", dataset=ds.id, emitted=len(values), truth_kpis=len(ds.kpis),
               truth_coverage=covered / len(ds.kpis), value_accuracy=(len(values) - wrong) / len(values) if values else None,
               validity_rate=None)


# --- summary ----------------------------------------------------------------------------------------


def fmt(value: Optional[float], pct: bool = True) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value * 100:.1f}%" if pct else f"{value:.3f}"


def macro(frame: pd.DataFrame, column: str) -> Optional[float]:
    if frame.empty or column not in frame:
        return None
    return mean(pd.to_numeric(frame[column], errors="coerce").dropna().tolist())


def summary_markdown(t: Tables, datasets: list[str], variants: set[str]) -> str:
    out = ["# PowerPilot benchmark results", "", f"{len(datasets)} datasets. Every rate is the mean of per-dataset rates unless stated.", ""]

    def section(title: str, header: list[str], rows: list[list[str]], note: str = "") -> None:
        out.extend([f"## {title}", ""] + ([note, ""] if note else []))
        out.append("| " + " | ".join(header) + " |")
        out.append("|" + "|".join(["---"] * len(header)) + "|")
        out.extend("| " + " | ".join(r) + " |" for r in rows)
        out.append("")

    sem = t.frame("semantic_type")
    dom = t.frame("domain")
    rows = []
    for system in ["full", "raw_llm"]:
        s = sem[(sem["system"] == system) & (sem.get("status") != NOT_RUN)] if not sem.empty else sem
        d = dom[(dom["system"] == system) & (dom.get("status") != NOT_RUN)] if not dom.empty else dom
        if s.empty and d.empty:
            rows.append([system, "not run", "", "", "", "", ""])
            continue
        ece_domain = None
        if not d.empty and "confidence" in d:
            from eval.common import expected_calibration_error

            ece_domain = expected_calibration_error(d["confidence"].astype(float).tolist(), d["correct"].astype(bool).tolist(), bins=5)
        rows.append([system, str(len(s)), fmt(macro(s, "accuracy")), fmt(macro(s, "f1_labelled")), fmt(macro(s, "ece"), False),
                     fmt(d["correct"].astype(float).mean() if not d.empty else None), fmt(ece_domain, False)])
    section("Semantic types and domain", ["system", "datasets", "column accuracy", "F1 (labelled columns)", "column ECE", "domain accuracy", "domain ECE (5 bins)"], rows,
            "Column accuracy counts `unknown` as a class; F1 is over the columns that mean something. Domain ECE uses 5 bins because there are only a few dozen datasets.")

    kpi = t.frame("kpi")
    rows = []
    for system in ["full", "no_kpi_verifier", "raw_llm"]:
        k = kpi[(kpi["system"] == system) & (kpi.get("status") != NOT_RUN)] if not kpi.empty else kpi
        rows.append([system, str(len(k)), fmt(macro(k, "validity_rate")), fmt(macro(k, "value_accuracy")), fmt(macro(k, "truth_coverage"))] if not k.empty else [system, "not run", "", "", ""])
    section("KPIs", ["system", "datasets", "validity (refs exist and executes)", "value accuracy", "hand-computed KPIs recovered"], rows,
            "Validity and value accuracy are checked by an independent DAX evaluator. Recovery compares against hand-written pandas on the raw file.")

    ins = t.frame("insights")
    if not ins.empty:
        section("Insights on shuffled-column (null) data", ["datasets", "mean relationship claims, real data", "mean claims, null data", "share of datasets with any false claim"],
                [[str(len(ins)), fmt(macro(ins, "real_claims"), False), fmt(macro(ins, "null_claims"), False), fmt(ins["false_insight_dataset"].dropna().astype(float).mean())]],
                "A claim is a CORRELATION or TREND insight. On a shuffled copy every such claim is false by construction.")

    cop = t.frame("copilot")
    rows = []
    for system in COPILOT_SYSTEMS:
        c = cop[cop["system"] == system] if not cop.empty else cop
        if c.empty:
            rows.append([system, "not run", "", "", ""])
            continue
        ran = c[c["status"] == "ok"]
        rows.append([system, f"{len(ran)} of {len(c)}", fmt(ran["has_unsupported"].astype(float).mean()) if len(ran) else "n/a",
                     fmt(ran["correct"].astype(float).mean()) if len(ran) else "n/a", fmt(ran["answered"].astype(float).mean()) if len(ran) else "n/a"])
    section("Copilot grounding", ["system", "questions answered", "answers with an unsupported number", "answers that are correct", "answers stating a number"], rows,
            "Questions per system are `answered of asked`; those without a cached model reply are not run. Pooled over questions.")

    rev = t.frame("reverse")
    rows = []
    for system in REVERSE_VARIANTS:
        r = rev[rev["system"] == system] if not rev.empty else rev
        if r.empty:
            rows.append([system, "not run", "", "", "", "", ""])
            continue
        sums = r[["correct_cells", "reproduced_correct_formula", "reproduced_any", "false_alarms", "planted", "detected", "hints_ok"]].sum()
        flagged = sums["detected"] + sums["false_alarms"]
        rows.append([system, str(len(r)), fmt(sums["reproduced_correct_formula"] / sums["correct_cells"] if sums["correct_cells"] else None),
                     fmt(sums["reproduced_any"] / sums["correct_cells"] if sums["correct_cells"] else None),
                     fmt(sums["detected"] / flagged if flagged else None), fmt(sums["detected"] / sums["planted"] if sums["planted"] else None),
                     fmt(sums["hints_ok"] / sums["detected"] if sums["detected"] else None)])
    section("Reverse-engineering legacy reports", ["system", "reports", "correct cells reproduced with the right formula", "reproduced (any formula)", "planted-mistake precision", "planted-mistake recall", "hints naming the right problem"], rows,
            "Pooled over cells. A planted mistake is detected when its cell is reported NOT_REPRODUCIBLE.")

    tim = t.frame("timing")
    if not tim.empty:
        rows = [[s, str(len(g)), f"{g['seconds'].mean():.2f}", f"{g['seconds'].median():.2f}", f"{g['seconds'].max():.2f}"] for s, g in tim.groupby("system")]
        section("Wall-clock seconds", ["system", "runs", "mean", "median", "max"], rows)
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", nargs="*", default=["all"])
    parser.add_argument("--variants", default="all", help=f"comma list of {sorted(VARIANTS)} or 'all'")
    parser.add_argument("--llm-mode", choices=["replay", "record", "off"], default="replay")
    parser.add_argument("--out", default=str(RESULTS))
    args = parser.parse_args(argv)

    logging.disable(logging.INFO)  # the pipeline logs every stage
    ids = dataset_ids() if args.datasets == ["all"] else args.datasets
    variants = set(VARIANTS) if args.variants == "all" else set(args.variants.split(","))
    unknown = variants - set(VARIANTS)
    if unknown:
        parser.error(f"unknown variants: {sorted(unknown)}")
    llm = CachedLLM(args.llm_mode)
    tables = Tables()
    started = time.perf_counter()
    for ident in ids:
        t0 = time.perf_counter()
        ds = load(ident)
        run_dataset(ds, variants, llm, tables)
        log(f"{ident:28} {time.perf_counter() - t0:6.1f}s")
    from pathlib import Path

    out = Path(args.out)
    tables.write(out)
    summary = summary_markdown(tables, ids, variants)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    log(f"done in {time.perf_counter() - started:.0f}s; LLM cache hits={llm.hits} misses={llm.misses} live calls={llm.calls}")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
