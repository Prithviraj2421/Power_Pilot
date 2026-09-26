"""Shared pytest fixtures for the PowerPilot backend test suite.

Two jobs:

1.  Expose the ``tests/datasets/*.csv`` sample files as ready-to-use fixtures.
    Each file carries deliberate imperfections (missing values, a casing
    inconsistency, one exact duplicate row, one numeric outlier) so the Data
    Quality & Preparation Engine has genuine work to do rather than scoring a
    perfect dataset every time.

2.  Share the expensive things. A full 12-stage pipeline run takes ~150-200ms;
    session-scoped result fixtures let export, copilot and route tests reuse one
    run instead of paying for it per test.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

DATASETS_DIR = Path(__file__).parent / "datasets"


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
# HTTP fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI test client bound to the real application instance."""
    return TestClient(app)


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
