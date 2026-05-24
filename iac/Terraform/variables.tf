// Root-level variables

variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  type    = string
  default = "northcentralus"
  validation {
    condition     = length(var.location) > 0
    error_message = "location must not be empty."
  }
}

variable "owner_tag" {
  type    = string
  default = "EMS-ReadyKit-Team"
  validation {
    condition     = length(var.owner_tag) > 0
    error_message = "owner_tag must not be empty."
  }
}

variable "cost_center_tag" {
  type    = string
  default = "EMS-Demo"
  validation {
    condition     = length(var.cost_center_tag) > 0
    error_message = "cost_center_tag must not be empty."
  }
}

variable "storage_account_name" {
  type    = string
  default = "emsreadykitstorage123"
  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "storage_account_name must be 3-24 lowercase alphanumeric characters."
  }
}

variable "pg_admin_login" {
  type    = string
  default = "emsadmin"
  validation {
    condition     = length(var.pg_admin_login) >= 4 && !contains(["admin", "administrator", "postgres", "root"], lower(var.pg_admin_login))
    error_message = "pg_admin_login must be at least 4 characters and not a reserved name."
  }
}

variable "pg_admin_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU. B1 recommended — enables VNet integration, always-on, no CPU quota."
  default     = "B1"
  validation {
    condition     = contains(["F1", "B1", "B2", "B3", "S1", "S2", "S3", "P1v2", "P2v2", "P3v2"], var.app_service_sku)
    error_message = "app_service_sku must be a valid App Service SKU."
  }
}

variable "static_web_app_sku" {
  type        = string
  description = "Free for dev/demo. Standard for production."
  default     = "Free"
  validation {
    condition     = contains(["Free", "Standard"], var.static_web_app_sku)
    error_message = "static_web_app_sku must be 'Free' or 'Standard'."
  }
}

variable "enable_siem" {
  type    = bool
  default = false
}

variable "siem_admin_username" {
  type    = string
  default = "siemadmin"
}

variable "siem_admin_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "allowed_admin_ips" {
  type        = list(string)
  description = "Public IPs (CIDR) allowed to access Key Vault during terraform apply. Find yours: (Invoke-WebRequest -Uri 'https://checkip.amazonaws.com').Content.Trim()"
  default     = []
}

variable "monthly_budget_usd" {
  type    = number
  default = 50
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be positive."
  }
}

variable "budget_start_date" {
  type    = string
  default = "2026-05-01T00:00:00Z"
  validation {
    condition     = can(regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$", var.budget_start_date))
    error_message = "budget_start_date must be RFC3339 format: YYYY-MM-DDTHH:MM:SSZ."
  }
}

variable "budget_alert_emails" {
  type    = list(string)
  default = []
}

variable "office_ip_cidr" {
  type    = string
  default = ""
  validation {
    condition     = var.office_ip_cidr == "" || can(regex("^(\\d{1,3}\\.){3}\\d{1,3}/\\d{1,2}$", var.office_ip_cidr))
    error_message = "office_ip_cidr must be a valid CIDR block or empty string."
  }
}
