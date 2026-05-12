// Root module — wires all child modules together

data "azurerm_client_config" "current" {}

locals {
  is_dev = var.environment == "dev"
}

resource "azurerm_resource_group" "ems_rg" {
  name     = "rg-${local.name_prefix}"
  location = local.location
  tags     = local.common_tags
}

# ── Resource Group delete lock ─────────────────────────────────────────────────
resource "azurerm_management_lock" "rg_lock" {
  name       = "delete-lock"
  scope      = azurerm_resource_group.ems_rg.id
  lock_level = "CanNotDelete"
  notes      = "Protect EMS ReadyKit resource group from accidental deletion."
}

# ── Budget alert ───────────────────────────────────────────────────────────────
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-${local.name_prefix}"
  resource_group_id = azurerm_resource_group.ems_rg.id

  amount     = var.monthly_budget_usd
  time_grain = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = var.budget_alert_emails
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = var.budget_alert_emails
  }
}

# ── Logging (deployed first — needed for diagnostics) ─────────────────────────
module "logging" {
  source = "./modules/logging"

  resource_group_name = azurerm_resource_group.ems_rg.name
  location            = azurerm_resource_group.ems_rg.location
  name_prefix         = local.name_prefix
  tags                = local.common_tags
}

# ── Networking ────────────────────────────────────────────────────────────────
module "network" {
  source = "./modules/network"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.common_tags
}

# ── Identity & RBAC ───────────────────────────────────────────────────────────
module "identity_rbac" {
  source = "./modules/identity_rbac"

  resource_group_id = azurerm_resource_group.ems_rg.id
  subscription_id   = local.subscription_id
  tenant_id         = data.azurerm_client_config.current.tenant_id
  tags              = local.common_tags
}

# ── Policy ────────────────────────────────────────────────────────────────────
module "policy" {
  source = "./modules/policy"

  subscription_id     = local.subscription_id
  resource_group_name = azurerm_resource_group.ems_rg.name
  allowed_location    = local.location
}

# ── Storage ───────────────────────────────────────────────────────────────────
module "storage" {
  source = "./modules/storage"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  storage_account_name       = var.storage_account_name
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.common_tags
}

# ── Platform secrets ──────────────────────────────────────────────────────────

resource "random_password" "pg_admin" {
  length           = 24
  special          = true
  override_special = "_%@"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

resource "random_string" "kv_suffix" {
  length  = 6
  special = false
  upper   = false
}

# Platform Key Vault for infrastructure secrets.
# Purge protection relaxed in dev for easier iteration.
resource "azurerm_key_vault" "platform" {
  name                = "kv${random_string.kv_suffix.result}"
  location            = azurerm_resource_group.ems_rg.location
  resource_group_name = azurerm_resource_group.ems_rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id

  sku_name                   = "standard"
  purge_protection_enabled   = local.is_dev ? false : true
  soft_delete_retention_days = local.is_dev ? 7 : 90

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
  }

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.allowed_admin_ips
  }

  tags = local.common_tags
}

resource "azurerm_key_vault_secret" "pg_admin_password" {
  name         = "pg-admin-password"
  value        = random_password.pg_admin.result
  key_vault_id = azurerm_key_vault.platform.id

  depends_on = [azurerm_key_vault.platform]
}

# ── Data (PostgreSQL) ─────────────────────────────────────────────────────────
module "data" {
  source = "./modules/data"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  name_prefix                = local.name_prefix
  subnet_data_id             = module.network.subnet_data_id
  pg_admin_login             = var.pg_admin_login
  pg_admin_password          = azurerm_key_vault_secret.pg_admin_password.value
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.common_tags

  depends_on = [azurerm_key_vault_secret.pg_admin_password]
}

# ── Application (App Service + Key Vault) ─────────────────────────────────────
module "app" {
  source = "./modules/app"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  name_prefix                = local.name_prefix
  environment                = var.environment
  app_service_sku            = var.app_service_sku
  subnet_app_id              = module.network.subnet_app_id
  key_vault_tenant_id        = data.azurerm_client_config.current.tenant_id
  sql_connection_string      = module.data.sql_connection_string
  storage_account_name       = module.storage.storage_account_name
  storage_account_sas_url    = module.storage.backup_sas_url
  log_analytics_workspace_id = module.logging.workspace_id
  office_ip_cidr             = var.office_ip_cidr
  allowed_admin_ips          = var.allowed_admin_ips
  tenant_id                  = module.identity_rbac.tenant_id
  client_id                  = module.identity_rbac.client_id
  tags                       = local.common_tags
}

# ── SIEM — Security Onion (optional) ─────────────────────────────────────────
module "siem" {
  source = "./modules/siem"
  count  = var.enable_siem ? 1 : 0

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  name_prefix                = local.name_prefix
  subnet_monitoring_id       = module.network.subnet_management_id
  admin_username             = var.siem_admin_username
  admin_password             = var.siem_admin_password
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.common_tags
}
