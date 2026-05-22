# EMS ReadyKit — OSI Layer Security Review
# Document version: 1.0
# Last updated: 2026-05-21

---

## Purpose

This document maps the EMS ReadyKit stack against the OSI model to confirm which
layers are addressed, where coverage is partial, and what concrete actions remain
to close each gap. It was produced by reviewing the live codebase and Terraform
configuration on 2026-05-21.

---

## Layer-by-Layer Analysis

### Layer 1 — Physical

| Item | Status |
|------|--------|
| Infrastructure ownership | ✅ N/A — Azure managed |

**Findings:** Physical infrastructure is Microsoft's responsibility under the
Azure shared-responsibility model. No action required.

---

### Layer 2 — Data Link

| Item | Status |
|------|--------|
| Network switching / MAC addressing | ✅ N/A — Azure managed |

**Findings:** Handled at the hypervisor level by Azure's SDN fabric. No action
required.

---

### Layer 3 — Network (IP)

| Item | Status |
|------|--------|
| VNet segmentation | ✅ Implemented |
| Subnet isolation (app / data / management) | ✅ Implemented |
| Private Endpoints for SQL, Key Vault, Storage | ✅ Provisioned |
| App Service VNet integration (outbound) | ✅ Configured |
| Azure Firewall / NVA for outbound inspection | ❌ Not implemented |
| Route table with forced tunnelling | ❌ Not implemented |

**Findings:** `modules/network/main.tf` provisions a `/16` VNet
(`10.10.0.0/16`) with three segmented subnets:

- `snet-app` (`10.10.1.0/24`) — App Service VNet integration (outbound only)
- `snet-data` (`10.10.2.0/24`) — Private Endpoints; `private_endpoint_network_policies = "Disabled"`
- `snet-management` (`10.10.3.0/24`) — SSH restricted to RFC1918 only

The code correctly documents that App Service VNet integration is **outbound-only**
and that inbound internet traffic enters via Azure's managed frontend, not the
subnet. The empty route table placeholder was intentionally removed because an
empty table "creates a false impression of traffic control" — an honest and
correct call.

**Gaps:**

1. No Azure Firewall or NVA. Outbound traffic from the app subnet to the
   internet (e.g., JWKS endpoint at `login.microsoftonline.com`) is unfiltered
   and uninspected.
2. No User-Defined Routes (UDRs) forcing traffic through an inspection point.

**Actions to close gaps:**

| # | Action | File(s) to change | Priority |
|---|--------|-------------------|----------|
| L3-1 | Add an Azure Firewall (or Azure Firewall Basic for cost) to `modules/network` and create a route table with a UDR forcing `0.0.0.0/0` through it. Add an application rule collection allowing only required FQDNs (Azure AD JWKS, Azure SQL, Key Vault). | `iac/Terraform/modules/network/main.tf` (new `azurerm_firewall`, `azurerm_route_table`, `azurerm_subnet_route_table_association`) | Medium — dev tier, not urgent |
| L3-2 | Re-add the route table resource to all three subnets once a Firewall is in place. The Terraform comment already marks the location. | Same file — see the existing comment block | Blocked on L3-1 |

---

### Layer 4 — Transport (TCP/UDP)

| Item | Status |
|------|--------|
| NSG on app subnet (deny-all inbound) | ✅ Implemented |
| NSG on data subnet (SQL port 1433 from app only) | ✅ Implemented |
| NSG on management subnet (SSH RFC1918 only) | ✅ Implemented |
| NSG diagnostic logs → Log Analytics | ✅ Implemented |
| DDoS protection | ⚠️ Azure platform default only |

**Findings:** All three NSGs are defined with explicit deny-all inbound defaults
(priority 4096). The data NSG allows TCP/1433 only from `10.10.1.0/24`. The
management NSG allows TCP/22 only from RFC1918 space. NSG flow logs are routed
to Log Analytics via diagnostic settings — giving KQL-queryable traffic
visibility. This is solid Layer 4 posture.

**Gaps:**

