"""Tests for the AI Copilot endpoint.

The copilot answers from a registered dataset's computed analysis. These tests
assert the answers are actually grounded in that dataset rather than generic
text, which is what distinguishes this from the placeholder it replaced.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

URL = "/api/v1/copilot/ask"


def _ask(client: TestClient, dataset_id: str, query: str):
    return client.post(URL, json={"dataset_id": dataset_id, "query": query})


def test_ask_returns_a_grounded_answer(client: TestClient, registered_dataset_id: str) -> None:
    response = _ask(client, registered_dataset_id, "What are my key KPIs?")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["dataset_id"] == registered_dataset_id
    assert body["dataset_name"] == "retail.csv"
    assert body["answer"].strip()
    assert body["intent"]


def test_answer_references_the_actual_dataset(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = _ask(client, registered_dataset_id, "Summarize this dataset")

    body = response.json()
    combined = (body["answer"] + " ".join(body["evidence"])).lower()
    assert "retail" in combined, "the answer should reflect the classified domain"


def test_response_carries_evidence_and_followups(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = _ask(client, registered_dataset_id, "Why did profit decrease?")

    body = response.json()
    assert isinstance(body["evidence"], list)
    assert isinstance(body["recommended_actions"], list)
    assert isinstance(body["suggested_followups"], list)
    assert body["evidence"], "a grounded answer should cite something from the analysis"


def test_different_intents_are_routed_differently(
    client: TestClient, registered_dataset_id: str
) -> None:
    kpi_intent = _ask(client, registered_dataset_id, "Show me the DAX measures").json()["intent"]
    action_intent = _ask(client, registered_dataset_id, "What should we do next?").json()["intent"]

    assert kpi_intent != action_intent, "distinct questions should resolve to distinct intents"


def test_repeated_questions_do_not_require_reuploading(
    client: TestClient, registered_dataset_id: str
) -> None:
    for question in (
        "What are my KPIs?",
        "Break down sales by region",
        "What management actions do you recommend?",
        "Why did revenue drop?",
    ):
        assert _ask(client, registered_dataset_id, question).status_code == 200


def test_unknown_dataset_id_returns_404(client: TestClient) -> None:
    assert _ask(client, "deadbeef", "What are my KPIs?").status_code == 404


def test_missing_fields_are_rejected(client: TestClient, registered_dataset_id: str) -> None:
    assert client.post(URL, json={"query": "hello"}).status_code == 422
    assert client.post(URL, json={"dataset_id": registered_dataset_id}).status_code == 422


def test_blank_query_is_rejected(client: TestClient, registered_dataset_id: str) -> None:
    response = client.post(URL, json={"dataset_id": registered_dataset_id, "query": ""})
    assert response.status_code == 422


def test_overlong_query_is_rejected(client: TestClient, registered_dataset_id: str) -> None:
    response = client.post(
        URL, json={"dataset_id": registered_dataset_id, "query": "x" * 2001}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Engine provenance
# ---------------------------------------------------------------------------


def test_status_reports_the_deterministic_engine_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/copilot/status")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_enabled"] is False
    assert body["engine"] == "rules"
    assert "POWERPILOT_ANTHROPIC_API_KEY" in body["detail"]


def test_status_never_returns_the_api_key_value(client: TestClient) -> None:
    """Naming the env var is helpful; leaking its value is not."""
    from app.core.config import Settings, get_settings
    from app.main import app

    secret = "sk-ant-secret-value-must-not-leak"
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=get_settings().data_dir, anthropic_api_key=secret
    )
    try:
        body = client.get("/api/v1/copilot/status").json()
        assert body["llm_enabled"] is True
        assert body["engine"] == "llm"
        assert secret not in str(body)
        assert "anthropic_api_key" not in body
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_answers_declare_which_engine_produced_them(
    client: TestClient, registered_dataset_id: str
) -> None:
    """A reader should never have to guess whether an answer was generated."""
    response = _ask(client, registered_dataset_id, "How is the data quality?")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] in ("rules", "llm")
    assert body["verified"] is True
    assert body["verification_note"]


def test_a_cited_llm_answer_comes_back_clean_with_its_citations(client: TestClient, registered_dataset_id: str) -> None:
    """The model's [F12] tags never reach the page; the figures they pointed at are returned as citations."""
    from types import SimpleNamespace

    from app.core.config import Settings
    from app.datasets.service import get_dataset_service
    from app.intelligence.llm.grounding import build_facts
    from app.intelligence.llm.llm_copilot import LlmCopilotService
    from app.main import app
    from app.routes.copilot_route import get_copilot_service

    analysis = get_dataset_service().get_analysis(registered_dataset_id)
    rows = next(f for f in build_facts(analysis.result).facts.values() if f.key == "dataset.rows")
    reply = f"The dataset has {rows.value:,.0f} [{rows.id}] rows."
    stub = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: SimpleNamespace(
        content=[SimpleNamespace(type="text", text=reply)], stop_reason="end_turn")))
    app.dependency_overrides[get_copilot_service] = lambda: LlmCopilotService(settings=Settings(anthropic_api_key="k"), client=stub)
    try:
        body = _ask(client, registered_dataset_id, "How many rows?").json()
    finally:
        app.dependency_overrides.pop(get_copilot_service, None)

    assert body["source"] == "llm" and body["answer"] == f"The dataset has {rows.value:,.0f} rows."
    (citation,) = body["citations"]
    assert citation["fact_id"] == rows.id and citation["label"] == "Number of rows in the dataset" and citation["value"] == rows.value
    assert body["answer"][citation["start"] : citation["end"]] == f"{rows.value:,.0f}"


def test_rules_answers_have_no_citations(client: TestClient, registered_dataset_id: str) -> None:
    assert _ask(client, registered_dataset_id, "Summarize this dataset").json()["citations"] == []
