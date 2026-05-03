// logging outputs.tf

output "workspace_id" {
  description = "Resource ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.ems_law.id
}

output "workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.ems_law.name
}

output "primary_shared_key" {
  description = "Primary shared key for the Log Analytics workspace (sensitive)"
  value       = azurerm_log_analytics_workspace.ems_law.primary_shared_key
  sensitive   = true
}

output "workspace_customer_id" {
  description = "Workspace customer ID (used by agents)"
  value       = azurerm_log_analytics_workspace.ems_law.workspace_id
}
