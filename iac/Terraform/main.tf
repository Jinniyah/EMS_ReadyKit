// Root module — wires all child modules together

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "ems_rg" {
  name     = "rg-${local.name_prefix}"
  location = local.location
  tags     = local.common_tags
}

# ── Logging (deployed first — needed for diagnostics) ───────────────────────
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

  resource_group_name      = azurerm_resource_group.ems_rg.name
  location                 = azurerm_resource_group.ems_rg.location
  log_analytics_workspace_id = module.logging.workspace_id
  tags                     = local.common_tags
}

# ── Identity & RBAC ───────────────────────────────────────────────────────────
module "identity_rbac" {
  source = "./modules/identity_rbac"

  resource_group_id   = azurerm_resource_group.ems_rg.id
  subscription_id     = local.subscription_id
  tags                = local.common_tags
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

# ── Data (Azure SQL) ──────────────────────────────────────────────────────────
module "data" {
  source = "./modules/data"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  name_prefix                = local.name_prefix
  subnet_data_id             = module.network.subnet_data_id
  sql_admin_login            = var.sql_admin_login
  sql_admin_password         = var.sql_admin_password
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.common_tags
}

# ── Application (App Service + Key Vault) ─────────────────────────────────────
module "app" {
  source = "./modules/app"

  resource_group_name        = azurerm_resource_group.ems_rg.name
  location                   = azurerm_resource_group.ems_rg.location
  name_prefix                = local.name_prefix
  subnet_app_id              = module.network.subnet_app_id
  key_vault_tenant_id        = data.azurerm_client_config.current.tenant_id
  sql_connection_string      = module.data.sql_connection_string
  storage_account_name       = module.storage.storage_account_name
  log_analytics_workspace_id = module.logging.workspace_id
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
