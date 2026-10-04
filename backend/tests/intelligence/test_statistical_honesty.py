"""Insights must not be noise: multiple-testing correction, effect-size floor, and what survives on random data."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from app.core.config import Settings
from app.intelligence.data.plugins import CorrelationPlugin, TrendsPlugin
from app.intelligence.data_intelligence_engine import DataIntelligenceEngine
from app.intelligence.insight.generators.correlation_insights_generator import CorrelationInsightsGenerator
from app.intelligence.insight_engine import noise_note
from app.intelligence.stats.significance import (
    apply_fdr,
    benjamini_hochberg,
    correlation_p_values,
    reportable,
    trend_test,
)
from app.models.data_intelligence_models import CorrelationResult
from app.models.dataset_profile import DatasetProfile
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def profile(df: pd.DataFrame) -> DatasetProfile:
    return DatasetProfile(dataset_name="t.csv", total_rows=len(df), total_columns=len(df.columns))


def noise(seed: int, columns: int = 30, rows: int = 200, dates: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f"metric_{i:02d}": rng.normal(size=rows) for i in range(columns)})
    if dates:
        df.insert(0, "order_date", pd.date_range("2023-01-01", periods=rows))
    return df


# --- Benjamini-Hochberg ---------------------------------------------------------------------------


def reference_bh(p: list[float]) -> list[float]:
    """The textbook step-up procedure, written the slow obvious way."""
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    q = [0.0] * m
    best = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        best = min(best, p[i] * m / rank)
        q[i] = best
    return q


def test_bh_matches_the_textbook_example() -> None:
    assert benjamini_hochberg([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.02, 0.04, 0.04, 0.02])
    assert benjamini_hochberg([0.5]) == [0.5]
    assert benjamini_hochberg([]) == []


def test_bh_equals_the_reference_implementation_on_random_input() -> None:
    rng = np.random.default_rng(0)
    for _ in range(50):
        p = rng.uniform(size=int(rng.integers(1, 60))).tolist()
        assert benjamini_hochberg(p) == pytest.approx(reference_bh(p))


def test_q_values_never_fall_below_p_never_exceed_one_and_keep_the_order() -> None:
    p = np.random.default_rng(1).uniform(size=100)
    q = np.array(benjamini_hochberg(p.tolist()))
    assert (q >= p - 1e-12).all() and (q <= 1).all()
    assert (np.diff(q[np.argsort(p)]) >= -1e-12).all()  # monotone in p


def test_untestable_results_get_q_of_one_and_cannot_survive() -> None:
    assert benjamini_hochberg([None, math.nan, 0.001]) == pytest.approx([1.0, 1.0, 0.003])


def test_the_correction_counts_every_test_not_just_the_interesting_ones() -> None:
    """p = 0.01 alone is significant at q = 0.05; among 20 tests it is not."""
    alone = benjamini_hochberg([0.01])
    crowd = benjamini_hochberg([0.01] + [0.9] * 19)
    assert alone[0] <= 0.05 < crowd[0]


# --- the tests themselves match scipy -------------------------------------------------------------------


def test_correlation_p_values_equal_scipys_pearsonr_and_spearmanr() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=60)
    y = 0.4 * x + rng.normal(size=60)
    r_p, p_p = stats.pearsonr(x, y)
    r_s, p_s = stats.spearmanr(x, y)
    n = np.array([60.0])
    assert correlation_p_values(np.array([r_p]), n)[0] == pytest.approx(p_p, rel=1e-9)
    assert correlation_p_values(np.array([r_s]), n)[0] == pytest.approx(p_s, rel=1e-9)
    assert correlation_p_values(np.array([1.0]), n)[0] == 0.0
    assert math.isnan(correlation_p_values(np.array([0.9]), np.array([2.0]))[0])  # two points prove nothing


def test_the_plugin_reports_scipys_numbers_for_each_pair() -> None:
    df = noise(3, columns=3, rows=80)
    df["metric_01"] = 0.5 * df["metric_00"] + df["metric_01"]
    found = {(c.column_a, c.column_b): c for c in CorrelationPlugin().test_all(df, profile(df))}
    pair = found[("metric_00", "metric_01")]
    r, p_pearson = stats.pearsonr(df["metric_00"], df["metric_01"])
    _, p_spearman = stats.spearmanr(df["metric_00"], df["metric_01"])
    assert pair.coefficient == pytest.approx(r, abs=1e-4) and pair.n == 80
    assert pair.p_value == pytest.approx(max(p_pearson, p_spearman), rel=1e-6)  # must convince under both
    assert pair.effect_size == pytest.approx(abs(r), abs=1e-4)
    assert len(found) == 3  # every pair is tested, not just the strong ones


def test_pearson_alone_is_not_enough_when_one_outlier_drives_it() -> None:
    rng = np.random.default_rng(4)
    x, y = rng.normal(size=60), rng.normal(size=60)
    x[0], y[0] = 40.0, 40.0  # a single point manufactures a Pearson correlation
    df = pd.DataFrame({"a": x, "b": y})
    (pair,) = CorrelationPlugin().test_all(df, profile(df))
    assert pair.effect_size > 0.9 and pair.p_value > 0.05  # the rank test sees nothing, so the pair does not pass


def test_trend_uses_linregress_for_enough_points_and_mann_kendall_for_few() -> None:
    rng = np.random.default_rng(5)
    long = np.arange(40) * 0.5 + rng.normal(size=40)
    slope, p, effect, method = trend_test(long)
    fit = stats.linregress(np.arange(40), long)
    assert method == "linregress" and p == pytest.approx(fit.pvalue) and effect == pytest.approx(abs(fit.rvalue)) and slope == pytest.approx(fit.slope)

    short = np.array([1.0, 2.5, 2.0, 4.0, 5.5, 5.0])
    _, p, effect, method = trend_test(short)
    tau, expected = stats.kendalltau(np.arange(6), short)
    assert method == "mann-kendall" and p == pytest.approx(expected) and effect == pytest.approx(abs(tau))


def test_a_constant_or_tiny_series_has_no_p_value() -> None:
    assert math.isnan(trend_test(np.ones(20))[1]) and math.isnan(trend_test(np.array([1.0, 2.0]))[1])


# --- pure noise: nothing survives -------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(10))
def test_on_random_data_with_30_columns_at_most_one_finding_survives(seed: int) -> None:
    df = noise(seed, dates=True)
    report = DataIntelligenceEngine().analyze(df, profile(df))

    assert len(report.correlations) + len(report.trends) <= 1, (seed, report.correlations, report.trends)
    assert report.tests_run == 30 * 29 // 2 + 30  # every pair and every metric-over-time was counted
    assert report.rejected_as_noise >= report.tests_run - 1


def test_without_the_correction_the_same_data_is_full_of_findings() -> None:
    """Why the correction exists: ~5% of 435 independent tests clear p < 0.05 by chance."""
    df = noise(0)
    tested = CorrelationPlugin().test_all(df, profile(df))
    naive = [c for c in tested if c.p_value < 0.05]
    assert len(tested) == 435 and len(naive) >= 10
    assert [c for c in apply_fdr(tested, 0.05) if c.survived_fdr] == []


@pytest.mark.parametrize("seed", range(5))
def test_no_insight_reaches_the_report_from_random_data(seed: int) -> None:
    df = noise(seed, columns=30, rows=120, dates=True)
    result = PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="noise.csv")
    report = result.insight_report

    claims = [i for i in report.insights if i.category in ("CORRELATION", "TREND")]
    assert len(claims) <= 1
    assert "Rejected as likely noise" in report.noise_note and report.rejected_as_noise >= 400


# --- a real relationship survives ---------------------------------------------------------------------------


def planted(seed: int = 11, rows: int = 200) -> pd.DataFrame:
    df = noise(seed, rows=rows, dates=True)
    rng = np.random.default_rng(seed + 1)
    df["driver"] = rng.normal(size=rows)
    df["response"] = 0.7 * df["driver"] + rng.normal(scale=0.7, size=rows)  # r around 0.7
    df["growth"] = np.arange(rows) * 0.05 + rng.normal(size=rows)  # a real upward trend
    return df


def test_a_planted_correlation_survives_among_thirty_noise_columns() -> None:
    df = planted()
    report = DataIntelligenceEngine().analyze(df, profile(df))

    pairs = {(c.column_a, c.column_b): c for c in report.correlations}
    found = pairs[("driver", "response")]
    assert found.survived_fdr and found.q_value < 0.001 and found.effect_size > 0.6 and found.n == 200
    assert len(report.correlations) == 1


def test_a_planted_trend_survives_and_noise_trends_do_not() -> None:
    df = planted()
    report = DataIntelligenceEngine().analyze(df, profile(df))

    assert [t.metric_column for t in report.trends] == ["growth"]
    trend = report.trends[0]
    assert trend.direction == "increasing" and trend.survived_fdr and trend.test_method == "linregress"


def test_a_planted_correlation_reaches_the_insight_report() -> None:
    result = PowerPilotIntelligencePipeline().run_pipeline(planted(rows=150), dataset_name="planted.csv")
    titles = " ".join(i.title for i in result.insight_report.insights)
    assert "driver" in titles and "response" in titles


def test_a_real_but_tiny_effect_is_statistically_significant_yet_not_reported() -> None:
    """With 20,000 rows even r = 0.05 beats the correction. It is real and it is not worth an executive's attention."""
    rng = np.random.default_rng(8)
    x = rng.normal(size=20_000)
    df = pd.DataFrame({"a": x, "b": 0.05 * x + rng.normal(size=20_000)})
    (finding,) = apply_fdr(CorrelationPlugin().test_all(df, profile(df)), 0.05)
    assert finding.survived_fdr and finding.effect_size < 0.1
    assert not reportable(finding, 0.3)

    report = DataIntelligenceEngine().analyze(df, profile(df))
    assert report.correlations == () and report.below_effect_threshold == 1 and report.rejected_as_noise == 0


