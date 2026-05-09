// policy variables.tf

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID for policy assignment scope"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name (used for resource group-scoped policies)"
}

variable "allowed_location" {
  type        = string
  description = "The single Azure region where resources are permitted. Always passed from root local.location — do not rely on this default."
  default     = "northcentralus"
}

variable "required_tags" {
  type        = list(string)
  description = "List of tag keys that must be present on all resources"
  default     = ["Project", "Environment", "Owner", "CostCenter", "ManagedBy"]
}
