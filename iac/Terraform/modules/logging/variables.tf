// logging variables.tf

variable "resource_group_name" {
  type        = string
  description = "Resource group to deploy logging resources into"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource naming"
}

variable "log_retention_days" {
  type        = number
  description = "Number of days to retain logs in Log Analytics"
  default     = 30
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
