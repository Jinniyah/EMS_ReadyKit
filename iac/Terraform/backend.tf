// backend.tf
// NOTE: Storage account names must be globally unique (3-24 chars, lowercase)
// If recreating: az storage account create --name sttfstate$RANDOM --resource-group tfstate-rg

terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "emsreadykittfstate"
    container_name       = "tfstate"
    key                  = "emsreadykit.tfstate"
    subscription_id      = "75fce2ea-1d83-4c5a-9929-b424b2913c8e"
    use_azuread_auth     = true
  }
}