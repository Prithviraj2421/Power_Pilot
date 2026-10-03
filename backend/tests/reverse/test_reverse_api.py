"""The HTTP surface: dataset flow, exports, and the guarded write-back to a live model."""

from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.routes.powerbi_live_route as live_route
import app.routes.reverse_route as reverse_route
from app.core.config import Settings
from app.datasets.cache import ResultCache
from app.main import app
from app.powerbi_live.connector import MeasureInfo
from app.powerbi_live.service import LiveModelService
from app.reverse.service import ReverseService

from tests.powerbi_live.fake_connector import FakeConnector
from tests.reverse import legacy_reports as lr

LIVE = "/api/v1/powerbi-live"
TOKEN = "s3cret-token"
HEADERS = {"X-PowerPilot-Token": TOKEN}
TABLE = "Superstore"
XLSX = ("legacy.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def live_settings(**overrides) -> Settings:
    return Settings(**{"pbi_server": "localhost:51234", "pbi_database": "abc", "pbi_token": TOKEN, **overrides})


@pytest.fixture(scope="module")
def spec():
    return lr.build()


@pytest.fixture(scope="module")
def xlsx(spec) -> bytes:
    return lr.to_xlsx(spec)


@pytest.fixture
def reverse_service() -> ReverseService:
    return ReverseService(store=ResultCache(max_entries=8, ttl_seconds=3600), settings=live_settings(), use_default_proposer=False)


@pytest.fixture
def api(reverse_service) -> TestClient:
    app.dependency_overrides[reverse_route.get_reverse_service] = lambda: reverse_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def upload(content: bytes, name: str = "legacy.xlsx", **extra):
    return {"file": (name, io.BytesIO(content), XLSX[1]), **extra}


# --- uploaded dataset ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def dataset_id(spec) -> str:
    client = TestClient(app)
    csv = lr.GOLDEN.read_bytes()
    response = client.post("/api/v1/datasets", files={"file": ("Superstore Sample.csv", io.BytesIO(csv), "text/csv")})
    assert response.status_code == 201, response.text
    return response.json()["dataset"]["dataset_id"]


def test_the_report_is_explained_against_an_uploaded_dataset(api, dataset_id, xlsx) -> None:
    response = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(xlsx))
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["summary"]["reproduced"], body["summary"]["not_reproducible"], body["summary"]["derived"]) == (17, 3, 2)
    assert body["dataset_id"] == dataset_id and not body["live"] and body["table"] == "Superstore_Sample"
    assert {c["status"] for c in body["cells"]} == {"REPRODUCED", "NOT_REPRODUCIBLE", "DERIVED"}
    assert body["plan"]["measures"] and "Region" in " ".join(body["plan"]["measures"][0]["notes"])
    assert body["layout"][0]["cells"]


def test_a_finished_report_can_be_fetched_by_id(api, dataset_id, xlsx) -> None:
    report_id = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(xlsx)).json()["report_id"]
    assert api.get(f"/api/v1/reverse/{report_id}").json()["report_id"] == report_id
    assert api.get("/api/v1/reverse/nope").status_code == 404


def test_csv_and_pdf_reports_work_too(api, dataset_id, spec) -> None:
    for content, name in ((lr.to_csv(spec), "legacy.csv"), (lr.to_pdf(spec), "legacy.pdf")):
        body = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(content, name)).json()
        assert body["summary"]["reproduced"] == 17, name


@pytest.mark.parametrize(
    ("content", "name", "message"),
    [
        (b"hello", "notes.txt", "Unsupported file type"),
        (b"", "empty.xlsx", "empty"),
        (b"not really a workbook", "fake.xlsx", "could not be opened"),
        (b"Region,Sales\nEast,abc\n", "words.csv", "No numbers"),
    ],
)
def test_unreadable_reports_get_a_422_with_a_plain_message(api, dataset_id, content, name, message) -> None:
    response = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(content, name))
    assert response.status_code == 422 and message in response.json()["detail"]


def test_an_unknown_dataset_is_a_404(api, xlsx) -> None:
    assert api.post("/api/v1/datasets/does-not-exist/reverse-engineer", files=upload(xlsx)).status_code == 404


def test_the_upload_size_limit_is_enforced(dataset_id, xlsx) -> None:
    tiny = ReverseService(store=ResultCache(), settings=live_settings(max_upload_mb=1), use_default_proposer=False)
    app.dependency_overrides[reverse_route.get_reverse_service] = lambda: tiny
    try:
        big = b"A,B\n" + b"x,1\n" * 400_000
        response = TestClient(app).post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(big, "big.csv"))
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422 and "1 MB" in response.json()["detail"]


def test_the_dax_export_holds_only_proven_measures(api, dataset_id, xlsx) -> None:
    body = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(xlsx)).json()
    script = api.get(f"/api/v1/reverse/{body['report_id']}/dax").text
    for measure in body["plan"]["measures"]:
        assert f"{measure['name']} = {measure['dax']}" in script
    assert "Proven:  17 number(s)" in script
    assert "16,097.19" not in script and "swapped" not in script  # nothing about the mistakes becomes a measure
    definitions = [line for line in script.splitlines() if line.strip() and not line.startswith("//")]
    assert len(definitions) == len(body["plan"]["measures"])  # one line per measure, nothing else


