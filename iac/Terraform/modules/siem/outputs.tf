// siem outputs.tf

output "siem_vm_id" {
  description = "Resource ID of the Security Onion VM"
  value       = azurerm_linux_virtual_machine.security_onion.id
}

output "siem_private_ip" {
  description = "Private IP address of the Security Onion VM"
  value       = azurerm_network_interface.siem_nic.private_ip_address
}

output "siem_vm_name" {
  description = "Name of the Security Onion VM"
  value       = azurerm_linux_virtual_machine.security_onion.name
}
