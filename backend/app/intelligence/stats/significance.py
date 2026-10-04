"""Statistical honesty for findings: p-values, a false-discovery-rate correction across *every* test run, and an effect-size floor.

Testing 400 column pairs at p < 0.05 produces about 20 "significant" correlations in pure noise. So every relationship
PowerPilot tests (each correlation pair, each metric-over-time trend) is pooled into one family and corrected with
Benjamini-Hochberg at a fixed false discovery rate q. A finding is *reportable* only if it survives that correction AND
is big enough to matter (|r| or |tau| at least ``insight_min_effect_size``): with 20,000 rows even r = 0.02 is "significant".

The tests themselves:
* correlation: Pearson's r with the exact t-test p-value of ``scipy.stats.pearsonr``, and Spearman's rho the same way
  (``scipy.stats.spearmanr``'s t approximation) on ranks. The finding's p-value is the larger of the two, so a relationship
  that only one outlier drives (strong Pearson, nothing in the ranks) does not pass. Computed for all pairs at once with
  vectorised pairwise-complete statistics; tests assert equality with scipy's per-pair functions.
* trend: ``scipy.stats.linregress`` slope p-value against the time order, or, for fewer than ``SMALL_N`` points, the
  Mann-Kendall test (Kendall's tau against time order), which needs no normality and is exact for small n.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Optional, Sequence, TypeVar

import numpy as np
from scipy import stats

SMALL_N = 10  # below this many points a trend is tested with Mann-Kendall instead of linear regression
MIN_N = 3  # a relationship cannot be tested on fewer points

F = TypeVar("F")


def benjamini_hochberg(p_values: Sequence[Optional[float]]) -> list[float]:
    """BH-adjusted p-values ("q-values"). An untestable result (None or NaN) gets q = 1.

    Reject the hypotheses whose q-value is at most the chosen false discovery rate. The adjustment is the step-up
    procedure: sort, scale p(i) by m / i, and take a running minimum from the largest p downwards.
    """
    m = len(p_values)
    if m == 0:
        return []
    p = np.array([1.0 if v is None or not math.isfinite(v) else min(max(float(v), 0.0), 1.0) for v in p_values])
    order = np.argsort(p, kind="stable")
    scaled = p[order] * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(scaled[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(adjusted, 1.0)
    return q.tolist()


def correlation_p_values(r: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Two-sided p-values for correlation coefficients ``r`` on ``n`` points (the t-test scipy's pearsonr/spearmanr use)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        degrees = n - 2
        t = r * np.sqrt(degrees / np.maximum(1 - r * r, 0.0))
        p = 2 * stats.t.sf(np.abs(t), degrees)
    p = np.where(np.abs(r) >= 1.0, 0.0, p)
    return np.where(n >= MIN_N, p, np.nan)


def trend_test(values: np.ndarray) -> tuple[float, float, float, str]:
    """(slope, p_value, effect_size, method) for a series against its own order.

    ``effect_size`` is |r| for the regression and |tau| for Mann-Kendall. A series too short or constant yields p = NaN.
    """
    y = np.asarray(values, dtype=float)
    n = len(y)
    x = np.arange(n, dtype=float)
    if n < MIN_N or np.ptp(y) == 0:
        slope = float(np.polyfit(x, y, 1)[0]) if n >= 2 else 0.0
        return slope, math.nan, 0.0, "none"
    if n < SMALL_N:
        tau, p = stats.kendalltau(x, y)
        slope = float(stats.theilslopes(y, x)[0])
        return slope, float(p), abs(float(tau)), "mann-kendall"
    fit = stats.linregress(x, y)
    return float(fit.slope), float(fit.pvalue), abs(float(fit.rvalue)), "linregress"


def apply_fdr(findings: Sequence[F], q: float) -> list[F]:
    """Set ``q_value`` and ``survived_fdr`` on every finding, correcting across all of them together."""
    q_values = benjamini_hochberg([getattr(f, "p_value", None) for f in findings])
    return [replace(f, q_value=qv, survived_fdr=qv <= q) for f, qv in zip(findings, q_values)]


def reportable(finding: object, min_effect: float) -> bool:
    """Survived the FDR correction and is large enough to matter."""
    effect = getattr(finding, "effect_size", None)
    return bool(getattr(finding, "survived_fdr", False)) and effect is not None and effect >= min_effect


def testable_columns(names: Sequence[str], profile: object) -> list[str]:
    """Columns worth testing for relationships: not keys. A trend through order_id is arithmetic, not a finding,
    and including keys would also enlarge the family every real finding is corrected against."""
    from app.common.metric_filter import SmartMetricFilter

    flagged = {
        c.name
        for c in getattr(profile, "columns", [])
        if c.identifier or str(getattr(c.semantic_type, "value", c.semantic_type)).upper() == "IDENTIFIER"
    }
    return [n for n in names if str(n) not in flagged and not SmartMetricFilter.is_identifier_column(str(n))]
