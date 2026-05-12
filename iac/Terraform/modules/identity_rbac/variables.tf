// identity_rbac variables.tf

variable "resource_group_id" {
  type        = string
  description = "Resource ID of the station resource group (for Supervisor and CI/CD scope)"
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID (for Administrator scope)"
}

variable "tenant_id" {
  type        = string
  description = "Azure AD tenant ID — passed through to outputs for app settings"
}

variable "tfstate_storage_account_id" {
  type        = string
  description = "Resource ID of the storage account holding Terraform state — grants CI/CD service principal Storage Blob Data Contributor so it can read/write state with azuread_auth"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to taggable resources"
  default     = {}
}
