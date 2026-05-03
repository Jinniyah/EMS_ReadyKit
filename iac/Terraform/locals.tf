locals {
  subscription_id = "75fce2ea-1d83-4c5a-9929-b424b2913c8e"

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
