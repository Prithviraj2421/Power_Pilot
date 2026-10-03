from __future__ import annotations

from typing import Callable

import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile

I, F, T = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT


@pytest.fixture
def make_profile() -> Callable[..., DatasetProfile]:
    """Build a profile from (name, physical_type[, is_identifier]) tuples."""

    def build(name: str, domain: DatasetDomain, *columns: tuple) -> DatasetProfile:
        cols = [
            ColumnProfile(
                name=c[0],
                physical_type=c[1],
                nullable=False,
                unique=False,
                identifier=bool(c[2]) if len(c) > 2 else False,
                missing_count=0,
                unique_count=10,
            )
            for c in columns
        ]
        return DatasetProfile(
            dataset_name=name,
            total_rows=100,
            total_columns=len(cols),
            columns=cols,
            detected_domain=domain,
        )

    return build
