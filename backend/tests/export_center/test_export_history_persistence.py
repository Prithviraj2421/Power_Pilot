"""Tests for the SQLite-backed export history.

The point of the change is durability: this was a class-level Python list that
reset on every restart while the UI labelled it an "Export Audit History".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.export_center.models.export_models import ExportFormat
from app.export_center.services.export_history_service import ExportHistoryService


@pytest.fixture
def history_db(tmp_path: Path):
    """Point the service at a throwaway database and restore it afterwards."""
    original_path = ExportHistoryService._db_path
    ExportHistoryService.configure(tmp_path / "history.sqlite3")
    yield tmp_path / "history.sqlite3"
    if original_path is not None:
        ExportHistoryService.configure(original_path)
    else:
        ExportHistoryService._db_path = None
        ExportHistoryService._initialized = False


def _record(dataset_name: str = "retail.csv", dataset_id: str | None = "ds-1", **kwargs):
    defaults = dict(
        export_format=ExportFormat.EXECUTIVE_PDF,
        file_size_bytes=2048,
        duration_ms=123.456,
    )
    defaults.update(kwargs)
    return ExportHistoryService.record_export(
        dataset_name=dataset_name, dataset_id=dataset_id, **defaults
    )


def test_recorded_export_is_returned(history_db: Path) -> None:
    entry = _record()

    history = ExportHistoryService.get_history()
    assert len(history) == 1
    assert history[0].entry_id == entry.entry_id
    assert history[0].dataset_name == "retail.csv"
    assert history[0].export_format == ExportFormat.EXECUTIVE_PDF
    assert history[0].file_size_bytes == 2048


def test_duration_is_rounded_for_display(history_db: Path) -> None:
    _record(duration_ms=123.456789)
    assert ExportHistoryService.get_history()[0].duration_ms == 123.46


def test_history_survives_a_simulated_restart(history_db: Path) -> None:
    """The whole reason for the change: a restart must not erase the audit trail."""
    _record(dataset_name="finance.csv")

    # Drop every scrap of in-process state, as a fresh boot would.
    ExportHistoryService._initialized = False
    ExportHistoryService.configure(history_db)

    history = ExportHistoryService.get_history()
    assert len(history) == 1
    assert history[0].dataset_name == "finance.csv"


def test_history_is_ordered_newest_first(history_db: Path) -> None:
    for index in range(5):
        _record(dataset_name=f"file-{index}.csv")

    history = ExportHistoryService.get_history()
    assert [entry.dataset_name for entry in history] == [
        f"file-{index}.csv" for index in reversed(range(5))
    ]


def test_limit_caps_the_number_of_rows_returned(history_db: Path) -> None:
    for index in range(10):
        _record(dataset_name=f"file-{index}.csv")

    assert len(ExportHistoryService.get_history(limit=3)) == 3
    assert ExportHistoryService.count() == 10


def test_history_can_be_filtered_to_one_dataset(history_db: Path) -> None:
    _record(dataset_name="retail.csv", dataset_id="ds-retail")
    _record(dataset_name="retail.csv", dataset_id="ds-retail")
    _record(dataset_name="finance.csv", dataset_id="ds-finance")

    assert ExportHistoryService.count() == 3
    assert ExportHistoryService.count(dataset_id="ds-retail") == 2
    assert len(ExportHistoryService.get_history(dataset_id="ds-finance")) == 1
    assert ExportHistoryService.get_history(dataset_id="ds-finance")[0].dataset_name == (
        "finance.csv"
    )


def test_entries_without_a_dataset_id_are_still_recorded(history_db: Path) -> None:
    _record(dataset_id=None)

    assert ExportHistoryService.count() == 1
    assert ExportHistoryService.count(dataset_id="ds-1") == 0


def test_every_export_format_round_trips(history_db: Path) -> None:
    for export_format in ExportFormat:
        _record(export_format=export_format)

    stored = {entry.export_format for entry in ExportHistoryService.get_history(limit=100)}
    assert stored == set(ExportFormat)


def test_clear_removes_all_rows(history_db: Path) -> None:
    _record()
    _record()

    ExportHistoryService.clear()
    assert ExportHistoryService.count() == 0
    assert ExportHistoryService.get_history() == []


def test_a_failed_write_does_not_break_the_export(tmp_path: Path) -> None:
    """History is metadata. An export that succeeded must still return its bytes."""
    original_path = ExportHistoryService._db_path
    # A directory where the database file should be makes sqlite3 fail to open it.
    broken = tmp_path / "blocked"
    broken.mkdir()
    ExportHistoryService.configure(broken)

    try:
        entry = _record()
        assert entry.dataset_name == "retail.csv", "the caller still gets its entry back"
        assert ExportHistoryService.get_history() == [], "reads degrade to empty, not raise"
    finally:
        if original_path is not None:
            ExportHistoryService.configure(original_path)
        else:
            ExportHistoryService._db_path = None
            ExportHistoryService._initialized = False
