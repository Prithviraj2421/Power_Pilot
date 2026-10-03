import sqlite3

import pandas as pd
import pytest

from app.common.powerbi_names import dax_references
from app.datasets.service import DatasetService, InvalidDatasetError
from app.datasets.store import DatasetStore


def revenue(analysis):
    return next(k for k in analysis.result.kpi_report.all_kpis if k.name == "Total Sales Revenue")


def test_a_dataframe_registers_with_its_real_table_name(dataset_service: DatasetService, retail_df) -> None:
    analysis = dataset_service.register_dataframe(retail_df, "Sales Data", powerbi_table="Sales Data")

    record = analysis.record
    assert record.is_live_model and record.powerbi_table == "Sales Data" and record.verify_on == "source"
    assert record.filename == "Sales Data.csv"
    assert {t for t, _ in dax_references(revenue(analysis).formula)} == {"Sales Data"}
    assert record.to_dict()["powerbi_table"] == "Sales Data"
    assert "stored_path" not in record.to_dict()


def test_kpis_are_verified_on_the_rows_the_model_holds(dataset_service: DatasetService, retail_df) -> None:
    analysis = dataset_service.register_dataframe(retail_df, "Sales", powerbi_table="Sales")

    assert revenue(analysis).computed_value == pytest.approx(float(retail_df["sales_amount"].sum()))


def test_a_recompute_after_a_cache_miss_keeps_the_table_and_verification_mode(
    dataset_service: DatasetService, retail_df
) -> None:
    first = dataset_service.register_dataframe(retail_df, "Sales Data", powerbi_table="Sales Data")
    dataset_service._cache.invalidate(first.dataset_id)

    again = dataset_service.get_analysis(first.dataset_id)

    assert {t for t, _ in dax_references(revenue(again).formula)} == {"Sales Data"}
    assert revenue(again).computed_value == pytest.approx(revenue(first).computed_value)


def test_the_same_table_is_reused_but_an_upload_of_the_same_bytes_is_not(
    dataset_service: DatasetService, retail_df
) -> None:
    csv_bytes = retail_df.to_csv(index=False).encode("utf-8")
    upload = dataset_service.register(csv_bytes, "Sales Data.csv")
    live = dataset_service.register_dataframe(retail_df, "Sales Data", powerbi_table="Sales Data")
    live_again = dataset_service.register_dataframe(retail_df, "Sales Data", powerbi_table="Sales Data")

    assert live.dataset_id != upload.dataset_id, "an upload's formulas name a different table"
    assert live_again.dataset_id == live.dataset_id
    assert not upload.record.is_live_model


def test_a_different_table_with_identical_rows_is_its_own_dataset(dataset_service: DatasetService, retail_df) -> None:
    a = dataset_service.register_dataframe(retail_df, "Orders", powerbi_table="Orders")
    b = dataset_service.register_dataframe(retail_df, "Archive", powerbi_table="Archive")

    assert a.dataset_id != b.dataset_id


def test_an_empty_table_is_rejected(dataset_service: DatasetService) -> None:
    with pytest.raises(InvalidDatasetError):
        dataset_service.register_dataframe(pd.DataFrame({"a": []}), "T", powerbi_table="T")


def test_a_registry_created_before_these_columns_existed_is_migrated(tmp_path) -> None:
    db = tmp_path / "registry.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """CREATE TABLE datasets (dataset_id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL, content_sha256 TEXT NOT NULL, original_rows INTEGER NOT NULL,
            total_rows INTEGER NOT NULL, total_columns INTEGER NOT NULL, detected_domain TEXT NOT NULL,
            domain_confidence REAL NOT NULL, quality_grade TEXT NOT NULL, quality_score REAL NOT NULL,
            quality_issues_count INTEGER NOT NULL, created_at TEXT NOT NULL, last_accessed_at TEXT NOT NULL,
            source_encoding TEXT NOT NULL DEFAULT 'utf-8', source_delimiter TEXT NOT NULL DEFAULT ',',
            source_file_format TEXT NOT NULL DEFAULT 'csv', source_sheet TEXT);
            INSERT INTO datasets VALUES ('old','a.csv','x',1,'h',1,1,1,'retail',0.9,'A',90,0,'t','t','utf-8',',','csv',NULL);"""
        )

    store = DatasetStore(db_path=db, datasets_dir=tmp_path / "datasets")
    record = store.get("old")

    assert record.powerbi_table is None and record.verify_on == "cleaned" and not record.is_live_model
