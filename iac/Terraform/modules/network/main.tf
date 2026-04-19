// modules/network/main.tf

resource "azurerm_virtual_network" "ems_vnet" {
  name                = "vnet-ems-readykit"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = ["10.10.0.0/16"]
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.2.0/24"]
}

resource "azurerm_subnet" "management" {
  name                 = "snet-management"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.3.0/24"]
}

resource "azurerm_network_security_group" "app_nsg" {
  name                = "nsg-app"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_network_security_group" "data_nsg" {
  name                = "nsg-data"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_network_security_group" "management_nsg" {
  name                = "nsg-management"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_subnet_network_security_group_association" "app_assoc" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app_nsg.id
}

resource "azurerm_subnet_network_security_group_association" "data_assoc" {
  subnet_id                 = azurerm_subnet.data.id
  network_security_group_id = azurerm_network_security_group.data_nsg.id
}

resource "azurerm_subnet_network_security_group_association" "management_assoc" {
  subnet_id                 = azurerm_subnet.management.id
  network_security_group_id = azurerm_network_security_group.management_nsg.id
}

resource "azurerm_route_table" "ems_rt" {
  name                = "rt-ems-readykit"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_subnet_route_table_association" "app_rt_assoc" {
  subnet_id      = azurerm_subnet.app.id
  route_table_id = azurerm_route_table.ems_rt.id
}

resource "azurerm_subnet_route_table_association" "data_rt_assoc" {
  subnet_id      = azurerm_subnet.data.id
  route_table_id = azurerm_route_table.ems_rt.id
}

resource "azurerm_subnet_route_table_association" "management_rt_assoc" {
  subnet_id      = azurerm_subnet.management.id
  route_table_id = azurerm_route_table.ems_rt.id
}