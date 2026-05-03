// network variables.tf

variable "resource_group_name" {
  type        = string
  description = "Resource group name for network resources"
}

variable "location" {
  type        = string
  description = "Azure region for network resources"
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID for NSG flow log diagnostics"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
