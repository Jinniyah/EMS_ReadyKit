// siem variables.tf

variable "resource_group_name" {
  type        = string
  description = "Resource group for SIEM resources"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource naming"
}

variable "subnet_monitoring_id" {
  type        = string
  description = "Resource ID of the monitoring/management subnet"
}

variable "admin_username" {
  type        = string
  description = "Admin username for the Security Onion VM"
  default     = "siemadmin"
}

variable "admin_password" {
  type        = string
  description = "Admin password for the Security Onion VM"
  sensitive   = true
}

variable "vm_size" {
  type        = string
  description = "VM size for Security Onion (minimum 4 vCPU / 8 GB RAM recommended)"
  default     = "Standard_D4s_v3"
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
