"""The real connector: TOM (to read the model's structure and write measures) and ADOMD (to run DAX).

Both libraries are .NET Framework assemblies that ship with Power BI Desktop. They are reached through
pythonnet, which is imported lazily so that nothing here loads on a machine without it (CI, Linux).
"""

from __future__ import annotations

import importlib
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterator, Optional

from app.common.powerbi_names import dax_table
from app.powerbi_live.connector import (
    DISPLAY_FOLDER,
    KPI_ANNOTATION,
    MeasureInfo,
    ModelConnectionError,
    NewMeasure,
    TableData,
    TableInfo,
)
from app.powerbi_live.dll_locator import DllNotFoundError, find_dll_dir, REQUIRED
from app.powerbi_live.security import validate_database_name, validate_model_address
from app.powerbi_live.values import frame_from_rows, is_blank, kind_for, column_name, TEXT

# Column types that hold data a user can analyse (RowNumber is Analysis Services' internal row id).
_READABLE_COLUMNS = {"Data", "Calculated", "CalculatedTableColumn"}
# Tables Power BI creates itself for "auto date/time", plus the template it copies them from.
_HIDDEN_TABLE_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")

_runtime: Optional[SimpleNamespace] = None
_runtime_lock = threading.Lock()


def load_runtime(explicit_dir: Optional[str] = None) -> SimpleNamespace:
    """Load pythonnet and the Analysis Services client libraries once per process."""
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            return _runtime
        try:
            folder = find_dll_dir(explicit_dir)
        except DllNotFoundError as exc:
            raise ModelConnectionError(str(exc)) from exc
        try:
            from pythonnet import load

            load("netfx")  # these are .NET Framework builds, not .NET (Core)
            import clr
        except Exception as exc:
            raise ModelConnectionError(
                "PowerPilot needs the 'pythonnet' package (Windows only) to talk to Power BI. "
                "Install it with: pip install -r backend/requirements-powerbi.txt"
            ) from exc
        for name in REQUIRED:
            clr.AddReference(str(folder / name))
        _runtime = SimpleNamespace(
            System=importlib.import_module("System"),
            tom=importlib.import_module("Microsoft.AnalysisServices.Tabular"),
            adomd=importlib.import_module("Microsoft.AnalysisServices.AdomdClient"),
        )
        return _runtime


def read_rows(reader: Any, column_count: int, max_rows: int, system: Any) -> list[list[Any]]:
    """Read up to ``max_rows`` rows from a .NET data reader, one whole row per .NET call.

    Reading a row at once with ``GetValues`` is about 3.5x faster than ``GetValue`` per cell, which is
    what decides whether a half-million-row table takes seconds or minutes through pythonnet.
    """
    buffer = system.Array.CreateInstance(system.Object, column_count)
    rows: list[list[Any]] = []
    while len(rows) < max_rows and reader.Read():
        reader.GetValues(buffer)
        rows.append(list(buffer))
    return rows


def add_measures_to_model(tom: Any, model: Any, measures: list[NewMeasure]) -> None:
    """Add measures to a TOM model object. Never replaces or edits anything that exists.

    Split from ``SaveChanges`` so it can be exercised on an offline model.
    """
    taken = {m.Name.lower() for table in model.Tables for m in table.Measures}
    for new in measures:
        if new.name.lower() in taken:
            raise ModelConnectionError(f"a measure named '{new.name}' already exists in the model")
        taken.add(new.name.lower())

    for new in measures:
        table = model.Tables.Find(new.table)
        if table is None:
            raise ModelConnectionError(f"the model has no table named '{new.table}'")
        measure = tom.Measure()
        measure.Name = new.name
        measure.Expression = new.expression
        measure.Description = new.description
        measure.DisplayFolder = DISPLAY_FOLDER
        marker = tom.Annotation()
        marker.Name = KPI_ANNOTATION
        marker.Value = new.kpi_id
        measure.Annotations.Add(marker)
        table.Measures.Add(measure)


def _friendly(exc: BaseException, action: str) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    lowered = text.lower()
    if any(s in lowered for s in ("could not connect", "refused", "no connection", "connection failed", "unable to connect")):
        return f"Could not {action}: Power BI Desktop's model is not reachable. Is the report still open?"
    return f"Could not {action}: {text}"


