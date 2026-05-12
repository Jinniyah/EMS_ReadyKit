// identity_rbac outputs.tf

output "administrators_group_id" {
  description = "Object ID of the EMS Administrators Azure AD group"
  value       = azuread_group.administrators.object_id
}

output "supervisors_group_id" {
  description = "Object ID of the EMS Supervisors Azure AD group"
  value       = azuread_group.supervisors.object_id
}

output "responders_group_id" {
  description = "Object ID of the EMS Responders Azure AD group"
  value       = azuread_group.responders.object_id
}

output "client_id" {
  description = "Application (client) ID of the EMS ReadyKit App Registration"
  value       = azuread_application.ems_readykit.client_id
}

output "tenant_id" {
  description = "Azure AD tenant ID — passed to the app as AZURE_AD_TENANT_ID"
  value       = var.tenant_id
}
