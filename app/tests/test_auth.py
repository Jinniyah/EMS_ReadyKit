"""
tests/test_auth.py
Session AM: coverage for the real Azure AD JWT validation path in
core/auth.py (_validate_azure_token), which the rest of the suite never
exercises -- every other test authenticates via the dev/test fake-token
path (Bearer test-{role}), per auth.py's own module docstring. The full
suite previously reported core/auth.py at 44% coverage, almost entirely
this function and its branches.

Approach: generate one session-scoped RS256 test keypair and mint real,
correctly-signed JWTs against it. core/auth.py's module-level JWKS client
is never touched -- _get_jwks_client is monkeypatched per-test to return a
stub whose get_signing_key_from_jwt() hands back our test public key,
wrapped the same way PyJWKClient wraps a real one (an object exposing
.key). This exercises jwt.decode() and all of _validate_azure_token's
real logic (audience, issuer, expiry, nbf, tid, roles) with zero network
calls and zero dependency on a real Azure AD tenant.

Settings are monkeypatched via core.auth.get_settings (the name auth.py
imported it under) rather than core.config.get_settings, since patching
the call site is what actually changes what _validate_azure_token sees --
get_settings() is @lru_cache'd, and the cached singleton must not leak
into the rest of the suite. Patches are undone automatically via
monkeypatch's per-test teardown.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from ems_readykit.core import auth as auth_module
from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
    resolve_current_user,
)
from ems_readykit.core.config import Settings

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_CLIENT_ID = "22222222-2222-2222-2222-222222222222"
TEST_AUDIENCE = f"api://{TEST_CLIENT_ID}"
TEST_ISSUER = f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0"


@pytest.fixture(scope="session")
def rsa_keypair():
    """One RS256 keypair shared across all tests in this module."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def test_settings():
    """
    A Settings instance with Azure AD fields populated so jwks_uri and
    token_issuer resolve to our test tenant, matching the issuer/audience
    the test tokens below are signed for.
    """
    return Settings(
        azure_ad_tenant_id=TEST_TENANT_ID,
        azure_ad_client_id=TEST_CLIENT_ID,
        azure_ad_audience=TEST_AUDIENCE,
    )


class _FakeSigningKey:
    """Stand-in for jwt.api_jwk.PyJWK -- only the .key attribute is used."""

    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    """Stand-in for PyJWKClient -- returns our test public key for any token."""

    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


@pytest.fixture(autouse=True)
def _patch_auth_settings_and_jwks(monkeypatch, test_settings, rsa_keypair):
    """
    Applied to every test in this module: makes get_settings() (as imported
    into core.auth) return test_settings, and makes _get_jwks_client()
    return a fake client backed by our test public key. Individual tests
    can still call monkeypatch again to override test_settings for
    tenant-mismatch scenarios.
    """
    _, public_key = rsa_keypair
    monkeypatch.setattr(auth_module, "get_settings", lambda: test_settings)
    monkeypatch.setattr(
        auth_module, "_get_jwks_client", lambda: _FakeJWKSClient(public_key)
    )


