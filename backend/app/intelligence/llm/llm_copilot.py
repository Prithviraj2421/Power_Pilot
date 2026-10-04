"""LLM-backed copilot, grounded in the pipeline's computed analysis.

Architecture, and why it is this shape:

The deterministic ``CopilotEngine`` cannot hallucinate, but it can only answer
the five intents it was written for, and it answers in templates. A language
model phrases well and handles arbitrary questions, but will invent a figure if
its context leaves room for one.

So the rule-based engine is kept as the retrieval layer and the model is given
only what the pipeline computed -- never the dataset. Three things then hold the
guarantee together:

* The context contains no raw data, so there is nothing to compute a new figure
  from.
* The system prompt forbids introducing numbers, and instructs the model to say
  when the analysis does not cover something.
* Every answer is checked by ``verifier.py`` before it is returned. Prompting is
  a request; the check is enforcement.

When no API key is configured, or the call fails, or the answer fails
verification, the deterministic engine answers instead. The response always
states which produced it, so a user is never left guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.common.logger import get_logger
from app.core.config import Settings, get_settings
from app.intelligence.copilot_engine import CopilotEngine, CopilotResponse
from app.intelligence.llm.grounding import SYSTEM_PROMPT, build_facts
from app.intelligence.llm.verifier import verify_citations
from app.models.master_intelligence_result import MasterIntelligenceResult

logger = get_logger("LlmCopilot")


@dataclass(slots=True, frozen=True)
class GroundedAnswer:
    """An answer plus the provenance a reader needs to judge it."""

    answer: str
    intent: str
    evidence: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    suggested_followups: tuple[str, ...]
    source: str  # "llm" | "rules"
    verified: bool
    verification_note: str
    fallback_reason: Optional[str] = None
    # Where each cited figure in ``answer`` came from: [{start, end, text, fact_id, label, value, unit}]
    citations: tuple[dict, ...] = ()

    @classmethod
    def from_rules(
        cls, response: CopilotResponse, fallback_reason: Optional[str] = None
    ) -> "GroundedAnswer":
        return cls(
            answer=response.answer,
            intent=response.intent,
            evidence=response.evidence,
            recommended_actions=response.recommended_actions,
            suggested_followups=response.suggested_followups,
            source="rules",
            # The deterministic engine only ever restates computed values, so its
            # numbers are grounded by construction.
            verified=True,
            verification_note="Answer composed directly from the computed analysis.",
            fallback_reason=fallback_reason,
        )


def make_anthropic_client(settings: Settings) -> Optional[Any]:
    """An Anthropic client for the configured key, or None (not installed, or construction failed)."""
    try:
        import anthropic
    except ImportError:
        logger.error(
            "LLM copilot is enabled but the 'anthropic' package is not installed. "
            "Install it with: pip install anthropic"
        )
        return None
    try:
        return anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=float(settings.llm_timeout_seconds),
        )
    except Exception as exc:  # pragma: no cover - constructor rarely raises
        logger.error(f"Could not construct the Anthropic client: {exc}")
        return None


class LlmCopilotService:
    """Answers questions with Claude, grounded in a dataset's analysis."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        rules_engine: Optional[CopilotEngine] = None,
        client: Optional[Any] = None,
    ) -> None:
        self._settings = get_settings() if settings is None else settings
        self._rules = CopilotEngine() if rules_engine is None else rules_engine
        self._client = client
        self._client_failed = False

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def _get_client(self) -> Optional[Any]:
        """Build the Anthropic client lazily, so an unconfigured server still boots."""
        if self._client is not None:
            return self._client
        if self._client_failed or not self.enabled:
            return None

        self._client = make_anthropic_client(self._settings)
        if self._client is None:
            self._client_failed = True
            return None

        return self._client

    def ask(self, query: str, result: MasterIntelligenceResult) -> GroundedAnswer:
        """Answer ``query`` about ``result``, falling back to rules when needed."""
        rules_response = self._rules.ask(query, result)

        if not self.enabled:
            return GroundedAnswer.from_rules(
                rules_response,
                fallback_reason="LLM answering is not configured on this server.",
            )

        client = self._get_client()
        if client is None:
            return GroundedAnswer.from_rules(
                rules_response, fallback_reason="The language model client is unavailable."
            )

        sheet = build_facts(result)

        try:
            answer_text = self._complete(client, query, sheet.text)
        except Exception as exc:
            logger.error(f"LLM call failed, answering from the deterministic engine: {exc}")
            return GroundedAnswer.from_rules(
                rules_response, fallback_reason=f"The language model call failed: {exc}"
            )

        if not answer_text.strip():
            return GroundedAnswer.from_rules(
                rules_response, fallback_reason="The language model returned an empty answer."
            )

        verification = verify_citations(answer_text, sheet.facts, query)
        if not verification.grounded:
            # An answer that states a figure absent from the analysis is exactly
            # what this feature exists to prevent, so it is discarded rather than
            # shown with a caveat.
            logger.warning(
                f"Discarded an LLM answer with ungrounded figures: {verification.summary}"
            )
            return GroundedAnswer.from_rules(
                rules_response,
                fallback_reason=(
                    "The generated answer contained figures that could not be tied to the right fact in the "
                    f"analysis ({', '.join(verification.unsupported_values)}), so the "
                    "verified deterministic answer is shown instead."
                ),
            )

        return GroundedAnswer(
            answer=verification.clean_text.strip(),
            intent=rules_response.intent,
            # Evidence stays from the deterministic engine: it is the actual
            # provenance, independent of how the answer was phrased.
            evidence=rules_response.evidence,
            recommended_actions=rules_response.recommended_actions,
            suggested_followups=rules_response.suggested_followups,
            source="llm",
            verified=True,
            verification_note=verification.summary,
            citations=tuple(self._trimmed(c, verification.clean_text) for c in verification.citations),
        )

    @staticmethod
    def _trimmed(citation: Any, clean_text: str) -> dict:
        """A citation as JSON, with offsets adjusted for the leading whitespace ``answer`` loses by being stripped."""
        shift = len(clean_text) - len(clean_text.lstrip())
        data = citation.to_dict()
        data["start"] -= shift
        data["end"] -= shift
        return data

    def _complete(self, client: Any, query: str, fact_sheet: str) -> str:
        """One Claude call. Returns the concatenated text blocks."""
        settings = self._settings

        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            # Adaptive thinking, at low effort: synthesizing an answer from a
            # prepared fact sheet is light reasoning, and this sits behind an
            # interactive chat box where latency is visible.
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            system=[
                # The rules never change, so they cache across every question
                # from every user.
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
                # The fact sheet is stable for a dataset, so follow-up questions
                # about the same dataset read it from cache too.
                {
                    "type": "text",
                    "text": f"Fact sheet for the dataset under discussion:\n\n{fact_sheet}",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": query}],
        )

        if getattr(response, "stop_reason", None) == "refusal":
            raise RuntimeError("the model declined to answer this request")

        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
