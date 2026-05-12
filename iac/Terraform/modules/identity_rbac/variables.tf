// identity_rbac variables.tf

variable "resource_group_id" {
  type        = string
  description = "Resource ID of the station resource group (for Supervisor scope)"
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID (for Administrator scope)"
}

variable "tenant_id" {
  type        = string
  description = "Azure AD tenant ID — passed through to outputs for app settings"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to taggable resources"
  default     = {}
}
