import pandas as pd
import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.core.config import get_settings
from app.intelligence.kpi_engine import KPIEngine

I, F, T, D = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT, PhysicalType.DATETIME
RETAIL = (("Order ID", T, True), ("Customer ID", T, True), ("Order Date", D), ("Quantity", I), ("Sales", F))


def test_a_kpi_that_cannot_be_computed_is_rejected_and_never_reported(make_dataset) -> None:
    profile, df = make_dataset("shop.csv", DatasetDomain.RETAIL, *RETAIL)
    df["Sales"] = "n/a"  # the profile says numeric, the data says otherwise

    report = KPIEngine().recommend(profile, df=df)

    rejected = {k.name: k for k in report.rejected_kpis}
    assert "Total Sales Revenue" in rejected and "Average Order Value (AOV)" in rejected
    assert all(not k.verified and k.computed_value is None for k in rejected.values())
    assert "Sales" in rejected["Total Sales Revenue"].verification_note
    assert "Total Sales Revenue" not in {k.name for k in report.all_kpis}
    assert all(k.verified for k in report.all_kpis)


def test_when_nothing_in_the_domain_verifies_the_generic_plugin_takes_over(make_dataset) -> None:
    profile, df = make_dataset("shop.csv", DatasetDomain.RETAIL, ("Sales", F), ("Weight", F))
    df["Sales"] = "n/a"

    report = KPIEngine().recommend(profile, df=df)

    assert [k.name for k in report.all_kpis] == ["Total Weight"]
    assert any(k.name == "Total Sales Revenue" for k in report.rejected_kpis)


def test_targets_come_from_the_data_when_there_is_a_date_column(make_dataset) -> None:
    profile, df = make_dataset("shop.csv", DatasetDomain.RETAIL, *RETAIL)

    report = KPIEngine().recommend(profile, df=df)

    revenue = next(k for k in report.all_kpis if k.name == "Total Sales Revenue")
    assert revenue.target_threshold.startswith("Latest month 2024-04 vs 2024-03:")
    assert "Example target" not in revenue.target_threshold


def test_without_a_date_column_the_old_benchmark_is_labelled_as_an_example(make_dataset) -> None:
    profile, df = make_dataset("shop.csv", DatasetDomain.RETAIL, ("Sales", F))

    (revenue,) = KPIEngine().recommend(profile, df=df).all_kpis

    assert revenue.target_threshold == "Example target (not derived from your data): > +5% MoM Growth"


def test_a_kpi_with_no_benchmark_at_all_says_so_instead_of_inventing_one(make_dataset) -> None:
    profile, df = make_dataset("misc.csv", DatasetDomain.UNKNOWN, ("Weight", F))

    (kpi,) = KPIEngine().recommend(profile, df=df).all_kpis

    assert kpi.target_threshold.startswith("No baseline")


def test_detected_entities_choose_the_column_over_the_name(make_dataset) -> None:
    from app.models.detected_entity import DetectedEntity

    profile, df = make_dataset("shop.csv", DatasetDomain.RETAIL, ("takings", F), ("Quantity", I))
    entities = [DetectedEntity("takings", "revenue", 0.9, "detector")]

    report = KPIEngine().recommend(profile, entities=entities, df=df)

    assert "SUM('shop'[takings])" in {k.formula for k in report.all_kpis}


class FakeEngine:
    """Stands in for Analysis Services / the Power BI Modeling MCP."""

    def __init__(self, scale: float = 1.0, boom: bool = False, blank: bool = False) -> None:
        self.scale, self.boom, self.blank, self.calls = scale, boom, blank, []

    def execute(self, dax: str, table: str, df: pd.DataFrame):
        self.calls.append((dax, table))
        if self.boom:
            raise RuntimeError("syntax error near '('")
        if self.blank:
            return None
        return float(df["Sales"].sum()) * self.scale


@pytest.fixture
def engine_check_on(monkeypatch):
    monkeypatch.setenv("POWERPILOT_DAX_ENGINE_CHECK", "1")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("POWERPILOT_DAX_ENGINE_CHECK")
    get_settings.cache_clear()


def one_kpi_dataset(make_dataset):
    return make_dataset("shop.csv", DatasetDomain.RETAIL, ("Sales", F))


def test_the_engine_is_not_consulted_unless_the_flag_is_on(make_dataset) -> None:
    profile, df = one_kpi_dataset(make_dataset)
    fake = FakeEngine()

    KPIEngine(dax_executor=fake).recommend(profile, df=df)

    assert fake.calls == []


def test_when_the_dax_engine_agrees_the_kpi_stays_verified(make_dataset, engine_check_on) -> None:
    profile, df = one_kpi_dataset(make_dataset)
    fake = FakeEngine(scale=1 + 1e-9)  # inside the 1e-6 tolerance

    report = KPIEngine(dax_executor=fake).recommend(profile, df=df)

    assert report.total_kpis_recommended == 1
    assert fake.calls == [("SUM('shop'[Sales])", "shop")]


@pytest.mark.parametrize(
    ("fake", "fragment"),
    [
        (FakeEngine(scale=1.001), "returned"),
        (FakeEngine(boom=True), "could not evaluate"),
        (FakeEngine(blank=True), "BLANK"),
    ],
)
def test_when_the_dax_engine_disagrees_the_kpi_is_rejected(make_dataset, engine_check_on, fake, fragment) -> None:
    profile, df = one_kpi_dataset(make_dataset)

    report = KPIEngine(dax_executor=fake).recommend(profile, df=df)

    assert report.total_kpis_recommended == 0
    assert any(fragment in k.verification_note for k in report.rejected_kpis)


def test_the_flag_without_an_executor_is_ignored_not_fatal(make_dataset, engine_check_on) -> None:
    profile, df = one_kpi_dataset(make_dataset)

    assert KPIEngine().recommend(profile, df=df).total_kpis_recommended == 1


def test_a_dataset_with_no_numeric_columns_still_gets_a_verified_row_count(make_dataset) -> None:
    profile, df = make_dataset("names.csv", DatasetDomain.UNKNOWN, ("Name", T), ("City", T))

    report = KPIEngine().recommend(profile, df=df)

    (kpi,) = report.all_kpis
    assert kpi.name == "Total Record Count" and kpi.formula == "COUNTROWS('names')"
    assert kpi.verified and kpi.computed_value == float(len(df))
