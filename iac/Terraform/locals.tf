// locals.tf
// Resolves the current subscription dynamically so no subscription ID
// is hardcoded in version-controlled files.

data "azurerm_subscription" "current" {}

locals {
  # Resolved at plan time from the authenticated Azure context.
  # Avoids hardcoding an environment-specific subscription ID in source control.
  subscription_id = data.azurerm_subscription.current.subscription_id

  project     = "ems-readykit"
  environment = var.environment
  location    = var.location

  # Common tags applied to all resources
  common_tags = {
    Project     = local.project
    Environment = local.environment
    Owner       = var.owner_tag
    CostCenter  = var.cost_center_tag
    ManagedBy   = "Terraform"
  }

  # Naming prefix for resources
  name_prefix = "${local.project}-${local.environment}"
}
