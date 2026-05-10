# Phase 3 — Authentication & RBAC Implementation Notes
# For Claude to pick up mid-session

## Status as of 2026-05-10
- Azure AD groups exist (identity_rbac module): administrators, supervisors, responders
- NO App Registration exists yet — must be created
- NO JWT middleware exists in Python yet
- Python app is working locally, deployment to Azure F1 is blocked by CPU quota
  (recommend switching to B1 in temp.tfvars before next deploy attempt)

## What needs to be built — in order

### Step 1 — Terraform: App Registration (identity_rbac/main.tf)  ← START HERE
ADD to identity_rbac/main.tf:
- azuread_application "ems_readykit" with:
    display_name = "EMS ReadyKit API"
    app_roles for: Administrator, Supervisor, Responder
    api block with oauth2_permission_scope: "api.access"
    identifier_uris = ["api://${azuread_application.ems_readykit.client_id}"]
- azuread_service_principal for the app
- azuread_app_role_assignment to wire each AD group to its app role
- Output: client_id, tenant_id

ADD to modules/app/main.tf app_settings:
    "AZURE_AD_TENANT_ID"  = var.tenant_id
    "AZURE_AD_CLIENT_ID"  = var.client_id
    "AZURE_AD_AUDIENCE"   = "api://${var.client_id}"

ADD to modules/app/variables.tf:
    variable "tenant_id"
    variable "client_id"

ADD to root main.tf module "app" block:
    tenant_id  = data.azurerm_client_config.current.tenant_id
    client_id  = module.identity_rbac.client_id

ADD to identity_rbac/outputs.tf:
    output "client_id"
    output "tenant_id"

### Step 2 — Python: core/auth.py (NEW FILE)
Validate Azure AD JWT bearer tokens using PyJWT.
Key things:
- Fetch JWKS from: https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys
- Cache JWKS in memory (refresh on unknown kid)
- Validate: signature, aud == AZURE_AD_AUDIENCE, iss, exp, nbf
- Extract roles claim (list of strings) from token
- Return a CurrentUser dataclass: user_id (oid claim), email, roles, name
- In non-production mode (APP_ENV != "production"): accept fake Bearer tokens
  format "test-{role}" e.g. "test-responder", "test-supervisor", "test-administrator"
  so the test suite works without a real Azure AD

Dependencies to add to requirements.txt:
    PyJWT[crypto]>=2.8.0

### Step 3 — Python: routers/deps.py (UPDATE)
Add to existing deps.py:
- get_current_user(token: HTTPAuthorizationCredentials) -> CurrentUser
  uses auth.py, raises 401 if invalid
- require_role(*roles) -> dependency factory
  raises 403 if user roles don't intersect with required roles
  usage: Depends(require_role("Supervisor", "Administrator"))

### Step 4 — Python: protect each router
Permissions per router:

  stations.py:
    GET  /stations          — Supervisor, Administrator
    POST /stations          — Administrator only
    GET  /stations/{id}     — Supervisor, Administrator
    PUT  /stations/{id}     — Administrator only
    DELETE /stations/{id}   — Administrator only

  vehicles.py:
    GET  /vehicles          — Supervisor, Administrator
    POST /vehicles          — Supervisor, Administrator
    GET  /vehicles/{id}     — Responder (own vehicle), Supervisor, Administrator
    PUT  /vehicles/{id}     — Supervisor, Administrator
    DELETE /vehicles/{id}   — Administrator only

  items.py:
    GET  /items             — all authenticated
    POST /items             — Supervisor, Administrator
    PUT  /items/{id}        — Supervisor, Administrator
    DELETE /items/{id}      — Administrator only

  inventory.py:
    GET  /inventory/*       — all authenticated
    POST /inventory/*       — Supervisor, Administrator

  checks.py:
    POST /checks/daily               — Responder, Supervisor, Administrator
    GET  /checks/daily/{id}          — Supervisor, Administrator
    GET  /checks/daily/vehicle/{id}  — Responder (own), Supervisor, Administrator
    POST /checks/controlled-substance — Responder, Supervisor, Administrator
    GET  /checks/controlled-substance/* — Supervisor, Administrator

  audit.py:
    GET  /audit             — Supervisor, Administrator

### Step 5 — Python: bind identity to check submissions
In checks.py POST handlers, replace free-text performed_by / primary_signer
with current_user.name or current_user.email from the JWT.
Keep the field in the schema as Optional so old data still reads fine.

### Step 6 — Tests: conftest.py (UPDATE)
Add fixtures:
- auth_headers_responder   = {"Authorization": "Bearer test-responder"}
- auth_headers_supervisor  = {"Authorization": "Bearer test-supervisor"}
- auth_headers_admin       = {"Authorization": "Bearer test-administrator"}

Update ALL existing test client calls to include auth headers.
Add new test class TestRBAC to test_routers.py covering:
- 401 with no token
- 403 Responder hitting Supervisor-only endpoint
- 200 Supervisor hitting Supervisor endpoint
- 200 Admin hitting any endpoint

### Step 7 — schemas: bind performed_by to identity
In daily_inventory_check.py schema:
  performed_by: Optional[str] = None  (filled from JWT in router, not caller)
In controlled_substance_check.py schema:
  primary_signer: Optional[str] = None
  secondary_signer: str  (still required — dual signer, second person must type theirs)

## Azure deployment steps (after all code is done)
1. Switch app_service_sku from F1 to B1 in temp.tfvars BEFORE anything else
2. terraform apply (identity_rbac changes + app settings changes)
3. In Azure Portal: manually add test users to AD groups for smoke testing
4. Rebuild deploy.zip (requirements.txt now has PyJWT)
5. az webapp deploy ...

## Files to create/modify
NEW:   app/ems_readykit/core/auth.py
MOD:   app/ems_readykit/routers/deps.py
MOD:   app/ems_readykit/routers/stations.py
MOD:   app/ems_readykit/routers/vehicles.py
MOD:   app/ems_readykit/routers/items.py
MOD:   app/ems_readykit/routers/inventory.py
MOD:   app/ems_readykit/routers/checks.py
MOD:   app/ems_readykit/routers/audit.py
MOD:   app/ems_readykit/core/config.py
MOD:   app/requirements.txt
MOD:   app/tests/conftest.py
MOD:   app/tests/test_routers.py
MOD:   iac/Terraform/modules/identity_rbac/main.tf
MOD:   iac/Terraform/modules/identity_rbac/outputs.tf
MOD:   iac/Terraform/modules/app/main.tf
MOD:   iac/Terraform/modules/app/variables.tf
MOD:   iac/Terraform/main.tf  (pass tenant_id + client_id to app module)
