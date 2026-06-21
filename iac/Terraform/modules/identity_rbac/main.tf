// modules/identity_rbac/main.tf
// Creates the Azure AD App Registration, app roles, AD groups, and Azure RBAC
// assignments for EMS ReadyKit per ADR-002.
//
// Also creates a CI/CD service principal for GitHub Actions deployments.
//
// Roles:
//   Administrator — Full access; Reader at subscription scope in Azure RBAC
//   Supervisor    — Station-level management; Contributor at resource group scope
//   Responder     — Submit checks and read own vehicle; application-enforced only
//
// sign_in_audience / api block (Session AH+):
// EMS ReadyKit must support personal Microsoft accounts (e.g. @gmail.com,
// @outlook.com) signing in via Azure AD external identities, not just
// accounts native to this tenant. AzureADMyOrg (the provider default when
// sign_in_audience is unset) rejects personal Microsoft accounts entirely —
// this previously caused administrators with personal email addresses to be
// unable to sign in. Do not remove sign_in_audience or revert it to the
// provider default without confirming all admin accounts are tenant-native.
//
// requested_access_token_version = 2 is required so the issued access token
// uses v2 claim shapes — core/auth.py reads the `preferred_username` claim
// (a v2-token claim) to resolve CurrentUser.email. Reverting to v1 tokens
// changes claim availability and will break station-membership lookups that
// key off email.
//
// Two oauth2_permission_scope blocks (api.access + user_impersonation):
// The frontend (frontend/src/shared/api/authConfig.js) requests the
// "api.access" scope by name when acquiring API tokens. A separate, newer
// "user_impersonation" scope also exists live. Both must stay defined here —
// dropping either one breaks something: dropping api.access breaks the
// frontend's token acquisition (AADSTS650053 "scope not supported");
// dropping user_impersonation reverts to a value the live app no longer
// expects. If the frontend is ever migrated to request user_impersonation
// instead, api.access can be retired then — not before.
//
// required_resource_access / single_page_application / web — NOT managed
// here, deliberately, for two different reasons:
//
//   required_resource_access: the live app self-references its own
//   client_id (it requests delegated consent for its own api.access scope —
//   a SPA-calls-own-API pattern). The azuread provider (~> 2.47) rejects
//   self-referential blocks inside the same resource ("Configuration for
//   azuread_application.ems_readykit may not refer to itself") and has no
//   decoupled resource for this in this provider version (see
//   hashicorp/terraform-provider-azuread issues #924 and #1182 — still open
//   as of writing). Hardcoding the client_id instead of referencing it would
//   silently go stale if the app registration is ever recreated, which is a
//   worse failure mode than just leaving this block unmanaged.
//
//   single_page_application / web: the azuread provider requires a trailing
//   slash on origin-only redirect URIs (e.g. "https://host/"), but the
//   frontend's MSAL config (frontend/src/shared/api/authConfig.js) sets
//   redirectUri to window.location.origin, which per spec NEVER has a
//   trailing slash. The live App Registration was configured by hand (via
//   the Azure Portal, which validates differently / more leniently) with
//   the no-trailing-slash redirect URIs that actually match what MSAL
//   sends, and sign-in works correctly today. Writing a trailing-slash
//   version here would pass `terraform plan` but break real sign-in,
//   including for personal Microsoft accounts.
//
// ignore_changes excludes all three blocks from drift detection so
// Terraform stops trying to "fix" the working manual config on every apply.
// If this is ever revisited, the right fix is upstream — either wait for a
// decoupled required_resource_access resource in a future provider version,
// or get MSAL's redirect handling and the provider's validation to agree on
// a single canonical form — not just override one side by hand again.

