"""Tests for the application settings layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings, get_settings


def test_defaults_are_usable_without_any_environment() -> None:
    settings = Settings()

    assert settings.app_name == "PowerPilot API"
    assert settings.max_upload_mb == 50
    assert settings.debug is False
    assert settings.result_cache_size > 0


def test_max_upload_bytes_is_derived_from_megabytes() -> None:
    assert Settings(max_upload_mb=1).max_upload_bytes == 1_048_576
    assert Settings(max_upload_mb=50).max_upload_bytes == 52_428_800


def test_non_positive_upload_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        Settings(max_upload_mb=0)

    with pytest.raises(ValueError, match="greater than 0"):
        Settings(max_upload_mb=-5)


def test_cors_origins_default_to_the_local_dev_servers() -> None:
    origins = Settings().cors_allow_origins

    assert "http://localhost:3000" in origins
    assert "*" not in origins, (
        "a wildcard origin with allow_credentials=True is rejected by browsers"
    )


def test_cors_origins_accept_a_comma_separated_string() -> None:
    settings = Settings(cors_allow_origins="https://a.example, https://b.example")

    assert settings.cors_allow_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_accept_a_json_array_string() -> None:
    settings = Settings(cors_allow_origins='["https://a.example","https://b.example"]')

    assert settings.cors_allow_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_accept_a_plain_list() -> None:
    settings = Settings(cors_allow_origins=["https://only.example"])

    assert settings.cors_allow_origins == ["https://only.example"]


def test_registry_paths_are_derived_from_the_data_directory(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)

    assert settings.registry_db_path == tmp_path / "registry.sqlite3"
    assert settings.datasets_path == tmp_path / "datasets"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POWERPILOT_MAX_UPLOAD_MB", "7")
    monkeypatch.setenv("POWERPILOT_DEBUG", "true")
    monkeypatch.setenv("POWERPILOT_RESULT_CACHE_SIZE", "3")

    settings = Settings()

    assert settings.max_upload_mb == 7
    assert settings.debug is True
    assert settings.result_cache_size == 3


def test_environment_prefix_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unprefixed variable must not leak into configuration."""
    monkeypatch.setenv("MAX_UPLOAD_MB", "999")

    assert Settings().max_upload_mb == 50


def test_unknown_environment_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POWERPILOT_TOTALLY_UNKNOWN_SETTING", "boom")

    assert Settings().app_name == "PowerPilot API"


def test_get_settings_returns_a_cached_singleton() -> None:
    assert get_settings() is get_settings()
