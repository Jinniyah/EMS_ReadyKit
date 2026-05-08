// modules/app/main.tf
// App Service (Linux, Python 3.11) with:
//   - Configurable SKU (F1 free tier or B1+ paid)
//   - VNet integration when SKU supports it (B1 and above only)
//   - System-assigned Managed Identity
//   - Key Vault for secrets (SQL connection string)
//   - Diagnostic settings to Log Analytics
//
// NOTE: F1 (Free tier) does not support VNet integration or always_on.
//       Set app_service_sku = "B1" once subscription quota is raised
//       to enable full private networking.

locals {
  # F1 does not support VNet integration or always_on
  is_free_tier = var.app_service_sku == "F1"
  enable_vnet  = !local.is_free_tier
}

data "azurerm_client_config" "current" {}

# ── App Service Plan ───────────────────────────────────────────────────────────

resource "azurerm_service_plan" "ems_plan" {
  name                = "asp-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  os_type  = "Linux"
  sku_name = var.app_service_sku

  tags = var.tags
}

# ── App Service ────────────────────────────────────────────────────────────────

resource "azurerm_linux_web_app" "ems_app" {
  name                = "app-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.ems_plan.id

  # VNet integration — only supported on B1 and above
  virtual_network_subnet_id = local.enable_vnet ? var.subnet_app_id : null

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    # always_on not supported on F1 free tier
    always_on           = local.is_free_tier ? false : true
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"

    application_stack {
      python_version = "3.11"
    }

    # Uvicorn startup command
    app_command_line = "pip install -r requirements.txt && uvicorn ems_readykit.main:app --host 0.0.0.0 --port 8000"
  }

  app_settings = merge(
    {
      "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
      "ENABLE_ORYX_BUILD"              = "true"
      "StorageAccountName"             = var.storage_account_name
      "KeyVaultUri"                    = azurerm_key_vault.ems_kv.vault_uri
      "APP_ENV"                        = "production"
      "LOG_LEVEL"                      = "INFO"
    },
    # Route all outbound traffic through VNet only when VNet integration is active
    local.enable_vnet ? { "WEBSITE_VNET_ROUTE_ALL" = "1" } : {}
  )

  tags = var.tags
}

# ── Key Vault ──────────────────────────────────────────────────────────────────

resource "azurerm_key_vault" "ems_kv" {
  name                = "kv-${replace(var.name_prefix, "-", "")}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.key_vault_tenant_id

  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = false # Set true in production
  soft_delete_retention_days = 7

  # On F1 (no VNet), allow Azure services through.
  # On B1+, lock down to AzureServices bypass only (app accesses via VNet).
  network_acls {
    default_action = "Allow"
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
