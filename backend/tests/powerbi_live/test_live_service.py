from __future__ import annotations

import pandas as pd
import pytest

from app.common.powerbi_names import dax_references
from app.datasets.service import DatasetService
from app.powerbi_live.connector import MeasureInfo
from app.powerbi_live.service import ApplyItem, LiveModelService, make_kpi_id
from tests.powerbi_live.fake_connector import FakeConnector

TABLE = "Sales Data"  # a real-world name: the space must survive into every formula


@pytest.fixture
def connector(retail_df: pd.DataFrame, finance_df: pd.DataFrame) -> FakeConnector:
    return FakeConnector({TABLE: retail_df, "Ledger": finance_df})


def make_service(dataset_service: DatasetService, connector, max_rows: int = 500_000) -> LiveModelService:
    return LiveModelService(connector, dataset_service, max_rows=max_rows)


def analyzed(service: LiveModelService, table: str = TABLE) -> dict:
    return next(t for t in service.analyze([table])["tables"] if t["table"] == table)


def kpi(table_result: dict, name: str) -> dict:
    return next(k for k in table_result["kpis"] if k["name"] == name)


def apply_one(service, table_result, name, **kw):
    item = ApplyItem(table_result["table"], kpi(table_result, name)["id"])
    return service.apply([item], **kw)["results"][0]


# -- status / analyze ---------------------------------------------------------------------------


def test_status_lists_tables_and_flags_the_ones_that_will_be_sampled(dataset_service, connector) -> None:
    status = make_service(dataset_service, connector, max_rows=1_000).status()

    assert status["connected"] and {t["name"] for t in status["tables"]} == {TABLE, "Ledger"}
    sales = next(t for t in status["tables"] if t["name"] == TABLE)
    assert sales["rows"] == 61 and sales["will_be_sampled"] is False


def test_status_reports_an_unreachable_model_instead_of_raising(dataset_service, connector) -> None:
    def broken():
        from app.powerbi_live.connector import ModelConnectionError

        raise ModelConnectionError("Power BI Desktop's model is not reachable. Is the report still open?")

    connector.list_tables = broken

    status = make_service(dataset_service, connector).status()

    assert status["connected"] is False and "still open" in status["error"] and status["tables"] == []


def test_analyze_runs_the_pipeline_on_each_table_with_formulas_naming_the_real_table(dataset_service, connector) -> None:
    result = make_service(dataset_service, connector).analyze()

    assert {t["table"] for t in result["tables"]} == {TABLE, "Ledger"}
    sales = next(t for t in result["tables"] if t["table"] == TABLE)
    assert sales["rows_read"] == sales["rows_total"] == 61 and not sales["sampled"] and sales["can_write"]
    assert sales["domain"] == "retail"
    for k in sales["kpis"]:
        assert k["verified"] and k["computed_value"] is not None
        assert {t for t, _ in dax_references(k["formula"])} == {TABLE}
        assert k["id"] == make_kpi_id(sales["dataset_id"], k["name"])


def test_the_datasets_are_registered_as_live_model_tables(dataset_service, connector) -> None:
    sales = analyzed(make_service(dataset_service, connector))

    record = dataset_service.get_record(sales["dataset_id"])

    assert record.is_live_model and record.powerbi_table == TABLE and record.verify_on == "source"


def test_unknown_and_empty_tables_are_skipped_with_a_reason(dataset_service, connector) -> None:
    connector.tables["Empty"] = pd.DataFrame({"a": []})

    result = make_service(dataset_service, connector).analyze([TABLE, "Nope", "Empty"])

    reasons = {s["table"]: s["reason"] for s in result["skipped"]}
    assert "no such table" in reasons["Nope"] and "no rows" in reasons["Empty"]
    assert [t["table"] for t in result["tables"]] == [TABLE]


def test_a_table_over_the_row_limit_is_analysed_as_a_flagged_sample(dataset_service, connector) -> None:
    sales = make_service(dataset_service, connector).analyze([TABLE], max_rows=1_000)["tables"][0]
    sampled = make_service(dataset_service, connector, max_rows=1_000)

    # 61 rows fit under 1,000, so shrink the model's own view of the cap by growing the table instead.
    big = pd.concat([connector.tables[TABLE]] * 30, ignore_index=True)  # 1,830 rows
    connector.tables[TABLE] = big
    result = sampled.analyze([TABLE])["tables"][0]

    assert sales["sampled"] is False
    assert result["sampled"] is True and result["rows_read"] == 1_000 and result["rows_total"] == 1_830
    assert result["can_write"] is False


