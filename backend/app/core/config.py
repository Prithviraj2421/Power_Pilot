"""Application configuration.

Every tunable value the backend needs lives here and is sourced from the
environment (optionally via a .env file) with a safe default. Nothing reads
os.environ directly elsewhere in the codebase.

Environment variables use the ``POWERPILOT_`` prefix, so the ``max_upload_mb``
setting below is set with ``POWERPILOT_MAX_UPLOAD_MB=100``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="POWERPILOT_",
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application identity -------------------------------------------------
    app_name: str = "PowerPilot API"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- CORS -----------------------------------------------------------------
    # An explicit origin list. A wildcard "*" combined with allow_credentials=True
    # is rejected by every browser, so credentialed requests need real origins.
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    cors_allow_credentials: bool = True

    # --- Uploads --------------------------------------------------------------
    max_upload_mb: int = 50

    # --- Dataset registry -----------------------------------------------------
    # Directory holding uploaded CSV source files plus the metadata database.
    # The CSV is the durable source of truth: an analysis result is derived data
    # and can always be recomputed from it.
    data_dir: Path = BACKEND_ROOT / "data"
    registry_db_filename: str = "registry.sqlite3"
    datasets_dirname: str = "datasets"

    # In-memory analysis result cache. A cache miss re-runs the pipeline from the
    # stored CSV, so these bound memory without ever losing a dataset.
    result_cache_size: int = 32
    result_cache_ttl_seconds: int = 3600

    # Upper bound on datasets retained on disk. The oldest by last-access are
    # pruned past this. Set to 0 to disable pruning.
    max_stored_datasets: int = 200

    # --- Email delivery -------------------------------------------------------
    # Plain SMTP rather than a vendor SDK, so the same settings work against
    # Gmail, Amazon SES's SMTP endpoint, SendGrid's SMTP relay or a self-hosted
    # server. Email is disabled until smtp_host and smtp_from_address are both
    # set; the endpoint reports that explicitly instead of pretending to send.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
    smtp_from_name: str = "PowerPilot"
    # STARTTLS on the standard submission port. Set smtp_use_ssl for implicit
    # TLS on port 465 instead; the two are mutually exclusive.
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 30
    max_email_recipients: int = 20

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string so the env var stays easy to write.

        A JSON array is also accepted, since that is what pydantic-settings
        conventionally expects for list fields.
        """
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"cors_allow_origins is not valid JSON: {exc}") from exc

        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    @field_validator("max_upload_mb")
    @classmethod
    def _positive_upload_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_upload_mb must be greater than 0")
        return value

    @model_validator(mode="after")
    def _tls_modes_are_exclusive(self) -> "Settings":
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError(
                "smtp_use_tls (STARTTLS) and smtp_use_ssl (implicit TLS) are mutually "
                "exclusive. Use smtp_use_ssl for port 465, smtp_use_tls for port 587."
            )
        return self

    @property
    def email_enabled(self) -> bool:
        """Whether outbound email is configured well enough to attempt a send."""
        return bool(self.smtp_host.strip() and self.smtp_from_address.strip())

    @property
    def smtp_sender(self) -> str:
        """The From header value, with a display name when one is configured."""
        name = self.smtp_from_name.strip()
        address = self.smtp_from_address.strip()
        return f"{name} <{address}>" if name else address

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def registry_db_path(self) -> Path:
        return self.data_dir / self.registry_db_filename

    @property
    def datasets_path(self) -> Path:
        return self.data_dir / self.datasets_dirname


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton.

    Cached so the .env file is read once. Tests that need different values call
    ``get_settings.cache_clear()`` after patching the environment.
    """
    return Settings()
