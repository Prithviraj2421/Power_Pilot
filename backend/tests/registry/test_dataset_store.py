"""Tests for the durable dataset store (SQLite metadata + CSV file storage)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.datasets.store import DatasetStore, sha256_of

PAYLOAD = b"col_a,col_b\n1,2\n3,4\n"


@pytest.fixture
def store(tmp_path: Path) -> DatasetStore:
    return DatasetStore(db_path=tmp_path / "registry.sqlite3", datasets_dir=tmp_path / "datasets")


def _insert(store: DatasetStore, *, filename: str = "sample.csv", payload: bytes = PAYLOAD):
    return store.insert(
        filename=filename,
        payload=payload,
        original_rows=2,
        total_rows=2,
        total_columns=2,
        detected_domain="retail",
        domain_confidence=0.81,
        quality_grade="A",
        quality_score=94.5,
        quality_issues_count=3,
    )


def test_initialization_creates_database_and_dataset_directory(tmp_path: Path) -> None:
    store = DatasetStore(db_path=tmp_path / "nested" / "db.sqlite3", datasets_dir=tmp_path / "files")

    assert (tmp_path / "nested" / "db.sqlite3").exists()
    assert (tmp_path / "files").is_dir()
    assert store.count() == 0


def test_insert_persists_metadata_and_source_bytes(store: DatasetStore) -> None:
    record = _insert(store)

    assert record.dataset_id
    assert record.filename == "sample.csv"
    assert record.size_bytes == len(PAYLOAD)
    assert record.content_sha256 == sha256_of(PAYLOAD)
    assert Path(record.stored_path).read_bytes() == PAYLOAD
    assert store.count() == 1


def test_get_round_trips_every_field(store: DatasetStore) -> None:
    record = _insert(store)
    fetched = store.get(record.dataset_id)

    assert fetched == record


def test_get_unknown_id_returns_none(store: DatasetStore) -> None:
    assert store.get("does-not-exist") is None


def test_read_source_returns_original_bytes(store: DatasetStore) -> None:
    record = _insert(store)
    assert store.read_source(record.dataset_id) == PAYLOAD


def test_read_source_returns_none_when_file_was_removed(store: DatasetStore) -> None:
    record = _insert(store)
    Path(record.stored_path).unlink()

    assert store.read_source(record.dataset_id) is None, (
        "a missing source file must be reported, not raised, so the service can "
        "turn it into a clear 404"
    )


def test_find_by_content_hash_locates_identical_content(store: DatasetStore) -> None:
    record = _insert(store)

    found = store.find_by_content_hash(sha256_of(PAYLOAD))
    assert found is not None and found.dataset_id == record.dataset_id
    assert store.find_by_content_hash(sha256_of(b"different,bytes\n1,2\n")) is None


def test_delete_removes_row_and_source_file(store: DatasetStore) -> None:
    record = _insert(store)
    source = Path(record.stored_path)

    assert store.delete(record.dataset_id) is True
    assert store.get(record.dataset_id) is None
    assert not source.exists()
    assert store.count() == 0


def test_delete_unknown_id_reports_false(store: DatasetStore) -> None:
    assert store.delete("does-not-exist") is False


def test_delete_succeeds_even_if_source_file_is_already_gone(store: DatasetStore) -> None:
    record = _insert(store)
    Path(record.stored_path).unlink()

    assert store.delete(record.dataset_id) is True
    assert store.count() == 0


def test_list_recent_orders_newest_first_and_paginates(store: DatasetStore) -> None:
    ids = [
        _insert(store, filename=f"file-{index}.csv", payload=f"a,b\n{index},{index}\n".encode()).dataset_id
        for index in range(5)
    ]

    listed = store.list_recent(limit=50)
    assert len(listed) == 5
    assert [record.dataset_id for record in listed][0] in ids

    page = store.list_recent(limit=2, offset=0)
    next_page = store.list_recent(limit=2, offset=2)
    assert len(page) == 2 and len(next_page) == 2
    assert {r.dataset_id for r in page}.isdisjoint({r.dataset_id for r in next_page})


def test_touch_updates_last_accessed(store: DatasetStore) -> None:
    record = _insert(store)
    store.touch(record.dataset_id)

    refreshed = store.get(record.dataset_id)
    assert refreshed is not None
    assert refreshed.last_accessed_at >= record.last_accessed_at


def test_prune_removes_least_recently_accessed_beyond_limit(store: DatasetStore) -> None:
    records = [
        _insert(store, filename=f"file-{index}.csv", payload=f"a,b\n{index},{index}\n".encode())
        for index in range(5)
    ]
    # Make the first record the most recently accessed so it survives pruning.
    store.touch(records[0].dataset_id)

    removed = store.prune(max_datasets=2)

    assert len(removed) == 3
    assert store.count() == 2
    assert store.get(records[0].dataset_id) is not None


def test_prune_is_a_noop_when_under_the_limit(store: DatasetStore) -> None:
    _insert(store)
    assert store.prune(max_datasets=10) == []
    assert store.count() == 1


def test_prune_disabled_when_limit_is_zero_or_negative(store: DatasetStore) -> None:
    for index in range(3):
        _insert(store, filename=f"f{index}.csv", payload=f"a\n{index}\n".encode())

    assert store.prune(max_datasets=0) == []
    assert store.prune(max_datasets=-1) == []
    assert store.count() == 3


def test_record_to_dict_hides_server_path_and_derives_rows_removed(store: DatasetStore) -> None:
    record = store.insert(
        filename="sample.csv",
        payload=PAYLOAD,
        original_rows=61,
        total_rows=60,
        total_columns=11,
        detected_domain="retail",
        domain_confidence=0.8,
        quality_grade="A",
        quality_score=93.0,
        quality_issues_count=8,
    )

    payload = record.to_dict()
    assert "stored_path" not in payload, "server filesystem paths must not reach clients"
    assert payload["rows_removed_by_cleaning"] == 1
    assert payload["original_rows"] == 61
    assert payload["total_rows"] == 60
