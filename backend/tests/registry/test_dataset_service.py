"""Tests for DatasetService: validation, registration, caching and rehydration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.core.config import Settings
from app.datasets.service import (
    DatasetNotFoundError,
    DatasetService,
    InvalidDatasetError,
)
from app.datasets.store import DatasetStore

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_an_unsupported_extension_with_actionable_advice(
    dataset_service: DatasetService,
) -> None:
    """A refusal should name the fix, not just say no."""
    with pytest.raises(InvalidDatasetError, match="Export the underlying table"):
        dataset_service.parse_csv(b"a,b\n1,2\n", "report.pdf")

    with pytest.raises(InvalidDatasetError, match="save it as .xlsx or CSV"):
        dataset_service.parse_csv(b"a,b\n1,2\n", "legacy.xls")


def test_rejects_an_unknown_extension_by_listing_supported_formats(
    dataset_service: DatasetService,
) -> None:
    with pytest.raises(InvalidDatasetError, match="Supported formats"):
        dataset_service.parse_csv(b"a,b\n1,2\n", "mystery.dat")


def test_rejects_empty_payload(dataset_service: DatasetService) -> None:
    with pytest.raises(InvalidDatasetError, match="empty"):
        dataset_service.parse_csv(b"", "empty.csv")


def test_rejects_payload_over_the_configured_size_limit(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, max_upload_mb=1)
    service = DatasetService(
        store=DatasetStore(
            db_path=settings.registry_db_path, datasets_dir=settings.datasets_path
        ),
        settings=settings,
    )

    oversized = b"col_a,col_b\n" + (b"1,2\n" * 300_000)
    assert len(oversized) > settings.max_upload_bytes

    with pytest.raises(InvalidDatasetError, match="exceeds maximum limit of 1MB"):
        service.parse_csv(oversized, "big.csv")


def test_accepts_payload_just_under_the_size_limit(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, max_upload_mb=1)
    service = DatasetService(
        store=DatasetStore(
            db_path=settings.registry_db_path, datasets_dir=settings.datasets_path
        ),
        settings=settings,
    )

    header = b"col_a,col_b\n"
    row = b"1,2\n"
    rows = (settings.max_upload_bytes - len(header)) // len(row) - 10
    payload = header + row * rows
    assert len(payload) < settings.max_upload_bytes

    df = service.parse_csv(payload, "just_under.csv")
    assert len(df) == rows


def test_rejects_csv_with_no_parseable_header(dataset_service: DatasetService) -> None:
    with pytest.raises(InvalidDatasetError, match="no parseable columns"):
        dataset_service.parse_csv(b"\n", "blank.csv")


def test_rejects_header_only_csv_with_no_rows(dataset_service: DatasetService) -> None:
    with pytest.raises(InvalidDatasetError, match="at least one column with valid data rows"):
        dataset_service.parse_csv(b"col_a,col_b\n", "header_only.csv")


def test_accepts_a_valid_csv(dataset_service: DatasetService) -> None:
    df = dataset_service.parse_csv(b"col_a,col_b\n1,2\n3,4\n", "ok.csv")
    assert list(df.columns) == ["col_a", "col_b"]
    assert len(df) == 2


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_returns_analysis_with_metadata_and_cleaned_frame(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    assert analysis.dataset_id
    assert analysis.record.filename == "retail.csv"
    assert analysis.record.detected_domain == DatasetDomain.RETAIL.value
    assert analysis.record.domain_confidence > 0.5
    assert analysis.result.dataset_profile is not None
    assert isinstance(analysis.cleaned_dataframe, pd.DataFrame)


def test_register_records_both_original_and_cleaned_row_counts(
    dataset_service: DatasetService, retail_csv_bytes: bytes, retail_df: pd.DataFrame
) -> None:
    """The retail sample carries one exact duplicate row, which cleaning removes."""
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    assert analysis.record.original_rows == len(retail_df)
    assert analysis.record.total_rows == len(retail_df) - 1
    assert analysis.record.to_dict()["rows_removed_by_cleaning"] == 1


def test_cleaned_frame_is_actually_cleaned_not_the_raw_upload(
    dataset_service: DatasetService, retail_csv_bytes: bytes, retail_df: pd.DataFrame
) -> None:
    """Guards the bug where exports labelled 'cleaned' shipped the raw upload."""
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    assert retail_df.duplicated().sum() == 1, "fixture should start with one duplicate"
    assert analysis.cleaned_dataframe.duplicated().sum() == 0
    assert len(analysis.cleaned_dataframe) < len(retail_df)


def test_register_persists_the_dataset_for_later_retrieval(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    assert dataset_service.count_datasets() == 1
    assert dataset_service.get_record(analysis.dataset_id).dataset_id == analysis.dataset_id


def test_identical_content_is_deduplicated(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    first = dataset_service.register(retail_csv_bytes, "retail.csv")
    second = dataset_service.register(retail_csv_bytes, "retail_renamed.csv")

    assert second.dataset_id == first.dataset_id
    assert dataset_service.count_datasets() == 1, "identical bytes must not create a second dataset"


def test_deduplication_can_be_disabled(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    first = dataset_service.register(retail_csv_bytes, "retail.csv")
    second = dataset_service.register(retail_csv_bytes, "retail.csv", reuse_identical=False)

    assert second.dataset_id != first.dataset_id
    assert dataset_service.count_datasets() == 2


def test_different_content_creates_separate_datasets(
    dataset_service: DatasetService, datasets_dir: Path
) -> None:
    retail = dataset_service.register((datasets_dir / "retail.csv").read_bytes(), "retail.csv")
    finance = dataset_service.register((datasets_dir / "finance.csv").read_bytes(), "finance.csv")

    assert retail.dataset_id != finance.dataset_id
    assert retail.record.detected_domain == DatasetDomain.RETAIL.value
    assert finance.record.detected_domain == DatasetDomain.FINANCE.value
    assert dataset_service.count_datasets() == 2


# ---------------------------------------------------------------------------
# Retrieval, caching and rehydration
# ---------------------------------------------------------------------------


def test_registration_warms_the_cache(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")
    assert dataset_service.is_cached(analysis.dataset_id)


def test_cached_retrieval_reuses_the_same_result_object(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    registered = dataset_service.register(retail_csv_bytes, "retail.csv")
    fetched = dataset_service.get_analysis(registered.dataset_id)

    assert fetched.result is registered.result, "a cache hit must not recompute the analysis"


def test_analysis_is_recomputed_from_stored_csv_after_eviction(
    small_cache_service: DatasetService, datasets_dir: Path
) -> None:
    """The cache is a performance layer: losing an entry must never lose a dataset."""
    service = small_cache_service
    retail = service.register((datasets_dir / "retail.csv").read_bytes(), "retail.csv")

    # The single-entry cache evicts retail when the second dataset is registered.
    service.register((datasets_dir / "finance.csv").read_bytes(), "finance.csv")
    assert not service.is_cached(retail.dataset_id)

    rehydrated = service.get_analysis(retail.dataset_id)

    assert rehydrated.result is not retail.result, "expected a fresh recomputation"
    assert rehydrated.record.dataset_id == retail.dataset_id
    assert rehydrated.record.detected_domain == DatasetDomain.RETAIL.value
    assert rehydrated.record.total_rows == retail.record.total_rows
    assert list(rehydrated.cleaned_dataframe.columns) == list(retail.cleaned_dataframe.columns)
    assert len(rehydrated.cleaned_dataframe) == len(retail.cleaned_dataframe)


def test_rehydration_reproduces_the_same_analysis_values(
    small_cache_service: DatasetService, datasets_dir: Path
) -> None:
    """The pipeline is deterministic, so a recomputed analysis must match the original."""
    service = small_cache_service
    original = service.register((datasets_dir / "retail.csv").read_bytes(), "retail.csv")
    original_domain = original.result.dataset_profile.detected_domain
    original_grade = original.result.quality_report.grade
    original_kpis = [kpi.name for kpi in original.result.kpi_report.primary_kpis]

    service.register((datasets_dir / "hr.csv").read_bytes(), "hr.csv")  # forces eviction
    rehydrated = service.get_analysis(original.dataset_id)

    assert rehydrated.result.dataset_profile.detected_domain == original_domain
    assert rehydrated.result.quality_report.grade == original_grade
    assert [kpi.name for kpi in rehydrated.result.kpi_report.primary_kpis] == original_kpis


def test_unknown_dataset_id_raises_not_found(dataset_service: DatasetService) -> None:
    with pytest.raises(DatasetNotFoundError, match="No dataset registered"):
        dataset_service.get_analysis("deadbeef")

    with pytest.raises(DatasetNotFoundError):
        dataset_service.get_record("deadbeef")


def test_missing_source_file_raises_a_clear_not_found(
    small_cache_service: DatasetService, datasets_dir: Path
) -> None:
    service = small_cache_service
    analysis = service.register((datasets_dir / "retail.csv").read_bytes(), "retail.csv")

    # Evict the cached analysis, then delete the file it would be rebuilt from.
    service.register((datasets_dir / "hr.csv").read_bytes(), "hr.csv")
    Path(service.get_record(analysis.dataset_id).stored_path).unlink()

    with pytest.raises(DatasetNotFoundError, match="stored source file is missing"):
        service.get_analysis(analysis.dataset_id)


def test_get_source_dataframe_returns_the_uncleaned_upload(
    dataset_service: DatasetService, retail_csv_bytes: bytes, retail_df: pd.DataFrame
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")
    source = dataset_service.get_source_dataframe(analysis.dataset_id)

    assert len(source) == len(retail_df), "source must still include the duplicate row"
    assert source.duplicated().sum() == 1


# ---------------------------------------------------------------------------
# Management
# ---------------------------------------------------------------------------


def test_list_datasets_returns_registered_records(
    dataset_service: DatasetService, datasets_dir: Path
) -> None:
    for name in ("retail.csv", "finance.csv", "hr.csv"):
        dataset_service.register((datasets_dir / name).read_bytes(), name)

    listed = dataset_service.list_datasets()
    assert len(listed) == 3
    assert {record.filename for record in listed} == {"retail.csv", "finance.csv", "hr.csv"}


def test_delete_removes_dataset_and_invalidates_cache(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    dataset_service.delete(analysis.dataset_id)

    assert not dataset_service.is_cached(analysis.dataset_id)
    assert dataset_service.count_datasets() == 0
    with pytest.raises(DatasetNotFoundError):
        dataset_service.get_analysis(analysis.dataset_id)


def test_delete_unknown_dataset_raises_not_found(dataset_service: DatasetService) -> None:
    with pytest.raises(DatasetNotFoundError):
        dataset_service.delete("deadbeef")


def test_cache_stats_are_reported(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")
    dataset_service.get_analysis(analysis.dataset_id)

    stats = dataset_service.cache_stats()
    assert stats["hits"] >= 1
    assert stats["entries"] == 1


# ---------------------------------------------------------------------------
# Source format is recorded on the dataset
# ---------------------------------------------------------------------------


def test_utf8_comma_upload_is_recorded_as_defaults(
    dataset_service: DatasetService, retail_csv_bytes: bytes
) -> None:
    analysis = dataset_service.register(retail_csv_bytes, "retail.csv")

    assert analysis.record.source_encoding == "utf-8"
    assert analysis.record.source_delimiter == ","
    assert analysis.record.read_with_defaults is True


def test_semicolon_upload_records_the_delimiter(
    dataset_service: DatasetService, retail_df: pd.DataFrame
) -> None:
    """Semicolon separation is what European Excel produces."""
    text = retail_df.to_csv(index=False).replace(",", ";")
    analysis = dataset_service.register(text.encode("utf-8"), "euro_retail.csv")

    assert analysis.record.source_delimiter == ";"
    assert analysis.record.read_with_defaults is False
    assert analysis.record.source_format == "utf-8, semicolon-separated"
    # The point of recording it: the data still parsed into real columns.
    assert analysis.record.total_columns == len(retail_df.columns)


def test_cp1252_upload_records_the_encoding(dataset_service: DatasetService) -> None:
    """Encoding is only detectable once a byte differs from ASCII.

    A pure-ASCII file encoded as cp1252 is byte-identical to UTF-8, so it is
    correctly reported as utf-8 -- there is nothing to distinguish. The accented
    characters here are what make the difference observable, and are also the only
    case where getting the encoding wrong would corrupt the data.
    """
    text = "region;revenue\nMünchen;120\nOrléans;90\n"
    analysis = dataset_service.register(text.encode("cp1252"), "euro.csv")

    assert analysis.record.source_encoding == "cp1252"
    assert analysis.record.source_delimiter == ";"
    assert analysis.record.source_format == "cp1252, semicolon-separated"
    assert "München" in analysis.cleaned_dataframe["region"].tolist()


def test_bom_upload_records_the_bom_encoding(
    dataset_service: DatasetService, retail_df: pd.DataFrame
) -> None:
    payload = retail_df.to_csv(index=False).encode("utf-8-sig")
    analysis = dataset_service.register(payload, "bom_retail.csv")

    assert analysis.record.source_encoding == "utf-8-sig"
    assert analysis.record.read_with_defaults is False
    assert list(analysis.cleaned_dataframe.columns)[0] == retail_df.columns[0]
