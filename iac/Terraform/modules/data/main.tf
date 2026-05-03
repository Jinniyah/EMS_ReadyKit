// modules/data/main.tf
// Azure SQL Server + Database with private endpoint, firewall deny-all,
// auditing, and diagnostic log forwarding to Log Analytics.

resource "azurerm_mssql_server" "ems_sql" {
  name                         = "sql-${var.name_prefix}"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = var.sql_admin_password

  # No public network access — all access via private endpoint
  public_network_access_enabled = false

  minimum_tls_version = "1.2"

  tags = var.tags
}

resource "azurerm_mssql_database" "ems_db" {
  name      = "db-ems-readykit"
  server_id = azurerm_mssql_server.ems_sql.id

  # Basic SKU — right-sized for demo scope, cost-controlled
  sku_name   = "Basic"
  max_size_gb = 2

  # Short-term backup retention appropriate for non-production
  short_term_retention_policy {
    retention_days = 7
  }

  tags = var.tags
}

# ── Firewall: deny all public access ─────────────────────────────────────────
# public_network_access_enabled = false on the server handles this,
# but we add an explicit empty rule set for auditability.
resource "azurerm_mssql_firewall_rule" "deny_all" {
  name             = "deny-all-public"
  server_id        = azurerm_mssql_server.ems_sql.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ── Private Endpoint ──────────────────────────────────────────────────────────

resource "azurerm_private_endpoint" "sql_pe" {
  name                = "pe-sql-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_data_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-sql"
    private_connection_resource_id = azurerm_mssql_server.ems_sql.id
    subresource_names              = ["sqlServer"]
    is_manual_connection           = false
  }
}

# ── SQL Auditing → Log Analytics ──────────────────────────────────────────────

resource "azurerm_mssql_server_extended_auditing_policy" "ems_sql_audit" {
  server_id                               = azurerm_mssql_server.ems_sql.id
  log_monitoring_enabled                  = true
  retention_in_days                       = 30
}

# ── Diagnostic Settings ────────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "sql_db_diag" {
  name                       = "diag-sql-db"
  target_resource_id         = azurerm_mssql_database.ems_db.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "SQLSecurityAuditEvents"
  }

  enabled_log {
    category = "Errors"
  }

  metric {
    category = "Basic"
    enabled  = true
  }
}
