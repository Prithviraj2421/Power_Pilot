"""The benchmark's own machinery: the pieces that decide what a number in the results means."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from app.core.config import Settings
from app.intelligence.llm.llm_copilot import LlmCopilotService
from eval import common, raw_llm
from eval.llm import CacheMiss, CachedLLM, ModelUnavailable, request_key
from eval.metrics import copilot as copilot_metric
from eval.metrics import insights as insight_metric
from eval.metrics import semantic
from eval.reports import generate
from eval.systems import ablation, run_pipeline


def require_data() -> None:
    """The datasets are downloaded, not committed: tests that need them skip until `python -m eval.datasets.download` ran."""
    if not (common.RAW / "golden_superstore.csv").exists():
        pytest.skip("benchmark datasets not downloaded (python -m eval.datasets.download)")


# --- calibration and scoring -----------------------------------------------------------------------


def test_ece_is_zero_for_a_calibrated_predictor_and_large_for_an_overconfident_one() -> None:
    assert common.expected_calibration_error([0.5, 0.5, 0.5, 0.5], [True, False, True, False]) == pytest.approx(0.0)
    assert common.expected_calibration_error([0.99] * 10, [True] * 5 + [False] * 5) == pytest.approx(0.49)
    assert common.expected_calibration_error([], []) is None
    assert common.expected_calibration_error([1.0], [True]) == pytest.approx(0.0)  # confidence 1.0 lands in the last bin


def test_column_scores_separate_unknown_from_meaningful() -> None:
    rows = [
        {"truth": "revenue", "predicted": "revenue", "confidence": 0.9},
        {"truth": "revenue", "predicted": "unknown", "confidence": 0.5},
        {"truth": "unknown", "predicted": "revenue", "confidence": 0.5},  # a wrong claim
        {"truth": "unknown", "predicted": "unknown", "confidence": 1.0},
    ]
    s = semantic.score_columns(rows)
    assert s["accuracy"] == 0.5 and s["recall_labelled"] == 0.5 and s["precision_claims"] == 0.5 and s["f1_labelled"] == 0.5


def test_labels_cover_every_dataset_and_use_the_products_taxonomy() -> None:
    from app.common.enums import SemanticType

    require_data()
    allowed = {s.value for s in SemanticType}
    ids = common.dataset_ids()
    assert len(ids) >= 25
    for ident in ids:
        ds = common.load(ident)
        assert set(ds.columns) == set(ds.frame.columns), ident  # every column labelled (explicitly or as unknown)
        assert set(ds.columns.values()) <= allowed, ident
        assert ds.domain in {"retail", "finance", "hr", "healthcare", "marketing", "logistics", "unknown"}
        assert len(ds.kpis) >= 3 and all(isinstance(k["value"], float) for k in ds.kpis)


def test_the_manifest_lock_records_a_licence_and_checksum_for_every_dataset() -> None:
    lock = json.loads((common.EVAL / "datasets" / "manifest.lock.json").read_text(encoding="utf-8"))
    assert set(lock) == set(common.dataset_ids())
    for ident, record in lock.items():
        assert record["sha256"] and record["licence"] and "NOT FOUND" not in record["licence"], ident
        if ident.startswith("uci_"):
            assert "Creative Commons" in record["licence"] and record["source"].startswith("https://archive.ics.uci.edu/")


# --- the model cache ----------------------------------------------------------------------------------


def make_client(text: str):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn")

    return SimpleNamespace(messages=SimpleNamespace(create=create)), calls


def test_record_then_replay_costs_nothing_the_second_time(tmp_path) -> None:
    live, calls = make_client("hello")
    path = tmp_path / "llm.jsonl"
    first = CachedLLM("record", path, live_client=live)
    request = dict(model="m", system="s", messages=[{"role": "user", "content": "hi"}], max_tokens=5)
    assert first.messages.create(**request).content[0].text == "hello" and len(calls) == 1

    replay = CachedLLM("replay", path)
    assert replay.messages.create(**request).content[0].text == "hello" and replay.hits == 1 and len(calls) == 1
    with pytest.raises(CacheMiss):
        replay.messages.create(**{**request, "messages": [{"role": "user", "content": "different"}]})
    assert replay.misses == 1


def test_off_never_answers_and_the_key_ignores_irrelevant_arguments() -> None:
    with pytest.raises(ModelUnavailable):
        CachedLLM("off").messages.create(model="m", messages=[])
    assert request_key({"model": "m", "messages": [1], "stream": True}) == request_key({"model": "m", "messages": [1]})
    assert request_key({"model": "m", "messages": [1]}) != request_key({"model": "m", "messages": [2]})
    with pytest.raises(ValueError):
        CachedLLM("sometimes")


# --- copilot grounding --------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def retail():
    require_data()
    return common.load("golden_superstore")


def test_the_question_set_has_truth_computed_by_pandas(retail) -> None:
    asked = {q.text: q for q in copilot_metric.questions(retail)}
    assert asked["How many rows are in the dataset?"].truth == 156
    total = next(q for q in asked.values() if q.text.startswith("What is the total of"))
    column = total.text.removeprefix("What is the total of ").removesuffix("?")
    assert total.truth == pytest.approx(retail.frame[column].sum())
    assert any(q.group for q in asked.values())


def test_a_true_number_is_supported_and_an_invented_one_is_not(retail) -> None:
    universe = copilot_metric.fact_universe(retail)
    question = copilot_metric.questions(retail)[1]
    exact = copilot_metric.grade(retail, question, f"The total is {question.truth:,.2f}.", universe)
    assert not exact["has_unsupported"] and exact["correct"]
    invented = copilot_metric.grade(retail, question, f"It is about {question.truth * 1.37:,.2f}.", universe)
    assert invented["has_unsupported"] and not invented["correct"]
    rounded = copilot_metric.grade(retail, question, f"Roughly {question.truth / 1000:,.1f}K.", universe)
    assert not rounded["has_unsupported"]  # rounding to the precision written is not an invention


def test_small_whole_numbers_are_not_flagged(retail) -> None:
    universe = copilot_metric.fact_universe(retail)
    question = copilot_metric.questions(retail)[0]
    graded = copilot_metric.grade(retail, question, "There are 156 rows across 2 groups; top 3 shown.", universe)
    assert not graded["has_unsupported"] and graded["correct"]


def test_a_which_group_question_needs_the_right_group(retail) -> None:
    question = next(q for q in copilot_metric.questions(retail) if q.group)
    universe = copilot_metric.fact_universe(retail)
    right = copilot_metric.grade(retail, question, f"{question.group} with {question.truth:,.2f}.", universe)
    wrong = copilot_metric.grade(retail, question, f"Nowhere with {question.truth:,.2f}.", universe)
    assert right["correct"] and not wrong["correct"]


def test_the_verifier_ablation_changes_what_the_copilot_shows(retail) -> None:
    """A model that invents a number: the verifier falls back to the rules answer; without it the invention is shown."""
    run = run_pipeline(retail.frame, retail.name)
    live, _ = make_client("Total sales were 999,999,999.12 across the whole file.")
    service = LlmCopilotService(settings=Settings(anthropic_api_key="x"), client=live)
    guarded = service.ask("What is the total of Sales?", run.result)
    assert guarded.source == "rules" and "999,999,999" not in guarded.answer
    with ablation("no_copilot_verifier"):
        unguarded = service.ask("What is the total of Sales?", run.result)
    assert unguarded.source == "llm" and "999,999,999.12" in unguarded.answer


def test_raw_llm_baseline_sees_only_the_head_and_parses_json(retail, tmp_path) -> None:
    reply = 'Sure: {"domain": "retail", "domain_confidence": 0.9, "columns": {"Sales": {"type": "revenue", "confidence": 0.8}}}'
    live, calls = make_client(reply)
    llm = CachedLLM("record", tmp_path / "c.jsonl", live_client=live)
    guess = raw_llm.classify(llm, retail)
    assert guess["domain"] == "retail" and guess["columns"]["Sales"]["type"] == "revenue"
    prompt = calls[0]["messages"][0]["content"]
    assert prompt.count("\n") < 40  # the head, not the whole file


# --- the kpi scorer -----------------------------------------------------------------------------------


def test_the_kpi_oracle_executes_dax_and_rejects_bad_references() -> None:
    from eval.metrics.kpi import execute

    frame = pd.DataFrame({"Sales": [1.0, 2.0, 3.0], "Region": ["a", "b", "a"]})
    assert execute("SUM('T'[Sales])", "T", frame) == (True, 6.0, "")
    exists, value, problem = execute("SUM('T'[Nope])", "T", frame)
    assert not exists and value is None and "Nope" in problem
    assert not execute("SUM('Other'[Sales])", "T", frame)[0]
    assert execute("CALCULATE(SUM('T'[Sales]), 'T'[Region] = \"a\")", "T", frame)[1] == 4.0


# --- insights and reports -------------------------------------------------------------------------------


def test_shuffling_keeps_each_columns_values_and_breaks_the_relationships() -> None:
    frame = pd.DataFrame({"a": range(200), "b": [2 * i for i in range(200)]})
    shuffled = insight_metric.shuffle_columns(frame, 1)
    assert sorted(shuffled["a"]) == sorted(frame["a"]) and sorted(shuffled["b"]) == sorted(frame["b"])
    assert abs(shuffled["a"].corr(shuffled["b"])) < 0.3 < frame["a"].corr(frame["b"])
    assert shuffled.equals(insight_metric.shuffle_columns(frame, 1))
    assert not shuffled.equals(insight_metric.shuffle_columns(frame, 2))


def test_generated_reports_have_known_formulas_and_planted_mistakes(retail) -> None:
    (spec, _, filename), second = generate.reports_for(retail)
    assert filename.endswith(".xlsx") and second[2].endswith(".csv")
    assert {c.mistake for c in spec.cells if c.mistake} == {"swapped-digits", "one-row", "missing-category"}
    for cell in spec.cells:
        if cell.mistake is None and cell.formula is None:
            assert cell.expected is not None  # every correct cell has the formula that produced it
        if cell.mistake is not None:
            assert cell.expected is None  # a mistake has no formula that explains it
    assert json.loads(json.dumps(spec.truth()))["cells"]
    assert [c.value for c in generate.reports_for(retail)[0][0].cells] == [c.value for c in spec.cells]  # deterministic


def test_the_missing_category_mistake_is_lower_than_the_true_grand_total(retail) -> None:
    from app.intelligence.kpi.compilers import PandasCompiler
    from app.intelligence.kpi.ir import Measure, Op

    (spec, _, _), _ = generate.reports_for(retail)
    first = [c for c in spec.cells if c.table == next(iter(spec.tables))]
    typed_all = next(c for c in first if c.mistake == "missing-category")
    grand = float(PandasCompiler().evaluate(Measure(Op.SUM, typed_all.col), retail.frame))
    assert typed_all.value < grand
