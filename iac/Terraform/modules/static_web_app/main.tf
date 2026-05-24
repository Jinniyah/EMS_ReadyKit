// modules/static_web_app/main.tf
//
// Azure Static Web Apps — hosts the EMS ReadyKit React frontend.
//
// Static Web Apps (SWA) is the right choice here over Storage + CDN because:
//   - Free tier includes a global CDN, custom domain, and managed TLS
//   - Built-in GitHub Actions integration via deployment token
//   - SWA routes all unknown paths back to index.html (required for React Router)
//   - No egress costs for static assets
//
// The Free tier has no SLA but is appropriate for dev/demo. Upgrade to
// Standard tier for production (adds custom auth, private endpoints, SLA).
//
// Security posture:
//   - HTTPS only — no plain HTTP access
//   - Deployment token stored as GitHub secret, never in Terraform state output logs
//   - CORS is handled by the backend App Service, not this resource
//   - Azure AD auth is enforced in the React app via MSAL, not at the SWA layer
//
// Region note:
//   SWA is only available in: centralus, eastus2, westus2, westeurope, eastasia.
//   northcentralus is NOT supported. This module defaults to centralus.
//   The location only affects metadata placement — SWA serves from a global CDN.

resource "azurerm_static_web_app" "frontend" {
  name                = "swa-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = var.sku_tier
  sku_size            = var.sku_tier

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "swa_diag" {
  name                       = "diag-swa"
  target_resource_id         = azurerm_static_web_app.frontend.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