def test_the_effect_size_floor_is_configurable(monkeypatch) -> None:
    df = planted()
    monkeypatch.setattr("app.intelligence.data_intelligence_engine.get_settings", lambda: Settings(insight_min_effect_size=0.95))
    strict = DataIntelligenceEngine().analyze(df, profile(df))
    assert strict.correlations == () and strict.below_effect_threshold >= 1

    monkeypatch.setattr("app.intelligence.data_intelligence_engine.get_settings", lambda: Settings(insight_min_effect_size=0.3))
    assert len(DataIntelligenceEngine().analyze(df, profile(df)).correlations) == 1


def test_the_fdr_level_is_configurable(monkeypatch) -> None:
    rng = np.random.default_rng(9)
    x = rng.normal(size=40)
    df = pd.DataFrame({"a": x, "b": 0.5 * x + rng.normal(size=40), **{f"n{i}": rng.normal(size=40) for i in range(8)}})
    monkeypatch.setattr("app.intelligence.data_intelligence_engine.get_settings", lambda: Settings(insight_fdr_q=0.5))
    loose = DataIntelligenceEngine().analyze(df, profile(df))
    monkeypatch.setattr("app.intelligence.data_intelligence_engine.get_settings", lambda: Settings(insight_fdr_q=0.001))
    strict = DataIntelligenceEngine().analyze(df, profile(df))
    assert len(loose.correlations) >= len(strict.correlations) and loose.fdr_q == 0.5 and strict.fdr_q == 0.001