def _make_token(
    private_key,
    *,
    audience=TEST_AUDIENCE,
    issuer=TEST_ISSUER,
    tenant_id: Optional[str] = TEST_TENANT_ID,
    roles: Optional[list] = None,
    exp_delta: timedelta = timedelta(hours=1),
    nbf_delta: timedelta = timedelta(minutes=-5),
    name: str = "Jamie Responder",
    email: str = "jamie@newbergems.local",
    oid: Optional[str] = "33333333-3333-3333-3333-333333333333",
    sub: Optional[str] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Mint a real RS256 JWT signed with the test private key."""
    now = datetime.now(timezone.utc)
    payload = {
        "aud": audience,
        "iss": issuer,
        "exp": now + exp_delta,
        "nbf": now + nbf_delta,
        "name": name,
        "preferred_username": email,
    }
    if tenant_id is not None:
        payload["tid"] = tenant_id
    if roles is not None:
        payload["roles"] = roles
    if oid is not None:
        payload["oid"] = oid
    if sub is not None:
        payload["sub"] = sub
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


class TestValidAzureToken:
    """A correctly signed, correctly claimed token resolves to CurrentUser."""

    def test_valid_token_returns_current_user(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(
            private_key,
            roles=[ROLE_RESPONDER],
            name="Jamie Responder",
            email="jamie@newbergems.local",
        )
        user = resolve_current_user(token)
        assert isinstance(user, CurrentUser)
        assert user.name == "Jamie Responder"
        assert user.email == "jamie@newbergems.local"
        assert user.roles == [ROLE_RESPONDER]

    def test_valid_token_with_multiple_roles(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, roles=[ROLE_ADMINISTRATOR, ROLE_SUPERVISOR])
        user = resolve_current_user(token)
        assert set(user.roles) == {ROLE_ADMINISTRATOR, ROLE_SUPERVISOR}

    def test_user_id_falls_back_to_oid(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, oid="oid-value", sub="sub-value")
        user = resolve_current_user(token)
        assert user.user_id == "oid-value"

    def test_user_id_falls_back_to_sub_when_oid_missing(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, oid=None, sub="sub-only-value")
        user = resolve_current_user(token)
        assert user.user_id == "sub-only-value"

    def test_email_falls_back_to_upn(self, rsa_keypair):
        private_key, _ = rsa_keypair
        # _make_token always sets preferred_username, so build the payload
        # manually here to omit it and exercise the upn fallback.
        now = datetime.now(timezone.utc)
        payload = {
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": now + timedelta(hours=1),
            "nbf": now - timedelta(minutes=5),
            "tid": TEST_TENANT_ID,
            "name": "No Preferred Username",
            "upn": "upn-fallback@newbergems.local",
            "oid": "oid-value",
            "roles": [ROLE_RESPONDER],
        }
        token = jwt.encode(payload, private_key, algorithm="RS256")
        user = resolve_current_user(token)
        assert user.email == "upn-fallback@newbergems.local"

    def test_accepts_bare_client_id_as_audience(self, rsa_keypair):
        """
        _validate_azure_token accepts azure_ad_audience, the bare client_id,
        and "api://{client_id}" as equally valid audiences (some Azure AD
        configurations issue tokens with the bare GUID as aud).
        """
        private_key, _ = rsa_keypair
        token = _make_token(private_key, audience=TEST_CLIENT_ID)
        user = resolve_current_user(token)
        assert isinstance(user, CurrentUser)


class TestExpiredAndNotYetValid:

    def test_expired_token_returns_401(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(
            private_key,
            exp_delta=timedelta(minutes=-10),
            nbf_delta=timedelta(minutes=-20),
        )
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_not_yet_valid_token_returns_401(self, rsa_keypair):
        """nbf in the future -- PyJWT raises ImmatureSignatureError, a
        subclass of InvalidTokenError, caught by the generic branch."""
        private_key, _ = rsa_keypair
        token = _make_token(private_key, nbf_delta=timedelta(minutes=10))
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401


class TestAudienceAndIssuer:

    def test_wrong_audience_returns_401(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, audience="api://some-other-app")
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401
        assert "invalid token" in exc_info.value.detail.lower()

    def test_wrong_issuer_returns_401(self, rsa_keypair):
        private_key, _ = rsa_keypair
        other_tenant = "99999999-9999-9999-9999-999999999999"
        token = _make_token(
            private_key,
            issuer=f"https://login.microsoftonline.com/{other_tenant}/v2.0",
        )
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401

    def test_missing_audience_claim_returns_401(self, rsa_keypair):
        """options={"require": [...]} on jwt.decode enforces aud is present."""
        private_key, _ = rsa_keypair
        now = datetime.now(timezone.utc)
        payload = {
            "iss": TEST_ISSUER,
            "exp": now + timedelta(hours=1),
            "nbf": now - timedelta(minutes=5),
            "tid": TEST_TENANT_ID,
            "name": "No Audience",
        }
        token = jwt.encode(payload, private_key, algorithm="RS256")
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401


class TestTenantMismatch:

    def test_tid_mismatch_returns_401(self, rsa_keypair):
        """
        tid is checked manually after jwt.decode succeeds -- a token can
        pass signature/audience/issuer validation yet still carry the wrong
        tenant ID claim if, e.g., the issuer string were ever to become
        tenant-agnostic. This guards that case explicitly.
        """
        private_key, _ = rsa_keypair
        other_tenant = "99999999-9999-9999-9999-999999999999"
        token = _make_token(private_key, tenant_id=other_tenant)
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401
        assert "tenant" in exc_info.value.detail.lower()

    def test_missing_tid_claim_is_not_rejected(self, rsa_keypair):
        """
        auth.py only checks tid mismatch `if token_tid and token_tid !=
        expected` -- a token with no tid claim at all is not rejected on
        that basis (some token shapes omit it). This pins that intentional
        leniency so a future change doesn't silently start requiring tid.
        """
        private_key, _ = rsa_keypair
        token = _make_token(private_key, tenant_id=None)
        user = resolve_current_user(token)
        assert isinstance(user, CurrentUser)


class TestRoleHandling:

    def test_no_roles_claim_returns_empty_roles(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, roles=None)
        user = resolve_current_user(token)
        assert user.roles == []

    def test_unknown_role_is_filtered_out(self, rsa_keypair):
        """
        Unrecognised role strings are logged as a warning but do not reject
        the token -- they're silently excluded from the returned roles list
        so an unexpected App Role assignment can't accidentally grant access
        to a role-gated route under a name require_role() never checks for.
        """
        private_key, _ = rsa_keypair
        token = _make_token(private_key, roles=[ROLE_RESPONDER, "SomeFutureRole"])
        user = resolve_current_user(token)
        assert user.roles == [ROLE_RESPONDER]
        assert "SomeFutureRole" not in user.roles

    def test_all_unknown_roles_returns_empty_roles(self, rsa_keypair):
        private_key, _ = rsa_keypair
        token = _make_token(private_key, roles=["TotallyMadeUp"])
        user = resolve_current_user(token)
        assert user.roles == []


class TestMalformedToken:

    def test_garbage_token_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user("not-a-real-jwt-at-all")
        assert exc_info.value.status_code == 401

    def test_token_signed_with_wrong_key_returns_401(self, rsa_keypair):
        """A token signed with a *different* RSA key must fail signature
        verification even though every claim is otherwise well-formed."""
        wrong_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        token = _make_token(wrong_private_key)
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user(token)
        assert exc_info.value.status_code == 401


class TestCurrentUserHelpers:
    """has_role / require_role on the resolved CurrentUser -- no JWT involved."""

    def test_has_role_true_when_role_present(self):
        user = CurrentUser(
            user_id="u1", name="N", email="e@x.com", roles=[ROLE_SUPERVISOR]
        )
        assert user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR) is True

    def test_has_role_false_when_role_absent(self):
        user = CurrentUser(
            user_id="u1", name="N", email="e@x.com", roles=[ROLE_RESPONDER]
        )
        assert user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR) is False

    def test_require_role_raises_403_when_missing(self):
        user = CurrentUser(
            user_id="u1", name="N", email="e@x.com", roles=[ROLE_RESPONDER]
        )
        with pytest.raises(HTTPException) as exc_info:
            user.require_role(ROLE_ADMINISTRATOR)
        assert exc_info.value.status_code == 403

    def test_require_role_passes_when_present(self):
        user = CurrentUser(
            user_id="u1", name="N", email="e@x.com", roles=[ROLE_ADMINISTRATOR]
        )
        user.require_role(ROLE_ADMINISTRATOR)  # must not raise


class TestDevModeFakeTokenFallthrough:
    """
    resolve_current_user's branching in non-production mode: test-{role}
    tokens still take the fake-token path even with Azure AD settings
    configured, since is_production gates the real-vs-fake decision, not
    whether azure_ad_tenant_id happens to be set.
    """

    def test_test_token_path_unaffected_by_azure_settings(self, test_settings):
        # test_settings has is_production == False by default (app_env
        # defaults to "development"), so the fake-token branch still wins
        # even though Azure AD fields are populated.
        user = resolve_current_user("test-responder")
        assert user.roles == [ROLE_RESPONDER]
        assert user.email == "test-responder@ems.local"

    def test_dotted_non_test_token_routes_to_azure_validation(self, rsa_keypair):
        """A token containing '.' that isn't a test-{role} string is routed
        to _validate_azure_token even outside production, as long as a
        tenant ID is configured -- this is what lets a developer test
        against a real Azure AD token locally without flipping APP_ENV."""
        private_key, _ = rsa_keypair
        token = _make_token(private_key, roles=[ROLE_SUPERVISOR])
        user = resolve_current_user(token)
        assert user.roles == [ROLE_SUPERVISOR]

    def test_garbage_non_dotted_token_returns_401_with_helpful_message(self):
        with pytest.raises(HTTPException) as exc_info:
            resolve_current_user("totally-unrecognized")
        assert exc_info.value.status_code == 401
        assert "test-responder" in exc_info.value.detail
