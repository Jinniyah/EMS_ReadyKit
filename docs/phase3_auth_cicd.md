# EMS ReadyKit — Phase 3: Authentication, RBAC, and CI/CD
# Document version: 1.0
# Status: Complete
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 3 secured the API with Azure Active Directory JWT authentication and
enforced role-based access control on every endpoint. Authentication is
cryptographically verified using RS256-signed tokens from Azure AD with
JWKS key caching. All six routers are protected; the user's identity is
bound server-side to all check submissions so it cannot be overridden by
the request body. A GitHub Actions CI/CD pipeline was also established,
automating test execution and deployment on every push to main. The pipeline
permanently resolved the Windows zip path issue by building deployment
artifacts on Linux.

---

## 2. Objectives

| Objective | Description |
|-----------|-------------|
| Authentication | Azure AD JWT validation on all API endpoints |
| RBAC enforcement | Role-based access control per endpoint per role tier |
| Identity binding | performed_by and primary_signer bound to JWT — not client-supplied |
| Dev/test tokens | Fake tokens for local development without Azure AD dependency |
| CI/CD pipeline | Automated test + build + deploy on every push to main |
| Linux artifact build | Eliminate Windows backslash path issue permanently |
| Deployment verification | Health check confirms app is live after every deploy |

---

## 3. Scope

### In scope
- Azure AD App Registration with three app roles (Administrator, Supervisor, Responder)
- Azure AD groups with app role assignments via Terraform (identity_rbac module)
- JWT validation middleware (RS256, JWKS caching, audience/issuer verification)
- `CurrentUser` dataclass populated from JWT claims
- `require_role()` dependency factory used on all endpoints
- Dev/test fake token support (`test-administrator`, `test-supervisor`, `test-responder`)
- RBAC test fixtures in conftest.py
- GitHub Actions workflow (`.github/workflows/deploy.yml`)
- Zip build on Linux runner (eliminates backslash path issue)
- SCM IP restriction set to Allow for GitHub Actions runners
- CI/CD service principal with Website Contributor scope
- Health check verification step in deployment pipeline

### Out of scope
- MSAL frontend token acquisition (Phase 5)
- Frontend authentication flow (Phase 5)
- User provisioning automation (Phase 6)

---

## 4. Authentication Architecture

### Token validation flow

```
Client Request
    │
    ├── Authorization: Bearer {token}
    │
    ▼
FastAPI HTTPBearer dependency
    │
    ▼
core/auth.py — validate_token()
    ├── Fetch JWKS from Azure AD (cached, refreshed on miss)
    ├── Decode header → get kid (key ID)
    ├── Select matching public key from JWKS
    ├── Verify RS256 signature
    ├── Verify issuer (https://login.microsoftonline.com/{tenant_id}/v2.0)
    ├── Verify audience (api://{client_id})
    ├── Verify expiry
    └── Extract claims → CurrentUser(user_id, name, email, roles)
    │
    ▼
require_role(*roles) dependency
    ├── Check CurrentUser.roles against required roles
    ├── 403 if role not present
    └── Return CurrentUser to route handler
    │
    ▼
Route handler
    └── Uses current_user.name for performed_by / primary_signer
```

### Dev/test token bypass

When `APP_ENV=development`, the following bearer tokens are accepted without
Azure AD validation:

| Token | Role | Name |
|-------|------|------|
| `test-administrator` | Administrator | Test Administrator |
| `test-supervisor` | Supervisor | Test Supervisor |
| `test-responder` | Responder | Test Responder |

This allows local development and CI test execution without Azure AD dependency.
The bypass is blocked in production (`APP_ENV=production`).

---

## 5. RBAC Permission Matrix

