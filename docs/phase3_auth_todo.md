# Phase 3 — Authentication & RBAC Implementation Notes

## Status as of 2026-05-11 — ALL CODE COMPLETE

## ALL STEPS COMPLETED
- [x] Step 1 — Terraform: App Registration, service principal, app roles, group→role assignments
- [x] Step 2 — core/auth.py: JWT validation, JWKS caching, fake test tokens, CurrentUser
- [x] Step 3 — routers/deps.py: get_current_user, require_role factory
- [x] Step 4 — All 6 routers protected with require_role per permission map
- [x] Step 5 — performed_by and primary_signer bound to JWT identity in checks.py
- [x] Step 6 — conftest.py: auth_admin, auth_supervisor, auth_responder fixtures
- [x] Step 6 — test_routers.py: all calls have auth headers + new TestRBAC class
- [x] Step 7 — schemas updated: performed_by and primary_signer are Optional

## NEXT: Run tests locally
  cd app
  .venv\Scripts\Activate.ps1
  pip install PyJWT[crypto]==2.8.0
  pytest tests/ -v

## NEXT: Azure deployment
1. Change app_service_sku from "F1" to "B1" in temp.tfvars
2. terraform apply (creates App Registration + updates App Service settings)
3. Rebuild deploy.zip (requirements.txt now has PyJWT)
4. az webapp deploy ...
5. In Azure Portal: add yourself to ems-readykit-administrators group
6. Get a token: az account get-access-token --resource api://<client_id>
7. Test: curl -H "Authorization: Bearer <token>" https://app-ems-readykit-dev.azurewebsites.net/api/v1/stations