resource "azuread_application" "ems_readykit" {
  display_name     = "EMS ReadyKit API"
  sign_in_audience  = "AzureADandPersonalMicrosoftAccount"

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      admin_consent_description  = "Access the EMS ReadyKit API on behalf of the signed-in user"
      admin_consent_display_name = "Access EMS ReadyKit API"
      enabled                    = true
      id                         = "00000000-0000-0000-0000-000000000001"
      type                       = "User"
      user_consent_description   = "Access the EMS ReadyKit API on your behalf"
      user_consent_display_name  = "Access EMS ReadyKit API"
      value                      = "api.access"
    }

    oauth2_permission_scope {
      admin_consent_description  = "Allows the app to access EMS ReadyKit API on behalf of the signed-in user"
      admin_consent_display_name = "Access EMS ReadyKit API"
      enabled                    = true
      id                         = "413150f6-0b02-4000-b484-4b2345f025b0"
      type                       = "User"
      user_consent_description   = "Allow the app to access EMS ReadyKit API on your behalf"
      user_consent_display_name  = "Access EMS ReadyKit API"
      value                      = "user_impersonation"
    }
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "EMS ReadyKit global administrators"
    display_name         = "Administrator"
    enabled              = true
    id                   = "00000000-0000-0000-0001-000000000001"
    value                = "Administrator"
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "EMS ReadyKit station supervisors"
    display_name         = "Supervisor"
    enabled              = true
    id                   = "00000000-0000-0000-0001-000000000002"
    value                = "Supervisor"
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "EMS ReadyKit field responders"
    display_name         = "Responder"
    enabled              = true
    id                   = "00000000-0000-0000-0001-000000000003"
    value                = "Responder"
  }

  lifecycle {
    ignore_changes = [
      required_resource_access,
      single_page_application,
      web,
    ]
  }
}

resource "azuread_service_principal" "ems_readykit" {
  client_id = azuread_application.ems_readykit.client_id
}

# ── Azure AD Groups ───────────────────────────────────────────────────────────

resource "azuread_group" "administrators" {
  display_name     = "ems-readykit-administrators"
  mail_enabled     = false
  security_enabled = true
  description      = "EMS ReadyKit global administrators — subscription-level read access"
}

resource "azuread_group" "supervisors" {
  display_name     = "ems-readykit-supervisors"
  mail_enabled     = false
  security_enabled = true
  description      = "EMS ReadyKit station supervisors — resource group contributor access"
}

resource "azuread_group" "responders" {
  display_name     = "ems-readykit-responders"
  mail_enabled     = false
  security_enabled = true
  description      = "EMS ReadyKit responders — application-enforced access only"
}

# ── App Role Assignments ──────────────────────────────────────────────────────

resource "azuread_app_role_assignment" "administrators" {
  app_role_id         = "00000000-0000-0000-0001-000000000001"
  principal_object_id = azuread_group.administrators.object_id
  resource_object_id  = azuread_service_principal.ems_readykit.object_id
}

resource "azuread_app_role_assignment" "supervisors" {
  app_role_id         = "00000000-0000-0000-0001-000000000002"
  principal_object_id = azuread_group.supervisors.object_id
  resource_object_id  = azuread_service_principal.ems_readykit.object_id
}

resource "azuread_app_role_assignment" "responders" {
  app_role_id         = "00000000-0000-0000-0001-000000000003"
  principal_object_id = azuread_group.responders.object_id
  resource_object_id  = azuread_service_principal.ems_readykit.object_id
}

# ── Azure RBAC Role Assignments ───────────────────────────────────────────────

resource "azurerm_role_assignment" "administrators_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = azuread_group.administrators.object_id
}

resource "azurerm_role_assignment" "supervisors_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azuread_group.supervisors.object_id
}

resource "azurerm_role_assignment" "supervisors_log_reader" {
  scope                = var.resource_group_id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azuread_group.supervisors.object_id
}

# ── CI/CD Service Principal (GitHub Actions) ──────────────────────────────────
# Scoped to the resource group only — least privilege for deployments.
# After terraform apply, run the following to generate AZURE_CREDENTIALS:
#
#   az ad sp create-for-rbac \
#     --name "sp-ems-readykit-github-actions" \
#     --role "Website Contributor" \
#     --scopes /subscriptions/<sub_id>/resourceGroups/rg-ems-readykit-dev \
#     --sdk-auth
#
# Paste the JSON output as the AZURE_CREDENTIALS GitHub secret.
# The sp is created by the az command above; Terraform just documents it here.
# We do NOT store the client secret in Terraform state.

resource "azuread_application" "github_actions" {
  display_name = "sp-ems-readykit-github-actions"
}

resource "azuread_service_principal" "github_actions" {
  client_id = azuread_application.github_actions.client_id
}

# Website Contributor: can deploy to App Service, cannot modify networking or IAM
resource "azurerm_role_assignment" "github_actions_website_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Website Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}

# Storage Blob Data Contributor: needed to read/write Terraform state
# (backend uses use_azuread_auth = true which requires data plane RBAC,
# not just storage account key access)
resource "azurerm_role_assignment" "github_actions_tfstate_blob" {
  scope                = var.tfstate_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}
