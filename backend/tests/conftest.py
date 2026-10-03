"""Shared pytest fixtures for the PowerPilot backend test suite.

Three jobs:

1.  **Isolation.** The dataset registry writes uploaded CSVs and a SQLite database
    under ``settings.data_dir``. Tests must never touch the real one, so this
    module points ``POWERPILOT_DATA_DIR`` at a temporary directory *before* the
    application is imported. The import order below is load-bearing: importing
    ``app.main`` builds the settings singleton, so the environment has to be set
    first.

2.  Expose the ``tests/datasets/*.csv`` sample files as ready-to-use fixtures.
    Each carries deliberate imperfections (missing values, a casing
    inconsistency, one exact duplicate row, one numeric outlier) so the Data
    Quality & Preparation Engine has genuine work to do rather than scoring a
    perfect dataset every time.

3.  Share the expensive things. A full 12-stage pipeline run takes ~200ms;
    session-scoped result fixtures let export, copilot and route tests reuse one
    run instead of paying for it per test.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterator

# --- Isolation: must precede any import of app.* --------------------------------
_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="powerpilot-tests-"))
os.environ["POWERPILOT_DATA_DIR"] = str(_TEST_DATA_DIR)

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.common.enums import DatasetDomain  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.datasets.cache import ResultCache  # noqa: E402
from app.datasets.service import DatasetService  # noqa: E402
from app.datasets.store import DatasetStore  # noqa: E402
from app.main import app  # noqa: E402
from app.models.column_profile import ColumnProfile  # noqa: E402
from app.models.dataset_profile import DatasetProfile  # noqa: E402
from app.models.master_intelligence_result import MasterIntelligenceResult  # noqa: E402
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline  # noqa: E402

DATASETS_DIR = Path(__file__).parent / "datasets"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_data_dir() -> Iterator[None]:
    """Remove the temporary registry directory once the session finishes."""
    yield
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """The temporary directory backing the registry during tests."""
    return _TEST_DATA_DIR


# ---------------------------------------------------------------------------
# Sample dataset fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def datasets_dir() -> Path:
    """Directory holding the domain sample CSV files."""
    return DATASETS_DIR


def _load(name: str) -> pd.DataFrame:
    path = DATASETS_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Sample dataset '{name}' is missing or empty at {path}. "
            "The test suite expects populated fixtures in tests/datasets/."
        )
    return pd.read_csv(path)


def _read_bytes(name: str) -> bytes:
    return (DATASETS_DIR / name).read_bytes()


@pytest.fixture
def retail_df() -> pd.DataFrame:
    """61-row retail orders dataset. Classifies as DatasetDomain.RETAIL."""
    return _load("retail.csv")


@pytest.fixture
def finance_df() -> pd.DataFrame:
    """61-row finance transactions dataset. Classifies as DatasetDomain.FINANCE."""
    return _load("finance.csv")


@pytest.fixture
def hr_df() -> pd.DataFrame:
    """61-row HR headcount dataset. Classifies as DatasetDomain.HR."""
    return _load("hr.csv")


@pytest.fixture
def healthcare_df() -> pd.DataFrame:
    """61-row patient admissions dataset. Classifies as DatasetDomain.HEALTHCARE."""
    return _load("healthcare.csv")


@pytest.fixture
def retail_csv_bytes() -> bytes:
    """Raw bytes of the retail sample, for upload and registry tests."""
    return _read_bytes("retail.csv")


# ---------------------------------------------------------------------------
# Pipeline fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pipeline() -> PowerPilotIntelligencePipeline:
    """A reusable pipeline instance. Stateless across runs, so session scope is safe."""
    return PowerPilotIntelligencePipeline()


@pytest.fixture(scope="session")
def retail_result(
    pipeline: PowerPilotIntelligencePipeline,
) -> MasterIntelligenceResult:
    """A full pipeline run over the retail sample, computed once per session.

    Treat this as READ-ONLY. It is shared by every test that requests it, so
    mutating it will leak into unrelated tests. Need to mutate? Use the
    ``pipeline`` and ``retail_df`` fixtures to build your own run.
    """
    return pipeline.run_pipeline(_load("retail.csv"), dataset_name="retail.csv")


@pytest.fixture(scope="session")
def finance_result(
    pipeline: PowerPilotIntelligencePipeline,
) -> MasterIntelligenceResult:
    """A full pipeline run over the finance sample. READ-ONLY, see ``retail_result``."""
    return pipeline.run_pipeline(_load("finance.csv"), dataset_name="finance.csv")


# ---------------------------------------------------------------------------
# Dataset registry fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dataset_service(tmp_path: Path) -> DatasetService:
    """A registry backed by this test's own tmp_path, isolated from every other test."""
    settings = get_settings()
    store = DatasetStore(
        db_path=tmp_path / "registry.sqlite3",
        datasets_dir=tmp_path / "datasets",
    )
    return DatasetService(store=store, settings=settings)


