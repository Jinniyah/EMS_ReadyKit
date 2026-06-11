# EMS ReadyKit -- OSI Layer Security Review
# Document version: 2.1
# Last updated: 2026-06-11 (Sessions H through T)
# Previous review: 2026-06-08 (v2.0)

---

## Purpose

This document maps the EMS ReadyKit stack against the OSI model to confirm which
layers are addressed, where coverage is partial, and what concrete actions remain
to close each gap. Updated to reflect the current production deployment
(Sessions A through T complete; UAT in progress).

---

## Layer-by-Layer Analysis

### Layer 1 -- Physical

| Item | Status |
|------|--------|
| Infrastructure ownership | N/A -- Azure managed |

**Findings:** Physical infrastructure is Microsoft's responsibility under the
Azure shared-responsibility model. No action required.

---

### Layer 2 -- Data Link

| Item | Status |
|------|--------|
| Network switching / MAC addressing | N/A -- Azure managed |

**Findings:** Handled at the hypervisor level by Azure's SDN fabric. No action
required.

---

### Layer 3 -- Network (IP)

| Item | Status |
|------|--------|
| VNet segmentation | Implemented |
| Subnet isolation (app / data / management) | Implemented |
| Private Endpoints for PostgreSQL, Key Vault, Storage | Provisioned |
| App Service VNet integration (outbound) | Configured (B1 tier) |
| Azure Firewall / NVA for outbound inspection | Not implemented |
| Route table with forced tunnelling | Blocked on Firewall |

**Findings:** `modules/network/main.tf` provisions a `/16` VNet
(`10.10.0.0/16`) with three segmented subnets:

- `snet-app` (`10.10.1.0/24`) -- App Service VNet integration (outbound only)
- `snet-data` (`10.10.2.0/24`) -- Private Endpoints; `private_endpoint_network_policies = "Disabled"`
- `snet-management` (`10.10.3.0/24`) -- SSH restricted to RFC1918 only

The App Service runs on B1, which supports VNet integration. The VNet,
subnets, and private endpoint infrastructure are provisioned and ready. Full
private PostgreSQL connectivity requires enabling VNet integration on the App
Service and adding a Private DNS Zone for
`privatelink.postgres.database.azure.com`. An Azure-services firewall rule on
PostgreSQL (Azure-originating traffic only) is the current interim measure.

**Gaps:**

1. No Azure Firewall or NVA. Outbound traffic from the app subnet to the
   internet (e.g., JWKS endpoint at `login.microsoftonline.com`) is unfiltered.
2. No User-Defined Routes (UDRs) forcing traffic through an inspection point.

**Actions to close gaps:**

| # | Action | File(s) | Priority |
|---|--------|---------|----------|
| L3-1 | Add Azure Firewall Basic to `modules/network` with a route table and UDR forcing `0.0.0.0/0` through it. Allow-list required FQDNs: Azure AD JWKS, PostgreSQL private endpoint, Key Vault. | `iac/Terraform/modules/network/main.tf` | Medium -- not urgent for current scale |
| L3-2 | Re-add route table associations to all three subnets once Firewall is in place. | Same file | Blocked on L3-1 |

---

### Layer 4 -- Transport (TCP/UDP)

| Item | Status |
|------|--------|
| NSG on app subnet (deny-all inbound) | Implemented |
| NSG on data subnet (PostgreSQL port 5432 from app only) | Implemented |
| NSG on management subnet (SSH RFC1918 only) | Implemented |
| NSG diagnostic logs to Log Analytics | Implemented |
| DDoS protection | Azure platform default only |

**Findings:** All three NSGs are defined with explicit deny-all inbound defaults
(priority 4096). The data NSG allows TCP/5432 only from `10.10.1.0/24`
(PostgreSQL, not 1433). The management NSG allows TCP/22 only from RFC1918
space. NSG flow logs route to Log Analytics for KQL-queryable traffic visibility.

**Gaps:**

1. DDoS Protection is Azure platform default (Basic), not Azure DDoS Protection
   Standard. Basic provides some mitigation; Standard adds adaptive tuning,
   attack analytics, and SLA guarantees.

**Actions to close gaps:**

| # | Action | File(s) | Priority |
|---|--------|---------|----------|
| L4-1 | Evaluate Azure DDoS Protection Standard (~$2,944/month). Cost-prohibitive at current scale. Document the tradeoff as a standalone ADR. | `docs/adr/` | Low -- document the decision |

---

### Layer 5 -- Session

| Item | Status |
|------|--------|
| Azure AD JWT authentication | Implemented |
| RS256 signature validation via JWKS | Implemented |
| Full claim validation (exp, nbf, iss, aud, oid) | Implemented |
| JWKS client caching with TTL refresh | Implemented |
| Role-based session authorization | Implemented |
| Station membership enforced per-request | Implemented |
| Dev-mode fake tokens gated to non-production | Implemented |
| Token lifetime documented | Implemented (ADR-006) |
| Token revocation / short-lived tokens | Relies on Azure AD defaults |

