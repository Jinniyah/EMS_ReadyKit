// app variables.tf

variable "resource_group_name" {
  type        = string
  description = "Resource group for app resources"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource naming"
}

variable "subnet_app_id" {
  type        = string
  description = "Resource ID of the app subnet for VNet integration"
}

variable "key_vault_tenant_id" {
  type        = string
  description = "Azure AD tenant ID for Key Vault access policies"
}

variable "sql_connection_string" {
  type        = string
  description = "SQL connection string stored as a Key Vault secret"
  sensitive   = true
}

variable "storage_account_name" {
  type        = string
  description = "Storage account name passed to the app as a setting"
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID for diagnostic settings"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
