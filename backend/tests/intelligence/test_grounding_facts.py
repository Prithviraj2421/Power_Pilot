"""The fact sheet gives every number an id and a meaning, so a citation can be checked against what it stands for."""

from __future__ import annotations

import re

from app.intelligence.llm.facts import TAG, find_numbers, is_trivial
from app.intelligence.llm.grounding import SYSTEM_PROMPT, build_fact_sheet, build_facts
from app.models.master_intelligence_result import MasterIntelligenceResult


def test_every_fact_id_in_the_text_is_defined_and_unique(retail_result: MasterIntelligenceResult) -> None:
    sheet = build_facts(retail_result)
    in_text = [i for m in TAG.finditer(sheet.text) for i in re.findall(r"F\d+", m.group(1))]

    assert len(in_text) == len(set(in_text)), "an id must name exactly one number"
    assert set(in_text) == set(sheet.facts)
    assert all(fact.id == key for key, fact in sheet.facts.items())


def test_no_bare_number_is_left_for_the_model_to_cite_without_an_id(retail_result: MasterIntelligenceResult) -> None:
    """Outside the DAX formulas (which are code, not findings), every non-trivial number is followed by its tag."""
    sheet = build_facts(retail_result)
    untagged = []
    for line in sheet.text.splitlines():
        line = re.sub(r"\| DAX: .*?(?= \| |$)", "", line)
        for mention in find_numbers(line):
            if is_trivial(mention):
                continue
            if not re.match(r"\s?\[F\d+", line[mention.end :]):
                untagged.append((mention.token, line.strip()[:90]))
    assert untagged == []


def test_facts_carry_a_meaning_a_unit_and_the_real_value(retail_result: MasterIntelligenceResult) -> None:
    sheet = build_facts(retail_result)
    by_key = {f.key: f for f in sheet.facts.values()}
    profile = retail_result.dataset_profile

    rows = by_key["dataset.rows"]
    assert (rows.value, rows.unit, rows.label) == (profile.total_rows, "count", "Number of rows in the dataset")
    quality = by_key["quality.overall_score"]
    assert quality.unit == "percent" and quality.value == retail_result.quality_report.overall_score
    assert f"{rows.value:.0f} [{rows.id}] rows" in sheet.text


def test_kpi_values_are_facts_with_their_own_names(retail_result: MasterIntelligenceResult) -> None:
    """The old sheet described each KPI but never stated its computed value."""
    sheet = build_facts(retail_result)
    values = {f.label: f for f in sheet.facts.values() if f.key.startswith("kpi.") and f.key.endswith(".value")}

    assert values
    for kpi in retail_result.kpi_report.primary_kpis[:5]:
        if kpi.computed_value is not None:
            fact = values[f"{kpi.name} (KPI value)"]
            assert fact.value == kpi.computed_value
    money = [f for f in values.values() if "Revenue" in f.label or "Sales" in f.label]
    assert money and all(f.unit == "currency" for f in money)


def test_free_text_findings_are_tagged_with_the_finding_they_came_from(retail_result: MasterIntelligenceResult) -> None:
    sheet = build_facts(retail_result)
    insight_facts = [f for f in sheet.facts.values() if f.label.startswith("Insight: ")]
    assert insight_facts or any("Executive summary" == f.label for f in sheet.facts.values())


def test_the_text_helper_still_returns_the_readable_sheet(retail_result: MasterIntelligenceResult) -> None:
    text = build_fact_sheet(retail_result)
    assert text == build_facts(retail_result).text and "DATASET" in text and "RECOMMENDED KPIs" in text


def test_the_prompt_demands_a_citation_beside_every_number() -> None:
    assert "[F12]" in SYSTEM_PROMPT and "immediately after the number" in SYSTEM_PROMPT
    assert "never cite a" in SYSTEM_PROMPT.lower() and "question need no citation" in SYSTEM_PROMPT
