import time
from typing import Optional
from app.export_center.models.export_models import ExportFormat, ExportHistoryEntry


class ExportHistoryService:
    """
    Service tracking and persisting export activity history.
    """

    _history: list[ExportHistoryEntry] = []

    @classmethod
    def record_export(
        cls,
        dataset_name: str,
        export_format: ExportFormat,
        file_size_bytes: int,
        duration_ms: float,
        status: str = "SUCCESS",
        file_path: Optional[str] = None,
    ) -> ExportHistoryEntry:
        entry = ExportHistoryEntry(
            entry_id=f"EXP-{int(time.time() * 1000)}",
            dataset_name=dataset_name,
            export_format=export_format,
            file_size_bytes=file_size_bytes,
            duration_ms=round(duration_ms, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            status=status,
            file_path=file_path,
        )
        cls._history.insert(0, entry)
        return entry

    @classmethod
    def get_history(cls, limit: int = 50) -> list[ExportHistoryEntry]:
        return cls._history[:limit]
