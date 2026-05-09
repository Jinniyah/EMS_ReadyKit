// storage outputs.tf

output "storage_account_id" {
  description = "Resource ID of the storage account"
  value       = azurerm_storage_account.ems_storage.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.ems_storage.name
}

output "primary_blob_endpoint" {
  description = "Primary blob service endpoint URL"
  value       = azurerm_storage_account.ems_storage.primary_blob_endpoint
}

output "backup_sas_url" {
  description = "SAS URL for the app-backups container, used by the App Service backup configuration"
  value       = "${azurerm_storage_account.ems_storage.primary_blob_endpoint}${azurerm_storage_container.backup.name}${data.azurerm_storage_account_sas.backup.sas}"
  sensitive   = true
}
