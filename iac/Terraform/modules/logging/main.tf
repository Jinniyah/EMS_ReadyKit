// modules/logging/main.tf
// Deploys a Log Analytics Workspace as the central log store.
// All platform diagnostics, application logs, and audit events
// are routed here per ADR-003.
//
// Provider note:
//   data "azurerm_client_config" is used below to resolve the subscription ID
//   for the activity log alert scope. This data source uses the azurerm provider
//   inherited from the root module — no explicit provider block is needed here,
//   but this module implicitly requires the root azurerm provider to be configured.

resource "azurerm_log_analytics_workspace" "ems_law" {
  name                = "law-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name

  sku               = "PerGB2018"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# ── Saved queries for operational and audit use ───────────────────────────────

# Query: All audit events in the last 24 hours
resource "azurerm_log_analytics_saved_search" "recent_audit_events" {
  name                       = "EMS-RecentAuditEvents"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.ems_law.id

  category     = "EMS Audit"
  display_name = "Recent Audit Events (24h)"

  query = <<-EOQ
    AppEvents
    | where TimeGenerated > ago(24h)
    | where Properties has "audit"
    | project TimeGenerated, Name, Properties
    | order by TimeGenerated desc
  EOQ
}

# Query: High-severity events (controlled substance discrepancies, auth failures)
resource "azurerm_log_analytics_saved_search" "high_severity_events" {
  name                       = "EMS-HighSeverityEvents"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.ems_law.id

  category     = "EMS Audit"
  display_name = "High Severity Events"

  query = <<-EOQ
    AppEvents
    | where TimeGenerated > ago(7d)
    | where Properties has_any ("controlled_substance_discrepancy", "unauthorized_access", "auth_failure")
    | project TimeGenerated, Name, Properties
    | order by TimeGenerated desc
  EOQ
}

# ── Azure Activity Log alert: destructive operations ──────────────────────────

resource "azurerm_monitor_action_group" "ems_ops" {
  name                = "ag-${var.name_prefix}-ops"
  resource_group_name = var.resource_group_name
  short_name          = "ems-ops"
  tags                = var.tags
}

# Resolves the current subscription ID at plan time via the inherited
# azurerm provider. See provider note in the file header.
data "azurerm_client_config" "current" {}

resource "azurerm_monitor_activity_log_alert" "destructive_operations" {
  name                = "alert-${var.name_prefix}-destructive-ops"
  resource_group_name = var.resource_group_name
  scopes              = ["/subscriptions/${data.azurerm_client_config.current.subscription_id}"]
  description         = "Alert on destructive resource operations (delete)"
  tags                = var.tags

  criteria {
    category       = "Administrative"
    operation_name = "Microsoft.Resources/deployments/delete"
  }

  action {
    action_group_id = azurerm_monitor_action_group.ems_ops.id
  }
}