1. DDoS protection is Azure platform default (basic), not Azure DDoS Protection
   Standard. Basic provides some mitigation; Standard adds adaptive tuning,
   attack analytics, and SLA guarantees.

**Actions to close gaps:**

| # | Action | File(s) to change | Priority |
|---|--------|-------------------|----------|
| L4-1 | Evaluate Azure DDoS Protection Standard for the VNet. At ~$2,944/month it is cost-prohibitive for a dev deployment, but should be assessed before any production use. Document the decision in an ADR. | New `docs/adr/ADR-005-DDoS-Strategy.md` | Low — document the tradeoff |

---

### Layer 5 — Session

| Item | Status |
|------|--------|
| Azure AD JWT authentication | ✅ Implemented |
| RS256 signature validation via JWKS | ✅ Implemented |
| Full claim validation (exp, nbf, iss, aud, oid) | ✅ Implemented |
| JWKS client caching with TTL refresh | ✅ Implemented |
| Role-based session authorization | ✅ Implemented |
| Token revocation / short-lived tokens | ⚠️ Relies on Azure AD defaults |

**Findings:** `core/auth.py` validates Azure AD access tokens fully — signature,
audience, issuer, expiry, not-before, and object ID. The JWKS client is cached
in memory with a 24-hour TTL and refreshes automatically. Roles (`Responder`,
`Supervisor`, `Administrator`) are extracted from the `roles` claim and enforced
per-endpoint via `require_role()`. The dev-mode fake token path (`test-{role}`)
is cleanly gated behind `APP_ENV != "production"`.

**Gaps:**

1. Token lifetime and revocation depend entirely on Azure AD tenant configuration
   (default access token lifetime is 60–90 minutes). There is no short-circuit
   revocation check in the app if an account is compromised mid-session.

**Actions to close gaps:**

| # | Action | File(s) to change | Priority |
|---|--------|-------------------|----------|
| L5-1 | Document the expected Azure AD token lifetime configuration in `runbook.md`. Confirm Continuous Access Evaluation (CAE) is enabled on the Azure AD app registration — this provides near-real-time revocation without app changes. | `docs/runbook.md` | Low — Azure AD config, not code |
| L5-2 | Add structured `extra={}` fields to the JWKS failure log warning in `auth.py` (currently inconsistent with the rest of the logging strategy). | `app/ems_readykit/core/auth.py` | Low |

---

### Layer 6 — Presentation (Encoding / Encryption)

| Item | Status |
|------|--------|
| TLS enforcement (HTTPS) | ✅ Azure App Service frontend |
| Database connection SSL (`sslmode=require`) | ✅ Implemented |
| Key Vault retrieval over HTTPS (Managed Identity) | ✅ Implemented |
| Certificate management | ✅ Azure managed |
| In-app HTTPS redirect middleware | ❌ Not implemented |

**Findings:** TLS is terminated at the Azure App Service managed frontend.
The database connection string includes `sslmode=require`. Key Vault access
uses Managed Identity over HTTPS. Certificate management is handled by Azure.
However, `main.py` contains no `HTTPSRedirectMiddleware` — the app itself
does not enforce HTTPS at the application layer.

**Gaps:**

1. No in-app HTTPS redirect. If the app is ever placed behind a different
   reverse proxy that does not enforce TLS, HTTP traffic would be accepted
   silently.

**Actions to close gaps:**

| # | Action | File(s) to change | Priority |
|---|--------|-------------------|----------|
| L6-1 | Add Starlette's `HTTPSRedirectMiddleware` to `main.py`, gated to production only (`if settings.is_production`). This provides defense-in-depth without breaking local HTTP dev. See implementation note below. | `app/ems_readykit/main.py` | Low — one-line add, worth doing |

**Implementation note for L6-1:**
```python
# Add after the existing CORS middleware block, inside create_app():
if settings.is_production:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)
```

---

### Layer 7 — Application

