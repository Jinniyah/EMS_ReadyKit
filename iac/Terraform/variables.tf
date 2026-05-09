// Root-level variables

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  default     = "northcentralus"

  validation {
    condition     = length(var.location) > 0
    error_message = "location must not be empty."
  }
}

variable "owner_tag" {
  type        = string
  description = "Owner tag value applied to all resources"
  default     = "EMS-ReadyKit-Team"

  validation {
    condition     = length(var.owner_tag) > 0
    error_message = "owner_tag must not be empty."
  }
}

variable "cost_center_tag" {
  type        = string
  description = "Cost center tag value applied to all resources"
  default     = "EMS-Demo"

  validation {
    condition     = length(var.cost_center_tag) > 0
    error_message = "cost_center_tag must not be empty."
  }
}

variable "storage_account_name" {
  type        = string
  description = "Globally unique name for the blob storage account (3-24 lowercase alphanumeric)"
  default     = "emsreadykitstorage123"

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "storage_account_name must be 3-24 characters, lowercase letters and numbers only."
  }
}

variable "pg_admin_login" {
  type        = string
  description = "PostgreSQL Flexible Server administrator login name"
  default     = "emsadmin"

  validation {
    condition     = length(var.pg_admin_login) >= 4 && !contains(["admin", "administrator", "postgres", "root"], lower(var.pg_admin_login))
    error_message = "pg_admin_login must be at least 4 characters and must not be a reserved name (admin, administrator, postgres, root)."
  }
}

variable "pg_admin_password" {
  type        = string
  description = "PostgreSQL administrator password (sensitive). Leave empty to use the randomly generated password."
  sensitive   = true
  default     = ""
}

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU. F1 for free demo (no VNet integration). B1/P1v2 for production with private networking."
  default     = "F1"

  validation {
    condition     = contains(["F1", "B1", "B2", "B3", "S1", "S2", "S3", "P1v2", "P2v2", "P3v2"], var.app_service_sku)
    error_message = "app_service_sku must be a valid App Service SKU (e.g. F1, B1, S1, P1v2)."
  }
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

variable "allowed_admin_ips" {
  type        = list(string)
  description = "Public IP addresses (CIDR) allowed to access the platform Key Vault during bootstrap"
  default     = []
}

# ── Budget ────────────────────────────────────────────────────────────────────

variable "monthly_budget_usd" {
  type        = number
  description = "Monthly budget threshold in USD for cost alerts"
  default     = 50

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be a positive number."
  }
}

variable "budget_start_date" {
  type        = string
  description = "Budget period start date in RFC3339 format (e.g. \"2026-05-01T00:00:00Z\")"
  default     = "2026-05-01T00:00:00Z"

  validation {
    condition     = can(regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$", var.budget_start_date))
    error_message = "budget_start_date must be in RFC3339 format: YYYY-MM-DDTHH:MM:SSZ."
  }
}

variable "budget_alert_emails" {
  type        = list(string)
  description = "Email addresses to notify when budget thresholds are reached. If empty, no notifications are sent."
  default     = []
}

# ── Networking ────────────────────────────────────────────────────────────────

variable "office_ip_cidr" {
  type        = string
  description = "Office or admin IP in CIDR notation used to restrict SCM/Kudu access (e.g. \"203.0.113.5/32\")"
  default     = ""

  validation {
    condition     = var.office_ip_cidr == "" || can(regex("^(\\d{1,3}\\.){3}\\d{1,3}/\\d{1,2}$", var.office_ip_cidr))
    error_message = "office_ip_cidr must be a valid CIDR block (e.g. \"203.0.113.5/32\") or empty string."
  }
}
