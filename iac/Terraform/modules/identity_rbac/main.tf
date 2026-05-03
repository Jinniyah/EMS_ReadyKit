// modules/identity_rbac/main.tf
// Creates Azure AD groups for each EMS role and assigns Azure RBAC
// at the appropriate scope per ADR-002.
//
// Roles:
//   Administrator — Reader at subscription scope
//   Supervisor    — Contributor at resource group scope
//   Responder     — Application-enforced only (no Azure RBAC assignment needed)

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

# ── Azure RBAC Role Assignments ───────────────────────────────────────────────

# Administrators: Reader at subscription scope
# Allows global oversight without destructive capability
resource "azurerm_role_assignment" "administrators_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = azuread_group.administrators.object_id
}

# Supervisors: Contributor scoped to the station resource group
# Allows operational management without subscription-wide access
resource "azurerm_role_assignment" "supervisors_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azuread_group.supervisors.object_id
}

# Supervisors: Log Analytics Reader so they can query logs
resource "azurerm_role_assignment" "supervisors_log_reader" {
  scope                = var.resource_group_id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azuread_group.supervisors.object_id
}

# Responders: No Azure RBAC assignment.
# Access is entirely enforced at the application layer per ADR-002.
