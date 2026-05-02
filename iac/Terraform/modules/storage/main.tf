// storage main.tf
resource "azurerm_storage_account" "ems_storage" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

  https_traffic_only_enabled = true
}

resource "azurerm_storage_container" "app" {
  name                  = "app"
  storage_account_name  = azurerm_storage_account.ems_storage.name
  container_access_type = "private"
}


