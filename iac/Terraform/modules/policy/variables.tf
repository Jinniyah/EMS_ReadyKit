// modules/policy/variables.tf

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID for policy assignment scope"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name"
}

variable "allowed_locations" {
  type        = list(string)
  description = "Azure regions permitted for resource deployment. Includes northcentralus (primary) and centralus (required for Static Web Apps)."
  default     = ["northcentralus", "centralus"]
}

variable "required_tags" {
  type        = list(string)
  description = "List of tag keys that must be present on all resources"
  default     = ["Project", "Environment", "Owner", "CostCenter", "ManagedBy"]
}
