"""Tests for the dataset registry endpoints."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.common.enums import DatasetDomain


def _upload(client: TestClient, payload: bytes, filename: str = "retail.csv"):
    return client.post(
        "/api/v1/datasets",
        files={"file": (filename, io.BytesIO(payload), "text/csv")},
    )


def test_register_returns_201_with_dataset_id_and_result(
    client: TestClient, retail_csv_bytes: bytes
) -> None:
    response = _upload(client, retail_csv_bytes)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["dataset"]["dataset_id"]
    assert body["dataset"]["detected_domain"] == DatasetDomain.RETAIL.value
    assert body["result"]["dataset_profile"] is not None
    assert body["result"]["kpi_report"]["primary_kpis"]


def test_registered_metadata_reports_both_row_counts(
    client: TestClient, retail_csv_bytes: bytes
) -> None:
    dataset = _upload(client, retail_csv_bytes).json()["dataset"]

    assert dataset["original_rows"] == 61
    assert dataset["total_rows"] == 60
    assert dataset["rows_removed_by_cleaning"] == 1


def test_stored_path_is_never_exposed(client: TestClient, retail_csv_bytes: bytes) -> None:
    dataset = _upload(client, retail_csv_bytes).json()["dataset"]
    assert "stored_path" not in dataset


def test_register_rejects_non_csv_with_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets",
        files={"file": ("document.pdf", b"not a csv", "application/pdf")},
    )

    assert response.status_code == 400
    assert "must be a valid .csv file" in response.json()["detail"]


def test_register_rejects_empty_file_with_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets", files={"file": ("empty.csv", b"", "text/csv")}
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_register_rejects_header_only_csv_with_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets", files={"file": ("headers.csv", b"a,b,c\n", "text/csv")}
    )

    assert response.status_code == 400


def test_get_dataset_returns_metadata_without_recomputing(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.get(f"/api/v1/datasets/{registered_dataset_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["dataset_id"] == registered_dataset_id
    assert "analysis_cached" in body


def test_get_result_returns_the_full_analysis(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.get(f"/api/v1/datasets/{registered_dataset_id}/result")

    assert response.status_code == 200
    result = response.json()["result"]
    for section in (
        "dataset_profile",
        "quality_report",
        "preparation_report",
        "kpi_report",
        "dashboard_report",
        "decision_report",
        "insight_report",
        "relationship_report",
    ):
        assert result[section] is not None, f"{section} missing from restored analysis"


def test_unknown_dataset_id_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/datasets/deadbeef").status_code == 404
    assert client.get("/api/v1/datasets/deadbeef/result").status_code == 404
    assert client.delete("/api/v1/datasets/deadbeef").status_code == 404


def test_list_datasets_includes_registered_dataset(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.get("/api/v1/datasets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert registered_dataset_id in {item["dataset_id"] for item in body["datasets"]}


def test_list_datasets_respects_pagination_bounds(client: TestClient) -> None:
    assert client.get("/api/v1/datasets", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/datasets", params={"limit": 500}).status_code == 422
    assert client.get("/api/v1/datasets", params={"offset": -1}).status_code == 422


def test_identical_upload_reuses_the_same_dataset_id(
    client: TestClient, retail_csv_bytes: bytes
) -> None:
    first = _upload(client, retail_csv_bytes, "retail.csv").json()["dataset"]["dataset_id"]
    second = _upload(client, retail_csv_bytes, "retail_again.csv").json()["dataset"]["dataset_id"]

    assert first == second


def test_delete_removes_the_dataset(client: TestClient, retail_csv_bytes: bytes) -> None:
    # Use distinct content so deletion cannot affect other tests' shared dataset.
    payload = retail_csv_bytes + b"100999,2024-12-31,9,Lamp,Home,North,1,10.0,0.0,10.0,2.0\n"
    dataset_id = _upload(client, payload, "retail_delete_me.csv").json()["dataset"]["dataset_id"]

    assert client.delete(f"/api/v1/datasets/{dataset_id}").status_code == 200
    assert client.get(f"/api/v1/datasets/{dataset_id}").status_code == 404


def test_cache_stats_endpoint_is_not_shadowed_by_the_id_route(client: TestClient) -> None:
    """'/stats/cache' must not be parsed as a dataset id."""
    response = client.get("/api/v1/datasets/stats/cache")

    assert response.status_code == 200
    body = response.json()
    assert "registered_datasets" in body
    assert "hit_rate" in body["analysis_cache"]


def test_health_endpoint_reports_registry_state(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "registered_datasets" in body
    assert "analysis_cache" in body