| Endpoint Group | Responder | Supervisor | Administrator |
|----------------|-----------|------------|---------------|
| GET /stations | ❌ | ✅ | ✅ |
| POST /stations | ❌ | ❌ | ✅ |
| GET /vehicles | ✅ | ✅ | ✅ |
| POST /vehicles | ❌ | ❌ | ✅ |
| GET /items | ✅ | ✅ | ✅ |
| POST /items | ❌ | ❌ | ✅ |
| GET /inventory/* | ✅ | ✅ | ✅ |
| POST /inventory/lots | ❌ | ✅ | ✅ |
| POST /inventory/par-levels | ❌ | ✅ | ✅ |
| POST /inventory/compartments | ❌ | ✅ | ✅ |
| POST /checks/daily | ✅ | ✅ | ✅ |
| GET /checks/daily/{id} | ❌ | ✅ | ✅ |
| POST /checks/controlled-substance | ✅ | ✅ | ✅ |
| GET /checks/controlled-substance/* | ❌ | ✅ | ✅ |
| GET /audit | ❌ | ✅ | ✅ |

---

## 6. Identity Binding

A critical security property: the `performed_by` field on daily checks and the
`primary_signer` field on CS checks are set **server-side** from the validated
JWT. Any value submitted in the request body is ignored. This means:

- A responder cannot submit a check attributed to another person
- A CS check primary signer is cryptographically bound to the token presenter
- The audit trail is tamper-resistant at the application layer

---

## 7. Terraform Changes (Phase 3)

The `identity_rbac` module was extended to include:

- `azuread_application.ems_readykit` — App Registration with three app roles
- `azuread_service_principal.ems_readykit` — Service principal for the app
- `azuread_app_role_assignment` — Group-to-role assignments for all three groups
- `azuread_application.github_actions` — Service principal for CI/CD
- `azurerm_role_assignment.github_actions_website_contributor` — Website Contributor on resource group
- `azurerm_role_assignment.github_actions_tfstate_blob` — Storage Blob Data Contributor on tfstate account

**Bug fixed during Phase 3:** `allowed_member_types` on app roles contained
`"Group"` which is not a valid value. Corrected to `["User", "Application"]`.
Group assignment is handled via `azuread_app_role_assignment`, not this field.

---

## 8. CI/CD Pipeline

### Workflow file
`.github/workflows/deploy.yml`

### Trigger
Push to `main` branch

### Concurrency
Cancel-in-progress runs on the same branch (prevents stacking)

### Jobs

#### Job 1: test
- Runs on: `ubuntu-latest`
- Steps:
  1. Checkout code
  2. Set up Python 3.11 with pip cache
  3. Install dependencies (`pip install -r requirements.txt`)
  4. Run pytest (`pytest tests/ -v --tb=short`)
- If tests fail, deployment job does not run

#### Job 2: deploy
- Runs on: `ubuntu-latest`
- Condition: `github.ref == 'refs/heads/main' AND github.event_name == 'push' AND tests pass`
- Steps:
  1. Checkout code
  2. Build deployment zip on Linux (forward-slash paths — critical)
  3. Log in to Azure using `AZURE_CREDENTIALS` secret
  4. Deploy zip via `azure/webapps-deploy@v3`
  5. Wait 30 seconds
  6. Verify health: `curl /health` must return HTTP 200

### GitHub secrets required

| Secret | Value |
|--------|-------|
| `AZURE_CREDENTIALS` | JSON from `az ad sp create-for-rbac --sdk-auth` |

### Linux zip build (critical)
The zip is built on the Linux runner using `zip -r` (POSIX forward-slash paths).
Windows `Compress-Archive` produces backslash paths that Oryx cannot extract as
directories. This was the root cause of all deployment failures prior to Phase 3.

---

## 9. Startup Script

`app/startup.sh` runs at container startup before gunicorn:

1. Detect `APP_PATH` (Oryx extraction path, e.g. `/tmp/8deafb.../`)
2. Change to `APP_PATH` (all app files are here — alembic.ini, alembic/, antenv/)
3. Activate antenv virtualenv from `APP_PATH/antenv/bin/activate`
4. Run `alembic upgrade head` (idempotent — safe to run on every startup)
5. Exec gunicorn with UvicornWorker on port 8000

**Key insight:** Oryx compresses the built app into `output.tar.zst` stored in
`/home/site/wwwroot`. On container startup, it extracts to `APP_PATH` (/tmp/...).
The actual files (alembic.ini, alembic/, app code) are in APP_PATH, not wwwroot.
Previous versions of startup.sh cd'd to wwwroot, causing `alembic.ini NOT FOUND`.

---

## 10. Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| JWT validation | `app/ems_readykit/core/auth.py` | ✅ Complete |
| RBAC dependency | `app/ems_readykit/routers/deps.py` | ✅ Complete |
| All routers protected | All 6 router files | ✅ Complete |
| Azure AD App Registration + roles | Terraform identity_rbac module | ✅ Complete |
| CI/CD workflow | `.github/workflows/deploy.yml` | ✅ Complete |
| GitHub Actions service principal | Terraform identity_rbac module | ✅ Complete |
| Startup script (fixed) | `app/startup.sh` | ✅ Complete |
| RBAC test fixtures | `app/tests/conftest.py` | ✅ Complete |
| RBAC test class | `app/tests/test_routers.py` — TestRBAC | ✅ Complete |
| CI/CD badge in README | `README.md` | ✅ Complete |

---

## 11. Testing

### RBAC test coverage

| Test | Result |
|------|--------|
| Unauthenticated request returns 401/403 | ✅ Pass |
| Responder cannot list stations (403) | ✅ Pass |
| Responder cannot create station (403) | ✅ Pass |
| Supervisor can list stations (200) | ✅ Pass |
| Supervisor cannot create station (403) | ✅ Pass |
| Administrator can create station (201) | ✅ Pass |
| Responder can read items (200) | ✅ Pass |
| Responder cannot create item (403) | ✅ Pass |
| Responder cannot access audit log (403) | ✅ Pass |
| Supervisor can access audit log (200) | ✅ Pass |
| Responder can submit daily check (201) | ✅ Pass |
| Responder cannot view check detail (403) | ✅ Pass |

Total: 74/74 tests passing.

---

## 12. Known Issues and Tradeoffs

| Item | Detail | Resolution |
|------|--------|------------|
| SCM IP restriction opened | GitHub Actions runners have dynamic IPs — cannot allowlist | Website Contributor SP auth is the security control; IP restriction removed from SCM |
| F1 tier CPU quota | F1 has 60 CPU minutes/day — exceeded by first cold start | Upgrade to B1 resolves. B1 applied via `az appservice plan update` |
| JWKS cache is in-process | Cache resets on restart; first request fetches keys | Acceptable. Keys rotate infrequently. TTL is effectively pod lifetime. |

---

## 13. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 1 | Requires: Azure AD infrastructure, App Service, Key Vault |
| Phase 2 | Requires: All API endpoints to protect |
| Phase 5 | Provides: Auth infrastructure for MSAL frontend integration |

---

## 14. Next Phase

Phase 4 — Compartments, Line Items, and Expiration Tracking: Physical
compartment model, per-item check line items matching the paper inventory
form, and daily expiration verification with lot-level tracking.
