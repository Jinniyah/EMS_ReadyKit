// Root module wiring child modules
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "ems_rg" {
  name     = "rg-ems-readykit"
  location = "eastus"
}

module "network" {
  source = "./modules/network"

  resource_group_name = azurerm_resource_group.ems_rg.name
  location            = azurerm_resource_group.ems_rg.location
}

module "storage" {
  source = "./modules/storage"

  resource_group_name  = azurerm_resource_group.ems_rg.name
  location             = azurerm_resource_group.ems_rg.location
  storage_account_name = "emsreadykitstorage123"
}
