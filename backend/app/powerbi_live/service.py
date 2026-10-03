from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from app.datasets.service import DatasetNotFoundError, DatasetService
from app.intelligence.kpi.dax_executor import disagreement
from app.models.kpi_recommendation import KPIRecommendation
from app.powerbi_live.connector import ModelConnectionError, ModelConnector, NewMeasure

SAVE_REMINDER = "Measures were added to the open model. Save your report (Ctrl+S) to keep them."

WRITTEN, VERIFIED, REFUSED, EXISTS, FAILED = "written", "verified", "refused", "skipped_exists", "failed"


def make_kpi_id(dataset_id: str, kpi_name: str) -> str:
    """A stable id for a KPI of one analysis: the dataset's id plus a slug of its name."""
    slug = re.sub(r"[^a-z0-9]+", "-", kpi_name.lower()).strip("-")
    return f"{dataset_id}:{slug}"


@dataclass(frozen=True)
class ApplyItem:
    table: str
    kpi_id: str


class _EngineExecutor:
    """Adapts a connector to the ``DaxExecutor`` protocol and remembers the value it returned."""

    def __init__(self, connector: ModelConnector) -> None:
        self._connector = connector
        self.value: Optional[float] = None

    def execute(self, dax: str, table: str, df: pd.DataFrame) -> Optional[float]:
        self.value = self._connector.run_dax(f'EVALUATE ROW("v", {dax})')
        return self.value


