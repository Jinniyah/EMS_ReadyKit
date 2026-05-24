// modules/static_web_app/variables.tf

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to deploy the Static Web App into"
}

variable "location" {
  type        = string
  description = "Azure region for SWA metadata placement. Must be one of: centralus, eastus2, westus2, westeurope, eastasia. SWA is a global resource — this does not affect CDN edge location or performance."
  default     = "centralus"

  validation {
    condition     = contains(["centralus", "eastus2", "westus2", "westeurope", "eastasia"], var.location)
    error_message = "Azure Static Web Apps is only available in: centralus, eastus2, westus2, westeurope, eastasia."
  }
}

variable "name_prefix" {
  type        = string
  description = "Naming prefix shared across all resources (e.g. ems-readykit-dev)"
}

variable "sku_tier" {
  type        = string
  description = "SWA SKU tier: Free (dev/demo) or Standard (production — adds custom auth, private endpoints, SLA)"
  default     = "Free"

  validation {
    condition     = contains(["Free", "Standard"], var.sku_tier)
    error_message = "sku_tier must be 'Free' or 'Standard'."
  }
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Resource ID of the Log Analytics workspace for diagnostic settings"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
