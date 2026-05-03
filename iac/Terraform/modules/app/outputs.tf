// app outputs.tf

output "app_service_id" {
  description = "Resource ID of the App Service"
  value       = azurerm_linux_web_app.ems_app.id
}

output "app_service_url" {
  description = "Default HTTPS hostname of the App Service"
  value       = "https://${azurerm_linux_web_app.ems_app.default_hostname}"
}

output "app_managed_identity_principal_id" {
  description = "Principal ID of the App Service managed identity"
  value       = azurerm_linux_web_app.ems_app.identity[0].principal_id
}

output "key_vault_id" {
  description = "Resource ID of the Key Vault"
  value       = azurerm_key_vault.ems_kv.id
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.ems_kv.vault_uri
}
