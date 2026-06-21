// modules/app/main.tf

locals {
  is_free_tier             = var.app_service_sku == "F1"
  enable_vnet              = !local.is_free_tier
  is_dev                   = var.environment == "dev"
  kv_purge_protection      = local.is_dev ? false : true
  kv_soft_delete_retention = local.is_dev ? 7 : 90

  cors_origins = compact([
    "http://localhost:5173",
    "http://localhost:3000",
    var.frontend_url,
  ])
}

data "azurerm_client_config" "current" {}

resource "azurerm_service_plan" "ems_plan" {
  name                = "asp-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = var.tags
}

resource "random_string" "kv_suffix" {
  length  = 6
  special = false
  upper   = false
}

# SEC-4: main.py asserts secret_key != "change-me-in-production" whenever
# APP_ENV=production, and crashes app startup if the assertion fails. Generate
# a real value here so a future production cutover doesn't boot-loop on this.
# Not currently read for any cryptographic purpose in the app — it exists to
# satisfy the SEC-4 startup guard — but treat it as a real secret regardless.
resource "random_password" "app_secret_key" {
  length  = 48
  special = true
}

resource "azurerm_key_vault" "ems_kv" {
  name                       = "kv-${random_string.kv_suffix.result}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.key_vault_tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = local.kv_purge_protection
  soft_delete_retention_days = local.kv_soft_delete_retention

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.allowed_admin_ips
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "terraform_kv_secrets_officer" {
  scope                = azurerm_key_vault.ems_kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
  depends_on           = [azurerm_key_vault.ems_kv]
}

resource "azurerm_linux_web_app" "ems_app" {
  name                      = "app-${var.name_prefix}"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.ems_plan.id
  virtual_network_subnet_id = local.enable_vnet ? var.subnet_app_id : null
  https_only                = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on           = local.is_free_tier ? false : true
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"
    health_check_path                  = "/health"
    health_check_eviction_time_in_min  = 10

    application_stack {
      python_version = "3.11"
    }

    app_command_line = "bash startup.sh"

    scm_ip_restriction_default_action = "Allow"

    cors {
      allowed_origins     = local.cors_origins
      support_credentials = true
    }
  }

  # WEBSITE_VNET_ROUTE_ALL is managed automatically by the azurerm provider
  # when virtual_network_subnet_id is set — do not set it in app_settings.
  app_settings = {
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "ENABLE_ORYX_BUILD"              = "true"
    "STORAGE_ACCOUNT_NAME"           = var.storage_account_name
    "KEY_VAULT_URI"                  = azurerm_key_vault.ems_kv.vault_uri
    "APP_ENV"                        = local.is_dev ? "development" : "production"
    "LOG_LEVEL"                      = "INFO"
    "SECRET_KEY"                     = random_password.app_secret_key.result
    "DATABASE_URL"                   = var.sql_connection_string
    "AZURE_AD_TENANT_ID"             = var.tenant_id
    "AZURE_AD_CLIENT_ID"             = var.client_id
    "AZURE_AD_AUDIENCE"              = "api://${var.client_id}"
    "ALLOWED_ORIGINS"                = join(",", local.cors_origins)
  }

  dynamic "backup" {
    for_each = local.is_free_tier ? [] : [1]
    content {
      name                = "default-backup"
      enabled             = true
      storage_account_url = var.storage_account_sas_url
      schedule {
        frequency_interval       = 1
        frequency_unit           = "Day"
        retention_period_days    = 7
        keep_at_least_one_backup = true
      }
    }
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "app_kv_secrets_user" {
  scope                = azurerm_key_vault.ems_kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.ems_app.identity[0].principal_id
}

resource "azurerm_key_vault_secret" "sql_connection" {
  name         = "sql-connection-string"
  value        = var.sql_connection_string
  key_vault_id = azurerm_key_vault.ems_kv.id
  depends_on   = [azurerm_role_assignment.terraform_kv_secrets_officer]
}

resource "azurerm_key_vault_secret" "app_secret_key" {
  name         = "app-secret-key"
  value        = random_password.app_secret_key.result
  key_vault_id = azurerm_key_vault.ems_kv.id
  depends_on   = [azurerm_role_assignment.terraform_kv_secrets_officer]
}

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
