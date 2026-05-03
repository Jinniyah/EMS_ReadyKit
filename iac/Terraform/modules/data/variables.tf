// data variables.tf

variable "resource_group_name" {
  type        = string
  description = "Resource group for data resources"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource naming"
}

variable "subnet_data_id" {
  type        = string
  description = "Resource ID of the data subnet for private endpoint"
}

variable "sql_admin_login" {
  type        = string
  description = "SQL Server administrator login"
}

variable "sql_admin_password" {
  type        = string
  description = "SQL Server administrator password"
  sensitive   = true
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
