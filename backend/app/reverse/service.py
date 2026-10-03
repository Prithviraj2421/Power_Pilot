"""Running reverse-engineering for an uploaded dataset or a table of the open Power BI model.

A finished report is kept in memory for a while (``ReportStore``) so exports and the "add to Power BI"
step can refer to it by id. The legacy file itself is never stored: only what was read from it and
what was found.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any, Optional

from app.common.powerbi_names import powerbi_table_name
from app.core.config import Settings, get_settings
from app.datasets.cache import ResultCache
from app.datasets.service import DatasetService
from app.powerbi_live.connector import ModelConnector
from app.powerbi_live.service import MeasureToAdd
from app.reverse.engine import ReverseEngine
from app.reverse.errors import ReportReadError
from app.reverse.models import ReverseReport
from app.reverse.proposer import Proposer, default_proposer
from app.reverse.report_reader import read_report


class ReportNotFoundError(Exception):
    """The report id is unknown or has expired; the person should run the reverse-engineering again."""


@lru_cache(maxsize=1)
def get_report_store() -> ResultCache[ReverseReport]:
    settings = get_settings()
    return ResultCache[ReverseReport](max_entries=settings.reverse_max_reports, ttl_seconds=settings.reverse_report_ttl_seconds)


class ReverseService:
    def __init__(
        self,
        store: Optional[ResultCache[ReverseReport]] = None,
        settings: Optional[Settings] = None,
        proposer: Optional[Proposer] = None,
        use_default_proposer: bool = True,
    ) -> None:
        self._settings = get_settings() if settings is None else settings
        self._store = get_report_store() if store is None else store
        self._proposer = proposer if proposer is not None or not use_default_proposer else default_proposer(self._settings)

    # -- running ------------------------------------------------------------------------------

    def _check_upload(self, content: bytes) -> None:
        if len(content) > self._settings.max_upload_bytes:
            raise ReportReadError(f"The report is larger than the {self._settings.max_upload_mb} MB limit.")

    def _engine(self, raw, table: str, cleaned=None, existing_measures: Optional[set[str]] = None, basis_label: str = "raw table") -> ReverseEngine:
        return ReverseEngine(
            raw,
            table,
            cleaned=cleaned,
            proposer=self._proposer,
            time_budget=self._settings.reverse_time_budget_seconds,
            basis_label=basis_label,
            existing_measures=existing_measures,
        )

    def run_for_dataset(self, datasets: DatasetService, dataset_id: str, content: bytes, filename: str) -> ReverseReport:
        """Explain a legacy report from an uploaded dataset: the raw upload first, the cleaned data as a fallback."""
        self._check_upload(content)
        record = datasets.get_record(dataset_id)
        parsed = read_report(content, filename)
        raw = datasets.get_source_dataframe(dataset_id)
        cleaned = datasets.get_analysis(dataset_id).cleaned_dataframe
        table = record.powerbi_table or powerbi_table_name(record.filename)
        report = self._engine(raw, table, cleaned).run(parsed, filename, uuid.uuid4().hex[:12])
        report.dataset_id = dataset_id
        report.live = record.is_live_model
        self._store.put(report.report_id, report)
        return report

    def run_for_live(
        self, connector: ModelConnector, table: str, content: bytes, filename: str, max_rows: int
    ) -> ReverseReport:
        """Explain a legacy report from a table of the open Power BI model, using the model's own rows."""
        self._check_upload(content)
        parsed = read_report(content, filename)
        data = connector.read_table(table, max_rows)
        existing = {m.name for m in connector.list_measures()}
        report = self._engine(data.frame, table, None, existing, basis_label="table in the open model").run(
            parsed, filename, uuid.uuid4().hex[:12]
        )
        report.live = True
        report.rows_total = data.rows_total
        report.sampled = data.sampled
        if data.sampled:
            report.warnings.append(
                f"Only the first {len(data.frame):,} of the {data.rows_total:,} rows were read, so numbers cannot be "
                "proven against the whole table and nothing can be added to your report."
            )
        self._store.put(report.report_id, report)
        return report

    # -- using a finished report --------------------------------------------------------------

    def get(self, report_id: str) -> ReverseReport:
        report = self._store.get(report_id)
        if report is None:
            raise ReportNotFoundError("That report analysis is no longer available (it expires after a while). Run the reverse-engineering again.")
        return report

    def measures_to_add(self, report: ReverseReport, measure_ids: list[str]) -> list[MeasureToAdd]:
        """The planned measures with these ids, as the Power BI writer wants them. DAX comes from the plan, never a client."""
        if report.plan is None:
            return []
        out: list[MeasureToAdd] = []
        for measure_id in measure_ids:
            measure = report.plan.get(measure_id)
            if measure is None:
                raise ReportNotFoundError(f"The report has no planned measure '{measure_id}'.")
            out.append(
                MeasureToAdd(
                    table=report.plan.table,
                    id=measure.id,
                    name=measure.name,
                    expression=measure.dax,
                    description=measure.description,
                    display_folder=measure.display_folder,
                    checks=tuple((c.label, c.dax, c.expected) for c in measure.checks),
                    rows_total=report.rows_total,
                    sampled=report.sampled,
                    cells=tuple(measure.cell_ids),
                )
            )
        return out


def planned_measures(report: ReverseReport) -> list[dict[str, Any]]:
    return report.plan.to_dict()["measures"] if report.plan is not None else []
