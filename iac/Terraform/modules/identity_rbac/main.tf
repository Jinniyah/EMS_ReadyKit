// modules/identity_rbac/main.tf
// Creates the Azure AD App Registration, app roles, AD groups, and Azure RBAC
// assignments for EMS ReadyKit per ADR-002.
//
// Roles:
//   Administrator — Full access; Reader at subscription scope in Azure RBAC
//   Supervisor    — Station-level management; Contributor at resource group scope
//   Responder     — Submit checks and read own vehicle; application-enforced only

# ── App Registration ──────────────────────────────────────────────────────────

resource "azuread_application" "ems_readykit" {
  display_name = "EMS ReadyKit API"

  # Expose an OAuth2 scope so client apps can request delegated access.
  # Tokens issued for "api://<client_id>/api.access" are accepted by the API.
  api {
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
  }

  # App roles — these appear in the "roles" claim of access tokens issued
  # to members of the corresponding AD groups (via app role assignments below).
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
}

# The service principal is required for app role assignments to work.
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

# ── App Role Assignments (groups → app roles) ─────────────────────────────────
# These cause Azure AD to include the role value in the "roles" claim
# of access tokens issued to members of each group.

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

# Responders: No Azure RBAC assignment.
# Access is entirely enforced at the application layer per ADR-002.
