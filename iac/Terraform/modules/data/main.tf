// modules/data/main.tf
// Azure PostgreSQL Flexible Server + Database with public access firewall,
// private endpoint (ready for B1+ VNet upgrade), auditing, and
// diagnostic log forwarding to Log Analytics.
//
// Why PostgreSQL over Azure SQL:
//   Azure SQL has regional provisioning restrictions on new Azure Plan
//   subscriptions. PostgreSQL Flexible Server does not have the same
//   restrictions and is available broadly. It is also a better fit for
//   the FastAPI + SQLAlchemy Python stack.
//
// Connectivity note (F1 SKU):
//   The App Service F1 tier does not support VNet integration, so the app
//   reaches PostgreSQL over the public internet. public_network_access_enabled
//   is set to true and an Azure-services firewall rule permits inbound
//   connections from Azure's shared IP ranges.
//
// Upgrade path to full private networking (B1+):
//   1. Set app_service_sku = "B1" (or higher) in variables.tf
//   2. Add azurerm_private_dns_zone + virtual_network_link here
//   3. Set delegated_subnet_id and private_dns_zone_id on the server
//   4. Remove the azurerm_postgresql_flexible_server_firewall_rule below

resource "azurerm_postgresql_flexible_server" "ems_pg" {
  name                = "pg-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  version                = "16"
  administrator_login    = var.pg_admin_login
  administrator_password = var.pg_admin_password

  # Burstable B1ms — cost-effective for demo/dev workloads
  # ~$12-15/month. Upgrade to GeneralPurpose for production.
  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768   # 32 GB minimum

  # Public access required for F1 App Service (no VNet integration).
  # Set to false and configure delegated_subnet_id when upgrading to B1+.
  public_network_access_enabled = true

  # Backup retention appropriate for non-production
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  tags = var.tags
}

# Allow Azure-hosted services (including App Service on F1) through the
# PostgreSQL firewall. The 0.0.0.0/0.0.0.0 sentinel maps to
# "Allow Azure Services" — it does NOT open PostgreSQL to the general internet.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.ems_pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "ems_db" {
  name      = "ems_readykit"
  server_id = azurerm_postgresql_flexible_server.ems_pg.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# ── Private Endpoint ──────────────────────────────────────────────────────────
# Retained for B1+ upgrade readiness. On F1 connectivity flows via the
# public firewall rule above. To activate: add a Private DNS Zone for
# privatelink.postgres.database.azure.com and link it to the VNet,
# then set delegated_subnet_id on the server resource instead.

resource "azurerm_private_endpoint" "pg_pe" {
  name                = "pe-pg-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_data_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-pg"
    private_connection_resource_id = azurerm_postgresql_flexible_server.ems_pg.id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }
}

# ── Diagnostic Settings → Log Analytics ───────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "pg_diag" {
  name                       = "diag-pg"
  target_resource_id         = azurerm_postgresql_flexible_server.ems_pg.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "PostgreSQLLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
