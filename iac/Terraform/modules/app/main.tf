// modules/app/main.tf
// App Service (Linux, Free tier for demo) with:
//   - System-assigned Managed Identity
//   - VNet integration to the app subnet
//   - Key Vault for secrets (connection string)
//   - Diagnostic settings to Log Analytics

data "azurerm_client_config" "current" {}

# ── App Service Plan ───────────────────────────────────────────────────────────

resource "azurerm_service_plan" "ems_plan" {
  name                = "asp-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  # B1 — smallest billable SKU that supports VNet integration and managed identity
  os_type  = "Linux"
  sku_name = "B1"

  tags = var.tags
}

# ── App Service ────────────────────────────────────────────────────────────────

resource "azurerm_linux_web_app" "ems_app" {
  name                = "app-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.ems_plan.id

  # VNet integration — traffic flows through the app subnet
  virtual_network_subnet_id = var.subnet_app_id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on        = false
    ftps_state       = "Disabled"
    http2_enabled    = true
    minimum_tls_version = "1.2"

    application_stack {
      # Placeholder runtime — update to match the actual application stack
      dotnet_version = "8.0"
    }
  }

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = ""  # Wire in if App Insights added later
    "StorageAccountName"                    = var.storage_account_name
    "KeyVaultUri"                           = azurerm_key_vault.ems_kv.vault_uri
    "WEBSITE_VNET_ROUTE_ALL"                = "1"
  }

  tags = var.tags
}

# ── Key Vault ──────────────────────────────────────────────────────────────────

resource "azurerm_key_vault" "ems_kv" {
  name                = "kv-${replace(var.name_prefix, "-", "")}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.key_vault_tenant_id

  sku_name                    = "standard"
  enable_rbac_authorization   = true
  purge_protection_enabled    = false  # Disabled for demo; enable in production
  soft_delete_retention_days  = 7

  # Network ACL: deny public access, allow Azure services
  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# ── Key Vault RBAC: App Managed Identity → Secrets User ───────────────────────

resource "azurerm_role_assignment" "app_kv_secrets_user" {
  scope                = azurerm_key_vault.ems_kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.ems_app.identity[0].principal_id
}

# ── Store SQL Connection String as a Secret ────────────────────────────────────

resource "azurerm_key_vault_secret" "sql_connection" {
  name         = "sql-connection-string"
  value        = var.sql_connection_string
  key_vault_id = azurerm_key_vault.ems_kv.id

  depends_on = [azurerm_role_assignment.app_kv_secrets_user]
}

# ── Diagnostic Settings → Log Analytics ───────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "app_diag" {
  name                       = "diag-app"
  target_resource_id         = azurerm_linux_web_app.ems_app.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AppServiceHTTPLogs"
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
  }

  enabled_log {
    category = "AppServiceAppLogs"
  }

  enabled_log {
    category = "AppServiceAuditLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "kv_diag" {
  name                       = "diag-kv"
  target_resource_id         = azurerm_key_vault.ems_kv.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
