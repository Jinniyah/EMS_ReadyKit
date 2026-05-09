// modules/app/main.tf
// App Service (Linux, Python 3.11) with:
//   - Configurable SKU (F1 free tier or B1+ paid)
//   - VNet integration when SKU supports it (B1 and above only)
//   - System-assigned Managed Identity
//   - Key Vault for secrets (PostgreSQL connection string)
//   - SCM/Kudu IP restriction (office IP only)
//   - Health check endpoint wired to /health
//   - Backup configuration to storage account
//   - Diagnostic settings to Log Analytics
//
// NOTE: F1 (Free tier) does not support VNet integration, always_on, or
//       backup.  Set app_service_sku = "B1" to enable full private
//       networking and backup.
//
// Key Vault RBAC model:
//   This vault uses enable_rbac_authorization = true (no access policies).
//   Two role assignments are required:
//     1. Terraform identity → Key Vault Secrets Officer (to write secrets)
//     2. App managed identity → Key Vault Secrets User (to read secrets at runtime)
//   The network_acls ip_rules must include the Terraform runner IP so the
//   firewall does not block secret writes during terraform apply.
//
// Key Vault purge protection note:
//   purge_protection_enabled and soft_delete_retention_days are gated on
//   var.environment. In dev, purge protection is disabled and retention is
//   7 days so deleted vaults can be purged immediately during iteration.
//   In staging/prod, purge protection is enabled with 90-day retention.

locals {
  # F1 does not support VNet integration, always_on, or backup
  is_free_tier = var.app_service_sku == "F1"
  enable_vnet  = !local.is_free_tier

  # Key Vault protection settings — relaxed in dev for easier iteration
  is_dev                   = var.environment == "dev"
  kv_purge_protection      = local.is_dev ? false : true
  kv_soft_delete_retention = local.is_dev ? 7 : 90
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

# ── Key Vault ──────────────────────────────────────────────────────────────────
# Key Vault names must be globally unique (3-24 chars, alphanumeric + hyphens).
# A random suffix is appended to avoid collisions across deployments.

resource "random_string" "kv_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_key_vault" "ems_kv" {
  name                = "kv-${random_string.kv_suffix.result}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.key_vault_tenant_id

  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = local.kv_purge_protection
  soft_delete_retention_days = local.kv_soft_delete_retention

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    # Allow the Terraform runner IP so secret writes succeed during apply.
    # In CI/CD this would be the pipeline agent IP range.
    ip_rules = var.allowed_admin_ips
  }

  tags = var.tags
}

# ── Key Vault RBAC: Terraform identity → Secrets Officer ──────────────────────
# Required so Terraform can write azurerm_key_vault_secret resources.
# Without this, the RBAC-enabled vault returns 403 ForbiddenByRbac even
# for subscription owners. RBAC propagation takes 30-90 seconds — the
# secret resource depends_on this assignment to ensure correct ordering.

resource "azurerm_role_assignment" "terraform_kv_secrets_officer" {
  scope                = azurerm_key_vault.ems_kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
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
    always_on           = local.is_free_tier ? false : true
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"

    health_check_path = "/health"

    application_stack {
      python_version = "3.11"
    }

    app_command_line = "gunicorn -w 2 -k uvicorn.workers.UvicornWorker ems_readykit.main:app"

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
      "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
      "ENABLE_ORYX_BUILD"              = "true"
      "StorageAccountName"             = var.storage_account_name
      "KeyVaultUri"                    = azurerm_key_vault.ems_kv.vault_uri
      "APP_ENV"                        = "production"
      "LOG_LEVEL"                      = "INFO"
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

# ── Key Vault RBAC: App Managed Identity → Secrets User ───────────────────────

resource "azurerm_role_assignment" "app_kv_secrets_user" {
  scope                = azurerm_key_vault.ems_kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.ems_app.identity[0].principal_id
}

# ── Store PostgreSQL connection string as a Key Vault secret ───────────────────
# depends_on the Terraform role assignment to ensure RBAC has propagated
# and depends_on the firewall ip_rules being in place before the write.

resource "azurerm_key_vault_secret" "sql_connection" {
  name         = "sql-connection-string"
  value        = var.sql_connection_string
  key_vault_id = azurerm_key_vault.ems_kv.id

  depends_on = [azurerm_role_assignment.terraform_kv_secrets_officer]
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
