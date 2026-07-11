"""
core/config.py
Application settings loaded from environment variables (or .env).

In production the DATABASE_URL is pulled from Azure Key Vault via managed
identity at startup. In development it falls back to a local SQLite file
so no Azure or PostgreSQL dependencies are needed for local dev/testing.

Database backends:
  - Local dev/test: SQLite (sqlite:///./ems_readykit_dev.db)
  - Production:     PostgreSQL via Azure Key Vault secret
                    (postgresql+psycopg2://user:pass@host:5432/db?sslmode=require)

Auth:
  - REQUIRE_REAL_AUTH controls whether real Azure AD JWTs are required.
    Defaults to True (secure by default) — every deployed environment,
    regardless of its APP_ENV / resource-naming environment (dev/staging/
    prod), must explicitly opt out to accept the fake "test-{role}" bearer
    tokens. Local dev and the test suite set REQUIRE_REAL_AUTH=false
    explicitly (see conftest.py and CONTRIBUTING.md section 11).

  This is intentionally a *separate* setting from APP_ENV. APP_ENV only
  controls resource naming and cost tags — it was previously (incorrectly)
  also used to decide whether real auth was required, which meant the
  deployed App Service (environment=dev, APP_ENV=development) silently
  accepted the fake test-{role} tokens over the public internet. See the
  2026-07 incident write-up in docs/backlog_completed.md.

OpenAPI docs:
  - ENABLE_API_DOCS controls whether /docs, /redoc, and /openapi.json are
    served (see SEC-2 in main.py). Defaults to False (secure by default),
    for the same reason REQUIRE_REAL_AUTH is decoupled from APP_ENV above:
    this deployed App Service intentionally runs with APP_ENV=development
    for resource-naming/cost purposes, so gating docs on is_production left
    the OpenAPI docs publicly reachable on the live UAT app (caught by
    SEC-03 in the portfolio evidence checklist). Set ENABLE_API_DOCS=true
    locally, or temporarily on a deployed environment, when you need to
    capture the Swagger UI for evidence (see ARCH-04).
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

    # ── Auth ──────────────────────────────────────────────────────────────────
    # Secure by default: real Azure AD JWTs are required unless explicitly
    # disabled. See the module docstring above for why this is decoupled
    # from app_env/is_production.
    require_real_auth: bool = True

    # ── API docs ──────────────────────────────────────────────────────────────
    # Secure by default: OpenAPI docs are off unless explicitly enabled. See
    # the module docstring above for why this is decoupled from
    # app_env/is_production.
    enable_api_docs: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./ems_readykit_dev.db"

    # ── Azure Key Vault ───────────────────────────────────────────────────────
    key_vault_uri: Optional[str] = None

    # ── Azure AD / JWT Auth ───────────────────────────────────────────────────
    # Set automatically as App Service app settings by Terraform.
    azure_ad_tenant_id: Optional[str] = None
    azure_ad_client_id: Optional[str] = None
    azure_ad_audience: Optional[str] = None

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

    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def jwks_uri(self) -> Optional[str]:
        """Azure AD JWKS endpoint for public key retrieval."""
        if not self.azure_ad_tenant_id:
            return None
        return (
            f"https://login.microsoftonline.com/"
            f"{self.azure_ad_tenant_id}/discovery/v2.0/keys"
        )

    @property
    def token_issuer(self) -> Optional[str]:
        """Expected issuer claim in Azure AD access tokens."""
        if not self.azure_ad_tenant_id:
            return None
        return f"https://login.microsoftonline.com/" f"{self.azure_ad_tenant_id}/v2.0"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


def resolve_database_url(settings: Settings) -> str:
    """
    If KEY_VAULT_URI is configured, retrieve the PostgreSQL connection string
    from Azure Key Vault using the App Service Managed Identity.
    Falls back to DATABASE_URL from environment for local development.

    connection_timeout=10 on ManagedIdentityCredential caps how long we wait
    for the Azure IMDS token endpoint. Without a timeout, a slow/unready
    identity service on F1 cold start can hang indefinitely — no exception is
    raised, startup.sh produces no output, and Azure eventually stops the
    instance after the health check eviction window expires.
    """
    if not settings.key_vault_uri:
        return settings.database_url

    try:
        from azure.identity import ManagedIdentityCredential
        from azure.keyvault.secrets import SecretClient

        credential = ManagedIdentityCredential(connection_timeout=10)
        client = SecretClient(vault_url=settings.key_vault_uri, credential=credential)
        secret = client.get_secret("sql-connection-string")
        logging.getLogger(__name__).info(
            "Database URL resolved from Key Vault.",
            extra={"key_vault_uri": settings.key_vault_uri},
        )
        return secret.value
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Could not retrieve secret from Key Vault (%s). "
            "Falling back to DATABASE_URL env var.",
            exc,
        )
        return settings.database_url
