// modules/app/main.tf
//
// Deployment lessons learned:
//   Oryx extracts the zip to /tmp/8dea.../ and creates the virtualenv at
//   /tmp/8dea.../antenv/. The system Python at /opt/python/3.11.14/ has no
//   packages installed. The startup command MUST use the antenv binaries
//   directly (antenv/bin/gunicorn) rather than the system Python/gunicorn,
//   otherwise uvicorn and ems_readykit are not found.
//
//   Oryx sets the working directory to the extracted app path before running
//   app_command_line, so relative paths like antenv/bin/gunicorn work correctly.
//
//   DO NOT use --chdir — it overrides Oryx's working directory setup.
//   DO NOT set PYTHONPATH manually — Oryx sets it correctly.
//   DO NOT leave app_command_line empty — Oryx falls back to the system Python.

locals {
  is_free_tier             = var.app_service_sku == "F1"
  enable_vnet              = !local.is_free_tier
  is_dev                   = var.environment == "dev"
  kv_purge_protection      = local.is_dev ? false : true
  kv_soft_delete_retention = local.is_dev ? 7 : 90
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
    health_check_path                 = "/health"
    # Allow up to 10 minutes of health-check failures before recycling.
    # Gives startup.sh time to run Alembic migrations before gunicorn
    # begins accepting traffic.
    health_check_eviction_time_in_min  = 10

    application_stack {
      python_version = "3.11"
    }

    # startup.sh activates the antenv virtualenv, runs Alembic migrations,
    # then execs gunicorn. This guarantees the schema is current before the
    # app accepts traffic. Migrations are idempotent (no-op if already at head).
    app_command_line = "bash startup.sh"

    scm_ip_restriction_default_action = "Deny"

    dynamic "scm_ip_restriction" {
      for_each = var.office_ip_cidr != "" ? [var.office_ip_cidr] : []
      content {
        name       = "Allow-Office"
        ip_address = scm_ip_restriction.value
        action     = "Allow"
        priority   = 100
      }
    }
  }

  app_settings = merge(
    {
      "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
      "ENABLE_ORYX_BUILD"                   = "true"
      "STORAGE_ACCOUNT_NAME"                = var.storage_account_name
      "KEY_VAULT_URI"                       = azurerm_key_vault.ems_kv.vault_uri
      "APP_ENV"                             = "production"
      "LOG_LEVEL"                           = "INFO"
      "DATABASE_URL"                        = var.sql_connection_string
      "AZURE_AD_TENANT_ID"                  = var.tenant_id
      "AZURE_AD_CLIENT_ID"                  = var.client_id
      "AZURE_AD_AUDIENCE"                   = "api://${var.client_id}"
    },
    local.enable_vnet ? { "WEBSITE_VNET_ROUTE_ALL" = "1" } : {}
  )

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
