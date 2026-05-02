// network variables.tf
variable "resource_group_name" {
  type        = string
  description = "Resource group name for network resources"
}

variable "location" {
  type        = string
  description = "Azure region for network resources"
}