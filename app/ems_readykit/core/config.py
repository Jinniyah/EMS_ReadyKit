"""
core/config.py
Application settings loaded from environment variables (or .env).
In production the DATABASE_URL is pulled from Azure Key Vault via managed identity;
in development it falls back to a local SQLite file so no Azure dependencies are needed.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # ── Database ──────────────────────────────────────────────────────────────
    # Falls back to local SQLite when not set — makes local dev dependency-free.
    database_url: str = "sqlite:///./ems_readykit_dev.db"

    # ── Azure Key Vault ───────────────────────────────────────────────────────
    # When set, the app fetches 'sql-connection-string' from KV at startup
    # and overrides database_url.  Requires Managed Identity on the App Service.
    key_vault_uri: Optional[str] = None

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        level = v.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid log level: {v}")
        return level

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


def resolve_database_url(settings: Settings) -> str:
    """
    If KEY_VAULT_URI is configured, retrieve the SQL connection string from
    Azure Key Vault using the App Service's managed identity.
    Falls back to DATABASE_URL from environment for local development.
    """
    if not settings.key_vault_uri:
        return settings.database_url

    try:
        from azure.identity import ManagedIdentityCredential
        from azure.keyvault.secrets import SecretClient

        credential = ManagedIdentityCredential()
        client = SecretClient(vault_url=settings.key_vault_uri, credential=credential)
        secret = client.get_secret("sql-connection-string")
        logging.getLogger(__name__).info("Database URL resolved from Key Vault.")
        return secret.value
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "Could not retrieve secret from Key Vault (%s). "
            "Falling back to DATABASE_URL env var.",
            exc,
        )
        return settings.database_url
