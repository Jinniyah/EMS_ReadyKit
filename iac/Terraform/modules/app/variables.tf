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

variable "environment" {
  type        = string
  description = "Deployment environment (dev/staging/prod). Controls Key Vault purge protection and retention."
  default     = "dev"
}

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU. F1 = free tier (no VNet integration or backup). B1+ = paid."
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
  description = "PostgreSQL connection string stored as a Key Vault secret"
  sensitive   = true
}

variable "storage_account_name" {
  type        = string
  description = "Storage account name passed to the app as a setting"
}

variable "storage_account_sas_url" {
  type        = string
  description = "SAS URL for the storage account container used for App Service backup (required for B1+ SKUs)"
  sensitive   = true
  default     = ""
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID for diagnostic settings"
}

variable "office_ip_cidr" {
  type        = string
  description = "Office or admin IP in CIDR notation to allow SCM/Kudu access (e.g. \"203.0.113.5/32\"). Leave empty to deny all SCM access."
  default     = ""

  validation {
    condition     = var.office_ip_cidr == "" || can(regex("^(\\d{1,3}\\.){3}\\d{1,3}/\\d{1,2}$", var.office_ip_cidr))
    error_message = "office_ip_cidr must be a valid CIDR block (e.g. \"203.0.113.5/32\") or empty string."
  }
}

variable "allowed_admin_ips" {
  type        = list(string)
  description = "Public IP addresses (CIDR) allowed to access the app Key Vault during Terraform runs (e.g. [\"203.0.113.5/32\"])"
  default     = []
}

variable "tenant_id" {
  type        = string
  description = "Azure AD tenant ID — set as AZURE_AD_TENANT_ID app setting for JWT validation"
}

variable "client_id" {
  type        = string
  description = "App Registration client ID — set as AZURE_AD_CLIENT_ID app setting for JWT validation"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
