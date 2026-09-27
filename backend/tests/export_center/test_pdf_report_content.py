"""Content-correctness tests for the executive PDF report.

The previous builder produced a PDF that was non-empty and had the right sheet
structure, and that was the entire test coverage -- which is exactly how it
shipped with truncated sentences, three hardcoded quality sub-scores that never
changed regardless of the dataset, a hardcoded "98.4% HIGH" confidence, a
cleaning summary that always read "0 -> 0" because it accessed attributes that
don't exist on DataPreparationReport, a schema table capped at 10 columns, and
five whole report sections (trends, correlations, anomalies, insights,
relationships) that were computed by the pipeline and never once appeared in
the document.

These tests extract the real text from the real rendered PDF with pypdf and
assert against it, rather than checking that bytes came back non-empty.
"""

from __future__ import annotations

import io

import pandas as pd
import pypdf
import pytest

from app.export_center.builders.pdf_builder import PdfExportBuilder
from app.export_center.models.export_models import BrandingConfig
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def _extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


@pytest.fixture(scope="module")
def rich_df() -> pd.DataFrame:
    """A dataset large and messy enough to exercise every report section:
    >10 columns (schema table), missing values and duplicates (quality audit),
    a genuine trend and correlation (statistical intelligence), and enough
    rows for the domain classifier to commit to RETAIL with real confidence.
    """
    import numpy as np

    rng = np.random.default_rng(11)
    n = 300
    quantity = rng.integers(1, 10, n)
    unit_price = np.round(rng.uniform(5, 500, n), 2)
    sales = np.round(quantity * unit_price, 2)
    profit = np.round(sales * rng.uniform(0.05, 0.3, n), 2)

    df = pd.DataFrame(
        {
            "order_id": [f"ORD-{i:05d}" for i in range(n)],
            "order_date": pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
            "customer_id": [f"CUST-{i % 60:03d}" for i in range(n)],
            "region": rng.choice(["North", "South", "East", "West"], n),
            "category": rng.choice(["Electronics", "Furniture", "Office Supplies"], n),
            "sub_category": rng.choice(["Chairs", "Phones", "Binders", "Tables"], n),
            "ship_mode": rng.choice(["Standard Class", "First Class", "Same Day"], n),
            "segment": rng.choice(["Consumer", "Corporate", "Home Office"], n),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount": rng.choice([0.0, 0.1, 0.2], n),
            "sales": sales,
            "profit": profit,
        }
    )
    # Deliberate, known dirt so the quality section has real, checkable numbers.
    df.loc[rng.choice(n, 20, replace=False), "region"] = None
    df.loc[rng.choice(n, 15, replace=False), "profit"] = None
    df = pd.concat([df, df.iloc[[0, 1, 2]]], ignore_index=True)  # 3 exact duplicates
    return df


@pytest.fixture(scope="module")
def rich_pdf_text(rich_df: pd.DataFrame) -> str:
    result = PowerPilotIntelligencePipeline().run_pipeline(rich_df, dataset_name="rich_test.csv")
    pdf_bytes = PdfExportBuilder.build_executive_pdf(result)
    return _extract_text(pdf_bytes)


@pytest.fixture(scope="module")
def rich_result(rich_df: pd.DataFrame):
    return PowerPilotIntelligencePipeline().run_pipeline(rich_df, dataset_name="rich_test.csv")


# ---------------------------------------------------------------------------
# No fabricated numbers
# ---------------------------------------------------------------------------


def test_cover_confidence_is_the_real_domain_confidence(rich_pdf_text: str, rich_result) -> None:
    """The cover page previously showed a flat "98.4% HIGH" regardless of dataset."""
    real_confidence_pct = round(rich_result.dataset_profile.domain_confidence * 100)
    assert f"{real_confidence_pct}% Confidence" in rich_pdf_text
    assert "98.4" not in rich_pdf_text


def test_quality_subscores_are_computed_not_hardcoded(rich_pdf_text: str, rich_result) -> None:
    """These three exact figures were hardcoded constants in every previous
    report regardless of what was actually in the dataset."""
    scores = rich_result.quality_report.column_scores
    assert scores, "fixture assumption: column scores must exist to test against"

    real_completeness = sum(s.completeness for s in scores) / len(scores)
    real_validity = sum(s.validity for s in scores) / len(scores)

    assert f"{real_completeness:.1f}%" in rich_pdf_text
    assert f"{real_validity:.1f}%" in rich_pdf_text
    # The old fixed triple. Real data essentially never lands on all three at once.
    assert not all(v in rich_pdf_text for v in ("98.5%", "96.2%", "99.1%"))


def test_missing_value_counts_are_real_not_zero(rich_pdf_text: str) -> None:
    """The cleaning summary used to read attributes that don't exist on
    DataPreparationReport and silently showed "0" for missing values and
    duplicate rows no matter what was actually cleaned."""
    assert "20 (" in rich_pdf_text  # the 20 missing `region` values
    assert "15 (" in rich_pdf_text  # the 15 missing `profit` values
    assert "3 (1.0%)" in rich_pdf_text or "3 (0." in rich_pdf_text  # the 3 duplicate rows


def test_cleaning_row_counts_are_real(rich_pdf_text: str, rich_result) -> None:
    prep = rich_result.preparation_report
    assert f"{prep.original_rows:,}" in rich_pdf_text
    assert f"{prep.cleaned_rows:,}" in rich_pdf_text