**Findings:** `core/auth.py` validates Azure AD access tokens fully -- signature,
audience, issuer, expiry, not-before, and object ID. The JWKS client is cached
in memory with a 24-hour TTL and refreshes automatically. Roles are extracted
from the `roles` claim and enforced per-endpoint via `require_role()`. Station
membership is enforced per-request via `require_station_membership()`.

The dev-mode fake token path (`Bearer test-{role}`) is cleanly gated behind
`APP_ENV != "production"` and generates deterministic emails
(`test-{role}@ems.local`) that map to seed-created `StationMember` rows.

Azure AD token lifetime and the HTTPS redirect strategy are documented in
ADR-006 (`docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`).

**Gaps:**

1. No short-circuit revocation check exists in the app if an account is
   compromised mid-session. Mitigation relies on Azure AD Continuous Access
   Evaluation (CAE) being enabled on the app registration.

**Actions to close gaps:**

| # | Action | File(s) | Priority |
|---|--------|---------|----------|
| L5-1 | Confirm Continuous Access Evaluation (CAE) is enabled on the Azure AD app registration -- provides near-real-time revocation without code changes. | Azure portal / App Registration | Low -- Azure AD config, not code |
| L5-2 | Standardise `extra={}` fields in `auth.py` JWKS failure log warning to match the shape used in `checks.py`. | `app/ems_readykit/core/auth.py` | Low |

---

### Layer 6 -- Presentation (Encoding / Encryption)

| Item | Status |
|------|--------|
| TLS enforcement (HTTPS) | Azure App Service "HTTPS Only" platform setting |
| Database connection SSL (`sslmode=require`) | Implemented |
| Key Vault retrieval over HTTPS (Managed Identity) | Implemented |
| Certificate management | Azure managed |
| HSTS on SWA frontend | `staticwebapp.config.json` (`max-age=31536000; includeSubDomains`) |
| In-app HTTPS redirect middleware | Intentionally omitted -- see note |

**Findings:** TLS is terminated at the Azure App Service managed frontend.
The database connection string includes `sslmode=require`. HSTS is set on
the SWA frontend via `staticwebapp.config.json`.

`HTTPSRedirectMiddleware` is intentionally NOT used in `main.py`. Azure App
Service terminates TLS at the load balancer and forwards requests to the
container as plain HTTP. The middleware cannot inspect `X-Forwarded-Proto`,
so it would redirect every request to HTTPS, causing an infinite redirect loop.
HTTPS enforcement is handled by the Azure App Service "HTTPS Only" platform
setting. This decision is documented in ADR-006 and in `main.py`.

**No open gaps at Layer 6.**

---

### Layer 7 -- Application

| Item | Status |
|------|--------|
| CORS origin restriction | Implemented |
| Per-request structured logging with correlation ID | Implemented |
| Role-based access control on all endpoints | Implemented |
| Rate limiting on check creation | Implemented (slowapi) |
| Pydantic v2 input validation | Implemented |
| Compliance audit events (DB-persisted, immutable) | Implemented |
| Audit log date-range filter | Implemented |
| API versioning (`/api/v1`) | Implemented |
| Health endpoint (excluded from log noise) | Implemented |
| OpenAPI docs disabled in production | Implemented (SEC-2) |
| Secret key validation at startup (production) | Implemented (SEC-4) |
| `X-Content-Type-Options: nosniff` on API | Implemented (`main.py` middleware) |
| `X-XSS-Protection: 1; mode=block` on API | Implemented (`main.py` middleware) |
| `Referrer-Policy` on API | Implemented (`main.py` middleware) |
| `X-Frame-Options: DENY` on SWA frontend | Implemented (`staticwebapp.config.json`) |
| `Content-Security-Policy` on SWA frontend | Implemented (`staticwebapp.config.json`) |
| `X-Content-Type-Options` on SWA frontend | Implemented (`staticwebapp.config.json`) |
| `check_date` server-derived (cannot be back-dated) | Implemented |
| `performed_by` JWT-bound (cannot be spoofed) | Implemented |
| Retired locations excluded from active lists | Implemented (`retired_at IS NULL` filter) |
| Structured logging in all routers | Partial |
| `X-Frame-Options` on API | Intentionally omitted -- see note |

**Findings:** Layer 7 is comprehensively addressed. Security headers are split
correctly between the two delivery surfaces:

- **API (`main.py` middleware):** `X-Content-Type-Options`, `X-XSS-Protection`,
  `Referrer-Policy` -- applied to every JSON API response.
- **SWA (`staticwebapp.config.json`):** `X-Frame-Options: DENY`,
  `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`,
  `Strict-Transport-Security` -- applied to all frontend responses.

