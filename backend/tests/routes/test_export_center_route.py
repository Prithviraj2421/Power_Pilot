"""Tests for the Export & Distribution Center endpoints.

Every export addresses a registered dataset by id. The cleaned-data tests in
particular guard a real bug: the previous implementation handed the raw upload to
a builder that assumes it received the cleaned frame, so downloads labelled
"cleaned" contained uncleaned rows.
"""

from __future__ import annotations

import io
import json

import pandas as pd
from fastapi.testclient import TestClient

BASE = "/api/v1/export-center"


def test_cleaned_csv_export_contains_the_cleaned_frame(
    client: TestClient, registered_dataset_id: str, retail_df: pd.DataFrame
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/cleaned-data", params={"format": "csv"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    exported = pd.read_csv(io.BytesIO(response.content))
    assert len(exported) == len(retail_df) - 1, "the duplicate row must be gone"
    assert exported.duplicated().sum() == 0

    # Numeric gaps are imputed (median strategy); the fixture's 2 missing profit
    # values come back filled.
    assert retail_df["profit"].isna().sum() == 2
    assert exported["profit"].isna().sum() == 0

    # KNOWN GAP: categorical gaps are NOT imputed -- the fixture's 3 missing
    # 'region' values survive cleaning. Asserted so the behavior is visible and
    # this test fails loudly if categorical imputation is added later.
    assert retail_df["region"].isna().sum() == 3
    assert exported["region"].isna().sum() == 3


def test_cleaned_csv_export_differs_from_the_raw_upload(
    client: TestClient, registered_dataset_id: str, retail_csv_bytes: bytes
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/cleaned-data", params={"format": "csv"})

    assert response.content != retail_csv_bytes, (
        "a 'cleaned' export identical to the upload means cleaning was not applied"
    )


def test_cleaned_excel_export_returns_a_workbook(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/cleaned-data", params={"format": "xlsx"})

    assert response.status_code == 200
    assert response.content[:2] == b"PK", "xlsx files are zip archives"
    assert "attachment" in response.headers["content-disposition"]


def test_cleaned_data_rejects_an_unsupported_format(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/cleaned-data", params={"format": "pdf"})
    assert response.status_code == 422


def test_pdf_export_returns_a_pdf(client: TestClient, registered_dataset_id: str) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"
    assert len(response.content) > 10_000, "an executive report should not be near-empty"


def test_pdf_export_accepts_branding_parameters(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/pdf",
        params={
            "company_name": "Contoso Ltd",
            "prepared_for": "Board of Directors",
            "prepared_by": "Analytics Team",
        },
    )

    assert response.status_code == 200
    assert response.content[:5] == b"%PDF-"


def test_docx_export_returns_a_word_document(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/docx")

    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert "wordprocessingml" in response.headers["content-type"]


def test_html_export_returns_a_standalone_document(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/html")

    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace").lower()
    assert "<html" in body


def test_json_export_is_parseable_and_carries_the_analysis(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/json")

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert isinstance(payload, dict)
    assert payload, "master JSON export should not be empty"


def test_data_dictionary_export_returns_a_workbook(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/data-dictionary")

    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_download_filenames_are_derived_from_the_dataset(
    client: TestClient, registered_dataset_id: str
) -> None:
    response = client.post(f"{BASE}/{registered_dataset_id}/pdf")

    disposition = response.headers["content-disposition"]
    assert "retail" in disposition
    assert ".csv.pdf" not in disposition, "the .csv extension should be stripped, not stacked"


def test_every_export_rejects_an_unknown_dataset_id(client: TestClient) -> None:
    for endpoint in ("cleaned-data", "pdf", "docx", "html", "json", "data-dictionary"):
        response = client.post(f"{BASE}/deadbeef/{endpoint}")
        assert response.status_code == 404, f"{endpoint} should 404 on an unknown id"


def test_email_distribution_reports_not_implemented(
    client: TestClient, registered_dataset_id: str
) -> None:
    """It must not claim success: no SMTP delivery exists yet."""
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com"},
    )

    assert response.status_code == 501
    detail = response.json()["detail"]
    assert "not implemented" in detail.lower()
    assert "no message was sent" in detail.lower()


def test_export_history_records_completed_exports(
    client: TestClient, registered_dataset_id: str
) -> None:
    client.post(f"{BASE}/{registered_dataset_id}/json")

    response = client.get(f"{BASE}/history")
    assert response.status_code == 200
    history = response.json()["history"]
    assert history, "history should contain the export just performed"
    assert {"dataset_name", "export_format", "file_size_bytes", "timestamp"} <= set(history[0])


def test_repeated_exports_do_not_require_reuploading(
    client: TestClient, registered_dataset_id: str
) -> None:
    """Four different exports from one registration -- the point of the registry."""
    for endpoint in ("pdf", "docx", "json", "data-dictionary"):
        assert client.post(f"{BASE}/{registered_dataset_id}/{endpoint}").status_code == 200
