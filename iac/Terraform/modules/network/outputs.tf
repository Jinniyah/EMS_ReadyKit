// network outputs.tf

output "vnet_id" {
  description = "Resource ID of the virtual network"
  value       = azurerm_virtual_network.ems_vnet.id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.ems_vnet.name
}

output "subnet_app_id" {
  description = "Resource ID of the app subnet"
  value       = azurerm_subnet.app.id
}

output "subnet_data_id" {
  description = "Resource ID of the data subnet"
  value       = azurerm_subnet.data.id
}

output "subnet_management_id" {
  description = "Resource ID of the management/monitoring subnet"
  value       = azurerm_subnet.management.id
}

output "nsg_app_id" {
  description = "Resource ID of the app NSG"
  value       = azurerm_network_security_group.app_nsg.id
}

output "nsg_data_id" {
  description = "Resource ID of the data NSG"
  value       = azurerm_network_security_group.data_nsg.id
}
