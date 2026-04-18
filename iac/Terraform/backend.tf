// Remote state backend configuration (no secrets)
terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "emsreadykittfstate"
    container_name       = "tfstate"
    key                  = "emsreadykit.tfstate"
    subscription_id      = "75fce2ea-1d83-4c5a-9929-b424b2913c8e"
  }
}