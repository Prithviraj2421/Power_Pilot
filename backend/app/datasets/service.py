"""Dataset service: the single entry point for registering and retrieving analyses.

Before this existed, every endpoint that needed an analysis re-accepted the CSV
upload and re-ran all 12 pipeline stages -- eleven endpoints, eleven redundant
full runs, and nothing survived a browser refresh.

The model here is a two-layer one:

* **Durability** -- the uploaded CSV on disk plus a SQLite metadata row. This is
  the source of truth and it survives restarts.
* **Performance** -- an in-memory LRU/TTL cache of computed analyses. On a miss
  the analysis is transparently recomputed from the stored CSV, so the cache can
  be evicted, expired or lost at any time without costing a dataset.

That split is what makes ``dataset_id`` durable while keeping repeat requests
cheap, and it avoids pickling the deeply nested result graph.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import pandas as pd

from app.common.logger import get_logger
from app.core.config import Settings, get_settings
from app.datasets.cache import ResultCache
from app.datasets.models import DatasetRecord
from app.datasets.store import DatasetStore, sha256_of
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PipelineExecution, PowerPilotIntelligencePipeline

logger = get_logger("DatasetService")


class DatasetError(Exception):
    """Base class for dataset service failures."""


class DatasetNotFoundError(DatasetError):
    """Raised when a dataset id is unknown or its stored source has gone missing."""


class InvalidDatasetError(DatasetError):
    """Raised when an upload is not a usable CSV dataset."""


@dataclass(slots=True, frozen=True)
class DatasetAnalysis:
    """A dataset's metadata together with its computed analysis."""

    record: DatasetRecord
    result: MasterIntelligenceResult
    cleaned_dataframe: pd.DataFrame

    @property
    def dataset_id(self) -> str:
        return self.record.dataset_id