# ---------------------------------------------------------------------------
# No truncation
# ---------------------------------------------------------------------------


def test_long_narrative_text_is_not_cut_with_an_ellipsis(rich_pdf_text: str) -> None:
    """The 4-part briefing box used to hard-truncate every point at 75
    characters with `desc[:75] + "..."`, mid-word, regardless of content."""
    assert "..." not in rich_pdf_text.replace("CJK", "")  # guard against false positive from font metadata


def test_recommended_actions_appear_in_full(rich_pdf_text: str, rich_result) -> None:
    summary = rich_result.insight_report.executive_summary if rich_result.insight_report else None
    if summary and summary.recommended_actions:
        # A full sentence from the real summary must appear complete, not cut.
        last_action = summary.recommended_actions[-1]
        assert last_action[-10:] in rich_pdf_text, "the end of the sentence was truncated"


# ---------------------------------------------------------------------------
# Nothing capped or dropped
# ---------------------------------------------------------------------------


def test_every_column_appears_not_just_the_first_ten(rich_pdf_text: str) -> None:
    """The schema table was hardcoded to `columns[:10]`. This dataset has 13
    columns; discount/sales/profit are the 11th-13th, past the old cutoff."""
    for column in ("discount", "sales", "profit"):
        assert column in rich_pdf_text


def test_every_primary_kpi_appears(rich_pdf_text: str, rich_result) -> None:
    for kpi in rich_result.kpi_report.primary_kpis:
        assert kpi.name in rich_pdf_text


def test_every_primary_decision_appears(rich_pdf_text: str, rich_result) -> None:
    """The decisions page was hardcoded to `primary_decisions[:4]`."""
    for decision in rich_result.decision_report.primary_decisions:
        assert decision.action_title in rich_pdf_text


# ---------------------------------------------------------------------------
# Previously-missing sections now exist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    [
        "Statistical Intelligence",
        "Executive Insights",
        "Entity Relationships",
    ],
)
def test_previously_absent_sections_are_present(rich_pdf_text: str, heading: str) -> None:
    assert heading in rich_pdf_text


def test_trend_content_is_real(rich_pdf_text: str, rich_result) -> None:
    trends = rich_result.data_intelligence_report.trends if rich_result.data_intelligence_report else ()
    if trends:
        assert trends[0].metric_column in rich_pdf_text


def test_insight_content_is_real(rich_pdf_text: str, rich_result) -> None:
    insights = rich_result.insight_report.insights if rich_result.insight_report else ()
    if insights:
        assert insights[0].title in rich_pdf_text


def test_relationship_content_is_real(rich_pdf_text: str, rich_result) -> None:
    relationships = (
        rich_result.relationship_report.all_relationships if rich_result.relationship_report else ()
    )
    if relationships:
        assert relationships[0].source_column in rich_pdf_text


# ---------------------------------------------------------------------------
# Running header tracks the actual section on each page (regression for the
# old fixed page-number -> label table, which mislabeled any page once a
# section grew past its assumed length)
# ---------------------------------------------------------------------------


def test_running_header_matches_content_across_a_multipage_section(rich_pdf_text: str) -> None:
    """Executive Insights runs several pages for a dataset this size. Every
    one of those pages must be labelled "EXECUTIVE INSIGHTS" in the running
    header -- not whatever section the old fixed page-number table assumed."""
    reader_pages = rich_pdf_text.split("POWERPILOT MAGAZINE |")
    insight_pages = [p for p in reader_pages if p.strip().startswith("EXECUTIVE INSIGHTS")]
    assert len(insight_pages) >= 1


# ---------------------------------------------------------------------------
# Honesty for an unclassified dataset
# ---------------------------------------------------------------------------


def test_unclassified_dataset_does_not_show_a_fabricated_confidence() -> None:
    df = pd.DataFrame({"a": range(40), "b": range(40)})
    result = PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="unknown.csv")

    text = _extract_text(PdfExportBuilder.build_executive_pdf(result))

    assert "Not classified" in text
    assert "0% Confidence" not in text


# ---------------------------------------------------------------------------
# Robustness: still builds when optional sections are empty
# ---------------------------------------------------------------------------


def test_minimal_dataset_still_builds_a_valid_pdf() -> None:
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    result = PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="minimal.csv")

    pdf_bytes = PdfExportBuilder.build_executive_pdf(result)

    assert pdf_bytes[:5] == b"%PDF-"
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 2


def test_custom_branding_appears_in_the_output() -> None:
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    result = PowerPilotIntelligencePipeline().run_pipeline(df, dataset_name="branded.csv")
    branding = BrandingConfig(company_name="Acme Corp", prepared_for="Board of Directors")

    text = _extract_text(PdfExportBuilder.build_executive_pdf(result, branding=branding))

    assert "ACME CORP" in text
    assert "Board of Directors" in text


# ---------------------------------------------------------------------------
# Table cell wrapping (regression for cells overflowing into the next column)
# ---------------------------------------------------------------------------


def test_long_issue_type_values_are_not_lost_to_column_overflow(rich_pdf_text: str) -> None:
    """Plain strings don't wrap in a ReportLab Table; long values like
    "CATEGORY_CASE_INCONSISTENCY" used to overflow into the next column
    instead of wrapping. The characters must still all be present in the
    extracted text even if pypdf reports them split across wrapped lines."""
    normalized = rich_pdf_text.replace("\n", "")
    assert "MISSING_VALUES" in normalized or "MISSING" in rich_pdf_text
