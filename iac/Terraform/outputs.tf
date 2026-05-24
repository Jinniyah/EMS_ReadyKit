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
  description = "Default hostname of the App Service (backend API)"
  value       = module.app.app_service_url
}

output "frontend_url" {
  description = "Full HTTPS URL of the Static Web App (React frontend)"
  value       = module.static_web_app.url
}

output "frontend_hostname" {
  description = "Hostname of the Static Web App — use when configuring Azure AD redirect URIs (F-5H4)"
  value       = module.static_web_app.hostname
}

output "frontend_deployment_token" {
  description = "SWA deployment token — store as AZURE_STATIC_WEB_APPS_API_TOKEN GitHub secret"
  value       = module.static_web_app.api_key
  sensitive   = true
}

output "swa_resource_id" {
  description = "Resource ID of the Static Web App — copy into temp.tfvars as static_web_app_resource_id, then set create_swa_exemption=true and re-run terraform apply"
  value       = module.static_web_app.static_web_app_id
}

output "key_vault_uri" {
  description = "URI of the application Key Vault"
  value       = module.app.key_vault_uri
}

output "pg_server_fqdn" {
  description = "FQDN of the PostgreSQL Flexible Server"
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

output "github_actions_client_id" {
  description = "Client ID of the GitHub Actions service principal"
  value       = module.identity_rbac.github_actions_client_id
}