class LiveModelService:
    """Analyses the tables of the open model and writes verified measures back into it."""

    def __init__(self, connector: ModelConnector, datasets: DatasetService, *, max_rows: int) -> None:
        self._connector = connector
        self._datasets = datasets
        self._max_rows = max_rows

    # -- status -------------------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        try:
            tables = self._connector.list_tables()
        except ModelConnectionError as exc:
            return {"connected": False, "error": str(exc), "tables": [], "max_rows": self._max_rows}
        return {
            "connected": True,
            "error": None,
            "max_rows": self._max_rows,
            "tables": [
                {
                    "name": t.name,
                    "columns": t.column_count,
                    "rows": t.row_count,
                    "will_be_sampled": t.row_count > self._max_rows,
                }
                for t in tables
            ],
        }

    # -- analyze ------------------------------------------------------------------------------

    def analyze(self, tables: Optional[list[str]] = None, max_rows: Optional[int] = None) -> dict[str, Any]:
        cap = max_rows or self._max_rows
        available = {t.name: t for t in self._connector.list_tables()}
        wanted = tables if tables else list(available)
        existing = {m.name.lower(): m for m in self._connector.list_measures()}

        results: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        for name in wanted:
            if name not in available:
                skipped.append({"table": name, "reason": "the model has no such table"})
                continue
            data = self._connector.read_table(name, cap)
            if data.frame.empty:
                skipped.append({"table": name, "reason": "the table has no rows"})
                continue

            analysis = self._datasets.register_dataframe(data.frame, name, powerbi_table=name, verify_on="source")
            report = analysis.result.kpi_report
            results.append(
                {
                    "table": name,
                    "dataset_id": analysis.dataset_id,
                    "rows_read": len(data.frame),
                    "rows_total": data.rows_total,
                    "sampled": data.sampled,
                    "can_write": not data.sampled,
                    "domain": analysis.record.detected_domain,
                    "kpis": [self._kpi_view(analysis.dataset_id, k, existing) for k in report.all_kpis],
                    "rejected": [{"name": k.name, "reason": k.verification_note} for k in report.rejected_kpis],
                }
            )
        return {"max_rows": cap, "tables": results, "skipped": skipped}

    @staticmethod
    def _kpi_view(dataset_id: str, kpi: KPIRecommendation, existing: dict[str, Any]) -> dict[str, Any]:
        clash = existing.get(kpi.name.lower())
        return {
            "id": make_kpi_id(dataset_id, kpi.name),
            "name": kpi.name,
            "formula": kpi.formula,
            "computed_value": kpi.computed_value,
            "verified": kpi.verified,
            "baseline": kpi.target_threshold,
            "note": kpi.verification_note,
            "name_taken": clash is not None,
            "added_by_powerpilot": clash is not None and clash.kpi_id is not None,
        }

    # -- apply --------------------------------------------------------------------------------

    def apply(self, items: list[ApplyItem], dry_run: bool = False) -> dict[str, Any]:
        """Write the chosen KPIs into the model as measures, but only those the engine agrees with.

        For each KPI the DAX is run by Power BI's own engine and compared with the value pandas
        computed. A measure is written only if they match; a KPI whose table has changed or was only
        sampled is refused, since the comparison would not be like for like.
        """
        tables = {t.name: t for t in self._connector.list_tables()}
        existing = {m.name.lower(): m for m in self._connector.list_measures()}

        results: list[dict[str, Any]] = []
        to_write: list[NewMeasure] = []
        planned: dict[str, int] = {}  # lowered name -> index in results, to catch duplicates in one request

        for item in items:
            outcome, measure = self._check(item, tables, existing, planned)
            results.append(outcome)
            if measure is not None:
                planned[measure.name.lower()] = len(results) - 1
                to_write.append(measure)

        if dry_run:
            return {"dry_run": True, "saved": False, "results": results, "reminder": None}

        saved = False
        if to_write:
            try:
                self._connector.add_measures(to_write)
                saved = True
            except ModelConnectionError as exc:
                for measure in to_write:
                    index = planned[measure.name.lower()]
                    results[index] = {**results[index], "status": FAILED, "reason": str(exc)}
            else:
                for measure in to_write:
                    index = planned[measure.name.lower()]
                    results[index] = {**results[index], "status": WRITTEN, "reason": "added to your model"}
        return {"dry_run": False, "saved": saved, "results": results, "reminder": SAVE_REMINDER if saved else None}

    def _check(
        self,
        item: ApplyItem,
        tables: dict[str, Any],
        existing: dict[str, Any],
        planned: dict[str, int],
    ) -> tuple[dict[str, Any], Optional[NewMeasure]]:
        def result(status: str, reason: str, name: str = "", engine: Any = None, computed: Any = None) -> dict[str, Any]:
            return {
                "table": item.table,
                "kpi_id": item.kpi_id,
                "name": name,
                "status": status,
                "reason": reason,
                "engine_value": engine,
                "computed_value": computed,
            }

        dataset_id = item.kpi_id.partition(":")[0]
        try:
            analysis = self._datasets.get_analysis(dataset_id)
        except DatasetNotFoundError:
            return result(REFUSED, "that analysis no longer exists; run Analyze again"), None

        record = analysis.record
        if not record.is_live_model or record.powerbi_table != item.table:
            return result(REFUSED, "that KPI was not computed from this table of the open model"), None

        kpi = next((k for k in analysis.result.kpi_report.all_kpis if make_kpi_id(dataset_id, k.name) == item.kpi_id), None)
        if kpi is None or not kpi.verified or not kpi.formula or kpi.computed_value is None:
            return result(REFUSED, "that is not a verified KPI of this analysis"), None

        current = tables.get(item.table)
        if current is None:
            return result(REFUSED, f"the model no longer has a table named '{item.table}'", kpi.name), None
        if current.row_count != record.original_rows:
            return (
                result(
                    REFUSED,
                    f"the analysis saw {record.original_rows:,} of the {current.row_count:,} rows now in "
                    f"'{item.table}' (a sample, or the data changed), so its value cannot be checked against "
                    "the engine like for like. Run Analyze again, with a larger row limit if the table is big.",
                    kpi.name,
                    computed=kpi.computed_value,
                ),
                None,
            )

        clash = existing.get(kpi.name.lower())
        if clash is not None:
            mine = clash.kpi_id == item.kpi_id
            reason = (
                "PowerPilot already added this measure"
                if mine
                else f"a measure named '{kpi.name}' already exists in your model and was left untouched"
            )
            return result(EXISTS, reason, kpi.name, computed=kpi.computed_value), None
        if kpi.name.lower() in planned:
            return result(EXISTS, "another selected KPI has the same name", kpi.name, computed=kpi.computed_value), None

        engine = _EngineExecutor(self._connector)
        # Also covers the engine failing or returning BLANK: those come back as a reason, not an exception.
        problem = disagreement(kpi.computed_value, kpi.formula, item.table, pd.DataFrame(), engine)
        if problem:
            return result(REFUSED, problem, kpi.name, engine=engine.value, computed=kpi.computed_value), None

        measure = NewMeasure(
            table=item.table,
            name=kpi.name,
            expression=kpi.formula,
            description=f"{kpi.reason} Checked by PowerPilot: Power BI's engine returned the same value as the data.",
            kpi_id=item.kpi_id,
        )
        return (
            result(VERIFIED, "Power BI's engine agrees with the computed value", kpi.name, engine.value, kpi.computed_value),
            measure,
        )
