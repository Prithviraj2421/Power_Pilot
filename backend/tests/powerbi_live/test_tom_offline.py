"""Exercise the real TOM / .NET code paths without a Power BI model.

Skipped unless this is Windows with pythonnet and Power BI Desktop's libraries available, so CI on
Linux ignores it. What it covers is everything except talking to a live engine: loading the
libraries, building measures on an offline TOM model, and converting real .NET reader values.
"""

from __future__ import annotations

import sys

import pandas as pd
import pytest

pytest.importorskip("pythonnet")

from app.powerbi_live.connector import DISPLAY_FOLDER, KPI_ANNOTATION, ModelConnectionError, NewMeasure
from app.powerbi_live.dll_locator import DllNotFoundError, find_dll_dir
from app.powerbi_live.tom_connector import TomAdomdConnector, add_measures_to_model, load_runtime, read_rows
from app.powerbi_live.values import BOOL, DATETIME, FLOAT, INT, TEXT, frame_from_rows

if sys.platform != "win32":
    pytest.skip("Power BI Desktop is Windows-only", allow_module_level=True)
try:
    find_dll_dir()
except DllNotFoundError:
    pytest.skip("Power BI Desktop's Analysis Services libraries are not installed", allow_module_level=True)


@pytest.fixture(scope="module")
def rt():
    return load_runtime()


@pytest.fixture
def model(rt):
    """An in-memory model: a 'Sales Data' table with one existing, user-written measure."""
    tom = rt.tom
    database = tom.Database("Offline")
    database.CompatibilityLevel = 1500
    database.Model = tom.Model()
    table = tom.Table()
    table.Name = "Sales Data"
    column = tom.DataColumn()
    column.Name = "Amount"
    column.DataType = tom.DataType.Double
    column.SourceColumn = "Amount"
    table.Columns.Add(column)
    mine = tom.Measure()
    mine.Name = "My Own Measure"
    mine.Expression = "SUM('Sales Data'[Amount]) * 2"
    mine.DisplayFolder = "Mine"
    table.Measures.Add(mine)
    database.Model.Tables.Add(table)
    return database.Model


def new(name="Total Amount", kpi_id="ds1:total-amount") -> NewMeasure:
    return NewMeasure("Sales Data", name, "SUM('Sales Data'[Amount])", "Sum of 'Amount'.", kpi_id)


def test_the_libraries_load_from_the_desktop_install(rt) -> None:
    assert rt.tom.Measure is not None and rt.adomd.AdomdConnection is not None


def test_a_measure_is_added_in_the_powerpilot_folder_with_its_kpi_id(rt, model) -> None:
    add_measures_to_model(rt.tom, model, [new()])

    measure = model.Tables.Find("Sales Data").Measures.Find("Total Amount")
    assert measure.Expression == "SUM('Sales Data'[Amount])"
    assert measure.DisplayFolder == DISPLAY_FOLDER
    assert measure.Annotations.Find(KPI_ANNOTATION).Value == "ds1:total-amount"


def test_an_existing_user_measure_is_never_modified(rt, model) -> None:
    add_measures_to_model(rt.tom, model, [new()])

    mine = model.Tables.Find("Sales Data").Measures.Find("My Own Measure")
    assert mine.Expression == "SUM('Sales Data'[Amount]) * 2"
    assert mine.DisplayFolder == "Mine" and mine.Annotations.Find(KPI_ANNOTATION) is None


def test_a_name_that_exists_is_refused_not_overwritten_and_nothing_else_is_added(rt, model) -> None:
    batch = [new("Brand New", "ds1:brand-new"), new("my own measure", "ds1:clash")]  # case-insensitive clash

    with pytest.raises(ModelConnectionError, match="already exists"):
        add_measures_to_model(rt.tom, model, batch)

    measures = model.Tables.Find("Sales Data").Measures
    assert measures.Count == 1 and not measures.Contains("Brand New"), "validation happens before any change"
    assert measures.Find("My Own Measure").Expression == "SUM('Sales Data'[Amount]) * 2"


def test_two_new_measures_with_one_name_are_refused(rt, model) -> None:
    with pytest.raises(ModelConnectionError, match="already exists"):
        add_measures_to_model(rt.tom, model, [new("Same", "a"), new("Same", "b")])


def test_an_unknown_table_is_refused(rt, model) -> None:
    with pytest.raises(ModelConnectionError, match="no table named"):
        add_measures_to_model(rt.tom, model, [NewMeasure("Nope", "X", "1", "", "k")])


def test_the_written_measure_survives_serialisation_like_a_saved_model(rt, model) -> None:
    add_measures_to_model(rt.tom, model, [new()])

    json_text = rt.tom.JsonSerializer.SerializeDatabase(model.Database)

    assert "Total Amount" in json_text and DISPLAY_FOLDER in json_text and "ds1:total-amount" in json_text


def test_real_net_values_become_a_correctly_typed_frame(rt) -> None:
    """DBNull, DateTime, Decimal, Int64, Boolean and String through a real .NET data reader."""
    import clr

    clr.AddReference("System.Data")
    from System import Boolean, DBNull, DateTime, Decimal, Double, Int64, String
    from System.Data import DataTable

    table = DataTable()
    for name, net_type in [("id", Int64), ("region", String), ("amount", Decimal), ("score", Double),
                           ("when", DateTime), ("flag", Boolean)]:
        table.Columns.Add(f"Sales[{name}]", net_type)
    table.Rows.Add(1, "East", Decimal(12.5), 1.5, DateTime(2024, 3, 5, 14, 30, 15), True)
    table.Rows.Add(2, "West", Decimal(7), 2.5, DateTime(1999, 12, 31), False)
    table.Rows.Add(3, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)

    reader = table.CreateDataReader()
    names = [reader.GetName(i) for i in range(reader.FieldCount)]
    rows = read_rows(reader, reader.FieldCount, 100, rt.System)
    frame = frame_from_rows("Sales", names, [INT, TEXT, FLOAT, FLOAT, DATETIME, BOOL], rows)

    assert list(frame.columns) == ["id", "region", "amount", "score", "when", "flag"]
    assert frame["id"].tolist() == [1, 2, 3] and frame["id"].dtype == "int64"
    assert frame["amount"].iloc[0] == 12.5 and pd.isna(frame["amount"].iloc[2])
    assert frame["when"].iloc[0] == pd.Timestamp("2024-03-05 14:30:15")
    assert frame["when"].iloc[1] == pd.Timestamp("1999-12-31") and pd.isna(frame["when"].iloc[2])
    assert frame["region"].iloc[1] == "West" and pd.isna(frame["region"].iloc[2])
    assert frame["flag"].iloc[0] is True or bool(frame["flag"].iloc[0]) is True
    assert not any("DBNull" in str(v) for v in frame.to_numpy().ravel())


def test_the_reader_stops_at_the_row_cap(rt) -> None:
    import clr

    clr.AddReference("System.Data")
    from System import Int64
    from System.Data import DataTable

    table = DataTable()
    table.Columns.Add("n", Int64)
    for i in range(50):
        table.Rows.Add(i)

    rows = read_rows(table.CreateDataReader(), 1, 10, rt.System)

    assert [r[0] for r in rows] == list(range(10))


def test_a_non_loopback_address_is_refused_before_any_connection() -> None:
    with pytest.raises(ValueError):
        TomAdomdConnector("example.com:51234", "abc")
    with pytest.raises(ValueError):
        TomAdomdConnector("localhost:51234", "x; Data Source=evil")