class TomAdomdConnector:
    """A connection to the model open in Power BI Desktop, opened afresh for every call."""

    def __init__(self, server: str, database: str, dll_dir: Optional[str] = None) -> None:
        self._server = validate_model_address(server)
        self._database = validate_database_name(database)
        self._dll_dir = dll_dir
        self._lock = threading.Lock()

    # -- connections ----------------------------------------------------------------------

    def _runtime(self) -> SimpleNamespace:
        return load_runtime(self._dll_dir)

    @contextmanager
    def _tom(self, action: str) -> Iterator[Any]:
        rt = self._runtime()
        server = rt.tom.Server()
        try:
            server.Connect(f"Data Source={self._server}")
            database = server.Databases.GetByName(self._database)
        except Exception as exc:
            self._disconnect(server)
            raise ModelConnectionError(_friendly(exc, action)) from exc
        try:
            yield database
        finally:
            self._disconnect(server)

    @staticmethod
    def _disconnect(server: Any) -> None:
        try:
            server.Disconnect()
        except Exception:
            pass

    @contextmanager
    def _adomd(self, action: str) -> Iterator[Any]:
        rt = self._runtime()
        connection = rt.adomd.AdomdConnection(f"Data Source={self._server};Initial Catalog={self._database}")
        try:
            connection.Open()
        except Exception as exc:
            raise ModelConnectionError(_friendly(exc, action)) from exc
        try:
            yield connection
        finally:
            try:
                connection.Close()
            except Exception:
                pass

    # -- ModelConnector -------------------------------------------------------------------

    def run_dax(self, query: str) -> Optional[float]:
        with self._lock, self._adomd("run a DAX query") as connection:
            try:
                reader = self._runtime().adomd.AdomdCommand(query, connection).ExecuteReader()
            except Exception as exc:
                raise ModelConnectionError(_friendly(exc, "run a DAX query")) from exc
            try:
                if not reader.Read():
                    return None
                value = reader.GetValue(0)
            finally:
                reader.Close()
        if is_blank(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ModelConnectionError("the DAX query returned a value that is not a number") from exc

    def list_tables(self) -> list[TableInfo]:
        found: list[tuple[str, int]] = []
        with self._lock, self._tom("read the model's tables") as database:
            for table in database.Model.Tables:
                if self._is_internal(table):
                    continue
                columns = [c for c in table.Columns if str(c.Type) in _READABLE_COLUMNS]
                if columns:
                    found.append((table.Name, len(columns)))
        return [TableInfo(name, count, self._count_rows(name)) for name, count in found]

    def read_table(self, name: str, max_rows: int) -> TableData:
        with self._lock:
            with self._tom(f"read table '{name}'") as database:
                table = database.Model.Tables.Find(name)
                if table is None:
                    raise ModelConnectionError(f"the model has no table named '{name}'")
                kinds = {c.Name: kind_for(str(c.DataType)) for c in table.Columns if str(c.Type) in _READABLE_COLUMNS}

            total = self._count_rows(name)
            query = f"EVALUATE {dax_table(name)}" if total <= max_rows else f"EVALUATE TOPN({max_rows}, {dax_table(name)})"
            with self._adomd(f"read table '{name}'") as connection:
                rt = self._runtime()
                try:
                    reader = rt.adomd.AdomdCommand(query, connection).ExecuteReader()
                except Exception as exc:
                    raise ModelConnectionError(_friendly(exc, f"read table '{name}'")) from exc
                try:
                    width = reader.FieldCount
                    raw_names = [reader.GetName(i) for i in range(width)]
                    rows = read_rows(reader, width, max_rows, rt.System)
                finally:
                    reader.Close()

        column_kinds = [kinds.get(column_name(raw, name), TEXT) for raw in raw_names]
        try:
            frame = frame_from_rows(name, raw_names, column_kinds, rows)
        except ValueError as exc:
            raise ModelConnectionError(f"could not read table '{name}': {exc}") from exc
        return TableData(frame=frame, rows_total=total)

    def list_measures(self) -> list[MeasureInfo]:
        found: list[MeasureInfo] = []
        with self._lock, self._tom("read the model's measures") as database:
            for table in database.Model.Tables:
                for measure in table.Measures:
                    marker = measure.Annotations.Find(KPI_ANNOTATION)
                    found.append(
                        MeasureInfo(
                            table=table.Name,
                            name=measure.Name,
                            expression=measure.Expression or "",
                            display_folder=measure.DisplayFolder or "",
                            kpi_id=marker.Value if marker is not None else None,
                        )
                    )
        return found

    def add_measures(self, measures: list[NewMeasure]) -> None:
        if not measures:
            return
        with self._lock, self._tom("add measures") as database:
            add_measures_to_model(self._runtime().tom, database.Model, measures)
            try:
                database.Model.SaveChanges()
            except Exception as exc:
                # Nothing is persisted: the in-memory changes are dropped when the connection closes.
                raise ModelConnectionError(f"Power BI did not accept the measures: {exc}") from exc

    # -- helpers --------------------------------------------------------------------------

    @staticmethod
    def _is_internal(table: Any) -> bool:
        if table.IsPrivate or table.ShowAsVariationsOnly:
            return True
        if table.Name.startswith(_HIDDEN_TABLE_PREFIXES):
            return True
        return getattr(table, "CalculationGroup", None) is not None

    def _count_rows(self, name: str) -> int:
        value = self._count_via_adomd(name)
        return int(value or 0)

    def _count_via_adomd(self, name: str) -> Optional[float]:
        # run_dax takes the lock itself, so call the unlocked body here: callers already hold it.
        with self._adomd(f"count rows of '{name}'") as connection:
            try:
                reader = self._runtime().adomd.AdomdCommand(
                    f'EVALUATE ROW("n", COUNTROWS({dax_table(name)}))', connection
                ).ExecuteReader()
            except Exception as exc:
                raise ModelConnectionError(_friendly(exc, f"count rows of '{name}'")) from exc
            try:
                if not reader.Read():
                    return None
                value = reader.GetValue(0)
            finally:
                reader.Close()
        return None if is_blank(value) else float(value)