# --- bookkeeping, keys, and the generators ------------------------------------------------------------------


def test_every_finding_stores_its_evidence() -> None:
    df = planted()
    for finding in [*CorrelationPlugin().test_all(df, profile(df)), *TrendsPlugin().test_all(df, profile(df))]:
        assert finding.p_value is not None and 0 <= finding.p_value <= 1
        assert finding.effect_size is not None and finding.n > 0
        assert finding.q_value is None and finding.survived_fdr is False  # not corrected until the engine pools them
    report = DataIntelligenceEngine().analyze(df, profile(df))
    for finding in [*report.correlations, *report.trends]:
        assert finding.q_value is not None and finding.q_value <= 0.05 and finding.survived_fdr


def test_key_columns_are_not_tested_and_do_not_inflate_the_family() -> None:
    df = noise(0, columns=5, dates=True)
    df["order_id"] = np.arange(len(df))
    df["customer_id"] = np.arange(len(df)) * 3
    tested = TrendsPlugin().test_all(df, profile(df))
    assert {t.metric_column for t in tested} == {f"metric_{i:02d}" for i in range(5)}
    assert all("order_id" not in (c.column_a, c.column_b) for c in CorrelationPlugin().test_all(df, profile(df)))


def test_the_plugins_alone_also_correct_and_filter() -> None:
    df = planted()
    assert [(c.column_a, c.column_b) for c in CorrelationPlugin().analyze(df, profile(df))] == [("driver", "response")]
    assert [t.metric_column for t in TrendsPlugin().analyze(df, profile(df))] == ["growth"]


