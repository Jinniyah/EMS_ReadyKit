// network outputs.tf
output "vnet_id" {
  value = azurerm_virtual_network.ems_vnet.id
}

output "subnet_app_id" {
  value = azurerm_subnet.app.id
}

output "subnet_data_id" {
  value = azurerm_subnet.data.id
}

output "subnet_management_id" {
  value = azurerm_subnet.management.id
}