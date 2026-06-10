"""
core/auth.py
JWT authentication and CurrentUser resolution for EMS ReadyKit.

Production mode (APP_ENV == "production"):
    Validates Azure AD access tokens (RS256) by:
      1. Fetching the JWKS from Azure AD and caching it in memory.
      2. Verifying the token signature, audience, issuer, expiry, and nbf.
      3. Extracting the "roles" claim (list of strings assigned via App Roles).
      4. Returning a CurrentUser dataclass.

Development / test mode (APP_ENV != "production"):
    Accepts fake Bearer tokens in the format "test-{role}", e.g.:
        Authorization: Bearer test-responder
        Authorization: Bearer test-supervisor
        Authorization: Bearer test-administrator
    This allows pytest and local curl usage without a real Azure AD tenant.

Refactor (Session B / REF-6):
    All logger.warning() calls now include extra={} fields for structured
    Log Analytics queries. Previously some used plain string interpolation
    which did not surface in structured queries.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient, PyJWKClientError

from ems_readykit.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Role constants (match app_role.value in Terraform) ───────────────────────

ROLE_ADMINISTRATOR = "Administrator"
ROLE_SUPERVISOR = "Supervisor"
ROLE_RESPONDER = "Responder"

ALL_ROLES = {ROLE_ADMINISTRATOR, ROLE_SUPERVISOR, ROLE_RESPONDER}

# ── CurrentUser dataclass ─────────────────────────────────────────────────────


@dataclass
class CurrentUser:
    """Resolved identity attached to each authenticated request."""

    user_id: str
    name: str
    email: str
    roles: list[str] = field(default_factory=list)

    def has_role(self, *roles: str) -> bool:
        return bool(set(self.roles) & set(roles))

    def require_role(self, *roles: str) -> None:
        if not self.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {list(roles)}",
            )


# ── JWKS client (cached, thread-safe via PyJWKClient) ────────────────────────

_jwks_client: Optional[PyJWKClient] = None
_jwks_client_built_at: float = 0.0
_JWKS_TTL_SECONDS = 86_400  # refresh once per day


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client, _jwks_client_built_at

    settings = get_settings()
    if not settings.jwks_uri:
        raise RuntimeError(
            "AZURE_AD_TENANT_ID is not configured. "
            "Cannot validate tokens in production mode."
        )

    now = time.monotonic()
    if _jwks_client is None or (now - _jwks_client_built_at) > _JWKS_TTL_SECONDS:
        logger.debug("Building JWKS client from %s", settings.jwks_uri)
        _jwks_client = PyJWKClient(settings.jwks_uri, cache_jwk_set=True)
        _jwks_client_built_at = now

    return _jwks_client


# ── Token validation ──────────────────────────────────────────────────────────


def _validate_azure_token(token: str) -> CurrentUser:
    settings = get_settings()

    if not settings.azure_ad_audience or not settings.token_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is not configured on this server.",
        )

    client_id = settings.azure_ad_client_id or ""
    accepted_audiences = list(
        {
            settings.azure_ad_audience,
            client_id,
            f"api://{client_id}",
        }
        - {""}
    )

    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientError as exc:
        logger.warning(
            "JWKS key lookup failed: %s",
            exc,
            extra={
                "action": "JWKS_LOOKUP_FAILED",
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve token signing key.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=accepted_audiences,
            issuer=settings.token_issuer,
            options={"require": ["exp", "nbf", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            token_aud = unverified.get("aud", "unknown")
        except Exception:
            token_aud = "could not decode"
        logger.warning(
            "Token validation failed: %s",
            exc,
            extra={
                "action": "TOKEN_REJECTED",
                "error": str(exc),
                "token_aud": token_aud,
                "accepted_audiences": accepted_audiences,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token_tid = payload.get("tid")
    if token_tid and token_tid != settings.azure_ad_tenant_id:
        logger.warning(
            "Token rejected: tid mismatch",
            extra={
                "action": "TENANT_MISMATCH",
                "token_tid": token_tid,
                "expected_tid": settings.azure_ad_tenant_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not for this tenant.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles: list[str] = payload.get("roles", [])
    unknown = set(roles) - ALL_ROLES
    if unknown:
        logger.warning(
            "Token contained unrecognised roles: %s",
            unknown,
            extra={
                "action": "UNKNOWN_ROLES",
                "unrecognised": list(unknown),
            },
        )

    user_id = payload.get("oid") or payload.get("sub", "unknown")

    return CurrentUser(
        user_id=user_id,
        name=payload.get("name", "Unknown"),
        email=payload.get("preferred_username") or payload.get("upn", ""),
        roles=[r for r in roles if r in ALL_ROLES],
    )


def _validate_test_token(token: str) -> CurrentUser:
    mapping = {
        "test-responder": (ROLE_RESPONDER,),
        "test-supervisor": (ROLE_SUPERVISOR,),
        "test-administrator": (ROLE_ADMINISTRATOR,),
        "test-admin": (ROLE_ADMINISTRATOR, ROLE_SUPERVISOR, ROLE_RESPONDER),
    }

    roles_tuple = mapping.get(token.lower())
    if roles_tuple is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Unknown test token '{token}'. "
                f"Valid values: {list(mapping.keys())}"
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_label = token.replace("test-", "").capitalize()
    return CurrentUser(
        user_id=f"test-user-{role_label.lower()}",
        name=f"Test {role_label}",
        email=f"test-{role_label.lower()}@ems.local",
        roles=list(roles_tuple),
    )


# ── Public entry point ────────────────────────────────────────────────────────


def resolve_current_user(token: str) -> CurrentUser:
    settings = get_settings()

    if settings.is_production:
        return _validate_azure_token(token)
    else:
        if token.lower().startswith("test-"):
            return _validate_test_token(token)
        if "." in token and settings.azure_ad_tenant_id:
            return _validate_azure_token(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid token provided. In dev mode use 'test-responder', 'test-supervisor', or 'test-administrator'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
