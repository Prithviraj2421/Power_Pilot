"""Export activity history, persisted to SQLite.

This was a class-level Python list. It died on every server restart, was shared
process-wide with no way to scope it, and could grow without bound. The Export
Center UI presented it as an "Export Audit History", which an in-memory list
cannot honestly be.

It now lives in the same database as the dataset registry, so history survives
restarts and can be filtered to a single dataset.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from app.common.logger import get_logger
from app.core.config import get_settings
from app.export_center.models.export_models import ExportFormat, ExportHistoryEntry

logger = get_logger("ExportHistory")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS export_history (
    entry_id        TEXT    PRIMARY KEY,
    dataset_id      TEXT,
    dataset_name    TEXT    NOT NULL,
    export_format   TEXT    NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    duration_ms     REAL    NOT NULL,
    timestamp       TEXT    NOT NULL,
    status          TEXT    NOT NULL,
    file_path       TEXT,
    created_at_ns   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_created ON export_history (created_at_ns DESC);
CREATE INDEX IF NOT EXISTS idx_history_dataset ON export_history (dataset_id);
"""

_COLUMNS = (
    "entry_id, dataset_id, dataset_name, export_format, file_size_bytes, "
    "duration_ms, timestamp, status, file_path"
)


class ExportHistoryService:
    """Records and reads export activity.

    The classmethod surface is unchanged so the Export Center facade's six call
    sites did not have to move.
    """

    _db_path: Optional[Path] = None
    _lock = threading.Lock()
    _initialized = False

    # -- wiring -------------------------------------------------------------

    @classmethod
    def configure(cls, db_path: Path) -> None:
        """Point the service at a database file. Tests use this for isolation."""
        with cls._lock:
            cls._db_path = db_path
            cls._initialized = False

    @classmethod
    def _resolve_db_path(cls) -> Path:
        if cls._db_path is None:
            cls._db_path = get_settings().registry_db_path
        return cls._db_path

    @classmethod
    @contextmanager
    def _connect(cls) -> Iterator[sqlite3.Connection]:
        db_path = cls._resolve_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            if not cls._initialized:
                connection.executescript(_SCHEMA)
                cls._initialized = True
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # -- writes -------------------------------------------------------------

    @classmethod
    def record_export(
        cls,
        dataset_name: str,
        export_format: ExportFormat,
        file_size_bytes: int,
        duration_ms: float,
        status: str = "SUCCESS",
        file_path: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> ExportHistoryEntry:
        created_at_ns = time.time_ns()
        entry = ExportHistoryEntry(
            # A timestamp is not a unique id. time_ns() is coarse on Windows, so two
            # exports in the same tick produced identical ids -- which the old
            # in-memory list accepted silently and a PRIMARY KEY rejects outright.
            entry_id=f"EXP-{uuid.uuid4().hex[:16]}",
            dataset_name=dataset_name,
            export_format=export_format,
            file_size_bytes=file_size_bytes,
            duration_ms=round(duration_ms, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            status=status,
            file_path=file_path,
        )

        try:
            with cls._connect() as connection:
                connection.execute(
                    f"INSERT INTO export_history ({_COLUMNS}, created_at_ns) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.entry_id,
                        dataset_id,
                        entry.dataset_name,
                        entry.export_format.value,
                        entry.file_size_bytes,
                        entry.duration_ms,
                        entry.timestamp,
                        entry.status,
                        entry.file_path,
                        created_at_ns,
                    ),
                )
        except sqlite3.Error as exc:
            # An export that succeeded must not fail because its audit row did not
            # persist. The download is the user's deliverable; history is metadata.
            logger.error(f"Could not record export history for '{dataset_name}': {exc}")

        return entry

    # -- reads --------------------------------------------------------------

    @classmethod
    def get_history(
        cls, limit: int = 50, dataset_id: Optional[str] = None
    ) -> list[ExportHistoryEntry]:
        query = f"SELECT {_COLUMNS} FROM export_history"
        params: list[object] = []
        if dataset_id is not None:
            query += " WHERE dataset_id = ?"
            params.append(dataset_id)
        query += " ORDER BY created_at_ns DESC, rowid DESC LIMIT ?"
        params.append(limit)

        try:
            with cls._connect() as connection:
                rows = connection.execute(query, params).fetchall()
        except sqlite3.Error as exc:
            logger.error(f"Could not read export history: {exc}")
            return []

        return [
            ExportHistoryEntry(
                entry_id=row["entry_id"],
                dataset_name=row["dataset_name"],
                export_format=ExportFormat(row["export_format"]),
                file_size_bytes=row["file_size_bytes"],
                duration_ms=row["duration_ms"],
                timestamp=row["timestamp"],
                status=row["status"],
                file_path=row["file_path"],
            )
            for row in rows
        ]

    @classmethod
    def count(cls, dataset_id: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM export_history"
        params: list[object] = []
        if dataset_id is not None:
            query += " WHERE dataset_id = ?"
            params.append(dataset_id)

        try:
            with cls._connect() as connection:
                return int(connection.execute(query, params).fetchone()[0])
        except sqlite3.Error:
            return 0

    @classmethod
    def clear(cls) -> None:
        """Remove all recorded history. Used by tests."""
        try:
            with cls._connect() as connection:
                connection.execute("DELETE FROM export_history")
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            logger.error(f"Could not clear export history: {exc}")
