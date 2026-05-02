// storage outputs.tf
output "storage_account_id" {
  description = "The ID of the storage account"
  value       = azurerm_storage_account.ems_storage.id
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.ems_storage.name
}
