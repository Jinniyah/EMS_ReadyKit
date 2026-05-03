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
