from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.routes.powerbi_live_route as route
from app.core.config import Settings
from app.main import app
from app.powerbi_live.connector import ModelConnectionError
from app.powerbi_live.service import LiveModelService
from tests.powerbi_live.fake_connector import FakeConnector

BASE = "/api/v1/powerbi-live"
TOKEN = "s3cret-token"
TABLE = "Sales Data"


def live_settings(**overrides) -> Settings:
    values = {"pbi_server": "localhost:51234", "pbi_database": "abc-123", "pbi_token": TOKEN}
    return Settings(**{**values, **overrides})


@pytest.fixture
def connector(retail_df: pd.DataFrame) -> FakeConnector:
    return FakeConnector({TABLE: retail_df})


@pytest.fixture
def client(connector, dataset_service, monkeypatch) -> TestClient:
    service = LiveModelService(connector, dataset_service, max_rows=500_000)
    monkeypatch.setattr(route, "_build_service", lambda *args: service)
    app.dependency_overrides[route.get_live_settings] = lambda: live_settings()
    yield TestClient(app)
    app.dependency_overrides.clear()


HEADERS = {"X-PowerPilot-Token": TOKEN}


def first_kpi_id(client: TestClient) -> str:
    body = client.post(f"{BASE}/analyze", json={"tables": [TABLE]}, headers=HEADERS).json()
    return next(k["id"] for k in body["tables"][0]["kpis"] if k["name"] == "Total Sales Revenue")


# -- access control -----------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/status", "/analyze", "/apply-measures"])
def test_every_live_endpoint_needs_the_session_token(client: TestClient, path: str) -> None:
    send = client.get if path == "/status" else client.post
    kwargs = {} if path == "/status" else {"json": {"items": [{"table": TABLE, "kpi_id": "abc:def"}]} if "apply" in path else {}}

    assert send(f"{BASE}{path}", **kwargs).status_code == 401
    assert send(f"{BASE}{path}", headers={"X-PowerPilot-Token": "wrong"}, **kwargs).status_code == 401


def test_the_right_token_is_accepted(client: TestClient) -> None:
    response = client.get(f"{BASE}/status", headers=HEADERS)

    assert response.status_code == 200 and response.json()["connected"] is True


def test_without_a_launch_context_the_endpoints_say_there_is_no_open_model(client: TestClient) -> None:
    app.dependency_overrides[route.get_live_settings] = lambda: Settings(pbi_server="", pbi_database="")

    response = client.get(f"{BASE}/status", headers=HEADERS)

    assert response.status_code == 409 and "External Tools" in response.json()["detail"]


def test_an_empty_configured_token_never_matches_so_it_cannot_leave_the_endpoints_open(client: TestClient) -> None:
    app.dependency_overrides[route.get_live_settings] = lambda: live_settings(pbi_token="")

    assert client.get(f"{BASE}/status").status_code == 401
    assert client.get(f"{BASE}/status", headers={"X-PowerPilot-Token": ""}).status_code == 401


def test_a_malformed_model_address_in_the_launch_environment_is_a_clear_error(client: TestClient, monkeypatch) -> None:
    def bad(*args):
        raise ValueError("'evil.example:80' is not a local Power BI model address (expected localhost:<port>)")

    monkeypatch.setattr(route, "_build_service", bad)

    response = client.get(f"{BASE}/status", headers=HEADERS)

    assert response.status_code == 409 and "local Power BI model address" in response.json()["detail"]


def test_the_rest_of_the_api_does_not_need_the_token(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


# -- behaviour ----------------------------------------------------------------------------------


def test_analyze_then_apply_writes_a_verified_measure(client: TestClient, connector: FakeConnector) -> None:
    kpi_id = first_kpi_id(client)

    response = client.post(
        f"{BASE}/apply-measures", json={"items": [{"table": TABLE, "kpi_id": kpi_id}]}, headers=HEADERS
    )

    body = response.json()
    assert response.status_code == 200 and body["saved"] is True
    assert body["results"][0]["status"] == "written" and "Ctrl+S" in body["reminder"]
    assert [m.name for m in connector.measures] == ["Total Sales Revenue"]


def test_dry_run_through_the_api_writes_nothing(client: TestClient, connector: FakeConnector) -> None:
    kpi_id = first_kpi_id(client)

    body = client.post(
        f"{BASE}/apply-measures",
        json={"items": [{"table": TABLE, "kpi_id": kpi_id}], "dry_run": True},
        headers=HEADERS,
    ).json()

    assert body["dry_run"] is True and body["results"][0]["status"] == "verified" and connector.measures == []


def test_a_mismatch_is_reported_as_refused_with_both_values(client: TestClient, connector: FakeConnector) -> None:
    kpi_id = first_kpi_id(client)
    connector.engine_scale = 2.0

    result = client.post(
        f"{BASE}/apply-measures", json={"items": [{"table": TABLE, "kpi_id": kpi_id}]}, headers=HEADERS
    ).json()["results"][0]

    assert result["status"] == "refused"
    assert result["engine_value"] == pytest.approx(result["computed_value"] * 2)
    assert connector.measures == []


def test_a_lost_connection_is_a_502_with_a_readable_message(client: TestClient, connector: FakeConnector) -> None:
    def gone(*args, **kwargs):
        raise ModelConnectionError("Could not read table 'Sales Data': Power BI Desktop's model is not reachable.")

    connector.read_table = gone

    response = client.post(f"{BASE}/analyze", json={"tables": [TABLE]}, headers=HEADERS)

    assert response.status_code == 502 and "not reachable" in response.json()["detail"]


# -- input validation ---------------------------------------------------------------------------


def test_dax_is_never_accepted_from_the_client(client: TestClient, connector: FakeConnector) -> None:
    payload = {"items": [{"table": TABLE, "kpi_id": "abc:def", "formula": "1"}], "dax": "EVALUATE x"}

    response = client.post(f"{BASE}/apply-measures", json=payload, headers=HEADERS)

    assert response.status_code == 422
    assert connector.queries == [] and connector.measures == []


@pytest.mark.parametrize(
    "payload",
    [
        {"items": []},
        {"items": [{"table": "", "kpi_id": "abc:def"}]},
        {"items": [{"table": TABLE, "kpi_id": "x"}]},
        {"items": [{"table": TABLE, "kpi_id": "abc:def"}] * 51},
        {"items": "all"},
        {},
    ],
)
def test_malformed_apply_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post(f"{BASE}/apply-measures", json=payload, headers=HEADERS).status_code == 422


@pytest.mark.parametrize("payload", [{"max_rows": 10}, {"max_rows": 10_000_000}, {"tables": "Sales"}, {"model": "x"}])
def test_malformed_analyze_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post(f"{BASE}/analyze", json=payload, headers=HEADERS).status_code == 422
