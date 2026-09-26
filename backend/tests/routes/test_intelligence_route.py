import io
from fastapi.testclient import TestClient
import pandas as pd
import pytest

from app.main import app

client = TestClient(app)


def test_analyze_csv_endpoint() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "customer_id": [101, 102, 103],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "sales_amount": [100.0, 200.0, 150.0],
            "quantity": [1, 2, 1],
        }
    )

    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    response = client.post(
        "/api/v1/intelligence/analyze-csv",
        files={"file": ("test_sales.csv", csv_buf, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["dataset_name"] == "test_sales.csv"
    assert data["summary"]["detected_entities_count"] >= 3
    assert data["summary"]["primary_kpis_count"] == 3
    assert data["summary"]["dashboard_tabs_count"] >= 2
    assert data["summary"]["primary_decisions_count"] >= 2

    # The analysis is registered, so the response hands back an id every
    # downstream endpoint can use instead of re-uploading the file.
    assert data["dataset_id"]
    assert data["dataset"]["dataset_id"] == data["dataset_id"]
    assert data["dataset"]["filename"] == "test_sales.csv"


def test_analyze_csv_registers_a_retrievable_dataset() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3, 4],
            "customer_id": [11, 12, 13, 14],
            "order_date": ["2024-03-01", "2024-03-02", "2024-03-03", "2024-03-04"],
            "sales_amount": [120.0, 340.0, 90.0, 275.0],
            "quantity": [1, 3, 1, 2],
        }
    )

    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    dataset_id = client.post(
        "/api/v1/intelligence/analyze-csv",
        files={"file": ("registered.csv", csv_buf, "text/csv")},
    ).json()["dataset_id"]

    # The same analysis is now addressable by id without another upload.
    restored = client.get(f"/api/v1/datasets/{dataset_id}/result")
    assert restored.status_code == 200
    assert restored.json()["result"]["kpi_report"]["primary_kpis"]


def test_analyze_non_csv_rejected() -> None:
    response = client.post(
        "/api/v1/intelligence/analyze-csv",
        files={"file": ("document.pdf", b"fake content", "application/pdf")},
    )

    assert response.status_code == 400
    assert "must be a valid .csv file" in response.json()["detail"]
