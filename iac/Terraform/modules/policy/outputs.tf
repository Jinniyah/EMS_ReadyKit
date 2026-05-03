// policy outputs.tf

output "allowed_locations_assignment_id" {
  description = "Resource ID of the Allowed Locations policy assignment"
  value       = azurerm_subscription_policy_assignment.allowed_locations.id
}

output "deny_public_ip_assignment_id" {
  description = "Resource ID of the Deny Public IP policy assignment"
  value       = azurerm_subscription_policy_assignment.deny_public_ip.id
}