def test_existing_measures_are_flagged_so_the_ui_can_show_them(dataset_service, connector) -> None:
    connector.measures.append(MeasureInfo(TABLE, "Total Sales Revenue", "SUM('Sales Data'[x])"))

    sales = analyzed(make_service(dataset_service, connector))

    taken = kpi(sales, "Total Sales Revenue")
    assert taken["name_taken"] is True and taken["added_by_powerpilot"] is False
    assert kpi(sales, "Total Units Sold")["name_taken"] is False


# -- apply: the engine check --------------------------------------------------------------------


def test_a_kpi_the_engine_agrees_with_is_written_in_the_powerpilot_folder(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    names = ["Total Sales Revenue", "Total Units Sold"]

    response = service.apply([ApplyItem(TABLE, kpi(sales, n)["id"]) for n in names])

    assert response["saved"] and "Ctrl+S" in response["reminder"]
    assert [r["status"] for r in response["results"]] == ["written", "written"]
    written = {m.name: m for m in connector.measures}
    assert set(written) == set(names)
    assert written["Total Sales Revenue"].display_folder == "PowerPilot"
    assert written["Total Sales Revenue"].kpi_id == kpi(sales, "Total Sales Revenue")["id"]
    first = response["results"][0]
    assert first["engine_value"] == pytest.approx(first["computed_value"], rel=1e-6)


def test_the_value_the_engine_computes_is_over_the_models_raw_rows(dataset_service, connector, retail_df) -> None:
    # The sample has a duplicate row and gaps that cleaning changes; the engine sees the raw rows,
    # so verifying on cleaned data would make this KPI disagree with Power BI and be refused.
    service = make_service(dataset_service, connector)
    sales = analyzed(service)

    result = apply_one(service, sales, "Total Sales Revenue", dry_run=True)

    assert result["status"] == "verified"
    assert result["engine_value"] == pytest.approx(float(retail_df["sales_amount"].sum()))


def test_a_measure_whose_value_the_engine_disagrees_with_is_refused_and_nothing_is_written(
    dataset_service, connector
) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    connector.engine_scale = 1.001

    result = apply_one(service, sales, "Total Sales Revenue")

    assert result["status"] == "refused" and "engine returned" in result["reason"]
    assert result["engine_value"] == pytest.approx(result["computed_value"] * 1.001)
    assert connector.measures == [] and connector.add_calls == []


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [({"engine_blank": True}, "BLANK"), ({"engine_error": "syntax error"}, "could not evaluate")],
)
def test_an_engine_that_cannot_evaluate_the_measure_blocks_it(dataset_service, connector, kwargs, fragment) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    for key, value in kwargs.items():
        setattr(connector, key, value)

    result = apply_one(service, sales, "Total Sales Revenue")

    assert result["status"] == "refused" and fragment in result["reason"]
    assert connector.add_calls == []


