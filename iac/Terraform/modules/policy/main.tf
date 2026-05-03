// modules/policy/main.tf
// Azure Policy guardrails:
//   1. Allowed locations — restrict deployments to one region
//   2. Required tags     — enforce Owner, CostCenter, Project, Environment, ManagedBy
//   3. Deny public IPs   — prevent accidental exposure

locals {
  subscription_scope = "/subscriptions/${var.subscription_id}"
}

# ── 1. Allowed Locations ──────────────────────────────────────────────────────
# Uses the built-in "Allowed locations" policy definition.

data "azurerm_policy_definition" "allowed_locations" {
  display_name = "Allowed locations"
}

resource "azurerm_subscription_policy_assignment" "allowed_locations" {
  name                 = "ems-allowed-locations"
  subscription_id      = local.subscription_scope
  policy_definition_id = data.azurerm_policy_definition.allowed_locations.id
  display_name         = "EMS ReadyKit — Allowed Locations"
  description          = "Restricts all resource deployments to the approved Azure region."

  parameters = jsonencode({
    listOfAllowedLocations = {
      value = [var.allowed_location]
    }
  })
}

# ── 2. Required Tags ──────────────────────────────────────────────────────────
# One policy assignment per required tag key using the built-in
# "Require a tag on resources" definition.

data "azurerm_policy_definition" "require_tag" {
  display_name = "Require a tag on resources"
}

resource "azurerm_subscription_policy_assignment" "require_tag" {
  for_each = toset(var.required_tags)

  name                 = "ems-require-tag-${lower(each.key)}"
  subscription_id      = local.subscription_scope
  policy_definition_id = data.azurerm_policy_definition.require_tag.id
  display_name         = "EMS ReadyKit — Require tag: ${each.key}"
  description          = "Ensures all resources carry the '${each.key}' tag."

  parameters = jsonencode({
    tagName = {
      value = each.key
    }
  })
}

# ── 3. Deny Public IP Creation ────────────────────────────────────────────────
# Custom policy that denies creation of Public IP resources.

resource "azurerm_policy_definition" "deny_public_ip" {
  name         = "ems-deny-public-ip"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "EMS ReadyKit — Deny Public IP Creation"
  description  = "Prevents creation of public IP addresses to enforce network isolation."

  metadata = jsonencode({
    category = "EMS ReadyKit Security"
  })

  policy_rule = jsonencode({
    if = {
      allOf = [
        {
          field  = "type"
          equals = "Microsoft.Network/publicIPAddresses"
        }
      ]
    }
    then = {
      effect = "Deny"
    }
  })
}

resource "azurerm_subscription_policy_assignment" "deny_public_ip" {
  name                 = "ems-deny-public-ip"
  subscription_id      = local.subscription_scope
  policy_definition_id = azurerm_policy_definition.deny_public_ip.id
  display_name         = "EMS ReadyKit — Deny Public IP Creation"
  description          = "Enforces network isolation by denying public IP resources."
}
