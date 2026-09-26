"""Durable dataset storage: uploaded CSV bytes on disk, metadata in SQLite.

The uploaded CSV is the source of truth. An analysis result is derived data and
is always recomputable from it, which is what lets the in-memory result cache be
a pure performance layer rather than something whose loss costs a dataset.

Thread safety: FastAPI runs synchronous route handlers in a worker threadpool, so
several requests can hit this store concurrently. Each operation opens its own
short-lived connection rather than sharing one across threads, and the database
runs in WAL mode so readers never block on a writer.
"""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.common.logger import get_logger
from app.datasets.models import DatasetRecord

logger = get_logger("DatasetStore")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id           TEXT    PRIMARY KEY,
    filename             TEXT    NOT NULL,
    stored_path          TEXT    NOT NULL,
    size_bytes           INTEGER NOT NULL,
    content_sha256       TEXT    NOT NULL,
    original_rows        INTEGER NOT NULL,
    total_rows           INTEGER NOT NULL,
    total_columns        INTEGER NOT NULL,
    detected_domain      TEXT    NOT NULL,
    domain_confidence    REAL    NOT NULL,
    quality_grade        TEXT    NOT NULL,
    quality_score        REAL    NOT NULL,
    quality_issues_count INTEGER NOT NULL,
    created_at           TEXT    NOT NULL,
    last_accessed_at     TEXT    NOT NULL,
    source_encoding      TEXT    NOT NULL DEFAULT 'utf-8',
    source_delimiter     TEXT    NOT NULL DEFAULT ','
);
CREATE INDEX IF NOT EXISTS idx_datasets_sha      ON datasets (content_sha256);
CREATE INDEX IF NOT EXISTS idx_datasets_accessed ON datasets (last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_datasets_created  ON datasets (created_at DESC);
"""

_COLUMNS = (
    "dataset_id, filename, stored_path, size_bytes, content_sha256, "
    "original_rows, total_rows, total_columns, detected_domain, domain_confidence, "
    "quality_grade, quality_score, quality_issues_count, created_at, last_accessed_at, "
    "source_encoding, source_delimiter"
)

# Columns added after the first release. CREATE TABLE IF NOT EXISTS does not alter
# an existing table, so a database created before these existed needs them added.
_ADDED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("source_encoding", "TEXT NOT NULL DEFAULT 'utf-8'"),
    ("source_delimiter", "TEXT NOT NULL DEFAULT ','"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class DatasetStore:
    """SQLite metadata index plus a content-addressed CSV file store."""

    def __init__(self, db_path: Path, datasets_dir: Path) -> None:
        self._db_path = db_path
        self._datasets_dir = datasets_dir
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._datasets_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    # -- connection handling ------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            self._apply_column_migrations(connection)
        logger.info(f"Dataset registry ready at {self._db_path}")

    @staticmethod
    def _apply_column_migrations(connection: sqlite3.Connection) -> None:
        """Add columns introduced after a database was first created.

        Without this, upgrading against an existing registry fails every query with
        "no such column" -- CREATE TABLE IF NOT EXISTS silently does nothing when
        the table already exists.
        """
        existing = {
            row["name"] for row in connection.execute("PRAGMA table_info(datasets)")
        }
        for column, definition in _ADDED_COLUMNS:
            if column not in existing:
                connection.execute(f"ALTER TABLE datasets ADD COLUMN {column} {definition}")
                logger.info(f"Migrated dataset registry: added column '{column}'")

    @staticmethod
    def _to_record(row: sqlite3.Row) -> DatasetRecord:
        return DatasetRecord(**{key: row[key] for key in row.keys()})

    # -- writes -------------------------------------------------------------

    def save_source(self, dataset_id: str, payload: bytes) -> Path:
        """Persist the uploaded CSV bytes and return the stored path."""
        path = self._datasets_dir / f"{dataset_id}.csv"
        path.write_bytes(payload)
        return path

    def insert(
        self,
        *,
        filename: str,
        payload: bytes,
        original_rows: int,
        total_rows: int,
        total_columns: int,
        detected_domain: str,
        domain_confidence: float,
        quality_grade: str,
        quality_score: float,
        quality_issues_count: int,
        dataset_id: Optional[str] = None,
        source_encoding: str = "utf-8",
        source_delimiter: str = ",",
    ) -> DatasetRecord:
        """Register a dataset, writing its source bytes and metadata row."""
        dataset_id = dataset_id or uuid.uuid4().hex
        stored_path = self.save_source(dataset_id, payload)
        now = _utc_now()

        record = DatasetRecord(
            dataset_id=dataset_id,
            filename=filename,
            stored_path=str(stored_path),
            size_bytes=len(payload),
            content_sha256=sha256_of(payload),
            original_rows=original_rows,
            total_rows=total_rows,
            total_columns=total_columns,
            detected_domain=detected_domain,
            domain_confidence=domain_confidence,
            quality_grade=quality_grade,
            quality_score=quality_score,
            quality_issues_count=quality_issues_count,
            created_at=now,
            last_accessed_at=now,
            source_encoding=source_encoding,
            source_delimiter=source_delimiter,
        )

        placeholders = ", ".join(["?"] * 17)
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO datasets ({_COLUMNS}) VALUES ({placeholders})",
                (
                    record.dataset_id,
                    record.filename,
                    record.stored_path,
                    record.size_bytes,
                    record.content_sha256,
                    record.original_rows,
                    record.total_rows,
                    record.total_columns,
                    record.detected_domain,
                    record.domain_confidence,
                    record.quality_grade,
                    record.quality_score,
                    record.quality_issues_count,
                    record.created_at,
                    record.last_accessed_at,
                    record.source_encoding,
                    record.source_delimiter,
                ),
            )

        logger.info(
            f"Registered dataset {record.dataset_id} ('{filename}', "
            f"{record.size_bytes} bytes, domain={detected_domain})"
        )
        return record

    def touch(self, dataset_id: str) -> None:
        """Record an access so least-recently-used pruning stays meaningful."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE datasets SET last_accessed_at = ? WHERE dataset_id = ?",
                (_utc_now(), dataset_id),
            )

    def delete(self, dataset_id: str) -> bool:
        """Remove a dataset's metadata row and its stored CSV. True if it existed."""
        record = self.get(dataset_id)
        if record is None:
            return False

        with self._connect() as connection:
            connection.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))

        source = Path(record.stored_path)
        try:
            source.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem-dependent
            logger.warning(f"Could not delete source file {source} for {dataset_id}: {exc}")

        logger.info(f"Deleted dataset {dataset_id} ('{record.filename}')")
        return True

    # -- reads --------------------------------------------------------------

    def get(self, dataset_id: str) -> Optional[DatasetRecord]:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM datasets WHERE dataset_id = ?", (dataset_id,)
            ).fetchone()
        return self._to_record(row) if row else None

    def find_by_content_hash(self, content_sha256: str) -> Optional[DatasetRecord]:
        """Look up an existing registration of identical bytes.

        Re-uploading the same file returns the existing dataset instead of paying
        for a duplicate pipeline run and a duplicate copy on disk.
        """
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM datasets WHERE content_sha256 = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (content_sha256,),
            ).fetchone()
        return self._to_record(row) if row else None

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[DatasetRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM datasets ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._to_record(row) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])

    def read_source(self, dataset_id: str) -> Optional[bytes]:
        """Return the stored CSV bytes, or None if the record or file is gone."""
        record = self.get(dataset_id)
        if record is None:
            return None
        path = Path(record.stored_path)
        if not path.exists():
            logger.warning(
                f"Dataset {dataset_id} metadata exists but source file is missing at {path}"
            )
            return None
        return path.read_bytes()

    # -- maintenance --------------------------------------------------------

    def prune(self, max_datasets: int) -> list[str]:
        """Drop the least-recently-accessed datasets beyond ``max_datasets``.

        Returns the ids removed. A value of 0 or less disables pruning.
        """
        if max_datasets <= 0:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT dataset_id FROM datasets ORDER BY last_accessed_at DESC LIMIT -1 OFFSET ?",
                (max_datasets,),
            ).fetchall()

        stale_ids = [row["dataset_id"] for row in rows]
        for dataset_id in stale_ids:
            self.delete(dataset_id)
        if stale_ids:
            logger.info(f"Pruned {len(stale_ids)} dataset(s) beyond retention limit {max_datasets}")
        return stale_ids
