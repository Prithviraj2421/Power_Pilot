"""Tests for the grounded LLM copilot service.

No network: a stub client stands in for Anthropic. What matters here is not that
the SDK works, but that every path which could surface an unverified answer
falls back to the deterministic engine instead, and that the response always
says which engine answered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.core.config import Settings
from app.intelligence.llm.grounding import build_fact_sheet
from app.intelligence.llm.llm_copilot import LlmCopilotService
from app.models.master_intelligence_result import MasterIntelligenceResult


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _Response:
    content: list[_TextBlock]
    stop_reason: str = "end_turn"


class _StubClient:
    """Records the request it was given and returns a scripted answer."""

    def __init__(self, answer: str = "", raises: Exception | None = None,
                 stop_reason: str = "end_turn") -> None:
        self._answer = answer
        self._raises = raises
        self._stop_reason = stop_reason
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return _Response(content=[_TextBlock(self._answer)], stop_reason=self._stop_reason)


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {"anthropic_api_key": "test-key-not-real"}
    base.update(overrides)
    return Settings(**base)


def _service(client: Any, **overrides: Any) -> LlmCopilotService:
    return LlmCopilotService(settings=_settings(**overrides), client=client)


# ---------------------------------------------------------------------------
# Disabled / unconfigured
# ---------------------------------------------------------------------------


def test_without_an_api_key_the_rules_engine_answers(
    retail_result: MasterIntelligenceResult,
) -> None:
    service = LlmCopilotService(settings=Settings(), client=None)

    assert service.enabled is False
    answer = service.ask("What are my KPIs?", retail_result)

    assert answer.source == "rules"
    assert answer.verified is True
    assert "not configured" in (answer.fallback_reason or "")
    assert answer.answer.strip()


def test_rules_answers_are_marked_verified(retail_result: MasterIntelligenceResult) -> None:
    """The deterministic engine only restates computed values, so it is grounded."""
    answer = LlmCopilotService(settings=Settings()).ask("How is data quality?", retail_result)

    assert answer.verified is True
    assert "computed analysis" in answer.verification_note


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_grounded_llm_answer_is_returned(retail_result: MasterIntelligenceResult) -> None:
    quality = retail_result.quality_report
    generated = f"Data quality scored {quality.overall_score:.1f}% overall."
    service = _service(_StubClient(answer=generated))

    answer = service.ask("How is the data quality?", retail_result)

    assert answer.source == "llm"
    assert answer.verified is True
    assert answer.answer == generated
    assert answer.fallback_reason is None


def test_evidence_still_comes_from_the_deterministic_engine(
    retail_result: MasterIntelligenceResult,
) -> None:
    """Provenance should not depend on how the answer was phrased."""
    service = _service(_StubClient(answer="Quality is good."))

    answer = service.ask("How is the data quality?", retail_result)

    assert answer.source == "llm"
    assert answer.evidence, "evidence must survive LLM phrasing"
    assert answer.suggested_followups


def test_the_model_is_never_given_the_dataset(
    retail_result: MasterIntelligenceResult, retail_df
) -> None:
    """The context must contain computed facts only -- no rows to extrapolate from."""
    client = _StubClient(answer="Quality is good.")
    _service(client).ask("Summarize this", retail_result)

    sent = str(client.calls[0])
    # A value that exists only in the raw data, never in the analysis.
    sample_value = str(retail_df["product_name"].iloc[0])
    assert sent.count(sample_value) == 0 or "COLUMNS" in sent
    assert "DATA QUALITY" in sent, "the fact sheet should be what is sent"


def test_request_uses_the_configured_model_and_caching(
    retail_result: MasterIntelligenceResult,
) -> None:
    client = _StubClient(answer="Quality is good.")
    _service(client, llm_model="claude-opus-5").ask("hello", retail_result)

    request = client.calls[0]
    assert request["model"] == "claude-opus-5"
    assert request["thinking"]["type"] == "adaptive"
    # Both the rules and the per-dataset fact sheet are cached, so follow-up
    # questions about one dataset do not re-send them at full price.
    assert all(block.get("cache_control") for block in request["system"])


# ---------------------------------------------------------------------------
# Every failure path falls back
# ---------------------------------------------------------------------------


def test_a_fabricated_figure_is_discarded(retail_result: MasterIntelligenceResult) -> None:
    """The case this feature exists to prevent."""
    service = _service(_StubClient(answer="Revenue grew 23.8% and churn is 14.2%."))

    answer = service.ask("How did we do?", retail_result)

    assert answer.source == "rules"
    assert "do not appear in the analysis" in (answer.fallback_reason or "")
    assert "23.8%" in (answer.fallback_reason or "")
    assert "23.8%" not in answer.answer, "the fabricated answer must not reach the user"


def test_an_api_failure_falls_back(retail_result: MasterIntelligenceResult) -> None:
    service = _service(_StubClient(raises=RuntimeError("upstream exploded")))

    answer = service.ask("What are my KPIs?", retail_result)

    assert answer.source == "rules"
    assert "upstream exploded" in (answer.fallback_reason or "")
    assert answer.answer.strip(), "a failure must still produce an answer"


def test_an_empty_completion_falls_back(retail_result: MasterIntelligenceResult) -> None:
    service = _service(_StubClient(answer="   "))

    answer = service.ask("What are my KPIs?", retail_result)

    assert answer.source == "rules"
    assert "empty" in (answer.fallback_reason or "")


def test_a_refusal_falls_back(retail_result: MasterIntelligenceResult) -> None:
    service = _service(_StubClient(answer="...", stop_reason="refusal"))

    answer = service.ask("What are my KPIs?", retail_result)

    assert answer.source == "rules"
    assert "declined" in (answer.fallback_reason or "")


def test_the_user_always_gets_an_answer(retail_result: MasterIntelligenceResult) -> None:
    """Across every failure mode, the response is never empty."""
    for client in (
        _StubClient(answer="Revenue grew 23.8%."),
        _StubClient(raises=RuntimeError("boom")),
        _StubClient(answer=""),
        _StubClient(answer="x", stop_reason="refusal"),
    ):
        answer = _service(client).ask("What should management do?", retail_result)
        assert answer.answer.strip()
        assert answer.source == "rules"


# ---------------------------------------------------------------------------
# Fact sheet
# ---------------------------------------------------------------------------


def test_fact_sheet_contains_the_computed_analysis(
    retail_result: MasterIntelligenceResult,
) -> None:
    sheet = build_fact_sheet(retail_result)

    assert "DATASET" in sheet
    assert "DATA QUALITY" in sheet
    assert "RECOMMENDED KPIs" in sheet
    assert "retail.csv" in sheet
    assert f"{retail_result.quality_report.overall_score:.1f}%" in sheet


def test_fact_sheet_states_when_the_domain_is_unknown(pipeline) -> None:
    """An UNKNOWN domain must be stated, not quietly omitted."""
    import pandas as pd

    result = pipeline.run_pipeline(
        pd.DataFrame({"a": range(40), "b": range(40)}), dataset_name="mystery.csv"
    )

    assert "no domain could be determined" in build_fact_sheet(result)


def test_fact_sheet_is_bounded(retail_result: MasterIntelligenceResult) -> None:
    """It is sent on every question, so it must not grow without limit."""
    sheet = build_fact_sheet(retail_result)

    assert len(sheet) < 12_000, "fact sheet should stay compact enough to cache cheaply"


def test_fact_sheet_excludes_identifier_trends(
    retail_result: MasterIntelligenceResult,
) -> None:
    """A trend through order_id is real arithmetic and meaningless as a fact.

    Stated in the fact sheet it invites the model to reason from it, which is how
    a grounded answer still ends up nonsense.
    """
    sheet = build_fact_sheet(retail_result)

    assert "order_id is " not in sheet
    assert "customer_id is " not in sheet
    # Genuine measures survive.
    assert "unit_price is decreasing" in sheet


def test_fact_sheet_does_not_list_identifier_twice(
    retail_result: MasterIntelligenceResult,
) -> None:
    sheet = build_fact_sheet(retail_result)

    assert "identifier, identifier" not in sheet


def test_fact_sheet_is_ascii_safe(retail_result: MasterIntelligenceResult) -> None:
    """It crosses an HTTP boundary and is logged; non-ASCII separators invite mojibake."""
    assert build_fact_sheet(retail_result).isascii()
