// Root-level variables

variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, staging, prod)"
  default     = "dev"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  # Changed from eastus → eastus2: SQL provisioning is restricted in eastus
  # on trial/free subscriptions. eastus2 has open quota for both SQL and App Service.
  default     =  "southcentralus" # tried "eastus" and "eastus2"
}

variable "owner_tag" {
  type        = string
  description = "Owner tag value applied to all resources"
  default     = "EMS-ReadyKit-Team"
}

variable "cost_center_tag" {
  type        = string
  description = "Cost center tag value applied to all resources"
  default     = "EMS-Demo"
}

variable "storage_account_name" {
  type        = string
  description = "Globally unique name for the blob storage account"
  default     = "emsreadykitstorage123"
}

variable "sql_admin_login" {
  type        = string
  description = "SQL Server administrator login name"
  default     = "emsadmin"
}

variable "sql_admin_password" {
  type        = string
  description = "SQL Server administrator password (sensitive)"
  sensitive   = true
}

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU. Use F1 for free tier (no VNet integration), B1 for Basic (requires quota)."
  default     = "F1"
}

variable "enable_siem" {
  type        = bool
  description = "Whether to deploy the optional Security Onion SIEM VM"
  default     = false
}

variable "siem_admin_username" {
  type        = string
  description = "Admin username for the Security Onion VM"
  default     = "siemadmin"
}

variable "siem_admin_password" {
  type        = string
  description = "Admin password for the Security Onion VM (sensitive)"
  sensitive   = true
  default     = ""
}