def test_a_good_kpi_is_still_written_when_another_in_the_same_request_is_refused(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    original = connector.run_dax
    connector.run_dax = lambda q: (original(q) * 2 if "Quantity" in q or "quantity" in q else original(q))

    response = service.apply(
        [ApplyItem(TABLE, kpi(sales, n)["id"]) for n in ("Total Sales Revenue", "Total Units Sold")]
    )

    by_name = {r["name"]: r["status"] for r in response["results"]}
    assert by_name == {"Total Sales Revenue": "written", "Total Units Sold": "refused"}
    assert [m.name for m in connector.measures] == ["Total Sales Revenue"]


def test_dry_run_checks_everything_and_writes_nothing(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)

    response = service.apply([ApplyItem(TABLE, kpi(sales, "Total Sales Revenue")["id"])], dry_run=True)

    assert response["dry_run"] and response["saved"] is False and response["reminder"] is None
    assert response["results"][0]["status"] == "verified"
    assert connector.measures == [] and connector.add_calls == []
    assert len(connector.queries) == 1, "the engine really was consulted"


# -- apply: refusals that protect the user ----------------------------------------------------------


def test_a_sampled_table_cannot_be_written_back(dataset_service, connector) -> None:
    connector.tables[TABLE] = pd.concat([connector.tables[TABLE]] * 30, ignore_index=True)
    service = make_service(dataset_service, connector, max_rows=1_000)
    sales = analyzed(service)

    result = apply_one(service, sales, "Total Sales Revenue")

    assert sales["sampled"] and result["status"] == "refused" and "1,000 of the 1,830" in result["reason"]
    assert connector.queries == [], "no point asking the engine: the comparison would not be like for like"


def test_data_that_changed_since_analysis_is_refused(dataset_service, connector, retail_df) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    connector.tables[TABLE] = pd.concat([retail_df, retail_df.head(5)], ignore_index=True)  # a refresh

    result = apply_one(service, sales, "Total Sales Revenue")

    assert result["status"] == "refused" and "Run Analyze again" in result["reason"]
    assert connector.measures == []


def test_a_users_existing_measure_with_the_same_name_is_left_untouched(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    mine = MeasureInfo(TABLE, "Total Sales Revenue", "SUM('Sales Data'[sales_amount]) * 100", "Mine")
    connector.measures.append(mine)
    sales = analyzed(service)

    response = service.apply(
        [ApplyItem(TABLE, kpi(sales, n)["id"]) for n in ("Total Sales Revenue", "Total Units Sold")]
    )

    by_name = {r["name"]: r for r in response["results"]}
    assert by_name["Total Sales Revenue"]["status"] == "skipped_exists"
    assert "left untouched" in by_name["Total Sales Revenue"]["reason"]
    assert by_name["Total Units Sold"]["status"] == "written"
    assert connector.measures[0] is mine and mine.expression.endswith("* 100")


def test_running_apply_twice_does_not_duplicate_measures(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    item = ApplyItem(TABLE, kpi(sales, "Total Sales Revenue")["id"])
    service.apply([item])

    again = service.apply([item])["results"][0]

    assert again["status"] == "skipped_exists" and "already added" in again["reason"]
    assert len(connector.measures) == 1
    assert kpi(analyzed(service), "Total Sales Revenue")["added_by_powerpilot"] is True


def test_the_same_kpi_selected_twice_is_written_once(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    item = ApplyItem(TABLE, kpi(sales, "Total Sales Revenue")["id"])

    results = service.apply([item, item])["results"]

    assert [r["status"] for r in results] == ["written", "skipped_exists"]
    assert len(connector.measures) == 1


@pytest.mark.parametrize(
    "item",
    [
        ApplyItem(TABLE, "deadbeef:total-sales-revenue"),
        ApplyItem(TABLE, "not-an-id"),
    ],
)
def test_an_unknown_kpi_id_is_refused(dataset_service, connector, item) -> None:
    result = make_service(dataset_service, connector).apply([item])["results"][0]

    assert result["status"] == "refused" and connector.measures == []


def test_a_kpi_cannot_be_written_to_a_different_table_than_it_was_computed_from(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)

    result = service.apply([ApplyItem("Ledger", kpi(sales, "Total Sales Revenue")["id"])])["results"][0]

    assert result["status"] == "refused" and "not computed from this table" in result["reason"]


def test_a_kpi_id_of_an_ordinary_upload_cannot_be_applied(dataset_service, connector, retail_csv_bytes) -> None:
    upload = dataset_service.register(retail_csv_bytes, "retail.csv")
    k = upload.result.kpi_report.all_kpis[0]

    result = make_service(dataset_service, connector).apply([ApplyItem(TABLE, make_kpi_id(upload.dataset_id, k.name))])

    assert result["results"][0]["status"] == "refused" and connector.measures == []


def test_a_failed_save_reports_every_measure_as_failed_and_records_nothing(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    connector.save_error = "Power BI did not accept the measures: model is read-only"

    response = service.apply(
        [ApplyItem(TABLE, kpi(sales, n)["id"]) for n in ("Total Sales Revenue", "Total Units Sold")]
    )

    assert response["saved"] is False and response["reminder"] is None
    assert [r["status"] for r in response["results"]] == ["failed", "failed"]
    assert all("read-only" in r["reason"] for r in response["results"])
    assert connector.measures == []


def test_formulas_written_to_the_model_are_exactly_the_verified_ones(dataset_service, connector) -> None:
    service = make_service(dataset_service, connector)
    sales = analyzed(service)
    names = [k["name"] for k in sales["kpis"]]

    service.apply([ApplyItem(TABLE, kpi(sales, n)["id"]) for n in names])

    assert {m.name: m.expression for m in connector.measures} == {k["name"]: k["formula"] for k in sales["kpis"]}