class DatasetService:
    """Registers datasets and serves their analyses from cache or by recomputation."""

    def __init__(
        self,
        store: DatasetStore,
        pipeline: Optional[PowerPilotIntelligencePipeline] = None,
        cache: Optional[ResultCache[PipelineExecution]] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        # Explicit `is None` checks, not `or`: ResultCache defines __len__, so an
        # empty injected cache is falsy and `cache or default` would silently
        # discard it.
        self._settings = get_settings() if settings is None else settings
        self._store = store
        self._pipeline = PowerPilotIntelligencePipeline() if pipeline is None else pipeline
        self._cache = (
            ResultCache[PipelineExecution](
                max_entries=self._settings.result_cache_size,
                ttl_seconds=self._settings.result_cache_ttl_seconds,
            )
            if cache is None
            else cache
        )

    # -- validation ---------------------------------------------------------

    def parse_csv(self, payload: bytes, filename: str) -> pd.DataFrame:
        """Validate and parse uploaded bytes into a DataFrame.

        Raises ``InvalidDatasetError`` with a client-safe message on any problem.
        """
        if not filename.lower().endswith(".csv"):
            raise InvalidDatasetError("File must be a valid .csv file.")

        if not payload:
            raise InvalidDatasetError(
                "The uploaded file is empty. Please upload a non-empty CSV dataset."
            )

        limit = self._settings.max_upload_bytes
        if len(payload) > limit:
            raise InvalidDatasetError(
                f"File size exceeds maximum limit of {self._settings.max_upload_mb}MB."
            )

        try:
            df = pd.read_csv(io.BytesIO(payload))
        except pd.errors.EmptyDataError as exc:
            raise InvalidDatasetError(
                "Invalid CSV formatting: file contains no parseable columns or headers."
            ) from exc
        except pd.errors.ParserError as exc:
            raise InvalidDatasetError(
                "Malformed CSV syntax: could not parse row records. "
                "Please verify delimiter formatting."
            ) from exc
        except UnicodeDecodeError as exc:
            raise InvalidDatasetError(
                "Could not decode the file as text. Please upload a UTF-8 encoded CSV."
            ) from exc

        if df.empty or len(df.columns) == 0:
            raise InvalidDatasetError(
                "The CSV file must contain at least one column with valid data rows."
            )

        return df

    # -- registration -------------------------------------------------------

    def register(
        self, payload: bytes, filename: str, *, reuse_identical: bool = True
    ) -> DatasetAnalysis:
        """Validate, analyze and durably register an uploaded CSV.

        When ``reuse_identical`` is set and byte-identical content is already
        registered, the existing dataset is returned instead of paying for a
        duplicate pipeline run and a second copy on disk.
        """
        df = self.parse_csv(payload, filename)

        if reuse_identical:
            existing = self._store.find_by_content_hash(sha256_of(payload))
            if existing is not None:
                logger.info(
                    f"Upload '{filename}' matches existing dataset {existing.dataset_id} "
                    "by content hash; reusing it"
                )
                return self.get_analysis(existing.dataset_id)

        execution = self._pipeline.execute(df, dataset_name=filename)
        result = execution.result
        profile = result.dataset_profile
        quality = result.quality_report

        record = self._store.insert(
            filename=filename,
            payload=payload,
            original_rows=len(df),
            total_rows=profile.total_rows,
            total_columns=profile.total_columns,
            detected_domain=profile.detected_domain.value,
            domain_confidence=float(profile.domain_confidence),
            quality_grade=quality.grade.value if quality else "N/A",
            quality_score=float(quality.overall_score) if quality else 0.0,
            quality_issues_count=int(quality.total_issues_count) if quality else 0,
        )

        self._cache.put(record.dataset_id, execution)
        self._store.prune(self._settings.max_stored_datasets)

        return DatasetAnalysis(
            record=record,
            result=result,
            cleaned_dataframe=execution.cleaned_dataframe,
        )

    # -- retrieval ----------------------------------------------------------

    def get_record(self, dataset_id: str) -> DatasetRecord:
        record = self._store.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(f"No dataset registered with id '{dataset_id}'.")
        return record

    def get_analysis(self, dataset_id: str) -> DatasetAnalysis:
        """Return a dataset's analysis, recomputing it if it is not cached."""
        record = self.get_record(dataset_id)

        execution = self._cache.get(dataset_id)
        if execution is None:
            execution = self._recompute(record)
            self._cache.put(dataset_id, execution)

        self._store.touch(dataset_id)
        return DatasetAnalysis(
            record=record,
            result=execution.result,
            cleaned_dataframe=execution.cleaned_dataframe,
        )

    def _recompute(self, record: DatasetRecord) -> PipelineExecution:
        """Re-run the pipeline from the stored CSV after a cache miss."""
        payload = self._store.read_source(record.dataset_id)
        if payload is None:
            raise DatasetNotFoundError(
                f"Dataset '{record.dataset_id}' is registered but its stored source file "
                "is missing. Please re-upload the dataset."
            )

        logger.info(
            f"Cache miss for dataset {record.dataset_id}; recomputing analysis "
            f"from stored source '{record.filename}'"
        )
        df = self.parse_csv(payload, record.filename)
        return self._pipeline.execute(df, dataset_name=record.filename)

    def get_source_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """The original uploaded data, exactly as submitted, before any cleaning."""
        record = self.get_record(dataset_id)
        payload = self._store.read_source(dataset_id)
        if payload is None:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' is registered but its stored source file is missing."
            )
        return self.parse_csv(payload, record.filename)

    # -- management ---------------------------------------------------------

    def list_datasets(self, limit: int = 50, offset: int = 0) -> list[DatasetRecord]:
        return self._store.list_recent(limit=limit, offset=offset)

    def count_datasets(self) -> int:
        return self._store.count()

    def delete(self, dataset_id: str) -> None:
        self._cache.invalidate(dataset_id)
        if not self._store.delete(dataset_id):
            raise DatasetNotFoundError(f"No dataset registered with id '{dataset_id}'.")

    def cache_stats(self) -> dict[str, object]:
        return self._cache.describe()

    def is_cached(self, dataset_id: str) -> bool:
        return dataset_id in self._cache


@lru_cache(maxsize=1)
def get_dataset_service() -> DatasetService:
    """Process-wide dataset service singleton, wired from application settings."""
    settings = get_settings()
    store = DatasetStore(
        db_path=settings.registry_db_path,
        datasets_dir=settings.datasets_path,
    )
    return DatasetService(store=store, settings=settings)