def test_a_generator_ignores_findings_that_did_not_survive() -> None:
    from app.models.business_profile import BusinessProfile
    from app.models.data_intelligence_models import DataIntelligenceReport, QualityReport, StatisticalSummary

    def finding(**kw) -> CorrelationResult:
        return CorrelationResult("a", "b", 0.9, "strong_positive", 0.9, "r=0.9", p_value=0.001, q_value=0.001, effect_size=0.9, n=50, **kw)

    def run(corr: CorrelationResult):
        report = DataIntelligenceReport(
            QualityReport(100, 100, 100, 100, 0), StatisticalSummary(10, 2, 0, 0), correlations=(corr,)
        )
        return CorrelationInsightsGenerator().generate(DatasetProfile("t", 10, 2), BusinessProfile.__new__(BusinessProfile), report)

    assert len(run(finding(survived_fdr=True))) == 1
    assert run(finding(survived_fdr=False)) == ()
    assert run(CorrelationResult("a", "b", 0.9, "strong_positive", 0.9, "r=0.9")) == ()  # no evidence at all is not a finding


def test_the_noise_note_says_how_much_was_thrown_away() -> None:
    df = planted()
    report = DataIntelligenceEngine().analyze(df, profile(df))
    note = noise_note(report)
    assert note.startswith(f"Rejected as likely noise: {report.rejected_as_noise} findings")
    assert f"of {report.tests_run} relationships tested" in note and "false discovery rate 5%" in note
    assert noise_note(DataIntelligenceEngine().analyze(pd.DataFrame({"a": ["x", "y"]}), DatasetProfile("t", 2, 1))) == ""


def test_the_fact_sheet_states_the_rejection_so_the_copilot_can_cite_it() -> None:
    from app.intelligence.llm.grounding import build_facts

    result = PowerPilotIntelligencePipeline().run_pipeline(planted(rows=150), dataset_name="planted.csv")
    sheet = build_facts(result)
    keys = {f.key: f for f in sheet.facts.values()}
    assert keys["statistics.rejected_as_noise"].value == result.data_intelligence_report.rejected_as_noise
    assert keys["statistics.tests_run"].value == result.data_intelligence_report.tests_run
    assert "STATISTICAL RIGOUR" in sheet.text


def test_correlations_and_trends_are_corrected_as_one_family() -> None:
    """A correlation that passes alone must fail when 30 trends were tested beside it."""
    from app.models.data_intelligence_models import TrendResult

    corr = CorrelationResult("a", "b", 0.5, "strong_positive", 0.5, "r", p_value=0.01, effect_size=0.5, n=50)
    trends = tuple(
        TrendResult("d", f"m{i}", "increasing", 1.0, 5.0, 0.8, "t", p_value=0.9, effect_size=0.1, n=50) for i in range(30)
    )
    alone = DataIntelligenceEngine._correct_for_multiple_testing((corr,), ())
    pooled = DataIntelligenceEngine._correct_for_multiple_testing((corr,), trends)

    assert len(alone[0]) == 1 and alone[2]["tests_run"] == 1
    assert pooled[0] == () and pooled[2]["tests_run"] == 31 and pooled[2]["rejected_as_noise"] == 31
