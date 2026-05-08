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

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU. F1 = free tier (no VNet integration). B1+ = paid (VNet integration supported)."
  default     = "F1"

  validation {
    condition     = contains(["F1", "B1", "B2", "B3", "S1", "S2", "S3", "P1v2", "P2v2", "P3v2"], var.app_service_sku)
    error_message = "app_service_sku must be a valid App Service SKU (e.g. F1, B1, S1)."
  }
}

variable "subnet_app_id" {
  type        = string
  description = "Resource ID of the app subnet for VNet integration (only used when SKU is B1 or higher)"
}

variable "key_vault_tenant_id" {
  type        = string
  description = "Azure AD tenant ID for Key Vault"
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