| Item | Status |
|------|--------|
| CORS origin restriction | ✅ Implemented |
| Per-request structured logging with correlation ID | ✅ Implemented |
| Role-based access control on all endpoints | ✅ Implemented |
| Pydantic v2 input validation | ✅ Implemented |
| Compliance audit events (DB-persisted) | ✅ Implemented |
| API versioning (`/api/v1`) | ✅ Implemented |
| Health endpoint (excluded from log noise) | ✅ Implemented |
| Structured logging in all routers | ⚠️ Partial |
| HTTP security response headers | ❌ Not implemented |

**Findings:** Layer 7 is the most thoroughly addressed. CORS, auth, RBAC, Pydantic
validation, audit events, and request logging with correlation IDs are all
present in `main.py` and the router modules. The audit event model is
compliance-grade — actor identity, entity type, entity ID, and severity are
all persisted.

**Gaps:**

1. `inventory.py`, `stations.py`, `vehicles.py`, and `items.py` have no
   structured logger calls. Admin or supervisor actions on these resources
   leave no log lines beyond the audit event.
2. `extra={}` fields are inconsistent across modules — `checks.py` uses them
   fully; `auth.py` does not.
3. No HTTP security headers (`X-Content-Type-Options`, `X-Frame-Options`).

**Actions to close gaps:**

| # | Action | File(s) to change | Priority |
|---|--------|-------------------|----------|
| L7-1 | Add structured `logger` calls to `inventory.py`, `stations.py`, `vehicles.py`, and `items.py` at INFO level on mutating operations (POST, PATCH, DELETE). Include `entity_type`, `entity_id`, and actor context in `extra={}`. | `app/ems_readykit/routers/inventory.py`, `stations.py`, `vehicles.py`, `items.py` | Medium |
| L7-2 | Standardise `extra={}` fields in `auth.py` warning and error log calls to match the shape used in `checks.py`. | `app/ems_readykit/core/auth.py` | Low |
| L7-3 | Add a security headers middleware to `main.py` setting `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`. | `app/ems_readykit/main.py` | Low |

---

## Consolidated Gap / Action List

All open actions in priority order:

| ID | Layer | Action | Priority | File(s) |
|----|-------|--------|----------|---------|
| L3-1 | 3 — Network | Add Azure Firewall and UDR for outbound inspection; allow-list required FQDNs only | Medium | `iac/Terraform/modules/network/main.tf` |
| L7-1 | 7 — Application | Add structured logger calls to inventory, stations, vehicles, and items routers | Medium | `app/ems_readykit/routers/*.py` |
| L3-2 | 3 — Network | Re-add route table to subnets once Firewall is in place | Blocked on L3-1 | `iac/Terraform/modules/network/main.tf` |
| L4-1 | 4 — Transport | Document DDoS Protection Standard tradeoff in a new ADR | Low | `docs/adr/ADR-005-DDoS-Strategy.md` |
| L5-1 | 5 — Session | Document Azure AD token lifetime and confirm CAE is enabled in `runbook.md` | Low | `docs/runbook.md` |
| L5-2 | 5 — Session | Add structured `extra={}` to JWKS failure log in `auth.py` | Low | `app/ems_readykit/core/auth.py` |
| L6-1 | 6 — Presentation | Add `HTTPSRedirectMiddleware` (production-gated) to `main.py` | Low | `app/ems_readykit/main.py` |
| L7-2 | 7 — Application | Standardise `extra={}` logging fields in `auth.py` | Low | `app/ems_readykit/core/auth.py` |
| L7-3 | 7 — Application | Add `X-Content-Type-Options` and `X-Frame-Options` security headers to `main.py` | Low | `app/ems_readykit/main.py` |

---

## Layers with No Action Required

| Layer | Reason |
|-------|--------|
| Layer 1 — Physical | Azure shared-responsibility model; fully managed |
| Layer 2 — Data Link | Azure SDN fabric; fully managed |

---

## References

- `docs/architecture.md` — VNet and component diagram
- `docs/req_security.txt` — Security and monitoring requirements
- `iac/Terraform/modules/network/main.tf` — NSG and subnet definitions
- `app/ems_readykit/core/auth.py` — JWT validation and session resolution
- `app/ems_readykit/main.py` — Middleware stack (CORS, request logging)
- `app/ems_readykit/core/config.py` — Environment configuration and TLS settings