`X-Frame-Options` is intentionally NOT set on the API. Setting it caused MSAL's
auth iframe to be blocked during redirect, producing
`BrowserAuthError: hash_empty_error`. The correct fix is to set it on the SWA
only, which is done. This decision is documented in `main.py`.

The audit event model is compliance-grade: actor identity (JWT-bound), entity
type, entity ID, action, severity, and station/vehicle context are all persisted
per-event. Submitted checks are immutable legal records -- line items cannot be
modified after submission.

Rate limiting is implemented via slowapi on the daily check creation endpoint.
The `TESTING=true` environment variable (set by conftest.py before main.py loads)
raises the limit to 99,999/minute so tests never exhaust the counter.

**Gaps:**

1. `inventory.py`, `stations.py`, `vehicles.py`, and `items.py` have incomplete
   structured logger calls on mutating operations. These resources produce audit
   events but limited log line context in `extra={}`.

**Actions to close gaps:**

| # | Action | File(s) | Priority |
|---|--------|---------|----------|
| L7-1 | Add structured `logger` calls at INFO level to `inventory.py`, `stations.py`, `vehicles.py`, and `items.py` on mutating operations. Include `entity_type`, `entity_id`, actor, and station context in `extra={}`. | `app/ems_readykit/routers/inventory.py`, `stations.py`, `vehicles.py`, `items.py` | Medium |
| L7-2 | Standardise `extra={}` fields in `auth.py` warning/error log calls to match `checks.py`. | `app/ems_readykit/core/auth.py` | Low |

---

## Consolidated Gap / Action List

All open actions in priority order:

| ID | Layer | Action | Priority | File(s) |
|----|-------|--------|----------|---------|
| L3-1 | 3 -- Network | Add Azure Firewall Basic + UDR for outbound inspection; allow-list Azure AD JWKS, PostgreSQL, Key Vault FQDNs | Medium | `iac/Terraform/modules/network/main.tf` |
| L7-1 | 7 -- Application | Add structured logger calls to inventory, stations, vehicles, items routers | Medium | `app/ems_readykit/routers/` |
| L3-2 | 3 -- Network | Re-add route table associations once Firewall is in place | Blocked on L3-1 | `iac/Terraform/modules/network/main.tf` |
| L4-1 | 4 -- Transport | Document DDoS Protection Standard cost/benefit as a standalone ADR | Low | `docs/adr/` |
| L5-1 | 5 -- Session | Confirm CAE is enabled on the Azure AD app registration | Low | Azure portal |
| L5-2 | 5 -- Session | Standardise `extra={}` in JWKS failure log in `auth.py` | Low | `app/ems_readykit/core/auth.py` |
| L7-2 | 7 -- Application | Standardise `extra={}` logging fields in `auth.py` | Low | `app/ems_readykit/core/auth.py` |

---

## Items Closed Since v1.0 (2026-05-21)

| ID | Layer | Item | Closed in |
|----|-------|------|-----------|
| L6-1 | 6 -- Presentation | HTTPSRedirectMiddleware -- resolved: Azure App Service "HTTPS Only" handles this; middleware would cause infinite redirects | Session H |
| L7-3 | 7 -- Application | `X-Content-Type-Options` and `X-Frame-Options` security headers | Session H -- split correctly: API headers in `main.py`, frontend headers in `staticwebapp.config.json` |
| -- | 7 -- Application | CSP and HSTS on SWA frontend | Session H -- `staticwebapp.config.json` |
| L5-ADR | 5 -- Session | Azure AD token lifetime and HTTPS redirect strategy documented | Session R -- ADR-006 written |
| -- | 7 -- Application | Rate limiting on check creation endpoint | Session L -- slowapi implemented; TESTING env var disables in test suite |
| -- | 7 -- Application | `check_date` server-derived; `performed_by` JWT-bound | Session L -- both enforced server-side |
| -- | 7 -- Application | Retired locations excluded from active API responses | Session U (UAT) -- `retired_at IS NULL` filter on list_locations |

---

## Layers with No Action Required

| Layer | Reason |
|-------|--------|
| Layer 1 -- Physical | Azure shared-responsibility; fully managed |
| Layer 2 -- Data Link | Azure SDN fabric; fully managed |
| Layer 6 -- Presentation | TLS via platform + database SSL + HSTS on SWA; no open gaps |

---

## References

- `docs/architecture.md` -- VNet and component diagram
- `docs/adr/ADR-006-Azure-AD-Token-Lifetime.md` -- token lifetime and HTTPS redirect strategy
- `iac/Terraform/modules/network/main.tf` -- NSG and subnet definitions
- `app/ems_readykit/core/auth.py` -- JWT validation and session resolution
- `app/ems_readykit/core/limiter.py` -- slowapi rate limiter configuration
- `app/ems_readykit/main.py` -- Middleware stack (security headers, CORS, request logging)
- `frontend/staticwebapp.config.json` -- SWA security headers (CSP, HSTS, X-Frame-Options)
- `app/ems_readykit/core/config.py` -- Environment configuration
