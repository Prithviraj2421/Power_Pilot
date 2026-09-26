"""Tests for the Power BI asset generation endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/api/v1/export/powerbi"


def test_status_endpoint_advertises_the_dataset_id_routes(client: TestClient) -> None:
    response = client.get(f"{BASE}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert "{dataset_id}" in body["endpoints"]["dax"]


def test_dax_export_returns_measure_script(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/dax")

    assert response.status_code == 200
    script = response.text
    assert script.strip()
    assert "=" in script, "a DAX measure script should contain measure definitions"


def test_dax_script_reflects_the_datasets_kpis(
    client: TestClient, registered_dataset_id: str
) -> None:
    kpis = client.get(f"/api/v1/datasets/{registered_dataset_id}/result").json()[
        "result"
    ]["kpi_report"]["primary_kpis"]
    script = client.post(f"{BASE}/{registered_dataset_id}/dax").text

    assert kpis, "the retail sample should produce primary KPIs"
    matched = sum(1 for kpi in kpis if kpi["name"].split()[0].lower() in script.lower())
    assert matched > 0, "the generated script should mention the dataset's own KPIs"


def test_bim_export_returns_a_tabular_model_schema(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/bim")

    assert response.status_code == 200
    bim = response.json()
    assert isinstance(bim, dict)
    assert "model" in bim, "a .bim schema is rooted at a 'model' object"
    assert bim["model"]["tables"], "the model should define at least one table"


def test_bim_columns_match_the_dataset_profile(
    client: TestClient, registered_dataset_id: str
) -> None:
    profile = client.get(f"/api/v1/datasets/{registered_dataset_id}/result").json()[
        "result"
    ]["dataset_profile"]
    bim = client.post(f"{BASE}/{registered_dataset_id}/bim").json()

    bim_columns = {col["name"] for table in bim["model"]["tables"] for col in table["columns"]}
    profile_columns = {col["name"] for col in profile["columns"]}
    assert profile_columns <= bim_columns, "every profiled column should appear in the model"


def test_power_query_m_export_returns_m_code(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/m")

    assert response.status_code == 200
    script = response.text
    assert "let" in script and "in" in script, "M code is a let/in expression"


def test_every_asset_endpoint_rejects_an_unknown_dataset_id(client: TestClient) -> None:
    for endpoint in ("dax", "bim", "m"):
        response = client.post(f"{BASE}/deadbeef/{endpoint}")
        assert response.status_code == 404, f"{endpoint} should 404 on an unknown id"


def test_all_three_assets_from_one_registration(
    client: TestClient, registered_dataset_id: str
) -> None:
    """One upload, three Power BI artifacts -- previously three full pipeline runs."""
    for endpoint in ("dax", "bim", "m"):
        assert client.post(f"{BASE}/{registered_dataset_id}/{endpoint}").status_code == 200