def test_the_bim_export_has_the_measures_in_their_folder_and_nothing_else(api, dataset_id, xlsx) -> None:
    body = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(xlsx)).json()
    bim = api.get(f"/api/v1/reverse/{body['report_id']}/bim").json()
    measures = bim["model"]["tables"][0]["measures"]
    assert [m["name"] for m in measures] == [m["name"] for m in body["plan"]["measures"]]
    assert {m["displayFolder"] for m in measures} == {"PowerPilot\\Migrated"}
    names = {a["name"] for a in bim["model"]["annotations"]}
    assert {"PowerPilot_MigratedFrom", "PowerPilot_MigrationBasis"} <= names


def test_an_expired_report_has_no_exports(api) -> None:
    for path in ("dax", "bim"):
        assert api.get(f"/api/v1/reverse/gone/{path}").status_code == 404


# --- the open Power BI model --------------------------------------------------------------


def superstore_table(spec) -> pd.DataFrame:
    frame = spec.df.copy()
    frame["Order Date"] = pd.to_datetime(frame["Order Date"], dayfirst=True)
    frame["Ship Date"] = pd.to_datetime(frame["Ship Date"], dayfirst=True)
    return frame


@pytest.fixture
def connector(spec) -> FakeConnector:
    return FakeConnector({TABLE: superstore_table(spec)})


@pytest.fixture
def live(connector, dataset_service, reverse_service, monkeypatch) -> TestClient:
    service = LiveModelService(connector, dataset_service, max_rows=500_000)
    monkeypatch.setattr(live_route, "_build_service", lambda *args: service)
    app.dependency_overrides[live_route.get_live_settings] = lambda: live_settings()
    app.dependency_overrides[reverse_route.get_reverse_service] = lambda: reverse_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def run_live(live, xlsx, table: str = TABLE):
    return live.post(f"{LIVE}/reverse-engineer", data={"table": table}, files=upload(xlsx), headers=HEADERS)


def apply(live, report: dict, ids=None, dry_run=False, headers=HEADERS):
    ids = [m["id"] for m in report["plan"]["measures"]] if ids is None else ids
    return live.post(f"{LIVE}/reverse-engineer/apply", json={"report_id": report["report_id"], "measure_ids": ids, "dry_run": dry_run}, headers=headers)


def test_the_live_endpoints_need_the_session_token(live, xlsx) -> None:
    assert live.post(f"{LIVE}/reverse-engineer", data={"table": TABLE}, files=upload(xlsx)).status_code == 401
    assert live.post(f"{LIVE}/reverse-engineer/apply", json={"report_id": "abc", "measure_ids": ["x"]}).status_code == 401
    wrong = {"X-PowerPilot-Token": "wrong"}
    assert live.post(f"{LIVE}/reverse-engineer", data={"table": TABLE}, files=upload(xlsx), headers=wrong).status_code == 401


def test_the_report_is_explained_from_the_open_models_own_rows(live, xlsx) -> None:
    response = run_live(live, xlsx)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["live"] and not body["sampled"] and body["rows_total"] == 156 and body["dataset_id"] is None
    assert body["summary"]["reproduced"] == 17


def test_an_unknown_table_is_a_clear_error(live, xlsx) -> None:
    response = run_live(live, xlsx, table="Nope")
    assert response.status_code == 502 and "no table named 'Nope'" in response.json()["detail"]


def test_a_dry_run_checks_with_the_engine_and_writes_nothing(live, connector, xlsx) -> None:
    report = run_live(live, xlsx).json()
    result = apply(live, report, dry_run=True).json()
    assert result["dry_run"] and not result["saved"] and connector.add_calls == []
    assert {r["status"] for r in result["results"]} == {"verified"}
    assert any("Total Sales" in q or "SUM" in q for q in connector.queries), "the engine was actually consulted"


def test_the_proven_measures_are_written_into_their_own_folder(live, connector, xlsx) -> None:
    report = run_live(live, xlsx).json()
    result = apply(live, report).json()
    assert result["saved"] and result["reminder"] and {r["status"] for r in result["results"]} == {"written"}
    written = {m.name: m for m in connector.measures}
    assert set(written) == {m["name"] for m in report["plan"]["measures"]}
    assert {m.display_folder for m in written.values()} == {"PowerPilot\\Migrated"}
    total = written["Total Sales"]
    assert total.expression == "SUM('Superstore'[Sales])" and total.kpi_id.endswith(":total-sales")
    assert all(m.table == TABLE for m in written.values())


def test_every_cell_a_grouped_measure_covers_is_checked_by_the_engine(live, connector, xlsx) -> None:
    report = run_live(live, xlsx).json()
    grouped = next(m for m in report["plan"]["measures"] if m["name"] == "Total Sales")
    connector.queries.clear()
    apply(live, report, ids=[grouped["id"]], dry_run=True)
    assert len(connector.queries) == 7  # the measure itself + each of the 6 numbers it reproduces
    assert sum("CALCULATE" in q for q in connector.queries) == 6


