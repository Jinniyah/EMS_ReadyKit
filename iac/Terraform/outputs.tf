// Root-level outputs

output "resource_group_name" {
  description = "Name of the primary resource group"
  value       = azurerm_resource_group.ems_rg.name
}

output "log_analytics_workspace_id" {
  description = "Resource ID of the Log Analytics workspace"
  value       = module.logging.workspace_id
}

output "app_service_url" {
  description = "Default hostname of the deployed App Service"
  value       = module.app.app_service_url
}

output "key_vault_uri" {
  description = "URI of the application Key Vault"
  value       = module.app.key_vault_uri
}

output "pg_server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL Flexible Server"
  value       = module.data.pg_server_fqdn
}

output "pg_database_name" {
  description = "Name of the PostgreSQL database"
  value       = module.data.pg_database_name
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = module.storage.storage_account_name
}

output "vnet_id" {
  description = "Resource ID of the virtual network"
  value       = module.network.vnet_id
}