@pytest.fixture
def small_cache_service(tmp_path: Path) -> DatasetService:
    """A registry whose analysis cache holds a single entry, to exercise eviction."""
    settings = get_settings()
    store = DatasetStore(
        db_path=tmp_path / "registry.sqlite3",
        datasets_dir=tmp_path / "datasets",
    )
    return DatasetService(
        store=store,
        cache=ResultCache(max_entries=1, ttl_seconds=3600),
        settings=settings,
    )


# ---------------------------------------------------------------------------
# HTTP fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI test client bound to the real application instance."""
    return TestClient(app)


@pytest.fixture
def registered_dataset_id(client: TestClient, retail_csv_bytes: bytes) -> str:
    """Register the retail sample through the API and return its dataset id.

    Registration is content-hash deduplicated, so repeated use across tests
    resolves to the same dataset rather than re-running the pipeline.
    """
    response = client.post(
        "/api/v1/datasets",
        files={"file": ("retail.csv", io.BytesIO(retail_csv_bytes), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()["dataset"]["dataset_id"]


@pytest.fixture
def csv_upload() -> Callable[..., dict]:
    """Factory turning a DataFrame into a ``files=`` payload for TestClient.

    Usage::

        response = client.post(url, files=csv_upload(retail_df, "retail.csv"))
    """

    def _build(df: pd.DataFrame, filename: str = "dataset.csv") -> dict:
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return {"file": (filename, buffer, "text/csv")}

    return _build


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------


@pytest.fixture
def make_profile() -> Callable[..., DatasetProfile]:
    """Build a profile from (name, physical_type[, is_identifier]) tuples."""

    def build(name: str, domain: DatasetDomain, *columns: tuple) -> DatasetProfile:
        cols = [
            ColumnProfile(
                name=col[0],
                physical_type=col[1],
                nullable=False,
                unique=False,
                identifier=bool(col[2]) if len(col) > 2 else False,
                missing_count=0,
                unique_count=10,
            )
            for col in columns
        ]
        return DatasetProfile(
            dataset_name=name,
            total_rows=100,
            total_columns=len(cols),
            columns=cols,
            detected_domain=domain,
        )

    return build


@pytest.fixture
def make_dataset(make_profile) -> Callable[..., tuple[DatasetProfile, pd.DataFrame]]:
    """Like ``make_profile``, plus a matching DataFrame, so engines that verify against data can run.

    Numeric columns hold positive values, identifier columns are unique, other text columns cycle
    through three categories, and date columns span four months of ISO dates.
    """

    from app.common.enums import PhysicalType

    def build(name: str, domain: DatasetDomain, *columns: tuple, rows: int = 120):
        profile = make_profile(name, domain, *columns)
        frame = {}
        for column in profile.columns:
            if column.physical_type in (PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL):
                step = 1 if column.physical_type is PhysicalType.INTEGER else 0.5
                frame[column.name] = [(i % 9 + 1) * step + 1 for i in range(rows)]
            elif column.physical_type in (PhysicalType.DATE, PhysicalType.DATETIME):
                frame[column.name] = pd.date_range("2024-01-01", periods=rows).strftime("%Y-%m-%d")
            elif column.identifier:
                frame[column.name] = [f"{column.name[:3].upper()}-{i:04d}" for i in range(rows)]
            else:
                frame[column.name] = [f"{column.name[:3].title()}{i % 3}" for i in range(rows)]
        return profile, pd.DataFrame(frame)

    return build