def test_a_measure_the_engine_disagrees_with_is_refused(spec, dataset_service, reverse_service, xlsx, monkeypatch) -> None:
    connector = FakeConnector({TABLE: superstore_table(spec)}, engine_scale=1.01)
    monkeypatch.setattr(live_route, "_build_service", lambda *args: LiveModelService(connector, dataset_service, max_rows=500_000))
    app.dependency_overrides[live_route.get_live_settings] = lambda: live_settings()
    app.dependency_overrides[reverse_route.get_reverse_service] = lambda: reverse_service
    try:
        client = TestClient(app)
        report = run_live(client, xlsx).json()
        result = apply(client, report).json()
    finally:
        app.dependency_overrides.clear()
    assert not result["saved"] and connector.add_calls == []
    assert {r["status"] for r in result["results"]} == {"refused"} and "engine returned" in result["results"][0]["reason"]


def test_a_table_that_changed_since_is_refused(live, connector, xlsx, spec) -> None:
    report = run_live(live, xlsx).json()
    connector.tables[TABLE] = pd.concat([connector.tables[TABLE], connector.tables[TABLE].head(3)], ignore_index=True)
    result = apply(live, report).json()
    assert not result["saved"] and "now has 159" in result["results"][0]["reason"] and connector.add_calls == []


def test_a_sampled_table_can_be_analysed_but_never_written(spec, dataset_service, reverse_service, xlsx, monkeypatch) -> None:
    connector = FakeConnector({TABLE: superstore_table(spec)})
    monkeypatch.setattr(live_route, "_build_service", lambda *args: LiveModelService(connector, dataset_service, max_rows=100))
    app.dependency_overrides[live_route.get_live_settings] = lambda: live_settings()
    app.dependency_overrides[reverse_route.get_reverse_service] = lambda: reverse_service
    try:
        client = TestClient(app)
        report = run_live(client, xlsx).json()
        assert report["sampled"] and any("Only the first 100 of the 156 rows" in w for w in report["warnings"])
        result = apply(client, report).json()
    finally:
        app.dependency_overrides.clear()
    assert {r["status"] for r in result["results"]} == {"refused"} and "sample" in result["results"][0]["reason"]
    assert connector.add_calls == []


def test_a_name_that_is_taken_is_left_untouched(live, connector, xlsx) -> None:
    connector.measures.append(MeasureInfo(TABLE, "Total Sales", "SUM('Superstore'[Quantity])", "", None))
    report = run_live(live, xlsx).json()
    names = [m["name"] for m in report["plan"]["measures"]]
    assert "Total Sales" not in names and "Total Sales (2)" in names  # the plan already steers around it
    connector.measures.append(MeasureInfo(TABLE, "Total Sales (2)", "1", "", None))  # taken after the analysis
    result = apply(live, report).json()
    clash = next(r for r in result["results"] if r["name"] == "Total Sales (2)")
    assert clash["status"] == "skipped_exists" and "left untouched" in clash["reason"]
    assert next(m for m in connector.measures if m.name == "Total Sales").expression == "SUM('Superstore'[Quantity])"


def test_only_the_chosen_measures_are_written(live, connector, xlsx) -> None:
    report = run_live(live, xlsx).json()
    chosen = report["plan"]["measures"][0]
    apply(live, report, ids=[chosen["id"]])
    assert [m.name for m in connector.measures] == [chosen["name"]]


def test_a_client_cannot_supply_dax_or_unknown_measures(live, xlsx) -> None:
    report = run_live(live, xlsx).json()
    smuggled = live.post(
        f"{LIVE}/reverse-engineer/apply",
        json={"report_id": report["report_id"], "measure_ids": ["x"], "dax": "1", "expression": "DELETE"},
        headers=HEADERS,
    )
    assert smuggled.status_code == 422
    assert apply(live, report, ids=["rep:not-a-planned-measure"]).status_code == 404
    assert live.post(f"{LIVE}/reverse-engineer/apply", json={"report_id": report["report_id"], "measure_ids": []}, headers=HEADERS).status_code == 422


def test_an_expired_or_unknown_report_cannot_be_applied(live) -> None:
    response = live.post(f"{LIVE}/reverse-engineer/apply", json={"report_id": "expired-id", "measure_ids": ["x"]}, headers=HEADERS)
    assert response.status_code == 404 and "Run the reverse-engineering again" in response.json()["detail"]


def test_a_report_run_against_an_upload_cannot_be_written_to_the_open_model(live, api, dataset_id, xlsx, reverse_service) -> None:
    report = api.post(f"/api/v1/datasets/{dataset_id}/reverse-engineer", files=upload(xlsx)).json()
    response = apply(live, report)
    assert response.status_code == 409 and "not run against the open model" in response.json()["detail"]


def test_a_live_report_has_no_bim_export(live, xlsx) -> None:
    report = run_live(live, xlsx).json()
    response = live.get(f"/api/v1/reverse/{report['report_id']}/bim")
    assert response.status_code == 409 and "Add proven measures" in response.json()["detail"]
    assert live.get(f"/api/v1/reverse/{report['report_id']}/dax").status_code == 200
